Attribute VB_Name = "Mod_Common"
Option Explicit

'========================================
' モジュール名 : Mod_Common
' 目的         : 共通定数・型定義・ユーティリティ
' 更新         : v0.4.3（新仕様：項番・4列ブロック・辞書駆動・全T行除外）
'========================================

'--- シート名
Public Const SHEET_CS As String = "CS"
Public Const SHEET_CD As String = "command"
Public Const SHEET_LOG As String = "Log"
Public Const SHEET_PROMPT As String = "プロンプト"

'--- CSヘッダ（1行目）
Public Const HDR_TIME As String = "時刻"
Public Const HDR_WINDOW As String = "window"
Public Const HDR_PROMPT As String = "P"
Public Const HDR_COMMAND As String = "コマンド"

'--- 項番列（CS）
Public Const COL_ITEM_A As Long = 1 'A:大項目
Public Const COL_ITEM_B As Long = 2 'B:中項目
Public Const COL_ITEM_C As Long = 3 'C:小項目

'--- CD列
Public Const MAX_DEVICE_COL As Long = 20 'A～T
Public Const DEFAULT_NEED As String = "T"

'属性列（固定） V/W/Y/Z/AA
Public Const CD_COL_TYPE As Long = 22     'V
Public Const CD_COL_CONT_ON As Long = 23  'W
Public Const CD_COL_REG As Long = 25      'Y
Public Const CD_COL_PROMPT As Long = 26   'Z
Public Const CD_COL_COMMAND As Long = 27  'AA

'--- NeedRule ID
Public Const RULE_ALWAYS_T As String = "RULE_ALWAYS_T"
Public Const RULE_PROMPT_SYM_AND_CMD As String = "RULE_PROMPT_SYM_AND_CMD"
Public Const RULE_CMD_NONEMPTY As String = "RULE_CMD_NONEMPTY" '将来用

'--- ログレベル
Public Enum eLogLevel
    Info = 0
    Warn = 1
    [Error] = 2
End Enum

'--- ブロック列（検出結果）
Public Type TBlockCols
    timeCol As Long
    windowCol As Long
    promptCol As Long
    commandCol As Long
End Type

'========================================
' ユーティリティ
'========================================

Public Function BuildItemKey(ByVal aVal As Variant, ByVal bVal As Variant, ByVal cVal As Variant) As String
    Dim a As String, b As String, c As String
    a = Trim$(CStr(aVal))
    b = Trim$(CStr(bVal))
    c = Trim$(CStr(cVal))
    If Len(a) = 0 Or Len(b) = 0 Or Len(c) = 0 Then
        BuildItemKey = "" '暫定：空欄行はスキップ
    Else
        BuildItemKey = a & "-" & b & "-" & c
    End If
End Function

Public Function NzStr(ByVal v As Variant) As String
    If IsError(v) Then
        NzStr = ""
    Else
        NzStr = Trim$(CStr(v))
    End If
End Function

Public Function GetLastUsedRow(ByVal ws As Worksheet) As Long
    If Application.WorksheetFunction.CountA(ws.Cells) = 0 Then
        GetLastUsedRow = 0
    Else
        GetLastUsedRow = ws.Cells.Find(What:="*", After:=ws.Cells(1, 1), LookIn:=xlFormulas, _
            LookAt:=xlPart, SearchOrder:=xlByRows, SearchDirection:=xlPrevious).Row
    End If
End Function

Public Function GetLastUsedCol(ByVal ws As Worksheet, Optional ByVal rowNo As Long = 1) As Long
    GetLastUsedCol = ws.Cells(rowNo, ws.Columns.Count).End(xlToLeft).Column
End Function


