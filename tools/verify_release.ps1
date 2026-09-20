param([string]$Executable = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Executable) { $Executable = Join-Path $projectRoot 'build\LANFALL.exe' }
$testFolder = Join-Path $projectRoot 'standalone-test'
New-Item -ItemType Directory -Force -Path $testFolder | Out-Null
$testExe = Join-Path $testFolder 'LANFALL.exe'
Copy-Item -LiteralPath $Executable -Destination $testExe -Force
$cacheFolder = Join-Path $env:LOCALAPPDATA 'LANFALL\0.5'
$began = [DateTime]::UtcNow
$info = New-Object System.Diagnostics.ProcessStartInfo
$info.FileName = $testExe
$info.Arguments = '--offscreen --smoke 41 --presentation-test --bots 3 --port 29749'
$info.WorkingDirectory = $testFolder
$info.UseShellExecute = $false
$info.CreateNoWindow = $true
$info.EnvironmentVariables['PATH'] = "$env:SystemRoot\System32;$env:SystemRoot"
foreach ($key in @('PYTHONHOME','PYTHONPATH','VIRTUAL_ENV')) { $info.EnvironmentVariables.Remove($key) }
$process = [System.Diagnostics.Process]::Start($info)
Write-Host "Testing isolated executable, PID $($process.Id)"
$loaded = @()
while (-not $process.WaitForExit(1000)) {
    foreach ($candidate in (Get-Process LANFALL -ErrorAction SilentlyContinue)) {
        try {
            if ($candidate.Path.StartsWith($cacheFolder)) {
                $loaded += @($candidate.Modules | Where-Object { $_.ModuleName -match 'python|panda|\.pyd$' } | Select-Object -ExpandProperty FileName)
            }
        } catch { }
    }
    if (([DateTime]::UtcNow - $began).TotalSeconds -gt 150) {
        Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $process.Id } | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
        $process.Kill()
        throw 'Standalone test timed out'
    }
}
if ($process.ExitCode -ne 0) {
    $report = Join-Path $env:USERPROFILE '.lanfall\error.log'
    if (Test-Path $report) { Get-Content -LiteralPath $report -Encoding UTF8 }
    throw "Standalone exit code: $($process.ExitCode)"
}
$resultPath = Join-Path $cacheFolder 'logs\smoke.json'
if (-not (Test-Path $resultPath) -or (Get-Item $resultPath).LastWriteTimeUtc -lt $began) { throw 'No fresh smoke result from packaged game' }
$result = Get-Content -Raw -Encoding UTF8 $resultPath | ConvertFrom-Json
if (-not $result.playing -or -not $result.pause_menu_cleaned -or -not $result.deployment_ready -or $result.players -ne 4 -or 'medical-verified' -notin $result.presentation_checks) { throw 'Packaged game smoke assertions failed' }
$loaded = @($loaded | Sort-Object -Unique)
if (-not $loaded.Count -or @($loaded | Where-Object { -not $_.StartsWith($cacheFolder) }).Count) { throw 'A runtime library was not loaded from the standalone cache' }
$verification = [ordered]@{ executable=$testExe; sha256=(Get-FileHash $testExe -Algorithm SHA256).Hash; source_free=$true; python_paths_removed=$true; bundled_modules=$loaded; smoke=$result }
$verification | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 (Join-Path $projectRoot 'logs\release-check.json')
Get-ChildItem -LiteralPath (Join-Path $cacheFolder 'logs') -Filter '*.png' | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $projectRoot ('logs\release-'+$_.Name)) -Force }
Write-Host 'PASS: one executable, bundled runtime, lobby/game/inventory/optic/map/leave checked.'
