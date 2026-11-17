[CmdletBinding()]
param(
    [switch]$Reemplazar,
    [string]$RepoRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
)

$ErrorActionPreference = 'Stop'
$sourceRoot = Join-Path $PSScriptRoot 'ui-tests'
$targetRoot = Join-Path $RepoRoot 'frontend\src'

if (-not (Test-Path $targetRoot)) {
    throw "No encuentro '$targetRoot'. Verifica que RepoRoot apunte a la raíz del repositorio."
}

$files = @(
    @{ Source = 'components\ui\StateMessage.component.test.tsx'; Target = 'components\ui\StateMessage.component.test.tsx' },
    @{ Source = 'features\app-shell\TopBar.component.test.tsx'; Target = 'features\app-shell\TopBar.component.test.tsx' },
    @{ Source = 'features\auth\SessionMenu.component.test.tsx'; Target = 'features\auth\SessionMenu.component.test.tsx' }
)

$copied = 0
$skipped = 0
foreach ($file in $files) {
    $source = Join-Path $sourceRoot $file.Source
    $target = Join-Path $targetRoot $file.Target
    if (-not (Test-Path $source)) { throw "Falta el archivo fuente: $source" }
    if (Test-Path $target) {
        if (-not $Reemplazar) {
            Write-Warning "Ya existe '$target'; se conserva sin cambios. Usa -Reemplazar solo después de respaldarlo."
            $skipped++
            continue
        }
    }
    $targetDirectory = Split-Path -Parent $target
    New-Item -ItemType Directory -Force -Path $targetDirectory | Out-Null
    Copy-Item -LiteralPath $source -Destination $target -Force:$Reemplazar
    Write-Host "Copiado: $($file.Target)" -ForegroundColor Green
    $copied++
}

Write-Host "`nInstalador finalizado. Nuevos: $copied | Existentes conservados: $skipped" -ForegroundColor Cyan
