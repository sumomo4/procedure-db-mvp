Attribute VB_Name = "Numbering_Tool"
Option Explicit

'==============================================================================
' Module:      Numbering_Tool
' Purpose:     ボタンから実行する公開マクロ（アクティブシートのみ採番）
' Dependencies:
'   - M_Config
'   - Numbering_Logic
' Notes:
'   - 公開プロシージャは標準化したエラーハンドラを持つ[1](https://westnttcojp-my.sharepoint.com/personal/isamu_chiba_eu_west_ntt_co_jp/Documents/Microsoft%20Copilot%20Chat%20%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB/%E3%82%B3%E3%83%BC%E3%83%87%E3%82%A3%E3%83%B3%E3%82%B0%E8%A6%8F%E7%B4%84.txt)
'   - Application状態（ScreenUpdating等）は必ず finally 的に復旧する[1](https://westnttcojp-my.sharepoint.com/personal/isamu_chiba_eu_west_ntt_co_jp/Documents/Microsoft%20Copilot%20Chat%20%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB/%E3%82%B3%E3%83%BC%E3%83%87%E3%82%A3%E3%83%B3%E3%82%B0%E8%A6%8F%E7%B4%84.txt)
' History:
'   2026-02-16  Initial
'==============================================================================

'------------------------------------------------------------------------------
' Public Sub:   AssignNumbersOnActiveSheet
' Purpose:      アクティブシートに対して採番を実行する（要件：アクティブのみ）
' Arguments:    None
' Returns:      None
' Exceptions:   実行時エラーはメッセージ表示し、状態を必ず復旧する
' SideEffects:  シートの「大・中・小」列に値を書き込む
' Preconditions:
'   - 対象シートに「大」「中」「小」ヘッダが存在すること
'------------------------------------------------------------------------------
Public Sub AssignNumbersOnActiveSheet()
    Dim appStateArry As Variant
    Dim targetSheet As Worksheet

    On Error GoTo ErrHandler

    appStateArry = captureApplicationState()
    Call applyApplicationStateForBatch

    ' 要件は「アクティブのみ」だが、以降は明示参照で処理する（暗黙依存を避ける）[1](https://westnttcojp-my.sharepoint.com/personal/isamu_chiba_eu_west_ntt_co_jp/Documents/Microsoft%20Copilot%20Chat%20%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB/%E3%82%B3%E3%83%BC%E3%83%87%E3%82%A3%E3%83%B3%E3%82%B0%E8%A6%8F%E7%B4%84.txt)
    If TypeName(Application.ActiveSheet) <> "Worksheet" Then
        Err.Raise vbObjectError + 1000, "AssignNumbersOnActiveSheet", "アクティブシートがワークシートではありません。"
    End If
    Set targetSheet = Application.ActiveSheet

    Call RenumberWorksheet(targetSheet)

Finally:
    Call restoreApplicationState(appStateArry)
    Exit Sub

ErrHandler:
    Call restoreApplicationState(appStateArry)
    MsgBox "採番処理でエラーが発生しました。" & vbCrLf & _
           "場所: " & Err.Source & vbCrLf & _
           "内容: " & Err.Description, vbExclamation
    Resume Finally
End Sub


'========================
' Application状態管理（共通化）
'========================
Private Function captureApplicationState() As Variant
    Dim stateArry(1 To 3) As Variant

    stateArry(1) = Application.ScreenUpdating
    stateArry(2) = Application.EnableEvents
    stateArry(3) = Application.Calculation

    captureApplicationState = stateArry
End Function

Private Sub applyApplicationStateForBatch()
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.Calculation = xlCalculationManual
End Sub

Private Sub restoreApplicationState(ByVal stateArry As Variant)
    If IsEmpty(stateArry) Then Exit Sub

    Application.ScreenUpdating = CBool(stateArry(1))
    Application.EnableEvents = CBool(stateArry(2))
    Application.Calculation = stateArry(3)
End Sub

