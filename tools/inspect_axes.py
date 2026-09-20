import bpy
from pathlib import Path
from mathutils import Vector
r=Path(__file__).resolve().parents[1]/'game/assets/source'
for name in ('akm','m4'):
    if name=='akm':bpy.ops.wm.open_mainfile(filepath=str(r/'akm.blend'),load_ui=False,use_scripts=False)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(r/'m4a1/M4A1/M4A1.fbx'))
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        e=o.evaluated_get(dg); mesh=e.to_mesh();vs=[e.matrix_world@v.co for v in mesh.vertices]
        lo=[min(v[i] for v in vs) for i in range(3)];hi=[max(v[i] for v in vs) for i in range(3)]
        print(name,o.name,'LO',lo,'HI',hi,flush=True)
