$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $python -m pip --disable-pip-version-check install nuitka ordered-set zstandard pefile ziglang==0.16.0
if ($LASTEXITCODE -ne 0) { throw 'Build dependencies failed' }
& $python tools\fetch_runtime.py
if ($LASTEXITCODE -ne 0) { throw 'Runtime assets are missing' }
$env:PATH = (Join-Path $PSScriptRoot '.venv\Lib\site-packages\ziglang') + ';' + $env:PATH
& $python tools\stage_python_libs.py
$env:LDFLAGS = '-L"' + (Join-Path $PSScriptRoot 'build\native-libs') + '"'
& $python -m nuitka --mode=onefile --experimental=force-dependencies-pefile --user-plugin=tools/nuitka_windows.py --zig --assume-yes-for-downloads --output-dir=build --output-filename=LANFALL.exe --windows-console-mode=disable --windows-icon-from-ico=game/assets/cache/lanfall.ico --jobs=4 --onefile-tempdir-spec='{CACHE_DIR}/LANFALL/0.5' --include-package=ursina --include-package=panda3d --include-package=simplepbr --include-package-data=panda3d --include-data-dir=game/assets/cache=game/assets/cache --noinclude-data-files=game/assets/cache/full_city.bam --include-data-dir=game/assets/audio=game/assets/audio --noinclude-data-files=game/assets/audio/kenney/** --include-data-dir=game/assets/licenses=game/assets/licenses --include-data-files=ASSET_CREDITS.md=ASSET_CREDITS.md --nofollow-import-to=pytest,unittest,tkinter,wx,direct.dist,direct.distributed,ursina.editor main.py
if ($LASTEXITCODE -ne 0) { throw 'Nuitka build failed; see the compiler output' }
$releaseExe = Join-Path $PSScriptRoot 'build\LANFALL.exe'
& (Join-Path $PSScriptRoot 'tools\verify_release.ps1') -Executable $releaseExe
Copy-Item -LiteralPath $releaseExe -Destination (Join-Path $PSScriptRoot 'LANFALL.exe') -Force
Write-Host 'Build verified: LANFALL.exe. Copy this single file to other Windows x64 PCs.'




