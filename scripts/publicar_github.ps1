$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$logDir = Join-Path $projectRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'publicar_github.log'
Start-Transcript -Path $log -Force | Out-Null
try {
    $branch = (& git branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or $branch -ne 'main') { throw 'Se esperaba la rama main. No se publico.' }
    $remote = (& git remote get-url origin).Trim()
    if ($LASTEXITCODE -ne 0 -or $remote -ne 'https://github.com/vaurmeneta-22/P1-Grupo-6.git') {
        throw 'El remoto origin no coincide con el proyecto. No se publico.'
    }
    & git fetch origin
    if ($LASTEXITCODE -ne 0) { throw 'Fallo fetch. Revisa conexion y acceso a GitHub.' }
    $behind = (& git rev-list --count HEAD..origin/main).Trim()
    if ($LASTEXITCODE -ne 0 -or $behind -ne '0') {
        throw 'GitHub tiene cambios nuevos que deben integrarse antes del push. No se modificaron los commits.'
    }
    & git add -A
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron preparar los archivos.' }
    & git diff --cached --quiet
    $diffCode = $LASTEXITCODE
    if ($diffCode -eq 1) {
        & git --no-pager diff --cached --stat
        & git commit -m 'feat: agrega viga AR a escala real, resultados v4 y cierre de semana 6'
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el commit.' }
    } elseif ($diffCode -ne 0) {
        throw 'No se pudo revisar el indice de Git.'
    }
    & git push origin main
    if ($LASTEXITCODE -ne 0) { throw 'No se completo el push. El commit local se conserva.' }
    & git fetch origin
    if ($LASTEXITCODE -ne 0) { throw 'Push realizado, pero fallo la verificacion posterior.' }
    $local = (& git rev-parse HEAD).Trim()
    $published = (& git rev-parse origin/main).Trim()
    if ($local -ne $published) { throw 'La referencia remota no coincide con el commit local.' }
    Write-Host "PUSH VERIFICADO: $local" -ForegroundColor Green
    & git status --short
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    Stop-Transcript | Out-Null
}