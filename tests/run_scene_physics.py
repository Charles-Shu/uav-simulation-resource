#!/usr/bin/env python3
"""Exercise all scenes without the user's Gazebo cache; requires Gazebo 11 dev.

Run scripts/prepare_scenes.sh first, then python3 tests/run_scene_physics.py.
Only test fixtures/logs are generated, under tests/output; source worlds stay intact.
"""
import argparse
import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import xml.etree.ElementTree as ET


def tower_rays(repo):
    """Cast through a face on original steel and conductors, in both directions."""
    ns = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
    result = []
    for part in ('steel', 'conductors'):
        root = ET.parse(repo/'worlds/models/uav_power_corridor/meshes'/f'{part}.dae')
        mesh = root.find('.//c:mesh', ns)
        arr = [float(v) for v in mesh.find('c:source/c:float_array', ns).text.split()]
        ids = [int(v) for v in mesh.find('c:triangles/c:p', ns).text.split()[:3]]
        pts = [arr[i*3:i*3+3] for i in ids]
        u = [pts[1][i]-pts[0][i] for i in range(3)]
        v = [pts[2][i]-pts[0][i] for i in range(3)]
        n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        norm = math.sqrt(sum(x*x for x in n))
        n = [x/norm for x in n]
        c = [sum(p[i] for p in pts)/3 for i in range(3)]
        transform = lambda p: [300-p[1], -340+p[0], 8+p[2]]
        # Start outside the surface; a short segment avoids neighbouring trusses.
        start = transform([c[i]+0.02*n[i] for i in range(3)])
        end = transform([c[i]-0.02*n[i] for i in range(3)])
        result.append(dict(name='original_'+part, start=start, end=end,
                           expected_entity='power_corridor_0::structure::'+part,
                           expected_distance=0.02))
    return result


def add_probe(world, p):
    mass = p['mass']
    model = ET.SubElement(world, 'model', name=p['name'])
    ET.SubElement(model, 'pose').text = f"{p['x']} {p['y']} {p['z']} 0 0 0"
    # A closed 1 m³ body: density 400 floats, 1600 sinks in 1000 kg/m³ water.
    link = ET.SubElement(model, 'link', name='body')
    inertia = ET.SubElement(link, 'inertial')
    ET.SubElement(inertia, 'mass').text = str(mass)
    tensor = ET.SubElement(inertia, 'inertia')
    for name in ('ixx', 'iyy', 'izz', 'ixy', 'ixz', 'iyz'):
        ET.SubElement(tensor, name).text = str(mass/6 if name in ('ixx', 'iyy', 'izz') else 0)
    collision = ET.SubElement(link, 'collision', name='body')
    ET.SubElement(ET.SubElement(ET.SubElement(collision, 'geometry'), 'box'), 'size').text = '1 1 1'
    surface = ET.SubElement(collision, 'surface')
    friction = ET.SubElement(ET.SubElement(surface, 'friction'), 'ode')
    for name in ('mu', 'mu2'):
        ET.SubElement(friction, name).text = '1'
    contact = ET.SubElement(ET.SubElement(surface, 'contact'), 'ode')
    for name, value in [('kp', '1e10'), ('kd', '1000'), ('max_vel', '1'), ('min_depth', '.001')]:
        ET.SubElement(contact, name).text = value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--port', type=int, default=11635)
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = repo/'tests/output'
    output.mkdir(parents=True, exist_ok=True)
    home = output/'isolated_home'
    home.mkdir(exist_ok=True)
    plugin = repo/'worlds/.scene-build'
    if not (plugin/'libLakeWaterPlugin.so').is_file():
        parser.error('Run scripts/prepare_scenes.sh first.')
    flags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'gazebo'], text=True))
    binary = output/'scene_physics'
    subprocess.run(['g++', '-std=c++17', '-O2', str(repo/'tests/scene_physics.cpp'), '-o', str(binary), *flags], check=True)
    env = dict(os.environ, HOME=str(home), GAZEBO_MODEL_DATABASE_URI='',
               GAZEBO_MODEL_PATH=str(repo/'worlds/models'), GAZEBO_PLUGIN_PATH=str(plugin),
               GAZEBO_RESOURCE_PATH=str(repo/'worlds')+':/usr/share/gazebo-11',
               GAZEBO_IP='127.0.0.1')
    specs = json.loads((repo/'tests/scene_probe_specs.json').read_text())
    results = {}
    failures = []
    for index, (scene, spec) in enumerate(specs.items()):
        env['GAZEBO_MASTER_URI'] = f'http://127.0.0.1:{args.port+index}'
        tree = ET.parse(repo/'worlds/worlds'/f'{scene}.world')
        world = tree.getroot().find('world')
        for probe in spec['probes']:
            add_probe(world, probe)
        fixture = output/f'{scene}.world'
        tree.write(fixture, encoding='utf-8', xml_declaration=True)
        rays = spec['rays'] + (tower_rays(repo) if scene == 'urban_river_1km' else [])
        rayfile = output/f'{scene}_rays.txt'
        rayfile.write_text(''.join(p['name']+' '+' '.join(map(str, p['start']+p['end']))+'\n' for p in rays))
        proc = subprocess.run([str(binary), str(fixture), str(rayfile)], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)
        (output/f'{scene}.log').write_text(proc.stdout)
        lines = [s for s in proc.stdout.splitlines() if s.startswith('WORLD_RESULT ')]
        if proc.returncode or not lines:
            failures.append(f'{scene}: runtime failure (see log)')
            continue
        result = json.loads(lines[-1].split(' ', 1)[1])
        results[scene] = result
        if not result['all_trajectories_finite'] or result['simulated_s'] != 20:
            failures.append(f'{scene}: invalid trajectories or simulation duration')
        if result['model_count'] != spec['includes']+len(spec['probes']):
            failures.append(f'{scene}: missing models')
        probes = {p['name']: p for p in result['probes']}
        for p in spec['probes']:
            got = probes[p['name']]
            contact = p['expected_contact']
            if contact and not any(n.endswith(contact) for n in got['contacts']):
                failures.append(f'{scene}/{p["name"]}: missing contact {contact}')
            if contact is None:
                if got['contacts'] or not p['level']-0.15 < got['z'] < p['level']+0.3:
                    failures.append(f'{scene}/{p["name"]}: buoyancy failed')
            else:
                if not p['ground_z']+0.1 < got['z'] < p['ground_z']+0.8:
                    failures.append(f'{scene}/{p["name"]}: incorrect rest height {got["z"]}')
            if got['speed'] > 0.2:
                failures.append(f'{scene}/{p["name"]}: failed to settle')
        actual_rays = {r['name']: r for r in result['rays']}
        for ray in rays:
            got = actual_rays[ray['name']]
            if got['entity'] != ray['expected_entity'] or abs(got['distance']-ray['expected_distance']) > ray.get('distance_tolerance', 0.01):
                failures.append(f'{scene}/{ray["name"]}: incorrect ray intersection {got}')
        # Missing resources/plugins are errors even when another probe succeeds.
        if any(s in proc.stdout for s in ('[Err]', 'Unable to find uri', 'Failed to load plugin')):
            failures.append(f'{scene}: Gazebo reported a loading error (see log)')
        print(scene, 'simulated', result['simulated_s'], 's,', result['model_count'], 'models', flush=True)
    report = dict(test='isolated-home Gazebo Classic physics integration',
                  results=results, failures=failures, passed=not failures)
    (output/'physics_results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(passed=not failures, failures=failures), indent=2))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
