#!/usr/bin/env python3
"""Shared helpers for the Cat Dash procedural art generators (Agent B, batch CD-B1).

Used by:
    blender --background --python tool/blender_cat.py     -- --output Assets/Art/Generated/Cat.fbx
    blender --background --python tool/blender_propset.py -- --asset crate   --output Assets/Art/Generated/Prop_Crate.fbx
    blender --background --python tool/blender_road.py    -- --output Assets/Art/Generated/Road_Segment.fbx

Nothing here talks to the network, Unity or CI. Geometry is authored explicitly
(vertices/faces/UVs written by this code), so tri budgets and the texture atlas
layout are deterministic and reviewable instead of depending on an operator's
viewport. `bpy` is imported lazily so the module stays importable, and
`python3 tool/preflight.py` can still syntax-check it outside Blender.

Conventions
-----------
* Blender axes while authoring: +X right, +Y back, +Z up. The cat faces -Y.
* Exported with axis_forward='-Z', axis_up='Y' (the same Unity preset the kit's
  tool/blender_props.py uses) => Unity: +X right, +Y up, +Z forward, so the cat
  faces Unity +Z and the road runs along Unity Z.
* Every asset is modelled in metres with its pivot documented per asset.
* Textures are 8-bit sRGB PNG, <= 1024 px, no HDR, generated procedurally here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

try:  # present only inside Blender; the geometry/texture helpers work without it
    import bpy  # type: ignore
except ImportError:  # pragma: no cover - outside Blender
    bpy = None


# --------------------------------------------------------------------------- #
# Repo plumbing: deterministic GUIDs and hand-written .meta files
# --------------------------------------------------------------------------- #
META_NAMESPACE = "catdash-agent-b:"


def repo_root(start: Path) -> Path:
    """Walk up from a path until the repo marker file is found."""
    for candidate in [start, *start.parents]:
        if (candidate / "unity-kit.json").is_file():
            return candidate
    raise SystemExit(f"error: no unity-kit.json above {start}; run from inside the repo")


def guid_for(target: Path) -> str:
    """Deterministic, collision-checked-by-preflight GUID derived from the repo path."""
    root = repo_root(target)
    rel = target.resolve().relative_to(root).as_posix()
    return hashlib.md5((META_NAMESPACE + rel).encode()).hexdigest()


def write_text_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def folder_meta(target: Path) -> str:
    return (f"fileFormatVersion: 2\nguid: {guid_for(target)}\nfolderAsset: yes\n"
            "DefaultImporter:\n  externalObjects: {}\n  userData:\n"
            "  assetBundleName:\n  assetBundleVariant:\n")


def png_meta(target: Path, max_size: int) -> str:
    return (f"fileFormatVersion: 2\nguid: {guid_for(target)}\nTextureImporter:\n"
            "  serializedVersion: 13\n"
            "  mipmaps:\n    mipMapMode: 0\n    enableMipMap: 1\n"
            "    sRGBTexture: 1\n    linearTexture: 0\n    fadeOut: 0\n"
            "    borderMipMap: 0\n    mipMapsPreserveCoverage: 0\n    alphaTestReferenceValue: 0.5\n"
            "    mipMapFadeDistanceStart: 1\n    mipMapFadeDistanceEnd: 3\n"
            f"  maxTextureSize: {max_size}\n  textureCompression: 1\n"
            "  compressionQuality: 50\n  textureType: 0\n  textureShape: 1\n"
            "  singleChannelComponent: 0\n  flipbookRows: 1\n  flipbookColumns: 1\n"
            "  sRGBTexture: 1\n  alphaSource: 1\n  alphaIsTransparency: 0\n"
            "  isReadable: 0\n  streamingMipmaps: 0\n  streamingMipmapsPriority: 0\n"
            "  wrapU: 1\n  wrapV: 1\n  wrapW: 1\n  filterMode: -1\n  aniso: 1\n"
            "  mipBias: 0\n  npotScale: 0\n  spriteImportMode: 0\n"
            "  generateCubemap: 6\n  cubemapConvolution: 0\n  seamlessCubemap: 0\n"
            "  userData:\n  assetBundleName:\n  assetBundleVariant:\n")


def model_meta(target: Path) -> str:
    """Minimal ModelImporter meta; Unity normalises the rest on first import."""
    return (f"fileFormatVersion: 2\nguid: {guid_for(target)}\nModelImporter:\n"
            "  serializedVersion: 22200\n  internalIDToNameTable: []\n"
            "  materials:\n    materialImportMode: 2\n    materialName: 0\n"
            "    materialSearch: 0\n    materialLocation: 1\n"
            "  animations:\n    legacyGenerateAnimations: 4\n    bakeSimulation: 0\n"
            "    optimizeGameObjects: 0\n    animationCompression: 1\n"
            "    animationPositionError: 0.5\n    animationRotationError: 0.5\n"
            "    animationScaleError: 0.5\n  importAnimation: 0\n"
            "  importBlendShapeDeformPercent: 0\n  importBlendShapes: 0\n"
            "  importCameras: 0\n  importLights: 0\n  importVisibility: 0\n"
            "  importConstraints: 0\n  importNormals: 0\n  importTangents: 0\n"
            "  importAnimatedCustomProperties: 0\n  importMaterials: 1\n"
            "  importSkeleton: 0\n  addCollider: 0\n  meshCompression: 0\n"
            # isReadable = Read/Write Enabled. The art tests read mesh.triangles, and a
            # non-readable mesh returns an EMPTY array instead of throwing, which would
            # make a triangle-budget assertion pass at zero. These meshes are tiny.
            "  isReadable: 1\n  optimizeMeshPolygons: 1\n  optimizeMeshVertices: 1\n"
            "  weldVertices: 1\n  keepQuads: 0\n  swapUVChannels: 0\n"
            "  generateSecondaryUV: 0\n  useFileScale: 1\n  fileScale: 1\n"
            "  globalScale: 1\n  useFileUnits: 1\n  bakeAxisConversion: 0\n"
            "  meshOptimizationFlags: -1\n  skinWeights: 4\n  maxBonesPerVertex: 4\n"
            "  minBoneWeight: 0.001\n  optimizeBones: 1\n  meshSmoothingAngle: 60\n"
            "  appendAnchor: 0\n  externalObjects: {}\n  userData:\n"
            "  assetBundleName:\n  assetBundleVariant:\n")


def cs_meta(target: Path) -> str:
    return (f"fileFormatVersion: 2\nguid: {guid_for(target)}\nMonoImporter:\n"
            "  externalObjects: {}\n  serializedVersion: 2\n  defaultReferences: []\n"
            "  executionOrder: 0\n  icon: {instanceID: 0}\n  userData:\n"
            "  assetBundleName:\n  assetBundleVariant:\n")


def text_meta(target: Path) -> str:
    return (f"fileFormatVersion: 2\nguid: {guid_for(target)}\nTextScriptImporter:\n"
            "  externalObjects: {}\n  userData:\n  assetBundleName:\n"
            "  assetBundleVariant:\n")


def ensure_asset_folders(paths, kinds=("folder",)) -> list[str]:
    """Create missing Assets/ folder metas for every parent of the given targets."""
    created = []
    for target in paths:
        root = repo_root(target)
        parents = [p for p in target.parents if p.is_relative_to(root / "Assets")]
        for folder in reversed(parents):
            if folder.name == "Assets":
                continue
            meta = folder.with_name(folder.name + ".meta")
            if not meta.exists():
                write_text_file(meta, folder_meta(folder))
                created.append(str(meta.relative_to(root)))
    return created


def write_asset_meta(target: Path, kind: str, max_size: int = 1024) -> str:
    writers = {"folder": lambda p: folder_meta(p),
               "png": lambda p: png_meta(p, max_size),
               "model": lambda p: model_meta(p),
               "cs": lambda p: cs_meta(p),
               "text": lambda p: text_meta(p)}
    meta = target.with_name(target.name + ".meta")
    write_text_file(meta, writers[kind](target))
    return str(meta.relative_to(repo_root(target)))


# --------------------------------------------------------------------------- #
# PNG output + procedural texture painting
# --------------------------------------------------------------------------- #
def _png_chunks(width: int, height: int, rows: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


class Canvas:
    """Tiny deterministic painter. u,v are UV coordinates with v=0 at the bottom,
    which is flipped to PNG row order on save."""

    def __init__(self, size: int, seed: int = 7):
        self.size = int(size)
        self.px = np.zeros((self.size, self.size, 3), dtype=np.float32)
        self.rng = np.random.default_rng(seed)

    # -- region helpers ----------------------------------------------------- #
    def _bounds(self, u0, v0, u1, v1):
        n = self.size
        x0 = int(round(min(u0, u1) * n)); x1 = int(round(max(u0, u1) * n))
        y0 = int(round(min(v0, v1) * n)); y1 = int(round(max(v0, v1) * n))
        if x1 > n: x1 = n
        if y1 > n: y1 = n
        return max(x0, 0), max(x1, x0 + 1), max(y0, 0), max(y1, y0 + 1)

    def fill(self, u0, v0, u1, v1, rgb):
        x0, x1, y0, y1 = self._bounds(u0, v0, u1, v1)
        self.px[y0:y1, x0:x1] = np.asarray(rgb, dtype=np.float32)

    def blend(self, u0, v0, u1, v1, rgb, alpha):
        x0, x1, y0, y1 = self._bounds(u0, v0, u1, v1)
        colour = np.asarray(rgb, dtype=np.float32)
        self.px[y0:y1, x0:x1] = (1.0 - alpha) * self.px[y0:y1, x0:x1] + alpha * colour

    def vgrad(self, u0, v0, u1, v1, rgb_lo, rgb_hi):
        """Vertical gradient across the region (v0 -> rgb_lo, v1 -> rgb_hi)."""
        x0, x1, y0, y1 = self._bounds(u0, v0, u1, v1)
        rows = np.linspace(0.0, 1.0, y1 - y0, dtype=np.float32).reshape(-1, 1, 1)
        lo = np.asarray(rgb_lo, dtype=np.float32); hi = np.asarray(rgb_hi, dtype=np.float32)
        self.px[y0:y1, x0:x1] = (1.0 - rows) * lo + rows * hi

    def hgrad(self, u0, v0, u1, v1, rgb_lo, rgb_hi):
        x0, x1, y0, y1 = self._bounds(u0, v0, u1, v1)
        cols = np.linspace(0.0, 1.0, x1 - x0, dtype=np.float32).reshape(1, -1, 1)
        lo = np.asarray(rgb_lo, dtype=np.float32); hi = np.asarray(rgb_hi, dtype=np.float32)
        self.px[y0:y1, x0:x1] = (1.0 - cols) * lo + cols * hi

    def ellipse(self, cu, cv, ru, rv, rgb, alpha=1.0):
        n = self.size
        y0 = max(int((cv - rv) * n) - 1, 0); y1 = min(int((cv + rv) * n) + 2, n)
        x0 = max(int((cu - ru) * n) - 1, 0); x1 = min(int((cu + ru) * n) + 2, n)
        if x1 <= x0 or y1 <= y0:
            return
        ys = ((np.arange(y0, y1) + 0.5) / n - cv) / max(rv, 1e-6)
        xs = ((np.arange(x0, x1) + 0.5) / n - cu) / max(ru, 1e-6)
        d = np.sqrt(xs[None, :] ** 2 + ys[:, None] ** 2)
        mask = np.clip(1.5 - 1.5 * d, 0.0, 1.0)[:, :, None]
        region = self.px[y0:y1, x0:x1]
        colour = np.asarray(rgb, dtype=np.float32)
        self.px[y0:y1, x0:x1] = region * (1.0 - mask * alpha) + colour * (mask * alpha)

    def bands_y(self, u0, u1, v_centres, half_height, rgb, alpha=1.0, feather=0.008):
        """Horizontal stripe bands (wrap around a body: constant texture v)."""
        for centre in v_centres:
            self.blend(u0, centre - half_height - feather, u1, centre - half_height + feather,
                       rgb, alpha * 0.5)
            self.blend(u0, centre - half_height + feather, u1, centre + half_height - feather,
                       rgb, alpha)
            self.blend(u0, centre + half_height - feather, u1, centre + half_height + feather,
                       rgb, alpha * 0.5)

    def bands_x(self, v0, v1, u_centres, half_width, rgb, alpha=1.0, feather=0.008):
        for centre in u_centres:
            self.blend(centre - half_width - feather, v0, centre - half_width + feather, v1,
                       rgb, alpha * 0.5)
            self.blend(centre - half_width + feather, v0, centre + half_width - feather, v1, rgb, alpha)
            self.blend(centre + half_width - feather, v0, centre + half_width + feather, v1,
                       rgb, alpha * 0.5)

    def grain(self, u0, v0, u1, v1, amount=0.03, cells=96, blur=2):
        """Deterministic value-noise grain over a region (keeps flat colours alive)."""
        x0, x1, y0, y1 = self._bounds(u0, v0, u1, v1)
        noise = self.rng.random((max(cells, 2), max(cells, 2)), dtype=np.float32)
        reps = int(np.ceil(max(x1 - x0, y1 - y0) / max(cells, 2))) + 1
        noise = np.repeat(np.repeat(noise, reps, axis=0), reps, axis=1)
        for _ in range(max(blur, 0)):
            noise = (np.roll(noise, 1, 0) + np.roll(noise, -1, 0)
                     + np.roll(noise, 1, 1) + np.roll(noise, -1, 1) + 4 * noise) / 8.0
        patch = noise[: y1 - y0, : x1 - x0, None] - 0.5
        self.px[y0:y1, x0:x1] = np.clip(self.px[y0:y1, x0:x1] * (1.0 + amount * 2.0 * patch), 0.0, 1.0)

    def grain_tiled(self, u0, v0, u1, v1, amount=0.04, block=64):
        """Like grain(), but the noise tiles exactly, so a texture that wraps along
        an axis stays seamless there."""
        x0, x1, y0, y1 = self._bounds(u0, v0, u1, v1)
        base = self.rng.random((block, block), dtype=np.float32)
        reps_y = int(np.ceil((y1 - y0) / block))
        reps_x = int(np.ceil((x1 - x0) / block))
        noise = np.tile(base, (reps_y, reps_x))[: y1 - y0, : x1 - x0, None] - 0.5
        self.px[y0:y1, x0:x1] = np.clip(self.px[y0:y1, x0:x1] * (1.0 + amount * 2.0 * noise),
                                        0.0, 1.0)

    def diagonal_stripes(self, u0, v0, u1, v1, rgb_a, rgb_b, period=0.08, slope=1.0):
        """Two-colour diagonal banding (hazard stripes on barrier boards)."""
        x0, x1, y0, y1 = self._bounds(u0, v0, u1, v1)
        ys, xs = np.meshgrid(np.arange(y0, y1, dtype=np.float32),
                             np.arange(x0, x1, dtype=np.float32), indexing="ij")
        phase = ((xs + ys * slope) / (max(period, 1e-3) * self.size)) % 1.0
        band = np.where(phase < 0.5, 0.0, 1.0)[:, :, None]
        a = np.asarray(rgb_a, dtype=np.float32)
        b = np.asarray(rgb_b, dtype=np.float32)
        self.px[y0:y1, x0:x1] = (1.0 - band) * a + band * b

    def segment(self, u0, v0, u1, v1, rgb, thickness=0.02, alpha=1.0):
        """Thick line from (u0,v0) to (u1,v1) in texture space (brace bars)."""
        n = self.size
        steps = max(int(np.hypot((u1 - u0) * n, (v1 - v0) * n) * 2), 8)
        for i in range(steps + 1):
            t = i / steps
            self.ellipse(u0 + (u1 - u0) * t, v0 + (v1 - v0) * t, thickness, thickness, rgb,
                         alpha)

    def speckle(self, u0, v0, u1, v1, rgb, count=180, radius=0.003, alpha=0.5):
        x0, x1, y0, y1 = self._bounds(u0, v0, u1, v1)
        for _ in range(count):
            u = (x0 + self.rng.random() * (x1 - x0)) / self.size
            v = (y0 + self.rng.random() * (y1 - y0)) / self.size
            self.ellipse(u, v, radius * (0.4 + self.rng.random()), radius * (0.4 + self.rng.random()),
                         rgb, alpha)

    def rectangle(self, u0, v0, u1, v1, rgb, alpha=1.0):
        self.blend(u0, v0, u1, v1, rgb, alpha)

    def mirror_tile(self, u0, v0, u1, v1):
        """Force the region's left edge to match its right edge (seam-safe wrap)."""
        x0, x1, y0, y1 = self._bounds(u0, v0, u1, v1)
        self.px[y0:y1, x0] = self.px[y0:y1, x1 - 1]

    def save(self, path: Path) -> None:
        rgb = np.clip(self.px[::-1] * 255.0 + 0.5, 0.0, 255.0).astype(np.uint8)
        rows = b"".join(b"\x00" + rgb[y].tobytes() for y in range(rgb.shape[0]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_png_chunks(rgb.shape[1], rgb.shape[0], rows))


def srgb(hex_colour: str):
    """'#RRGGBB' -> linear-ish float triple (values are authored as sRGB display
    colours and stored as-is; Unity reads the PNG as sRGB, so we keep them raw)."""
    value = hex_colour.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


# --------------------------------------------------------------------------- #
# Geometry: explicit verts/faces/UVs
# --------------------------------------------------------------------------- #
class Part:
    """A chunk of geometry: vertices, polygon index lists, per-polygon UV lists."""

    def __init__(self, verts, faces, face_uvs):
        self.verts = [tuple(map(float, v)) for v in verts]
        self.faces = [list(map(int, f)) for f in faces]
        self.face_uvs = [[tuple(map(float, uv)) for uv in f] for f in face_uvs]
        if len(self.faces) != len(self.face_uvs):
            raise ValueError("faces and face_uvs length mismatch")
        for face, uvs in zip(self.faces, self.face_uvs):
            if len(face) != len(uvs):
                raise ValueError("polygon/uv count mismatch")

    def tri_count(self) -> int:
        return sum(len(f) - 2 for f in self.faces)

    def transformed(self, offset=(0.0, 0.0, 0.0), rot_z=0.0, rot_x=0.0, rot_y=0.0):
        """Rotate about Y, then Z, then X, then translate.

        rot_x splays front/back legs (trestle), rot_y tilts left/right parts outward
        (ears, eyes), rot_z yaws them.
        """
        cx, cy, cz = offset
        cos_y, sin_y = math.cos(rot_y), math.sin(rot_y)
        cos_z, sin_z = math.cos(rot_z), math.sin(rot_z)
        cos_x, sin_x = math.cos(rot_x), math.sin(rot_x)
        verts = []
        for x, y, z in self.verts:
            xr, zr = x * cos_y + z * sin_y, -x * sin_y + z * cos_y
            xr, yr = xr * cos_z - y * sin_z, xr * sin_z + y * cos_z
            yr, zr = yr * cos_x - zr * sin_x, yr * sin_x + zr * cos_x
            verts.append((xr + cx, yr + cy, zr + cz))
        return Part(verts, self.faces, self.face_uvs)

    def mirrored_x(self):
        faces = [list(reversed(f)) for f in self.faces]
        uvs = [list(reversed(u)) for u in self.face_uvs]
        return Part([(-x, y, z) for x, y, z in self.verts], faces, uvs)

    def signed_volume(self) -> float:
        total = 0.0
        for face in self.faces:
            for i in range(1, len(face) - 1):
                a = self.verts[face[0]]; b = self.verts[face[i]]; c = self.verts[face[i + 1]]
                total += (a[0] * (b[1] * c[2] - b[2] * c[1])
                          - a[1] * (b[0] * c[2] - b[2] * c[0])
                          + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
        return total

    def ensure_outward(self) -> "Part":
        """Winding sanity check: closed meshes must have positive signed volume."""
        if self.signed_volume() >= 0.0:
            return self
        return Part(self.verts, [list(reversed(f)) for f in self.faces],
                    [list(reversed(u)) for u in self.face_uvs])

    def bounds(self):
        xs = [v[0] for v in self.verts]; ys = [v[1] for v in self.verts]; zs = [v[2] for v in self.verts]
        return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def combine(parts) -> Part:
    verts, faces, uvs = [], [], []
    for part in parts:
        base = len(verts)
        verts.extend(part.verts)
        faces.extend([[i + base for i in f] for f in part.faces])
        uvs.extend(part.face_uvs)
    return Part(verts, faces, uvs)


# --- primitive builders ----------------------------------------------------- #
_CUBE_FACES = [[1, 3, 7, 5], [0, 4, 6, 2], [2, 6, 7, 3], [0, 1, 5, 4], [4, 5, 7, 6], [0, 2, 3, 1]]


def box(size, center=(0.0, 0.0, 0.0), uv=(0.0, 0.0, 1.0, 1.0), faces_uv=None):
    """Axis-aligned box. `uv` (u0,v0,u1,v1) is used for every face unless
    `faces_uv` gives one rect per face in the order +X,-X,+Y,-Y,+Z,-Z."""
    sx, sy, sz = (s * 0.5 for s in size)
    cx, cy, cz = center
    corners = []
    for bits in range(8):
        corners.append((cx + (sx if bits & 1 else -sx),
                        cy + (sy if bits & 2 else -sy),
                        cz + (sz if bits & 4 else -sz)))
    rects = faces_uv if faces_uv is not None else [uv] * 6
    face_uvs = []
    for rect in rects:
        u0, v0, u1, v1 = rect
        face_uvs.append([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    return Part(corners, _CUBE_FACES, face_uvs).ensure_outward()


def _frame(tangent, hint):
    t = np.asarray(tangent, dtype=np.float64)
    t /= np.linalg.norm(t) + 1e-12
    h = np.asarray(hint, dtype=np.float64)
    h /= np.linalg.norm(h) + 1e-12
    if abs(float(np.dot(t, h))) > 0.98:  # hint parallel to the path: pick another axis
        for candidate in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)):
            c = np.asarray(candidate, dtype=np.float64)
            if abs(float(np.dot(t, c))) < 0.9:
                h = c
                break
    side = np.cross(h, t)
    side /= np.linalg.norm(side) + 1e-12
    up = np.cross(t, side)
    up /= np.linalg.norm(up) + 1e-12
    return side, up


def tube(path, radii, segments, u_range, ring_v, phase=0.0, caps=(True, True),
         hint=(0.0, 0.0, 1.0), squash=1.0):
    """Closed tube through `path` (list of 3-tuples) with per-ring `radii`.

    Ring UV u runs from u_range[0] at angle `phase` counter-clockwise around the
    tube axis; each ring's v comes from `ring_v`. `squash` scales the local
    second axis (elliptical cross-section, e.g. the cat's body)."""
    pts = [np.asarray(p, dtype=np.float64) for p in path]
    verts, faces, face_uvs = [], [], []
    u0, u1 = u_range
    ring_index = []
    for i, point in enumerate(pts):
        if i == 0:
            tangent = pts[1] - pts[0]
        elif i == len(pts) - 1:
            tangent = pts[-1] - pts[-2]
        else:
            tangent = pts[i + 1] - pts[i - 1]
        side, up = _frame(tangent, hint)
        base = len(verts)
        ring_index.append(base)
        radius = radii[i]
        v = ring_v[i]
        for k in range(segments):
            angle = phase + 2.0 * math.pi * k / segments
            offset = math.cos(angle) * radius * side + math.sin(angle) * radius * squash * up
            verts.append(tuple(point + offset))
    for i in range(len(pts) - 1):
        a, b = ring_index[i], ring_index[i + 1]
        va, vb = ring_v[i], ring_v[i + 1]
        for k in range(segments):
            k2 = (k + 1) % segments
            ua = u0 + (u1 - u0) * (k / segments)
            ub = u0 + (u1 - u0) * ((k + 1) / segments)
            faces.append([a + k, a + k2, b + k2, b + k])
            face_uvs.append([(ua, va), (ub, va), (ub, vb), (ua, vb)])
    start_cap, end_cap = caps
    if start_cap:
        centre = len(verts)
        verts.append(tuple(pts[0]))
        cu = u0 + (u1 - u0) * 0.5
        for k in range(segments):
            k2 = (k + 1) % segments
            faces.append([centre, ring_index[0] + k2, ring_index[0] + k])
            face_uvs.append([(cu, ring_v[0]), (u0 + (u1 - u0) * ((k + 1) / segments), ring_v[0]),
                             (u0 + (u1 - u0) * (k / segments), ring_v[0])])
    if end_cap:
        centre = len(verts)
        verts.append(tuple(pts[-1]))
        cu = u0 + (u1 - u0) * 0.5
        for k in range(segments):
            k2 = (k + 1) % segments
            faces.append([centre, ring_index[-1] + k, ring_index[-1] + k2])
            face_uvs.append([(cu, ring_v[-1]), (u0 + (u1 - u0) * (k / segments), ring_v[-1]),
                             (u0 + (u1 - u0) * ((k + 1) / segments), ring_v[-1])])
    return Part(verts, faces, face_uvs).ensure_outward()


def sphere(center, radii, segments=12, rows=8, u_range=(0.0, 1.0), v_range=(0.0, 1.0),
           phase=0.0):
    """Lat-long sphere. u wraps around (u_range maps the full 360 degrees); v is
    latitude from the south pole (v_range[0]) to the north pole (v_range[1])."""
    cx, cy, cz = center
    rx, ry, rz = radii
    verts, faces, face_uvs = [], [], []
    ring_index = []
    for j in range(1, rows):
        lat = math.pi * j / rows
        v = v_range[0] + (v_range[1] - v_range[0]) * (j / rows)
        ring_index.append(len(verts))
        for k in range(segments):
            u_frac = k / segments
            angle = phase + 2.0 * math.pi * u_frac
            verts.append((cx + rx * math.sin(lat) * math.sin(angle),
                          cy - ry * math.sin(lat) * math.cos(angle),
                          cz + rz * math.cos(lat)))
    south = len(verts); verts.append((cx, cy, cz - rz))
    north = len(verts); verts.append((cx, cy, cz + rz))

    def u_of(k):
        return u_range[0] + (u_range[1] - u_range[0]) * (k / segments)

    for k in range(segments):
        k2 = (k + 1) % segments
        faces.append([south, ring_index[0] + k2, ring_index[0] + k])
        face_uvs.append([(u_range[0] + (u_range[1] - u_range[0]) * 0.5, v_range[0]),
                         (u_of(k2), v_range[0] + (v_range[1] - v_range[0]) / rows),
                         (u_of(k), v_range[0] + (v_range[1] - v_range[0]) / rows)])
    for j in range(len(ring_index) - 1):
        a, b = ring_index[j], ring_index[j + 1]
        va = v_range[0] + (v_range[1] - v_range[0]) * ((j + 1) / rows)
        vb = v_range[0] + (v_range[1] - v_range[0]) * ((j + 2) / rows)
        for k in range(segments):
            k2 = (k + 1) % segments
            faces.append([a + k, a + k2, b + k2, b + k])
            face_uvs.append([(u_of(k), va), (u_of(k2), va), (u_of(k2), vb), (u_of(k), vb)])
    last = ring_index[-1]
    v_last = v_range[0] + (v_range[1] - v_range[0]) * ((rows - 1) / rows)
    for k in range(segments):
        k2 = (k + 1) % segments
        faces.append([north, last + k, last + k2])
        face_uvs.append([(u_range[0] + (u_range[1] - u_range[0]) * 0.5, v_range[1]),
                         (u_of(k), v_last), (u_of(k2), v_last)])
    return Part(verts, faces, face_uvs).ensure_outward()


def pyramid(base_center, base_size, apex, uv_out, uv_in):
    """Square-base pyramid; -Y side (and the base) uses uv_in, the rest uv_out."""
    cx, cy, cz = base_center
    hw, hd = base_size[0] * 0.5, base_size[1] * 0.5
    corners = [(cx - hw, cy - hd, cz), (cx + hw, cy - hd, cz),
               (cx + hw, cy + hd, cz), (cx - hw, cy + hd, cz)]
    verts = corners + [tuple(apex)]

    def quad(rect):
        u0, v0, u1, v1 = rect
        return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]

    faces = [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4], [0, 3, 2, 1]]
    face_uvs = [quad(uv_in)[:3], quad(uv_out)[:3], quad(uv_out)[:3], quad(uv_in)[:3],
                quad(uv_in)]
    return Part(verts, faces, face_uvs).ensure_outward()


def prism(profile, rings, uv_side, uv_cap_start=None, uv_cap_end=None):
    """Extrude a 2D `profile` (list of local (x, y) pairs, CCW, closed) along Z.

    `rings` is a list of (z, scale) pairs (scale shrinks the profile, e.g. a chamfer).
    Side UVs run u along the closed perimeter (proportional to edge length) and v
    across the rings, so texture features can be placed at exact perimeter
    fractions. Caps use uv_cap_start/uv_cap_end (default: uv_side)."""
    count = len(profile)
    ring_index = []
    verts, faces, face_uvs = [], [], []
    lengths = []
    for i in range(count):
        x0, y0 = profile[i]
        x1, y1 = profile[(i + 1) % count]
        lengths.append(math.hypot(x1 - x0, y1 - y0))
    total = sum(lengths)
    u_at = [0.0]
    for length in lengths:
        u_at.append(u_at[-1] + length / total)
    u0, v0, u1, v1 = uv_side
    for z, scale in rings:
        ring_index.append(len(verts))
        for x, y in profile:
            verts.append((x * scale, y * scale, z))
    for j in range(len(rings) - 1):
        a, b = ring_index[j], ring_index[j + 1]
        va = v0 + (v1 - v0) * (j / (len(rings) - 1))
        vb = v0 + (v1 - v0) * ((j + 1) / (len(rings) - 1))
        for i in range(count):
            i2 = (i + 1) % count
            faces.append([a + i, a + i2, b + i2, b + i])
            face_uvs.append([(u0 + (u1 - u0) * u_at[i], va), (u0 + (u1 - u0) * u_at[i + 1], va),
                             (u0 + (u1 - u0) * u_at[i + 1], vb), (u0 + (u1 - u0) * u_at[i], vb)])
    for which, rect, flip in (("start", uv_cap_start or uv_side, True),
                              ("end", uv_cap_end or uv_side, False)):
        if rect is None:
            continue
        cu0, cv0, cu1, cv1 = rect
        centre = len(verts)
        z, _ = rings[0] if which == "start" else rings[-1]
        verts.append((0.0, 0.0, z))
        ring = ring_index[0] if which == "start" else ring_index[-1]
        rmax = max(math.hypot(px, py) for px, py in profile) or 1.0
        cap_uv = [((cu0 + cu1) * 0.5 + (cu1 - cu0) * 0.5 * px / rmax,
                   (cv0 + cv1) * 0.5 + (cv1 - cv0) * 0.5 * py / rmax)
                  for px, py in profile]
        cap_uv = [((cu0 + cu1) * 0.5, (cv0 + cv1) * 0.5)] + cap_uv
        for i in range(count):
            i2 = (i + 1) % count
            order = [centre, ring + (i2 if flip else i), ring + (i if flip else i2)]
            faces.append(order)
            face_uvs.append([cap_uv[0] if flip else cap_uv[0],
                             cap_uv[1 + (i2 if flip else i)], cap_uv[1 + (i if flip else i2)]])
    return Part(verts, faces, face_uvs).ensure_outward()


def annulus(center, r_inner, r_outer, segments, uv, phase=0.0, facing=1.0):
    """Flat ring of quads at z=center[2], facing +Z (facing=-1 flips it)."""
    cx, cy, cz = center
    verts, faces, face_uvs = [], [], []
    u0, v0, u1, v1 = uv
    for i in range(segments):
        angle = phase + 2.0 * math.pi * i / segments
        ca, sa = math.cos(angle), math.sin(angle)
        verts.append((cx + r_inner * ca, cy + r_inner * sa, cz))
        verts.append((cx + r_outer * ca, cy + r_outer * sa, cz))
        _ = (ca, sa)
    for i in range(segments):
        i2 = (i + 1) % segments
        a, b = 2 * i, 2 * i + 1
        c, d = 2 * i2, 2 * i2 + 1
        if facing > 0:
            faces.append([b, d, c, a])
        else:
            faces.append([a, c, d, b])
        ua = u0 + (u1 - u0) * (i / segments)
        ub = u0 + (u1 - u0) * ((i + 1) / segments)
        face_uvs.append([(ua, v0), (ub, v0), (ub, v1), (ua, v1)])
    return Part(verts, faces, face_uvs)


def disc(center, radius, segments, uv, phase=0.0, facing=1.0, rings=1):
    """Flat n-gon fan at z=center[2] facing +Z (facing=-1 flips it)."""
    cx, cy, cz = center
    u0, v0, u1, v1 = uv
    verts = [(cx, cy, cz)]
    faces, face_uvs = [], []
    cu, cv = (u0 + u1) * 0.5, (v0 + v1) * 0.5
    for i in range(segments):
        angle = phase + 2.0 * math.pi * i / segments
        verts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle), cz))
    half_u, half_v = (u1 - u0) * 0.5, (v1 - v0) * 0.5
    for i in range(segments):
        i2 = (i + 1) % segments
        faces.append([0, i + 1, i2 + 1] if facing > 0 else [0, i2 + 1, i + 1])
        angle_a = phase + 2.0 * math.pi * i / segments
        angle_b = phase + 2.0 * math.pi * i2 / segments
        face_uvs.append([(cu, cv),
                         (cu + half_u * math.cos(angle_a), cv + half_v * math.sin(angle_a)),
                         (cu + half_u * math.cos(angle_b), cv + half_v * math.sin(angle_b))])
    _ = rings
    return Part(verts, faces, face_uvs)


def planar_uv(part, x0, y0, x1, y1):
    """Re-project a part top-down: u,v from world (x, y). Used for road slabs,
    where every surface is either horizontal or a thin vertical edge."""
    uvs = []
    for face_uv, face in zip(part.face_uvs, part.faces):
        rebuilt = []
        for vertex in face:
            x, y, _ = part.verts[vertex]
            rebuilt.append(((x - x0) / (x1 - x0), (y - y0) / (y1 - y0)))
        uvs.append(rebuilt)
    return Part(part.verts, part.faces, uvs)


# --------------------------------------------------------------------------- #
# Blender scene plumbing
# --------------------------------------------------------------------------- #
def reset_scene():
    require_blender()
    bpy.ops.wm.read_factory_settings(use_empty=True)


def require_blender():
    if bpy is None:
        raise SystemExit("error: this script must run inside Blender "
                         "(blender --background --python tool/blender_<asset>.py -- ...)")


def make_object(name, part: Part, material=None, smooth=False, parent=None):
    require_blender()
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in part.verts], [], [list(f) for f in part.faces])
    mesh.validate(verbose=False)
    if len(mesh.polygons) != len(part.faces):
        raise SystemExit(f"error: {name}: mesh.validate() dropped geometry "
                         f"({len(mesh.polygons)} of {len(part.faces)} polygons kept)")
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for poly, uvs in zip(mesh.polygons, part.face_uvs):
        poly.use_smooth = smooth
        for loop, uv in zip(poly.loop_indices, uvs):
            uv_layer.data[loop].uv = uv
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if material is not None:
        obj.data.materials.append(material)
    if parent is not None:
        obj.parent = parent
    return obj


def make_empty(name):
    require_blender()
    empty = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(empty)
    return empty


def make_material(name, image_path: Path | None, base_colour, roughness=0.75, metallic=0.0):
    require_blender()
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*base_colour, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    material.diffuse_color = (*base_colour, 1.0)
    material.roughness = roughness
    if image_path is not None:
        image = bpy.data.images.load(str(image_path))
        texture = nodes.new("ShaderNodeTexImage")
        texture.image = image
        texture.location = (-350, 200)
        material.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    return material


def export_fbx(path: Path, object_names=None):
    require_blender()
    for obj in bpy.context.scene.objects:
        obj.select_set(True)
    if object_names:
        for obj in bpy.context.scene.objects:
            obj.select_set(obj.name in object_names)
    wanted = {
        "filepath": str(path), "use_selection": True,
        "object_types": {"MESH", "EMPTY"}, "axis_forward": "-Z", "axis_up": "Y",
        "apply_unit_scale": True, "global_scale": 1.0, "mesh_smooth_type": "FACE",
        "use_mesh_modifiers": True, "path_mode": "AUTO", "bake_space_transform": False,
    }
    supported = set(bpy.ops.export_scene.fbx.get_rna_type().properties.keys())
    kwargs = {k: v for k, v in wanted.items() if k in supported}
    missing = set(wanted) - supported - {"filepath"}
    if missing:
        print(f"note: FBX exporter ignored unsupported options: {sorted(missing)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit(f"error: refusing to overwrite an existing asset: {path}")
    bpy.ops.export_scene.fbx(**kwargs)


def emit_report(name, asset_path: Path, texture_path: Path | None, parts_summary, material_name,
                pivot, forward, extra=None):
    """Machine-readable one-line report consumed by the manifest builder."""
    payload = {
        "asset": name,
        "fbx": str(asset_path),
        "texture": str(texture_path) if texture_path else None,
        "material": material_name,
        "parts": parts_summary,
        "triangles": sum(p["triangles"] for p in parts_summary),
        "pivot": pivot,
        "forward": forward,
    }
    if extra:
        payload.update(extra)
    print("REPORT_JSON " + json.dumps(payload, sort_keys=True))


def part_summary(name, part: Part, material=None):
    x0, y0, z0, x1, y1, z1 = part.bounds()
    return {"name": name, "triangles": part.tri_count(),
            "size_m": [round(x1 - x0, 4), round(y1 - y0, 4), round(z1 - z0, 4)],
            "material": material}


def standard_args(description, extra=None, texture_size=1024):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--output", required=True, help="Assets/Art/Generated/<Asset>.fbx")
    parser.add_argument("--texture", default=None, help="texture PNG path (default: sibling Textures/)")
    parser.add_argument("--texture-size", type=int, default=texture_size)
    parser.add_argument("--no-meta", action="store_true", help="skip hand-written .meta files")
    if extra:
        extra(parser)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def finish(asset_name, args, texture_canvas, parts, material_name, object_name, pivot, forward,
           extra=None, texture_name=None, texture_written=False):
    """Shared tail: write texture + metas + FBX + report."""
    root = repo_root(Path(args.output).resolve())
    output = Path(args.output).resolve()
    if texture_name is None:
        texture_name = f"{Path(args.output).stem}_{args.texture_size}.png"
    texture_path = Path(args.texture).resolve() if args.texture else \
        output.parent / "Textures" / texture_name
    if texture_canvas is not None:
        texture_canvas.save(texture_path)
    has_texture = texture_canvas is not None or (texture_written and texture_path.exists())
    ensure_asset_folders([output, texture_path])
    export_fbx(output)
    if not args.no_meta:
        write_asset_meta(output, "model")
        if has_texture:
            write_asset_meta(texture_path, "png", max_size=args.texture_size)
    summary = [part_summary(p[0], p[1], material_name) for p in parts]
    emit_report(asset_name, output.relative_to(root),
                texture_path.relative_to(root) if has_texture else None,
                summary, material_name, pivot, forward, extra)
    print(f"note: {asset_name}: {sum(p['triangles'] for p in summary)} triangles, "
          f"1 material, texture {texture_path.name if has_texture else 'none'}. "
          "Validate scale/materials/colliders in Unity and register in docs/ASSETS.md.")
    if object_name not in {o.name for o in bpy.context.scene.objects}:
        raise SystemExit(f"error: expected object {object_name} missing from the scene")
