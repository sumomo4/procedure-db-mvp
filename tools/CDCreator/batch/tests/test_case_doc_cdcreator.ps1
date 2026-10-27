[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path (Split-Path -Parent $PSScriptRoot) "run_case_doc_cdcreator.ps1"
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) {
    throw ($parseErrors | Out-String)
}

# Load functions only; do not run the entry point or Excel automation.
foreach ($function in $ast.FindAll({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $false)) {
    . ([scriptblock]::Create($function.Extent.Text))
}

$script:LogPath = $null
$script:ExitCode = 1
$script:Passed = 0
$tempParent = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$testRoot = Join-Path $tempParent ("cdcreator-tests-" + [guid]::NewGuid().ToString("N"))
$driveName = "CDTest" + [guid]::NewGuid().ToString("N").Substring(0, 8)

function Assert-Equal {
    param([object]$Expected, [object]$Actual, [string]$Name)
    if ($Actual -cne $Expected) {
        throw "$Name failed. Expected: $Expected / Actual: $Actual"
    }
    $script:Passed++
    Write-Host "PASS: $Name"
}

function New-TestWorkbook {
    param([string]$Path, [bool]$IncludeVba = $true)
    $archive = [System.IO.Compression.ZipFile]::Open($Path, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        if ($IncludeVba) {
            $entry = $archive.CreateEntry("xl/vbaProject.bin")
            $stream = $entry.Open()
            try {
                $bytes = [System.Text.Encoding]::ASCII.GetBytes("validation-fixture-only")
                $stream.Write($bytes, 0, $bytes.Length)
            } finally {
                $stream.Dispose()
            }
        }
    } finally {
        $archive.Dispose()
    }
}

try {
    New-Item -ItemType Directory -Path $testRoot | Out-Null
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $workbookPath = Join-Path $testRoot "case doc [1].xlsm"
    New-TestWorkbook -Path $workbookPath

    Assert-Equal $workbookPath (Test-CaseDocFile -Path $workbookPath) "Native local path"

    $qualifiedPath = "Microsoft.PowerShell.Core\FileSystem::$workbookPath"
    Assert-Equal $workbookPath (Test-CaseDocFile -Path $qualifiedPath) "Provider-qualified input returns a native path"

    New-PSDrive -Name $driveName -PSProvider FileSystem -Root $testRoot | Out-Null
    $drivePath = "${driveName}:\case doc [1].xlsm"
    Assert-Equal $workbookPath (Test-CaseDocFile -Path $drivePath) "PowerShell drive path works with .NET"

    $locked = [System.IO.File]::Open($workbookPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    try {
        $failure = $null
        try { Test-CaseDocFile -Path $workbookPath | Out-Null } catch { $failure = $_ }
        Assert-Equal $true ($null -ne $failure) "An open workbook is rejected"
        Assert-Equal $true ($failure.Exception.Message.Contains($workbookPath)) "File error retains the native path"
        Assert-Equal $true ($failure.Exception.Message.Contains(" / ")) "File error retains the underlying reason"
    } finally {
        $locked.Dispose()
    }

    $missingVbaPath = Join-Path $testRoot "without-vba.xlsm"
    New-TestWorkbook -Path $missingVbaPath -IncludeVba $false
    $failure = $null
    try { Test-CaseDocFile -Path $missingVbaPath | Out-Null } catch { $failure = $_ }
    Assert-Equal $true ($null -ne $failure) "A workbook without VBA is rejected"

    $primary = Join-Path $testRoot "primary-logs"
    $fallback = Join-Path $testRoot "fallback-logs"
    Initialize-RunLog -LogDirectory $primary -FallbackLogDirectory $fallback
    Write-RunLog -Level INFO -Message "primary log test"
    Assert-Equal $primary ([System.IO.Path]::GetDirectoryName($script:LogPath)) "Preferred log directory"
    Assert-Equal $true ([System.IO.File]::ReadAllText($script:LogPath).Contains("primary log test")) "Log messages are saved"

    $blocked = Join-Path $testRoot "blocked-directory"
    [System.IO.File]::WriteAllText($blocked, "not a directory")
    Initialize-RunLog -LogDirectory (Join-Path $blocked "logs") -FallbackLogDirectory $fallback
    Write-RunLog -Level ERROR -Message "original error test"
    Assert-Equal $fallback ([System.IO.Path]::GetDirectoryName($script:LogPath)) "Unavailable primary directory falls back"
    Assert-Equal $true ([System.IO.File]::ReadAllText($script:LogPath).Contains("original error test")) "Fallback log preserves the original error"

    Initialize-RunLog -LogDirectory (Join-Path $blocked "logs") -FallbackLogDirectory (Join-Path $blocked "fallback")
    Assert-Equal $null $script:LogPath "Unavailable log directories do not terminate the run"
    $script:ExitCode = 2
    Write-RunLog -Level ERROR -Message "console-only test"
    Assert-Equal 2 $script:ExitCode "Console-only logging preserves the exit code"

    $script:LogPath = $testRoot
    Write-RunLog -Level ERROR -Message "original failure after log initialization"
    Assert-Equal $null $script:LogPath "A late log failure is non-terminating"
    Assert-Equal 2 $script:ExitCode "A late log failure preserves the exit code"

    Write-Host "All $($script:Passed) assertions passed. Excel was not started."
} finally {
    if (Get-PSDrive -Name $driveName -ErrorAction SilentlyContinue) {
        Remove-PSDrive -Name $driveName
    }
    $fullTestRoot = [System.IO.Path]::GetFullPath($testRoot)
    if (-not $fullTestRoot.StartsWith($tempParent.TrimEnd('\') + '\', [System.StringComparison]::OrdinalIgnoreCase) -or
        [System.IO.Path]::GetFileName($fullTestRoot) -notmatch '^cdcreator-tests-[a-f0-9]{32}$') {
        throw "Refusing to remove an unexpected test directory: $fullTestRoot"
    }
    if (Test-Path -LiteralPath $fullTestRoot) {
        Remove-Item -LiteralPath $fullTestRoot -Recurse -Force
    }
}
