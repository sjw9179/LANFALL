"""Copy source assets from the local standalone EXE cache; never downloads."""
import os
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
REQUIRED=('city.bam','collision.bam','operator.bam','arms.bam','pistol.bam',
          'rifle.bam','smg.bam','shotgun.bam','dmr.bam','sky.png','minimap.png',
          'lanfall.ico','item_ammo.bam','item_armor1.bam','item_armor2.bam',
          'item_bandage.bam','item_energy.bam','item_firstaid.bam',
          'item_medkit.bam','item_painkiller.bam')

def main():
    target=ROOT/'game/assets/cache'
    if all((target/name).is_file() for name in REQUIRED):
        print('Bundled runtime assets are ready.');return
    source=Path(os.environ.get('LOCALAPPDATA',''))/'LANFALL/0.5/game/assets/cache'
    if not all((source/name).is_file() for name in REQUIRED):
        raise SystemExit('Run the v0.5.0 LANFALL.exe release once, then retry. '
                         'Every asset is inside the EXE; no separate pack is needed.')
    target.mkdir(parents=True,exist_ok=True)
    for file in source.iterdir():
        if file.is_file() and not (target/file.name).exists():shutil.copy2(file,target/file.name)
    print('Copied assets from the local standalone game cache.')

if __name__=='__main__':main()
