Attribute VB_Name = "Mod_Validate"
Option Explicit

'========================================
' モジュール名 : Mod_Validate
' 目的         : 値検証（windowNo / command）
' 依存         : Mod_Common
'========================================

Public Function IsValidWindowNo(ByVal v As Variant) As Boolean
    If Not IsNumeric(v) Then
        IsValidWindowNo = False
        Exit Function
    End If
    Dim n As Long
    n = CLng(v)
    IsValidWindowNo = (n >= 1 And n <= MAX_DEVICE_COL)
End Function

Public Function IsCommandNonEmpty(ByVal s As String) As Boolean
    IsCommandNonEmpty = (Len(Trim$(s)) > 0)
End Function


