"""Inspector: replay() / summary() output to chosen stream."""

import io

from cantus.core.action import CallSkillAction
from cantus.core.event_stream import EventStream
from cantus.core.observation import SkillObservation
from cantus.inspect import Inspector


def test_replay_writes_trace():
    stream = EventStream()
    stream.append(CallSkillAction(skill_name="alpha"))
    stream.append(SkillObservation(skill_name="alpha", result=42))
    buf = io.StringIO()
    Inspector(stream).replay(out=buf)
    text = buf.getvalue()
    assert "alpha" in text
    assert "[0]" in text


def test_summary_counts_correctly():
    stream = EventStream()
    stream.append(CallSkillAction(skill_name="x"))
    stream.append(CallSkillAction(skill_name="y"))
    stream.append(SkillObservation(skill_name="x", result=1))
    buf = io.StringIO()
    Inspector(stream).summary(out=buf)
    text = buf.getvalue()
    assert "3 events" in text
    assert "2 actions" in text
    assert "1 observations" in text
