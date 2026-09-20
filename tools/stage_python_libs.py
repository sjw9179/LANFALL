"""Native linkers cannot traverse MS Store Python's protected libs directory."""
from pathlib import Path
import shutil,sys
target=Path(__file__).resolve().parents[1]/'build/native-libs'
target.mkdir(parents=True,exist_ok=True)
for source in (Path(sys.base_prefix)/'libs').glob('python*.lib'):
    shutil.copyfile(source,target/source.name)
