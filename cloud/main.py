"""Flash Cloud Coordination Service & Public Landing Page.

Designed for deployment on Render.
ARCHITECTURE BOUNDARY:
- This service serves the Flash Sloth Companion web app, handles health checks, public documentation,
  and coordinates connection between the companion app and the user's local Windows machine.
- Desktop control and OS automation CANNOT and DO NOT execute on Render; desktop execution
  is strictly confined to the user's local Windows agent running on localhost.
"""

import os
import time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Flash Cloud Coordinator",
    description="Render-hosted public companion app and cloud coordinator for Flash Sloth Agent.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
ASSETS_DIR = os.path.join(STATIC_DIR, "assets")

# Mount assets directory if present
if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


LANDING_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Flash — The Deliberate Sloth Desktop Companion</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: rgba(30, 41, 59, 0.7);
      --primary: #38bdf8;
      --accent: #a855f7;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --border: rgba(255, 255, 255, 0.1);
      --success: #22c55e;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    body { background-color: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }
    header { padding: 2rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); }
    .logo { font-size: 1.5rem; font-weight: 800; display: flex; align-items: center; gap: 0.5rem; color: var(--primary); text-decoration: none; }
    .nav-actions { display: flex; gap: 1rem; align-items: center; }
    .btn { background: var(--primary); color: #0f172a; padding: 0.5rem 1rem; border-radius: 8px; font-weight: 700; text-decoration: none; font-size: 0.9rem; }
    .badge { background: rgba(56, 189, 248, 0.15); color: var(--primary); padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 600; border: 1px solid rgba(56, 189, 248, 0.3); }
    main { max-width: 1000px; margin: 0 auto; padding: 4rem 1.5rem; flex: 1; }
    .hero { text-align: center; margin-bottom: 4rem; }
    .hero h1 { font-size: 3rem; font-weight: 900; margin-bottom: 1rem; background: linear-gradient(to right, var(--primary), var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .hero p { font-size: 1.25rem; color: var(--text-muted); max-width: 700px; margin: 0 auto 2rem; line-height: 1.6; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; margin-bottom: 3rem; }
    .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 1rem; padding: 1.5rem; backdrop-filter: blur(10px); }
    .card h3 { font-size: 1.2rem; margin-bottom: 0.75rem; color: var(--primary); display: flex; align-items: center; gap: 0.5rem; }
    .card p { color: var(--text-muted); font-size: 0.95rem; line-height: 1.5; }
    .boundary-banner { background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 1rem; padding: 1.5rem; margin-bottom: 3rem; }
    .boundary-banner h3 { color: var(--success); margin-bottom: 0.5rem; }
    .boundary-banner p { color: var(--text-muted); font-size: 0.95rem; line-height: 1.5; }
    footer { text-align: center; padding: 2rem; border-top: 1px solid var(--border); color: var(--text-muted); font-size: 0.85rem; }
  </style>
</head>
<body>
  <header>
    <a href="/" class="logo">🦥 Flash Agent</a>
    <div class="nav-actions">
      <a href="/" class="btn">Launch Flash Companion</a>
      <div class="badge">Deployed on Render</div>
    </div>
  </header>
  <main>
    <div class="hero">
      <h1>Deliberate, Safe AI Desktop Companion</h1>
      <p>Flash combines local Gemma 2B intelligence, responsive mobile control, and native Windows automation — working slowly, deliberately, and always with user consent.</p>
    </div>

    <div class="boundary-banner">
      <h3>🛡️ Security Boundary Guarantee</h3>
      <p>This public service runs on <strong>Render</strong>. All desktop actions, mouse movements, file operations, Office document generation, and screen inspections execute exclusively on your <strong>local Windows machine</strong>. Render has zero remote access or desktop privileges.</p>
    </div>

    <div class="grid">
      <div class="card">
        <h3>⚡ Local Gemma Intelligence</h3>
        <p>Runs on Ollama on-device. Zero token fees, zero private prompt exfiltration to cloud providers, with high-speed deterministic fast-path for sub-millisecond execution.</p>
      </div>
      <div class="card">
        <h3>📱 Mobile Companion</h3>
        <p>Responsive Vite PWA with voice dictation, grocery checklists, live connection health monitoring, and haptic feedback.</p>
      </div>
      <div class="card">
        <h3>🖥️ Windows Desktop Control</h3>
        <p>Native automation through Windows UIAutomation and pywinauto: controls accessible buttons, menus, Office documents (.docx, .xlsx, .pptx), and browser workflows.</p>
      </div>
      <div class="card">
        <h3>🎙️ ElevenLabs & Local Speech</h3>
        <p>Dual-engine speech synthesis: crystal-clear ElevenLabs neural voice when configured, with seamless 100% offline Windows SAPI fallback.</p>
      </div>
      <div class="card">
        <h3>🌐 Stagehand Browser Workflows</h3>
        <p>Web automation primitives (act, extract, observe) powered by local Playwright or cloud Browserbase sessions.</p>
      </div>
      <div class="card">
        <h3>💾 MongoDB Atlas & Local Storage</h3>
        <p>Routines and preferences stored locally by default in private JSON, with optional MongoDB Atlas cloud synchronization.</p>
      </div>
    </div>
  </main>
  <footer>
    <p>Flash Sloth Desktop Agent • Hacktoberfest Open-Source AI Challenge • Built with ❤️ on Windows & Render</p>
  </footer>
</body>
</html>
"""


@app.get("/healthz")
def health_check():
    """Health check endpoint required for Render deployments."""
    return JSONResponse({
        "status": "healthy",
        "service": "flash-cloud-coordinator",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "environment": os.getenv("RENDER_SERVICE_NAME", "local-or-render"),
        "architecture_boundary": {
            "cloud_role": "Public companion web app, health monitoring, documentation, and coordination",
            "desktop_execution_role": "Confined 100% to local Windows PC agent; no remote desktop execution from cloud",
            "zero_cloud_privilege": True,
        },
    })


@app.get("/api/v1/cloud-status")
def cloud_status():
    """Status endpoint detailing coordination features."""
    return JSONResponse({
        "service_name": "Flash Cloud Coordination Service",
        "deployed_on": "Render",
        "active_features": [
            "Flash Sloth Web Companion",
            "Interactive Web Demo Mode",
            "Render deployment blueprint (render.yaml)",
            "Automated health checks (/healthz)",
            "Boundary isolation between cloud telemetry and local Windows execution",
            "Public product documentation and connection guidance (/about)",
        ],
        "local_agent_requirement": "Windows 10/11 with Python 3.12, Ollama (Gemma 2:2b), and Flash Agent daemon",
    })


@app.get("/about", response_class=HTMLResponse)
def about_page():
    """Detailed architectural documentation and security boundary overview."""
    return LANDING_PAGE_HTML


@app.get("/favicon.svg")
def favicon():
    icon_path = os.path.join(STATIC_DIR, "favicon.svg")
    if os.path.isfile(icon_path):
        return FileResponse(icon_path, media_type="image/svg+xml")
    return JSONResponse({"error": "not found"}, status_code=404)


@app.get("/manifest.webmanifest")
def manifest():
    manifest_path = os.path.join(STATIC_DIR, "manifest.webmanifest")
    if os.path.isfile(manifest_path):
        return FileResponse(manifest_path, media_type="application/manifest+json")
    return JSONResponse({"error": "not found"}, status_code=404)


@app.get("/sw.js")
def service_worker():
    sw_path = os.path.join(STATIC_DIR, "sw.js")
    if os.path.isfile(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    return JSONResponse({"error": "not found"}, status_code=404)


@app.get("/")
def root():
    """Serves the interactive Flash Sloth Companion app if built, else fallback landing page."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    return HTMLResponse(LANDING_PAGE_HTML)
