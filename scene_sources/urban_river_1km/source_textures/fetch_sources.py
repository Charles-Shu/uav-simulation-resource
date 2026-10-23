#!/usr/bin/env python3
"""Fetch only original CC0 maps from the public Poly Haven API, with MD5 checks."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import time
from urllib.parse import urlparse
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT.parents[1] / 'mountain_lakes_1km' / 'source_textures'
REUSE = ['grass_ground', 'leafy_grass', 'rock_boulder_dry', 'aerial_rocks_04', 'brown_mud', 'sand_01']
NEW = ['clean_asphalt', 'concrete_pavement_02', 'rough_concrete']
CHANNELS = {'diff': 'Diffuse', 'nor_gl': 'nor_gl', 'rough': 'Rough'}

def get(url):
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=(8, 30), headers={'User-Agent': 'urban-river-gazebo-material-preparation/1.0'})
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(1 + attempt)

def asset(asset_id):
    files = get('https://api.polyhaven.com/files/' + asset_id).json()
    info = get('https://api.polyhaven.com/info/' + asset_id).json()
    (ROOT / (asset_id + '_api_files.json')).write_text(json.dumps(files, indent=2) + '\n')
    (ROOT / (asset_id + '_api_info.json')).write_text(json.dumps(info, indent=2) + '\n')
    result = {
        'id': asset_id, 'name': info['name'], 'authors': info.get('authors', {}),
        'asset_url': 'https://polyhaven.com/a/' + asset_id,
        'license': 'CC0-1.0', 'license_url': 'https://polyhaven.com/license',
        'original_dimensions_mm': info.get('dimensions'), 'files': [],
    }
    for kind, key in CHANNELS.items():
        src = files[key]['1k']['jpg']
        name = Path(urlparse(src['url']).path).name
        target = ROOT / name
        prior = PREVIOUS / name
        if asset_id in REUSE:
            data = prior.read_bytes()
            status = 'copied_verified_against_current_official_md5'
        elif target.exists() and hashlib.md5(target.read_bytes()).hexdigest() == src['md5']:
            data = target.read_bytes()
            status = 'downloaded_verified_against_current_official_md5'
        else:
            data = get(src['url']).content
            status = 'downloaded_verified_against_current_official_md5'
        md5 = hashlib.md5(data).hexdigest()
        assert md5 == src['md5'], (asset_id, kind, 'official MD5 mismatch')
        assert len(data) == src['size'], (asset_id, kind, 'size mismatch')
        target.write_bytes(data)
        with Image.open(target) as im:
            size = list(im.size)
            im.verify()
        assert size == [1024, 1024]
        rec = {'kind': kind, 'filename': name, 'path': str(target), 'url': src['url'],
               'official_md5': src['md5'], 'actual_md5': md5,
               'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data),
               'resolution': size, 'status': status}
        if asset_id in REUSE:
            rec['reused_from'] = str(prior)
        result['files'].append(rec)
    print('verified ' + asset_id, flush=True)
    return result

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        assets = list(pool.map(asset, REUSE + NEW))
    manifest = {'retrieved_utc': datetime.datetime.utcnow().isoformat() + 'Z',
                'provider': 'Poly Haven', 'license': 'CC0-1.0',
                'license_page': 'https://polyhaven.com/license',
                'no_watermarks': 'Original downloadable maps only; no previews or logos.',
                'assets': assets}
    (ROOT / 'sources.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    rows = ['# City terrain texture sources', '',
            'All maps below are original **Poly Haven CC0** assets, without watermarks.',
            '[Official license](https://polyhaven.com/license). Original files remain unmodified.', '',
            'Every JPG was checked against the **MD5 and byte count returned by the official API**; dimensions are 1024 × 1024. `sources.json` also records local SHA-256 hashes and direct download URLs. API responses are preserved alongside the files.', '',
            '| Asset | Use | Source |', '|---|---|---|']
    use = {'grass_ground': 'Lawns / slopes', 'leafy_grass': 'Natural grassy areas',
           'rock_boulder_dry': 'Mountain rock', 'aerial_rocks_04': 'Mountain rock',
           'brown_mud': 'Riverbank mud', 'sand_01': 'Riverbank sand',
           'clean_asphalt': 'Asphalt roads', 'concrete_pavement_02': 'Sidewalk slabs',
           'rough_concrete': 'Concrete structures'}
    for a in assets:
        rows.append('| ' + a['id'] + ' | ' + use[a['id']] + ' | [' + a['name'] + '](' + a['asset_url'] + ') |')
    rows.extend(['', 'Available for every asset: `{asset}_diff_1k.jpg`, `{asset}_nor_gl_1k.jpg`, `{asset}_rough_1k.jpg`.', '',
                 'The first six assets are byte-for-byte copies of the previous mountain scene sources, revalidated against the current official API. The final three were downloaded for this city scene.', '',
                 'Diffuse maps use sRGB; normal and roughness maps are data and should use Non-Color in Blender. Do not derive friction or soil stiffness from texture roughness: physical parameters are configured separately in Gazebo.', ''])
    (ROOT / 'SOURCES.md').write_text('\n'.join(rows))
    print('Done: ' + str(len(assets) * 3) + ' verified JPG maps.', flush=True)

if __name__ == '__main__':
    main()
