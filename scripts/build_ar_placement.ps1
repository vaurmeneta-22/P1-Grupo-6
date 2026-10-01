$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$unityProject = Join-Path $projectRoot 'Unity'
$unityExe = 'C:\Program Files\Unity\Hub\Editor\6000.6.0f1\Editor\Unity.exe'
$buildDir = Join-Path $unityProject 'Builds'
$buildLog = Join-Path $buildDir 'AR_Colocacion_v2_build.log'
$apk = Join-Path $buildDir 'P1_Grupo6_AR_Colocacion_v2.apk'
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
if (!(Test-Path -LiteralPath $unityExe)) { throw 'No se encontro Unity 6000.6.0f1.' }
# Release only the exact two background processes started by this build task.
# Start-time checks prevent terminating a different process if Windows reused a PID.
$stalledProcesses = @(
    @{ Id = 19812; Name = 'Unity'; Ticks = [long]639264527878388162 },
    @{ Id = 10028; Name = 'Unity.Licensing.Client'; Ticks = [long]639264526808840816 }
)
foreach ($entry in $stalledProcesses) {
    $process = Get-Process -Id $entry.Id -ErrorAction SilentlyContinue
    if ($null -ne $process -and $process.ProcessName -eq $entry.Name -and $process.StartTime.ToUniversalTime().Ticks -eq $entry.Ticks) {
        Stop-Process -Id $entry.Id -Force
        $process.WaitForExit(10000) | Out-Null
    }
}
Write-Host 'Compilando Viga AR v2. Puede tardar varios minutos.'
Write-Host "Registro: $buildLog"
$started = Get-Date
$job = Start-Process -FilePath $unityExe -ArgumentList @('-batchmode','-quit','-projectPath',('"'+$unityProject+'"'),'-buildTarget','Android','-executeMethod','ARPlacementSetup.BuildAndroid','-logFile',('"'+$buildLog+'"')) -WindowStyle Hidden -PassThru
$job.WaitForExit()
$job.Refresh()
$success = (Test-Path -LiteralPath $apk) -and ((Get-Item -LiteralPath $apk).LastWriteTime -gt $started) -and ((Get-Content -Raw -LiteralPath $buildLog) -match 'AR PLACEMENT BUILD: Succeeded')
if (!$success) {
    Write-Host 'La compilacion no termino correctamente. El registro contiene el motivo.' -ForegroundColor Red
    Get-Content -LiteralPath $buildLog -Tail 35
    exit 1
}
Write-Host "APK creado: $apk" -ForegroundColor Green
Get-FileHash -LiteralPath $apk -Algorithm SHA256
