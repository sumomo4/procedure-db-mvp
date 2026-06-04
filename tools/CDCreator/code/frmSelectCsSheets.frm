VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} frmSelectCsSheets 
   Caption         =   "UserForm1"
   ClientHeight    =   7440
   ClientLeft      =   105
   ClientTop       =   450
   ClientWidth     =   11790
   OleObjectBlob   =   "frmSelectCsSheets.frx":0000
   StartUpPosition =   1  'オーナー フォームの中央
End
Attribute VB_Name = "frmSelectCsSheets"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False




Option Explicit

Private mCandidates As Collection ' Collection(Worksheet)
Private mCanceled As Boolean

Public Property Get IsCanceled() As Boolean
    IsCanceled = mCanceled
End Property

' 候補シートを受け取ってチェックボックス生成
Public Sub SetCandidates(ByVal csCandidates As Collection)
    Set mCandidates = csCandidates
    BuildCheckBoxes
End Sub

' 選択されたシートを返す（Collection(Worksheet)）
Public Function GetSelectedSheets() As Collection
    Dim sel As New Collection
    Dim ctl As MSForms.Control
    For Each ctl In Me.fraList.Controls
        If TypeName(ctl) = "CheckBox" Then
            If ctl.Value = True Then
                Dim ws As Worksheet
                Set ws = ThisWorkbook.Worksheets(CStr(ctl.Tag))
                sel.Add ws
            End If
        End If
    Next ctl
    Set GetSelectedSheets = sel
End Function

Private Sub CommandButton2_Click()

End Sub

Private Sub UserForm_Initialize()
    mCanceled = True ' 初期はキャンセル扱い（OKでFalse）
    
    ' スクロールを有効化（縦並び想定）
    Me.fraList.ScrollBars = fmScrollBarsVertical
    Me.fraList.KeepScrollBarsVisible = fmScrollBarsVertical
End Sub

Private Sub cmdOK_Click()
    ' 1つも選ばれていない場合はOKさせない（事故防止）
    Dim has As Boolean: has = False
    Dim ctl As MSForms.Control
    For Each ctl In Me.fraList.Controls
        If TypeName(ctl) = "CheckBox" Then
            If ctl.Value = True Then
                has = True
                Exit For
            End If
        End If
    Next ctl
    
    If Not has Then
        MsgBox "少なくとも1つのCSシートを選択してください。", vbExclamation
        Exit Sub
    End If
    
    mCanceled = False
    Me.Hide
End Sub

Private Sub cmdCancel_Click()
    mCanceled = True
    Me.Hide
End Sub

Private Sub cmdAll_Click()
    Dim ctl As MSForms.Control
    For Each ctl In Me.fraList.Controls
        If TypeName(ctl) = "CheckBox" Then ctl.Value = True
    Next ctl
End Sub

Private Sub cmdNone_Click()
    Dim ctl As MSForms.Control
    For Each ctl In Me.fraList.Controls
        If TypeName(ctl) = "CheckBox" Then ctl.Value = False
    Next ctl
End Sub

' チェックボックスを縦に作成
Private Sub BuildCheckBoxes()
    ' --- 既存クリア（実行時に追加した chk_ だけ削除）
    Dim i As Long
    For i = Me.fraList.Controls.Count - 1 To 0 Step -1
        With Me.fraList.Controls(i)
            If TypeName(Me.fraList.Controls(i)) = "CheckBox" Then
                If Left$(.Name, 4) = "chk_" Then
                    Me.fraList.Controls.Remove .Name
                End If
            End If
        End With
    Next i

    ' --- 追加
    Dim topPos As Single: topPos = 6
    Dim ws As Worksheet
    Dim idx As Long: idx = 1

    For Each ws In mCandidates
        Dim cb As MSForms.CheckBox
        Set cb = Me.fraList.Controls.Add("Forms.CheckBox.1", "chk_" & CStr(idx), True)

        cb.Caption = ws.Name
        cb.Tag = ws.Name
        cb.Left = 6
        cb.Top = topPos
        cb.Width = Me.fraList.Width - 18
        cb.Height = 18
        cb.Value = False

        topPos = topPos + 20
        idx = idx + 1
    Next ws

    ' スクロール範囲
    Me.fraList.ScrollHeight = topPos + 6
End Sub
