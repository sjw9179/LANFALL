"""Convert downloaded CC0 props and licensed soldier parts to runtime GLB."""
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]/'game/assets'
SRC=ROOT/'source/presentation';OUT=ROOT/'items';OUT.mkdir(exist_ok=True)

def reset():bpy.ops.wm.read_factory_settings(use_empty=True)
def export(name,length):
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    coords=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    lo=Vector(tuple(min(v[i] for v in coords) for i in range(3)));hi=Vector(tuple(max(v[i] for v in coords) for i in range(3)))
    factor=length/max(hi-lo);offset=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for o in objects:
        mat=o.matrix_world.copy()
        for v in o.data.vertices:v.co=(mat@v.co-offset)*factor
        o.matrix_world.identity()
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/(name+'.glb')),export_format='GLB',use_selection=True,export_animations=False)

reset();bpy.ops.wm.obj_import(filepath=str(SRC/'firstaid/FirstAid.obj'));export('firstaid',.40)
export('medkit',.50)
for name,source,size in [('energy',SRC/'food/Models/GLB format/soda-can.glb',.22),
                         ('painkiller',SRC/'survival/Models/GLB format/bottle.glb',.22),
                         ('bandage',SRC/'survival/Models/GLB format/bedroll-packed.glb',.28),
                         ('ammo',ROOT/'weapons/kenney/Models/GLB format/clip-large.glb',.28)]:
    reset();bpy.ops.import_scene.gltf(filepath=str(source));export(name,size)
# Armor is the actual vest mesh of the downloaded operator, not a placeholder cube.
reset();bpy.ops.wm.obj_import(filepath=str(ROOT/'source/elite/elite/elite.obj'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
print('ARMOR SOURCES',[(o.name,tuple(o.dimensions)) for o in objects])
for o in objects:
    if not any(k in o.name.lower() for k in ('vest','bodyarmor','armour','armor')):bpy.data.objects.remove(o,do_unlink=True)
if not any(o.type=='MESH' for o in bpy.context.scene.objects):
    bpy.ops.wm.obj_import(filepath=str(ROOT/'source/elite/elite/elite.obj'))
    # Restrict to chest armor region when the OBJ uses a single unified body.
    import bmesh
    for o in [o for o in bpy.context.scene.objects if o.type=='MESH']:
        if 'MP5' in o.name:bpy.data.objects.remove(o,do_unlink=True);continue
        bm=bmesh.new();bm.from_mesh(o.data)
        coords=[v.co.z for v in bm.verts]
        if not coords:continue
        lo,hi=min(coords),max(coords);span=hi-lo
        bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.z<lo+span*.52 or v.co.z>lo+span*.79],context='VERTS')
        bm.to_mesh(o.data);bm.free()
export('armor1',.6);export('armor2',.65)
