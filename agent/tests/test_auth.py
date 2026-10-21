"""Unit and integration tests for device pairing and token authentication."""

import time
import pytest
from starlette.testclient import TestClient

from app.auth import PairingManager, TokenManager, pairing_manager, token_manager
from app.main import app


@pytest.fixture
def clean_auth_managers():
    """Create fresh isolated auth managers for unit tests."""
    p_mgr = PairingManager(code_ttl_seconds=10)
    t_mgr = TokenManager(persist_to_disk=False)
    return p_mgr, t_mgr


def test_pairing_code_generation_and_consumption(clean_auth_managers):
    """Test generating a 6-digit pairing code and consuming it."""
    p_mgr, _ = clean_auth_managers
    code = p_mgr.generate_code()
    assert len(code) == 7  # "123-456"
    assert "-" in code

    # Consumption with dash
    assert p_mgr.verify_and_consume(code) is True
    # One-time use: cannot consume twice
    assert p_mgr.verify_and_consume(code) is False


def test_pairing_code_consumption_without_dash(clean_auth_managers):
    """Test consuming code entered without dash (e.g. '123456')."""
    p_mgr, _ = clean_auth_managers
    code = p_mgr.generate_code()
    clean_digits = code.replace("-", "")
    assert p_mgr.verify_and_consume(clean_digits) is True


def test_pairing_code_expiry(clean_auth_managers):
    """Test that expired pairing codes are rejected."""
    p_mgr = PairingManager(code_ttl_seconds=-1)  # expired immediately
    code = p_mgr.generate_code()
    assert p_mgr.verify_and_consume(code) is False


def test_pairing_code_get_or_create(clean_auth_managers):
    """Test get_or_create_code_info retrieves active code with remaining TTL."""
    p_mgr, _ = clean_auth_managers
    code1, ttl1, exp1 = p_mgr.get_or_create_code_info()
    assert len(code1) == 7
    assert ttl1 > 0

    # Second call should return the exact same active code
    code2, ttl2, exp2 = p_mgr.get_or_create_code_info()
    assert code1 == code2
    assert exp1 == exp2


def test_token_lifecycle(clean_auth_managers):
    """Test issuing, validating, revoking, and listing tokens."""
    _, t_mgr = clean_auth_managers
    token = t_mgr.issue_token("Redmi Note 12")
    assert len(token) == 64  # 32 bytes hex
    assert t_mgr.validate_token(token) is True
    assert t_mgr.validate_token("invalid_token") is False
    assert t_mgr.validate_token(None) is False

    # List tokens
    catalog = t_mgr.list_tokens()
    assert len(catalog) == 1
    assert catalog[0]["client_name"] == "Redmi Note 12"
    assert "..." in catalog[0]["token_prefix"]

    # Revoke
    assert t_mgr.revoke_token(token) is True
    assert t_mgr.validate_token(token) is False
    assert t_mgr.revoke_token(token) is False


def test_api_pairing_and_auth_endpoints():
    """Test HTTP API pairing flow: get-code -> pair -> verify -> revoke."""
    with TestClient(app) as client:
        # 1. Fetch pairing code
        res_code = client.post("/api/v1/auth/pair-code")
        assert res_code.status_code == 200
        code_data = res_code.json()
        code = code_data["code"]
        assert len(code) == 7

        # 2. Pair with invalid code
        res_fail = client.post("/api/v1/auth/pair", json={"code": "000-000", "device_name": "TestPhone"})
        assert res_fail.status_code == 400

        # 3. Pair with valid code
        res_pair = client.post("/api/v1/auth/pair", json={"code": code, "device_name": "Redmi Android"})
        assert res_pair.status_code == 200
        pair_data = res_pair.json()
        token = pair_data["token"]
        assert pair_data["device_name"] == "Redmi Android"
        assert pair_data["status"] == "authenticated"

        # 4. Verify token
        res_verify = client.post("/api/v1/auth/verify", headers={"Authorization": f"Bearer {token}"})
        assert res_verify.status_code == 200
        assert res_verify.json()["valid"] is True

        # 5. Revoke token
        res_revoke = client.post("/api/v1/auth/revoke", json={"token": token})
        assert res_revoke.status_code == 200
        assert res_revoke.json()["success"] is True

        # 6. Verify again - now invalid
        res_verify_again = client.post("/api/v1/auth/verify", headers={"Authorization": f"Bearer {token}"})
        assert res_verify_again.status_code == 200
        assert res_verify_again.json()["valid"] is False


def test_remote_access_denied_without_auth():
    """Test that requests from non-loopback IPs require bearer authentication."""
    # TestClient lets us simulate remote client IP via client=("192.168.1.100", 54321)
    remote_client = TestClient(app, client=("192.168.1.100", 54321))

    # Health check and root remain public on LAN
    assert remote_client.get("/health").status_code == 200
    assert remote_client.get("/").status_code == 200

    # Computer control action without token MUST be rejected with 401
    res_denied = remote_client.post(
        "/api/v1/actions/execute",
        json={"action": "get_agent_status", "parameters": {}},
    )
    assert res_denied.status_code == 401
    assert "Unauthorized" in res_denied.json()["detail"]

    # Stop endpoint without token MUST be rejected with 401
    res_stop_denied = remote_client.post("/api/v1/stop")
    assert res_stop_denied.status_code == 401

    # Now issue a valid token
    valid_token = token_manager.issue_token("Test Remote Phone")

    # With valid token, action execution is permitted!
    res_allowed = remote_client.post(
        "/api/v1/actions/execute",
        json={"action": "get_agent_status", "parameters": {}},
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert res_allowed.status_code == 200
    assert res_allowed.json()["success"] is True
