[CmdletBinding()]
param(
    [string]$RepoRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    [switch]$OmitirAuditoria
)

$ErrorActionPreference = 'Stop'
$frontendDir = Join-Path $RepoRoot 'frontend'
if (-not (Test-Path (Join-Path $frontendDir 'package.json'))) {
    throw "No encuentro frontend\package.json en '$RepoRoot'."
}

$node = Get-Command node -ErrorAction SilentlyContinue
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $node) { throw 'Node.js no está disponible en PATH. Abre una terminal nueva y comprueba node -v.' }
if (-not $npm) { throw 'npm.cmd no está disponible. Comprueba la instalación de Node.js.' }

$installer = Join-Path $PSScriptRoot 'instalar_pruebas_ui.ps1'
& $installer -RepoRoot $RepoRoot
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    throw "Falló el instalador de pruebas UI (código $LASTEXITCODE)."
}

$resultsDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'resultado_ejecucion'
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null
$logPath = Join-Path $resultsDir ("frontend-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$transcriptStarted = $false

Push-Location $frontendDir
try {
    try {
        Start-Transcript -Path $logPath -Force | Out-Null
        $transcriptStarted = $true
    } catch {
        Write-Warning "No fue posible iniciar el registro de terminal: $($_.Exception.Message)"
    }

    Write-Host 'Instalando dependencias exactamente desde package-lock.json...' -ForegroundColor Cyan
    & npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw "npm ci falló (código $LASTEXITCODE)." }

    Write-Host "`n[1/5] ESLint" -ForegroundColor Yellow
    & npm.cmd run lint
    if ($LASTEXITCODE -ne 0) { throw "ESLint falló (código $LASTEXITCODE)." }

    Write-Host "`n[2/5] TypeScript" -ForegroundColor Yellow
    & npx.cmd tsc --noEmit
    if ($LASTEXITCODE -ne 0) { throw "La comprobación TypeScript falló (código $LASTEXITCODE)." }

    Write-Host "`n[3/5] Vitest + cobertura" -ForegroundColor Yellow
    & npm.cmd run test:coverage
    if ($LASTEXITCODE -ne 0) { throw "Vitest falló (código $LASTEXITCODE)." }

    Write-Host "`n[4/5] Build de producción" -ForegroundColor Yellow
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "El build falló (código $LASTEXITCODE)." }

    if (-not $OmitirAuditoria) {
        Write-Host "`n[5/5] Auditoría de dependencias de producción" -ForegroundColor Yellow
        & npm.cmd audit --omit=dev --audit-level=high
        if ($LASTEXITCODE -ne 0) { throw "npm audit encontró vulnerabilidades altas/críticas o no pudo completar la consulta (código $LASTEXITCODE)." }
    } else {
        Write-Host "`n[5/5] Auditoría omitida por parámetro." -ForegroundColor DarkYellow
    }

    Write-Host "`nFrontend: todas las verificaciones ejecutadas terminaron correctamente." -ForegroundColor Green
    Write-Host "Registro guardado en: $logPath" -ForegroundColor Green
} finally {
    if ($transcriptStarted) {
        try { Stop-Transcript | Out-Null } catch { }
    }
    Pop-Location
}
