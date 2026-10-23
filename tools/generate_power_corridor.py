#!/usr/bin/env python3
"""Generate original static lattice towers and sagging conductors (metres).

MIT, 2026 UAV simulation resource contributors. No downloaded tower geometry
is used. This is a navigation obstacle, not a structural/electrical design.
"""
from pathlib import Path
import math

REPO = Path(__file__).resolve().parents[1]


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def unit(a):
    length = math.sqrt(sum(x*x for x in a))
    return tuple(x/length for x in a)


class Mesh:
    def __init__(self):
        self.vertices = []
        self.faces = []

    def beam(self, start, end, radius, sides=6):
        axis = unit(sub(end, start))
        u = unit(cross(axis, (0, 0, 1) if abs(axis[2]) < .9 else (1, 0, 0)))
        v = cross(axis, u)
        index = len(self.vertices)
        for center in (start, end):
            for j in range(sides):
                theta = 2*math.pi*j/sides
                self.vertices.append(tuple(center[k]+radius*(u[k]*math.cos(theta)+v[k]*math.sin(theta)) for k in range(3)))
        for j in range(sides):
            k = (j+1) % sides
            self.faces.extend([(index+j,index+k,index+sides+k), (index+j,index+sides+k,index+sides+j)])
        for j in range(1, sides-1):
            self.faces.extend([(index,index+j+1,index+j), (index+sides,index+sides+j,index+sides+j+1)])

    def save(self, path, color):
        xyz = ' '.join(f'{x:.6f}' for p in self.vertices for x in p)
        faces = ' '.join(str(x) for f in self.faces for x in f)
        rgba = ' '.join(map(str, color))
        path.write_text(f'''<?xml version="1.0"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
<asset><contributor><author>UAV simulation resource contributors</author></contributor><unit name="meter" meter="1"/><up_axis>Z_UP</up_axis></asset>
<library_effects><effect id="fx"><profile_COMMON><technique sid="common"><phong><ambient><color>{rgba}</color></ambient><diffuse><color>{rgba}</color></diffuse><specular><color>0.1 0.1 0.1 1</color></specular><shininess><float>12</float></shininess></phong></technique></profile_COMMON></effect></library_effects>
<library_materials><material id="mat"><instance_effect url="#fx"/></material></library_materials>
<library_geometries><geometry id="mesh"><mesh><source id="positions"><float_array id="positions-array" count="{len(self.vertices)*3}">{xyz}</float_array><technique_common><accessor source="#positions-array" count="{len(self.vertices)}" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source><vertices id="vertices"><input semantic="POSITION" source="#positions"/></vertices><triangles count="{len(self.faces)}" material="M"><input semantic="VERTEX" source="#vertices" offset="0"/><p>{faces}</p></triangles></mesh></geometry></library_geometries>
<library_visual_scenes><visual_scene id="Scene"><node><instance_geometry url="#mesh"><bind_material><technique_common><instance_material symbol="M" target="#mat"/></technique_common></bind_material></instance_geometry></node></visual_scene></library_visual_scenes><scene><instance_visual_scene url="#Scene"/></scene>
</COLLADA>''')


def build():
    directory = REPO/'worlds/models/uav_power_corridor'
    (directory/'meshes').mkdir(parents=True, exist_ok=True)
    steel, conductors, insulators = Mesh(), Mesh(), Mesh()
    for offset in (0, 160):
        levels = [0, 4, 8, 12, 16, 20, 24, 28, 32]
        def corners(z):
            half = 1.7 - 1.2*z/32
            return [(offset-half,-half,z),(offset+half,-half,z),(offset+half,half,z),(offset-half,half,z)]
        for low, high in zip(levels, levels[1:]):
            a, b = corners(low), corners(high)
            for j in range(4):
                k = (j+1) % 4
                steel.beam(a[j], b[j], .12)
                steel.beam(a[j], a[k], .08)
                steel.beam(a[j], b[k], .065)
                steel.beam(a[k], b[j], .065)
        for z in (25.5, 28.5, 31.5):
            steel.beam((offset,-5.2,z),(offset,5.2,z),.16)
            for sign in (-1, 1):
                steel.beam((offset,0,z-2.5),(offset,sign*5.2,z),.10)
                insulators.beam((offset,sign*4.6,z),(offset,sign*4.6,z-1.5),.16,8)
    # Two 160 m spans per instance. Lowest phase: 24 m at towers, 16 m at midpoint.
    for beginning in (-160, 0):
        for y, z in [(sign*4.6,z) for z in (24,27,30) for sign in (-1,1)]+[(-.5,32),(.5,32)]:
            points=[]
            for j in range(49):
                t=j/48
                points.append((beginning+160*t,y,z-4*8*t*(1-t)))
            for a,b in zip(points,points[1:]):
                conductors.beam(a,b,.04,6)
    parts = [('steel',steel,(.48,.51,.54,1)),('conductors',conductors,(.16,.17,.18,1)),('insulators',insulators,(.23,.36,.29,1))]
    sdf=['<sdf version="1.6"><model name="uav_power_corridor"><static>true</static><link name="structure">']
    for name,mesh,color in parts:
        mesh.save(directory/'meshes'/(name+'.dae'),color)
        geometry=f'<geometry><mesh><uri>model://uav_power_corridor/meshes/{name}.dae</uri></mesh></geometry>'
        sdf.append(f'<visual name="{name}">{geometry}</visual><collision name="{name}">{geometry}</collision>')
    sdf.append('</link></model></sdf>')
    (directory/'model.sdf').write_text('\n'.join(sdf)+'\n')
    (directory/'model.config').write_text('<model><name>Original UAV power corridor</name><version>1</version><sdf version="1.6">model.sdf</sdf><author><name>UAV simulation resource contributors</name></author><description>Two original 32 m lattice towers and two 160 m spans. Static mesh collisions. MIT.</description></model>\n')
    print(f'Generated {directory.name}: {sum(len(m.faces) for _,m,_ in parts)} triangles')


if __name__ == '__main__':
    build()
