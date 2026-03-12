import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_hash_password():
    password = "TestPassword123"
    hashed = hash_password(password)
    assert hashed != password
    assert len(hashed) > 0


def test_verify_password_correct():
    password = "TestPassword123"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    password = "TestPassword123"
    hashed = hash_password(password)
    assert verify_password("WrongPassword", hashed) is False


def test_create_access_token():
    token = create_access_token(subject="user-123")
    assert token is not None
    assert len(token) > 0


def test_decode_access_token():
    token = create_access_token(subject="user-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_create_refresh_token():
    token = create_refresh_token(subject="user-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "refresh"


def test_decode_invalid_token():
    with pytest.raises(ValueError):
        decode_token("invalid.token.here")