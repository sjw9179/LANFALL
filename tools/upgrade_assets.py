"""Run inside Blender: convert licensed source assets into normalized GLBs."""
import bpy,math
from mathutils import Matrix,Vector
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'game/assets'
SRC=ROOT/'source'

def material(name,tint=(.11,.13,.14,1),texture=None,metal=.65):
    m=bpy.data.materials.new(name); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=tint
    bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=.42
    if texture:
        node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(texture),check_existing=True)
        m.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color'])
    return m

def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.hide_viewport=False;o.hide_render=False;o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]

def bake_meshes(objects,transform,length,axis=1):
    bpy.context.view_layer.update()
    result=[];dg=bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(dg),depsgraph=dg)
        mesh.transform(transform@obj.evaluated_get(dg).matrix_world)
        n=bpy.data.objects.new(obj.name+'_game',mesh);bpy.context.collection.objects.link(n);result.append(n)
    coords=[v.co for o in result for v in o.data.vertices]
    lo=Vector([min(v[i] for v in coords) for i in range(3)]); hi=Vector([max(v[i] for v in coords) for i in range(3)])
    scale=length/(hi[axis]-lo[axis])
    shift=Vector(((lo.x+hi.x)/2,lo.y,hi.z))
    if axis==2:shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for o in result:
        for v in o.data.vertices:v.co=(v.co-shift)*scale
        for poly in o.data.polygons:poly.use_smooth=True
    select(result);return result

def export(name,objects,folder='weapons'):
    select(objects)
    bpy.ops.export_scene.gltf(filepath=str(ROOT/folder/f'{name}.glb'),export_format='GLB',use_selection=True,export_animations=False,export_yup=True)
    print('EXPORTED',name,flush=True)

def weapon(name,path,transform,length,objects_filter=None,texture=None):
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and len(o.data.vertices)>0 and (not objects_filter or objects_filter(o))]
    if name in ('pistol','smg','shotgun'):
        m=material(name+'_tactical',texture=texture,metal=.6 if name!='shotgun' else .4)
        for o in objects:o.data.materials.clear();o.data.materials.append(m)
    if name=='dmr':
        # Retain the original weathered AKM PBR material. DMR is a tuned long-range variant.
        pass
    objects=bake_meshes(objects,transform,length)
    export(name,objects)

z90=Matrix.Rotation(math.pi/2,4,'Z')
weapon('dmr',SRC/'akm.blend',Matrix.Identity(4),1.0)
weapon('smg',SRC/'mp7.blend',z90,.53,
       lambda o:o.name in ['Cube','Cube.001','Cube.002','Cube.003','Cube.004','Cube.005','Cube.006','Cube.007','Cylinder','Cylinder.002','Cylinder.012'])
weapon('shotgun',SRC/'shotgun.blend',z90,1.05,lambda o:o.name!='Cube.003')
pistol_rot=Matrix(((0,0,-1,0),(-1,0,0,0),(0,1,0,0),(0,0,0,1)))
weapon('pistol',SRC/'pistol/pistol.blend',pistol_rot,.28,texture=SRC/'pistol/diffuse.png')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(SRC/'m4a1/M4A1/M4A1.fbx'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
print('M4 OBJECTS',[(o.name,tuple(o.dimensions)) for o in objects],flush=True)
m=material('M4A1_PBR',texture=SRC/'m4a1/M4A1/M4A1_Base_Color.png',metal=.7)
for o in objects:o.data.materials.clear();o.data.materials.append(m)
# FBX is lengthwise Y, Z up. The normalized output points along positive Y.
coords=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
extents=[max(v[i] for v in coords)-min(v[i] for v in coords) for i in range(3)]
transform=z90 if extents[0]>extents[1] else Matrix.Identity(4)
objects=bake_meshes(objects,transform,.85);export('rifle',objects)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=str(SRC/'elite/elite/elite.obj'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('MP5')]
print('ELITE',[(o.name,tuple(o.dimensions)) for o in objects],flush=True)
objects=bake_meshes(objects,Matrix.Identity(4),1.78,axis=2)
# Relax the T-pose into a combat-ready stance, then add a small lower-body rig.
for o in objects:
    for v in o.data.vertices:
        x,y,z=v.co
        if z>1.17 and abs(x)>.28:
            shoulder=Vector((.25 if x>0 else -.25,0,1.43))
            angle=(1 if x>0 else -1)*math.radians(62)
            v.co=shoulder+Matrix.Rotation(angle,3,'Y')@(v.co-shoulder)
            v.co.y+=max(0,abs(x)-.25)*.45
for o in objects:
    for m in o.data.materials:
        if m and m.use_nodes:
            bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
            if bs:bs.inputs['Roughness'].default_value=.85;bs.inputs['Metallic'].default_value=.05
bpy.ops.object.select_all(action='DESELECT')
arm=bpy.data.armatures.new('operator_rig'); rig=bpy.data.objects.new('operator_rig',arm);bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
root=arm.edit_bones.new('root');root.head=(0,0,.88);root.tail=(0,0,1.45)
for name,x in [('leg_left',.115),('leg_right',-.115)]:
    bone=arm.edit_bones.new(name);bone.head=(x,0,.86);bone.tail=(x,0,.1);bone.parent=root
bpy.ops.object.mode_set(mode='OBJECT')
for o in objects:
    for name in ('root','leg_left','leg_right'):o.vertex_groups.new(name=name)
    for v in o.data.vertices:
        name=('leg_left' if v.co.x>0 else 'leg_right') if v.co.z<.85 else 'root'
        o.vertex_groups[name].add([v.index],1,'REPLACE')
    modifier=o.modifiers.new('operator_skin','ARMATURE');modifier.object=rig;o.parent=rig
select(objects+[rig])
bpy.ops.export_scene.gltf(filepath=str(ROOT/'characters/operator.glb'),export_format='GLB',use_selection=True,export_animations=False)

# Equirectangular sky texture, derived from the licensed HDR without inventing detail.
img=bpy.data.images.load(str(SRC/'sky.hdr'));_ = img.pixels[0]
img.save_render(str(ROOT/'cache/sky.png'))
