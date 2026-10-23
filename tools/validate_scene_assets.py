#!/usr/bin/env python3
"""Check the three portable scenes without Gazebo or third-party Python modules.

Only the runtime dependency graph of these scenes is checked. Other legacy
worlds in this repository are deliberately outside this validator's scope.
"""

import argparse
import json
import re
import shlex
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlsplit


SCENES = {
    "alpine_snow_1km": 1,
    "mountain_lakes_1km": 487,
    "urban_river_1km": 819,
}
WATER_SCENES = {"mountain_lakes_1km", "urban_river_1km"}
WATER_PLUGIN = "libLakeWaterPlugin.so"
NETWORK = re.compile(r"(?:https?|ftp|sftp|ssh|package|fuel)://", re.IGNORECASE)
ABSOLUTE = re.compile(r"(?:^|[\s\"'])/(?:home|tmp)/|file://(?:/|localhost/)|(?<![A-Za-z0-9_])[A-Za-z]:[\\/]")


def tag(element):
    return element.tag.rsplit("}", 1)[-1]


def inside(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


class Validator:
    def __init__(self, repo):
        self.repo = repo.resolve()
        self.models = self.repo / "worlds" / "models"
        self.errors = set()
        self.checked_xml = set()
        self.checked_models = set()
        self.checked_dae = set()
        self.checked_materials = set()
        self.assets = set()
        self.water_links = set()
        self.scenes = {}

    def label(self, path):
        try:
            return str(path.relative_to(self.repo))
        except ValueError:
            return str(path)

    def error(self, source, message):
        self.errors.add("{}: {}".format(self.label(source), message))

    def portable(self, value, source):
        """Inspect values, not XML namespace declarations or comments."""
        value = unquote(value.strip())
        if ABSOLUTE.search(value) or "/home/" in value or "/tmp/" in value:
            self.error(source, "non-portable absolute path: " + value[:180])
            return False
        if NETWORK.search(value) or value.startswith("//"):
            self.error(source, "network/external URI: " + value[:180])
            return False
        return True

    def resolve(self, value, source, directory=False):
        value = unquote(value.strip())
        if not value:
            self.error(source, "empty asset URI")
            return None
        if not self.portable(value, source):
            return None
        parsed = urlsplit(value)
        if parsed.scheme == "model":
            if not parsed.netloc or parsed.query or parsed.fragment:
                self.error(source, "invalid model URI: " + value)
                return None
            path = self.models / parsed.netloc / parsed.path.lstrip("/")
        elif parsed.scheme == "file":
            if parsed.netloc or parsed.path.startswith("/"):
                self.error(source, "absolute file URI: " + value)
                return None
            path = source.parent / parsed.path
        elif parsed.scheme:
            self.error(source, "unsupported asset URI scheme: " + value)
            return None
        else:
            if Path(value).is_absolute():
                self.error(source, "absolute asset path: " + value)
                return None
            path = source.parent / value
        path = path.resolve()
        if not inside(path, self.repo):
            self.error(source, "asset escapes repository: " + value)
            return None
        if not (path.is_dir() if directory else path.exists()):
            self.error(source, "missing {}: {}".format("directory" if directory else "asset", value))
            return None
        self.assets.add(path)
        return path

    def xml(self, path, scan_values=True):
        try:
            root = ET.parse(str(path)).getroot()
        except (OSError, ET.ParseError) as exc:
            self.error(path, "cannot read XML: " + str(exc))
            return None
        self.checked_xml.add(path)
        if scan_values:
            for node in root.iter():
                if node.text and node.text.strip():
                    self.portable(node.text, path)
                for value in node.attrib.values():
                    self.portable(value, path)
        return root

    def model(self, directory):
        if directory in self.checked_models:
            return
        self.checked_models.add(directory)
        config = directory / "model.config"
        root = self.xml(config)
        if root is None:
            return
        entries = root.findall("sdf")
        if not entries:
            self.error(config, "no SDF entries")
        # Check every declared version, because Gazebo versions can choose
        # different entries from the same model.config.
        for entry in entries:
            path = self.resolve(entry.text or "", config)
            if path is not None:
                if not path.is_file():
                    self.error(config, "SDF entry is not a file: " + self.label(path))
                else:
                    self.sdf(path)

    def include(self, node, source):
        uri = node.find("uri")
        if uri is None:
            self.error(source, "include has no URI")
            return
        directory = self.resolve(uri.text or "", source, directory=True)
        if directory is not None:
            self.model(directory)

    def sdf(self, path, root=None):
        if root is None:
            if path in self.checked_xml:
                return
            root = self.xml(path)
        if root is None:
            return
        parents = {child: node for node in root.iter() for child in node}
        for node in root.iter("include"):
            self.include(node, path)
        for plugin in root.iter("plugin"):
            filename = plugin.get("filename", "")
            if not filename:
                self.error(path, "plugin has no filename")
            elif Path(filename).is_absolute() or "://" in filename or re.match(r"^[A-Za-z]:", filename):
                self.error(path, "plugin filename must be portable: " + filename)
            elif filename == WATER_PLUGIN:
                if not (self.repo / "worlds/plugins/LakeWaterPlugin.cc").is_file():
                    self.error(path, "missing source worlds/plugins/LakeWaterPlugin.cc")
            elif "/" in filename or "\\" in filename:
                self.resolve(filename, path)
        for uri in root.iter("uri"):
            parent = parents.get(uri)
            if parent is not None and tag(parent) in ("include", "script"):
                continue
            asset = self.resolve(uri.text or "", path)
            if asset is not None:
                self.asset(asset)
        # PBR maps and heightmap texture paths do not use <uri> elements.
        for node in root.iter():
            if tag(node) in {"albedo_map", "normal_map", "metalness_map", "roughness_map", "emissive_map", "environment_map", "light_map"}:
                parent = parents.get(node)
                if parent is not None and tag(parent) == "shader":
                    material = parents.get(parent)
                    directories = []
                    if material is not None:
                        for uri in material.findall("script/uri"):
                            resource = self.resolve(uri.text or "", path)
                            if resource is not None:
                                directories.append(resource if resource.is_dir() else resource.parent)
                    self.texture(node.text or "", path, directories)
                else:
                    asset = self.resolve(node.text or "", path)
                    if asset is not None:
                        self.asset(asset)
            if tag(node) == "texture":
                for child in node:
                    if tag(child) in {"diffuse", "normal"}:
                        asset = self.resolve(child.text or "", path)
                        if asset is not None:
                            self.asset(asset)
        for script in root.findall(".//material/script"):
            resources = []
            for uri in script.findall("uri"):
                asset = self.resolve(uri.text or "", path)
                if asset is not None:
                    resources.append(asset)
            directories = [p if p.is_dir() else p.parent for p in resources]
            for resource in resources:
                material_files = sorted(resource.rglob("*.material")) if resource.is_dir() else [resource]
                for material in material_files:
                    self.material(material, directories)
        for link in root.iter("link"):
            liquid = any(
                "water" in (visual.get("name", "") + " ".join((uri.text or "") for uri in visual.iter("uri"))).lower()
                for visual in link.findall("visual")
            )
            if liquid:
                self.water_links.add((path, link.get("name", "")))
                if link.findall("collision"):
                    self.error(path, "liquid-water link has solid collision: " + link.get("name", ""))

    def asset(self, path):
        if path.is_dir():
            return
        if path.suffix.lower() == ".dae":
            self.dae(path)
        elif path.suffix.lower() == ".material":
            self.material(path, [])
        elif path.suffix.lower() == ".sdf":
            self.sdf(path)

    def dae(self, path):
        if path in self.checked_dae:
            return
        self.checked_dae.add(path)
        # COLLADA metadata and namespace URLs are not runtime resources.
        root = self.xml(path, scan_values=False)
        if root is None:
            return
        for node in root.iter():
            if tag(node) != "image":
                continue
            for init in node.iter():
                if tag(init) != "init_from":
                    continue
                value = (init.text or "").strip()
                # COLLADA 1.5 permits an inner <ref> element.
                if not value:
                    value = next(((child.text or "").strip() for child in init if tag(child) == "ref"), "")
                asset = self.resolve(value, path)
                if asset is not None and not asset.is_file():
                    self.error(path, "image is not a file: " + value)
        # External geometry/controller documents are dependencies as well.
        for node in root.iter():
            for key in ("url", "source"):
                value = node.get(key, "")
                if value and not value.startswith("#"):
                    document = value.split("#", 1)[0]
                    if document:
                        asset = self.resolve(document, path)
                        if asset is not None:
                            self.asset(asset)

    def texture(self, value, material, directories):
        if not self.portable(value, material):
            return
        if "://" in value or Path(value).is_absolute():
            path = self.resolve(value, material)
            if path is not None and not path.is_file():
                self.error(material, "texture is not a file: " + value)
            return
        model_dir = next((p for p in material.parents if (p / "model.config").is_file()), material.parent)
        roots = {material.parent, model_dir / "materials" / "textures", model_dir / "textures"}
        roots.update(directories)
        candidates = {(root / unquote(value)).resolve() for root in roots if (root / unquote(value)).is_file()}
        if not candidates:
            self.error(material, "missing Ogre texture: " + value)
        elif len(candidates) != 1:
            self.error(material, "ambiguous Ogre texture {}: {}".format(value, ", ".join(sorted(self.label(p) for p in candidates))))
        else:
            path = next(iter(candidates))
            if not inside(path, self.repo):
                self.error(material, "texture escapes repository: " + value)
            else:
                self.assets.add(path)

    def material(self, path, directories):
        key = (path, tuple(sorted(directories)))
        if key in self.checked_materials:
            return
        self.checked_materials.add(key)
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            self.error(path, "cannot read material: " + str(exc))
            return
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        for number, line in enumerate(content.splitlines(), 1):
            line = re.sub(r"(^|\s)//.*$", "", line).strip()
            if not line:
                continue
            self.portable(line, path)
            try:
                parts = shlex.split(line, comments=False)
            except ValueError as exc:
                self.error(path, "invalid material syntax at line {}: {}".format(number, exc))
                continue
            if parts and parts[0] == "texture":
                if len(parts) < 2:
                    self.error(path, "empty texture at line " + str(number))
                else:
                    self.texture(parts[1], path, directories)
            elif parts and parts[0] in {"anim_texture", "cubic_texture"}:
                self.error(path, "unsupported texture directive requires explicit validation: " + parts[0])
            elif len(parts) >= 4 and parts[0] == "import" and parts[-2] == "from":
                imported = self.resolve(parts[-1], path)
                if imported is not None:
                    self.material(imported, directories)

    def run(self):
        for name, expected in SCENES.items():
            path = self.repo / "worlds" / "worlds" / (name + ".world")
            root = self.xml(path)
            if root is None:
                continue
            world = root.find("world")
            if world is None:
                self.error(path, "missing world element")
                continue
            count = len(world.findall("include"))
            if count != expected:
                self.error(path, "expected {} includes, found {}".format(expected, count))
            plugins = [p.get("filename", "") for p in world.iter("plugin")]
            if name in WATER_SCENES and plugins.count(WATER_PLUGIN) != 1:
                self.error(path, "expected one " + WATER_PLUGIN)
            self.scenes[name] = {"includes": count, "plugins": plugins}
            self.sdf(path, root)
        return {
            "passed": not self.errors,
            "scenes": self.scenes,
            "checked": {
                "models": len(self.checked_models),
                "xml_files": len(self.checked_xml),
                "collada_meshes": len(self.checked_dae),
                "material_files": len({p for p, _ in self.checked_materials}),
                "asset_paths": len(self.assets),
                "liquid_water_links": len(self.water_links),
            },
            "errors": sorted(self.errors),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1], help="repository root (defaults to this script's repository)")
    args = parser.parse_args()
    result = Validator(args.repo).run()
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
