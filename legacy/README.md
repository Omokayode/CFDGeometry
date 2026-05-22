# Legacy scripts

These directories contain earlier standalone scripts and experiments. They are **not** part of the installable `cfd_geometry` package.

Use the package instead:

```bash
pip install -e .
cfd-geometry --help
```

| Legacy folder | Replacement |
|---------------|-------------|
| Root `*.py` shims | `cfd-geometry` CLI or `import cfd_geometry` |
| `root_scripts/` | Older one-off scripts (clip+base, VTK download, etc.) |
| `wRaster/` | Terrain-aware workflows (port in progress; see `cfd_geometry.raster`) |
| `workingVersion/` | Archived known-good copies |
| `deprecated/` | Outdated approaches |
| `dev/` | Experiments |
| `apps/` | Tkinter STL clipper GUI (still usable; imports `stlClipper` at repo root if present) |
