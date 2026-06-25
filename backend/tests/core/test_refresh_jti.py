from app.core.security import create_refresh_token, decode_token


def test_refresh_token_carries_jti():
    token = create_refresh_token("user-1", "jti-abc")
    payload = decode_token(token)
    assert payload is not None
    assert payload["jti"] == "jti-abc"
    assert payload["type"] == "refresh"
    assert payload["sub"] == "user-1"
