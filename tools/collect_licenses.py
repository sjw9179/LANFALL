"""Keep runtime dependency notices with the packaged asset credits."""
from importlib.metadata import distribution,PackageNotFoundError
from pathlib import Path
import shutil,sys
root=Path(__file__).resolve().parents[1]/'game/assets/licenses/software'
for package in ('ursina','panda3d','panda3d-gltf','panda3d-simplepbr','msgpack','pillow','numpy','pyperclip','screeninfo','typing_extensions','sswg'):
    try:dist=distribution(package)
    except PackageNotFoundError:continue
    for entry in dist.files or []:
        if any(word in entry.name.lower() for word in ('license','copying','notice')) and '.dist-info' in str(entry):
            source=Path(dist.locate_file(entry))
            if source.is_file():
                target=root/package/entry.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists():
    root.mkdir(parents=True,exist_ok=True);shutil.copyfile(python_license,root/'Python-LICENSE.txt')
