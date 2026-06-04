Attribute VB_Name = "Mod_Flatten"
Option Explicit

'========================================
' Mod_Flatten : CS→CD生成
'
' ★FIX(既存)
' - 集約モード(WriteAggregatedSteps)で、同一装置ブロック内の同一コマンドが
'   ステップ違いで「集約されて消える」問題を解消するため、
'   rowKey に stepId（=CS行番号）を追加し、縦方向の重複を潰さない。
'   ※横方向（同一stepIdで複数装置が同じならRをまとめる）は維持。
'
' ★既存/追加仕様
' - CD2行目（A～T）をCSの「コマンド」ヘッダ1つ上の値で設定（値貼り）
' - CD X列（cont.time）をX3～最終行まで数値5で埋める
' - prompt-only 行のprompt(Z)を「装置別の次の実行プロンプト」に置換
'
' ★追加仕様（2026-02-16）
' (1) 抑止ルール：
'     同一項番×同一装置で NeedRule=RULE_ALWAYS_T が出現した後、
'     NeedRule=RULE_PROMPT_SYM_AND_CMD が出現するまでの間に出てくる
'     NeedRule=RULE_CMD_NONEMPTY のプロンプトは CDに出力しない（連鎖抑止）
'
' (2) 項番全体の扱い：
'     同一項番内（辞書定義済みPromptのみ対象）のNeedRuleが
'     {RULE_ALWAYS_T, RULE_CMD_NONEMPTY} のみで構成される場合、
'     ALWAYS_Tのみ相当として CMD_NONEMPTY を完全に無かったことにする
'     （=出力しない＋notify判定にも影響させない）
'
' (3) notify判定への影響：
'     抑止された CMD_NONEMPTY は prevNeedRule 等の履歴を更新しない
'
' ★追加仕様（2026-02-17/18）
' (4) 実行プロンプト判定の完全表駆動化（案B）
'     - ckOut補正の「直前行が実行系か？」判定を、
'       プロンプト表の NeedRule=RULE_PROMPT_SYM_AND_CMD に基づく判定へ変更
'     - prompt-only補正で用いる「実行プロンプト」集合も
'       プロンプト表（NeedRule=RULE_PROMPT_SYM_AND_CMD）の CdPromptOut から生成
'     - " >> " などの特例は廃止し、100% 表定義に従う
'
' ★追加仕様（2026-05-12）
' (5) CS側でチェック系prompt（chk/Eck/ckN/EcN）の「次のコマンド行」がSTOPの場合、
'     CD側ではそのSTOP行の直前へprompt-only空行を挿入し、直前の実行プロンプトを入れる。
'     また、STOP連動ではチェック系行の cont.on を解除しない。
'========================================

Private Const SEP As String = vbLf
Private Const NONE_SIG As String = "<NONE>"
' ckExist直後STOP対策：補正対象外にするための一時マーカー（出力保存前に空欄化）
Private Const STOP_BLANK_TYPE_MARKER As String = "__CKEXIST_STOP_PROMPT_BLANK"

' CD X列(cont.time)
Private Const CD_COL_CONT_TIME As Long = 24 ' X

' ★表駆動：実行プロンプト集合（CdPromptOut の正規化済み記号 → True）
Private mExecPromptOutSet As Object

'-------------------------------
' CSデータ開始行を自動検出（A/B/Cが数値の最初の行）
'-------------------------------
Private Function GetCsDataStartRow(ByVal ws As Worksheet, ByVal headerRow As Long, ByVal lastRow As Long) As Long
    Dim startRow As Long
    startRow = headerRow + 1
    If startRow < 1 Then startRow = 1

    Dim r As Long
    For r = startRow To lastRow
        Dim aStr As String, bStr As String, cVal As String
        aStr = NzStr(ws.Cells(r, COL_ITEM_A).Value)
        bStr = NzStr(ws.Cells(r, COL_ITEM_B).Value)
        cVal = NzStr(ws.Cells(r, COL_ITEM_C).Value)

        If (Len(aStr) > 0 And Len(bStr) > 0 And Len(cVal) > 0) Then
            If IsNumeric(aStr) And IsNumeric(bStr) And IsNumeric(cVal) Then
                GetCsDataStartRow = r
                Exit Function
            End If
        End If
    Next r

    GetCsDataStartRow = startRow
End Function

'-------------------------------
' 最終行（本モジュールローカル版）
'-------------------------------
Private Function GetLastUsedRowLocal(ByVal ws As Worksheet) As Long
    On Error GoTo Safe
    Dim f As Range
    Set f = ws.Cells.Find(What:="*", After:=ws.Cells(1, 1), LookIn:=xlFormulas, _
                          LookAt:=xlPart, SearchOrder:=xlByRows, SearchDirection:=xlPrevious)
    If f Is Nothing Then
        GetLastUsedRowLocal = 0
    Else
        GetLastUsedRowLocal = f.Row
    End If
    Exit Function
Safe:
    GetLastUsedRowLocal = 0
End Function

' ===== Signature（ステップ同一性判定用）=====
Private Function BuildSignature(ByVal cmdText As String, ByVal outType As String, ByVal outReg As String, ByVal outPrompt As String, ByVal outContOn As String) As String
    BuildSignature = cmdText & SEP & outType & SEP & outReg & SEP & outPrompt & SEP & outContOn
End Function

Private Sub SplitSignature(ByVal sig As String, ByRef cmdText As String, ByRef outType As String, ByRef outReg As String, ByRef outPrompt As String, ByRef outContOn As String)
    Dim parts() As String
    parts = Split(sig, SEP)
    cmdText = "": outType = "": outReg = "": outPrompt = "": outContOn = ""
    If UBound(parts) >= 0 Then cmdText = parts(0)
    If UBound(parts) >= 1 Then outType = parts(1)
    If UBound(parts) >= 2 Then outReg = parts(2)
    If UBound(parts) >= 3 Then outPrompt = parts(3)
    If UBound(parts) >= 4 Then outContOn = parts(4)
End Sub

'========================================================
' ★表駆動：実行プロンプト集合を構築
' - NeedRule=RULE_PROMPT_SYM_AND_CMD の行の CdPromptOut を採用
' - prompt-only補正等で用いるため、正規化して集合化
'========================================================
Private Sub InitExecPromptOutSet(ByVal promptRules As Object)
    Set mExecPromptOutSet = CreateObject("Scripting.Dictionary")
    If promptRules Is Nothing Then Exit Sub

    Dim k As Variant
    For Each k In promptRules.keys
        Dim rule As PromptRule
        Set rule = promptRules(k)
        If Not rule Is Nothing Then
            If UCase$(Trim$(rule.NeedRule)) = UCase$(RULE_PROMPT_SYM_AND_CMD) Then
                Dim p As String
                p = NzStr(rule.CdPromptOut)
                p = NormalizeExecPromptSymbol(p)
                If Len(p) > 0 Then
                    If Not mExecPromptOutSet.Exists(p) Then mExecPromptOutSet.Add p, True
                End If
            End If
        End If
    Next k
End Sub

'========================================
' メイン
'========================================
Public Sub BuildCdFromCs(ByVal csWs As Worksheet, ByVal cdWs As Worksheet, ByVal promptRules As Object, _
                         ByVal blockStarts As Collection, ByVal headerRow As Long, _
                         Optional ByVal outStartRow As Long = 3, Optional ByRef outNextRow As Variant)

    Dim itemOrder As Collection: Set itemOrder = New Collection
    Dim itemStepOrder As Object: Set itemStepOrder = CreateObject("Scripting.Dictionary")
    Dim itemStepDevSig As Object: Set itemStepDevSig = CreateObject("Scripting.Dictionary")
    Dim itemActiveDevs As Object: Set itemActiveDevs = CreateObject("Scripting.Dictionary")

    Dim stopStepDict As Object: Set stopStepDict = CreateObject("Scripting.Dictionary")
    Dim checkNextStopStepDict As Object: Set checkNextStopStepDict = CreateObject("Scripting.Dictionary")
    Dim notifyStepDict As Object: Set notifyStepDict = CreateObject("Scripting.Dictionary")
    Dim notifyItemDevs As Object: Set notifyItemDevs = CreateObject("Scripting.Dictionary")

    Dim prevNeedRuleByDev As Object: Set prevNeedRuleByDev = CreateObject("Scripting.Dictionary")
    Dim prevStepIdByDev As Object: Set prevStepIdByDev = CreateObject("Scripting.Dictionary")
    Dim prevItemKeyByDev As Object: Set prevItemKeyByDev = CreateObject("Scripting.Dictionary")

    Dim lastTTRowByItem As Object: Set lastTTRowByItem = CreateObject("Scripting.Dictionary")
    Dim lastTTStartByItem As Object: Set lastTTStartByItem = CreateObject("Scripting.Dictionary")

    ' ★抑止状態（項番×装置）
    Dim suppressCmdByDev As Object: Set suppressCmdByDev = CreateObject("Scripting.Dictionary")
    Dim suppressItemKey As String: suppressItemKey = ""

    Dim lastRow As Long: lastRow = GetLastUsedRowLocal(csWs)
    Dim dataStartRow As Long: dataStartRow = GetCsDataStartRow(csWs, headerRow, lastRow)

    If lastRow < dataStartRow Then
        Call Mod_Log.logWarn("CSに処理対象行がありません（データ開始行=" & dataStartRow & "）", "BuildCdFromCs")
        If Not IsMissing(outNextRow) Then outNextRow = outStartRow
        Exit Sub
    End If

    Call Mod_Log.logInfo("CSデータ開始行=" & dataStartRow & " (headerRow=" & headerRow & ")", "BuildCdFromCs")

    ' ★表駆動：実行プロンプト集合を構築
    Call InitExecPromptOutSet(promptRules)

    ' CD 2行目（A～T）をCSヘッダ上段から値貼りで作成
    Call FillCdRow2FromCs(csWs, cdWs, blockStarts, headerRow)

    ' ★②判定（項番が {ALWAYS_T, CMD_NONEMPTY} のみか）
    Dim itemOnlyAT_Cmd As Object
    Set itemOnlyAT_Cmd = BuildItemFlag_OnlyAlwaysT_AndCmdNonEmpty(csWs, promptRules, blockStarts, headerRow, dataStartRow, lastRow)

    Dim currentItemKey As String: currentItemKey = ""
    Dim r As Long

    For r = dataStartRow To lastRow

        ' ---- 項番決定（継承/部分入力スキップ） ----
        Dim aStr As String, bStr As String, cVal As String
        aStr = NzStr(csWs.Cells(r, COL_ITEM_A).Value)
        bStr = NzStr(csWs.Cells(r, COL_ITEM_B).Value)
        cVal = NzStr(csWs.Cells(r, COL_ITEM_C).Value)

        Dim rawItemKey As String
        rawItemKey = BuildItemKey(aStr, bStr, cVal)

        Dim itemKey As String
        Dim isInherited As Boolean
        isInherited = False
        itemKey = ""

        If Len(rawItemKey) > 0 Then
            currentItemKey = rawItemKey
            itemKey = rawItemKey
            If Not itemStepOrder.Exists(itemKey) Then
                itemStepOrder.Add itemKey, New Collection
                itemStepDevSig.Add itemKey, CreateObject("Scripting.Dictionary")
                itemActiveDevs.Add itemKey, CreateObject("Scripting.Dictionary")
                itemOrder.Add itemKey
            End If
        Else
            Dim hasAnyPart As Boolean
            hasAnyPart = (Len(aStr) > 0 Or Len(bStr) > 0 Or Len(cVal) > 0)
            If hasAnyPart Then
                Call Mod_Log.logWarn("項番が部分的に入力されています（A/B/Cのいずれか欠け）: スキップ", _
                                     "row=" & r & ", A=" & aStr & ", B=" & bStr & ", C=" & cVal)
                GoTo nextRow
            End If

            If Len(currentItemKey) = 0 Then
                Call Mod_Log.logWarn("項番なし行だが直前項番が無いためスキップ", "row=" & r)
                GoTo nextRow
            End If

            itemKey = currentItemKey
            isInherited = True
            If Not itemStepOrder.Exists(itemKey) Then
                itemStepOrder.Add itemKey, New Collection
                itemStepDevSig.Add itemKey, CreateObject("Scripting.Dictionary")
                itemActiveDevs.Add itemKey, CreateObject("Scripting.Dictionary")
                itemOrder.Add itemKey
            End If
        End If

        ' ★項番が切り替わったら抑止状態をリセット
        If itemKey <> suppressItemKey Then
            Set suppressCmdByDev = CreateObject("Scripting.Dictionary")
            suppressItemKey = itemKey
        End If

        ' ---- 装置ブロック走査 ----
        Dim bi As Long
        For bi = 1 To blockStarts.Count
            Dim startCol As Long, nextCol As Long
            startCol = CLng(blockStarts(bi))
            If bi < blockStarts.Count Then
                nextCol = CLng(blockStarts(bi + 1))
            Else
                nextCol = 0
            End If

            Dim cols As TBlockCols
            cols = Mod_Mapping.DetectBlockCols(csWs, startCol, nextCol, headerRow)
            If cols.windowCol = 0 Or cols.promptCol = 0 Or cols.commandCol = 0 Then
                Call Mod_Log.logWarn("装置ブロック必須ヘッダ不足（window/P/コマンド）", _
                                     "row=" & r & ", startCol=" & startCol & ", headerRow=" & headerRow)
                GoTo NextBlock
            End If

            Dim windowNo As Variant
            windowNo = csWs.Cells(2, cols.windowCol).Value
            If Not Mod_Validate.IsValidWindowNo(windowNo) Then
                Call Mod_Log.logError("Window番号不正", _
                                      "row=" & r & ", col=" & cols.windowCol & ", value=" & CStr(windowNo))
                GoTo NextBlock
            End If

            Dim devIndex As Long
            devIndex = CLng(windowNo)

            Dim promptKey As String
            promptKey = Mod_PromptRules.ResolvePromptKey(csWs.Cells(r, cols.promptCol))

            Dim cmdText As String
            cmdText = NzStr(csWs.Cells(r, cols.commandCol).Value)

            ' ---- TT特例 ----
            If UCase$(Trim$(promptKey)) = "TT" Then
                Dim lastTTRow As Long, ttStart As Long
                If lastTTRowByItem.Exists(itemKey) Then
                    lastTTRow = CLng(lastTTRowByItem(itemKey))
                Else
                    lastTTRow = 0
                End If

                If lastTTRow > 0 And (r = lastTTRow Or r = lastTTRow + 1) And lastTTStartByItem.Exists(itemKey) Then
                    ttStart = CLng(lastTTStartByItem(itemKey))
                Else
                    ttStart = r
                    lastTTStartByItem(itemKey) = ttStart
                    Call EnsureStepInOrder(itemStepOrder(itemKey), ttStart)
                End If

                lastTTRowByItem(itemKey) = r

                Dim sigTT As String
                sigTT = BuildSignature("Launch→Selectedをしてください", "notify", "", "", "")
                Call PutStepSig(itemStepDevSig(itemKey), ttStart, devIndex, sigTT)
                itemActiveDevs(itemKey)(CStr(devIndex)) = True
                GoTo NextBlock
            End If

            Dim stopFlg As Boolean
            stopFlg = IsCsStopRow(csWs, r, cols)
            If stopFlg Then
                Call ForcePrevStepContOff(itemStepOrder(itemKey), itemStepDevSig(itemKey), devIndex, r)
                Call RecordStopStep(stopStepDict, itemKey, devIndex, r)
            End If

            ' 継承行は「prompt非空 & command非空」だけ対象
            If isInherited Then
                If Len(promptKey) = 0 Then GoTo NextBlock
                If Not Mod_Validate.IsCommandNonEmpty(cmdText) Then GoTo NextBlock
            Else
                If Len(promptKey) = 0 Then GoTo NextBlock
            End If

            If Not promptRules.Exists(promptKey) Then
                Call Mod_Log.logWarn("PromptKeyが辞書未定義（スキップ）", "row=" & r & ", prompt=" & promptKey)
                GoTo NextBlock
            End If

            Dim rule As PromptRule
            Set rule = promptRules(promptKey)
            If rule Is Nothing Then
                Call Mod_Log.logWarn("PromptRuleがNothing（辞書格納異常の可能性）", "row=" & r & ", prompt=" & promptKey)
                GoTo NextBlock
            End If

            '===========================
            ' ①② CMD_NONEMPTY の出力抑止
            '===========================
            Dim currRuleId As String
            currRuleId = UCase$(Trim$(rule.NeedRule))
            If Len(currRuleId) = 0 Then currRuleId = UCase$(RULE_ALWAYS_T)

            Dim devKeyNR As String
            devKeyNR = CStr(devIndex)

            ' 抑止状態の更新（開始/解除）
            If currRuleId = UCase$(RULE_ALWAYS_T) Then
                suppressCmdByDev(devKeyNR) = True
            ElseIf currRuleId = UCase$(RULE_PROMPT_SYM_AND_CMD) Then
                suppressCmdByDev(devKeyNR) = False
            End If

            ' ②対象項番か？
            Dim isOnlyATandCmd As Boolean
            isOnlyATandCmd = False
            If Not itemOnlyAT_Cmd Is Nothing Then
                If itemOnlyAT_Cmd.Exists(itemKey) Then isOnlyATandCmd = CBool(itemOnlyAT_Cmd(itemKey))
            End If

            ' CMD_NONEMPTY 抑止判定
            Dim suppressThisCmd As Boolean
            suppressThisCmd = False
            If currRuleId = UCase$(RULE_CMD_NONEMPTY) Then
                If isOnlyATandCmd Then
                    suppressThisCmd = True
                Else
                    If suppressCmdByDev.Exists(devKeyNR) Then
                        If CBool(suppressCmdByDev(devKeyNR)) Then suppressThisCmd = True
                    End If
                End If
            End If

            If suppressThisCmd Then
                ' 抑止されたCMD_NONEMPTYはnotify判定に影響しない
                GoTo NextBlock
            End If

            ' ---- notify判定用：前回NeedRule → 今回NeedRule の遷移（PROMPT_SYM/CMD_NONEMPTY → ALWAYS_T） ----
            Dim prevRuleId As String
            If prevNeedRuleByDev.Exists(devKeyNR) Then
                prevRuleId = CStr(prevNeedRuleByDev(devKeyNR))
            Else
                prevRuleId = ""
            End If

            Dim prevStepId As Long
            If prevStepIdByDev.Exists(devKeyNR) Then
                prevStepId = CLng(prevStepIdByDev(devKeyNR))
            Else
                prevStepId = 0
            End If

            Dim prevItemKey As String
            If prevItemKeyByDev.Exists(devKeyNR) Then
                prevItemKey = CStr(prevItemKeyByDev(devKeyNR))
            Else
                prevItemKey = ""
            End If

            Dim shouldNotify As Boolean
            shouldNotify = ((UCase$(prevRuleId) = UCase$(RULE_PROMPT_SYM_AND_CMD) Or UCase$(prevRuleId) = UCase$(RULE_CMD_NONEMPTY)) And _
                            UCase$(currRuleId) = UCase$(RULE_ALWAYS_T) And prevStepId > 0)

            If shouldNotify Then
                If prevItemKey <> itemKey Then
                    Dim devDictN As Object
                    If notifyItemDevs.Exists(itemKey) Then
                        Set devDictN = notifyItemDevs(itemKey)
                    Else
                        Set devDictN = CreateObject("Scripting.Dictionary")
                        notifyItemDevs.Add itemKey, devDictN
                    End If
                    devDictN(CStr(devIndex)) = True
                Else
                    notifyStepDict(BuildItemDevStepKey(itemKey, devIndex, prevStepId)) = True
                End If
            End If

            ' notify判定用の履歴更新
            prevNeedRuleByDev(devKeyNR) = currRuleId
            prevStepIdByDev(devKeyNR) = r
            prevItemKeyByDev(devKeyNR) = itemKey

            Dim needIsR As Boolean
            needIsR = Mod_PromptRules.EvalNeedRule(rule.NeedRule, promptKey, cmdText)
            If needIsR = False Then GoTo NextBlock

            If rule.CommandRequired And Not Mod_Validate.IsCommandNonEmpty(cmdText) Then
                Call Mod_Log.logWarn("CommandRequiredなのにcommand空のため出力しません", "row=" & r & ", prompt=" & promptKey)
                GoTo NextBlock
            End If

            Dim outType As String, outReg As String, outPrompt As String, outContOn As String
            outType = rule.CdType
            outReg = rule.CdReg
            outPrompt = rule.CdPromptOut

            If Mod_Validate.IsCommandNonEmpty(cmdText) Then
                outContOn = "on"
            Else
                outContOn = ""
            End If
            If stopFlg Then outContOn = ""

            ' --- ckOut補正（表駆動：直前行がNeedRule=RULE_PROMPT_SYM_AND_CMDなら実行系） ---
            If r > dataStartRow Then
                Dim prevPromptKey As String
                prevPromptKey = Mod_PromptRules.ResolvePromptKey(csWs.Cells(r - 1, cols.promptCol))

                Dim prevCmdText As String
                prevCmdText = NzStr(csWs.Cells(r - 1, cols.commandCol).Value)

                Dim isPrevExec As Boolean
                isPrevExec = False

                If Len(prevPromptKey) > 0 Then
                    If promptRules.Exists(prevPromptKey) Then
                        Dim prevRule As PromptRule
                        Set prevRule = promptRules(prevPromptKey)
                        If Not prevRule Is Nothing Then
                            If UCase$(Trim$(prevRule.NeedRule)) = UCase$(RULE_PROMPT_SYM_AND_CMD) Then
                                isPrevExec = Mod_PromptRules.EvalNeedRule(prevRule.NeedRule, prevPromptKey, prevCmdText)
                            End If
                        End If
                    End If
                End If

                If IsCheckLikePrompt(promptKey) And isPrevExec Then
                    Call ForcePrevStepTypeCkOut(itemStepDevSig(itemKey), (r - 1), devIndex)
                End If
            End If

            Dim stepId As Long
            stepId = r
            Call EnsureStepInOrder(itemStepOrder(itemKey), stepId)

            Dim sig As String
            sig = BuildSignature(cmdText, outType, outReg, outPrompt, outContOn)
            Call PutStepSig(itemStepDevSig(itemKey), stepId, devIndex, sig)
            itemActiveDevs(itemKey)(CStr(devIndex)) = True

            ' チェック系promptの「次のコマンド行」がCS上でSTOPなら、後段でSTOP直前にprompt-only行を挿入する
            If IsCheckLikePrompt(promptKey) Then
                Call RecordCheckNextStopIfNeeded(checkNextStopStepDict, csWs, cols, itemKey, devIndex, r, lastRow)
            End If

NextBlock:
        Next bi

nextRow:
    Next r

    ' STOP連動：チェック系prompt直後STOPのprompt-only挿入、および既存のckOut無効化を適用
    Call ApplyStopNeutralize_CkOut(stopStepDict, checkNextStopStepDict, itemOrder, itemStepOrder, itemStepDevSig)

    Dim nextRowOut As Long
    nextRowOut = WriteCdWithShiftModes(cdWs, itemOrder, itemStepOrder, itemStepDevSig, itemActiveDevs, notifyStepDict, notifyItemDevs, outStartRow)

    ' prompt-only 調整（表駆動：mExecPromptOutSet を使用）
    Call AdjustPromptOnlyPromptByNextExecPrompt_SameNeed(cdWs, outStartRow, nextRowOut - 1)
    Call ClearStopBlankMarker(cdWs, outStartRow, nextRowOut - 1)

    ' X列（cont.time）を既定値5で埋める
    Call FillDefaultContTime(cdWs, outStartRow, nextRowOut - 1, 10)

    If Not IsMissing(outNextRow) Then outNextRow = nextRowOut
End Sub

'========================================
' CD X列(cont.time)を startRow～endRow に既定値で埋める
'========================================
Private Sub FillDefaultContTime(ByVal cdWs As Worksheet, ByVal startRow As Long, ByVal endRow As Long, ByVal defaultVal As Long)
    If endRow < startRow Then Exit Sub
    Dim r As Long
    For r = startRow To endRow
        cdWs.Cells(r, CD_COL_CONT_TIME).Value2 = defaultVal
    Next r
End Sub

'========================================
' CD（command）2行目（A～T）をCSの各装置ブロックから作成（値貼り）
'========================================
Private Sub FillCdRow2FromCs(ByVal csWs As Worksheet, ByVal cdWs As Worksheet, _
                             ByVal blockStarts As Collection, ByVal headerRow As Long)
    If headerRow <= 1 Then
        Call Mod_Log.logWarn("headerRow<=1のため、CD2行目の上書きをスキップしました", _
                             "FillCdRow2FromCs headerRow=" & headerRow)
        Exit Sub
    End If

    Dim c As Long
    For c = 1 To MAX_DEVICE_COL
        cdWs.Cells(2, c).Value = ""
    Next c

    Dim bi As Long
    For bi = 1 To blockStarts.Count
        Dim startCol As Long, nextCol As Long
        startCol = CLng(blockStarts(bi))
        If bi < blockStarts.Count Then
            nextCol = CLng(blockStarts(bi + 1))
        Else
            nextCol = 0
        End If

        Dim cols As TBlockCols
        cols = Mod_Mapping.DetectBlockCols(csWs, startCol, nextCol, headerRow)
        If cols.windowCol = 0 Or cols.commandCol = 0 Then
            Call Mod_Log.logWarn("装置ブロック必須ヘッダ不足（window/コマンド）", _
                                 "FillCdRow2FromCs startCol=" & startCol & ", headerRow=" & headerRow)
            GoTo NextBlock
        End If

        Dim windowNo As Variant
        windowNo = csWs.Cells(2, cols.windowCol).Value
        If Not Mod_Validate.IsValidWindowNo(windowNo) Then
            Call Mod_Log.logWarn("Window番号不正のため、CD2行目への反映をスキップ", _
                                 "FillCdRow2FromCs col=" & cols.windowCol & ", value=" & CStr(windowNo))
            GoTo NextBlock
        End If

        Dim devIndex As Long
        devIndex = CLng(windowNo)

        Dim srcVal As Variant
        srcVal = csWs.Cells(headerRow - 1, cols.commandCol).Value2

        Dim prevVal As Variant
        prevVal = cdWs.Cells(2, devIndex).Value2
        If Len(CStr(prevVal)) > 0 Then
            If CStr(prevVal) <> CStr(srcVal) Then
                Call Mod_Log.logWarn("同一装置列へのCD2行目値が競合（上書き）", _
                                     "FillCdRow2FromCs dev=" & devIndex & ", prev=" & CStr(prevVal) & ", new=" & CStr(srcVal))
            End If
        End If

        cdWs.Cells(2, devIndex).Value2 = srcVal

NextBlock:
    Next bi
End Sub

'========================================
' 出力（開始行指定＆次行を返す）
'========================================
Private Function WriteCdWithShiftModes(ByVal cdWs As Worksheet, ByVal itemOrder As Collection, ByVal itemStepOrder As Object, _
                                      ByVal itemStepDevSig As Object, ByVal itemActiveDevs As Object, ByVal notifyStepDict As Object, ByVal notifyItemDevs As Object, ByVal startRow As Long) As Long
    Dim headerFill As Long, headerFont As Long
    headerFill = cdWs.Range("A1").Interior.Color
    headerFont = cdWs.Range("A1").Font.Color

    Dim outRow As Long
    outRow = startRow

    Dim i As Long
    For i = 1 To itemOrder.Count
        Dim itemKey As String
        itemKey = CStr(itemOrder(i))

        If itemActiveDevs(itemKey).Count = 0 Then
            If (notifyItemDevs Is Nothing) Then GoTo NextItem
            If Not notifyItemDevs.Exists(itemKey) Then GoTo NextItem
        End If

        Dim itemStartRow As Long
        itemStartRow = outRow

        Dim perDevice As Boolean
        perDevice = IsPerDeviceMode(itemStepOrder(itemKey), itemStepDevSig(itemKey), itemActiveDevs(itemKey))

        ' 項番行
        Dim c As Long
        For c = 1 To MAX_DEVICE_COL
            cdWs.Cells(outRow, c).Value = DEFAULT_NEED
        Next c
        cdWs.Cells(outRow, CD_COL_TYPE).Value = ""
        cdWs.Cells(outRow, CD_COL_CONT_ON).Value = ""
        cdWs.Cells(outRow, CD_COL_REG).Value = ""
        cdWs.Cells(outRow, CD_COL_PROMPT).Value = ""
        cdWs.Cells(outRow, CD_COL_COMMAND).Value = itemKey
        cdWs.Cells(outRow, CD_COL_COMMAND).Interior.Color = headerFill
        cdWs.Cells(outRow, CD_COL_COMMAND).Font.Color = headerFont
        outRow = outRow + 1

        ' 項番境界 notify
        If Not notifyItemDevs Is Nothing Then
            If notifyItemDevs.Exists(itemKey) Then
                outRow = WriteNotifyRow(cdWs, outRow, notifyItemDevs(itemKey), "作業CSに則り実施")
            End If
        End If

        If perDevice Then
            outRow = WriteGroupedDeviceBlocks(cdWs, outRow, itemKey, itemStepOrder(itemKey), itemStepDevSig(itemKey), itemActiveDevs(itemKey), notifyStepDict)
        Else
            outRow = WriteAggregatedSteps(cdWs, outRow, itemKey, itemStepOrder(itemKey), itemStepDevSig(itemKey), notifyStepDict)
        End If

        ' 項番切替prompt-only（重複抑止：直前がprompt-onlyなら追加しない）
        If Not IsPromptOnlyRow(cdWs, outRow - 1) Then
            Dim lastExec As String
            lastExec = FindLastExecPromptInRange(cdWs, itemStartRow, outRow - 1)
            If Len(Trim$(lastExec)) > 0 Then
                Dim prevNeed As Variant
                prevNeed = ReadNeedArrayFromSheet(cdWs, outRow - 1)
                outRow = WritePromptOnlyRow(cdWs, outRow, lastExec, prevNeed)
            End If
        End If

NextItem:
    Next i

    WriteCdWithShiftModes = outRow
End Function

'--- prompt-only判定（command空欄 & 実行プロンプト）
Private Function IsPromptOnlyRow(ByVal cdWs As Worksheet, ByVal rowNo As Long) As Boolean
    If rowNo < 1 Then
        IsPromptOnlyRow = False
        Exit Function
    End If
    Dim cmd As String, p As String
    cmd = NzStr(cdWs.Cells(rowNo, CD_COL_COMMAND).Value)
    p = NzStr(cdWs.Cells(rowNo, CD_COL_PROMPT).Value)
    IsPromptOnlyRow = (Len(cmd) = 0 And IsExecPromptOut(p))
End Function

'========================================
' prompt-only 行の prompt(Z) を置換（表駆動）
'========================================
Private Sub AdjustPromptOnlyPromptByNextExecPrompt_SameNeed(ByVal cdWs As Worksheet, ByVal startRow As Long, ByVal endRow As Long)
    If endRow < startRow Then Exit Sub

    ' 次の実行prompt（装置ごと）
    Dim nextPromptByDev(1 To MAX_DEVICE_COL) As String
    Dim nextRowByDev(1 To MAX_DEVICE_COL) As Long
    Dim d As Long
    For d = 1 To MAX_DEVICE_COL
        nextPromptByDev(d) = ""
        nextRowByDev(d) = 0
    Next d

    Dim r As Long
    For r = endRow To startRow Step -1
        Dim p As String
        p = NzStr(cdWs.Cells(r, CD_COL_PROMPT).Value)

        Dim cmd As String
        cmd = NzStr(cdWs.Cells(r, CD_COL_COMMAND).Value)

        ' (1) prompt-only なら R装置群の「次の実行prompt」を見て差し替え
        If (NzStr(cdWs.Cells(r, CD_COL_TYPE).Value) <> STOP_BLANK_TYPE_MARKER) And (Len(cmd) = 0 And IsExecPromptOut(p)) Then
            Dim bestNextRow As Long: bestNextRow = 0
            Dim bestPrompt As String: bestPrompt = ""
            For d = 1 To MAX_DEVICE_COL
                If NzStr(cdWs.Cells(r, d).Value) = "R" Then
                    If nextRowByDev(d) > 0 Then
                        If bestNextRow = 0 Or nextRowByDev(d) < bestNextRow Then
                            bestNextRow = nextRowByDev(d)
                            bestPrompt = nextPromptByDev(d)
                        End If
                    End If
                End If
            Next d
            If bestNextRow > 0 And Len(Trim$(bestPrompt)) > 0 Then
                cdWs.Cells(r, CD_COL_PROMPT).Value = bestPrompt
            End If
        End If

        ' (2) 実行prompt行（NeedRule=RULE_PROMPT_SYM_AND_CMD相当）なら「次」を更新
        If IsExecPrompt_RuleSymAndCmd(p, cmd) Then
            For d = 1 To MAX_DEVICE_COL
                If NzStr(cdWs.Cells(r, d).Value) = "R" Then
                    nextPromptByDev(d) = p
                    nextRowByDev(d) = r
                End If
            Next d
        End If
    Next r
End Sub

'--- “実行prompt”判定（表駆動）
' 条件：command≠空 かつ promptOut が mExecPromptOutSet に含まれる
Private Function IsExecPrompt_RuleSymAndCmd(ByVal promptOut As String, ByVal cmdText As String) As Boolean
    If Not Mod_Validate.IsCommandNonEmpty(cmdText) Then
        IsExecPrompt_RuleSymAndCmd = False
        Exit Function
    End If

    Dim s As String
    s = NormalizeExecPromptSymbol(promptOut)

    If mExecPromptOutSet Is Nothing Then
        IsExecPrompt_RuleSymAndCmd = False
        Exit Function
    End If

    IsExecPrompt_RuleSymAndCmd = mExecPromptOutSet.Exists(s)
End Function

'--- 実行系プロンプト判定（完全表駆動）
' prompt-only 等で使用：mExecPromptOutSet に含まれる prompt を実行扱い
Private Function IsExecPromptOut(ByVal p As String) As Boolean
    Dim s As String
    s = NormalizeExecPromptSymbol(p)

    If mExecPromptOutSet Is Nothing Then
        IsExecPromptOut = False
        Exit Function
    End If

    IsExecPromptOut = mExecPromptOutSet.Exists(s)
End Function

'--- 実行系プロンプト記号の正規化（\> 等を > に寄せる。全角→半角も寄せる）
Private Function NormalizeExecPromptSymbol(ByVal p As String) As String
    Dim s As String
    s = Trim$(CStr(p))
    s = StrConv(s, vbNarrow)
    ' バックスラッシュ付きの記号を素の記号へ
    s = Replace(s, "\>", ">")
    s = Replace(s, "\$", "$")
    s = Replace(s, "\%", "%")
    s = Replace(s, "\#", "#")
    s = Trim$(s)
    NormalizeExecPromptSymbol = s
End Function

'--- チェック系プロンプト（既存仕様のまま）
Private Function IsCheckLikePrompt(ByVal p As String) As Boolean
    Select Case p
        Case "chk", "Eck", "ckN", "EcN"
            IsCheckLikePrompt = True
        Case Else
            IsCheckLikePrompt = False
    End Select
End Function

'--- CD出力後のチェック系行判定（type/promptどちらでも拾う）
Private Function IsCheckLikeCdRow(ByVal outType As String, ByVal outPrompt As String) As Boolean
    If IsCheckLikePrompt(outPrompt) Then
        IsCheckLikeCdRow = True
        Exit Function
    End If

    Select Case UCase$(Trim$(outType))
        Case "CKEXIST", "CKNOT"
            IsCheckLikeCdRow = True
        Case Else
            IsCheckLikeCdRow = False
    End Select
End Function

'--- CS上のSTOP行判定
' window列STOP（既存仕様）に加え、コマンド列そのものがSTOPの場合も拾う。
Private Function IsCsStopRow(ByVal csWs As Worksheet, ByVal rowNo As Long, ByRef cols As TBlockCols) As Boolean
    IsCsStopRow = False

    If cols.windowCol > 0 Then
        If IsStopToken(csWs.Cells(rowNo, cols.windowCol).Value) Then
            IsCsStopRow = True
            Exit Function
        End If
    End If

    If cols.commandCol > 0 Then
        If IsStopToken(csWs.Cells(rowNo, cols.commandCol).Value) Then
            IsCsStopRow = True
            Exit Function
        End If
    End If
End Function

'--- チェック系promptの次コマンド行がSTOPなら、STOP stepを記録する
Private Sub RecordCheckNextStopIfNeeded(ByVal checkNextStopStepDict As Object, ByVal csWs As Worksheet, _
                                        ByRef cols As TBlockCols, ByVal itemKey As String, ByVal devIndex As Long, _
                                        ByVal checkRow As Long, ByVal lastRow As Long)
    If checkNextStopStepDict Is Nothing Then Exit Sub

    Dim nextCmdRow As Long
    nextCmdRow = FindNextCommandRowInSameItem(csWs, cols, itemKey, checkRow, lastRow)
    If nextCmdRow <= 0 Then Exit Sub

    If IsCsStopRow(csWs, nextCmdRow, cols) Then
        Dim k As String
        k = BuildStopKey(itemKey, devIndex, nextCmdRow)
        If Not checkNextStopStepDict.Exists(k) Then checkNextStopStepDict.Add k, True
    End If
End Sub

'--- 同一項番内で、指定行より後ろにある最初の「コマンド非空」行を返す
Private Function FindNextCommandRowInSameItem(ByVal csWs As Worksheet, ByRef cols As TBlockCols, _
                                              ByVal currentItemKey As String, ByVal fromRow As Long, _
                                              ByVal lastRow As Long) As Long
    FindNextCommandRowInSameItem = 0
    If cols.commandCol <= 0 Then Exit Function

    Dim r As Long
    For r = fromRow + 1 To lastRow
        Dim aStr As String, bStr As String, cVal As String
        aStr = NzStr(csWs.Cells(r, COL_ITEM_A).Value)
        bStr = NzStr(csWs.Cells(r, COL_ITEM_B).Value)
        cVal = NzStr(csWs.Cells(r, COL_ITEM_C).Value)

        Dim rawItemKey As String
        rawItemKey = BuildItemKey(aStr, bStr, cVal)

        If Len(rawItemKey) > 0 Then
            If rawItemKey <> currentItemKey Then Exit Function
        Else
            Dim hasAnyPart As Boolean
            hasAnyPart = (Len(aStr) > 0 Or Len(bStr) > 0 Or Len(cVal) > 0)
            If hasAnyPart Then GoTo NextR
        End If

        If Mod_Validate.IsCommandNonEmpty(NzStr(csWs.Cells(r, cols.commandCol).Value)) Then
            FindNextCommandRowInSameItem = r
            Exit Function
        End If

NextR:
    Next r
End Function

'========================================
' STOP連動（修正）：ckOutの位置がSTOPなら、該当ckOutおよび後続のckExist/ckNotについて
' CDの type(V) と cont.on(W) を空にする（コマンド行自体は残す）
'========================================
Private Sub RecordStopStep(ByVal stopStepDict As Object, ByVal itemKey As String, ByVal devIndex As Long, ByVal stepId As Long)
    If stopStepDict Is Nothing Then Exit Sub
    Dim k As String
    k = BuildStopKey(itemKey, devIndex, stepId)
    If Not stopStepDict.Exists(k) Then stopStepDict.Add k, True
End Sub

Private Function BuildStopKey(ByVal itemKey As String, ByVal devIndex As Long, ByVal stepId As Long) As String
    BuildStopKey = CStr(itemKey) & ChrW(&H1F) & CStr(devIndex) & ChrW(&H1F) & CStr(stepId)
End Function

Private Sub ApplyStopNeutralize_CkOut(ByVal stopStepDict As Object, ByVal checkNextStopStepDict As Object, _
                                      ByVal itemOrder As Collection, ByVal itemStepOrder As Object, _
                                      ByVal itemStepDevSig As Object)
    If stopStepDict Is Nothing Then Exit Sub

    Dim iItem As Long
    For iItem = 1 To itemOrder.Count
        Dim itemKey As String
        itemKey = CStr(itemOrder(iItem))

        If Not itemStepOrder.Exists(itemKey) Then GoTo NextItem
        If Not itemStepDevSig.Exists(itemKey) Then GoTo NextItem

        Dim steps As Collection
        Set steps = itemStepOrder(itemKey)

        Dim stepDev As Object
        Set stepDev = itemStepDevSig(itemKey)

        ' 後ろから走査することで、STOP直前への空行挿入（Collection.Add Before）による
        ' インデックスずれの影響を避ける。
        Dim i As Long
        For i = steps.Count To 1 Step -1
            Dim stepId As Long
            stepId = CLng(steps(i))

            Dim stepKey As String
            stepKey = CStr(stepId)
            If Not stepDev.Exists(stepKey) Then GoTo NextStep

            Dim devMap As Object
            Set devMap = stepDev(stepKey)
            If devMap Is Nothing Then GoTo NextStep
            If devMap.Count = 0 Then GoTo NextStep

            Dim devKeys As Variant
            devKeys = devMap.keys

            Dim dk As Variant
            For Each dk In devKeys
                Dim devIndex As Long
                devIndex = CLng(dk)

                Dim stopKey As String
                stopKey = BuildStopKey(itemKey, devIndex, stepId)

                If stopStepDict.Exists(stopKey) Then
                    ' 新仕様：CS側でチェック系promptの次コマンド行がSTOPなら、STOP直前へprompt-only空行を挿入
                    If Not checkNextStopStepDict Is Nothing Then
                        If checkNextStopStepDict.Exists(stopKey) Then
                            Call InsertCheckNextStopPromptBlankIfNeeded(stepDev, steps, itemKey, i, stepId, devIndex)
                        End If
                    End If

                    Dim sig As String
                    sig = CStr(devMap(CStr(devIndex)))

                    Dim cmdText As String, outType As String, outReg As String, outPrompt As String, outContOn As String
                    Call SplitSignature(sig, cmdText, outType, outReg, outPrompt, outContOn)

                    If outType = "ckOut" Then
                        ' STOP位置のckOut自体は従来どおり自動化を外す（type/cont.onを空欄化）
                        outType = ""
                        outContOn = ""
                        devMap(CStr(devIndex)) = BuildSignature(cmdText, outType, outReg, outPrompt, outContOn)

                        ' STOPより後続のckExist/ckNotを、次の実行コマンドまで無効化する。
                        ' STOP直前に人工行を挿入した可能性があるため、現在のSTOP位置を再取得する。
                        Dim currentStopIndex As Long
                        currentStopIndex = GetStepIndex(steps, stepId)
                        If currentStopIndex = 0 Then currentStopIndex = i

                        Dim j As Long
                        For j = currentStopIndex + 1 To steps.Count
                            Dim stepId2 As Long
                            stepId2 = CLng(steps(j))

                            Dim stepKey2 As String
                            stepKey2 = CStr(stepId2)
                            If stepDev.Exists(stepKey2) Then
                                Dim devMap2 As Object
                                Set devMap2 = stepDev(stepKey2)

                                If Not devMap2 Is Nothing Then
                                    If devMap2.Exists(CStr(devIndex)) Then
                                        Dim sig2 As String
                                        sig2 = CStr(devMap2(CStr(devIndex)))

                                        Dim cmdText2 As String, outType2 As String, outReg2 As String, outPrompt2 As String, outContOn2 As String
                                        Call SplitSignature(sig2, cmdText2, outType2, outReg2, outPrompt2, outContOn2)

                                        '--- 次の「実行コマンド」が見つかったら、ここで打ち切り ---
                                        If IsExecPrompt_RuleSymAndCmd(outPrompt2, cmdText2) Then
                                            Exit For
                                        End If

                                        '--- ckExist / ckNot は「次の実行コマンド」まで無効化し続ける ---
                                        If outType2 = "ckExist" Or outType2 = "ckNot" Then
                                            outType2 = ""
                                            ' 2026-05-12: チェック系行の cont.on は解除しない
                                            devMap2(CStr(devIndex)) = BuildSignature(cmdText2, outType2, outReg2, outPrompt2, outContOn2)
                                        End If
                                    End If
                                End If
                            End If
                        Next j
                    End If
                End If
            Next dk
NextStep:
        Next i
NextItem:
    Next iItem
End Sub

'--- チェック系promptの次コマンド行STOP対策：必要時にSTOP直前へprompt-only空行を挿入する
Private Sub InsertCheckNextStopPromptBlankIfNeeded(ByVal stepDev As Object, ByVal steps As Collection, ByVal itemKey As String, _
                                                   ByVal stopIndex As Long, ByVal stopStepId As Long, ByVal devIndex As Long)
    Dim currentStopIndex As Long
    currentStopIndex = GetStepIndex(steps, stopStepId)
    If currentStopIndex = 0 Then currentStopIndex = stopIndex
    If currentStopIndex <= 1 Then Exit Sub

    Dim checkIndex As Long
    checkIndex = FindPreviousCommandStepIndex(stepDev, steps, currentStopIndex - 1, devIndex)
    If checkIndex <= 0 Then Exit Sub

    Dim checkStepId As Long
    checkStepId = CLng(steps(checkIndex))
    If Not stepDev.Exists(CStr(checkStepId)) Then Exit Sub

    Dim checkDevMap As Object
    Set checkDevMap = stepDev(CStr(checkStepId))
    If checkDevMap Is Nothing Then Exit Sub
    If Not checkDevMap.Exists(CStr(devIndex)) Then Exit Sub

    Dim checkSig As String
    checkSig = CStr(checkDevMap(CStr(devIndex)))

    Dim checkCmd As String, checkType As String, checkReg As String, checkPrompt As String, checkContOn As String
    Call SplitSignature(checkSig, checkCmd, checkType, checkReg, checkPrompt, checkContOn)

    If Not IsCheckLikeCdRow(checkType, checkPrompt) Then Exit Sub

    Dim insertPrompt As String
    insertPrompt = FindPreviousExecPromptInSteps(stepDev, steps, checkIndex - 1, devIndex)
    If Len(Trim$(insertPrompt)) = 0 Then Exit Sub

    Dim syntheticStepId As Long
    syntheticStepId = -CLng(stopStepId)

    currentStopIndex = GetStepIndex(steps, stopStepId)
    If currentStopIndex = 0 Then currentStopIndex = stopIndex

    If GetStepIndex(steps, syntheticStepId) = 0 Then
        steps.Add syntheticStepId, Before:=currentStopIndex
    End If

    Dim blankSig As String
    blankSig = BuildSignature("", STOP_BLANK_TYPE_MARKER, "", insertPrompt, "")
    Call PutStepSig(stepDev, syntheticStepId, devIndex, blankSig)
End Sub

'--- 指定位置以前から、同一装置の直近「command非空」stepのインデックスを返す
Private Function FindPreviousCommandStepIndex(ByVal stepDev As Object, ByVal steps As Collection, ByVal fromIndex As Long, ByVal devIndex As Long) As Long
    FindPreviousCommandStepIndex = 0
    If fromIndex < 1 Then Exit Function

    Dim i As Long
    For i = fromIndex To 1 Step -1
        Dim sid As Long
        sid = CLng(steps(i))

        If stepDev.Exists(CStr(sid)) Then
            Dim devMap As Object
            Set devMap = stepDev(CStr(sid))

            If Not devMap Is Nothing Then
                If devMap.Exists(CStr(devIndex)) Then
                    Dim sig As String
                    sig = CStr(devMap(CStr(devIndex)))

                    Dim cmdText As String, outType As String, outReg As String, outPrompt As String, outContOn As String
                    Call SplitSignature(sig, cmdText, outType, outReg, outPrompt, outContOn)

                    If Mod_Validate.IsCommandNonEmpty(cmdText) Then
                        FindPreviousCommandStepIndex = i
                        Exit Function
                    End If
                End If
            End If
        End If
    Next i
End Function

'--- 指定位置以前から、同一装置の直近「実行プロンプト」を返す
Private Function FindPreviousExecPromptInSteps(ByVal stepDev As Object, ByVal steps As Collection, ByVal fromIndex As Long, ByVal devIndex As Long) As String
    FindPreviousExecPromptInSteps = ""
    If fromIndex < 1 Then Exit Function

    Dim i As Long
    For i = fromIndex To 1 Step -1
        Dim sid As Long
        sid = CLng(steps(i))

        If stepDev.Exists(CStr(sid)) Then
            Dim devMap As Object
            Set devMap = stepDev(CStr(sid))

            If Not devMap Is Nothing Then
                If devMap.Exists(CStr(devIndex)) Then
                    Dim sig As String
                    sig = CStr(devMap(CStr(devIndex)))

                    Dim cmdText As String, outType As String, outReg As String, outPrompt As String, outContOn As String
                    Call SplitSignature(sig, cmdText, outType, outReg, outPrompt, outContOn)

                    If IsExecPrompt_RuleSymAndCmd(outPrompt, cmdText) Then
                        FindPreviousExecPromptInSteps = outPrompt
                        Exit Function
                    End If
                End If
            End If
        End If
    Next i
End Function

'--- Collection内のstepId位置を返す（なければ0）
Private Function GetStepIndex(ByVal steps As Collection, ByVal stepId As Long) As Long
    Dim i As Long
    For i = 1 To steps.Count
        If CLng(steps(i)) = stepId Then
            GetStepIndex = i
            Exit Function
        End If
    Next i
    GetStepIndex = 0
End Function

'--- ckExist後STOP対策の一時マーカーを出力前の空欄に戻す
Private Sub ClearStopBlankMarker(ByVal cdWs As Worksheet, ByVal startRow As Long, ByVal endRow As Long)
    If endRow < startRow Then Exit Sub

    Dim r As Long
    For r = startRow To endRow
        If NzStr(cdWs.Cells(r, CD_COL_TYPE).Value) = STOP_BLANK_TYPE_MARKER Then
            cdWs.Cells(r, CD_COL_TYPE).Value = ""
            cdWs.Cells(r, CD_COL_CONT_ON).Value = ""
        End If
    Next r
End Sub

'----------------------------------------
' notify用キー生成
'----------------------------------------
Private Function BuildItemDevStepKey(ByVal itemKey As String, ByVal devIndex As Long, ByVal stepId As Long) As String
    BuildItemDevStepKey = CStr(itemKey) & ChrW(&H1F) & CStr(devIndex) & ChrW(&H1F) & CStr(stepId)
End Function

Private Function WriteNotifyRow(ByVal cdWs As Worksheet, ByVal outRow As Long, ByVal devDict As Object, ByVal msg As String) As Long
    Dim c As Long
    For c = 1 To MAX_DEVICE_COL
        cdWs.Cells(outRow, c).Value = DEFAULT_NEED
    Next c

    If Not devDict Is Nothing Then
        Dim dk As Variant
        For Each dk In devDict.keys
            cdWs.Cells(outRow, CLng(dk)).Value = "R"
        Next dk
    End If

    cdWs.Cells(outRow, CD_COL_TYPE).Value = "notify"
    cdWs.Cells(outRow, CD_COL_CONT_ON).Value = ""
    cdWs.Cells(outRow, CD_COL_REG).Value = ""
    cdWs.Cells(outRow, CD_COL_PROMPT).Value = ""
    cdWs.Cells(outRow, CD_COL_COMMAND).Value = msg

    WriteNotifyRow = outRow + 1
End Function

'========================
' 既存処理（必要最小限）
'========================
Private Function IsPerDeviceMode(ByVal stepOrder As Collection, ByVal stepDevSig As Object, ByVal activeDevs As Object) As Boolean
    IsPerDeviceMode = False

    Dim k As Long
    For k = 1 To stepOrder.Count
        Dim stepId As Long: stepId = CLng(stepOrder(k))
        Dim uniq As Object: Set uniq = CreateObject("Scripting.Dictionary")

        Dim devKey As Variant
        For Each devKey In activeDevs.keys
            Dim d As String: d = CStr(devKey)
            Dim sig As String: sig = NONE_SIG

            If stepDevSig.Exists(CStr(stepId)) Then
                Dim devMap As Object: Set devMap = stepDevSig(CStr(stepId))
                If devMap.Exists(d) Then sig = CStr(devMap(d))
            End If

            If Not uniq.Exists(sig) Then uniq.Add sig, True
            If uniq.Count > 1 Then
                IsPerDeviceMode = True
                Exit Function
            End If
        Next devKey
    Next k
End Function

Private Function WriteGroupedDeviceBlocks(ByVal cdWs As Worksheet, ByVal outRow As Long, ByVal itemKey As String, ByVal stepOrder As Collection, ByVal stepDevSig As Object, ByVal activeDevs As Object, ByVal notifyStepDict As Object) As Long
    Dim groups As Object: Set groups = CreateObject("Scripting.Dictionary")

    Dim dev As Long
    For dev = 1 To MAX_DEVICE_COL
        If activeDevs.Exists(CStr(dev)) Then
            Dim gKey As String
            gKey = BuildDeviceSequenceKey(stepOrder, stepDevSig, dev)

            Dim col As Collection
            If groups.Exists(gKey) Then
                Set col = groups(gKey)
            Else
                Set col = New Collection
                groups.Add gKey, col
            End If
            col.Add dev
        End If
    Next dev

    Dim orderedKeys() As String
    orderedKeys = SortGroupKeysByMinDev(groups)

    Dim idx As Long
    For idx = LBound(orderedKeys) To UBound(orderedKeys)
        Dim key As String: key = orderedKeys(idx)
        Dim devs As Collection: Set devs = groups(key)
        outRow = WriteDeviceGroupSteps(cdWs, outRow, itemKey, stepOrder, stepDevSig, devs, notifyStepDict)
    Next idx

    WriteGroupedDeviceBlocks = outRow
End Function

Private Function BuildDeviceSequenceKey(ByVal stepOrder As Collection, ByVal stepDevSig As Object, ByVal devIndex As Long) As String
    Dim sb As String: sb = ""
    Dim k As Long
    For k = 1 To stepOrder.Count
        Dim stepId As Long: stepId = CLng(stepOrder(k))
        Dim sig As String: sig = NONE_SIG
        If stepDevSig.Exists(CStr(stepId)) Then
            Dim devMap As Object: Set devMap = stepDevSig(CStr(stepId))
            If devMap.Exists(CStr(devIndex)) Then sig = CStr(devMap(CStr(devIndex)))
        End If
        sb = sb & sig & ChrW(&H1E)
    Next k
    BuildDeviceSequenceKey = sb
End Function

Private Function SortGroupKeysByMinDev(ByVal groups As Object) As String()
    Dim keys() As String
    Dim n As Long: n = groups.Count
    ReDim keys(0 To n - 1)

    Dim i As Long: i = 0
    Dim k As Variant
    For Each k In groups.keys
        keys(i) = CStr(k)
        i = i + 1
    Next k

    Dim a As Long, b As Long
    For a = 0 To n - 2
        For b = a + 1 To n - 1
            If GetMinDev(groups(keys(a))) > GetMinDev(groups(keys(b))) Then
                Dim tmp As String
                tmp = keys(a): keys(a) = keys(b): keys(b) = tmp
            End If
        Next b
    Next a

    SortGroupKeysByMinDev = keys
End Function

Private Function GetMinDev(ByVal devs As Collection) As Long
    Dim m As Long: m = 9999
    Dim i As Long
    For i = 1 To devs.Count
        If CLng(devs(i)) < m Then m = CLng(devs(i))
    Next i
    GetMinDev = m
End Function

Private Function WriteDeviceGroupSteps(ByVal cdWs As Worksheet, ByVal outRow As Long, ByVal itemKey As String, ByVal stepOrder As Collection, ByVal stepDevSig As Object, ByVal devs As Collection, ByVal notifyStepDict As Object) As Long
    Dim repDev As Long: repDev = CLng(devs(1))

    Dim lastExecPromptOut As String: lastExecPromptOut = ""
    Dim lastNeedArr As Variant: lastNeedArr = Empty

    Dim k As Long
    For k = 1 To stepOrder.Count
        Dim stepId As Long: stepId = CLng(stepOrder(k))

        If stepDevSig.Exists(CStr(stepId)) Then
            Dim devMap As Object: Set devMap = stepDevSig(CStr(stepId))
            If devMap.Exists(CStr(repDev)) Then
                Dim sig As String: sig = CStr(devMap(CStr(repDev)))
                If sig <> NONE_SIG Then
                    Dim cmdText As String, outType As String, outReg As String, outPrompt As String, outContOn As String
                    Call SplitSignature(sig, cmdText, outType, outReg, outPrompt, outContOn)

                    If IsExecPromptOut(outPrompt) Then lastExecPromptOut = outPrompt

                    Dim c As Long
                    For c = 1 To MAX_DEVICE_COL
                        cdWs.Cells(outRow, c).Value = DEFAULT_NEED
                    Next c

                    Dim ii As Long
                    For ii = 1 To devs.Count
                        cdWs.Cells(outRow, CLng(devs(ii))).Value = "R"
                    Next ii

                    lastNeedArr = ReadNeedArrayFromSheet(cdWs, outRow)

                    cdWs.Cells(outRow, CD_COL_TYPE).Value = outType
                    cdWs.Cells(outRow, CD_COL_CONT_ON).Value = outContOn
                    cdWs.Cells(outRow, CD_COL_REG).Value = outReg
                    cdWs.Cells(outRow, CD_COL_PROMPT).Value = outPrompt
                    cdWs.Cells(outRow, CD_COL_COMMAND).Value = cmdText
                    outRow = outRow + 1

                    ' notify挿入（後）
                    Dim hasNotify As Boolean: hasNotify = False
                    Dim iiN As Long
                    For iiN = 1 To devs.Count
                        If notifyStepDict.Exists(BuildItemDevStepKey(itemKey, CLng(devs(iiN)), stepId)) Then
                            hasNotify = True
                            Exit For
                        End If
                    Next iiN

                    If hasNotify Then
                        Dim devDictN As Object
                        Set devDictN = CreateObject("Scripting.Dictionary")
                        For iiN = 1 To devs.Count
                            If notifyStepDict.Exists(BuildItemDevStepKey(itemKey, CLng(devs(iiN)), stepId)) Then
                                devDictN.Add CStr(devs(iiN)), True
                            End If
                        Next iiN
                        outRow = WriteNotifyRow(cdWs, outRow, devDictN, "作業CSに則り実施")
                    End If
                End If
            End If
        End If
    Next k

    If Len(Trim$(lastExecPromptOut)) > 0 Then
        If IsEmpty(lastNeedArr) Then lastNeedArr = InitNeedArray()
        outRow = WritePromptOnlyRow(cdWs, outRow, lastExecPromptOut, lastNeedArr)
    End If

    WriteDeviceGroupSteps = outRow
End Function

Private Function WriteAggregatedSteps(ByVal cdWs As Worksheet, ByVal outRow As Long, ByVal itemKey As String, ByVal stepOrder As Collection, ByVal stepDevSig As Object, ByVal notifyStepDict As Object) As Long
    Dim rowData As Object: Set rowData = CreateObject("Scripting.Dictionary")
    Dim rowOrder As Collection: Set rowOrder = New Collection

    Dim k As Long
    For k = 1 To stepOrder.Count
        Dim stepId As Long: stepId = CLng(stepOrder(k))

        If stepDevSig.Exists(CStr(stepId)) Then
            Dim devMap As Object: Set devMap = stepDevSig(CStr(stepId))

            Dim devKey As Variant
            For Each devKey In devMap.keys
                Dim devIndex As Long: devIndex = CLng(devKey)
                Dim sig As String: sig = CStr(devMap(devKey))

                Dim cmdText As String, outType As String, outReg As String, outPrompt As String, outContOn As String
                Call SplitSignature(sig, cmdText, outType, outReg, outPrompt, outContOn)

                Dim rowKey As String
                rowKey = itemKey & SEP & CStr(stepId) & SEP & cmdText & SEP & outType & SEP & outReg & SEP & outPrompt & SEP & outContOn

                Dim rd As Object
                If rowData.Exists(rowKey) Then
                    Set rd = rowData(rowKey)
                Else
                    Set rd = CreateObject("Scripting.Dictionary")
                    rd.Add "need", InitNeedArray()
                    rd.Add "type", outType
                    rd.Add "reg", outReg
                    rd.Add "promptOut", outPrompt
                    rd.Add "command", cmdText
                    rd.Add "contOn", outContOn
                    rowData.Add rowKey, rd
                    rowOrder.Add rowKey
                End If

                Dim needArr As Variant
                needArr = rd("need")
                needArr(devIndex) = "R"
                rd("need") = needArr
            Next devKey

            ' notify挿入（集約後）
            If Not notifyStepDict Is Nothing Then
                Dim devDictN As Object
                Set devDictN = CreateObject("Scripting.Dictionary")

                Dim devKeyN As Variant
                For Each devKeyN In devMap.keys
                    Dim dIndex As Long: dIndex = CLng(devKeyN)
                    If notifyStepDict.Exists(BuildItemDevStepKey(itemKey, dIndex, stepId)) Then
                        devDictN(CStr(dIndex)) = True
                    End If
                Next devKeyN

                If devDictN.Count > 0 Then
                    Dim notifyRowKey As String
                    notifyRowKey = itemKey & SEP & CStr(stepId) & SEP & "<NOTIFY>"

                    Dim rdN As Object
                    Set rdN = CreateObject("Scripting.Dictionary")
                    rdN.Add "need", InitNeedArray()

                    Dim aNeed As Variant
                    aNeed = rdN("need")

                    Dim kkk As Variant
                    For Each kkk In devDictN.keys
                        aNeed(CLng(kkk)) = "R"
                    Next kkk
                    rdN("need") = aNeed

                    rdN.Add "type", "notify"
                    rdN.Add "reg", ""
                    rdN.Add "promptOut", ""
                    rdN.Add "command", "作業CSに則り実施"
                    rdN.Add "contOn", ""

                    rowData.Add notifyRowKey, rdN
                    rowOrder.Add notifyRowKey
                End If
            End If
        End If
    Next k

    Dim j As Long
    For j = 1 To rowOrder.Count
        Dim rk As String: rk = CStr(rowOrder(j))
        Dim rd2 As Object: Set rd2 = rowData(rk)
        Dim needArr2 As Variant: needArr2 = rd2("need")

        Dim c As Long
        For c = 1 To MAX_DEVICE_COL
            cdWs.Cells(outRow, c).Value = needArr2(c)
        Next c

        cdWs.Cells(outRow, CD_COL_TYPE).Value = rd2("type")
        cdWs.Cells(outRow, CD_COL_CONT_ON).Value = rd2("contOn")
        cdWs.Cells(outRow, CD_COL_REG).Value = rd2("reg")
        cdWs.Cells(outRow, CD_COL_PROMPT).Value = rd2("promptOut")
        cdWs.Cells(outRow, CD_COL_COMMAND).Value = rd2("command")

        outRow = outRow + 1
    Next j

    WriteAggregatedSteps = outRow
End Function

Private Sub ForcePrevStepContOff(ByVal stepOrder As Collection, ByVal stepDevSig As Object, ByVal devIndex As Long, ByVal currentStepId As Long)
    Dim i As Long
    For i = stepOrder.Count To 1 Step -1
        Dim sid As Long: sid = CLng(stepOrder(i))
        If sid < currentStepId Then
            If stepDevSig.Exists(CStr(sid)) Then
                Dim devMap As Object: Set devMap = stepDevSig(CStr(sid))
                If devMap.Exists(CStr(devIndex)) Then
                    Dim sig As String: sig = CStr(devMap(CStr(devIndex)))
                    Dim cmdText As String, outType As String, outReg As String, outPrompt As String, outContOn As String
                    Call SplitSignature(sig, cmdText, outType, outReg, outPrompt, outContOn)
                    If Len(outContOn) > 0 Then
                        ' 2026-05-12: STOP直前がチェック系行の場合、その行のcont.onは保持する
                        If IsCheckLikeCdRow(outType, outPrompt) Then Exit Sub

                        outContOn = ""
                        devMap(CStr(devIndex)) = BuildSignature(cmdText, outType, outReg, outPrompt, outContOn)
                    End If
                    Exit Sub
                End If
            End If
        End If
    Next i
End Sub

Private Sub ForcePrevStepTypeCkOut(ByVal stepDevSig As Object, ByVal prevStepId As Long, ByVal devIndex As Long)
    Dim sid As String: sid = CStr(prevStepId)
    If Not stepDevSig.Exists(sid) Then Exit Sub

    Dim devMap As Object: Set devMap = stepDevSig(sid)
    Dim did As String: did = CStr(devIndex)
    If Not devMap.Exists(did) Then Exit Sub

    Dim sig As String: sig = CStr(devMap(did))
    Dim cmdText As String, outType As String, outReg As String, outPrompt As String, outContOn As String
    Call SplitSignature(sig, cmdText, outType, outReg, outPrompt, outContOn)

    outType = "ckOut"
    devMap(did) = BuildSignature(cmdText, outType, outReg, outPrompt, outContOn)
End Sub

Private Sub EnsureStepInOrder(ByVal col As Collection, ByVal stepId As Long)
    Dim i As Long
    For i = 1 To col.Count
        If CLng(col(i)) = stepId Then Exit Sub
    Next i
    col.Add stepId
End Sub

Private Sub PutStepSig(ByVal stepDevSig As Object, ByVal stepId As Long, ByVal devIndex As Long, ByVal sig As String)
    Dim sid As String: sid = CStr(stepId)
    Dim devMap As Object
    If stepDevSig.Exists(sid) Then
        Set devMap = stepDevSig(sid)
    Else
        Set devMap = CreateObject("Scripting.Dictionary")
        stepDevSig.Add sid, devMap
    End If
    devMap(CStr(devIndex)) = sig
End Sub

Private Function InitNeedArray() As Variant
    Dim a(1 To MAX_DEVICE_COL) As String
    Dim i As Long
    For i = 1 To MAX_DEVICE_COL
        a(i) = DEFAULT_NEED
    Next i
    InitNeedArray = a
End Function

Private Function ReadNeedArrayFromSheet(ByVal cdWs As Worksheet, ByVal rowNo As Long) As Variant
    Dim a(1 To MAX_DEVICE_COL) As String
    Dim c As Long
    For c = 1 To MAX_DEVICE_COL
        a(c) = NzStr(cdWs.Cells(rowNo, c).Value)
    Next c
    ReadNeedArrayFromSheet = a
End Function

Private Function WritePromptOnlyRow(ByVal cdWs As Worksheet, ByVal outRow As Long, ByVal promptText As String, ByVal needArr As Variant) As Long
    Dim c As Long
    For c = 1 To MAX_DEVICE_COL
        cdWs.Cells(outRow, c).Value = needArr(c)
    Next c
    cdWs.Cells(outRow, CD_COL_TYPE).Value = ""
    cdWs.Cells(outRow, CD_COL_CONT_ON).Value = ""
    cdWs.Cells(outRow, CD_COL_REG).Value = ""
    cdWs.Cells(outRow, CD_COL_PROMPT).Value = promptText
    cdWs.Cells(outRow, CD_COL_COMMAND).Value = ""
    WritePromptOnlyRow = outRow + 1
End Function

Private Function FindLastExecPromptInRange(ByVal cdWs As Worksheet, ByVal startRow As Long, ByVal endRow As Long) As String
    FindLastExecPromptInRange = ""
    If endRow < startRow Then Exit Function

    Dim r As Long
    For r = endRow To startRow Step -1
        Dim p As String
        p = NzStr(cdWs.Cells(r, CD_COL_PROMPT).Value)
        If IsExecPromptOut(p) Then
            FindLastExecPromptInRange = p
            Exit Function
        End If
    Next r
End Function

Private Function IsStopToken(ByVal v As Variant) As Boolean
    Dim s As String
    s = NzStr(v)
    If Len(s) = 0 Then
        IsStopToken = False
        Exit Function
    End If
    s = StrConv(s, vbNarrow)
    s = UCase$(Trim$(s))
    IsStopToken = (s = "STOP")
End Function

'========================================================
' ★②判定：同一項番内（辞書定義済みPromptKeyのみ対象）のNeedRuleが
' {RULE_ALWAYS_T, RULE_CMD_NONEMPTY} のみで構成されるか
'========================================================
Private Function BuildItemFlag_OnlyAlwaysT_AndCmdNonEmpty( _
    ByVal csWs As Worksheet, _
    ByVal promptRules As Object, _
    ByVal blockStarts As Collection, _
    ByVal headerRow As Long, _
    ByVal dataStartRow As Long, _
    ByVal lastRow As Long) As Object

    Dim maskByItem As Object
    Set maskByItem = CreateObject("Scripting.Dictionary")
    ' mask: bit1=hasAny(AT or CMD), bit2=hasOther

    Dim currentItemKey As String: currentItemKey = ""

    Dim r As Long
    For r = dataStartRow To lastRow

        ' 項番継承ロジックを本処理に合わせる（部分入力は無視）
        Dim aStr As String, bStr As String, cVal As String
        aStr = NzStr(csWs.Cells(r, COL_ITEM_A).Value)
        bStr = NzStr(csWs.Cells(r, COL_ITEM_B).Value)
        cVal = NzStr(csWs.Cells(r, COL_ITEM_C).Value)

        Dim rawItemKey As String
        rawItemKey = BuildItemKey(aStr, bStr, cVal)

        If Len(rawItemKey) > 0 Then
            currentItemKey = rawItemKey
        Else
            Dim hasAnyPart As Boolean
            hasAnyPart = (Len(aStr) > 0 Or Len(bStr) > 0 Or Len(cVal) > 0)
            If hasAnyPart Then GoTo NextR
            If Len(currentItemKey) = 0 Then GoTo NextR
        End If

        Dim itemKey As String: itemKey = currentItemKey
        If Len(itemKey) = 0 Then GoTo NextR

        ' 装置ブロック走査
        Dim bi As Long
        For bi = 1 To blockStarts.Count
            Dim startCol As Long, nextCol As Long
            startCol = CLng(blockStarts(bi))
            If bi < blockStarts.Count Then
                nextCol = CLng(blockStarts(bi + 1))
            Else
                nextCol = 0
            End If

            Dim cols As TBlockCols
            cols = Mod_Mapping.DetectBlockCols(csWs, startCol, nextCol, headerRow)
            If cols.promptCol = 0 Then GoTo NextBlock

            Dim promptKey As String
            promptKey = Mod_PromptRules.ResolvePromptKey(csWs.Cells(r, cols.promptCol))
            If Len(promptKey) = 0 Then GoTo NextBlock

            ' TTなど特例が出たら②対象外
            If UCase$(Trim$(promptKey)) = "TT" Then
                Call MarkItemMask(maskByItem, itemKey, False, True)
                GoTo NextBlock
            End If

            ' 未定義は②判定に含めない
            If Not promptRules.Exists(promptKey) Then GoTo NextBlock

            Dim rule As PromptRule
            Set rule = promptRules(promptKey)
            If rule Is Nothing Then GoTo NextBlock

            Dim rid As String
            rid = UCase$(Trim$(rule.NeedRule))
            If Len(rid) = 0 Then rid = UCase$(RULE_ALWAYS_T)

            If rid = UCase$(RULE_ALWAYS_T) Or rid = UCase$(RULE_CMD_NONEMPTY) Then
                Call MarkItemMask(maskByItem, itemKey, True, False)
            Else
                Call MarkItemMask(maskByItem, itemKey, False, True)
            End If

NextBlock:
        Next bi

NextR:
    Next r

    ' mask -> boolean（hasAny かつ hasOtherなし）
    Dim ret As Object
    Set ret = CreateObject("Scripting.Dictionary")

    Dim k As Variant
    For Each k In maskByItem.keys
        Dim m As Long: m = CLng(maskByItem(k))
        Dim hasAny As Boolean: hasAny = ((m And 1) <> 0)
        Dim hasOther As Boolean: hasOther = ((m And 2) <> 0)
        ret(CStr(k)) = (hasAny And (Not hasOther))
    Next k

    Set BuildItemFlag_OnlyAlwaysT_AndCmdNonEmpty = ret
End Function

' mask helper: bit1/bit2を立てる
Private Sub MarkItemMask(ByVal maskByItem As Object, ByVal itemKey As String, _
                         ByVal setAny As Boolean, ByVal setOther As Boolean)
    Dim m As Long
    If maskByItem.Exists(itemKey) Then
        m = CLng(maskByItem(itemKey))
    Else
        m = 0
    End If
    If setAny Then m = (m Or 1)
    If setOther Then m = (m Or 2)
    maskByItem(itemKey) = m
End Sub

