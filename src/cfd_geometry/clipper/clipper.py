"""STL clipping to axis-aligned bounding boxes."""

from __future__ import annotations

import os
import struct
from typing import List, Tuple

import numpy as np


class STLClipper:
    """Read, clip, and write ASCII or binary STL files."""

    def __init__(self) -> None:
        self.vertices: list = []
        self.normals: list = []
        self.triangles: list = []

    def read_stl_ascii(self, filename: str) -> bool:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                lines = f.readlines()

            i = 0
            while i < len(lines):
                line = lines[i].strip().lower()
                if line.startswith("facet normal"):
                    normal = [float(x) for x in line.split()[2:5]]
                    i += 2
                    triangle_vertices = []
                    for _ in range(3):
                        vertex_line = lines[i].strip().lower()
                        if vertex_line.startswith("vertex"):
                            vertex = [float(x) for x in vertex_line.split()[1:4]]
                            triangle_vertices.append(vertex)
                        i += 1
                    if len(triangle_vertices) == 3:
                        self.triangles.append(triangle_vertices)
                        self.normals.append(normal)
                    i += 2
                else:
                    i += 1
            return True
        except OSError as e:
            print(f"Error reading ASCII STL: {e}")
            return False

    def read_stl_binary(self, filename: str) -> bool:
        try:
            with open(filename, "rb") as f:
                f.read(80)
                num_triangles = struct.unpack("<I", f.read(4))[0]
                for _ in range(num_triangles):
                    normal = struct.unpack("<3f", f.read(12))
                    triangle_vertices = []
                    for _ in range(3):
                        vertex = struct.unpack("<3f", f.read(12))
                        triangle_vertices.append(list(vertex))
                    f.read(2)
                    self.triangles.append(triangle_vertices)
                    self.normals.append(list(normal))
            return True
        except OSError as e:
            print(f"Error reading binary STL: {e}")
            return False

    def is_binary_stl(self, filename: str) -> bool:
        try:
            with open(filename, "rb") as f:
                header = f.read(80)
                if header.startswith(b"solid"):
                    sample = f.read(200).decode("ascii", errors="ignore")
                    return "facet normal" not in sample.lower()
                return True
        except OSError:
            return False

    def read_stl(self, filename: str) -> bool:
        if not os.path.exists(filename):
            print(f"File not found: {filename}")
            return False
        if self.is_binary_stl(filename):
            print("Reading binary STL...")
            return self.read_stl_binary(filename)
        print("Reading ASCII STL...")
        return self.read_stl_ascii(filename)

    def get_bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        if not self.triangles:
            return np.array([0.0, 0.0, 0.0]), np.array([0.0, 0.0, 0.0])
        vertices_array = np.array([v for tri in self.triangles for v in tri])
        return np.min(vertices_array, axis=0), np.max(vertices_array, axis=0)

    def point_in_bounds(
        self, point: List[float], min_bounds: np.ndarray, max_bounds: np.ndarray
    ) -> bool:
        p = np.array(point)
        return bool(np.all(p >= min_bounds) and np.all(p <= max_bounds))

    def triangle_intersects_bounds(
        self,
        triangle: List[List[float]],
        min_bounds: np.ndarray,
        max_bounds: np.ndarray,
    ) -> bool:
        for vertex in triangle:
            if self.point_in_bounds(vertex, min_bounds, max_bounds):
                return True
        tri = np.array(triangle)
        tri_min = np.min(tri, axis=0)
        tri_max = np.max(tri, axis=0)
        return bool(np.all(min_bounds >= tri_min) and np.all(max_bounds <= tri_max))

    def clip_to_bounds(self, min_bounds: np.ndarray, max_bounds: np.ndarray) -> None:
        clipped_triangles = []
        clipped_normals = []
        for i, triangle in enumerate(self.triangles):
            if self.triangle_intersects_bounds(triangle, min_bounds, max_bounds):
                clipped_triangles.append(triangle)
                clipped_normals.append(self.normals[i])
        self.triangles = clipped_triangles
        self.normals = clipped_normals
        print(f"Clipped to {len(self.triangles)} triangles")

    def write_stl_binary(self, filename: str) -> bool:
        try:
            with open(filename, "wb") as f:
                header = b"STL clipped file" + b"\0" * (80 - 16)
                f.write(header)
                f.write(struct.pack("<I", len(self.triangles)))
                for i, triangle in enumerate(self.triangles):
                    f.write(struct.pack("<3f", *self.normals[i]))
                    for vertex in triangle:
                        f.write(struct.pack("<3f", *vertex))
                    f.write(struct.pack("<H", 0))
            return True
        except OSError as e:
            print(f"Error writing STL: {e}")
            return False

    def write_stl_ascii(self, filename: str) -> bool:
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("solid clipped_model\n")
                for i, triangle in enumerate(self.triangles):
                    normal = self.normals[i]
                    f.write(
                        f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n"
                    )
                    f.write("    outer loop\n")
                    for vertex in triangle:
                        f.write(
                            f"      vertex {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n"
                        )
                    f.write("    endloop\n")
                    f.write("  endfacet\n")
                f.write("endsolid clipped_model\n")
            return True
        except OSError as e:
            print(f"Error writing ASCII STL: {e}")
            return False


def clip_stl_to_bounds(
    input_file: str,
    output_file: str,
    clip_bounds: list[float],
    *,
    ascii_output: bool = False,
) -> int:
    """
    Clip an STL to ``[xmin, ymin, zmin, xmax, ymax, zmax]``.

    Returns 0 on success, 1 on failure.
    """
    if len(clip_bounds) != 6:
        raise ValueError("clip_bounds must have 6 values")

    clipper = STLClipper()
    if not clipper.read_stl(input_file):
        return 1

    original = len(clipper.triangles)
    clip_min = np.array(clip_bounds[:3])
    clip_max = np.array(clip_bounds[3:])
    clipper.clip_to_bounds(clip_min, clip_max)

    if not clipper.triangles:
        print("No triangles remain after clipping")
        return 1

    ok = (
        clipper.write_stl_ascii(output_file)
        if ascii_output
        else clipper.write_stl_binary(output_file)
    )
    if ok:
        print(f"Clipped {original} -> {len(clipper.triangles)} triangles -> {output_file}")
        return 0
    return 1
