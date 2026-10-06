$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$unityExe = 'C:\Program Files\Unity\Hub\Editor\6000.6.0f1\Editor\Unity.exe'
$unityProject = Join-Path $projectRoot 'Unity'
$buildDir = Join-Path $unityProject 'Builds'
$buildLog = Join-Path $buildDir 'AR_VR_v11_build.log'
$apk = Join-Path $buildDir 'P1_Grupo6_AR_VR_v11.apk'
if (!(Test-Path -LiteralPath $unityExe)) { throw 'No se encontró Unity 6000.6.0f1.' }
if (Get-Process Unity -ErrorAction SilentlyContinue) { throw 'Cierra el editor Unity antes de compilar en batch.' }
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
Write-Host 'Compilando la app AR + Google Cardboard VR de los pisos 1 a 4.'
Write-Host "Registro: $buildLog"
$started = Get-Date
$job = Start-Process -FilePath $unityExe -ArgumentList @('-batchmode','-quit','-projectPath',('"'+$unityProject+'"'),'-buildTarget','Android','-executeMethod','VRMobileSetup.BuildAndroid','-logFile',('"'+$buildLog+'"')) -WindowStyle Hidden -PassThru
$job.WaitForExit()
$success = (Test-Path -LiteralPath $apk) -and ((Get-Item -LiteralPath $apk).LastWriteTime -gt $started) -and ((Get-Content -Raw -LiteralPath $buildLog) -match 'H1 MOBILE BUILD: Succeeded')
if (!$success) {
    Get-Content -LiteralPath $buildLog -Tail 40
    throw 'No se generó un APK nuevo aprobado. Revisa el registro.'
}
Write-Host "APK creado: $apk" -ForegroundColor Green
Get-FileHash -LiteralPath $apk -Algorithm SHA256
