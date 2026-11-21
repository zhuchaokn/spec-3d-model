"""Rebuild the confirmed thimble through the registry and scheduling engine."""
import os
import sys
import importlib

PROJ = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(os.path.dirname(PROJ)), "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import s3d
import engine
importlib.reload(s3d)
importlib.reload(engine)
import bpy

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
s3d.set_cm_units()
built = engine.run_model(os.path.join(PROJ, "model.json"), lib_dir=LIB)
print("BUILT", built)
print("SCENE_DUMP", s3d.scene_dump())
