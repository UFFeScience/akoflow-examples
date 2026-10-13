import math, sys
import bpy
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:]
action=args[0]; out=args[1]
if action=='setup':
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.mesh.primitive_plane_add(size=20, location=(0,0,-1)); plane=bpy.context.object
 mat=bpy.data.materials.new('ground');mat.diffuse_color=(0.04,0.05,0.08,1);plane.data.materials.append(mat)
 for i,color in enumerate(((0.15,0.45,0.95,1),(0.95,0.35,0.15,1),(0.25,0.85,0.45,1))):
  bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,radius=.8,location=(-2+i*2,0,0));m=bpy.data.materials.new(f'm{i}');m.diffuse_color=color;bpy.context.object.data.materials.append(m)
 bpy.ops.object.light_add(type='AREA',location=(0,-2,6));bpy.context.object.data.energy=1200;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=5
 bpy.ops.object.camera_add(location=(0,-9,3));cam=bpy.context.object;cam.rotation_euler=(math.radians(72),0,0);bpy.context.scene.camera=cam
 s=bpy.context.scene;s.render.engine='BLENDER_EEVEE_NEXT';s.render.resolution_x=640;s.render.resolution_y=360;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.frame_start=1;s.frame_end=int(args[2]);s.render.fps=8
 bpy.ops.wm.save_as_mainfile(filepath=out+'/scene.blend')
else:
 parity=int(args[2]);count=int(args[3]);s=bpy.context.scene
 for frame in range(1,count+1):
  if frame%2!=parity:continue
  for i,obj in enumerate([x for x in s.objects if x.type=='MESH' and x.name!='Plane']):obj.location.y=math.sin(frame*.35+i)*.5;obj.rotation_euler.z=frame*.2
  s.frame_set(frame);s.render.filepath=f'{out}/frames/frame-{frame:04d}.png';bpy.ops.render.render(write_still=True)

