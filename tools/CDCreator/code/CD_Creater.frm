VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} CD_Creater 
   Caption         =   "CD_Creater v1.1"
   ClientHeight    =   3900
   ClientLeft      =   120
   ClientTop       =   465
   ClientWidth     =   6990
   OleObjectBlob   =   "CD_Creater.frx":0000
   StartUpPosition =   1  'オーナー フォームの中央
End
Attribute VB_Name = "CD_Creater"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
'
' CD_Creator v1.0
' 2025/6/5
'

Private Sub UserForm_Initialize()
    UpdateSelectionInfo
End Sub

Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
    StopSelectionMonitor
End Sub

Private Sub cre_btn_Click()
    Dim targetSheet As Worksheet
    Dim targetRow As Long
    Dim targetCol As Long

    Set targetSheet = Worksheets(Me.sh_name.Text)
    targetRow = CLng(Me.r_row.Text)
    targetCol = Columns(Me.r_col.Text).Column

    ' マクロ本体を呼び出す
    Call GenerateCDSheet
End Sub
