"""Binary STL read/write utilities."""

from __future__ import annotations

import struct

from cfd_geometry.mesh.normals import calculate_normal


def write_stl_binary(
    filename: str,
    triangles: list,
    *,
    header: bytes = b"CFD geometry STL",
) -> None:
    """Write triangles to a binary STL file."""
    header_bytes = header[:80]
    if len(header_bytes) < 80:
        header_bytes = header_bytes + b"\0" * (80 - len(header_bytes))

    with open(filename, "wb") as f:
        f.write(header_bytes)
        f.write(struct.pack("<I", len(triangles)))
        for tri in triangles:
            normal = calculate_normal(tri)
            f.write(
                struct.pack(
                    "<fff",
                    float(normal[0]),
                    float(normal[1]),
                    float(normal[2]),
                )
            )
            for vertex in tri:
                f.write(
                    struct.pack(
                        "<fff",
                        float(vertex[0]),
                        float(vertex[1]),
                        float(vertex[2]),
                    )
                )
            f.write(struct.pack("<H", 0))


def validate_stl(stl_file: str) -> None:
    """Basic validation of a binary STL file (header, count, size)."""
    try:
        with open(stl_file, "rb") as f:
            header = f.read(80)
            triangle_count = struct.unpack("<I", f.read(4))[0]
            print("STL validation:")
            print(f"  Header: {header[:25].decode('ascii', errors='ignore')}")
            print(f"  Triangle count: {triangle_count}")
            expected_size = 80 + 4 + triangle_count * 50
            actual_size = f.seek(0, 2)
            if actual_size == expected_size:
                print("  File size OK")
            else:
                print(f"  Size mismatch: expected {expected_size}, got {actual_size}")
    except OSError as e:
        print(f"STL validation failed: {e}")
