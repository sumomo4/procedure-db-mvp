Attribute VB_Name = "Numbering_Logic"
Option Explicit

'==============================================================================
' Module:      Numbering_Logic
' Purpose:     採番ロジック本体（小分割・副作用最小化・保守性重視）
' Dependencies:
'   - M_Config
' Notes:
'   - Select/Selection は使用しない
'   - 引数は原則 ByVal。更新が必要な場合のみ ByRef
' History:
'   2026-02-16  Initial
'   2026-03-09  大見出し行判定を「灰色 OR テーマ薄緑(Accent6のTint)」に拡張
'==============================================================================

'------------------------------------------------------------------------------
' Public Sub:   RenumberWorksheet
' Purpose:      指定されたワークシートに採番を実行する
' Arguments:    ByVal target_sheet As Worksheet
' Returns:      None
' Exceptions:   ヘッダが見つからない場合は何もしない（静かに終了）
' SideEffects:  セルに書き込み
'------------------------------------------------------------------------------
Public Sub RenumberWorksheet(ByVal target_sheet As Worksheet)
    Dim headerRow As Long
    Dim numberColsArry As Variant
    Dim startRow As Long
    Dim lastRow As Long

    ' 大見出し色（灰色/薄緑）判定用
    Dim grayColor As Variant                 ' RGB(Long) or Empty
    Dim greenTheme As Variant                ' XlThemeColor or Empty
    Dim greenTint As Variant                 ' Double or Empty
    Dim greenRgb As Variant                  ' RGB(Long) or Empty

    numberColsArry = findNumberColumns(target_sheet, headerRow)
    If headerRow = 0 Then Exit Sub

    startRow = headerRow + 1
    lastRow = GetLastUsedRow(target_sheet)
    If lastRow < startRow Then Exit Sub

    ' ★灰色/薄緑（テーマ）を両方推定
    Call detectHeaderColors(target_sheet, startRow, lastRow, numberColsArry, grayColor, greenTheme, greenTint, greenRgb)

    Call renumberRows(target_sheet, startRow, lastRow, numberColsArry, grayColor, greenTheme, greenTint, greenRgb)
End Sub


'========================
' 採番メインループ
'========================
Private Sub renumberRows( _
    ByVal target_sheet As Worksheet, _
    ByVal start_row As Long, _
    ByVal last_row As Long, _
    ByVal number_colsArry As Variant, _
    ByVal gray_color As Variant, _
    ByVal green_theme As Variant, _
    ByVal green_tint As Variant, _
    ByVal green_rgb As Variant _
)
    Dim bigNo As Long
    Dim midNo As Long
    Dim smallNo As Long
    Dim shouldInitNextRow As Boolean
    Dim r As Long

    bigNo = INITIAL_BIG_NO
    midNo = INITIAL_MID_NO
    smallNo = INITIAL_SMALL_NO
    shouldInitNextRow = False

    For r = start_row To last_row

        ' 1) 大見出し行（灰色 OR 薄緑）判定を最優先
        If isHeaderRow(target_sheet, r, number_colsArry, gray_color, green_theme, green_tint, green_rgb) Then
            bigNo = bigNo + 1
            midNo = 0
            smallNo = 0

            Call writeNumbers(target_sheet, r, number_colsArry, bigNo, midNo, smallNo)
            shouldInitNextRow = True
            GoTo ContinueNextRow
        End If

        ' 2) 大見出し行の次行は常に (中=1, 小=1) を付与（要件B）
        If shouldInitNextRow Then
            Call handleNextRowAfterHeader(target_sheet, r, number_colsArry, bigNo, midNo, smallNo)
            shouldInitNextRow = False
            GoTo ContinueNextRow
        End If

        ' 3) 通常行（E/Fに文字があるかで採番）
        Call handleNormalRow(target_sheet, r, number_colsArry, bigNo, midNo, smallNo)

ContinueNextRow:
    Next r
End Sub


'------------------------
' 大見出し行の次行処理（要件B：常に 中=1, 小=1 を書く）
'------------------------
Private Sub handleNextRowAfterHeader( _
    ByVal target_sheet As Worksheet, _
    ByVal row_index As Long, _
    ByVal number_colsArry As Variant, _
    ByVal big_no As Long, _
    ByRef mid_no As Long, _
    ByRef small_no As Long _
)
    mid_no = 1
    small_no = 1
    Call writeNumbers(target_sheet, row_index, number_colsArry, big_no, mid_no, small_no)
End Sub


'------------------------
' 通常行処理（E/Fで判定）
'------------------------
Private Sub handleNormalRow( _
    ByVal target_sheet As Worksheet, _
    ByVal row_index As Long, _
    ByVal number_colsArry As Variant, _
    ByRef big_no As Long, _
    ByRef mid_no As Long, _
    ByRef small_no As Long _
)
    Dim hasMain As Boolean
    Dim hasSub As Boolean

    hasMain = hasText(target_sheet.Cells(row_index, COL_MAIN_TRIGGER))
    hasSub = hasText(target_sheet.Cells(row_index, COL_SUB_TRIGGER))

    If hasMain Then
        ' E列に文字：中+1、小は1に戻す
        If big_no < 0 Then big_no = 0

        mid_no = mid_no + 1
        If RESET_SMALL_ON_MAIN Then
            small_no = 1
        End If

        Call writeNumbers(target_sheet, row_index, number_colsArry, big_no, mid_no, small_no)
        Exit Sub
    End If

    If hasSub Then
        ' F列に文字：小+1
        If big_no < 0 Then big_no = 0
        If mid_no = 0 Then mid_no = 1

        small_no = small_no + 1
        Call writeNumbers(target_sheet, row_index, number_colsArry, big_no, mid_no, small_no)
        Exit Sub
    End If

    ' 空行：何もしない
End Sub


'========================
' 列探索：「大」「中」「小」を同一行で探す
'========================
Private Function findNumberColumns(ByVal target_sheet As Worksheet, ByRef header_row As Long) As Variant
    Dim bigCell As Range
    Dim r As Long
    Dim colBig As Long
    Dim colsArry(1 To 3) As Long

    header_row = 0

    Set bigCell = target_sheet.Cells.Find(What:=HEADER_BIG_TEXT, LookIn:=xlValues, LookAt:=xlWhole)
    If bigCell Is Nothing Then Exit Function

    colBig = bigCell.Column

    For r = 1 To HEADER_SEARCH_MAX_ROW
        If CStr(target_sheet.Cells(r, colBig).Value) = HEADER_BIG_TEXT _
           And CStr(target_sheet.Cells(r, colBig + 1).Value) = HEADER_MID_TEXT _
           And CStr(target_sheet.Cells(r, colBig + 2).Value) = HEADER_SMALL_TEXT Then

            header_row = r
            colsArry(eClmBig) = colBig
            colsArry(eClmMid) = colBig + 1
            colsArry(eClmSmall) = colBig + 2

            findNumberColumns = colsArry
            Exit Function
        End If
    Next r
End Function


'==============================================================================
' 大見出し色（灰色/薄緑）推定
'
' - 「A～C(=採番列)が塗りあり & 同一色」の行を候補
' - 灰色: RGB(Interior.Color) の最頻を採用（ただし Accent6 は除外）
' - 薄緑: ThemeColor=Accent6 の候補行から最頻 TintAndShade を採用
'==============================================================================
Private Sub detectHeaderColors( _
    ByVal target_sheet As Worksheet, _
    ByVal start_row As Long, _
    ByVal last_row As Long, _
    ByVal number_colsArry As Variant, _
    ByRef out_grayColor As Variant, _
    ByRef out_greenTheme As Variant, _
    ByRef out_greenTint As Variant, _
    ByRef out_greenRgb As Variant _
)
    Dim grayCounts As Object
    Dim greenCounts As Object
    Dim r As Long
    Dim colBig As Long, colMid As Long, colSmall As Long

    Dim rgb As Long
    Dim th As Long
    Dim tint As Double
    Dim key As String

    colBig = CLng(number_colsArry(eClmBig))
    colMid = CLng(number_colsArry(eClmMid))
    colSmall = CLng(number_colsArry(eClmSmall))

    Set grayCounts = CreateObject("Scripting.Dictionary")
    Set greenCounts = CreateObject("Scripting.Dictionary")

    out_grayColor = Empty
    out_greenTheme = Empty
    out_greenTint = Empty
    out_greenRgb = Empty

    For r = start_row To last_row
        If isSameFillColorOnThreeCells(target_sheet, r, colBig, colMid, colSmall) Then
            rgb = target_sheet.Cells(r, colBig).Interior.Color
            th = getThemeColorSafe(target_sheet.Cells(r, colBig))
            tint = getTintSafe(target_sheet.Cells(r, colBig))

            ' 薄緑候補：ThemeColor=Accent6
            If th = xlThemeColorAccent6 Then
                key = Format$(Round(tint, 4), "0.0000") & "|" & CStr(rgb)
                If Not greenCounts.Exists(key) Then greenCounts.Add key, 0
                greenCounts(key) = CLng(greenCounts(key)) + 1

            ' 灰色候補：Accent6以外の最頻RGB
            Else
                key = CStr(rgb)
                If Not grayCounts.Exists(key) Then grayCounts.Add key, 0
                grayCounts(key) = CLng(grayCounts(key)) + 1
            End If
        End If
    Next r

    ' 薄緑（Accent6）の最頻Tint/RGB
    If greenCounts.Count > 0 Then
        Dim bestGreenKey As String
        bestGreenKey = getMostFrequentKey(greenCounts)

        out_greenTheme = xlThemeColorAccent6
        out_greenTint = CDbl(Split(bestGreenKey, "|")(0))
        out_greenRgb = CLng(Split(bestGreenKey, "|")(1))
    End If

    ' 灰色の最頻RGB（Accent6以外）
    If grayCounts.Count > 0 Then
        out_grayColor = CLng(getMostFrequentKey(grayCounts))
    End If
End Sub

Private Function getMostFrequentKey(ByVal dict As Object) As String
    Dim eachKey As Variant
    Dim maxCount As Long
    Dim bestKey As String

    maxCount = -1
    bestKey = vbNullString

    For Each eachKey In dict.keys
        If CLng(dict(eachKey)) > maxCount Then
            maxCount = CLng(dict(eachKey))
            bestKey = CStr(eachKey)
        End If
    Next eachKey

    getMostFrequentKey = bestKey
End Function


'========================
' 大見出し行判定（灰色 OR 薄緑）
'
' - 薄緑：ThemeColor=Accent6 & TintAndShade一致（優先）
'          取得不可の場合はRGB一致（フォールバック）
' - 灰色：RGB一致
'========================
Private Function isHeaderRow( _
    ByVal target_sheet As Worksheet, _
    ByVal row_index As Long, _
    ByVal number_colsArry As Variant, _
    ByVal gray_color As Variant, _
    ByVal green_theme As Variant, _
    ByVal green_tint As Variant, _
    ByVal green_rgb As Variant _
) As Boolean

    Dim colBig As Long, colMid As Long, colSmall As Long
    Dim cBig As Range, cMid As Range, cSmall As Range

    colBig = CLng(number_colsArry(eClmBig))
    colMid = CLng(number_colsArry(eClmMid))
    colSmall = CLng(number_colsArry(eClmSmall))

    Set cBig = target_sheet.Cells(row_index, colBig)
    Set cMid = target_sheet.Cells(row_index, colMid)
    Set cSmall = target_sheet.Cells(row_index, colSmall)

    ' 塗り無しは除外
    If cBig.Interior.Pattern = xlNone Then Exit Function
    If cMid.Interior.Pattern = xlNone Then Exit Function
    If cSmall.Interior.Pattern = xlNone Then Exit Function

    ' 3セルが同一塗り（誤検出防止）
    If cBig.Interior.Color <> cMid.Interior.Color Then Exit Function
    If cBig.Interior.Color <> cSmall.Interior.Color Then Exit Function

    ' --- 1) 薄緑（Accent6 + Tint）判定（優先） ---
    If Not IsEmpty(green_theme) And Not IsEmpty(green_tint) Then
        Dim thB As Long, thM As Long, thS As Long
        thB = getThemeColorSafe(cBig)
        thM = getThemeColorSafe(cMid)
        thS = getThemeColorSafe(cSmall)

        If thB = xlThemeColorAccent6 And thM = xlThemeColorAccent6 And thS = xlThemeColorAccent6 Then
            If Abs(getTintSafe(cBig) - CDbl(green_tint)) < 0.0002 _
               And Abs(getTintSafe(cMid) - CDbl(green_tint)) < 0.0002 _
               And Abs(getTintSafe(cSmall) - CDbl(green_tint)) < 0.0002 Then
                isHeaderRow = True
                Exit Function
            End If
        End If

        ' ThemeColor/Tintが取れないケース向け：RGBでフォールバック
        If Not IsEmpty(green_rgb) Then
            If cBig.Interior.Color = CLng(green_rgb) Then
                isHeaderRow = True
                Exit Function
            End If
        End If
    End If

    ' --- 2) 灰色（RGB）判定 ---
    If Not IsEmpty(gray_color) Then
        If cBig.Interior.Color = CLng(gray_color) Then
            isHeaderRow = True
            Exit Function
        End If
    End If
End Function


'------------------------
' A～C（3セル）が「塗りあり」かつ「同一色」かを判定
'------------------------
Private Function isSameFillColorOnThreeCells( _
    ByVal target_sheet As Worksheet, _
    ByVal row_index As Long, _
    ByVal col_big As Long, _
    ByVal col_mid As Long, _
    ByVal col_small As Long _
) As Boolean
    ' 塗り無しは除外
    If target_sheet.Cells(row_index, col_big).Interior.Pattern = xlNone Then Exit Function
    If target_sheet.Cells(row_index, col_mid).Interior.Pattern = xlNone Then Exit Function
    If target_sheet.Cells(row_index, col_small).Interior.Pattern = xlNone Then Exit Function

    ' 同一色か確認
    If target_sheet.Cells(row_index, col_big).Interior.Color <> target_sheet.Cells(row_index, col_mid).Interior.Color Then Exit Function
    If target_sheet.Cells(row_index, col_big).Interior.Color <> target_sheet.Cells(row_index, col_small).Interior.Color Then Exit Function

    isSameFillColorOnThreeCells = True
End Function


'------------------------
' Interior.ThemeColor を安全に読む（エラー回避）
' 戻り値：ThemeColor(=XlThemeColor) / 取得不可なら -1
'------------------------
Private Function getThemeColorSafe(ByVal c As Range) As Long
    On Error GoTo SafeExit
    getThemeColorSafe = CLng(c.Interior.ThemeColor)
    Exit Function
SafeExit:
    getThemeColorSafe = -1
End Function

'------------------------
' Interior.TintAndShade を安全に読む（エラー回避）
' 取得不可なら 0 を返す（フォールバック）
'------------------------
Private Function getTintSafe(ByVal c As Range) As Double
    On Error GoTo SafeExit
    getTintSafe = CDbl(c.Interior.TintAndShade)
    Exit Function
SafeExit:
    getTintSafe = 0#
End Function


'========================
' 最終使用行取得
'========================
Private Function GetLastUsedRow(ByVal target_sheet As Worksheet) As Long
    Dim lastCell As Range

    Set lastCell = target_sheet.Cells.Find( _
        What:="*", _
        LookIn:=xlFormulas, _
        LookAt:=xlPart, _
        SearchOrder:=xlByRows, _
        SearchDirection:=xlPrevious _
    )

    If lastCell Is Nothing Then
        GetLastUsedRow = 1
    Else
        GetLastUsedRow = lastCell.Row
    End If
End Function


'========================
' 文字あり判定
'========================
Private Function hasText(ByVal cell_range As Range) As Boolean
    hasText = (Len(Trim$(CStr(cell_range.Value))) > 0)
End Function


'========================
' 書き込み
'========================
Private Sub writeNumbers( _
    ByVal target_sheet As Worksheet, _
    ByVal row_index As Long, _
    ByVal number_colsArry As Variant, _
    ByVal big_no As Long, _
    ByVal mid_no As Long, _
    ByVal small_no As Long _
)
    target_sheet.Cells(row_index, CLng(number_colsArry(eClmBig))).Value = big_no
    target_sheet.Cells(row_index, CLng(number_colsArry(eClmMid))).Value = mid_no
    target_sheet.Cells(row_index, CLng(number_colsArry(eClmSmall))).Value = small_no
End Sub

