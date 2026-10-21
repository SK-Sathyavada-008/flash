"""FastAPI application entry point for Flash Windows Desktop Agent.
Provides RESTful endpoints for health checks, action execution, AI orchestration,
device pairing, and authenticated WebSocket communication.
"""

from contextlib import asynccontextmanager
from datetime import datetime
import json
import time
from typing import Any, AsyncGenerator, Optional

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from app.auth import pairing_manager, token_manager
from app.config import settings
from app.cursor_tracker import cursor_tracker
from app.logging_config import configure_logging, get_logger
from app.models import (
    ActionInfo,
    ActionRequest,
    ActionResponse,
    AgentStatusResponse,
    HealthResponse,
    InterpretationPlan,
    OllamaStatusResponse,
    PairingCodeResponse,
    PairRequest,
    PairResponse,
    RevokeTokenRequest,
    RevokeTokenResponse,
    TaskExecutionResponse,
    UserTaskRequest,
)
from app.service import agent_service

# Initialize logging before FastAPI app creation
configure_logging(level=settings.log_level)
logger = get_logger("flash.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle manager."""
    logger.info("Initializing %s lifespan...", settings.app_name)
    from app.telemetry.sentry_tracer import init_sentry
    init_sentry()
    agent_service.startup()
    await cursor_tracker.start()

    # Automatically generate pairing code and display banner in terminal
    code, ttl, _ = pairing_manager.get_or_create_code_info()
    import socket
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    banner = (
        f"\n{'=' * 62}\n"
        f"   🦥 FLASH SLOTH DESKTOP AGENT ONLINE\n"
        f"{'=' * 62}\n"
        f"   ► YOUR 6-DIGIT PAIRING CODE :  {code}\n"
        f"   ► LAPTOP IP ADDRESS         :  {local_ip}\n"
        f"   ► PHONE COMPANION URL       :  http://{local_ip}:5173\n"
        f"   (Enter this code on your phone to connect!)\n"
        f"{'=' * 62}\n"
    )
    print(banner, flush=True)
    logger.info("Pairing code active: %s on %s", code, local_ip)

    yield
    logger.info("Terminating %s lifespan...", settings.app_name)
    await cursor_tracker.stop()
    agent_service.shutdown()



app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local Windows desktop automation agent service for Flash the Sloth.",
    lifespan=lifespan,
)

# Allow CORS for local loopback and Wi-Fi private LAN clients (PWA companion on phone)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


async def verify_auth_if_remote(request: Request) -> None:
    """Ensure non-loopback (LAN / phone) requests provide a valid Flash bearer token.
    
    Permits unauthenticated loopback (127.0.0.1, ::1, testclient) for backward
    compatibility with local CLI commands and test suites.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    # Localhost / loopback does not require token
    if client_ip in ("127.0.0.1", "::1", "localhost", "testclient"):
        return

    # Check Authorization header (Bearer <token>) or x-flash-token
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    elif "x-flash-token" in request.headers:
        token = request.headers["x-flash-token"].strip()

    if not token or not token_manager.validate_token(token):
        logger.warning("Blocked unauthenticated remote request from %s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Valid Flash bearer token required for remote LAN access.",
        )


@app.get("/", tags=["General"])
async def root() -> dict[str, str]:
    """Root endpoint welcoming users and agents to Flash."""
    return {
        "message": "Welcome to Flash Desktop Agent",
        "character": "Flash the Sloth 🦥",
        "quote": "Fast... as... lightning...",
        "version": settings.app_version,
        "docs_url": "/docs",
        "health_url": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check() -> HealthResponse:
    """Service health-check endpoint."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now().isoformat(),
    )


@app.get("/api/v1/status", response_model=AgentStatusResponse, tags=["Agent Control"])
async def get_status() -> AgentStatusResponse:
    """Retrieve operational status, available actions, and environment metrics."""
    return agent_service.get_status()


@app.get("/api/v1/actions", response_model=list[ActionInfo], tags=["Actions"])
async def list_actions() -> list[ActionInfo]:
    """List all available registered actions and their schemas."""
    status_report = agent_service.get_status()
    return status_report.action_details


@app.post("/api/v1/actions/execute", response_model=ActionResponse, tags=["Actions"])
async def execute_action(
    request: ActionRequest, _auth: None = Depends(verify_auth_if_remote)
) -> ActionResponse:
    """Execute a registered action with validation and sandboxing."""
    response = agent_service.execute_action(request)
    if not response.success and response.error == "UNKNOWN_ACTION":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=response.message,
        )
    return response


@app.post("/api/v1/stop", tags=["Agent Control"])
async def trigger_emergency_stop(
    _auth: None = Depends(verify_auth_if_remote),
) -> dict[str, str]:
    """Trigger the global emergency stop circuit."""
    return agent_service.trigger_emergency_stop("Manual API stop trigger")


@app.post("/api/v1/resume", tags=["Agent Control"])
async def resume_from_emergency_stop(
    _auth: None = Depends(verify_auth_if_remote),
) -> dict[str, str]:
    """Clear emergency stop and resume normal operational state."""
    return agent_service.resume_from_emergency_stop()


# =====================================================================
# Milestone 2: AI Endpoints (Ollama & Gemma)
# =====================================================================

@app.get("/api/v1/ai/status", response_model=OllamaStatusResponse, tags=["AI Inference"])
async def get_ai_status() -> OllamaStatusResponse:
    """Check whether Ollama is installed, running, and if configured Gemma model is available."""
    return agent_service.get_ollama_status()


@app.post("/api/v1/ai/interpret", response_model=InterpretationPlan, tags=["AI Inference"])
async def interpret_prompt(
    request: UserTaskRequest, _auth: None = Depends(verify_auth_if_remote)
) -> InterpretationPlan:
    """Translate natural language instructions into a structured, validated action plan."""
    try:
        return agent_service.interpret_task(request.prompt)
    except Exception as e:
        logger.error("Interpretation failed for prompt '%s': %s", request.prompt, e)
        error_code = getattr(e, "error_code", "INTERPRETATION_ERROR")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Interpretation error ({error_code}): {e}",
        )


@app.post("/api/v1/ai/execute", response_model=TaskExecutionResponse, tags=["AI Inference"])
async def execute_task(
    request: UserTaskRequest, _auth: None = Depends(verify_auth_if_remote)
) -> TaskExecutionResponse:
    """Orchestrate interpretation, validation, and multi-step execution of a user prompt."""
    return agent_service.execute_task(request)


# =====================================================================
# Milestone 3: Device Pairing & Authentication Endpoints
# =====================================================================

@app.get("/api/v1/auth/pair-code", response_model=PairingCodeResponse, tags=["Authentication"])
@app.post("/api/v1/auth/pair-code", response_model=PairingCodeResponse, tags=["Authentication"])
async def get_or_create_pair_code() -> PairingCodeResponse:
    """Generate or retrieve the active 6-digit pairing code on the host agent."""
    code, ttl, expires_at = pairing_manager.get_or_create_code_info()
    return PairingCodeResponse(
        code=code,
        expires_in_seconds=ttl,
        expires_at=expires_at,
    )


@app.post("/api/v1/auth/pair", response_model=PairResponse, tags=["Authentication"])
async def pair_device(request: PairRequest) -> PairResponse:
    """Verify 6-digit pairing code and issue a revocable 256-bit bearer token for phone companion."""
    if not pairing_manager.verify_and_consume(request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired pairing code. Please generate a fresh code on the laptop.",
        )
    token = token_manager.issue_token(client_name=request.device_name)
    return PairResponse(
        token=token,
        device_name=request.device_name,
        status="authenticated",
    )


@app.post("/api/v1/auth/verify", tags=["Authentication"])
async def verify_auth_token(
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None),
) -> dict[str, Any]:
    """Verify whether a bearer token is valid and active."""
    check_token = token
    if not check_token and authorization and authorization.startswith("Bearer "):
        check_token = authorization.split(" ", 1)[1].strip()
    is_valid = token_manager.validate_token(check_token)
    return {"valid": is_valid}


@app.post("/api/v1/auth/revoke", response_model=RevokeTokenResponse, tags=["Authentication"])
async def revoke_auth_token(request: RevokeTokenRequest) -> RevokeTokenResponse:
    """Revoke an active companion bearer token immediately."""
    success = token_manager.revoke_token(request.token)
    if success:
        return RevokeTokenResponse(success=True, message="Token revoked successfully.")
    return RevokeTokenResponse(success=False, message="Token not found or already revoked.")


# =====================================================================
# Milestone 3: WebSocket Companion Streaming Endpoint
# =====================================================================

@app.websocket("/ws/v1/companion")
async def companion_websocket(websocket: WebSocket, token: Optional[str] = None) -> None:
    """Authenticated WebSocket endpoint for Flash phone companion.
    
    Streams live task updates, heartbeats, status changes, and emergency controls.
    """
    client_ip = websocket.client.host if websocket.client else "127.0.0.1"
    is_local = client_ip in ("127.0.0.1", "::1", "localhost", "testclient")

    # If non-localhost, require valid token.
    # On localhost, if token is provided, validate it as well.
    if not is_local:
        if not token or not token_manager.validate_token(token):
            await websocket.accept()
            await websocket.send_json({
                "type": "error",
                "code": "UNAUTHORIZED",
                "message": "Valid bearer token is required to connect companion.",
                "timestamp": time.time(),
            })
            await websocket.close(code=4401)
            logger.warning("Rejected unauthenticated WebSocket from %s", client_ip)
            return
    else:
        if token and not token_manager.validate_token(token):
            await websocket.accept()
            await websocket.send_json({
                "type": "error",
                "code": "UNAUTHORIZED",
                "message": "Supplied bearer token is invalid or revoked.",
                "timestamp": time.time(),
            })
            await websocket.close(code=4401)
            return

    await websocket.accept()
    logger.info("Phone companion WebSocket connected from %s", client_ip)
    cursor_tracker.add_client(websocket)

    # Send initial connection confirmation
    status_now = agent_service.get_status()
    await websocket.send_json({
        "type": "connection_established",
        "agent_name": settings.character_name,
        "version": settings.app_version,
        "status": status_now.status,
        "emergency_stop_active": status_now.emergency_stop_active,
        "timestamp": time.time(),
    })

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                msg_data = json.loads(raw_text)
            except Exception:
                await websocket.send_json({
                    "type": "error",
                    "code": "MALFORMED_JSON",
                    "message": "Invalid JSON payload received.",
                    "timestamp": time.time(),
                })
                continue

            msg_type = msg_data.get("type")
            if not msg_type:
                await websocket.send_json({
                    "type": "error",
                    "code": "MISSING_MESSAGE_TYPE",
                    "message": "Message missing required 'type' field.",
                    "timestamp": time.time(),
                })
                continue

            if msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "client_timestamp": msg_data.get("timestamp"),
                    "server_timestamp": time.time(),
                })
            elif msg_type == "get_status":
                current_status = agent_service.get_status()
                await websocket.send_json({
                    "type": "status_update",
                    "status": current_status.status,
                    "emergency_stop_active": current_status.emergency_stop_active,
                    "available_actions": current_status.available_actions,
                    "timestamp": time.time(),
                })
            elif msg_type == "set_gaze_enabled":
                enabled = bool(msg_data.get("enabled", True))
                cursor_tracker.set_client_gaze_enabled(websocket, enabled)
                await websocket.send_json({
                    "type": "gaze_status",
                    "enabled": enabled,
                    "timestamp": time.time(),
                })
            elif msg_type == "stop":
                agent_service.trigger_emergency_stop("Triggered by companion phone")
                await websocket.send_json({
                    "type": "stopped",
                    "status": "stopped",
                    "message": "Emergency stop triggered.",
                    "timestamp": time.time(),
                })
            elif msg_type == "resume":
                agent_service.resume_from_emergency_stop()
                await websocket.send_json({
                    "type": "resumed",
                    "status": "ready",
                    "message": "Emergency stop cleared. Agent is ready.",
                    "timestamp": time.time(),
                })
            elif msg_type == "execute_task":
                prompt = (msg_data.get("prompt") or "").strip()
                if not prompt:
                    await websocket.send_json({
                        "type": "error",
                        "code": "MISSING_PROMPT",
                        "message": "Prompt cannot be empty for execute_task.",
                        "timestamp": time.time(),
                    })
                    continue
                confirmed = bool(msg_data.get("confirmed", False))
                task_request = UserTaskRequest(prompt=prompt, confirmed=confirmed)
                async for event in agent_service.execute_task_stream(task_request):
                    await websocket.send_json(event)
            else:
                await websocket.send_json({
                    "type": "error",
                    "code": "UNSUPPORTED_MESSAGE_TYPE",
                    "message": f"Unsupported message type: '{msg_type}'",
                    "timestamp": time.time(),
                })
    except WebSocketDisconnect:
        logger.info("Phone companion disconnected (%s)", client_ip)
    except Exception as e:
        logger.error("Phone companion WebSocket exception: %s", e)
    finally:
        cursor_tracker.remove_client(websocket)


@app.get("/api/v1/telemetry/status")
def get_telemetry_status():
    """Retrieve telemetry and privacy status."""
    return {
        "sentry_configured": bool(settings.sentry_dsn),
        "environment": settings.sentry_environment,
        "traces_sample_rate": settings.sentry_traces_sample_rate,
        "pii_scrubbing": True,
        "privacy_guarantees": [
            "Local file paths redacted to [LOCAL_USER_PATH]",
            "Screenshots and image binaries stripped from error breadcrumbs",
            "Authentication tokens and secrets redacted",
            "No raw prompt exfiltration to cloud telemetry",
        ],
    }


@app.get("/api/v1/routines")
def list_routines():
    """List automated routines from Storage (Local JSON or MongoDB Atlas)."""
    from app.storage import get_storage
    storage = get_storage()
    return {
        "provider": storage.get_provider_name(),
        "cloud_sync": storage.is_cloud_enabled(),
        "routines": storage.list_routines(),
    }


@app.post("/api/v1/routines")
def save_routine(payload: dict[str, Any]):
    """Save an automated routine."""
    from app.storage import get_storage
    storage = get_storage()
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Routine 'name' is required.")
    steps = payload.get("steps", [])
    desc = payload.get("description", "")
    ok = storage.save_routine(name, steps, desc)
    return {"success": ok, "name": name, "provider": storage.get_provider_name()}


@app.get("/api/v1/preferences")
def get_user_preferences():
    """Retrieve user preferences."""
    from app.storage import get_storage
    storage = get_storage()
    return {
        "provider": storage.get_provider_name(),
        "preferences": storage.get_preferences(),
    }


@app.put("/api/v1/preferences")
def update_user_preferences(prefs: dict[str, Any]):
    """Update user preferences."""
    from app.storage import get_storage
    storage = get_storage()
    ok = storage.save_preferences(prefs)
    return {"success": ok, "provider": storage.get_provider_name()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
