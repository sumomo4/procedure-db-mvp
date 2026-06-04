Attribute VB_Name = "Mod_Mapping"

Option Explicit

'========================================
' モジュール名 : Mod_Mapping
' 目的         : CSの装置ブロック検出（ヘッダ駆動）
' 修正         : ヘッダ行を自動検出（複数段ヘッダ対応）
' 依存         : Mod_Common
'========================================

'--- ヘッダ行を自動検出（上からmaxScanRow行まで）
' 条件：同一行に「時刻」「window」「P」「コマンド」が少なくとも1つずつ存在
Public Function FindHeaderRow(ByVal csWs As Worksheet, Optional ByVal maxScanRow As Long = 10) As Long

    Dim lastCol As Long
    lastCol = GetLastUsedCol(csWs, 1)

    Dim r As Long
    For r = 1 To maxScanRow

        Dim hasTime As Boolean
        Dim hasWin As Boolean
        Dim hasP As Boolean
        Dim hasCmd As Boolean

        hasTime = False
        hasWin = False
        hasP = False
        hasCmd = False

        Dim c As Long
        For c = 1 To lastCol
            Dim h As String
            h = NzStr(csWs.Cells(r, c).Value)

            If h = HDR_TIME Then hasTime = True
            If h = HDR_WINDOW Then hasWin = True
            If h = HDR_PROMPT Then hasP = True
            If h = HDR_COMMAND Then hasCmd = True

            If hasTime And hasWin And hasP And hasCmd Then
                FindHeaderRow = r
                Exit Function
            End If
        Next c

    Next r

    FindHeaderRow = 0
End Function

'--- ヘッダ行で「時刻」ヘッダの列を全取得（ブロック開始列）
Public Function GetDeviceBlockStartCols(ByVal csWs As Worksheet, ByVal headerRow As Long) As Collection
    Dim starts As New Collection

    Dim lastCol As Long
    lastCol = GetLastUsedCol(csWs, headerRow)

    Dim c As Long
    For c = 1 To lastCol
        If NzStr(csWs.Cells(headerRow, c).Value) = HDR_TIME Then
            starts.Add c
        End If
    Next c

    Set GetDeviceBlockStartCols = starts
End Function

'--- startCol～nextStartCol-1 の範囲で window/P/コマンド の列を探す
Public Function DetectBlockCols(ByVal csWs As Worksheet, ByVal startCol As Long, ByVal nextStartCol As Long, ByVal headerRow As Long) As TBlockCols
    Dim cols As TBlockCols
    cols.timeCol = startCol
    cols.windowCol = 0
    cols.promptCol = 0
    cols.commandCol = 0

    Dim endCol As Long
    If nextStartCol > 0 Then
        endCol = nextStartCol - 1
    Else
        endCol = GetLastUsedCol(csWs, headerRow)
    End If

    Dim c As Long
    For c = startCol To endCol
        Dim h As String
        h = NzStr(csWs.Cells(headerRow, c).Value)

        Select Case h
            Case HDR_WINDOW: cols.windowCol = c
            Case HDR_PROMPT: cols.promptCol = c
            Case HDR_COMMAND: cols.commandCol = c
        End Select
    Next c

    DetectBlockCols = cols
End Function


