import bpy,math,bmesh
from mathutils import Vector,Matrix
from pathlib import Path
r=Path(__file__).resolve().parents[1]/'game/assets'
bpy.ops.wm.open_mainfile(filepath=str(r/'source/arms/FPS ARMS RIG 1 test anim.blend'),load_ui=False,use_scripts=False)
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
for bone in rig.pose.bones:
    if bone.name.startswith('f_'):
        for c in list(bone.constraints):bone.constraints.remove(c)
        bone.rotation_mode='XYZ';bone.rotation_euler.x=math.radians(62 if '.01.' in bone.name else 75)
    elif bone.name.startswith('thumb.'):
        for c in list(bone.constraints):bone.constraints.remove(c)
        bone.rotation_mode='XYZ'
        bone.rotation_euler.x=math.radians(45)
        if '.01.' in bone.name:bone.rotation_euler.y=math.radians(35 if '.L' in bone.name else -35)
bpy.context.view_layer.update()
cam=bpy.context.scene.camera
print('CAM',cam.matrix_world,flush=True)
transform=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))@cam.matrix_world.inverted()
dg=bpy.context.evaluated_depsgraph_get()
mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(dg),depsgraph=dg)
mesh.transform(transform@obj.matrix_world)
hand=transform@(rig.matrix_world@rig.pose.bones['hand.R'].head)
left_hand=transform@(rig.matrix_world@rig.pose.bones['hand.L'].head)
scale=.067
left_indices={v.index for v in mesh.vertices if sum(g.weight for g in v.groups if '.L' in obj.vertex_groups[g.group].name)>.5}
for v in mesh.vertices:v.co=(v.co-(left_hand if v.index in left_indices else hand))*scale
for poly in mesh.polygons:poly.use_smooth=True
m=bpy.data.materials.new('skin');m.use_nodes=True
bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.78
tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(r/'source/arms/new_diff.png'))
m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
mesh.materials.clear();mesh.materials.append(m)
objects=[]
for name,is_left in [('arm_left',True),('arm_right',False)]:
    half=mesh.copy();bm=bmesh.new();bm.from_mesh(half)
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if (v.index in left_indices)!=is_left],context='VERTS')
    bm.to_mesh(half);bm.free()
    new=bpy.data.objects.new(name,half);bpy.context.collection.objects.link(new);objects.append(new)
bpy.ops.object.select_all(action='DESELECT')
for new in objects:new.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.gltf(filepath=str(r/'characters/arms.glb'),export_format='GLB',use_selection=True,export_animations=False)
