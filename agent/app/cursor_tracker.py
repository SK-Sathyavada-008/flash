"""Cursor tracking and gaze synchronization for Flash Agent.

Captures cursor position on the Windows desktop, normalizes coordinates to (0.0 - 1.0),
throttles network updates (max 20 Hz), and broadcasts gaze events to connected
companion devices without transmitting screenshots or sensitive display data.
"""

import asyncio
import ctypes
import math
import sys
import time
from typing import Callable, Optional, Set
from fastapi import WebSocket

from app.logging_config import get_logger

logger = get_logger("flash.cursor_tracker")


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class CursorTracker:
    """Manages throttled cursor capture and streaming over WebSockets."""

    def __init__(self, sample_interval: float = 0.033, move_threshold: float = 0.002) -> None:
        self.sample_interval = sample_interval  # ~30 Hz for responsive synchronization
        self.move_threshold = move_threshold    # Fine-grained movement threshold
        self.is_enabled = True
        self.is_running = False

        self._active_sockets: Set[WebSocket] = set()
        self._disabled_sockets: Set[WebSocket] = set()
        self._last_x: float = -1.0
        self._last_y: float = -1.0
        self._task: Optional[asyncio.Task] = None

        # Position getter for Windows platform, mockable for non-Windows or tests
        self._get_raw_pos_and_dims: Callable[[], tuple[int, int, int, int]] = self._default_get_pos

    def _default_get_pos(self) -> tuple[int, int, int, int]:
        """Query native Windows screen dimensions and cursor position."""
        if sys.platform != "win32":
            return 500, 500, 1920, 1080
        try:
            user32 = ctypes.windll.user32
            screen_w = max(1, user32.GetSystemMetrics(0))
            screen_h = max(1, user32.GetSystemMetrics(1))
            pt = POINT()
            success = user32.GetCursorPos(ctypes.byref(pt))
            if not success:
                # If access denied in worker/service thread, attach to the interactive input desktop
                hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
                if hdesk:
                    user32.SetThreadDesktop(hdesk)
                    user32.GetCursorPos(ctypes.byref(pt))

            return pt.x, pt.y, screen_w, screen_h
        except Exception as e:
            logger.debug("Failed querying cursor pos: %s", e)
            return 0, 0, 1920, 1080

    def add_client(self, websocket: WebSocket) -> None:
        """Register an authorized companion WebSocket for gaze updates."""
        self._active_sockets.add(websocket)
        # Reset last coords to immediately stream initial position to new client
        self._last_x = -1.0
        self._last_y = -1.0
        logger.debug("Added WebSocket client to cursor tracker (total: %d)", len(self._active_sockets))

    def remove_client(self, websocket: WebSocket) -> None:
        """Remove a companion WebSocket upon disconnect."""
        self._active_sockets.discard(websocket)
        self._disabled_sockets.discard(websocket)
        logger.debug("Removed WebSocket client from cursor tracker (remaining: %d)", len(self._active_sockets))

    def set_client_gaze_enabled(self, websocket: WebSocket, enabled: bool) -> None:
        """Enable or disable gaze updates for an individual client preference."""
        if enabled:
            self._disabled_sockets.discard(websocket)
        else:
            self._disabled_sockets.add(websocket)

    def set_global_enabled(self, enabled: bool) -> None:
        """Globally toggle cursor tracking."""
        self.is_enabled = enabled
        logger.info("Cursor gaze tracking globally %s", "enabled" if enabled else "disabled")

    async def start(self) -> None:
        """Start the async tracking background loop."""
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._tracking_loop())
        logger.info("Cursor tracker background loop started (20 Hz, threshold=%.3f)", self.move_threshold)

    async def stop(self) -> None:
        """Stop the tracking background loop."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Cursor tracker stopped.")

    async def _tracking_loop(self) -> None:
        """Main sampling loop broadcasting normalized coordinates to active clients."""
        while self.is_running:
            try:
                # If no active clients or globally disabled, sleep longer to conserve resources
                eligible_sockets = [
                    ws for ws in self._active_sockets if ws not in self._disabled_sockets
                ]

                if not self.is_enabled or not eligible_sockets:
                    await asyncio.sleep(0.2)
                    continue

                raw_x, raw_y, screen_w, screen_h = self._get_raw_pos_and_dims()
                norm_x = max(0.0, min(1.0, raw_x / screen_w))
                norm_y = max(0.0, min(1.0, raw_y / screen_h))

                # Check if cursor moved significantly
                delta = math.hypot(norm_x - self._last_x, norm_y - self._last_y)
                if delta >= self.move_threshold:
                    self._last_x = norm_x
                    self._last_y = norm_y

                    payload = {
                        "type": "cursor_gaze",
                        "x": round(norm_x, 4),
                        "y": round(norm_y, 4),
                        "timestamp": time.time(),
                    }

                    # Broadcast to eligible sockets
                    dead_sockets = []
                    for ws in eligible_sockets:
                        try:
                            await ws.send_json(payload)
                        except Exception:
                            dead_sockets.append(ws)

                    for dead in dead_sockets:
                        self.remove_client(dead)

                await asyncio.sleep(self.sample_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cursor tracking loop: %s", e)
                await asyncio.sleep(0.5)


# Global cursor tracker instance
cursor_tracker = CursorTracker()
