# Ayush: hosting

Shared setup, layout and team rules are in [README.md](README.md).

## Goal

A public URL judges can open with no setup: the web UI plus a working API serving the three demo repos in read-only demo mode.

## Recommended setup

**Web UI on Vercel, API on Render using the existing `Dockerfile`.** Vercel forwards `/api/*` to Render, so the browser only ever talks to one address. That means no CORS changes and no frontend code changes.

Don't put the API on Vercel functions. It needs the `git` binary, writes SQLite files, and keeps running ingestion in a background thread after the response returns; serverless functions don't support any of those reliably. Render runs the container as a normal long-lived server. Railway or Fly.io work too if you prefer them.

## How the app is wired

- The web UI (`web/`) is a static Vite build. It calls the API with relative URLs (`/api/...`), so it needs the API reachable under the same origin, or a proxy.
- The API is FastAPI, started with `uvicorn api.main:app`. It reads repo databases from `$HEIRLOOM_HOME/db/<repo_id>.sqlite`.
- `HEIRLOOM_DEMO=1` makes it read-only: ingestion is disabled and nothing calls the network. No API keys are needed.
- The health check is `GET /api/health`, which returns `{"ok": true, "llm": "none", "demo": true}` in demo mode.

## Steps

1. **Fix the Dockerfile for hosting.**
   - Bind to the host's port. Render sets `$PORT`:
     ```dockerfile
     CMD sh -c "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
     ```
   - Copy the demo data in and switch on demo mode:
     ```dockerfile
     COPY demo ./demo
     ENV HEIRLOOM_HOME=/app/demo HEIRLOOM_DEMO=1
     ```
   - `git` is already installed in the image; keep it.
2. **Deploy the API on Render.** Create a new Web Service from the GitHub repo. Set the runtime to Docker, the root directory to the repo root, and the health check path to `/api/health`. No secrets are needed.
3. **Add `web/vercel.json`**, filling in your Render hostname:
   ```json
   {
     "rewrites": [
       { "source": "/api/:path*", "destination": "https://YOUR-SERVICE.onrender.com/api/:path*" },
       { "source": "/(.*)", "destination": "/index.html" }
     ]
   }
   ```
   The second rule makes deep links such as `/repo/x/why?path=...` survive a page refresh. Vercel serves real files (JS and CSS) before it applies rewrites.
4. **Deploy the web UI on Vercel.** Import the repo, then set:
   - Root Directory: `web`
   - Framework preset: Vite
   - Install command: `pnpm install`
   - Build command: `pnpm build`
   - Output directory: `dist`
5. **Send both URLs to Harsh** for the video and the submission text.

## While the demo snapshots don't exist yet

Deploy with a placeholder so you aren't blocked:

```bash
python tests/fixtures/make_repo.py ../heirloom-fixture
HEIRLOOM_HOME=./demo heirloom ingest ../heirloom-fixture   # -> demo/db/heirloom-fixture.sqlite
```

Deploy with that file, but don't commit it. Daksh owns what finally goes in `demo/`; redeploy once his snapshots land.

## Things that will bite

- Render's free tier sleeps after about 15 minutes idle and can take around a minute to wake. Open the site a few minutes before any live demo, or use a paid instance on demo day.
- Demo mode disables ingestion on purpose: `POST /api/repos` returns 422, and the home page hides the URL box. That's expected for a public instance.
- The container's filesystem resets on each deploy, so decisions recorded through the hosted UI don't persist. That's fine for a demo.
- The API's CORS settings only allow localhost. That's fine with the Vercel proxy, because the browser never calls Render directly. If you ever point the web UI straight at Render, add the Vercel origin in `api/main.py`.

## Done when

- [ ] `https://YOUR-APP.vercel.app/api/health` returns `{"ok": true, "llm": "none", "demo": true}`
- [ ] The home page lists the demo repos, and every page loads for each: Overview, Why Card, Trails, Ask, Decisions and People
- [ ] Refreshing a deep link like `/repo/<id>/why?path=...` works
- [ ] No CORS errors or `/api` 404s in the browser console
