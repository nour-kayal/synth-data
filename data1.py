import bpy
import random

# Get the active star object
obj = bpy.context.active_object
plane = bpy.data.objects.get("Plane")

if plane and obj:
    # 1. SETUP LIGHTING (Add a Sun light if one doesn't exist)
    sun = bpy.data.objects.get("AutoSunLight")
    if not sun:
        light_data = bpy.data.lights.new(name="SunLight", type='SUN')
        light_data.energy = 5.0  # Brightness
        sun = bpy.data.objects.new("AutoSunLight", light_data)
        bpy.context.collection.objects.link(sun)
    
    # Position the sun above the scene
    sun.location = (plane.location.x, plane.location.y, plane.location.z + 10)

    # 2. SETUP CAMERA (Add or position a top-down camera)
    cam = bpy.data.objects.get("AutoCamera")
    if not cam:
        cam_data = bpy.data.cameras.new(name="TopCamera")
        cam = bpy.data.objects.new("AutoCamera", cam_data)
        bpy.context.collection.objects.link(cam)
        bpy.context.scene.camera = cam  # Make it the active render camera

    # Position camera directly above the center of the plane, looking down
    cam.location = (plane.location.x, plane.location.y, plane.location.z + 15)
    cam.rotation_euler = (0, 0, 0)  # Pointing straight down

    # 3. GET PLANE BOUNDARIES
    width = plane.dimensions.x
    length = plane.dimensions.y
    max_x = (width / 2) * 0.85
    max_y = (length / 2) * 0.85

    num_images = 50
    print("Starting automated lighting, framing, and rendering...")

    for i in range(num_images):
        # Generate random coordinates
        random_x = random.uniform(-max_x, max_x)
        random_y = random.uniform(-max_y, max_y)

        # Move the star
        obj.location.x = plane.location.x + random_x
        obj.location.y = plane.location.y + random_y
        obj.location.z = plane.location.z

        # Update scene view
        bpy.context.view_layer.update()

        # Set render filepath
        filepath = bpy.path.abspath(f"//star_render_{i+1:02d}.png")
        bpy.context.scene.render.filepath = filepath

        # Render frame
        bpy.ops.render.render(write_still=True)
        print(f"Rendered and saved image {i+1} of {num_images}")

    print("Finished! All 50 bright, properly framed images are saved.")
else:
    print("Error: Make sure your star is selected and your plane is named 'Plane'.")