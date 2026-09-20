"""Bake the supplied city to spatially batched BAM files; preserve source GLB."""
from pathlib import Path
import json
import time
from panda3d.core import *

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'game/assets'

def prepare():
    started=time.perf_counter()
    loadPrcFileData('', 'coordinate-system y-up-left\ntextures-power-2 none\ntexture-max-dimension 4096')
    source=ASSETS/'cache/full_city.bam'
    if source.exists():
        raw=NodePath(Loader.getGlobalPtr().loadSync(Filename.fromOsSpecific(str(source))))
        conversion=Mat4.convertMat(CS_zup_right, CS_yup_left)
    else:
        import gltf
        raw=NodePath(gltf.load_model(str(ASSETS/'maps/drive_city_original.glb')))
        conversion=Mat4.identMat()
    visual=NodePath('Drive City / South District')
    collision=NodePath('static_collision')
    cells={}; count=0; tris=0
    for n in raw.findAllMatches('**/+GeomNode'):
        mat=n.getMat(raw)*conversion*Mat4.scaleMat(100)
        bounds=n.getTightBounds(n)
        if not bounds: continue
        a,b=bounds
        corners=[mat.xformPoint(Point3(x,y,z)) for x in (a.x,b.x) for y in (a.y,b.y) for z in (a.z,b.z)]
        lo=[min(p[i] for p in corners) for i in range(3)]
        hi=[max(p[i] for p in corners) for i in range(3)]
        if lo[0]>220 or hi[0]<-220 or lo[2]>220 or hi[2]<-220: continue
        name=n.getName().lower()
        if 'collider' in name:
            c=n.copyTo(collision); c.setMat(mat); c.clearTexture(); c.clearMaterial()
            continue
        # Drop tiny decor; keep all architecture, roads and terrain.
        if max(hi[i]-lo[i] for i in range(3))<.35: continue
        key=(int((lo[0]+hi[0])/2//64),int((lo[2]+hi[2])/2//64))
        cell=cells.setdefault(key, visual.attachNewNode('sector_%d_%d'%key))
        c=n.copyTo(cell); c.setMat(mat)
        count+=1
        tris+=sum(n.node().getGeom(i).getNumPrimitives() for i in range(n.node().getNumGeoms()))
        if not any(v in name for v in ('vegetation','bush','tree','grass','water','sea','ocean')):
            c=n.copyTo(collision); c.setMat(mat); c.clearTexture(); c.clearMaterial()
    for cell in cells.values(): cell.flattenStrong()
    visual.setTwoSided(True)
    # Retain glTF material stages for the physically based renderer.
    for n in visual.findAllMatches('**/+GeomNode'):
        for i in range(n.node().getNumGeoms()):
            state=n.node().getGeomState(i)
            material=state.getAttrib(MaterialAttrib)
            if material and material.getMaterial():
                mat=Material(material.getMaterial()); mat.setMetallic(.02); mat.setRoughness(.88)
                n.node().setGeomState(i,state.setAttrib(MaterialAttrib.make(mat)))
    # Store textures inside BAM to make the game portable.
    for tex in visual.findAllTextures():
        tex.setAnisotropicDegree(8)
        if tex.getXSize()>4096 or tex.getYSize()>4096:
            img=PNMImage()
            if tex.store(img):
                small=PNMImage(min(4096,img.getXSize()),min(4096,img.getYSize()),img.getNumChannels())
                small.quickFilterFrom(img); tex.load(small)
    loadPrcFileData('', 'bam-texture-mode rawdata')
    visual.writeBamFile(Filename.fromOsSpecific(str(ASSETS/'cache/city.bam')))
    collision.flattenStrong()
    # Driving-map facades are often single planes. Preserve both contact faces
    # for capsule sweeps, including movement from the rear of a wall.
    for n in collision.findAllMatches('**/+GeomNode'):
        node=n.node()
        for i in range(node.getNumGeoms()):
            back=node.getGeom(i).makeCopy();back.reverseInPlace()
            node.addGeom(back,node.getGeomState(i))
    collision.writeBamFile(Filename.fromOsSpecific(str(ASSETS/'cache/collision.bam')))
    cfg={'id':'drive_city','name':'DRIVE CITY','subtitle':'SOUTH DISTRICT','radius':185,'extent':210,'center':[0,0],
         'source_nodes':count,'batches':visual.findAllMatches('**/+GeomNode').getNumPaths(),'seconds':round(time.perf_counter()-started,2)}
    (ASSETS/'cache/city.json').write_text(json.dumps(cfg,indent=2),encoding='utf8')
    print(cfg,flush=True)

if __name__=='__main__': prepare()
