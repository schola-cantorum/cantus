"""Tests for cantus.serve.channels._errors."""

from __future__ import annotations


def test_channelsenderror_attributes() -> None:
    from cantus.serve.channels._errors import ChannelSendError

    err = ChannelSendError(
        status_code=400,
        body_excerpt='{"message":"Invalid reply token"}',
        provider="line",
    )
    assert err.status_code == 400
    assert err.body_excerpt == '{"message":"Invalid reply token"}'
    assert err.provider == "line"
    assert isinstance(err, Exception)


def test_channelsenderror_str_contains_provider_and_status() -> None:
    from cantus.serve.channels._errors import ChannelSendError

    err = ChannelSendError(
        status_code=403, body_excerpt="forbidden", provider="telegram"
    )
    s = str(err)
    assert "telegram" in s
    assert "403" in s
    assert "forbidden" in s


def test_channelsenderror_no_secret_leak() -> None:
    """str(err) must not contain any placeholder fake token. Constructor
    only takes status_code/body_excerpt/provider; the body_excerpt is the
    only string the caller controls. The class does not store nor
    interpolate any Settings object or secret."""
    from cantus.serve.channels._errors import ChannelSendError

    fake_token = "line-token-XYZ"
    # body_excerpt is the only writable string field; verify it does not
    # auto-pick up tokens from anywhere.
    err = ChannelSendError(
        status_code=400, body_excerpt="Invalid reply token", provider="line"
    )
    assert fake_token not in str(err)
    assert fake_token not in repr(err)
