#!/usr/bin/env python3
"""
Generate a thick disk mesh (short cylinder) with proper UV mapping.
UV coordinates on top/bottom faces are planar (no radial "tree ring"
wrapping like OGRE's default cylinder caps).

Top face:    planar UV from center (0.5,0.5) outward
Bottom face: same planar UV (mirrored orientation)
Side wall:   wrapped UV (u around circumference, v along height)

Radius = 5.0m, Height = 0.2m, 64 segments.
"""
import math

radius = 5.0
height = 0.2
seg = 64

verts = []
uvs = []
normals = []
faces = []

def add_vertex(x, y, z, u, v, nx, ny, nz):
    idx = len(verts)
    verts.append((x, y, z))
    uvs.append((u, v))
    normals.append((nx, ny, nz))
    return idx

def uv_planar(x, y):
    """Map (x,y) in [-radius, radius] to UV in [0,1]"""
    return (0.5 + x / (2.0 * radius), 0.5 + y / (2.0 * radius))

# ============ TOP FACE (z = +height/2) ============
top_z = height / 2.0
# Center vertex
ctr = add_vertex(0.0, 0.0, top_z, 0.5, 0.5, 0.0, 0.0, 1.0)
top_ring = []
for i in range(seg):
    theta = 2.0 * math.pi * i / seg
    x = radius * math.cos(theta)
    y = radius * math.sin(theta)
    u, v = uv_planar(x, y)
    idx = add_vertex(x, y, top_z, u, v, 0.0, 0.0, 1.0)
    top_ring.append(idx)

for i in range(seg):
    i1 = top_ring[i]
    i2 = top_ring[(i + 1) % seg]
    faces.append((ctr, i1, i2))

# ============ BOTTOM FACE (z = -height/2) ============
bot_z = -height / 2.0
ctr_bot = add_vertex(0.0, 0.0, bot_z, 0.5, 0.5, 0.0, 0.0, -1.0)
bot_ring = []
for i in range(seg):
    theta = 2.0 * math.pi * i / seg
    x = radius * math.cos(theta)
    y = radius * math.sin(theta)
    u, v = uv_planar(x, y)
    # Flip winding for bottom face (face down)
    idx = add_vertex(x, y, bot_z, u, v, 0.0, 0.0, -1.0)
    bot_ring.append(idx)

for i in range(seg):
    i1 = bot_ring[i]
    i2 = bot_ring[(i + 1) % seg]
    # Winding reversed for downward normal
    faces.append((ctr_bot, i2, i1))

# ============ SIDE WALL ============
side_ring_top = []
side_ring_bot = []
for i in range(seg):
    theta = 2.0 * math.pi * i / seg
    x = radius * math.cos(theta)
    y = radius * math.sin(theta)
    nx = math.cos(theta)
    ny = math.sin(theta)
    nz = 0.0
    
    u = i / seg  # circumference
    idx_t = add_vertex(x, y, top_z, u, 1.0, nx, ny, nz)
    idx_b = add_vertex(x, y, bot_z, u, 0.0, nx, ny, nz)
    side_ring_top.append(idx_t)
    side_ring_bot.append(idx_b)

for i in range(seg):
    i1 = side_ring_bot[i]
    i2 = side_ring_bot[(i + 1) % seg]
    i3 = side_ring_top[(i + 1) % seg]
    i4 = side_ring_top[i]
    faces.append((i1, i2, i3))
    faces.append((i1, i3, i4))

# ============ WRITE OBJ ============
with open('/home/user/water02/meshes/disk_cylinder.obj', 'w') as f:
    f.write("# Thick disk cylinder mesh (extruded disk)\n")
    f.write("# Radius: {}m, Height: {}m, Segments: {}\n".format(radius, height, seg))
    f.write("# Planar UV on top/bottom faces - no tree-ring effect\n\n")
    
    for v in verts:
        f.write("v {} {} {}\n".format(v[0], v[1], v[2]))
    
    f.write("\n")
    for vt in uvs:
        f.write("vt {} {}\n".format(vt[0], vt[1]))
    
    f.write("\n")
    for vn in normals:
        f.write("vn {} {} {}\n".format(vn[0], vn[1], vn[2]))
    
    f.write("\n")
    for face in faces:
        f.write("f {0}/{0}/{0} {1}/{1}/{1} {2}/{2}/{2}\n".format(
            face[0] + 1, face[1] + 1, face[2] + 1
        ))

print("Disk cylinder mesh generated: {} vertices, {} faces".format(len(verts), len(faces)))
