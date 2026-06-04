Attribute VB_Name = "Module1"
'
' CD_Creator v2.0
' 2025/9/xx
' ------v2.0 変更予定------
'  ・複数装置に対するCD作成に対応
'    ・window1～20までの行実施要否の出力
'    ・複数装置で個別にコマンド投入するパターンへの対応
'
' ------v1.1.1 変更履歴------
'  ・H列に実施要否（A～T列）を出力するように
'  ・実施しない箇所の空行が多くなるよう変更 → 他行での作業が入力しやすく
'
' ------v1.1 変更履歴------
'  ・"＃"（2バイト文字）で判定してしまっているバグを修正
'  ・「CDCreater」→「CDCreator」に変更（スペルミスの修正）
'  ・A列,B列が入力されていない場合、直前の値とするよう仕様変更
'  →A列,B列が空欄でも、C列に項番が付いていれば項番の行が生成されるように
'

Dim lastAddress As String
Dim monitorScheduled As Boolean

Public Sub CDCreater()
    CD_Creater.Show vbModeless
    StartSelectionMonitor
End Sub

Public Sub StartSelectionMonitor()
    lastAddress = ""
    monitorScheduled = True
    MonitorSelection
End Sub

Public Sub StopSelectionMonitor()
    monitorScheduled = False
End Sub

Private Sub MonitorSelection()
    If Not monitorScheduled Then Exit Sub

    Dim currentAddress As String
    currentAddress = ActiveSheet.Name & "!" & Selection.Address

    If currentAddress <> lastAddress Then
        lastAddress = currentAddress
        If CD_Creater.Visible Then
            UpdateSelectionInfo
        End If
    End If

    Application.OnTime Now + TimeValue("00:00:01"), "MonitorSelection"
End Sub

Public Sub UpdateSelectionInfo()
    With CD_Creater
        .sh_name.Text = ActiveSheet.Name
        .r_row.Text = Selection.Row
        .r_col.Text = Split(Cells(1, Selection.Column).Address, "$")(1)
    End With
End Sub

Public Sub GenerateCDSheet()
    Dim wsSrc As Worksheet
    Dim wsDest As Worksheet
    Dim lastRow As Long
    Dim srcRow As Long
    Dim destRow As Long
    Dim prompt As String
    Dim command As String
    Dim promptType As String
    Dim regValue As String
    Dim startRow As Long
    Dim itemNumber As String
    Dim aVal As String, bVal As String, cVal As String
    Dim showComment As Boolean
    Dim i As Long
    Dim lastCDRow As Long
    Dim prevPrompt As String
    Dim cdSheetName As String
    Dim commandCol As Long
    Dim promptCol As Long

    Set wsSrc = ActiveSheet
    startRow = ActiveCell.Row
    commandCol = ActiveCell.Column
    promptCol = commandCol - 1

    If commandCol <= 1 Then
        MsgBox "コマンド列はL列以降を選択してください。", vbExclamation
        Exit Sub
    End If

    'prevPrompt = ""
    'cdSheetName = "CD_" & wsSrc.Name & "_" & commandCol
    Dim colLetter As String
    colLetter = Split(Cells(1, commandCol).Address, "$")(1)
    cdSheetName = "CD_" & colLetter & "_" & wsSrc.Name

    On Error Resume Next
    Application.DisplayAlerts = False
    Worksheets(cdSheetName).Delete
    Application.DisplayAlerts = True
    On Error GoTo 0

    Set wsDest = Worksheets.Add(After:=wsSrc)
    wsDest.Name = cdSheetName

    With wsDest.Range("A1:H1")
        .Value = Array("type", "cont-on", "cont-time", "reg", "prompt", "command", "", "window1")
        .Interior.Color = rgb(226, 239, 218)
    End With
    '★仮でH列にwindow行を追加

    lastRow = wsSrc.Cells(wsSrc.Rows.Count, promptCol).End(xlUp).Row
    destRow = 2

    '複数カラムに対応するFor文で下記For文をネスト？
    For srcRow = startRow To lastRow
        prompt = Trim(wsSrc.Cells(srcRow, promptCol).Value)
        command = Trim(wsSrc.Cells(srcRow, commandCol).Value)

        'If prompt = "" Then GoTo NextRow
        'この行で空行を無視　→　無視せず空行のまま

        If Trim(wsSrc.Cells(srcRow, "A").Value) <> "" Then aVal = Trim(wsSrc.Cells(srcRow, "A").Value)
        If Trim(wsSrc.Cells(srcRow, "B").Value) <> "" Then bVal = Trim(wsSrc.Cells(srcRow, "B").Value)
        cVal = Trim(wsSrc.Cells(srcRow, "C").Value)

        showComment = Not (aVal = "" Or bVal = "" Or cVal = "" Or _
                           aVal = "--" Or bVal = "--" Or cVal = "--")

        If prompt = "TT" Or prompt = "SCP" Or prompt = "FTP" Or _
           prompt = "DF" Or prompt = "IE" Or prompt = "WIN" Then

            If prompt <> prevPrompt Then
                If showComment Then
                    itemNumber = aVal & "-" & bVal & "-" & cVal
                    wsDest.Cells(destRow, "A").Value = "comment"
                    wsDest.Cells(destRow, "H").Value = "T"
                    destRow = destRow + 1
                    wsDest.Cells(destRow, "A").Value = "comment"
                    wsDest.Cells(destRow, "F").NumberFormat = "@"
                    wsDest.Cells(destRow, "F").Value = CStr(itemNumber)
                    wsDest.Cells(destRow, "H").Value = "T"
                    wsDest.Cells(destRow, "H").Font.Name = "Wingdings 2"
                    '★仮でH列にwindow行を追加
                    destRow = destRow + 1
                End If

                With wsDest
                    .Cells(destRow, "A").Value = "notify"
                    .Cells(destRow, "F").Value = "作業CSに従い手動作業を実施してください。"
                    .Cells(destRow, "H").Value = "T"
                    .Cells(destRow, "H").Font.Name = "Wingdings 2"
                    '★仮でH列にwindow行を追加
                End With
                destRow = destRow + 1
            End If

            prevPrompt = prompt
            GoTo nextRow
        End If

        If showComment Then
            itemNumber = aVal & "-" & bVal & "-" & cVal
            wsDest.Cells(destRow, "A").Value = "comment"
            wsDest.Cells(destRow, "H").Value = "T"
            wsDest.Cells(destRow, "H").Font.Name = "Wingdings 2"
            destRow = destRow + 1
            wsDest.Cells(destRow, "A").Value = "comment"
            wsDest.Cells(destRow, "F").NumberFormat = "@"
            wsDest.Cells(destRow, "F").Value = CStr(itemNumber)
            wsDest.Cells(destRow, "H").Value = "T"
            wsDest.Cells(destRow, "H").Font.Name = "Wingdings 2"
            '★仮でH列にwindow行を追加
            destRow = destRow + 1
        End If

        promptType = ""
        regValue = ""

        Select Case prompt
            Case "chk", "Eck"
                promptType = "ckExist"
                If prompt = "Eck" Then regValue = "on"
            Case "ckN", "EcN"
                promptType = "ckNot"
                If prompt = "EcN" Then regValue = "on"
        End Select

        With wsDest
            .Cells(destRow, "A").Value = promptType
            If promptType = "ckExist" Or promptType = "ckNot" Then
                .Cells(destRow, "B").Value = "on"
            End If
            .Cells(destRow, "D").Value = regValue

            Select Case prompt
                Case ">", "$", "%", "#"
                    .Cells(destRow, "E").Value = prompt
                Case "chk", "Eck", "ckN", "EcN"
                    .Cells(destRow, "E").Value = ""
                Case Else
                    .Cells(destRow, "E").Value = prompt
            End Select

            .Cells(destRow, "F").Value = command
            .Cells(destRow, "H").Value = "R"
            .Cells(destRow, "H").Font.Name = "Wingdings 2"
            '★仮でH列にwindow行を追加
        End With

        destRow = destRow + 1

nextRow:
    Next srcRow

    lastCDRow = wsDest.Cells(wsDest.Rows.Count, "A").End(xlUp).Row

    For i = 3 To lastCDRow
        If wsDest.Cells(i, "A").Value = "ckExist" Or wsDest.Cells(i, "A").Value = "ckNot" Then
            wsDest.Cells(i, "B").Value = "on"
        End If

        If wsDest.Cells(i, "A").Value = "ckExist" Or wsDest.Cells(i, "A").Value = "ckNot" Then
            If wsDest.Cells(i - 1, "A").Value = "" Then
                wsDest.Cells(i - 1, "A").Value = "ckOut"
                wsDest.Cells(i - 1, "B").Value = "on"
                wsDest.Cells(i - 1, "C").Value = 5
            End If
        End If

        If wsDest.Cells(i, "A").Value = "ckExist" Or wsDest.Cells(i, "A").Value = "ckNot" Then
            If wsDest.Cells(i + 1, "A").Value = "comment" Then
                wsDest.Rows(i + 1).Insert Shift:=xlDown
            End If

            If Not (wsDest.Cells(i + 1, "A").Value = "ckExist" Or wsDest.Cells(i + 1, "A").Value = "ckNot") Then
                Dim j As Long
                Dim foundPrompt As String
                foundPrompt = ""
                For j = i - 1 To 2 Step -1
                    If wsDest.Cells(j, "A").Value = "ckOut" Then
                        foundPrompt = wsDest.Cells(j, "E").Value
                        Exit For
                    End If
                Next j

                With wsDest
                    '.Cells(i + 1, "C").Value = 5
                    .Cells(i + 1, "E").Value = foundPrompt
                End With
            End If

            If wsDest.Cells(i + 1, "A").Value = "comment" Then
                lastCDRow = lastCDRow + 1
                i = i + 1
            End If
        End If
    Next i

    wsDest.Columns("A:H").AutoFit
    MsgBox "[" + cdSheetName + "]の作成が完了しました｡ ", vbInformation
End Sub






