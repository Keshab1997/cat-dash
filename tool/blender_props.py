#!/usr/bin/env python3
"""Optional asset generator: blender --background --python tool/blender_props.py -- --output Assets/Art/Generated/Crate.fbx
Requires Blender installed on the machine running this command. Never called by CI.
"""
import argparse
import sys
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    target=Path(args.output).absolute()
    if target.suffix.lower() not in {'.fbx','.glb'}: parser.error('Output must end in .fbx or .glb')
    if target.exists(): parser.error('Refusing to overwrite an existing asset')
    import bpy
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0.5))
    obj=bpy.context.object;obj.name='LowPolyCrate'
    bevel=obj.modifiers.new(name='SoftEdges',type='BEVEL');bevel.width=0.025;bevel.segments=1
    mat=bpy.data.materials.new('CrateWood');mat.diffuse_color=(0.35,0.18,0.07,1)
    obj.data.materials.append(mat)
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.suffix.lower()=='.fbx':
        bpy.ops.export_scene.fbx(filepath=str(target),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y')
    else:
        bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True)
    print('Generated original procedural crate; validate import scale/materials in Unity and register in docs/ASSETS.md.')
if __name__=='__main__': main()
