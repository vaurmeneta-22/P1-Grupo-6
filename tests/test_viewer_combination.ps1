param([string]$Map = 'Unity/Assets/StreamingAssets/analysis_map.json')
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
# Only the coordinate container is stubbed; the parser and combination engine
# below are the production C# sources used by Unity.
$vector = @'
namespace UnityEngine {
    public struct Vector3 {
        float x, y, z;
        public Vector3(float a, float b, float c) { x=a; y=b; z=c; }
        public float this[int i] { get { return i==0 ? x : i==1 ? y : z; } }
    }
}
'@
$sources = @(
    $vector,
    (Get-Content Unity/Assets/Scripts/MiniJson.cs -Raw),
    (Get-Content Unity/Assets/Scripts/AnalysisMap.cs -Raw),
    (Get-Content Unity/Assets/Scripts/AnalysisMapCombination.cs -Raw),
    (Get-Content tests/ViewerCombinationChecks.cs -Raw)
)
Add-Type -TypeDefinition (($sources | ForEach-Object { "namespace ViewerTest {`n$_`n}" }) -join "`n")
[ViewerTest.ViewerCombinationChecks]::Run((Join-Path $repo $Map))
