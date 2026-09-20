import bpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'game/assets/source'
for p in [*root.rglob('*.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(p),load_ui=False,use_scripts=False)
    print('\nASSET',str(p),flush=True)
    for o in bpy.data.objects:
        if o.type in ('MESH','ARMATURE'):
            print(o.name,o.type,tuple(round(x,3) for x in o.dimensions),tuple(round(x,3) for x in o.location),len(o.data.vertices) if o.type=='MESH' else len(o.data.bones),flush=True)
    for m in bpy.data.materials:
        print('MATERIAL',m.name,list(m.diffuse_color),[(n.type,n.name,n.image.name if n.type=='TEX_IMAGE' and n.image else '') for n in m.node_tree.nodes] if m.use_nodes else '',flush=True)
    print('IMAGES',[(i.name,i.size[:],bool(i.packed_file)) for i in bpy.data.images],flush=True)
