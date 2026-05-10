"""Chat template helper merges system into first user turn."""

from cantus.model.chat_template import Message, merge_system_into_first_user


def test_pure_user_passthrough():
    msgs = [Message(role="user", content="hi")]
    out = merge_system_into_first_user(msgs)
    assert out == msgs


def test_system_prepended_to_first_user():
    msgs = [
        Message(role="system", content="You are a helpful tutor."),
        Message(role="user", content="What is recursion?"),
    ]
    out = merge_system_into_first_user(msgs)
    assert len(out) == 1
    assert out[0].role == "user"
    assert "helpful tutor" in out[0].content
    assert "recursion" in out[0].content


def test_multiple_system_messages_joined():
    msgs = [
        Message(role="system", content="A"),
        Message(role="system", content="B"),
        Message(role="user", content="Q"),
    ]
    out = merge_system_into_first_user(msgs)
    assert "A" in out[0].content and "B" in out[0].content
    assert "\n\n" in out[0].content
    assert "Q" in out[0].content


def test_dict_form_accepted():
    msgs = [{"role": "system", "content": "X"}, {"role": "user", "content": "Y"}]
    out = merge_system_into_first_user(msgs)
    assert "X" in out[0].content
    assert "Y" in out[0].content


def test_system_only_creates_synthetic_user():
    msgs = [Message(role="system", content="just system")]
    out = merge_system_into_first_user(msgs)
    assert len(out) == 1
    assert out[0].role == "user"
    assert "just system" in out[0].content


def test_multi_turn_only_first_user_gets_system():
    msgs = [
        Message(role="system", content="S"),
        Message(role="user", content="U1"),
        Message(role="assistant", content="A1"),
        Message(role="user", content="U2"),
    ]
    out = merge_system_into_first_user(msgs)
    assert "S" in out[0].content and "U1" in out[0].content
    # The second user turn should remain untouched.
    assert out[2].content == "U2"
    assert "S" not in out[2].content
