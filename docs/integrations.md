# Hacktoberfest 2026 Partner Integrations: Real-World Use & Verifiable Evidence

Flash embraces the Hacktoberfest 2026 theme: ***"AI belongs to everyone: building with open-weight models and open-source AI."***

This document details proposed integrations with official Hacktoberfest partners and sponsors, specifying the exact architectural role of each, how it delivers genuine end-user value, and the verifiable technical evidence required to prove authentic utilization without vanity dependencies.

---

## 1. Summary of Partner Integrations

| Partner / Technology | Role in Flash Architecture | Primary Deliverable | Evidence of Genuine Use |
| :--- | :--- | :--- | :--- |
| **Gemma (Google Cloud)** | Core intelligence, tool calling, reasoning, safety evaluations | Local inference via Ollama (`gemma2:9b` / `gemma2:2b`) | Multi-turn function execution logs with valid tool schemas & system prompts |
| **DigitalOcean** | Cloud synchronization, remote companion relay, Droplet hosting | FastAPI Agent relay server & MongoDB droplet backing | Deployed App Platform URL, remote PWA relay traffic, healthcheck API |
| **ElevenLabs** | Ultra-expressive voice responses & customized sloth personality TTS | Streaming audio output fallback to Web Audio chirp synthesizer | Real API audio buffers streamed to phone with latency logs & speaker IDs |
| **MongoDB (Atlas)** | Cloud cross-device transcript backup & multi-session analytics | Distributed document store for session history and meeting notes | Active collections (`sessions`, `transcripts`), write receipts with `_id` |
| **Sentry** | Production error telemetry, crash reporting, tool execution tracing | End-to-end tracing across Windows Win32 hooks and WebSockets | Verified trace spans for screen capture, OCR, and automation clicks |

---

## 2. In-Depth Integration Specifications

### 2.1 Gemma (Google DeepMind / Google Cloud)
- **Role**: Primary local reasoning engine powering natural language comprehension, screen context interpretation, structured tool dispatch, and conversational responses.
- **Why It Matters**:
  - Hacktoberfest 2026 emphasizes open-weight models. Gemma 2 offers state-of-the-art instruction-following and tool-use capabilities in compact 2B and 9B parameter sizes suitable for consumer laptops without cloud data egress.
- **Implementation**:
  - Ollama integration via `/api/chat` using structured JSON tool definitions.
  - Custom system prompt formatting tailored to Flash's sloth character: dry, concise, polite, and safety-focused.
- **Evidence of Genuine Use**:
  1. Complete tool schema manifests (`look_at_screen`, `point_at`, `click`, `generate_excel`, `create_document`, `web_research`).
  2. Recorded conversation logs showing multi-step autonomous tool calls generated directly by Gemma.
  3. Zero external network requests during local operation, validating true open-weight local execution.

---

### 2.2 DigitalOcean (Presenting Partner)
- **Role**: Cloud relay and optional remote companion access.
- **Why It Matters**:
  - While Flash defaults to 100% local Wi-Fi pairing, users who travel or connect over guest networks with client isolation (where phone-to-laptop direct communication is blocked) need a secure relay. DigitalOcean App Platform or Droplets host the lightweight WebSocket relay bridge with TLS termination.
- **Implementation**:
  - `flash-relay`: A secure Dockerized async relay container deployed to DigitalOcean App Platform.
  - Client and agent connect outbound over secure WebSockets (`wss://flash-relay.ondigitalocean.app`) when local Wi-Fi discovery fails.
- **Evidence of Genuine Use**:
  1. `Dockerfile` and `app.yaml` configuration targeting DigitalOcean App Platform.
  2. Publicly accessible health check endpoint: `https://<app-name>.ondigitalocean.app/health`.
  3. Live end-to-end trace demonstrating companion phone connecting through the DO relay when local Wi-Fi direct connection is intentionally severed.

---

### 2.3 ElevenLabs
- **Role**: High-fidelity, emotional sloth voice synthesis option.
- **Why It Matters**:
  - While Flash uses a whimsical procedural Web Audio chirp synthesizer by default (zero bandwidth and zero API key needed), users who want spoken natural language responses can enable ElevenLabs' low-latency streaming TTS (`eleven_turbo_v2_5` or `eleven_multilingual_v2`).
- **Implementation**:
  - Custom voice cloning or warm character voice preset (soft-spoken, relaxed, friendly sloth tempo).
  - Streamed chunk-by-chunk to the phone over WebSocket as base64 audio, synchronized with the 3D character's `jawOpen` blendshape.
- **Evidence of Genuine Use**:
  1. Audio streaming module in `server/audio/synth.py` consuming ElevenLabs REST / WebSocket API.
  2. Phoneme / viseme synchronization driving 3D sloth mouth animation in React Three Fiber.
  3. Network requests containing ElevenLabs latency headers and audio buffer playback verification on Android.

---

### 2.4 MongoDB (MongoDB Atlas)
- **Role**: Cloud session persistence, transcript indexing, and cross-device sync.
- **Why It Matters**:
  - Meeting notes and multi-device transcripts are stored in local SQLite by default. When MongoDB integration is activated, sessions automatically sync to a free-tier MongoDB Atlas cluster, enabling web-based review and semantic tag queries across multiple laptops and phones.
- **Implementation**:
  - Async Motor / PyMongo connector in `server/storage/mongo_sync.py`.
  - Schema:
    - Collection `sessions`: session metadata, start/end timestamps, duration, question count.
    - Collection `transcripts`: diarized speaker turns with embedded vector coordinates for semantic search.
- **Evidence of Genuine Use**:
  1. Verified PyMongo insertion queries with returned `InsertOneResult(inserted_id=ObjectId(...))`.
  2. Bi-directional sync test: Creating a meeting note on Windows updates the Atlas database, and deleting a session on Android propagates the change back.

---

### 2.5 Sentry
- **Role**: Desktop automation observability, exception telemetry, and performance tracing.
- **Why It Matters**:
  - Desktop automation on Windows interacts with unpredictable native OS states (minimized windows, UAC popups, DPI scaling differences). Sentry captures stack traces, performance bottlenecks in screen capture/OCR, and automation failures.
- **Implementation**:
  - Sentry Python SDK initialized in `server/app.py`:
    ```python
    import sentry_sdk
    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0
    )
    ```
  - Custom transaction spans measuring:
    - `screen_capture_duration_ms`
    - `ocr_recognition_latency_ms`
    - `gemma_inference_ttft_ms` (time to first token)
    - `win32_action_execution_ms`
- **Evidence of Genuine Use**:
  1. Live Sentry issue tracker displaying custom tags (`os_version: Windows 11`, `model: gemma2:9b`, `action: click`).
  2. Transaction timeline visual showing granular span breakdown from user voice command to physical mouse click.

---

## 3. Strict Rules on Non-Vanity Integrations

To ensure compliance with hackathon standards and maintain code integrity:
1. **No Dead Imports**: Every integrated package must have active callers in the executable business logic.
2. **Graceful Degradation**: If an optional third-party service (DigitalOcean, ElevenLabs, MongoDB, Sentry) is unconfigured or credentials are blank, Flash continues to function 100% locally on Gemma + SQLite + procedural chirps without crashing or throwing unhandled exceptions.
3. **Transparent Logging**: All cloud partner calls log execution time, payload size, and response codes to `%USERPROFILE%\Documents\Flash Notes\telemetry.log`.
