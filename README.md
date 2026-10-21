# Flash: AI-Powered Desktop Companion (Windows & Android)

[![CI](https://github.com/SK-Sathyavada-008/flash/actions/workflows/ci.yml/badge.svg)](https://github.com/SK-Sathyavada-008/flash/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/react-19-cyan.svg)](https://react.dev/)
[![Ollama](https://img.shields.io/badge/ollama-gemma2:2b-orange.svg)](https://ollama.com/)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/SK-Sathyavada-008/flash)

> **"Slow and steady wins the race."** — Built for the Hacktoberfest Open-Source AI Challenge: Week 3.

**Flash** is an AI-powered deliberate desktop companion featuring **Flash the Sloth** (inspired by Zootopia's Department of Mammal Vehicles). It pairs an interactive, voice-driven 3D companion running on your **Android phone (Redmi)** with a native automation agent running on your **Windows PC**.

Flash works deliberately, safely, and transparently — with **zero required cloud subscriptions**, **zero data exfiltration**, and a strict physical **Emergency Stop circuit**.

---

## 🏗️ System Architecture & Security Boundary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER'S WINDOWS 10/11 PC                         │
│                                                                         │
│  ┌───────────────────────┐          ┌────────────────────────────────┐  │
│  │  FastAPI Agent Daemon │ ◄──────► │    Local Gemma 2B (Ollama)     │  │
│  │  • Port 8765          │          │    • http://127.0.0.1:11434    │  │
│  │  • pywinauto / UIA    │          │    • Zero cloud network egress │  │
│  │  • Office Automation  │          │    • $0.00 token cost          │  │
│  │  • Sandboxed Storage  │          │    • Fast-path engine (<4ms)   │  │
│  └───────────▲───────────┘          └────────────────────────────────┘  │
│              │                                                          │
│              │ (Local WiFi / WebSocket with SHA-256 One-Time Pairing)   │
│              ▼                                                          │
│  ┌───────────────────────┐                                              │
│  │  Android Phone Companion                                             │
│  │  • Vite PWA on Phone  │                                              │
│  │  • 3D Procedural Sloth│                                              │
│  │  • Cursor Gaze Sync   │                                              │
│  │  • Push-to-Talk Mic   │                                              │
│  └───────────────────────┘                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
               (Optional Cloud Integrations — All Gracefully Fallback)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    OPTIONAL CLOUD PARTNER SERVICES                      │
│                                                                         │
│  ┌────────────────────────┐         ┌────────────────────────────────┐  │
│  │  Render Web Service    │         │  ElevenLabs Neural Speech      │  │
│  │  • Public landing page │         │  • Neural audio synthesis      │  │
│  │  • Health check /healthz│        │  • Local Windows SAPI fallback │  │
│  │  • Zero desktop access │         └────────────────────────────────┘  │
│  └────────────────────────┘         ┌────────────────────────────────┐  │
│  ┌────────────────────────┐         │  MongoDB Atlas Cloud DB        │  │
│  │  Sentry Error Telemetry│         │  • Routines & preferences sync │  │
│  │  • PII & Path scrubber │         │  • Local private JSON default  │  │
│  │  • No screenshots/PII  │         └────────────────────────────────┘  │
│  └────────────────────────┘         ┌────────────────────────────────┐  │
│                                     │  Stagehand & Browserbase       │  │
│                                     │  • Web extraction / act        │  │
│                                     │  • Local Playwright fallback   │  │
│                                     └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🦥 Core Capabilities Matrix

| Feature | Windows Desktop Agent | Android Phone Companion | Offline Fallback |
|---|---|---|---|
| **Natural Language Understanding** | Dual-Engine: Fast-path (<4ms) + Local Gemma 2B SLM | Voice & text input | 100% Offline |
| **Real Windows Desktop Control** | Windows UIA, pywinauto, mouse click/drag/scroll | Real-time event streaming | 100% Offline |
| **Active Cursor Restoration** | Warps cursor back to user position after task | Gaze follows cursor at 20Hz | 100% Offline |
| **Microsoft Office Generation** | Real `.xlsx` (formulas), `.docx`, `.pptx` decks | Instant download & preview | 100% Offline |
| **Checklists & Lists** | Spoken item splitting ("milk, bread and butter") | Reactive checklist UI | 100% Offline |
| **Speech Output** | ElevenLabs neural voice or Windows SAPI | Audio playback & captions | 100% Offline |
| **Web & Browser Automation** | Stagehand primitives (`act`, `extract`, `observe`) | Status & extracted results | Local Playwright |
| **Cloud Coordination & Deploy** | Strict localhost boundary; Render landing page | Optional cloud sync | Local JSON storage |
| **Safety & Emergency Stop** | Global kill switch (`Esc` key or phone `STOP` button) | Prominent persistent red button | 100% Offline |

---

## ⚡ Quick Start: Copy-Paste PowerShell Commands

### 1. Prerequisites
- **Windows 10/11**
- **Python 3.12+**
- **Node.js 20+**
- *(Optional)* [Ollama](https://ollama.com/) with `gemma2:2b`

### 2. Start the Windows Desktop Agent
Open PowerShell in `flash/agent`:
```powershell
cd c:\Keerthu\flash\flash\agent
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8765 --reload
```
*The agent will start on port 8765 and output your laptop's local Wi-Fi IP address (e.g. `192.168.1.15`).*

### 3. Start the Android Phone Companion (PWA)
In a second PowerShell window:
```powershell
cd c:\Keerthu\flash\flash\companion
npm run dev -- --host
```
*The companion web server will start on port 5173.*

### 4. Pair Your Phone with Your PC
1. Connect your Android phone to the **same Wi-Fi network** as your Windows PC.
2. Open Chrome on your phone and browse to:
   ```
   http://<YOUR-LAPTOP-IP>:5173
   ```
3. Enter the 6-digit pairing code shown in your laptop terminal and tap **"Pair with Flash"**.
4. You are ready to dictate tasks, generate spreadsheets, and watch Flash control your desktop!

---

## 🛑 How to Stop, Test, and Update

### Stop the Services
- In either PowerShell terminal: Press `Ctrl + C`.
- Emergency desktop stop while running: Tap `Esc` on your physical keyboard, or tap the red **`STOP`** button on your phone.

### Run All Automated Tests
```powershell
# 1. Run Python Agent Backend Suite (97 tests)
cd c:\Keerthu\flash\flash\agent
.\venv\Scripts\pytest -v

# 2. Run Companion Frontend Suite
cd c:\Keerthu\flash\flash\companion
npm test -- --run

# 3. Build Production Companion Bundle
npm run build
```

### Update and Install Dependencies
```powershell
cd c:\Keerthu\flash\flash\agent
pip install -r requirements.txt

cd c:\Keerthu\flash\flash\companion
npm install
```

---

## 📱 Redmi / Android Companion Guide

1. **Microphone Permission**: When prompted by Chrome on Android, tap **"Allow"** for microphone access. Flash uses push-to-talk: hold the microphone icon to speak, release to submit.
2. **Install as PWA**: Tap the three dots menu `⋮` in Chrome on Android ➔ **"Install app"** or **"Add to Home Screen"**. Flash runs in full-screen native app mode.
3. **Reconnection**: If Wi-Fi briefly drops, Flash automatically reconnects using exponential backoff without requiring re-pairing.

---

## 🛡️ Security & Privacy Architecture

- **No Remote Shell Access**: Flash does NOT possess any `shell`, `exec`, `cmd.exe`, or `powershell` execution actions. Only registered, strictly typed Python action classes in `app/actions/` can execute.
- **Path Sandboxing**: All file creation (`.docx`, `.xlsx`, `.pptx`, `.md`) is cryptographically confined within `%USERPROFILE%\Documents\Flash Workspace`. Traversal attacks (`../`) are blocked with `PATH_ACCESS_DENIED`.
- **Sensitive Guardrails**:
  - Refuses to interact with password fields (`IsPassword == True`).
  - Prohibits destructive shortcuts (`win+l`, `ctrl+alt+del`).
  - Requires explicit user confirmation (`confirmed=True`) for consequential operations like window closure (`alt+f4`) or file reorganization.
- **Zero-Cloud Default**: Flash operates 100% on localhost. If cloud integrations (ElevenLabs, Browserbase, MongoDB, Sentry) are enabled, privacy scrubbers automatically strip usernames, paths, and screenshot binaries before external transmission.

---

## 🤝 Hacktoberfest Partner Integrations

Full empirical benchmark logs, traces, and evidence are available in [`docs/integration-evidence.md`](docs/integration-evidence.md):

1. **Gemma (Featured)**: Primary local SLM (`gemma2:2b`) running via Ollama. 100% on-device, zero token costs, with 3.55ms fast-path dual engine.
2. **Render (Featured)**: Cloud coordination landing page and health checks (`render.yaml`). Desktop execution strictly isolated to local machine.
3. **ElevenLabs**: Speech synthesis abstraction with neural cloud voice and 100% offline Windows SAPI fallback.
4. **Browserbase / Stagehand**: Browser-level reasoning with Stagehand primitives (`act`, `extract`, `observe`) and local Playwright fallback.
5. **MongoDB Atlas**: Optional cloud sync for user routines and preferences with local JSON file default.
6. **Sentry**: Performance tracing (`flash.interpret`, `flash.action_execution`) with automated PII and path scrubbing.
7. **GitHub Actions**: Multi-platform CI pipeline running Windows agent tests and Linux web builds.
8. **.tech Domain**: DNS and deployment architecture ready for official domain binding.

---

## 🗺️ Known Limitations & Roadmap

- **Multi-Monitor Coordinate Warping**: Currently optimized for primary Windows display (0–1000 normalized grid). Multi-display spanning is scheduled for v0.2.
- **GPU Acceleration for Gemma**: On CPU, 2B model generation takes ~65s without CUDA GPU acceleration. The fast-path engine handles everyday commands in <4ms to preserve interactivity.
- **Linux/macOS Desktop Agent**: The companion PWA is platform-agnostic; Windows desktop automation currently uses Windows Accessibility APIs (`uiautomation`). Cross-platform desktop port is planned for v0.3.

---

## 📄 License

MIT License — Copyright (c) 2026 Sai Keerthana Sathyavada. Built with ❤️ for Hacktoberfest 2026.
