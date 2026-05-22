# Build the documentation

Docs use [MkDocs](https://www.mkdocs.org/) with the [Material](https://squidfunk.github.io/mkdocs-material/) theme.

## Local preview

```bash
pip install -r docs/requirements.txt
mkdocs serve
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

Strict build (CI-style):

```bash
mkdocs build --strict
```

## GitHub Pages

On every push to `main`, [.github/workflows/docs.yml](https://github.com/Omokayode/CFDGeometry/blob/main/.github/workflows/docs.yml) runs `mkdocs gh-deploy`.

**One-time repo setup:**

1. GitHub → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: **`gh-pages`** / `/ (root)`

Site URL: `https://omokayode.github.io/CFDGeometry/`

(Replace `Omokayode` if you fork the repo and update `site_url` in `mkdocs.yml`.)

## Read the Docs

1. Sign in at [readthedocs.org](https://readthedocs.org/)
2. **Import project** → GitHub → `CFDGeometry`
3. RTD reads [.readthedocs.yaml](https://github.com/Omokayode/CFDGeometry/blob/main/.readthedocs.yaml) automatically

Default docs URL will be like `https://cfd-geometry.readthedocs.io/` (you can set a custom subdomain in RTD settings).

## Edit content

Markdown lives under `docs/`. Navigation is in `mkdocs.yml` at the repo root.

After editing, run `mkdocs serve` and open the local URL to preview before pushing.
