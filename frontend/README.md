# Asset Pulse frontend

React + TypeScript + Vite. See the [project README](../README.md) for setup, deployment to Netlify, and architecture notes.

## Scripts

- `npm run dev` — Vite dev server on port 5173 with `/api` proxied to FastAPI on `:8000`.
- `npm run build` — production build to `dist/`.
- `npm run preview` — preview the production build.

## Environment

| Var                     | Effect                                                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| `VITE_API_BASE_URL`     | Build-time. Sets the base URL the bundle calls. Leave empty to use relative `/api/...`.    |
| `VITE_API_PROXY_TARGET` | Dev-only override for the Vite proxy (default `http://localhost:8000`).                    |
