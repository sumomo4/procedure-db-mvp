Attribute VB_Name = "Mod_UI"
Option Explicit

'==== 設定（必要に応じて変更）====
Private Const TEMPLATE_SHEET As String = "command_template" '入力ブック側テンプレ
Private Const OUT_SHEET_NAME As String = "command"          '出力ファイル内のシート名
Private Const OUT_PREFIX As String = "app修正前_"

Public Sub runCdCreator()
    On Error GoTo EH

    Dim prevScreenUpdating As Boolean: prevScreenUpdating = Application.ScreenUpdating
    Dim prevEnableEvents As Boolean: prevEnableEvents = Application.EnableEvents
    Dim prevCalc As XlCalculation: prevCalc = Application.Calculation
    Dim prevAlerts As Boolean: prevAlerts = Application.DisplayAlerts

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.Calculation = xlCalculationManual
    Application.DisplayAlerts = False

    '--- 完了ポップアップ用の集計 ---
    Dim createdCount As Long: createdCount = 0
    Dim failedCount As Long: failedCount = 0
    Dim createdPaths As Collection: Set createdPaths = New Collection

    '--- 必要シート参照（非表示でも参照自体は可能）---
    Dim logWs As Worksheet: Set logWs = ThisWorkbook.Worksheets(SHEET_LOG)
    Dim promptWs As Worksheet: Set promptWs = ThisWorkbook.Worksheets(SHEET_PROMPT)

    ClearLogArea logWs
    Call Mod_Log.logInfo("開始", "runCdCreator")

    '--- CS候補収集（シート名に "CS" を含む）---
    Dim candidates As Collection
    Set candidates = GetCsCandidates(ThisWorkbook)

    If candidates.Count = 0 Then
        Call Mod_Log.logError("CS対象シートが見つかりません（シート名に 'CS' を含むシートが0件）", "runCdCreator")
        GoTo Finally
    End If

    '--- 選択確定（1件なら自動、複数ならフォーム）---
    Dim selected As Collection
    If candidates.Count = 1 Then
        Set selected = candidates
        Call Mod_Log.logInfo("CS候補=1件のため自動選択: " & candidates(1).Name, "runCdCreator")
    Else
        Set selected = ShowCsSelectForm(candidates)
        If selected Is Nothing Then
            Call Mod_Log.logInfo("キャンセルされました", "runCdCreator")
            GoTo Finally 'キャンセル時はポップアップ出さない
        End If
        Call Mod_Log.logInfo("選択CS数=" & selected.Count, "runCdCreator")
    End If

    '--- 出力先フォルダ選択 ---
    Dim outFolder As String
    outFolder = DecideOutputFolder()
    If Len(outFolder) = 0 Then
        Call Mod_Log.logInfo("出力先フォルダ選択がキャンセルされました", "runCdCreator")
        GoTo Finally 'キャンセル時はポップアップ出さない
    End If

    '--- テンプレ存在確認（非表示でもOKだが、Copy時に可視化する）---
    Dim tmpl As Worksheet
    On Error Resume Next
    Set tmpl = ThisWorkbook.Worksheets(TEMPLATE_SHEET)
    On Error GoTo EH
    If tmpl Is Nothing Then
        Call Mod_Log.logError("テンプレートシート '" & TEMPLATE_SHEET & "' が見つかりません。", "runCdCreator")
        GoTo Finally
    End If

    '--- プロンプト辞書読み込み（1回だけ）---
    Dim rules As Object
    Set rules = Mod_PromptRules.LoadPromptRules(promptWs)

    '★作成元ファイル名（【原本】除去＋_作業CS以降カット）
    Dim srcBase As String
    srcBase = GetSourceBaseName(ThisWorkbook.Name)

    '--- CSごとに別ファイル出力 ---
    Dim csWs As Worksheet
    For Each csWs In selected
        On Error GoTo PerCsEH

        ' ヘッダ行検出（複数段ヘッダ対応）
        Dim headerRow As Long
        headerRow = Mod_Mapping.FindHeaderRow(csWs, 10)
        If headerRow = 0 Then
            Call Mod_Log.logError("CSヘッダ行を特定できません（時刻/window/P/コマンドが同一行にありません）", "sheet=" & csWs.Name)
            failedCount = failedCount + 1
            GoTo NextCs
        End If

        ' ブロック開始列（時刻ヘッダ列）
        Dim starts As Collection
        Set starts = Mod_Mapping.GetDeviceBlockStartCols(csWs, headerRow)
        If starts.Count = 0 Then
            Call Mod_Log.logError("CSヘッダ行に「時刻」が見つかりません", "sheet=" & csWs.Name & ", headerRow=" & headerRow)
            failedCount = failedCount + 1
            GoTo NextCs
        End If

        '--- テンプレを新規ブックとしてコピー（非表示対策：一時可視化）---
        Dim tmplVis As XlSheetVisibility
        tmplVis = tmpl.Visible
        tmpl.Visible = xlSheetVisible
        tmpl.Copy 'ここで出力ブックが作成される
        tmpl.Visible = tmplVis

        Dim outWb As Workbook
        Set outWb = ActiveWorkbook

        Dim cdWs As Worksheet
        Set cdWs = outWb.Worksheets(1) 'このシートが command になる

        '★出力ブックに必要なシートをコピー（並び順：工事→command→application）
        '★工事情報入力シート(含む) はコピー後に値貼り付け（数式→値）
        Call CopyExtraSheetsToOutput(outWb, cdWs)

        ' command シート名を設定
        On Error Resume Next
        cdWs.Name = OUT_SHEET_NAME
        On Error GoTo PerCsEH

        ClearOutputArea cdWs

        '--- CD生成 ---
        Call Mod_Flatten.BuildCdFromCs(csWs, cdWs, rules, starts, headerRow)

        '========================================================
        ' 出力ファイル名：
        '  app修正前_<作成元>_<シート名(_CS除去)>_CD_yyyymmdd.xlsx
        '========================================================
        Dim sheetPart As String
        sheetPart = RemoveCsSuffix(csWs.Name)
        sheetPart = SanitizeFileName(sheetPart)

        Dim basePart As String
        basePart = SanitizeFileName(srcBase)

        Dim stamp As String
        stamp = Format$(Date, "yyyymmdd")

        Dim outFileName As String
        outFileName = OUT_PREFIX & basePart & "_" & sheetPart & "_CD_" & stamp & ".xlsx"

        Dim fullPath As String
        fullPath = BuildUniquePath(outFolder, outFileName)

        ' ★出力ブック内の command/application を保存前に値貼り付け（数式→値）
        Call PasteValuesForOutputSheets(outWb)

        outWb.SaveAs fileName:=fullPath, FileFormat:=xlOpenXMLWorkbook
        outWb.Close SaveChanges:=False

        createdCount = createdCount + 1
        createdPaths.Add fullPath
        Call Mod_Log.logInfo("出力完了: " & csWs.Name & " -> " & fullPath, "runCdCreator")

NextCs:
        On Error GoTo EH
    Next csWs

    Call Mod_Log.logInfo("完了", "runCdCreator")

Finally:
    ' 仕様：出力が1件以上あった場合のみ表示
    If createdCount > 0 Then
        Dim msg As String
        msg = "CD作成が完了しました。" & vbCrLf & vbCrLf & _
              "作成数：" & createdCount & " 件" & vbCrLf & _
              IIf(failedCount > 0, "失敗数：" & failedCount & " 件" & vbCrLf, "") & _
              "出力先：" & outFolder & vbCrLf & vbCrLf & _
              "作成ファイル（先頭10件まで）：" & vbCrLf & BuildFileList(createdPaths, 10)
        MsgBox msg, vbInformation, "CDCreator"
    End If

    Application.DisplayAlerts = prevAlerts
    Application.Calculation = prevCalc
    Application.EnableEvents = prevEnableEvents
    Application.ScreenUpdating = prevScreenUpdating
    Exit Sub

PerCsEH:
    failedCount = failedCount + 1
    Call Mod_Log.logError("CS処理中の例外(" & Err.Number & "): " & Err.Description, "sheet=" & csWs.Name)

    '生成途中ブックが残っている可能性があるので、可能なら閉じる
    On Error Resume Next
    If Not ActiveWorkbook Is Nothing Then
        If ActiveWorkbook.Name <> ThisWorkbook.Name Then
            ActiveWorkbook.Close SaveChanges:=False
        End If
    End If
    On Error GoTo EH
    Resume NextCs

EH:
    Call Mod_Log.logError("実行時例外(" & Err.Number & "): " & Err.Description, "runCdCreator")
    Resume Finally
End Sub

'========================
' 作成元ファイル名（ベース名）を作る（ルール固定）
' - 拡張子除去
' - 先頭の「【原本】」を削除
' - 「_作業CS」があればそこより前で切り落とし
'========================
Private Function GetSourceBaseName(ByVal wbName As String) As String
    Dim base As String
    base = wbName

    Dim dotPos As Long
    dotPos = InStrRev(base, ".")
    If dotPos > 0 Then base = Left$(base, dotPos - 1)

    If Left$(base, Len("【原本】")) = "【原本】" Then
        base = Mid$(base, Len("【原本】") + 1)
    End If

    Dim p As Long
    p = InStr(1, base, "_作業CS", vbTextCompare)
    If p > 0 Then
        base = Left$(base, p - 1)
    End If

    If Len(Trim$(base)) = 0 Then base = "出力"
    GetSourceBaseName = base
End Function

'========================
' シート名から「_CS」を除去
'========================
Private Function RemoveCsSuffix(ByVal sheetName As String) As String
    Dim t As String
    t = sheetName
    t = Replace(t, "_CS", "", 1, -1, vbTextCompare)
    RemoveCsSuffix = t
End Function

'========================
' ★完了ポップアップ用のファイル一覧整形
'========================
Private Function BuildFileList(ByVal paths As Collection, ByVal maxCount As Long) As String
    Dim s As String: s = ""
    Dim i As Long
    Dim n As Long: n = paths.Count
    Dim limit As Long: limit = IIf(n < maxCount, n, maxCount)

    For i = 1 To limit
        s = s & "・" & CStr(paths(i)) & vbCrLf
    Next i
    If n > maxCount Then
        s = s & "…他 " & (n - maxCount) & " 件" & vbCrLf
    End If
    BuildFileList = s
End Function

'========================
' 出力ブックへ追加シートをコピー（並び順制御込み）
' 左→右：工事情報入力シート(含む複数) → command → application
' かつ、工事情報入力シート(含む) は「値貼り付け」（数式→値）
' ※非表示対策：コピー元は一時的に可視化→処理後に戻す
'========================
Private Sub CopyExtraSheetsToOutput(ByVal outWb As Workbook, ByVal commandWs As Worksheet)
    ' 1) “工事情報入力シート” を含むシート（部分一致）：全部コピー
    Dim foundKouji As Boolean
    foundKouji = False

    Dim srcWs As Worksheet
    For Each srcWs In ThisWorkbook.Worksheets
        If InStr(1, srcWs.Name, "工事情報入力シート", vbTextCompare) > 0 Then
            foundKouji = True

            Dim vis As XlSheetVisibility
            vis = srcWs.Visible
            srcWs.Visible = xlSheetVisible

            Dim idxBefore As Long
            idxBefore = commandWs.Index
            srcWs.Copy Before:=commandWs

            Dim newWs As Worksheet
            Set newWs = outWb.Worksheets(idxBefore)
            Call ConvertSheetFormulasToValues(newWs)

            srcWs.Visible = vis
        End If
    Next srcWs

    If Not foundKouji Then
        Call Mod_Log.logError( _
            "出力用のシートが見つかりません（名前に '工事情報入力シート' を含むシート）", _
            "CopyExtraSheetsToOutput" _
        )
    End If

    ' 2) “application” シート（完全一致）：右端に1枚
    Dim appSrc As Worksheet
    Set appSrc = FindSheetNameExact(ThisWorkbook, "application")

    If appSrc Is Nothing Then
        Call Mod_Log.logError( _
            "出力用のシートが見つかりません（'application' シート）", _
            "CopyExtraSheetsToOutput" _
        )
    Else
        Dim appVis As XlSheetVisibility
        appVis = appSrc.Visible
        appSrc.Visible = xlSheetVisible

        Dim appOut As Worksheet
        Set appOut = FindSheetNameExact(outWb, "application")
        If Not appOut Is Nothing Then
            Application.DisplayAlerts = False
            appOut.Delete
            Application.DisplayAlerts = True
        End If

        appSrc.Copy After:=outWb.Worksheets(outWb.Worksheets.Count)
        On Error Resume Next
        outWb.Worksheets(outWb.Worksheets.Count).Name = "application"
        On Error GoTo 0

        appSrc.Visible = appVis
    End If
End Sub

'========================
' シート内の数式を値に変換（値貼り付け相当）
'========================
Private Sub ConvertSheetFormulasToValues(ByVal ws As Worksheet)
    On Error GoTo SafeExit
    If Application.WorksheetFunction.CountA(ws.Cells) = 0 Then GoTo SafeExit
    Dim ur As Range
    Set ur = ws.UsedRange
    ur.Value2 = ur.Value2
SafeExit:
    On Error GoTo 0
End Sub

'========================
' 出力ブック内の指定シートを保存前に値貼り付け（数式→値）
' 対象：command / application
'========================
Private Sub PasteValuesForOutputSheets(ByVal wb As Workbook)
    Call PasteValuesIfSheetExists(wb, OUT_SHEET_NAME)
    Call PasteValuesIfSheetExists(wb, "application")
End Sub

Private Sub PasteValuesIfSheetExists(ByVal wb As Workbook, ByVal sheetName As String)
    On Error GoTo SafeExit

    Dim ws As Worksheet
    Set ws = FindSheetNameExact(wb, sheetName)
    If ws Is Nothing Then GoTo SafeExit

    Call ConvertSheetFormulasToValues(ws)

SafeExit:
    On Error GoTo 0
End Sub

'========================
' CS候補収集（シート名に"CS"を含む）
'========================
Private Function GetCsCandidates(ByVal wb As Workbook) As Collection
    Dim col As New Collection
    Dim ws As Worksheet
    For Each ws In wb.Worksheets
        If InStr(1, ws.Name, "CS", vbTextCompare) > 0 Then
            col.Add ws
        End If
    Next ws
    Set GetCsCandidates = col
End Function

'========================
' フォームで選択（キャンセルならNothing）
' ★修正：UserForm型を直参照しない（late binding）→コンパイルエラー回避
'========================
Private Function ShowCsSelectForm(ByVal candidates As Collection) As Collection
    Dim frm As Object

    ' UserFormを名前で生成（型参照しない）
    On Error Resume Next
    Set frm = VBA.UserForms.Add("frmSelectCsSheets")
    On Error GoTo 0

    If frm Is Nothing Then
        Dim ret As VbMsgBoxResult
        ret = MsgBox( _
            "複数CS選択フォーム(frmSelectCsSheets)が見つからないため、" & vbCrLf & _
            "CS候補を全件対象として処理しますか？", _
            vbYesNoCancel + vbExclamation, "CDCreator" _
        )
        If ret = vbYes Then
            Dim allSel As New Collection
            Dim ws As Worksheet
            For Each ws In candidates
                allSel.Add ws
            Next ws
            Set ShowCsSelectForm = allSel
            Exit Function
        Else
            ' No / Cancel は中止扱い
            Set ShowCsSelectForm = Nothing
            Exit Function
        End If
    End If

    frm.SetCandidates candidates
    frm.Show vbModal

    If frm.IsCanceled Then
        Unload frm
        Set ShowCsSelectForm = Nothing
        Exit Function
    End If

    Dim sel As Collection
    Set sel = frm.GetSelectedSheets
    Unload frm
    Set ShowCsSelectForm = sel
End Function

'========================
' 出力先フォルダ選択
'========================
Private Function DecideOutputFolder() As String
    Dim msg As String
    msg = "出力先フォルダを選択してください。" & vbCrLf & vbCrLf & _
          "はい(Y): このブックと同じフォルダ" & vbCrLf & _
          "いいえ(N): フォルダを選択" & vbCrLf & _
          "キャンセル: 中止"

    Dim ret As VbMsgBoxResult
    ret = MsgBox(msg, vbYesNoCancel + vbQuestion, "出力先フォルダ")

    If ret = vbCancel Then
        DecideOutputFolder = ""
        Exit Function
    End If

    If ret = vbYes Then
        If Len(ThisWorkbook.Path) > 0 Then
            DecideOutputFolder = ThisWorkbook.Path
            Exit Function
        End If
    End If

    Dim fd As FileDialog
    Set fd = Application.FileDialog(msoFileDialogFolderPicker)
    fd.Title = "出力先フォルダを選択してください"
    fd.AllowMultiSelect = False

    If fd.Show <> -1 Then
        DecideOutputFolder = ""
        Exit Function
    End If

    DecideOutputFolder = fd.SelectedItems(1)
End Function

'========================
' command出力領域クリア（3行目以降）
'========================
Private Sub ClearOutputArea(ByVal cdWs As Worksheet)
    On Error GoTo SafeExit
    If Application.WorksheetFunction.CountA(cdWs.Cells) = 0 Then GoTo SafeExit

    Dim lastRow As Long
    lastRow = cdWs.Cells.Find(What:="*", After:=cdWs.Cells(1, 1), LookIn:=xlFormulas, _
                              LookAt:=xlPart, SearchOrder:=xlByRows, SearchDirection:=xlPrevious).Row
    If lastRow < 3 Then GoTo SafeExit

    cdWs.Rows("3:" & lastRow).ClearContents
SafeExit:
    On Error GoTo 0
End Sub

Private Sub ClearLogArea(ByVal logWs As Worksheet)
    On Error GoTo SafeExit
    If Application.WorksheetFunction.CountA(logWs.Cells) = 0 Then GoTo SafeExit

    Dim lastRow As Long
    lastRow = logWs.Cells.Find(What:="*", After:=logWs.Cells(1, 1), LookIn:=xlFormulas, _
                               LookAt:=xlPart, SearchOrder:=xlByRows, SearchDirection:=xlPrevious).Row
    If lastRow < 2 Then GoTo SafeExit

    logWs.Rows("2:" & lastRow).ClearContents
SafeExit:
    On Error GoTo 0
End Sub

'========================
' ファイル名禁止文字除去
'========================
Private Function SanitizeFileName(ByVal s As String) As String
    Dim t As String
    t = s
    t = Replace(t, "\", "_")
    t = Replace(t, "/", "_")
    t = Replace(t, ":", "_")
    t = Replace(t, "*", "_")
    t = Replace(t, "?", "_")
    t = Replace(t, """", "_")
    t = Replace(t, "<", "_")
    t = Replace(t, ">", "_")
    t = Replace(t, vbLf, "_")
    Do While Len(t) > 0 And (Right$(t, 1) = "." Or Right$(t, 1) = " ")
        t = Left$(t, Len(t) - 1)
    Loop
    If Len(t) = 0 Then t = "CS"
    SanitizeFileName = t
End Function

'========================
' 同名ファイルがあれば _01,_02... を付けてユニーク化
'========================
Private Function BuildUniquePath(ByVal folder As String, ByVal fileName As String) As String
    Dim base As String, ext As String
    Dim dotPos As Long
    dotPos = InStrRev(fileName, ".")
    If dotPos > 0 Then
        base = Left$(fileName, dotPos - 1)
        ext = Mid$(fileName, dotPos)
    Else
        base = fileName
        ext = ""
    End If

    Dim full As String
    full = folder & "\" & fileName
    If Dir$(full) = "" Then
        BuildUniquePath = full
        Exit Function
    End If

    Dim i As Long
    For i = 1 To 999
        full = folder & "\" & base & "_" & Format$(i, "00") & ext
        If Dir$(full) = "" Then
            BuildUniquePath = full
            Exit Function
        End If
    Next i

    BuildUniquePath = folder & "\" & base & "_" & Format$(Now, "ss") & ext
End Function

'========================
' シート名 完全一致検索
'========================
Private Function FindSheetNameExact(ByVal wb As Workbook, ByVal sheetName As String) As Worksheet
    On Error Resume Next
    Set FindSheetNameExact = wb.Worksheets(sheetName)
    On Error GoTo 0
End Function






