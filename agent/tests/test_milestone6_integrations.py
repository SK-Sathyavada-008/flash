"""Unit and integration tests for Milestone 6 Partner Integrations:
- ElevenLabs & Speech Abstraction
- Stagehand & Browserbase
- MongoDB Atlas & Storage Layer
- Sentry Telemetry & Privacy Data Scrubber
- Gemma Benchmark Suite
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from app.speech.base import SpeechResult
from app.speech.local_provider import LocalSpeechProvider
from app.speech.elevenlabs_provider import ElevenLabsSpeechProvider
from app.speech import get_speech_provider
from app.actions.speak_text import SpeakTextAction
from app.actions.stagehand_browser import StagehandBrowserAction
from app.actions.manage_routines import ManageRoutinesAction
from app.storage.local_storage import LocalFileStorage
from app.storage.mongo_atlas import MongoAtlasStorage
from app.telemetry.sentry_tracer import scrub_sensitive_event, tracer, init_sentry
from app.ai.benchmark import run_benchmark


class TestSpeechProviderIntegration:
    """Test Speech Abstraction & ElevenLabs fallback."""

    def test_local_speech_synthesis(self):
        provider = LocalSpeechProvider()
        assert provider.get_provider_name() == "local_windows_sapi"
        assert not provider.requires_cloud()

        result = provider.synthesize("Flash is ready.")
        assert isinstance(result, SpeechResult)
        assert result.success is True
        assert result.provider == "local_windows_sapi"

    def test_elevenlabs_fallback_when_unconfigured(self):
        # Without API key, it must gracefully fallback to local
        provider = ElevenLabsSpeechProvider(api_key="")
        assert not provider.is_configured()
        result = provider.synthesize("Test speech without key.")
        assert result.success is True
        assert result.provider == "local_windows_sapi"

    @patch("httpx.Client.post")
    def test_elevenlabs_cloud_synthesis(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_mp3_audio_stream"
        mock_post.return_value = mock_response

        provider = ElevenLabsSpeechProvider(api_key="sk_test_key_123")
        assert provider.is_configured()
        result = provider.synthesize("Testing cloud voice.")
        assert result.success is True
        assert result.provider == "elevenlabs"
        assert result.audio_bytes == b"fake_mp3_audio_stream"

    def test_speak_text_action(self):
        action = SpeakTextAction()
        assert action.name == "speak_text"
        resp = action.run({"text": "Hello world from Flash sloth!"})
        assert resp.success is True
        assert "spoken" in resp.message.lower() or "synthes" in resp.message.lower()


class TestStagehandBrowserIntegration:
    """Test Stagehand AI Browser Automation & Browserbase."""

    def test_stagehand_action_validation(self):
        action = StagehandBrowserAction()
        assert action.name == "stagehand_browser"

        # Missing url
        resp = action.run({"url": "", "operation": "act", "instruction": "click test"})
        assert resp.success is False
        assert resp.error == "MISSING_PARAMETER"

        # Unsafe url
        resp = action.run({"url": "file:///etc/passwd", "operation": "act", "instruction": "click test"})
        assert resp.success is False
        assert resp.error == "UNSAFE_URL"

    @patch("app.services.browser_stagehand.StagehandBrowserService.act")
    def test_stagehand_act_execution(self, mock_act):
        mock_act.return_value = {
            "backend": "local_playwright",
            "url": "https://example.com",
            "title": "Example Domain",
            "instruction": "click More Information",
            "action_taken": "clicked text 'More Information'",
            "success": True,
        }
        action = StagehandBrowserAction()
        resp = action.run({
            "url": "https://example.com",
            "operation": "act",
            "instruction": "click More Information",
        })
        assert resp.success is True
        assert resp.data["action_taken"] == "clicked text 'More Information'"
        assert resp.data["backend"] == "local_playwright"

    @patch("app.services.browser_stagehand.StagehandBrowserService.extract")
    def test_stagehand_extract_execution(self, mock_extract):
        mock_extract.return_value = {
            "backend": "local_playwright",
            "url": "https://example.com",
            "title": "Example Domain",
            "instruction": "extract heading",
            "extracted_data": {"page_title": "Example Domain", "headings": ["Example Domain"]},
            "success": True,
        }
        action = StagehandBrowserAction()
        resp = action.run({
            "url": "https://example.com",
            "operation": "extract",
            "instruction": "extract heading",
        })
        assert resp.success is True
        assert "headings" in resp.data["extracted_data"]


class TestStorageAndRoutines:
    """Test Local JSON Storage and MongoDB Atlas layer."""

    def test_local_storage_lifecycle(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            storage = LocalFileStorage(file_path=tmp_path)
            assert storage.get_provider_name() == "local_json"
            assert storage.is_cloud_enabled() is False

            # Routine save & get
            saved = storage.save_routine(
                "morning_routine",
                [{"action": "open_url", "url": "https://news.ycombinator.com"}],
                "Open morning tech news",
            )
            assert saved is True

            routine = storage.get_routine("morning_routine")
            assert routine is not None
            assert routine["name"] == "morning_routine"
            assert len(routine["steps"]) == 1

            # List routines
            all_routines = storage.list_routines()
            assert len(all_routines) == 1

            # Preferences
            storage.save_preferences({"speech_speed": 1.25, "theme": "cyber"})
            prefs = storage.get_preferences()
            assert prefs["speech_speed"] == 1.25
            assert prefs["theme"] == "cyber"

            # Delete routine
            deleted = storage.delete_routine("morning_routine")
            assert deleted is True
            assert storage.get_routine("morning_routine") is None
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_mongo_atlas_graceful_fallback(self):
        # When unconfigured, fallback operates transparently
        storage = MongoAtlasStorage(uri="")
        assert not storage.is_cloud_enabled()
        assert "fallback" in storage.get_provider_name()

        # Should operate through local fallback seamlessly
        assert storage.save_routine("test_routine", [{"action": "test"}])
        assert storage.get_routine("test_routine") is not None
        assert storage.delete_routine("test_routine")

    def test_manage_routines_action(self):
        action = ManageRoutinesAction()
        assert action.name == "manage_routines"

        # List
        resp = action.run({"operation": "list"})
        assert resp.success is True
        assert "routines" in resp.data

        # Save
        resp = action.run({
            "operation": "save",
            "name": "study_mode",
            "description": "Prepare desktop for study",
            "steps": [{"action": "open_application", "app_name": "notepad"}],
        })
        assert resp.success is True

        # Get
        resp = action.run({"operation": "get", "name": "study_mode"})
        assert resp.success is True
        assert resp.data["name"] == "study_mode"

        # Delete
        resp = action.run({"operation": "delete", "name": "study_mode"})
        assert resp.success is True


class TestSentryPrivacyAndTelemetry:
    """Test Sentry telemetry and privacy data scrubber."""

    def test_privacy_scrubber_redacts_paths_and_tokens(self):
        event = {
            "breadcrumbs": {
                "values": [
                    {"message": "User file accessed at C:\\Users\\Administrator\\Documents\\secret.txt"},
                    {"message": "Auth header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"},
                    {"message": "Ollama query at /home/user/workspace/flash"},
                    {"data": {"screenshot_bytes": "base64_data_here_12345"}},
                ]
            },
            "extra": {
                "user_desktop_path": "C:\\Users\\JohnDoe\\Desktop",
                "api_key": "api_key=secret_live_key_999",
                "screen_capture": "raw_image_data",
            },
        }

        hint = {}
        scrubbed = scrub_sensitive_event(event, hint)

        b0 = scrubbed["breadcrumbs"]["values"][0]["message"]
        assert "C:\\Users\\Administrator" not in b0
        assert "[LOCAL_USER_PATH]" in b0

        b1 = scrubbed["breadcrumbs"]["values"][1]["message"]
        assert "eyJhbGciOi" not in b1
        assert "Bearer [REDACTED]" in b1

        b3 = scrubbed["breadcrumbs"]["values"][3]["data"]
        assert b3["screenshot_bytes"] == "[REDACTED_IMAGE_BYTES]"

        extra = scrubbed["extra"]
        assert "[LOCAL_USER_PATH]" in extra["user_desktop_path"]
        assert "JohnDoe" not in extra["user_desktop_path"]
        assert "secret_live_key_999" not in extra["api_key"]
        assert extra["screen_capture"] == "[REDACTED_IMAGE_BYTES]"

    def test_tracer_records_spans_safely(self):
        # Tracing must never crash even without SENTRY_DSN
        tracer.record_interpretation("create grocery list", 1.25, True, "create_grocery_list")
        tracer.record_tool_execution("create_grocery_list", 4.5, True)
        tracer.record_browser_workflow("https://example.com", "act", 120.0, True, "local_playwright")
        tracer.record_connection_failure("mongodb", Exception("Network unreachable"))


class TestGemmaBenchmarkSuite:
    """Test Gemma vs Fast-Path Benchmark Execution."""

    def test_benchmark_structure(self):
        with patch("app.ai.interpreter.CommandInterpreter.interpret_with_llm") as mock_llm:
            mock_plan = MagicMock()
            mock_action = MagicMock()
            mock_action.action_name = "create_spreadsheet"
            mock_action.parameters = {"filename": "q3_budget.xlsx"}
            mock_plan.actions = [mock_action]
            mock_llm.return_value = mock_plan

            results = run_benchmark()
            assert "tasks_tested" in results
            assert results["tasks_tested"] == 5
            assert results["fast_path_accuracy_pct"] == 100.0
            assert results["privacy"]["data_exfiltrated_to_cloud"] is False
            assert results["cost"]["token_cost_usd"] == 0.0
            assert len(results["details"]) == 5
