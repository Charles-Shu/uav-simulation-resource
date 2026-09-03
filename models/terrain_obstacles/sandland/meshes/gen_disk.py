#!/usr/bin/env python3
"""
Generate a flat circular disk mesh (OBJ format) with proper UV mapping.
The UV coordinates map the 2D texture directly onto the disk surface.
Radius = 5.0 meters, tessellated into 64 segments for smooth appearance.
"""
import math

radius = 5.0
segments = 64

vertices = []
uvs = []
normals = []
faces = []

# Center vertex
vertices.append((0.0, 0.0, 0.0))
uvs.append((0.5, 0.5))
normals.append((0.0, 0.0, 1.0))

# Edge vertices
for i in range(segments):
    theta = 2.0 * math.pi * i / segments
    x = radius * math.cos(theta)
    y = radius * math.sin(theta)
    vertices.append((x, y, 0.0))
    # UV: map from [-radius, radius] to [0, 1]
    u = 0.5 + x / (2.0 * radius)
    v = 0.5 + y / (2.0 * radius)
    uvs.append((u, v))
    normals.append((0.0, 0.0, 1.0))

# Faces (triangles): center + two consecutive edge points
for i in range(segments):
    i1 = i + 1
    i2 = (i + 1) % segments + 1
    faces.append((0, i1, i2))

# Write OBJ file
with open('/home/user/sandland/meshes/disk.obj', 'w') as f:
    f.write("# Flat circular disk mesh\n")
    f.write("# Radius: {}m, Segments: {}\n".format(radius, segments))
    f.write("# Generated for Sandland model\n\n")
    
    for v in vertices:
        f.write("v {} {} {}\n".format(v[0], v[1], v[2]))
    
    f.write("\n")
    for vt in uvs:
        f.write("vt {} {}\n".format(vt[0], vt[1]))
    
    f.write("\n")
    for vn in normals:
        f.write("vn {} {} {}\n".format(vn[0], vn[1], vn[2]))
    
    f.write("\n")
    for face in faces:
        # OBJ format: f v1/vt1/vn1 v2/vt2/vn2 v3/vt3/vn3
        f.write("f {0}/{0}/{0} {1}/{1}/{1} {2}/{2}/{2}\n".format(
            face[0] + 1, face[1] + 1, face[2] + 1
        ))

print("Disk mesh generated: {} vertices, {} faces".format(len(vertices), len(faces)))
