"""The v0.6 serve routes (/skills/{name}, /skills, /introspection/skills) as deprecated aliases.

Every expected text, header value and list below is written out in full; nothing is imported from
the package to build an expected value.
"""

import asyncio
import copy
import logging
import os
from typing import Any

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from cantus import Registry, tool  # noqa: E402
from cantus.config import Settings  # noqa: E402
from cantus.serve import serve  # noqa: E402
from cantus.serve.introspection import (  # noqa: E402
    DataflowGraph,
    IntrospectionSnapshot,
    PermissionsSnapshot,
    ToolEntry,
    register_introspection_routes,
)

DEPRECATION = "@1794441600"
LINK = (
    "<https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/"
    'MIGRATION_v0.6.0_to_v0.7.0.md>; rel="deprecation"; type="text/markdown"'
)
_GUIDE = (
    "https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/"
    "MIGRATION_v0.6.0_to_v0.7.0.md"
)
LOG_INVOKE = (
    "Legacy route /skills/{name} is deprecated since cantus 0.7.0; use /tools/{name}. See " + _GUIDE
)
LOG_DASHBOARD = "Legacy route /skills is deprecated since cantus 0.7.0; use /tools. See " + _GUIDE
LOG_INTROSPECTION = (
    "Legacy route /introspection/skills is deprecated since cantus 0.7.0; "
    "use /introspection/tools. See " + _GUIDE
)

ADD_SCHEMA = {
    "properties": {"a": {"title": "A", "type": "integer"}, "b": {"title": "B", "type": "integer"}},
    "required": ["a", "b"],
    "title": "AddArgs",
    "type": "object",
}
SPECS = [
    {"name": "add", "description": "Add two numbers.", "args_schema": ADD_SCHEMA},
    {
        "name": "boom",
        "description": "Always fails.",
        "args_schema": {
            "properties": {"x": {"title": "X", "type": "integer"}},
            "required": ["x"],
            "title": "BoomArgs",
            "type": "object",
        },
    },
    {
        "name": "multiply",
        "description": "Multiply two numbers.",
        "args_schema": {
            "properties": {
                "a": {"title": "A", "type": "integer"},
                "b": {"title": "B", "type": "integer"},
            },
            "required": ["a", "b"],
            "title": "MultiplyArgs",
            "type": "object",
        },
    },
    {
        "name": "ping",
        "description": "Ping.",
        "args_schema": {"properties": {}, "title": "PingArgs", "type": "object"},
    },
]
INTERNAL_ERROR = "Internal Server Error"
AUTH_REQUIRED = {"detail": "Authentication required"}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith("CANTUS_SERVE_"):
            monkeypatch.delenv(key, raising=False)


def _registry() -> Registry:
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    def multiply(a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b

    def boom(x: int) -> int:
        """Always fails."""
        raise RuntimeError("secret detail")

    def ping() -> str:
        """Ping."""
        return "pong"

    return Registry(tools=[tool(add), tool(multiply), tool(boom), tool(ping)])


def _settings(mode: str = "none", **kwargs: Any) -> Settings:
    if mode == "bearer":
        kwargs.update(auth_mode="bearer", bearer_token="t0k")
    elif mode == "api-key":
        kwargs.update(auth_mode="api-key", api_key="k3y")
    return Settings(**kwargs)


def _headers(mode: str, which: str) -> dict[str, str]:
    """Credentials for ``which`` in ``none`` / ``wrong`` / ``right``."""
    if which == "none":
        return {}
    if mode == "bearer":
        return {"Authorization": "Bearer " + ("t0k" if which == "right" else "WRONG")}
    return {"X-API-Key": "k3y" if which == "right" else "WRONG"}


def _client(mode: str = "none", **kwargs: Any) -> TestClient:
    return TestClient(serve(_registry(), settings=_settings(mode, **kwargs)), raise_server_exceptions=False)


def _serve_records(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "cantus.serve"]


def _has_notice(response) -> bool:
    return "deprecation" in response.headers or "link" in response.headers


def _assert_notice(response) -> None:
    assert response.headers["deprecation"] == DEPRECATION
    assert response.headers["link"] == LINK


# (method, alias path, primary path, request kwargs, expected 200 body)
_ALIASES = [
    ("POST", "/skills/add", "/tools/add", {"json": {"a": 3, "b": 4}}, {"result": 7}),
    ("GET", "/skills", "/tools", {}, SPECS),
    ("GET", "/introspection/skills", "/introspection/tools", {}, SPECS),
]
_ALIAS_IDS = ["invoke", "dashboard", "introspection"]


# --- Row 23: same behaviour as the primary ---------------------------------


@pytest.mark.parametrize("method,alias,primary,kwargs,expected", _ALIASES, ids=_ALIAS_IDS)
@pytest.mark.parametrize("mode", ["none", "bearer", "api-key"])
def test_alias_and_primary_answer_alike_for_every_credential(
    mode, method, alias, primary, kwargs, expected
):
    client = _client(mode)
    cases = ["right"] if mode == "none" else ["none", "wrong", "right"]
    for which in cases:
        headers = _headers(mode, which)
        a = client.request(method, alias, headers=headers, **kwargs)
        p = client.request(method, primary, headers=headers, **kwargs)
        if which == "right" or mode == "none":
            assert a.status_code == 200
            assert a.json() == expected
        else:
            assert a.status_code == 401
            assert a.json() == AUTH_REQUIRED
        assert (a.status_code, a.content) == (p.status_code, p.content)
        _assert_notice(a)
        assert not _has_notice(p)


def test_alias_list_routes_are_404_when_their_group_is_off():
    assert _client(dashboard=False).get("/skills").status_code == 404
    assert _client(introspection=False).get("/introspection/skills").status_code == 404


@pytest.mark.parametrize(
    "alias,flag",
    [("/skills", "dashboard_requires_auth"), ("/introspection/skills", "introspection_requires_auth")],
)
def test_alias_list_route_is_open_when_its_requires_auth_flag_is_off(alias, flag):
    client = _client("bearer", **{flag: False})
    response = client.get(alias)
    assert response.status_code == 200
    assert response.json() == SPECS


def test_alias_invoke_errors_match_the_primary_and_the_literals():
    client = _client()
    cases = [
        ({"x": 1}, "boom", 500, INTERNAL_ERROR),
        ({"a": 1}, "add", 500, INTERNAL_ERROR),
        ([1, 2], "ping", 200, {"result": "pong"}),
    ]
    for body, name, status, expected in cases:
        a = client.post(f"/skills/{name}", json=body)
        p = client.post(f"/tools/{name}", json=body)
        assert a.status_code == status
        assert (a.json() if status == 200 else a.text) == expected
        assert (a.status_code, a.content) == (p.status_code, p.content)


# --- Row 24: headers on aliases only ---------------------------------------


def test_alias_responses_carry_both_headers_on_200_401_and_500():
    ok = _client().post("/skills/add", json={"a": 3, "b": 4})
    assert ok.status_code == 200
    _assert_notice(ok)

    denied = _client("bearer").post("/skills/add", json={"a": 3, "b": 4})
    assert denied.status_code == 401
    _assert_notice(denied)

    boom = _client().post("/skills/boom", json={"x": 1})
    assert boom.status_code == 500
    _assert_notice(boom)

    bad_json = _client().post("/skills/add", content=b"{not json")
    assert bad_json.status_code == 500
    _assert_notice(bad_json)


def test_alias_405_responses_carry_both_headers():
    client = _client()
    responses = [
        client.get("/skills/add"),
        client.head("/skills"),
        client.options("/skills/add"),
        client.post("/skills", json={}),
        client.post("/introspection/skills", json={}),
    ]
    for response in responses:
        assert response.status_code == 405
        _assert_notice(response)


def test_primary_and_other_responses_carry_neither_header():
    client = _client()
    bearer = _client("bearer")
    responses = [
        client.post("/tools/add", json={"a": 3, "b": 4}),
        client.post("/tools/boom", json={"x": 1}),
        client.post("/tools/add", content=b"{not json"),
        bearer.post("/tools/add", json={"a": 3, "b": 4}),
        client.get("/tools/add"),
        client.head("/tools"),
        client.options("/tools/add"),
        client.post("/tools", json={}),
        client.post("/introspection/tools", json={}),
        client.get("/tools"),
        client.get("/introspection/tools"),
        client.get("/health"),
        client.get("/introspection"),
        client.post("/skills/nope", json={}),
        _client(dashboard=False).get("/skills"),
        _client(introspection=False).get("/introspection/skills"),
        client.get("/skills/", follow_redirects=False),
    ]
    for response in responses:
        assert not _has_notice(response), response.request.url
    assert responses[-1].status_code == 307
    assert responses[-2].status_code == 404
    assert responses[-3].status_code == 404
    assert responses[-4].status_code == 404


def test_host_exception_handler_still_shapes_the_alias_response():
    app = serve(_registry(), settings=_settings())

    def handler(request, exc):
        return JSONResponse({"custom": 1}, status_code=500)

    app.add_exception_handler(Exception, handler)
    client = TestClient(app, raise_server_exceptions=False)

    a = client.post("/skills/boom", json={"x": 1})
    p = client.post("/tools/boom", json={"x": 1})
    assert a.status_code == p.status_code == 500
    assert a.json() == p.json() == {"custom": 1}
    _assert_notice(a)
    assert not _has_notice(p)


# --- Row 25: OpenAPI -------------------------------------------------------


def test_openapi_marks_alias_operations_deprecated_with_literal_ids_and_summaries():
    paths = _client().get("/openapi.json").json()["paths"]

    invoke = paths["/skills/add"]["post"]
    dashboard = paths["/skills"]["get"]
    introspection = paths["/introspection/skills"]["get"]
    assert invoke["deprecated"] is True
    assert dashboard["deprecated"] is True
    assert introspection["deprecated"] is True
    assert invoke["operationId"] == "invoke_skill_add_skills_add_post"
    assert dashboard["operationId"] == "dashboard_list_skills_skills_get"
    assert introspection["operationId"] == "introspection_skills_introspection_skills_get"
    assert invoke["summary"] == "Invoke Skill: add"
    assert dashboard["summary"] == "List registered Skills"
    assert introspection["summary"] == "Registered Skill specs"
    assert invoke["requestBody"]["content"]["application/json"]["schema"] == ADD_SCHEMA
    assert invoke["description"] == "Add two numbers."

    deprecated = sorted(
        (path, method)
        for path, operations in paths.items()
        for method, operation in operations.items()
        if operation.get("deprecated")
    )
    assert deprecated == [
        ("/introspection/skills", "get"),
        ("/skills", "get"),
        ("/skills/add", "post"),
        ("/skills/boom", "post"),
        ("/skills/multiply", "post"),
        ("/skills/ping", "post"),
    ]


def test_a_tool_without_a_docstring_has_the_tool_fallback_description_on_both_families():
    def nodoc(value: str) -> str:
        return value

    app = serve(Registry(tools=[tool(nodoc)]), settings=_settings())
    paths = TestClient(app).get("/openapi.json").json()["paths"]

    assert paths["/skills/nodoc"]["post"]["description"] == "Invoke cantus Tool 'nodoc'"
    assert paths["/tools/nodoc"]["post"]["description"] == "Invoke cantus Tool 'nodoc'"


# --- Row 26: one log record per template -----------------------------------


def test_each_alias_template_is_logged_once_per_application(caplog):
    caplog.set_level(logging.WARNING)
    client = _client()
    client.post("/skills/add", json={"a": 1, "b": 2})
    client.post("/skills/multiply", json={"a": 1, "b": 2})
    client.post("/skills/add", json={"a": 1, "b": 2})
    client.post(
        "/skills/add",
        json={"a": 1, "b": 2, "note": "MARKER-BODY-456"},
        headers={"Authorization": "Bearer t0k"},
    )
    records = _serve_records(caplog)
    assert [r.getMessage() for r in records] == [LOG_INVOKE]
    for record in caplog.records:
        text = record.getMessage() + repr(record.args)
        assert "WRONG-SECRET-123" not in text
        assert "MARKER-BODY-456" not in text
        assert "t0k" not in text
    assert records[0].levelname == "WARNING"

    caplog.clear()
    client.get("/skills")
    client.get("/skills")
    assert [r.getMessage() for r in _serve_records(caplog)] == [LOG_DASHBOARD]

    caplog.clear()
    client.get("/introspection/skills")
    client.get("/introspection/skills")
    assert [r.getMessage() for r in _serve_records(caplog)] == [LOG_INTROSPECTION]


def test_primary_routes_and_non_alias_requests_log_nothing(caplog):
    caplog.set_level(logging.WARNING)
    client = _client()
    client.post("/tools/add", json={"a": 1, "b": 2})
    client.get("/tools")
    client.get("/introspection/tools")
    client.post("/skills/nope", json={})
    assert client.get("/skills/", follow_redirects=False).status_code == 307
    assert _serve_records(caplog) == []


# --- Row 27: first request outcome ----------------------------------------


def test_401_then_200_logs_one_record_in_total(caplog):
    caplog.set_level(logging.WARNING)
    client = _client("bearer")
    assert client.post("/skills/add", json={"a": 3, "b": 4}).status_code == 401
    right = {"Authorization": "Bearer t0k"}
    assert client.post("/skills/add", json={"a": 3, "b": 4}, headers=right).status_code == 200
    assert [r.getMessage() for r in _serve_records(caplog)] == [LOG_INVOKE]


def test_a_first_request_that_fails_with_500_or_405_still_logs(caplog):
    caplog.set_level(logging.WARNING)
    assert _client().post("/skills/boom", json={"x": 1}).status_code == 500
    assert [r.getMessage() for r in _serve_records(caplog)] == [LOG_INVOKE]

    caplog.clear()
    assert _client().get("/skills/add").status_code == 405
    assert [r.getMessage() for r in _serve_records(caplog)] == [LOG_INVOKE]

    caplog.clear()
    assert _client().head("/skills").status_code == 405
    assert [r.getMessage() for r in _serve_records(caplog)] == [LOG_DASHBOARD]

    caplog.clear()
    assert _client().options("/skills/add").status_code == 405
    assert [r.getMessage() for r in _serve_records(caplog)] == [LOG_INVOKE]


def test_a_404_from_a_disabled_group_logs_nothing(caplog):
    caplog.set_level(logging.WARNING)
    assert _client(dashboard=False).get("/skills").status_code == 404
    assert _client(introspection=False).get("/introspection/skills").status_code == 404
    assert _serve_records(caplog) == []


# --- Row 28: no secrets in the record -------------------------------------


def test_log_records_never_contain_the_credential_or_the_body(caplog):
    caplog.set_level(logging.DEBUG)
    client = _client("bearer")
    client.post(
        "/skills/add",
        json={"a": 1, "note": "MARKER-BODY-456"},
        headers={"Authorization": "Bearer WRONG-SECRET-123"},
    )
    records = _serve_records(caplog)
    assert [r.getMessage() for r in records] == [LOG_INVOKE]


# --- Row 29: per application ----------------------------------------------


def test_two_applications_each_log_once(caplog):
    caplog.set_level(logging.WARNING)
    first, second = _client(), _client()
    first.get("/skills")
    second.get("/skills")
    assert [r.getMessage() for r in _serve_records(caplog)] == [LOG_DASHBOARD, LOG_DASHBOARD]
    first.get("/skills")
    assert [r.getMessage() for r in _serve_records(caplog)] == [LOG_DASHBOARD, LOG_DASHBOARD]


# --- Row 30: concurrency ---------------------------------------------------


def test_fifty_concurrent_first_requests_log_exactly_once(caplog):
    caplog.set_level(logging.WARNING)
    app = serve(_registry(), settings=_settings())

    async def run() -> list[int]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await asyncio.gather(*[client.get("/skills") for _ in range(50)])
        return [r.status_code for r in responses]

    statuses = asyncio.run(run())
    assert statuses == [200] * 50
    assert [r.getMessage() for r in _serve_records(caplog)] == [LOG_DASHBOARD]


# --- Row 31: same work as the primary --------------------------------------


def test_alias_invoke_records_the_tool_source():
    client = _client()
    client.post("/skills/add", json={"a": 3, "b": 4})
    sessions = client.get("/introspection/sessions").json()
    assert sessions[-1]["source"] == "tool:add"


def test_alias_invoke_runs_no_hooks():
    calls: list[str] = []

    def echo(value: str) -> str:
        """Echo."""
        return value

    def pre(*args: Any, **kwargs: Any) -> None:
        calls.append("pre")

    def post(*args: Any, **kwargs: Any) -> None:
        calls.append("post")

    app = serve(Registry(tools=[tool(echo, pre_hook=pre, post_hook=post)]), settings=_settings())
    response = TestClient(app).post("/skills/echo", json={"value": "hi"})
    assert response.status_code == 200
    assert response.json() == {"result": "hi"}
    assert calls == []


def test_rollup_carries_the_same_list_under_both_keys():
    body = _client().get("/introspection").json()
    assert body["skills"] == SPECS
    assert body["tools"] == SPECS
    assert set(body) == {"tools", "skills", "sessions", "permissions", "queues", "dataflow"}


def _permissions() -> PermissionsSnapshot:
    return PermissionsSnapshot(
        auth_mode="none",
        dashboard_requires_auth=True,
        introspection_requires_auth=True,
        gated_routes=[],
    )


def test_snapshot_accepts_the_legacy_field_name():
    entry = ToolEntry(name="add", description="Add two numbers.", args_schema=ADD_SCHEMA)
    graph = DataflowGraph(nodes=[], edges=[])
    snapshot = IntrospectionSnapshot(
        skills=[entry], sessions=[], permissions=_permissions(), queues=[], dataflow=graph
    )
    assert snapshot.tools == snapshot.skills == [entry]

    loaded = IntrospectionSnapshot.model_validate(
        {
            "skills": [SPECS[0]],
            "sessions": [],
            "permissions": _permissions().model_dump(),
            "queues": [],
            "dataflow": {"nodes": [], "edges": []},
        }
    )
    assert loaded.tools == [entry]


def test_snapshot_built_with_tools_only_fills_the_legacy_list_with_the_same_entries():
    entry = ToolEntry(name="add", description="Add two numbers.", args_schema=ADD_SCHEMA)
    snapshot = IntrospectionSnapshot(
        tools=[entry],
        sessions=[],
        permissions=_permissions(),
        queues=[],
        dataflow=DataflowGraph(nodes=[], edges=[]),
    )

    dumped = snapshot.model_dump()
    assert dumped["skills"] == [SPECS[0]]
    assert dumped["tools"] == [SPECS[0]]
    assert set(dumped) == {"tools", "skills", "sessions", "permissions", "queues", "dataflow"}


def test_validating_a_v06_shaped_mapping_leaves_it_unchanged():
    payload = {
        "skills": [SPECS[0]],
        "sessions": [],
        "permissions": _permissions().model_dump(),
        "queues": [],
        "dataflow": {"nodes": [], "edges": []},
    }
    before = copy.deepcopy(payload)

    IntrospectionSnapshot.model_validate(payload)

    assert payload == before


def test_openapi_snapshot_schema_requires_both_lists():
    schema = _client().get("/openapi.json").json()["components"]["schemas"]["IntrospectionSnapshot"]

    assert "skills" in schema["required"]
    assert "tools" in schema["required"]


def test_snapshot_keeps_both_lists_as_given_when_they_differ():
    one = ToolEntry(name="one", description="", args_schema={})
    two = ToolEntry(name="two", description="", args_schema={})
    snapshot = IntrospectionSnapshot(
        tools=[one],
        skills=[two],
        sessions=[],
        permissions=_permissions(),
        queues=[],
        dataflow=DataflowGraph(nodes=[], edges=[]),
    )
    assert snapshot.tools == [one]
    assert snapshot.skills == [two]


# --- Row 32: gated routes ---------------------------------------------------

_INVOKE = ["/skills/add", "/skills/multiply", "/tools/add", "/tools/multiply"]
_DASHBOARD = ["/events", "/health", "/skills", "/tools"]
_INTROSPECTION = [
    "/introspection",
    "/introspection/dataflow",
    "/introspection/permissions",
    "/introspection/queues",
    "/introspection/sessions",
    "/introspection/skills",
    "/introspection/tools",
    "/introspection/workflows/{run_id}",
]


def _gated(mode: str, **kwargs: Any) -> list[str]:
    registry = Registry(tools=[_make("add"), _make("multiply")])
    app = serve(registry, settings=_settings(mode, **kwargs))
    headers = _headers(mode, "right") if mode != "none" else {}
    response = TestClient(app).get("/introspection/permissions", headers=headers)
    assert response.status_code == 200
    gated: list[str] = response.json()["gated_routes"]
    return gated


def _make(name: str):
    def fn(a: int, b: int) -> int:
        """Doc."""
        return a

    fn.__name__ = name
    return tool(fn)


def test_gated_routes_lists_the_alias_paths_beside_the_primaries():
    assert _gated("none") == []
    both = sorted(_INVOKE + _DASHBOARD + _INTROSPECTION)
    assert _gated("bearer") == both
    assert _gated("api-key") == both
    off = {"dashboard_requires_auth": False, "introspection_requires_auth": False}
    assert _gated("bearer", **off) == _INVOKE
    only_dash = {"dashboard_requires_auth": True, "introspection_requires_auth": False}
    assert _gated("bearer", **only_dash) == sorted(_INVOKE + _DASHBOARD)
    only_intro = {"dashboard_requires_auth": False, "introspection_requires_auth": True}
    assert _gated("bearer", **only_intro) == sorted(_INVOKE + _INTROSPECTION)
    assert _gated("bearer", dashboard=False) == sorted(_INVOKE + _INTROSPECTION)


def test_gated_routes_with_introspection_off_lists_the_invoke_and_dashboard_paths():
    from cantus.serve.introspection import collect_permissions

    settings = _settings("bearer", introspection=False)
    app = serve(Registry(tools=[_make("add"), _make("multiply")]), settings=settings)

    assert collect_permissions(app, settings).gated_routes == sorted(_INVOKE + _DASHBOARD)


# --- Row 13, legacy half ----------------------------------------------------


def test_a_tool_named_skills_collides_with_the_dashboard_path():
    class _Stub:
        name = "skills"

        def spec_for_llm(self) -> dict[str, Any]:
            return {"name": "skills", "description": "", "args_schema": {}}

        def run(self, **kwargs: Any) -> Any:
            return None

    registry = Registry()
    registry.register("tool", _Stub())
    with pytest.raises(ValueError) as exc:
        serve(registry)
    assert str(exc.value) == (
        "Tool name 'skills' collides with a reserved dashboard path (reserved dashboard path)"
    )


# --- Row 33: a plain FastAPI app --------------------------------------------


def test_alias_routes_work_on_an_app_not_built_by_serve(caplog):
    caplog.set_level(logging.WARNING)
    from cantus.serve.dashboard import register_dashboard_routes
    from cantus.serve.introspection import SessionTracker

    settings = _settings()
    app = FastAPI()
    app.state.settings = settings
    app.state.channels = []
    app.state.session_tracker = SessionTracker()
    register_introspection_routes(app, _registry(), settings)
    register_dashboard_routes(app, _registry(), settings)
    client = TestClient(app)

    introspection = client.get("/introspection/skills")
    assert introspection.status_code == 200
    assert introspection.json() == SPECS
    dashboard = client.get("/skills")
    assert dashboard.status_code == 200
    assert dashboard.json() == SPECS
    assert not _has_notice(introspection)
    assert not _has_notice(dashboard)
    assert _serve_records(caplog) == []
    paths = client.get("/openapi.json").json()["paths"]
    assert paths["/skills"]["get"]["deprecated"] is True
    assert paths["/introspection/skills"]["get"]["deprecated"] is True
    assert not paths["/tools"]["get"].get("deprecated")
    assert not paths["/introspection/tools"]["get"].get("deprecated")


def test_an_application_mounted_under_a_prefix_still_marks_and_logs_its_aliases(caplog):
    caplog.set_level(logging.WARNING)
    parent = FastAPI()
    parent.mount("/api", serve(_registry(), settings=_settings()))
    client = TestClient(parent)

    alias = client.get("/api/skills")
    primary = client.get("/api/tools")

    assert alias.status_code == 200
    assert alias.json() == SPECS
    _assert_notice(alias)
    assert not _has_notice(primary)
    assert [r.getMessage() for r in _serve_records(caplog)] == [LOG_DASHBOARD]
