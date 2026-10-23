"""Runs inside Blender itself:
    blender --background <file.blend> --python blender_export.py -- <out_path> <target_ext>

Blender opens the .blend file first (because it's passed before --python),
then this script exports the loaded scene to the requested format.
Handles both the old and new Blender operator names so it works across
Blender 2.9x/3.x and 4.x.
"""
import sys
import bpy

argv = sys.argv
argv = argv[argv.index("--") + 1:]
out_path, target_ext = argv[0], argv[1].lower()

if target_ext == "obj":
    if hasattr(bpy.ops.wm, "obj_export"):
        bpy.ops.wm.obj_export(filepath=out_path)
    else:
        bpy.ops.export_scene.obj(filepath=out_path)
elif target_ext == "fbx":
    bpy.ops.export_scene.fbx(filepath=out_path)
elif target_ext in ("gltf", "glb"):
    bpy.ops.export_scene.gltf(filepath=out_path)
elif target_ext == "stl":
    if hasattr(bpy.ops.wm, "stl_export"):
        bpy.ops.wm.stl_export(filepath=out_path)
    else:
        bpy.ops.export_scene.stl(filepath=out_path)
else:
    raise SystemExit(f"Unsupported blender export target: {target_ext}")
