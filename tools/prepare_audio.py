"""Extract single shots from CC0 location recordings, normalize and fade tails."""
from pathlib import Path
import numpy as np
import soundfile as sf
ROOT=Path(__file__).resolve().parents[1]/'game/assets'
source=ROOT/'source/firearms/Prepared SFX Library'
files={'pistol':'1911/A_42P.wav','rifle':'AR-15/D_32P.wav','smg':'Carl Gustav M45/G_31P.wav','shotgun':'CD/H_21P.wav','dmr':'AK-47/C_28P.wav'}
for name,path in files.items():
    data,rate=sf.read(source/path,always_2d=True)
    envelope=np.max(np.abs(data),axis=1)
    hits=np.flatnonzero(envelope>envelope.max()*.25)
    start=max(0,int(hits[0]) - int(rate*.005)); data=data[start:start+int(rate*1.35)]
    data*=.88/max(.001,np.max(np.abs(data)))
    fade=min(int(rate*.3),len(data));data[-fade:]*=np.linspace(1,0,fade)[:,None]
    sf.write(ROOT/'audio'/f'{name}.ogg',data,rate,format='OGG',subtype='VORBIS')
    print(name,rate,len(data)/rate)
data,rate=sf.read(ROOT/'source/reload.wav'); sf.write(ROOT/'audio/reload.ogg',data,rate,format='OGG')
