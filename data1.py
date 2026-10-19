import bpy
import random
import os

# 1. Clean up old auto cameras/lights to avoid duplicates
for obj_to_clear in ["AutoCamera", "AutoSunLight"]:
    if obj_to_clear in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[obj_to_clear], do_unlink=True)

# Get your grass mesh ("Plane")
plane = bpy.data.objects.get("Plane")

# Explicitly find your star mesh object safely using the correct context path
star = None
for o in bpy.context.scene.objects:
    if o.type == 'MESH' and o.name != "Plane":
        star = o
        break

if not star:
    star = bpy.context.active_object

if plane and star:
    plane.hide_render = False
    star.hide_render = False

    # GIVE THE STAR A BRIGHT BLUE MATERIAL SO IT POPS OUT
    if star.type == 'MESH':
        mat = bpy.data.materials.get("StarBlueMat")
        if not mat:
            mat = bpy.data.materials.new(name="StarBlueMat")
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs['Base Color'].default_value = (0.0, 0.4, 1.0, 1.0)  # Bright Blue
        
        if star.data.materials:
            star.data.materials[0] = mat
        else:
            star.data.materials.append(mat)

    # Force render resolution to square (1080x1080) for a border-free fit
    render_res = 1080
    bpy.context.scene.render.resolution_x = render_res
    bpy.context.scene.render.resolution_y = render_res
    bpy.context.scene.render.resolution_percentage = 100

    # 2. FIND TRUE MESH CENTER, DIMENSIONS & HEIGHT BOUNDS
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_plane = plane.evaluated_get(depsgraph)
    mesh = eval_plane.to_mesh()
    
    world_verts = [plane.matrix_world @ v.co for v in mesh.vertices]
    eval_plane.to_mesh_clear()
    
    if world_verts:
        min_x = min(v.x for v in world_verts)
        max_x = max(v.x for v in world_verts)
        min_y = min(v.y for v in world_verts)
        max_y = max(v.y for v in world_verts)
        min_z = min(v.z for v in world_verts)
        max_z = max(v.z for v in world_verts)  # Highest peak of the grass/rocks
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        width = max_x - min_x
        length = max_y - min_y
    else:
        center_x, center_y = plane.location.x, plane.location.y
        max_z = plane.location.z
        width, length = plane.dimensions.x, plane.dimensions.y

    # 3. SETUP LIGHTING (Bright Sun over the center)
    sun = bpy.data.objects.new("AutoSunLight", bpy.data.lights.new(name="SunLight", type='SUN'))
    bpy.context.collection.objects.link(sun)
    sun.data.energy = 15.0
    sun.location = (center_x, center_y, max_z + 20)

    # 4. SETUP TOP-DOWN ORTHOGRAPHIC CAMERA (Tightly fitted)
    cam = bpy.data.objects.new("AutoCamera", bpy.data.cameras.new(name="TopCamera"))
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam  

    cam.data.type = 'ORTHO'
    ortho_scale = max(width, length) * 1.0  # Perfect fit
    cam.data.ortho_scale = ortho_scale

    # Position camera directly overhead
    cam.location = (center_x, center_y, max_z + 25)
    cam.rotation_euler = (0, 0, 0)

    # 5. RANDOMIZATION BOUNDARIES (Keep star well inside)
    max_x = (width / 2) * 0.75
    max_y = (length / 2) * 0.75

    # Get the star's dimensions to compute bounding box size for labels
    star_dim_x = star.dimensions.x
    star_dim_y = star.dimensions.y

    num_images = 50
    print("Starting clean top-down rendering with visible star and label files...")

    for i in range(num_images):
        # Randomize star position on X/Y and place it safely ON TOP of the highest ground point
        star.location.x = center_x + random.uniform(-max_x, max_x)
        star.location.y = center_y + random.uniform(-max_y, max_y)
        star.location.z = max_z + 0.5  # Sits visibly above the ground/rocks

        bpy.context.view_layer.update()

        base_filename = f"star_render_{i+1:02d}"
        img_filepath = bpy.path.abspath(f"//{base_filename}.png")
        txt_filepath = bpy.path.abspath(f"//{base_filename}.txt")
        
        bpy.context.scene.render.filepath = img_filepath

        # Render image and generate label with error protection for locked files
        try:
            bpy.ops.render.render(write_still=True)

            # --- GENERATE YOLO LABEL FILE ---
            cam_min_x = center_x - (ortho_scale / 2)
            cam_max_x = center_x + (ortho_scale / 2)
            cam_min_y = center_y - (ortho_scale / 2)
            cam_max_y = center_y + (ortho_scale / 2)

            s_cx = star.location.x
            s_cy = star.location.y

            x_center_norm = (s_cx - cam_min_x) / (cam_max_x - cam_min_x)
            y_center_norm = (cam_max_y - s_cy) / (cam_max_y - cam_min_y)
            w_norm = star_dim_x / (cam_max_x - cam_min_x)
            h_norm = star_dim_y / (cam_max_y - cam_min_y)

            x_center_norm = max(0.0, min(1.0, x_center_norm))
            y_center_norm = max(0.0, min(1.0, y_center_norm))
            w_norm = max(0.0, min(1.0, w_norm))
            h_norm = max(0.0, min(1.0, h_norm))

            with open(txt_filepath, "w") as f:
                f.write(f"0 {x_center_norm:.6f} {y_center_norm:.6f} {w_norm:.6f} {h_norm:.6f}\n")

            print(f"Rendered and labeled item {i+1} of {num_images}")
            
        except Exception as e:
            print(f"Warning on image {i+1}: Could not save file due to Windows file lock ({e}). Skipping to next...")

    print("Finished! All images and matching YOLO .txt label files processed.")
else:
    print("Error: Make sure your star mesh exists and your grass mesh is named 'Plane'.")
