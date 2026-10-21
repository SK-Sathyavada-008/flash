# Flash AI & Privacy Boundary Specification

This document details the data privacy boundaries, threat model, and local inference architecture for the **Flash Desktop Companion**.

---

## 1. Local AI Inference Boundary (Ollama + Gemma)

Flash runs local inference via **Ollama** on `http://127.0.0.1:11434` using open-weights models such as **Gemma 2** (`gemma2:latest`, `gemma2:2b`, or `gemma4`).

### Privacy Guarantees of Local Inference:
- **Zero Cloud Transmission**: User text prompts, file contents, spreadsheet headers, and action parameters never leave your local machine during model inference.
- **Offline Operation**: Inference functions completely disconnected from the Internet; no OpenAI, Anthropic, or external cloud API keys are required.
- **Log Sanitization**: Flash automatically sanitizes environment logs to mask any potential secrets, passwords, or tokens.

---

## 2. The Critical Privacy Boundary: Local Inference vs External Services

> [!WARNING]
> **Crucial Security & Privacy Principle**:
> Running the AI language model locally **DOES NOT** automatically make external speech-to-text (STT) services, text-to-speech (TTS) services, default browsers, or cloud storage private.

When building or extending Flash across its milestones, the following boundary distinctions apply:

### A. Speech-to-Text (STT) & Audio
- **Local STT (Private)**: When using local models (e.g., `faster-whisper`, `sherpa-onnx`), audio stays strictly on-device in memory or `%USERPROFILE%\Documents\Flash Notes\`.
- **External Web Speech / Cloud STT (Non-Private)**: If a browser's native `SpeechRecognition` API (which may send audio buffers to Google or third-party cloud servers) or a cloud STT API is used, audio leaves the workstation. Flash's architecture mandates using local Whisper STT or explicit user opt-in before streaming raw voice off-device.

### B. Browser & URL Operations (`open_url`)
- When Flash opens a URL (e.g. `open_url` pointing to `https://www.youtube.com`), the operating system dispatches the request to the user's default browser.
- External web servers receive standard HTTP request headers, IP address, and cookie sessions as normal browsing behavior.

### C. Cloud Storage & Sync
- Flash stores all created documents, grocery checklists, and Excel spreadsheets strictly inside `%USERPROFILE%\Documents\Flash Workspace\`.
- If the user's `Documents` folder is synchronized to Microsoft OneDrive, Google Drive, or Dropbox, cloud sync providers will upload those files according to the user's OS cloud settings. Flash itself never communicates directly with cloud storage APIs.

---

## 3. Threat Model & Mitigations

| Threat | Attack Vector | Flash Mitigation |
| :--- | :--- | :--- |
| **Model Hallucination of Shell Commands** | Model attempts to run `rmdir`, `powershell.exe`, or malicious executables. | **Tool Allowlist & Strict Pydantic Schema**: Flash only executes tools registered in `ActionRegistry`. Arbitrary commands and shell interpreters are completely disallowed and rejected. |
| **Directory Traversal** | Request parameters specifying paths like `../../Windows/System32`. | **Filesystem Sandboxing**: All file paths are strictly resolved against `FLASH_WORKSPACE_DIR` via `resolve_safe_path()`. Escapes raise `PATH_ACCESS_DENIED`. |
| **Remote Exploitation** | External attacker sending HTTP requests across LAN or Internet. | **Localhost Binding**: FastAPI server binds strictly to `127.0.0.1`. Remote network calls are unreachable. |
| **Emergency Halt** | Runaway loop or unintended automated action sequence. | **Global Atomic Circuit**: `/api/v1/stop` immediately locks execution with `EMERGENCY_STOP_ACTIVE`. |
| **Unintended Data Overwrite** | Model attempts to overwrite existing files. | **Confirmation Gate**: Actions flagged with `requires_confirmation=True` pause execution until `confirmed=True` is explicitly supplied by the user. |
