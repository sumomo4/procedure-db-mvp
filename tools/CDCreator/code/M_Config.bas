Attribute VB_Name = "M_Config"
Option Explicit

'==============================================================================
' Module:      M_Config
' Purpose:     採番ツールの構成値を一元管理する（マジックナンバー排除）
' Dependencies: None
' Notes:
'   - 設定値は原則ここに集約する（グローバル変数は禁止）[1](https://westnttcojp-my.sharepoint.com/personal/isamu_chiba_eu_west_ntt_co_jp/Documents/Microsoft%20Copilot%20Chat%20%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB/%E3%82%B3%E3%83%BC%E3%83%87%E3%82%A3%E3%83%B3%E3%82%B0%E8%A6%8F%E7%B4%84.txt)
' History:
'   2026-02-16  Initial
'==============================================================================

'--- 採番トリガ列（テンプレ想定：E=作業内容、F=箇条書き） ---
Public Const COL_MAIN_TRIGGER As Long = 5     ' E列
Public Const COL_SUB_TRIGGER  As Long = 6     ' F列

'--- 初期値（大0開始を実現するため、内部は -1 から開始し灰色行で +1） ---
Public Const INITIAL_BIG_NO   As Long = -1
Public Const INITIAL_MID_NO   As Long = 0
Public Const INITIAL_SMALL_NO As Long = 0

'--- 要件確定：E行で小は 1 に戻す ---
Public Const RESET_SMALL_ON_MAIN As Boolean = True

'--- ヘッダ探索の上限（過剰探索を避けつつ安全側） ---
Public Const HEADER_SEARCH_MAX_ROW As Long = 200
Public Const HEADER_SEARCH_MAX_COL As Long = 50

'--- 「大・中・小」ヘッダ文字（テンプレ準拠） ---
Public Const HEADER_BIG_TEXT   As String = "大"
Public Const HEADER_MID_TEXT   As String = "中"
Public Const HEADER_SMALL_TEXT As String = "小"

'--- 列番号は列挙体で扱う（規約準拠）[1](https://westnttcojp-my.sharepoint.com/personal/isamu_chiba_eu_west_ntt_co_jp/Documents/Microsoft%20Copilot%20Chat%20%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB/%E3%82%B3%E3%83%BC%E3%83%87%E3%82%A3%E3%83%B3%E3%82%B0%E8%A6%8F%E7%B4%84.txt) ---
Public Enum eClm
    eClmBig = 1
    eClmMid = 2
    eClmSmall = 3
End Enum
