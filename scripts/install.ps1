param(
    [string]$Ref = "main"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SkillName = "feishu-creator-doc-workflow"
$RepoSlug = "MrQ-Coding/feishu-creator-doc-workflow"
$RepoName = "feishu-creator-doc-workflow"

function Get-DestinationDirectory {
    $codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
    $skillsRoot = Join-Path $codexHome "skills"
    return Join-Path $skillsRoot $SkillName
}

function Get-LocalSourceDirectory {
    if (-not $PSScriptRoot) {
        return $null
    }

    $localRoot = Split-Path -Parent $PSScriptRoot
    $skillFile = Join-Path $localRoot "SKILL.md"
    if (Test-Path -LiteralPath $skillFile) {
        return $localRoot
    }

    return $null
}

function Get-DownloadedSourceDirectory {
    param(
        [string]$RequestedRef
    )

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString("N"))
    $zipPath = Join-Path $tempRoot "skill.zip"
    $extractRoot = Join-Path $tempRoot "source"
    New-Item -ItemType Directory -Force -Path $extractRoot | Out-Null

    $url = "https://github.com/$RepoSlug/archive/refs/heads/$RequestedRef.zip"
    Invoke-WebRequest -Uri $url -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $extractRoot -Force

    return @{
        TempRoot = $tempRoot
        SourceDir = Join-Path $extractRoot "$RepoName-$RequestedRef"
    }
}

function Copy-SkillContent {
    param(
        [string]$SourceDir,
        [string]$DestDir
    )

    $destRoot = Split-Path -Parent $DestDir
    New-Item -ItemType Directory -Force -Path $destRoot | Out-Null
    if (Test-Path -LiteralPath $DestDir) {
        Remove-Item -LiteralPath $DestDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null

    Get-ChildItem -LiteralPath $SourceDir -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $DestDir -Recurse -Force
    }

    $gitDir = Join-Path $DestDir ".git"
    $readmeFile = Join-Path $DestDir "README.md"
    if (Test-Path -LiteralPath $gitDir) {
        Remove-Item -LiteralPath $gitDir -Recurse -Force
    }
    if (Test-Path -LiteralPath $readmeFile) {
        Remove-Item -LiteralPath $readmeFile -Force
    }
}

$downloadState = $null

try {
    $sourceDir = Get-LocalSourceDirectory
    if (-not $sourceDir) {
        $downloadState = Get-DownloadedSourceDirectory -RequestedRef $Ref
        $sourceDir = $downloadState.SourceDir
    }

    $destDir = Get-DestinationDirectory
    Copy-SkillContent -SourceDir $sourceDir -DestDir $destDir

    Write-Host "Installed $SkillName to $destDir"
    Write-Host "Restart Codex to pick up the updated skill."
}
finally {
    if ($downloadState -and (Test-Path -LiteralPath $downloadState.TempRoot)) {
        Remove-Item -LiteralPath $downloadState.TempRoot -Recurse -Force
    }
}
