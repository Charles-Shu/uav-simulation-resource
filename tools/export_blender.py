"""Build an editable scene from the same SDF visuals that Gazebo loads.

Run Blender in background with --python this_file. Optional script arguments:
  -- --no-render
  -- --check-model /absolute/model.sdf
Only visual geometry is imported. Gazebo retains the authoritative collisions,
ODE parameters and water plugin. Repeated assets share Blender mesh data.
"""
from pathlib import Path
import argparse
import json
import math
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

import bpy
import numpy as np
from mathutils import Matrix, Vector, Euler

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO/'scene_sources/urban_river_1km'
PACKAGE = REPO/'worlds'
SEARCH = [PACKAGE/'models']
NS = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
CACHE = {}
MATERIAL_CACHE = {}
WARNINGS = []
IMPORTED = []


def numbers(value, default):
    return list(default) if not value else [float(x) for x in value.split()]


def pose_matrix(pose):
    p = numbers(pose, [0]*6) if isinstance(pose, (str, type(None))) else pose
    return Matrix.Translation(Vector(p[:3])) @ Euler(p[3:6], 'XYZ').to_matrix().to_4x4()


def resolve(uri, base):
    uri = urllib.parse.unquote((uri or '').strip()).replace('\\', '/')
    if uri.startswith('file://'):
        return Path(uri[7:])
    if uri.startswith('model://'):
        rel = Path(uri[8:])
        # The current model's siblings take precedence over global model caches.
        for parent in [base, *base.parents, *SEARCH]:
            p = parent/rel
            if p.exists():
                return p
        raise FileNotFoundError('Unresolved model URI: '+uri)
    p = Path(uri)
    if p.is_absolute() and p.exists():
        return p
    p = base/uri
    if p.exists():
        return p
    # Legacy DAE files sometimes retain an author's old absolute texture path.
    for parent in [base, base.parent, base.parent.parent]:
        hits = list(parent.rglob(Path(uri).name)) if parent.exists() else []
        if hits:
            return hits[0]
    raise FileNotFoundError('Unresolved resource '+uri+' relative to '+str(base))


def material(name, color=(.55,.55,.55,1), texture=None, alpha_cut=False, roughness=.8):
    key = (name, tuple(color), str(texture), alpha_cut, roughness)
    if key in MATERIAL_CACHE:
        return MATERIAL_CACHE[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = color
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = color
    bs.inputs['Roughness'].default_value = roughness
    bs.inputs['Specular IOR Level'].default_value = .3
    if texture:
        tex = m.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(texture), check_existing=True)
        m.node_tree.links.new(tex.outputs['Color'], bs.inputs['Base Color'])
        if alpha_cut:
            threshold = m.node_tree.nodes.new('ShaderNodeMath')
            threshold.operation = 'GREATER_THAN'
            threshold.inputs[1].default_value = .5
            m.node_tree.links.new(tex.outputs['Alpha'], threshold.inputs[0])
            m.node_tree.links.new(threshold.outputs[0], bs.inputs['Alpha'])
    MATERIAL_CACHE[key] = m
    return m


def collada_materials(root, path):
    images = {e.get('id'): e.findtext('c:init_from', '', NS)
              for e in root.findall('c:library_images/c:image', NS)}
    effects = {}
    for effect in root.findall('c:library_effects/c:effect', NS):
        params = {p.get('sid'):p for p in effect.findall('c:profile_COMMON/c:newparam', NS)}
        technique = effect.find('c:profile_COMMON/c:technique', NS)
        shader = list(technique)[0] if technique is not None and len(technique) else None
        color = (.55,.55,.55,1)
        texture = None
        roughness = .8
        if shader is not None:
            diffuse = shader.find('c:diffuse', NS)
            if diffuse is not None:
                c = diffuse.find('c:color', NS)
                if c is not None:
                    color = tuple(numbers(c.text, color))
                tex = diffuse.find('c:texture', NS)
                if tex is not None:
                    token = tex.get('texture')
                    for _ in range(4):
                        if token not in params:
                            break
                        param = params[token]
                        token = param.findtext('c:sampler2D/c:source', None, NS) or param.findtext('c:surface/c:init_from', token, NS)
                    uri = images.get(token, token)
                    try:
                        texture = resolve(uri, path.parent)
                    except FileNotFoundError as exc:
                        WARNINGS.append(str(exc))
            shiny = float(shader.findtext('c:shininess/c:float', '8', NS))
            roughness = max(.2, min(.94, math.sqrt(2/(max(0,shiny)+2))))
        effects[effect.get('id')] = material(path.stem+'/'+effect.get('id'), color, texture, roughness=roughness)
    output = {}
    for m in root.findall('c:library_materials/c:material', NS):
        inst = m.find('c:instance_effect', NS)
        if inst is not None and inst.get('url','').lstrip('#') in effects:
            output[m.get('id')] = effects[inst.get('url').lstrip('#')]
    return output


def sdf_material(visual, model_dir):
    node = visual.find('material')
    if node is None:
        return None
    name = node.findtext('script/name', '')
    if name.startswith(('PineTree/', 'OakTree/')):
        kind = 'pine_tree' if name.startswith('Pine') else 'oak_tree'
        leaf = name.rsplit('/',1)[-1].lower() == 'branch'
        filename = ('branch_2_diffuse.png' if kind=='pine_tree' else 'branch_diffuse.png') if leaf else 'bark_diffuse.png'
        return material(name, (.3,.4,.2,1), model_dir/'materials/textures'/filename, leaf, .88)
    color = tuple(numbers(node.findtext('diffuse'), [.55,.55,.55,1]))
    texture = None
    if name:
        # Read the selected Ogre material block, keeping its diffuse texture.
        for p in model_dir.rglob('*.material'):
            text = p.read_text(errors='replace')
            start = re.search(r'\bmaterial\s+'+re.escape(name)+r'\s*(?::[^\{]+)?\{',text)
            if not start:
                continue
            depth, end = 1, start.end()
            while depth and end < len(text):
                depth += (text[end]=='{')-(text[end]=='}')
                end += 1
            block = text[start.end():end-1]
            texture_match = re.search(r'^\s*texture\s+("[^"]+"|\S+)',block,re.M)
            if texture_match:
                try:
                    texture = resolve(texture_match.group(1).strip('"'), model_dir/'materials/textures')
                except FileNotFoundError as exc:
                    WARNINGS.append(str(exc))
            break
    if name or node.find('diffuse') is not None:
        return material(name or visual.get('name','SDF material'),color,texture)
    return None


def local_collada_transform(node):
    matrix = Matrix.Identity(4)
    for e in node:
        tag = e.tag.rsplit('}',1)[-1]
        vals = numbers(e.text, []) if tag in ('matrix','translate','rotate','scale') else []
        if tag == 'matrix':
            local = Matrix(np.array(vals).reshape(4,4).tolist())
        elif tag == 'translate':
            local = Matrix.Translation(Vector(vals))
        elif tag == 'rotate':
            local = Matrix.Rotation(math.radians(vals[3]),4,Vector(vals[:3]))
        elif tag == 'scale':
            local = Matrix.Diagonal(Vector([*vals,1]))
        else:
            continue
        matrix = matrix @ local
    return matrix


def load_collada(path, submesh=None, override=None):
    key = (str(path), submesh, override.name if override else '')
    if key in CACHE:
        return CACHE[key]
    root = ET.parse(path).getroot()
    mats = collada_materials(root,path) if override is None else {}
    asset = root.find('c:asset',NS)
    unit = asset.find('c:unit',NS) if asset is not None else None
    scale = float(unit.get('meter','1')) if unit is not None else 1.
    up = asset.findtext('c:up_axis','Z_UP',NS) if asset is not None else 'Z_UP'
    axis = Matrix.Identity(4)
    if up == 'Y_UP':
        axis = Matrix.Rotation(math.pi/2,4,'X')
    elif up == 'X_UP':
        axis = Matrix.Rotation(-math.pi/2,4,'Y')
    base_transform = axis @ Matrix.Diagonal(Vector([scale,scale,scale,1]))
    geometries = {g.get('id'):g for g in root.findall('c:library_geometries/c:geometry',NS)}
    nodes = {n.get('id'):n for n in root.findall('.//c:node',NS) if n.get('id')}
    parsed = {}
    parts = []

    def geometry(gid, bindings, transform, node_name):
        geom = geometries[gid]
        if submesh and submesh not in (node_name, gid, geom.get('name')):
            return
        mesh_node = geom.find('c:mesh',NS)
        sources = {}
        for source in mesh_node.findall('c:source',NS):
            arr = source.find('c:float_array',NS)
            if arr is None:
                continue
            accessor = source.find('c:technique_common/c:accessor',NS)
            stride = int(accessor.get('stride','1'))
            offset = int(accessor.get('offset','0'))
            count = int(accessor.get('count','0'))
            values = np.fromstring(arr.text,sep=' ')[offset:offset+count*stride].reshape(-1,stride)
            sources[source.get('id')] = values
        vertices = {v.get('id'): {i.get('semantic'):i.get('source').lstrip('#') for i in v.findall('c:input',NS)}
                    for v in mesh_node.findall('c:vertices',NS)}
        for primitive_i, primitive in enumerate(mesh_node):
            tag = primitive.tag.rsplit('}',1)[-1]
            if tag not in ('triangles','polylist','polygons','lines'):
                continue
            inputs = primitive.findall('c:input',NS)
            stride = max(int(i.get('offset','0')) for i in inputs)+1
            pos_input = next((i for i in inputs if i.get('semantic')=='VERTEX'),None)
            if pos_input is None:
                continue
            po = int(pos_input.get('offset','0'))
            position_source = vertices[pos_input.get('source').lstrip('#')]['POSITION']
            positions = sources[position_source][:,:3]
            tex_input = next((i for i in inputs if i.get('semantic')=='TEXCOORD' and i.get('set','0')=='0'),None)
            chunks = [np.fromstring(p.text,sep=' ',dtype=np.int32).reshape(-1,stride) for p in primitive.findall('c:p',NS)]
            rows = np.concatenate(chunks)
            if tag == 'lines':
                # COLLADA line primitives are visible in Gazebo but need a tiny
                # optical thickness to render in Blender. They remain unchanged
                # in the authoritative Gazebo mesh/collision files.
                line_indices = rows[:,po].reshape(-1,2)
                points = (np.c_[positions,np.ones(len(positions))] @ np.asarray(transform).T)[:,:3]
                curve = bpy.data.curves.new(path.stem+'/'+node_name+'/lines'+str(primitive_i),'CURVE')
                curve.dimensions = '3D'
                curve.resolution_u = 1
                curve.bevel_depth = .0025
                curve.bevel_resolution = 0
                for pair in line_indices:
                    spline = curve.splines.new('POLY')
                    spline.points.add(1)
                    spline.points.foreach_set('co',np.c_[points[pair],np.ones(2)].ravel())
                selected = override or mats.get(bindings.get(primitive.get('material',''),''))
                curve.materials.append(selected or material(path.stem+' source line',(.12,.13,.14,1)))
                parts.append(curve)
                continue
            if tag == 'triangles':
                trirows = rows.reshape(-1,3,stride)
            else:
                counts = np.fromstring(primitive.findtext('c:vcount','',NS),sep=' ',dtype=np.int32) if tag=='polylist' else [len(c) for c in chunks]
                triangles, start = [], 0
                for count in counts:
                    for k in range(1,int(count)-1):
                        triangles.append(rows[[start,start+k,start+k+1]])
                    start += int(count)
                trirows = np.asarray(triangles,dtype=np.int32)
            if not len(trirows):
                continue
            indices = trirows[:,:,po]
            ids, inverse = np.unique(indices.ravel(),return_inverse=True)
            local_positions = positions[ids]
            transformed = (np.c_[local_positions,np.ones(len(ids))] @ np.asarray(transform).T)[:,:3]
            data = bpy.data.meshes.new(path.stem+'/'+node_name+'/'+str(primitive_i))
            data.from_pydata(transformed.tolist(),[],inverse.reshape(-1,3).tolist())
            data.update()
            if tex_input is not None:
                offset = int(tex_input.get('offset','0'))
                texcoords = sources[tex_input.get('source').lstrip('#')]
                uv = data.uv_layers.new(name='UVMap')
                uv.data.foreach_set('uv',texcoords[trirows[:,:,offset].ravel(),:2].ravel())
            selected = override or mats.get(bindings.get(primitive.get('material',''),''))
            if selected is None:
                selected = material(path.stem+' unassigned')
            data.materials.append(selected)
            if 'terrain' in path.name or path.name.startswith(('rock','grass','mud','sand','riverbed')):
                for face in data.polygons:
                    face.use_smooth = True
            parts.append(data)

    def visit(node,parent,seen=frozenset()):
        transform = parent @ local_collada_transform(node)
        name = node.get('name',node.get('id','part'))
        for inst in node.findall('c:instance_geometry',NS):
            bindings = {m.get('symbol'):m.get('target','').lstrip('#') for m in inst.findall('c:bind_material/c:technique_common/c:instance_material',NS)}
            geometry(inst.get('url').lstrip('#'),bindings,transform,name)
        for child in node.findall('c:node',NS):
            visit(child,transform,seen)
        for inst in node.findall('c:instance_node',NS):
            ref = inst.get('url','').lstrip('#')
            if ref in nodes and ref not in seen:
                visit(nodes[ref],transform,seen|{ref})
    active = root.find('c:scene/c:instance_visual_scene',NS)
    scene_id = active.get('url','').lstrip('#') if active is not None else None
    scenes = root.findall('c:library_visual_scenes/c:visual_scene',NS)
    for visual_scene in scenes:
        if scene_id and visual_scene.get('id') != scene_id:
            continue
        for node in visual_scene.findall('c:node',NS):
            visit(node,base_transform)
    if not parts:
        raise RuntimeError('No visual meshes from '+str(path)+' submesh='+str(submesh))
    CACHE[key] = parts
    print('COLLADA_OK',path.name,'parts',len(parts),'faces',sum(len(getattr(p,'polygons',[])) for p in parts),flush=True)
    return parts


def primitive_mesh(geometry,name):
    if geometry.find('box') is not None:
        size = numbers(geometry.findtext('box/size'),[1,1,1])
        bpy.ops.mesh.primitive_cube_add(size=1)
        obj = bpy.context.object
        obj.scale = size
    elif geometry.find('cylinder') is not None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=float(geometry.findtext('cylinder/radius','1')),depth=float(geometry.findtext('cylinder/length','1')))
        obj = bpy.context.object
    elif geometry.find('sphere') is not None:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=float(geometry.findtext('sphere/radius','1')))
        obj = bpy.context.object
    elif geometry.find('plane') is not None:
        size = numbers(geometry.findtext('plane/size'),[1,1])
        bpy.ops.mesh.primitive_plane_add(size=1)
        obj = bpy.context.object
        obj.scale = [*size,1]
    else:
        raise RuntimeError('Unsupported SDF geometry in '+name)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mesh = obj.data
    bpy.data.objects.remove(obj,do_unlink=True)
    mesh.name = name
    return mesh


def water_material():
    m = material('River water — same surface, optical render shader',(.035,.18,.19,1),roughness=.18)
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['IOR'].default_value = 1.333
    bs.inputs['Transmission Weight'].default_value = .22
    tex = m.node_tree.nodes.new('ShaderNodeTexNoise')
    tex.inputs['Scale'].default_value = .7
    tex.inputs['Detail'].default_value = 2
    coord = m.node_tree.nodes.new('ShaderNodeTexCoord')
    bump = m.node_tree.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .2
    bump.inputs['Distance'].default_value = .035
    links = m.node_tree.links
    links.new(coord.outputs['Object'],tex.inputs['Vector'])
    links.new(tex.outputs['Fac'],bump.inputs['Height'])
    links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    return m


def import_model(node, directory, parent, collection, instance_name=None):
    name = instance_name or node.get('name','model')
    transform = parent @ pose_matrix(node.findtext('pose'))
    object_count = 0
    for link in node.findall('link'):
        link_transform = transform @ pose_matrix(link.findtext('pose'))
        for visual in link.findall('visual'):
            geo = visual.find('geometry')
            if geo is None:
                continue
            visual_name = name+'/'+visual.get('name','visual')
            placement = link_transform @ pose_matrix(visual.findtext('pose'))
            override = sdf_material(visual,directory)
            if any(label in visual_name.lower() for label in ('water_surface','river_water','liquid_water')):
                override = water_material()
            mesh = geo.find('mesh')
            if mesh is not None:
                path = resolve(mesh.findtext('uri'),directory)
                if path.suffix.lower() != '.dae':
                    raise RuntimeError('Expected COLLADA visual, got '+str(path))
                data = load_collada(path,mesh.findtext('submesh/name'),override)
                scale = numbers(mesh.findtext('scale'),[1,1,1])
                placement = placement @ Matrix.Diagonal(Vector([*scale,1]))
            else:
                data = [primitive_mesh(geo,visual_name)]
                data[0].materials.append(override or material(visual_name))
            for i,part in enumerate(data):
                obj = bpy.data.objects.new(visual_name+'/'+str(i),part)
                collection.objects.link(obj)
                obj.matrix_world = placement
                obj['gazebo_source'] = str(directory)
                obj['physics'] = 'Visual copy. Authoritative collision and physics remain in Gazebo SDF.'
                object_count += 1
    for child in node.findall('model'):
        object_count += import_model(child,directory,transform,collection)
    for include in node.findall('include'):
        object_count += import_include(include,directory,transform,collection)
    IMPORTED.append({'name':name,'source':str(directory),'visual_objects':object_count})
    return object_count


def import_include(include,directory,parent,collection):
    path = resolve(include.findtext('uri'),directory)
    sdf = path/'model.sdf' if path.is_dir() else path
    if not sdf.exists() and path.is_dir():
        config = ET.parse(path/'model.config').getroot()
        sdf = path/config.findtext('sdf')
    root = ET.parse(sdf).getroot()
    node = root.find('model') if root.tag=='sdf' else root
    name = include.findtext('name',node.get('name','model'))
    return import_model(node,sdf.parent,parent @ pose_matrix(include.findtext('pose')),collection,name)


def camera(scene,name,position,target,lens=40,ortho=None):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    data.clip_start = .1
    data.clip_end = 10000
    data.lens = lens
    if ortho:
        data.type = 'ORTHO'
        data.ortho_scale = ortho
    return obj


def bounds(collection):
    points = [obj.matrix_world @ Vector(c) for obj in collection.objects if obj.type in ('MESH','CURVE') for c in obj.bound_box]
    arr = np.asarray(points)
    return {'min':arr.min(0).tolist(),'max':arr.max(0).tolist()} if len(arr) else {}


def main():
    global ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-render',action='store_true')
    parser.add_argument('--check-model')
    parser.add_argument('--scene',choices=['alpine_snow_1km','mountain_lakes_1km','urban_river_1km'],default='urban_river_1km')
    parser.add_argument('--world')
    parser.add_argument('--samples',type=int,default=24)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    ROOT = REPO/'scene_sources'/args.scene
    ROOT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    collection = bpy.data.collections.new('Gazebo authoritative world visuals')
    scene.collection.children.link(collection)
    if args.check_model:
        path = Path(args.check_model)
        root = ET.parse(path).getroot()
        import_model(root.find('model'),path.parent,Matrix.Identity(4),collection)
        bpy.context.view_layer.update()
        print('MODEL_CHECK',json.dumps({'source':str(path),'bounds':bounds(collection),'objects':len(collection.objects),'warnings':WARNINGS}),flush=True)
        return
    world_path = Path(args.world) if args.world else PACKAGE/'worlds'/(args.scene+'.world')
    root = ET.parse(world_path).getroot().find('world')
    for include in root.findall('include'):
        uri = include.findtext('uri','')
        if uri in ('model://sun','model://ground_plane'):
            continue
        import_include(include,world_path.parent,Matrix.Identity(4),collection)
    for node in root.findall('model'):
        import_model(node,world_path.parent,Matrix.Identity(4),collection)
    bpy.context.view_layer.update()
    sky = bpy.data.worlds.new('Clear river city sky')
    sky.use_nodes = True
    scene.world = sky
    sky.node_tree.nodes['Background'].inputs['Color'].default_value = (.57,.7,.86,1)
    sky.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
    sun_data = bpy.data.lights.new('Warm morning sun','SUN')
    sun_data.energy = 2
    sun_data.angle = math.radians(5)
    sun_data.color = (1,.95,.86)
    sun = bpy.data.objects.new('Warm morning sun',sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((-.5,.3,-.81)).to_track_quat('-Z','Y').to_euler()
    overview = camera(scene,'Full kilometre overview',(850,-1050,1020),(-10,0,35),ortho=1450)
    if args.scene == 'urban_river_1km':
        street = camera(scene,'River and original power corridor',(35,-440,90),(160,180,45),lens=30)
    else:
        street = camera(scene,'Lake basin and slopes',(420,-520,180),(120,-120,25),lens=30)
    scene.camera = overview
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.device = 'CPU'
    scene.cycles.max_bounces = 6
    scene.cycles.transparent_max_bounces = 16
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 8
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene['area_m'] = '1000 × 1000'
    scene['canonical_source'] = world_path.relative_to(REPO).as_posix() if world_path.is_relative_to(REPO) else world_path.name
    scene['physics_scope'] = 'SDF/Gazebo governs collisions, surface friction, compliant soil and water forces. Blender contains visual geometry only.'
    readme = bpy.data.texts.new('README — scene visuals and attribution')
    readme.write('Editable 1 km × 1 km Gazebo scene. Units are metres.\n'
        'Visuals were imported from the final Gazebo world: buildings, trees, terrain, river, roads and original transmission towers.\n'
        'Trees retain upstream collisions; the public tower is original project geometry.\n'
        'Terrain and building materials retain diffuse maps/colours. The Blender water shader adds optical reflections and fine ripples for preview.\n'
        'The authoritative collision geometry, friction and liquid water forces are in the Gazebo SDF/world.\n'
        'Blender previews are offline renders; see actual Gazebo screenshots separately.\n'
        'Project and resource attribution: docs/scenes/README.md and THIRD_PARTY_NOTICES.md\n')
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.clip_end = 6000
            area.spaces.active.region_3d.view_distance = 1300
            area.spaces.active.region_3d.view_location = (0,0,30)
            area.spaces.active.shading.type = 'MATERIAL'
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
    for folder in ('blender','previews','validation'):
        (ROOT/folder).mkdir(exist_ok=True)
    report = {'world':str(world_path),'visual_object_count':len(collection.objects),'unique_meshes':len(bpy.data.meshes),
              'model_instances':IMPORTED,'bounds':bounds(collection),'warnings':WARNINGS}
    (ROOT/'validation/blender_import.json').write_text(json.dumps(report,indent=2)+'\n')
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender'/(args.scene+'.blend')),compress=True)
    if not args.no_render:
        scene.render.filepath = str(ROOT/'previews/overview_blender.png')
        bpy.ops.render.render(write_still=True)
        scene.camera = street
        scene.render.resolution_y = 1000
        scene.render.filepath = str(ROOT/'previews/river_corridor_blender.png')
        bpy.ops.render.render(write_still=True)
    print('BLENDER_SCENE_OK',json.dumps({'objects':len(collection.objects),'warnings':WARNINGS}),flush=True)


if __name__ == '__main__':
    main()
