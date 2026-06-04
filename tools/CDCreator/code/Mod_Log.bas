Attribute VB_Name = "Mod_Log"
Option Explicit

'========================================
' モジュール名 : Mod_Log
' 目的         : 統一ログ出力（Logシート）
' 依存         : Mod_Common
'========================================

Public Sub logInfo(ByVal message As String, ByVal context As String)
    Call writeLog(Info, message, context)
End Sub

Public Sub logWarn(ByVal message As String, ByVal context As String)
    Call writeLog(Warn, message, context)
End Sub

Public Sub logError(ByVal message As String, ByVal context As String)
    Call writeLog([Error], message, context)
End Sub

Private Sub writeLog(ByVal level As eLogLevel, ByVal message As String, ByVal context As String)
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets(SHEET_LOG)

    Dim nextRow As Long
    nextRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1

    ws.Cells(nextRow, 1).Value = Now
    ws.Cells(nextRow, 2).Value = IIf(level = Info, "INFO", IIf(level = Warn, "WARN", "ERROR"))
    ws.Cells(nextRow, 3).Value = message
    ws.Cells(nextRow, 4).Value = context
End Sub


