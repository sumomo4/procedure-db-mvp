Attribute VB_Name = "Mod_PromptRules"
Option Explicit

'========================================
' モジュール名 : Mod_PromptRules
' 目的 : 「プロンプト」シートA1開始の変換表を読み込み、辞書化する
' 依存 : Mod_Common, Mod_Log, Mod_Validate, PromptRule
'
' 2026-02-19
' - Priority / ContOn 列は使用しない（列があっても無視）
' - 同一 PromptKey が複数行存在した場合は ERROR として停止（事故防止）
' - 全角(英数・記号・スペース)は半角に正規化（カナは変換しない）
'========================================

' 変換表ヘッダ（A1開始）
Private Const H_PROMPTKEY As String = "PromptKey"
Private Const H_CDTYPE As String = "CdType"
Private Const H_CDREG As String = "CdReg"
Private Const H_CDPROMPTOUT As String = "CdPromptOut"
Private Const H_NEEDRULE As String = "NeedRule"
Private Const H_COMMANDREQ As String = "CommandRequired"
' ※廃止（列があっても無視）
Private Const H_PRIORITY As String = "Priority"
Private Const H_CONTON As String = "ContOn"

'----------------------------------------
' 変換表読み込み
' 戻り値：Dictionary(PromptKey) -> PromptRule
' 仕様：同一PromptKeyが複数行存在したら ERROR で停止
'----------------------------------------
Public Function LoadPromptRules(ByVal promptWs As Worksheet) As Object
    Dim dict As Object
    Set dict = CreateObject("Scripting.Dictionary")

    Dim lastRow As Long
    lastRow = GetLastUsedRow(promptWs)
    If lastRow < 2 Then
        Set LoadPromptRules = dict
        Exit Function
    End If

    Dim colPromptKey As Long, colCdType As Long, colCdReg As Long, colCdPromptOut As Long
    Dim colNeedRule As Long, colCommandReq As Long

    colPromptKey = FindHeaderCol(promptWs, 1, H_PROMPTKEY)
    colCdType = FindHeaderCol(promptWs, 1, H_CDTYPE)
    colCdReg = FindHeaderCol(promptWs, 1, H_CDREG)
    colCdPromptOut = FindHeaderCol(promptWs, 1, H_CDPROMPTOUT)
    colNeedRule = FindHeaderCol(promptWs, 1, H_NEEDRULE)
    colCommandReq = FindHeaderCol(promptWs, 1, H_COMMANDREQ)

    If colPromptKey = 0 Then
        Call Mod_Log.logError("プロンプト変換表に PromptKey ヘッダがありません", "sheet=" & promptWs.Name)
        Set LoadPromptRules = dict
        Exit Function
    End If

    Dim r As Long
    For r = 2 To lastRow
        Dim key As String
        key = NormalizePromptKey(NzStr(promptWs.Cells(r, colPromptKey).Value))
        If Len(key) = 0 Then GoTo NextR

        ' ★重複は事故要因のため、ERRORで停止
        If dict.Exists(key) Then
            Dim msg As String
            msg = "プロンプト変換表に同一PromptKeyが複数行あります（禁止）: " & key & " / row=" & r
            Call Mod_Log.logError(msg, "sheet=" & promptWs.Name)
            Err.Raise vbObjectError + 513, "LoadPromptRules", msg
        End If

        Dim rule As PromptRule
        Set rule = New PromptRule
        rule.promptKey = key

        If colCdType > 0 Then rule.CdType = NzStr(promptWs.Cells(r, colCdType).Value)
        If colCdReg > 0 Then rule.CdReg = NzStr(promptWs.Cells(r, colCdReg).Value)
        If colCdPromptOut > 0 Then rule.CdPromptOut = ToHalfWidthAscii(NzStr(promptWs.Cells(r, colCdPromptOut).Value))

        If colNeedRule > 0 Then rule.NeedRule = NzStr(promptWs.Cells(r, colNeedRule).Value)
        If Len(Trim$(rule.NeedRule)) = 0 Then rule.NeedRule = RULE_ALWAYS_T

        If colCommandReq > 0 Then
            rule.CommandRequired = ToBool(promptWs.Cells(r, colCommandReq).Value)
        Else
            rule.CommandRequired = False
        End If

        ' Priority / ContOn は廃止（列があっても無視）
        ' rule.Priority / rule.ContOn は使用しない

        dict.Add key, rule

NextR:
    Next r

    Set LoadPromptRules = dict
End Function

'----------------------------------------
' promptKey決定（CSセル値を正規化して返す）
'----------------------------------------
Public Function ResolvePromptKey(ByVal promptCell As Range) As String
    ResolvePromptKey = NormalizePromptKey(NzStr(promptCell.Value))
End Function

'----------------------------------------
' NeedRule評価
' 戻り値 True=R付与 / False=T
'----------------------------------------
Public Function EvalNeedRule(ByVal ruleId As String, ByVal promptKey As String, ByVal commandText As String) As Boolean
    Dim id As String
    id = UCase$(Trim$(ruleId))

    Select Case id
        Case UCase$(RULE_ALWAYS_T)
            EvalNeedRule = False
        Case UCase$(RULE_PROMPT_SYM_AND_CMD)
            ' 表駆動：このNeedRuleが割り当てられているPromptKeyであれば
            ' 記号種別は問わず「command非空 => R / 空 => T」
            EvalNeedRule = IsCommandNonEmpty(commandText)
        Case UCase$(RULE_CMD_NONEMPTY)
            EvalNeedRule = IsCommandNonEmpty(commandText)
        Case Else
            ' 未定義は安全側でT
            EvalNeedRule = False
    End Select
End Function

'----------------------------------------
' PromptKey正規化
' - 全角→半角（英数・記号・スペース）
' - 一部記号の互換表現（＞→\>、＃→\# など）
'----------------------------------------
Public Function NormalizePromptKey(ByVal s As String) As String
    Dim t As String
    t = Trim$(CStr(s))

    ' 互換：全角記号を既存の内部表現へ
    t = Replace(t, "＞", "\>")
    t = Replace(t, "％", "%")
    t = Replace(t, "：", ":")
    t = Replace(t, "＃", "\#")
    t = Replace(t, "＄", "$")

    ' \> の過剰エスケープを補正
    If t = "\\\>" Then t = "\>"

    ' ★全角(ASCII/記号/スペース)→半角（カナは変換しない）
    t = ToHalfWidthAscii(t)

    NormalizePromptKey = t
End Function

'----------------------------------------
' 全角(ASCII/記号/スペース)→半角（カナは変換しない）
' - U+3000(全角スペース)→半角スペース
' - U+FF01～U+FF5E(全角ASCII)→U+0021～U+007E
' - U+FFE5(全角￥)→\
'----------------------------------------
Private Function ToHalfWidthAscii(ByVal s As String) As String
    Dim i As Long
    Dim ch As String
    Dim code As Long
    Dim out As String
    out = ""

    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)
        code = AscW(ch)

        If code = &H3000 Then
            out = out & " "
        ElseIf code >= &HFF01 And code <= &HFF5E Then
            out = out & ChrW(code - &HFEE0)
        ElseIf code = &HFFE5 Then
            out = out & "\"
        Else
            out = out & ch
        End If
    Next i

    ToHalfWidthAscii = out
End Function

'========================================
' internal helpers
'========================================
Private Function FindHeaderCol(ByVal ws As Worksheet, ByVal headerRow As Long, ByVal headerName As String) As Long
    Dim lastCol As Long
    lastCol = GetLastUsedCol(ws, headerRow)

    Dim c As Long
    For c = 1 To lastCol
        If NzStr(ws.Cells(headerRow, c).Value) = headerName Then
            FindHeaderCol = c
            Exit Function
        End If
    Next c
    FindHeaderCol = 0
End Function

Private Function ToBool(ByVal v As Variant) As Boolean
    Dim s As String
    s = UCase$(Trim$(CStr(v)))
    ToBool = (s = "TRUE" Or s = "1" Or s = "YES" Or s = "Y")
End Function

