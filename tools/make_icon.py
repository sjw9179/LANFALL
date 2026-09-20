from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1]
im=Image.new('RGBA',(256,256),(17,18,20,255));d=ImageDraw.Draw(im)
d.rounded_rectangle((12,12,243,243),radius=30,outline='#c7b386',width=5)
d.polygon([(52,61),(78,61),(78,164),(121,164),(121,190),(52,190)],fill='#f2f0e9')
d.polygon([(138,61),(209,61),(209,86),(164,86),(164,113),(201,113),(201,138),(164,138),(164,190),(138,190)],fill='#c7b386')
im.save(root/'game/assets/cache/lanfall.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
