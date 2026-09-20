"""Build-only DLL import cache and explicit VC runtime inclusion.

Nuitka 4.2's PE reader reparses complete DLL resources for every dependency.
Only import directories are needed here; cache each read for this build.
"""
from functools import lru_cache
from pathlib import Path
from nuitka.plugins.PluginBase import NuitkaPluginBase

@lru_cache(maxsize=None)
def imported_dlls(filename):
    import pefile
    try:
        # Bytes own no mmap/file handle. Avoid PE.close(), which forces a full
        # gc.collect over the compiler's entire AST for every DLL.
        pe=pefile.PE(data=Path(filename).read_bytes(),fast_load=True)
        try:
            pe.parse_data_directories(directories=[1,13])
            return tuple(dict.fromkeys(item.dll.decode('utf8') for name in ('DIRECTORY_ENTRY_IMPORT','DIRECTORY_ENTRY_DELAY_IMPORT') for item in getattr(pe,name,())))
        finally:pe.__data__=b''
    except pefile.PEFormatError:return None

class LanfallWindowsBuild(NuitkaPluginBase):
    plugin_name='lanfall-windows'

    def __init__(self):
        from nuitka.freezer import DllDependenciesWin32PEFile
        DllDependenciesWin32PEFile.getPEFileUsedDllNames=imported_dlls

    def getExtraDlls(self,module):
        if module.getFullName()=='game':
            path=Path(__file__).resolve().parents[1]/'game/assets/runtime/concrt140.dll'
            yield self.makeDllEntryPoint(source_path=str(path),dest_path='concrt140.dll',module_name='game',package_name='game',reason='Panda3D concurrency runtime')
