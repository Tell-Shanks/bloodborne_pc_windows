param([string]$MsysRoot='C:\msys64')
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$sdk=Join-Path $repo 'gpu\third_party\dlss-sdk'
$work=Join-Path $repo 'out\dlss-bridge'
$output=Join-Path $repo 'dist\windows'
$vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$vs=& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'MSVC x64 Build Tools are required for the NGX bridge.' }
if (-not (Test-Path -LiteralPath (Join-Path $sdk 'nvsdk_ngx_s.lib'))) { throw 'Run tools/fetch_dlss_sdk.py first.' }
New-Item -ItemType Directory -Path $work,$output -Force | Out-Null
foreach($dir in @('vulkan','vk_video')) {
 Copy-Item -LiteralPath (Join-Path $MsysRoot "ucrt64\include\$dir") -Destination $work -Recurse -Force
}
$source=Join-Path $sdk 'dlss_bridge.cpp'
$library=Join-Path $sdk 'nvsdk_ngx_s.lib'
$dll=Join-Path $output 'bb-dlss-bridge.dll'
$vcvars=Join-Path $vs 'VC\Auxiliary\Build\vcvars64.bat'
$environmentLines=& cmd.exe /d /c "`"$vcvars`" >nul && set"
if ($LASTEXITCODE) { throw 'MSVC environment initialization failed' }
foreach($line in $environmentLines) {
 $separator=$line.IndexOf('=')
 if ($separator -gt 0) { [Environment]::SetEnvironmentVariable($line.Substring(0,$separator),$line.Substring($separator+1),'Process') }
}
Push-Location $work
try {
 & cl.exe /nologo /LD /MT /EHsc /std:c++17 /I $work /I $sdk $source $library /link "/OUT:$dll" advapi32.lib shell32.lib ole32.lib user32.lib version.lib
 if ($LASTEXITCODE) {throw 'DLSS bridge compilation failed'}
}
finally { Pop-Location }
Write-Host "Built $dll"
