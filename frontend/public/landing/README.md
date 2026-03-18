# Landing page static assets

Files here are served at the site root: **`/landing/<filename>`**.

## “Your career facts” card

| File | Notes |
|------|--------|
| **`yaml-preview.png`** | Shown **top-right** of the card (~22% opacity). YAML screenshot, editor capture, or profile graphic. If missing, a small YAML-style snippet appears in the same corner. |

- On disk: **`frontend/public/landing/yaml-preview.png`**. At runtime the app requests **`{Vite base}landing/yaml-preview.png`** (usually **`/landing/yaml-preview.png`**).
- Hard-refresh after adding or changing the file.

## Other landing images

| File | Card |
|------|------|
| **`pdf-preview.png`** | PDF rendering — real resume PDF screenshot behind that card. |
| **`sankey-preview.png`** (optional copy) | The app **bundles** the preview from **`frontend/src/assets/landing/sankey-preview.png`** so it always loads in production (URLs under `/landing/` often 404 when the SPA server falls through to `index.html`). Update that file under `src/assets/landing/` and run `npm run build`. You can keep a copy in `public/landing/` for reference only. |

## General

- **SVG**: diagrams, icons. **PNG/JPEG**: screenshots.
- Use **lowercase, hyphens** in filenames.
