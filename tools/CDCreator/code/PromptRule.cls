VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "PromptRule"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False

Option Explicit

'========================================
' クラス名 : PromptRule
' 目的     : プロンプト変換表（プロンプトシート）1行分の定義を保持
'========================================


Private pPromptKey As String
Private pCdType As String
Private pCdReg As String
Private pCdPromptOut As String
Private pNeedRule As String
Private pCommandRequired As Boolean
Private pPriority As Long
Private pContOn As String

Public Property Get promptKey() As String
    promptKey = pPromptKey
End Property
Public Property Let promptKey(ByVal v As String)
    pPromptKey = v
End Property

Public Property Get CdType() As String
    CdType = pCdType
End Property
Public Property Let CdType(ByVal v As String)
    pCdType = v
End Property

Public Property Get CdReg() As String
    CdReg = pCdReg
End Property
Public Property Let CdReg(ByVal v As String)
    pCdReg = v
End Property

Public Property Get CdPromptOut() As String
    CdPromptOut = pCdPromptOut
End Property
Public Property Let CdPromptOut(ByVal v As String)
    pCdPromptOut = v
End Property

Public Property Get NeedRule() As String
    NeedRule = pNeedRule
End Property
Public Property Let NeedRule(ByVal v As String)
    pNeedRule = v
End Property

Public Property Get CommandRequired() As Boolean
    CommandRequired = pCommandRequired
End Property
Public Property Let CommandRequired(ByVal v As Boolean)
    pCommandRequired = v
End Property

Public Property Get Priority() As Long
    Priority = pPriority
End Property
Public Property Let Priority(ByVal v As Long)
    pPriority = v
End Property

Public Property Get ContOn() As String
    ContOn = pContOn
End Property
Public Property Let ContOn(ByVal v As String)
    pContOn = v
End Property



