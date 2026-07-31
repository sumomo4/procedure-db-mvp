[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$CaseDocPath,

    [switch]$ValidateOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:LogPath = $null
$script:ExitCode = 1

function Initialize-RunLog {
    $logDirectory = Join-Path $PSScriptRoot "logs"
    if (-not (Test-Path -LiteralPath $logDirectory)) {
        New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $script:LogPath = Join-Path $logDirectory "case_doc_cdcreator_$timestamp.log"
}

function Write-RunLog {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("INFO", "WARN", "ERROR")]
        [string]$Level,

        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    if ($Level -eq "ERROR") {
        Write-Host $line -ForegroundColor Red
    } elseif ($Level -eq "WARN") {
        Write-Host $line -ForegroundColor Yellow
    } else {
        Write-Host $line
    }

    if ($null -ne $script:LogPath) {
        Add-Content -LiteralPath $script:LogPath -Value $line -Encoding UTF8
    }
}

function Select-CaseDocFile {
    Add-Type -AssemblyName System.Windows.Forms

    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    try {
        $dialog.Title = "案件CSを選択してください"
        $dialog.Filter = "マクロ有効Excelブック (*.xlsm)|*.xlsm"
        $dialog.Multiselect = $false
        $dialog.CheckFileExists = $true
        $dialog.CheckPathExists = $true

        $result = $dialog.ShowDialog()
        if ($result -ne [System.Windows.Forms.DialogResult]::OK) {
            return $null
        }

        return $dialog.FileName
    } finally {
        $dialog.Dispose()
    }
}

function Test-CaseDocPackage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $vbaProject = $archive.GetEntry("xl/vbaProject.bin")
        if ($null -eq $vbaProject) {
            throw "VBAプロジェクトが含まれていません。CDCreator組み込み済みの案件CSを選択してください。"
        }
    } finally {
        $archive.Dispose()
    }
}

function Test-CaseDocFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "案件CSが見つかりません: $Path"
    }

    $resolvedPath = (Resolve-Path -LiteralPath $Path).Path
    $file = Get-Item -LiteralPath $resolvedPath

    if ($file.Extension -ine ".xlsm") {
        throw "対象ファイルは.xlsm形式である必要があります: $($file.Name)"
    }

    if ($file.Name.StartsWith("~`$")) {
        throw "Excelの一時ファイルは処理できません: $($file.Name)"
    }

    if (($file.Attributes -band [System.IO.FileAttributes]::ReadOnly) -ne 0) {
        throw "案件CSが読み取り専用です。書き込み可能な場所へ移動してください: $resolvedPath"
    }

    $stream = $null
    try {
        $stream = [System.IO.File]::Open(
            $resolvedPath,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None
        )
    } catch {
        throw "案件CSを開けません。Excelで開いている場合は閉じてください: $resolvedPath"
    } finally {
        if ($null -ne $stream) {
            $stream.Dispose()
        }
    }

    Test-CaseDocPackage -Path $resolvedPath

    try {
        $zoneData = Get-Content -LiteralPath $resolvedPath -Stream "Zone.Identifier" -ErrorAction Stop
        if (($zoneData -join "`n") -match "ZoneId=[34]") {
            Write-RunLog -Level "WARN" -Message "インターネット由来の印が付いています。マクロがブロックされる場合は、信頼できる場所へ配置するかファイルのブロックを解除してください。"
        }
    } catch {
        # Zone.Identifierがないローカルファイルは正常。
    }

    return $resolvedPath
}

function New-CaseDocLock {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $lockPath = "$Path.cdcreator.lock"
    try {
        $lockStream = [System.IO.File]::Open(
            $lockPath,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None
        )
    } catch {
        throw "同じ案件CSの処理中、またはロックファイルが残っています: $lockPath"
    }

    $lockText = "PID={0}`r`nStartedAt={1:O}`r`n" -f $PID, (Get-Date)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($lockText)
    $lockStream.Write($bytes, 0, $bytes.Length)
    $lockStream.Flush()

    return [PSCustomObject]@{
        Path = $lockPath
        Stream = $lockStream
    }
}

function Remove-CaseDocLock {
    param(
        [AllowNull()]
        [object]$Lock
    )

    if ($null -eq $Lock) {
        return
    }

    try {
        if ($null -ne $Lock.Stream) {
            $Lock.Stream.Dispose()
        }
    } finally {
        if (Test-Path -LiteralPath $Lock.Path) {
            Remove-Item -LiteralPath $Lock.Path -Force -ErrorAction SilentlyContinue
        }
    }
}

function Get-CdOutputSnapshot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Directory
    )

    $snapshot = @{}
    Get-ChildItem -LiteralPath $Directory -Filter "app修正前_*_CD_*.xlsx" -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            $snapshot[$_.FullName.ToLowerInvariant()] = $_.LastWriteTimeUtc.Ticks
        }
    return $snapshot
}

function Get-NewCdOutputs {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Directory,

        [Parameter(Mandatory = $true)]
        [hashtable]$Before
    )

    return @(
        Get-ChildItem -LiteralPath $Directory -Filter "app修正前_*_CD_*.xlsx" -File -ErrorAction SilentlyContinue |
            Where-Object {
                -not $Before.ContainsKey($_.FullName.ToLowerInvariant())
            } |
            Sort-Object FullName
    )
}

function Release-ComObject {
    param(
        [AllowNull()]
        [object]$ComObject
    )

    if ($null -eq $ComObject) {
        return
    }

    try {
        if ([System.Runtime.InteropServices.Marshal]::IsComObject($ComObject)) {
            [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($ComObject)
        }
    } catch {
        # 終了処理では元のエラーを優先する。
    }
}

function Get-CsSheetNames {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Worksheets
    )

    $names = New-Object System.Collections.Generic.List[string]
    for ($index = 1; $index -le $Worksheets.Count; $index++) {
        $worksheet = $null
        try {
            $worksheet = $Worksheets.Item($index)
            $name = [string]$worksheet.Name
            if ($name.IndexOf("CS", [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
                $names.Add($name)
            }
        } finally {
            Release-ComObject -ComObject $worksheet
        }
    }

    return @($names)
}

function Get-QualifiedMacroName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkbookName,

        [Parameter(Mandatory = $true)]
        [string]$MacroName
    )

    $escapedWorkbookName = $WorkbookName.Replace("'", "''")
    return "'$escapedWorkbookName'!$MacroName"
}

function Invoke-CaseDocAutomation {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $excel = $null
    $workbooks = $null
    $workbook = $null
    $worksheets = $null
    $caseDocLock = $null
    $saved = $false

    $directory = Split-Path -Parent $Path
    $beforeOutputs = Get-CdOutputSnapshot -Directory $directory

    try {
        $caseDocLock = New-CaseDocLock -Path $Path
        Write-RunLog -Level "INFO" -Message "Excelを起動します。"

        try {
            $excel = New-Object -ComObject Excel.Application
        } catch {
            throw "Excelデスクトップアプリを起動できません。Excelがインストールされているか確認してください。"
        }

        $excel.Visible = $true
        $excel.DisplayAlerts = $true
        $excel.AskToUpdateLinks = $false

        $workbooks = $excel.Workbooks
        $workbook = $workbooks.Open($Path, 0, $false)
        if ($workbook.ReadOnly) {
            throw "案件CSが読み取り専用で開かれました。ファイルの権限と使用状況を確認してください。"
        }

        $worksheets = $workbook.Worksheets
        $csSheetNames = @(Get-CsSheetNames -Worksheets $worksheets)
        if ($csSheetNames.Count -eq 0) {
            throw "シート名に「CS」を含む対象シートがありません。"
        }

        Write-RunLog -Level "INFO" -Message ("採番対象CSシート: " + ($csSheetNames -join ", "))

        $numberingMacro = Get-QualifiedMacroName -WorkbookName $workbook.Name -MacroName "AssignNumbersOnActiveSheet"
        foreach ($sheetName in $csSheetNames) {
            $worksheet = $null
            try {
                $worksheet = $worksheets.Item($sheetName)
                [void]$worksheet.Activate()
                Write-RunLog -Level "INFO" -Message "採番を実行します: $sheetName"
                [void]$excel.Run($numberingMacro)
            } catch {
                throw "採番マクロの実行に失敗しました。マクロ名と対象シートを確認してください。対象: $sheetName / $($_.Exception.Message)"
            } finally {
                Release-ComObject -ComObject $worksheet
            }
        }

        [void]$workbook.Activate()
        $runCdCreatorMacro = Get-QualifiedMacroName -WorkbookName $workbook.Name -MacroName "runCdCreator"

        Write-RunLog -Level "INFO" -Message "CDCreatorを起動します。Excel画面で対象CSと出力先を選択してください。出力先は「このブックと同じフォルダ」を選択します。"
        try {
            [void]$excel.Run($runCdCreatorMacro)
        } catch {
            throw "runCdCreatorの実行に失敗しました。マクロの有効化状態を確認してください。$($_.Exception.Message)"
        }

        $newOutputs = @(Get-NewCdOutputs -Directory $directory -Before $beforeOutputs)
        if ($newOutputs.Count -eq 0) {
            Write-RunLog -Level "WARN" -Message "案件CSと同じフォルダにCD用Excelが生成されませんでした。キャンセル、別フォルダの選択、またはVBA処理失敗の可能性があります。案件CSの変更は保存しません。"
            $script:ExitCode = 2
            return
        }

        $workbook.Save()
        $saved = $true
        Write-RunLog -Level "INFO" -Message "採番済み案件CSを保存しました: $Path"

        foreach ($output in $newOutputs) {
            Write-RunLog -Level "INFO" -Message "CD用Excelを確認しました: $($output.FullName)"
        }

        $script:ExitCode = 0
    } finally {
        if ($null -ne $workbook) {
            try {
                $workbook.Close($false)
            } catch {
                Write-RunLog -Level "WARN" -Message "案件CSを閉じる際にエラーが発生しました。"
            }
        }

        Release-ComObject -ComObject $worksheets
        Release-ComObject -ComObject $workbook
        Release-ComObject -ComObject $workbooks

        if ($null -ne $excel) {
            try {
                $excel.Quit()
            } catch {
                Write-RunLog -Level "WARN" -Message "Excel終了時にエラーが発生しました。"
            }
        }
        Release-ComObject -ComObject $excel

        Remove-CaseDocLock -Lock $caseDocLock

        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()

        if (-not $saved -and $script:ExitCode -eq 0) {
            $script:ExitCode = 1
        }
    }
}

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    Initialize-RunLog
    Write-RunLog -Level "INFO" -Message "案件CS・CDCreator連携バッチを開始します。"

    if ([string]::IsNullOrWhiteSpace($CaseDocPath)) {
        $CaseDocPath = Select-CaseDocFile
        if ([string]::IsNullOrWhiteSpace($CaseDocPath)) {
            Write-RunLog -Level "WARN" -Message "案件CSの選択をキャンセルしました。"
            $script:ExitCode = 2
        }
    }

    if ($script:ExitCode -ne 2) {
        $validatedPath = Test-CaseDocFile -Path $CaseDocPath
        Write-RunLog -Level "INFO" -Message "入力検証に成功しました: $validatedPath"

        if ($ValidateOnly) {
            Write-RunLog -Level "INFO" -Message "検証のみで終了します。Excelとマクロは実行していません。"
            $script:ExitCode = 0
        } else {
            Invoke-CaseDocAutomation -Path $validatedPath
        }
    }
} catch {
    Write-RunLog -Level "ERROR" -Message $_.Exception.Message
    $script:ExitCode = 1
}

Write-RunLog -Level "INFO" -Message "終了コード: $($script:ExitCode)"
if ($null -ne $script:LogPath) {
    Write-Host "ログ: $($script:LogPath)"
}
exit $script:ExitCode
