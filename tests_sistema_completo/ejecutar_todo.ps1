[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$SuiteRoot = $PSScriptRoot
$RepoRoot = Split-Path -Parent $SuiteRoot

Write-Host ''
Write-Host '============================================' -ForegroundColor Cyan
Write-Host ' SUITE COMPLETA - SISTEMA DE ITINERARIOS' -ForegroundColor Cyan
Write-Host '============================================' -ForegroundColor Cyan
Write-Host "Repositorio: $RepoRoot"

$backend = Join-Path $SuiteRoot 'backend\ejecutar_backend.ps1'
$frontend = Join-Path $SuiteRoot 'frontend\ejecutar_frontend.ps1'

Write-Host "`n[1/2] Ejecutando pruebas de backend..." -ForegroundColor Yellow
& $backend -RepoRoot $RepoRoot
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    throw "Falló la ejecución de pruebas backend (código $LASTEXITCODE)."
}

Write-Host "`n[2/2] Instalando pruebas UI complementarias si faltan y ejecutando frontend..." -ForegroundColor Yellow
& $frontend -RepoRoot $RepoRoot
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    throw "Falló la ejecución de pruebas frontend (código $LASTEXITCODE)."
}

Write-Host "`nSUITE COMPLETADA: backend y frontend terminaron sin errores reportados." -ForegroundColor Green
Write-Host 'Revisa los resúmenes de pytest y Vitest mostrados arriba.'
