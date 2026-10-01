$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$unityProject = Join-Path $projectRoot 'Unity'
$unityExe = 'C:\Program Files\Unity\Hub\Editor\6000.6.0f1\Editor\Unity.exe'
$buildDir = Join-Path $unityProject 'Builds'
$buildLog = Join-Path $buildDir 'AR_Diagramas_v3_build.log'
$apk = Join-Path $buildDir 'P1_Grupo6_AR_Diagramas_v3.apk'
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
if (!(Test-Path -LiteralPath $unityExe)) { throw 'No se encontro Unity 6000.6.0f1.' }
Write-Host 'Compilando Viga AR v3 con diagramas M/V. Puede tardar varios minutos.'
Write-Host "Registro: $buildLog"
$started = Get-Date
$job = Start-Process -FilePath $unityExe -ArgumentList @('-batchmode','-quit','-projectPath',('"'+$unityProject+'"'),'-buildTarget','Android','-executeMethod','ARPlacementSetup.BuildAndroid','-logFile',('"'+$buildLog+'"')) -WindowStyle Hidden -PassThru
$job.WaitForExit()
$success = (Test-Path -LiteralPath $apk) -and ((Get-Item -LiteralPath $apk).LastWriteTime -gt $started) -and ((Get-Content -Raw -LiteralPath $buildLog) -match 'AR PLACEMENT BUILD: Succeeded')
if (!$success) {
    Write-Host 'La compilacion no termino correctamente. Revisa el registro.' -ForegroundColor Red
    Get-Content -LiteralPath $buildLog -Tail 35
    exit 1
}
Write-Host "APK creado: $apk" -ForegroundColor Green
Get-FileHash -LiteralPath $apk -Algorithm SHA256
