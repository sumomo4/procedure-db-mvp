Attribute VB_Name = "ExportProcedureDbAccessTables"
Option Compare Database
Option Explicit

Private Const DEFAULT_OUTPUT_DIR As String = "C:\ProcedureDbExports\access_exports"

Public Sub ExportProcedureDbAccessTables(Optional ByVal outputDir As String = DEFAULT_OUTPUT_DIR)
    On Error GoTo ErrorHandler

    Dim fso As Object
    Set fso = CreateObject("Scripting.FileSystemObject")

    EnsureFolder fso, outputDir

    Dim definitions As Collection
    Set definitions = GetExportDefinitions()

    Dim backupDir As String
    backupDir = BackupExistingExports(fso, outputDir, definitions)

    Dim manifestItems As Collection
    Set manifestItems = New Collection

    Dim definition As Object
    For Each definition In definitions
        ExportOneDefinition fso, outputDir, definition, manifestItems
    Next definition

    WriteManifest fso, outputDir, manifestItems

    Dim message As String
    message = "AccessDBからExcelファイルを抽出しました。" & vbCrLf & _
              "出力先: " & outputDir
    If Len(backupDir) > 0 Then
        message = message & vbCrLf & "バックアップ: " & backupDir
    End If

    MsgBox message, vbInformation, "Procedure DB Access Export"
    Exit Sub

ErrorHandler:
    MsgBox "AccessDB Excel抽出に失敗しました。" & vbCrLf & _
           Err.Number & ": " & Err.Description, vbCritical, "Procedure DB Access Export"
End Sub

Private Function GetExportDefinitions() As Collection
    Dim definitions As New Collection

    definitions.Add CreateExportDefinition("unit_config", "ユニット構成", "ユニット構成.xlsx")
    definitions.Add CreateExportDefinition("sbc", "SBC", "SBC.xlsx")
    definitions.Add CreateExportDefinition("common_values", "case_common_values", "case_common_values.xlsx")

    ' 次段階で必要になったら以下を有効化します。
    ' definitions.Add CreateExportDefinition("gui", "GUI", "GUI.xlsx")
    ' definitions.Add CreateExportDefinition("fs", "FS", "FS.xlsx")
    ' definitions.Add CreateExportDefinition("hfs", "HFS", "HFS.xlsx")
    ' definitions.Add CreateExportDefinition("hss", "HSS", "HSS.xlsx")
    ' definitions.Add CreateExportDefinition("msw", "MSW", "MSW.xlsx")
    ' definitions.Add CreateExportDefinition("raid", "RAID", "RAID.xlsx")
    ' definitions.Add CreateExportDefinition("scce", "SCCE", "SCCE.xlsx")

    Set GetExportDefinitions = definitions
End Function

Private Function CreateExportDefinition( _
    ByVal name As String, _
    ByVal sourceName As String, _
    ByVal outputFileName As String _
) As Object
    Dim definition As Object
    Set definition = CreateObject("Scripting.Dictionary")

    definition.Add "name", name
    definition.Add "sourceName", sourceName
    definition.Add "outputFileName", outputFileName

    Set CreateExportDefinition = definition
End Function

Private Sub ExportOneDefinition( _
    ByVal fso As Object, _
    ByVal outputDir As String, _
    ByVal definition As Object, _
    ByVal manifestItems As Collection _
)
    Dim sourceName As String
    sourceName = CStr(definition("sourceName"))

    If Not AccessObjectExists(sourceName) Then
        Err.Raise vbObjectError + 1001, , "Accessオブジェクトが見つかりません: " & sourceName
    End If

    Dim outputPath As String
    outputPath = fso.BuildPath(outputDir, CStr(definition("outputFileName")))

    If fso.FileExists(outputPath) Then
        fso.DeleteFile outputPath, True
    End If

    DoCmd.TransferSpreadsheet _
        TransferType:=acExport, _
        SpreadsheetType:=acSpreadsheetTypeExcel12Xml, _
        TableName:=sourceName, _
        FileName:=outputPath, _
        HasFieldNames:=True

    If Not fso.FileExists(outputPath) Then
        Err.Raise vbObjectError + 1002, , "Excelファイルの出力に失敗しました: " & outputPath
    End If

    Dim manifestItem As Object
    Set manifestItem = CreateObject("Scripting.Dictionary")
    manifestItem.Add "name", CStr(definition("name"))
    manifestItem.Add "source", sourceName
    manifestItem.Add "output_file", CStr(definition("outputFileName"))
    manifestItem.Add "row_count", CountAccessRows(sourceName)

    manifestItems.Add manifestItem
End Sub

Private Function AccessObjectExists(ByVal objectName As String) As Boolean
    Dim tableDef As DAO.TableDef
    For Each tableDef In CurrentDb.TableDefs
        If tableDef.Name = objectName Then
            AccessObjectExists = True
            Exit Function
        End If
    Next tableDef

    Dim queryDef As DAO.QueryDef
    For Each queryDef In CurrentDb.QueryDefs
        If queryDef.Name = objectName Then
            AccessObjectExists = True
            Exit Function
        End If
    Next queryDef

    AccessObjectExists = False
End Function

Private Function CountAccessRows(ByVal sourceName As String) As Long
    Dim sql As String
    sql = "SELECT Count(*) AS row_count FROM [" & Replace(sourceName, "]", "]]") & "]"

    Dim recordset As DAO.Recordset
    Set recordset = CurrentDb.OpenRecordset(sql, dbOpenSnapshot)

    If recordset.EOF Then
        CountAccessRows = 0
    Else
        CountAccessRows = CLng(recordset.Fields("row_count").Value)
    End If

    recordset.Close
    Set recordset = Nothing
End Function

Private Function BackupExistingExports( _
    ByVal fso As Object, _
    ByVal outputDir As String, _
    ByVal definitions As Collection _
) As String
    Dim hasBackupTarget As Boolean
    hasBackupTarget = False

    Dim definition As Object
    For Each definition In definitions
        If fso.FileExists(fso.BuildPath(outputDir, CStr(definition("outputFileName")))) Then
            hasBackupTarget = True
            Exit For
        End If
    Next definition

    If fso.FileExists(fso.BuildPath(outputDir, "export_manifest.json")) Then
        hasBackupTarget = True
    End If

    If Not hasBackupTarget Then
        BackupExistingExports = ""
        Exit Function
    End If

    Dim backupDir As String
    backupDir = fso.BuildPath(outputDir, "backup\" & Format(Now, "yyyymmdd_hhnnss"))
    EnsureFolder fso, backupDir

    For Each definition In definitions
        Dim sourcePath As String
        sourcePath = fso.BuildPath(outputDir, CStr(definition("outputFileName")))
        If fso.FileExists(sourcePath) Then
            fso.CopyFile sourcePath, fso.BuildPath(backupDir, fso.GetFileName(sourcePath)), True
        End If
    Next definition

    Dim manifestPath As String
    manifestPath = fso.BuildPath(outputDir, "export_manifest.json")
    If fso.FileExists(manifestPath) Then
        fso.CopyFile manifestPath, fso.BuildPath(backupDir, "export_manifest.json"), True
    End If

    BackupExistingExports = backupDir
End Function

Private Sub EnsureFolder(ByVal fso As Object, ByVal folderPath As String)
    If Len(folderPath) = 0 Then
        Exit Sub
    End If

    If fso.FolderExists(folderPath) Then
        Exit Sub
    End If

    Dim parentPath As String
    parentPath = fso.GetParentFolderName(folderPath)
    If Len(parentPath) > 0 And Not fso.FolderExists(parentPath) Then
        EnsureFolder fso, parentPath
    End If

    fso.CreateFolder folderPath
End Sub

Private Sub WriteManifest(ByVal fso As Object, ByVal outputDir As String, ByVal manifestItems As Collection)
    Dim manifestPath As String
    manifestPath = fso.BuildPath(outputDir, "export_manifest.json")

    Dim stream As Object
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Charset = "utf-8"
    stream.Open
    stream.WriteText BuildManifestJson(manifestItems)
    stream.SaveToFile manifestPath, 2
    stream.Close
End Sub

Private Function BuildManifestJson(ByVal manifestItems As Collection) As String
    Dim json As String
    json = "{" & vbCrLf
    json = json & "  ""exported_at"": """ & JsonEscape(Format(Now, "yyyy-mm-dd hh:nn:ss")) & """," & vbCrLf
    json = json & "  ""exports"": [" & vbCrLf

    Dim index As Long
    For index = 1 To manifestItems.Count
        Dim item As Object
        Set item = manifestItems(index)

        json = json & "    {" & vbCrLf
        json = json & "      ""name"": """ & JsonEscape(CStr(item("name"))) & """," & vbCrLf
        json = json & "      ""source"": """ & JsonEscape(CStr(item("source"))) & """," & vbCrLf
        json = json & "      ""output_file"": """ & JsonEscape(CStr(item("output_file"))) & """," & vbCrLf
        json = json & "      ""row_count"": " & CStr(item("row_count")) & vbCrLf
        json = json & "    }"

        If index < manifestItems.Count Then
            json = json & ","
        End If
        json = json & vbCrLf
    Next index

    json = json & "  ]" & vbCrLf
    json = json & "}" & vbCrLf

    BuildManifestJson = json
End Function

Private Function JsonEscape(ByVal value As String) As String
    Dim escaped As String
    escaped = Replace(value, "\", "\\")
    escaped = Replace(escaped, """", "\""")
    escaped = Replace(escaped, vbCrLf, "\n")
    escaped = Replace(escaped, vbCr, "\n")
    escaped = Replace(escaped, vbLf, "\n")
    JsonEscape = escaped
End Function
