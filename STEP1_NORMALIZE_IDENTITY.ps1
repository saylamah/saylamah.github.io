param(
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

$TargetFiles = @(
    "index.html",
    "selected-work.html",
    "research-tools.html",
    "publications.html",
    "about-cv.html"
)

$OldFullName = "Prof. Dr. Ahmad Saylam"
$NewFullName = "Dr. Ahmad Saylam"
$OldHonorific = '"honorificPrefix": "Prof. Dr."'
$NewHonorific = '"honorificPrefix": "Dr."'

$Root = Get-Location
$Missing = @()

foreach ($File in $TargetFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $Root $File) -PathType Leaf)) {
        $Missing += $File
    }
}

if ($Missing.Count -gt 0) {
    throw "Run this file from the website repository root. Missing: $($Missing -join ', ')"
}

$Changes = @{}
$Total = 0

foreach ($File in $TargetFiles) {
    $Path = Join-Path $Root $File
    $Text = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)

    $CountFullName = ([regex]::Matches($Text, [regex]::Escape($OldFullName))).Count
    $CountHonorific = ([regex]::Matches($Text, [regex]::Escape($OldHonorific))).Count
    $FileTotal = $CountFullName + $CountHonorific
    $Total += $FileTotal

    $Updated = $Text.Replace($OldFullName, $NewFullName).Replace($OldHonorific, $NewHonorific)

    if ($Updated.Contains($OldFullName) -or $Updated.Contains($OldHonorific)) {
        throw "Old identity marker remains in $File after the planned replacement."
    }

    $Changes[$File] = [PSCustomObject]@{
        Original = $Text
        Updated = $Updated
        FullNameCount = $CountFullName
        HonorificCount = $CountHonorific
        Total = $FileTotal
    }
}

Write-Host ""
Write-Host "Step 1 identity normalization"
Write-Host "Repository: $Root"
Write-Host "Mode: $(if ($Apply) {'APPLY'} else {'DRY RUN'})"
Write-Host ""

foreach ($File in $TargetFiles) {
    Write-Host "$File`: $($Changes[$File].Total) replacement(s)"
}
Write-Host ""
Write-Host "Total planned replacements: $Total"

if ($Total -eq 0) {
    Write-Host ""
    Write-Host "No matching old identity strings were found. The files may already be normalized."
    exit 0
}

if (-not $Apply) {
    Write-Host ""
    Write-Host "Dry run passed. No files were changed."
    Write-Host "Run STEP1_APPLY.cmd to create backups and apply the verified replacements."
    exit 0
}

$Timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$BackupDir = Join-Path $Root "_identity_backup_$Timestamp"
New-Item -ItemType Directory -Path $BackupDir | Out-Null

foreach ($File in $TargetFiles) {
    $Path = Join-Path $Root $File
    Copy-Item -LiteralPath $Path -Destination (Join-Path $BackupDir $File)
    [System.IO.File]::WriteAllText(
        $Path,
        $Changes[$File].Updated,
        (New-Object System.Text.UTF8Encoding($false))
    )
}

foreach ($File in $TargetFiles) {
    $Path = Join-Path $Root $File
    $Written = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
    if ($Written.Contains($OldFullName) -or $Written.Contains($OldHonorific)) {
        throw "Verification failed: an old identity marker remains in $File."
    }
}

$Report = @(
    "# Identity Normalization Patch Report",
    "",
    "- Applied (UTC): $Timestamp",
    "- Approved current identity: **Dr. Ahmad Saylam**",
    "- Previous present-day identity: **Prof. Dr. Ahmad Saylam**",
    "- Scope: five principal website pages only",
    "- Historical publication/article pages modified: **No**",
    "- Backup directory: ``$(Split-Path $BackupDir -Leaf)/``",
    "",
    "## Modified files",
    ""
)

foreach ($File in $TargetFiles) {
    $Report += "### ``$File``"
    $Report += "- Full-name replacements: $($Changes[$File].FullNameCount)"
    $Report += "- JSON-LD honorific replacements: $($Changes[$File].HonorificCount)"
    $Report += "- Total replacements: $($Changes[$File].Total)"
    $Report += ""
}

$Report += @(
    "## Validation",
    "",
    "- No approved old identity marker remains in the five target files.",
    "- ``papers/`` and ``publications/`` article pages were not modified.",
    "- Review the Git diff before committing."
)

$ReportPath = Join-Path $Root "IDENTITY_PATCH_REPORT.md"
[System.IO.File]::WriteAllLines(
    $ReportPath,
    $Report,
    (New-Object System.Text.UTF8Encoding($false))
)

Write-Host ""
Write-Host "Patch applied and verified."
Write-Host "Backup: $BackupDir"
Write-Host "Report: $ReportPath"
