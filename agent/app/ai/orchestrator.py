"""Task Orchestrator for Flash Agent.

Coordinates the end-to-end flow of natural-language tasks:
1. Receives a user request.
2. Interprets the request using Gemma.
3. Validates the proposed action sequence against registry and safety rules.
4. Requests confirmation when necessary.
5. Executes the registered tools in sequence.
6. Enforces multi-step error recovery policies ('stop_on_error' vs 'continue_on_error').
7. Captures errors, timing, and output.
8. Reports the actual result to the user.
"""

import asyncio
import time
import uuid
from typing import Any, AsyncGenerator, Optional

from app.actions.registry import registry
from app.ai.interpreter import CommandInterpreter, command_interpreter
from app.ai.ollama_client import OllamaError
from app.config import settings
from app.logging_config import get_logger
from app.models import (
    InterpretationPlan,
    TaskExecutionResponse,
    TaskStepResult,
    UserTaskRequest,
)
from app.security import emergency_stop

logger = get_logger("flash.ai.orchestrator")


class TaskOrchestrator:
    """Orchestrates natural language task interpretation, validation, and execution."""

    def __init__(self, interpreter: Optional[CommandInterpreter] = None) -> None:
        self.interpreter = interpreter or command_interpreter

    def execute_task(self, request: UserTaskRequest) -> TaskExecutionResponse:
        """Process a natural-language user task from prompt to verified execution."""
        task_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()
        logger.info("Starting task [%s]: '%s'", task_id, request.prompt)

        # 1. Emergency stop check
        if emergency_stop.is_stopped:
            return TaskExecutionResponse(
                task_id=task_id,
                prompt=request.prompt,
                intent="Blocked by emergency stop",
                status="halted",
                success=False,
                explanation="Flash cannot execute actions while the emergency stop circuit is active.",
                error="EMERGENCY_STOP_ACTIVE",
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # 2. Interpret request via Gemma
        try:
            plan = self.interpreter.interpret(request.prompt)
        except OllamaError as e:
            logger.error("Ollama error interpreting task [%s]: %s", task_id, e)
            return TaskExecutionResponse(
                task_id=task_id,
                prompt=request.prompt,
                intent="Inference failed",
                status="failed",
                success=False,
                explanation=f"Flash could not consult local AI: {e.message}",
                error=e.error_code,
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )
        except Exception as e:
            logger.error("Interpretation error for task [%s]: %s", task_id, e)
            return TaskExecutionResponse(
                task_id=task_id,
                prompt=request.prompt,
                intent="Failed to interpret prompt",
                status="failed",
                success=False,
                explanation=f"Flash could not interpret the request: {e}",
                error=getattr(e, "error_code", "INTERPRETATION_ERROR"),
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # 3. Confirmation verification
        if plan.needs_confirmation and not request.confirmed:
            logger.info("Task [%s] paused: awaiting user confirmation.", task_id)
            return TaskExecutionResponse(
                task_id=task_id,
                prompt=request.prompt,
                intent=plan.intent,
                status="awaiting_confirmation",
                success=False,
                explanation=(
                    f"Flash needs your confirmation before proceeding with: {plan.user_facing_explanation}. "
                    "Please re-submit with confirmed=True."
                ),
                error="CONFIRMATION_REQUIRED",
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # 4. Multi-step execution loop
        step_results: list[TaskStepResult] = []
        overall_success = True
        error_msg = None
        error_policy = settings.multi_step_error_policy

        for idx, action_item in enumerate(plan.actions, start=1):
            # Check emergency stop before each step
            if emergency_stop.is_stopped:
                overall_success = False
                error_msg = "EMERGENCY_STOP_ACTIVE"
                step_results.append(
                    TaskStepResult(
                        step_index=idx,
                        action_name=action_item.action_name,
                        explanation=action_item.explanation,
                        success=False,
                        result=registry.execute(
                            name=action_item.action_name,
                            parameters=action_item.parameters,
                            confirmed=request.confirmed,
                        ),
                    )
                )
                break

            logger.info(
                "Task [%s] executing step %d/%d: '%s' with %s",
                task_id,
                idx,
                len(plan.actions),
                action_item.action_name,
                action_item.parameters,
            )

            result = registry.execute(
                name=action_item.action_name,
                parameters=action_item.parameters,
                confirmed=request.confirmed,
            )

            step_res = TaskStepResult(
                step_index=idx,
                action_name=action_item.action_name,
                explanation=action_item.explanation,
                success=result.success,
                result=result,
            )
            step_results.append(step_res)

            if not result.success:
                overall_success = False
                error_msg = result.error or "STEP_EXECUTION_FAILED"
                logger.warning(
                    "Task [%s] step %d (%s) failed: %s (Policy: %s)",
                    task_id,
                    idx,
                    action_item.action_name,
                    result.message,
                    error_policy,
                )
                if error_policy == "stop_on_error":
                    # Halt subsequent steps
                    break

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        status_str = "completed" if overall_success else "failed"

        # Final explanation
        if overall_success:
            final_explanation = plan.user_facing_explanation
        else:
            final_explanation = f"Task encountered an issue: {error_msg}. Check step results."

        return TaskExecutionResponse(
            task_id=task_id,
            prompt=request.prompt,
            intent=plan.intent,
            status=status_str,
            success=overall_success,
            explanation=final_explanation,
            steps=step_results,
            execution_time_ms=elapsed_ms,
            error=error_msg,
        )

    async def execute_task_stream(
        self, request: UserTaskRequest
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Process a natural-language task while yielding real-time progress events."""
        task_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()
        logger.info("Starting streamed task [%s]: '%s'", task_id, request.prompt)

        # 1. Yield started
        yield {
            "type": "task_started",
            "task_id": task_id,
            "prompt": request.prompt,
            "timestamp": time.time(),
        }

        # 2. Check emergency stop
        if emergency_stop.is_stopped:
            yield {
                "type": "task_failed",
                "task_id": task_id,
                "prompt": request.prompt,
                "intent": "Blocked by emergency stop",
                "error": "EMERGENCY_STOP_ACTIVE",
                "explanation": "Flash cannot execute actions while the emergency stop circuit is active.",
                "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
            }
            return

        # 3. Yield thinking state
        yield {
            "type": "task_thinking",
            "task_id": task_id,
            "intent": "Interpreting with local Gemma...",
            "explanation": "Flash is planning your task slowly and carefully...",
            "timestamp": time.time(),
        }

        # 4. Interpret request via Gemma (run in threadpool so event loop is not blocked)
        try:
            plan = await asyncio.to_thread(self.interpreter.interpret, request.prompt)
        except OllamaError as e:
            logger.error("Ollama error interpreting task [%s]: %s", task_id, e)
            yield {
                "type": "task_failed",
                "task_id": task_id,
                "prompt": request.prompt,
                "intent": "Inference failed",
                "error": e.error_code,
                "explanation": f"Flash could not consult local AI: {e.message}",
                "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
            }
            return
        except Exception as e:
            logger.error("Interpretation error for task [%s]: %s", task_id, e)
            yield {
                "type": "task_failed",
                "task_id": task_id,
                "prompt": request.prompt,
                "intent": "Failed to interpret prompt",
                "error": getattr(e, "error_code", "INTERPRETATION_ERROR"),
                "explanation": f"Flash could not interpret the request: {e}",
                "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
            }
            return

        # 5. Yield planned status
        yield {
            "type": "task_planned",
            "task_id": task_id,
            "intent": plan.intent,
            "explanation": plan.user_facing_explanation,
            "total_steps": len(plan.actions),
            "actions": [a.action_name for a in plan.actions],
            "timestamp": time.time(),
        }

        # 6. Check confirmation
        if plan.needs_confirmation and not request.confirmed:
            yield {
                "type": "task_awaiting_confirmation",
                "task_id": task_id,
                "intent": plan.intent,
                "explanation": (
                    f"Flash needs your confirmation before proceeding with: {plan.user_facing_explanation}. "
                    "Please re-submit with confirmed=True."
                ),
                "error": "CONFIRMATION_REQUIRED",
                "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
            }
            return

        # 7. Execute steps sequentially
        step_results: list[dict[str, Any]] = []
        overall_success = True
        error_msg = None
        error_policy = settings.multi_step_error_policy

        for idx, action_item in enumerate(plan.actions, start=1):
            if emergency_stop.is_stopped:
                overall_success = False
                error_msg = "EMERGENCY_STOP_ACTIVE"
                yield {
                    "type": "task_step_progress",
                    "task_id": task_id,
                    "step_index": idx,
                    "total_steps": len(plan.actions),
                    "action": action_item.action_name,
                    "explanation": "Halted by emergency stop.",
                }
                break

            yield {
                "type": "task_step_progress",
                "task_id": task_id,
                "step_index": idx,
                "total_steps": len(plan.actions),
                "action": action_item.action_name,
                "explanation": action_item.explanation,
                "timestamp": time.time(),
            }

            result = await asyncio.to_thread(
                registry.execute,
                name=action_item.action_name,
                parameters=action_item.parameters,
                confirmed=request.confirmed,
            )

            step_data = {
                "step_index": idx,
                "action_name": action_item.action_name,
                "explanation": action_item.explanation,
                "success": result.success,
                "message": result.message,
                "output_path": result.output_path,
                "data": result.data,
                "error": result.error,
                "execution_time_ms": result.execution_time_ms,
            }
            step_results.append(step_data)

            yield {
                "type": "task_step_completed",
                "task_id": task_id,
                "step_index": idx,
                "total_steps": len(plan.actions),
                "action": action_item.action_name,
                "success": result.success,
                "message": result.message,
                "output_path": result.output_path,
                "timestamp": time.time(),
            }

            if not result.success:
                overall_success = False
                error_msg = result.error or "STEP_EXECUTION_FAILED"
                if error_policy == "stop_on_error":
                    break

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        final_explanation = (
            plan.user_facing_explanation
            if overall_success
            else f"Task encountered an issue: {error_msg}."
        )

        yield {
            "type": "task_finished",
            "task_id": task_id,
            "prompt": request.prompt,
            "intent": plan.intent,
            "success": overall_success,
            "status": "completed" if overall_success else "failed",
            "explanation": final_explanation,
            "steps": step_results,
            "execution_time_ms": elapsed_ms,
            "error": error_msg,
            "timestamp": time.time(),
        }



# Global orchestrator singleton
task_orchestrator = TaskOrchestrator()
