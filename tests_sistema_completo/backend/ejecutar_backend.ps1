[CmdletBinding()]
param(
    [string]$RepoRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
)

$ErrorActionPreference = 'Stop'

function Invoke-DockerChecked {
    param([string[]]$Arguments, [string]$Description)
    & docker @Arguments
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        throw "$Description falló (código $code)."
    }
}

if (-not (Test-Path (Join-Path $RepoRoot 'docker-compose.yml'))) {
    throw "No encuentro docker-compose.yml en '$RepoRoot'. Ejecuta este script desde la carpeta del repositorio o pasa -RepoRoot."
}

Write-Host 'Comprobando Docker Engine...' -ForegroundColor Cyan
& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Docker Engine no está disponible. Abre Docker Desktop y espera a que indique que está en ejecución.'
}

$tag = "$PID"
$network = "itinerarios-tests-net-$tag"
$dbContainer = "itinerarios-tests-postgres-$tag"
$resultsDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'resultado_ejecucion'
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null
$logPath = Join-Path $resultsDir ("backend-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$transcriptStarted = $false
$failedServices = New-Object System.Collections.Generic.List[string]

$services = @(
    @{ Name = 'airport-service'; Database = 'airport_test' },
    @{ Name = 'itinerary-service'; Database = 'itinerary_test' },
    @{ Name = 'auth-stub'; Database = 'auth_test' },
    @{ Name = 'notification-function'; Database = 'notification_test' }
)

try {
    try {
        Start-Transcript -Path $logPath -Force | Out-Null
        $transcriptStarted = $true
    } catch {
        Write-Warning "No fue posible iniciar el registro de terminal: $($_.Exception.Message)"
    }

    Write-Host "Creando PostgreSQL 16 temporal para las pruebas..." -ForegroundColor Cyan
    Invoke-DockerChecked -Arguments @('network', 'create', $network) -Description 'Creación de red Docker'
    Invoke-DockerChecked -Arguments @(
        'run', '-d', '--name', $dbContainer,
        '--network', $network, '--network-alias', 'test-postgres',
        '-e', 'POSTGRES_USER=ci',
        '-e', 'POSTGRES_PASSWORD=ci-only-password',
        '-e', 'POSTGRES_DB=ci_test',
        'postgres:16-alpine'
    ) -Description 'Inicio del PostgreSQL temporal'

    $ready = $false
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        & docker exec $dbContainer pg_isready -U ci -d ci_test *> $null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) {
        throw 'PostgreSQL no quedó listo en 120 segundos. Revisa Docker Desktop y los registros del contenedor.'
    }

    foreach ($service in $services) {
        $serviceDir = Join-Path $RepoRoot ("services\" + $service.Name)
        if (-not (Test-Path (Join-Path $serviceDir 'requirements-dev.txt'))) {
            throw "No se encontró requirements-dev.txt para $($service.Name). La estructura del repositorio puede haber cambiado."
        }
        if (-not (Test-Path (Join-Path $serviceDir 'tests'))) {
            throw "No se encontró la carpeta tests de $($service.Name)."
        }
        Invoke-DockerChecked -Arguments @('exec', $dbContainer, 'createdb', '-U', 'ci', $service.Database) -Description "Creación de base $($service.Database)"
    }

    $repoMount = ($RepoRoot -replace '\\', '/') + ':/workspace'
    foreach ($service in $services) {
        Write-Host "`n--------------------------------------------" -ForegroundColor DarkCyan
        Write-Host "BACKEND: $($service.Name)" -ForegroundColor Cyan
        Write-Host 'Python 3.11 + pytest + PostgreSQL 16 (contenedores temporales)' -ForegroundColor Gray

        $workdir = "/workspace/services/$($service.Name)"
        $databaseUrl = "postgresql://ci:ci-only-password@test-postgres:5432/$($service.Database)"
        $pytestCommand = 'python -m pip install --disable-pip-version-check --no-cache-dir -r requirements-dev.txt && python -m pytest tests -v --cov --cov-config=.coveragerc --cov-report=term-missing:skip-covered'
        $dockerArgs = @(
            'run', '--rm', '--network', $network,
            '-v', $repoMount,
            '-w', $workdir,
            '-e', "TEST_DATABASE_URL=$databaseUrl",
            'python:3.11-slim',
            'sh', '-lc', $pytestCommand
        )
        & docker @dockerArgs
        $testCode = $LASTEXITCODE
        if ($testCode -ne 0) {
            $failedServices.Add($service.Name)
            Write-Host "FALLÓ: $($service.Name) (código $testCode)" -ForegroundColor Red
        } else {
            Write-Host "APROBADO: $($service.Name)" -ForegroundColor Green
        }
    }

    Write-Host "`nResumen backend:" -ForegroundColor Cyan
    if ($failedServices.Count -eq 0) {
        Write-Host 'Los cuatro servicios finalizaron sin errores reportados.' -ForegroundColor Green
    } else {
        Write-Host ('Servicios con error: ' + ($failedServices -join ', ')) -ForegroundColor Red
    }
} finally {
    Write-Host "`nLimpiando únicamente los recursos Docker temporales de esta ejecución..." -ForegroundColor DarkGray
    & docker rm -f $dbContainer *> $null
    & docker network rm $network *> $null
    if ($transcriptStarted) {
        try { Stop-Transcript | Out-Null } catch { }
    }
}

if ($failedServices.Count -gt 0) {
    throw ('Fallaron las pruebas de backend en: ' + ($failedServices -join ', ') + ". Registro: $logPath")
}
Write-Host "Registro guardado en: $logPath" -ForegroundColor Green
