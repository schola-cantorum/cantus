# Epic 0001 — vulnerability chain analysis

Close-out step 1 for epic 0001 (Tool rename, phase one), run on 2026-11-20 against `main` at `61ed932`
(tickets T-0006 to T-0020, PRs #57 to #71). The rule is in `docs/agents/review.md`, "Epic close-out:
chain analysis": take every finding of every grade from the epic's tickets and the trust boundaries,
and ask whether defects that are individually low-severity compose into a chain that crosses a trust
boundary. A chain that does opens a ticket before the epic is called done.

## Result

- **127 findings and candidates** were collected from the fifteen per-ticket reports
  (`security-T-0006.md` to `security-T-0020.md`) and the tickets' Comments; the count includes coverage
  limits and ticket notes that carry no grade. Five candidates were first graded medium (SEC-1,
  T0008-SEC-01, SEC-T0014-1, SEC-T0017-1, SEC-T0018-3) and the rest low; after the false-positive
  check none was confirmed as a security defect of the diff it was raised on.
- **13 chains were proposed** from three lenses (network client, model and in-process code, supply
  chain and documentation). Each was then handed to a separate agent whose task was to break it.
- **3 hold and cross a trust boundary** (C1, C2, C5 below). All three exist in v0.6.0; epic 0001
  neither introduced them nor made the code worse. Two are P1, one is P2.
- **2 hold at P2 without crossing a boundary** (M1, M2). **8 are not chains**; their carry-over
  notes are in the table below.
- No chain that crosses a boundary was introduced by the Tool rename. M1 was introduced by it, does
  not cross a boundary, and rests on a precondition nobody has shown to exist.

Under `review.md` the three crossing chains need tickets before the epic is called done. Opening them
is the user's decision; the proposals are under "Tickets this analysis asks for".

## Method and limits

- Inputs: the fifteen security reports, each ticket's Comments, `review/round-1.md` and `round-2.md`,
  the spec, and the code on `main`. The spec names no trust boundaries of its own, so the ten below
  were derived from the code and the spec's behaviour sections for this analysis.
- One workflow of 22 agents, 20 of them for this analysis: three collected findings and re-read each
  cited line on `main`; one described the boundaries; three proposed chains; thirteen each tried to
  break one chain. The other two gathered the acceptance evidence and the retrospective inputs. A
  second workflow of three reviewers then checked this document; its corrections are applied.
- Grades: `review.md` defines no scale for chains. P1 and P2 here borrow the spec-review scale only
  to express severity. Whether a ticket is required follows from crossing a boundary, not from the
  grade, so a P2 chain that crosses one (C5) still needs a ticket.
- Server-side links of C1, C2 and C5 were reproduced in process with FastAPI's `TestClient`. No real
  browser, tunnel or second machine was used: the browser leg of C2 and the network reach of C1 are
  inferred from how browsers and tunnels work.
- Channel webhook routes were read, not run: each verifies its platform's signature and answers 401
  on failure (LINE `cantus/serve/channels/line.py:70-73`, Telegram `telegram.py:91-95`, Discord
  `discord.py:239-268`), and each is registered without the auth dependency (`line.py:86`,
  `telegram.py:108`, `discord.py:286`). So `auth_mode` does not apply to a webhook, and turning bearer
  auth on does not block the platform's calls.
- "Pre-existing" means the same code shape is in the `v0.6.0` tag.

## Trust boundaries

| Boundary | Known gaps on `main` |
|---|---|
| B1. Network client -> cantus serve (HTTP) | (1) Auth none is the default, so out of the box every tool body is callable by anyone who can reach the port (config.py:76); the CLI warning does not look at the host, so --host 0.0.0.0 gets no extra warning (cli.py:307-313). (2) POST /tools/{name} calls tool_instance.run(**body) directly: no validate_args, no pre_hook/post_hook (app.py:245-249; spec.en.md:150 says this is intended, as in v0.6). Observed: {"a":"x","b":"y"} to an int tool returned 200 {"result":"xy"}; the pre_hook was never called. A permission or self-check gate placed in a hook or in _dispatch_tool is therefore bypassed over HTTP (round-2 R2-5; documented in MIGRATION V6, docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md:2105-2109, and X8 :1467-1478). (3) /docs, /redoc and /openapi.json are created by FastAPI with no auth dependency (app.py:137-143; config.py:71-73): observed 200 without credentials in bearer mode, so tool names, descriptions and argument schemas are readable unauthenticated. Not raised in round 1/2 or the per-ticket security reports I read; pre-existing (inferred: these settings predate the epic). (4) Extra keys, a non-object body (silently replaced by {}, app.py:246-247) or malformed JSON give 500 rather than 4xx (observed); request.json() runs after tracker.start and outside the try, so a malformed body leaves a session record never finished (app.py:244-245; inferred from code). (5) No rate limit or body-size limit in cantus (none found in cantus/serve). (6) Channel webhook routes rely on their own signature checks and were not re-read in this pass (only confirmed that channels do not touch the registry: grep of cantus/serve/channels found no Registry/Tool use beyond a docstring in googlechat.py:193). |
| B2. Legacy client -> alias routes (/skills/{name}, /skills, /introspection/skills) | (1) The surface is doubled during the alias window: a proxy/WAF rule written only for /skills leaves /tools open after upgrade, and a rule written only for /tools leaves /skills open; the only control is documentation (X11). (2) An unauthenticated request (401/405) consumes the once-per-template log record, so the operator signal can be spent by a stranger; accepted as reading D3 (security-T-0012.md:21). (3) The Link header and warning text point at the tag v0.7.0, which does not exist until release (_deprecation.py:10-13; spec.en.md:271-273). (4) A response produced before routing by host middleware is not marked (_aliases.py:8). |
| B3. Model output -> parser / dispatcher | (1) No permission seam: any registered tool the model names is run; OQ-008 is open (.proj.specs/OPEN-QUESTIONS.md:307). (2) Prompt injection path is open by design: tool results and the raw-output preview are fed back as repr(event) in the next prompt (agent.py:317-325, 466-473), and the unknown-tool feedback embeds the model-controlled name (agent.py:438; noted as pre-existing in security-T-0010.md:24). (3) With an empty registry any name parses (agent.py:432) and fails only at dispatch. (4) Under an error filter W13 is swallowed without a trace, so legacy-key output is undetectable there (approved reading D10, security-T-0010.md:21). (5) No grammar-constrained decoding is wired in, and the default prompt never states the action shape (spec.en.md:286-291; OQ-015), so this boundary rests entirely on the runtime parser. |
| B4. Student or third-party code -> global registry / Agent tool set | (1) Fail-open fallback: Agent(model) built while the global registry is empty holds that same object and silently gains any tool a library registers later; W11 is emitted only at construction (agent.py:98-101; AC-11, spec.en.md:84; round-2 R2-4 not adopted; security-T-0008.md:20 accepted as specified). tools=[] is the only way to state 'no tools'. (2) Registry.register replaces by name with no warning and no type check beyond a name attribute (registry.py:157-175), and a Registry passed to Agent is shared by reference, so later register_tool on it can replace a hooked tool (security-T-0017.md:24, R2-15 family). (3) The dispatch guard does not see a method assigned after class creation, an instance attribute, or a subclass below an intermediate __init_subclass__ that skips super() (OQ-013, OPEN-QUESTIONS.md:494-499). (4) The half-migration @tool + Agent(model) gives zero tools and no warning (spec.en.md:295-297). (5) The grammar helpers still fall back to the global registry when registry is omitted (grammar/tool_call.py:76, W12). |
| B5. Tool arguments -> tool body (three entry paths) | (1) Tool.run / __call__ and the HTTP endpoint do not validate or run hooks (tool.py:82-87; app.py:249); documented as V6 and in ludus-migration.md:26. So the same tool has different guarantees per entry path. (2) Remote adapter tools trust the remote schema: validate_args only checks that args is a dict (adapters/_remote_tool.py:58-63), so model-supplied arguments reach the remote framework unvalidated. (3) pydantic validation is type coercion, not authorization: no path/command allow-listing exists in cantus; that is left to the tool body. (4) hooks are developer-set and not checked for callability at construction (security-T-0006.md:24, accepted). |
| B6. Remote frameworks / MCP servers -> cantus (adapters) | (1) The MCP adapters do not work against MCP SDK 1.x; behaviour is deferred to epic 2 (spec.en.md:226-227, 266), so the controls above are untested against a real server. (2) Remote descriptions enter the prompt verbatim (prompt-injection vector) and nothing consumes is_remote to gate or label them (inferred: no reader of is_remote found in agent.py). (3) A re-exported remote tool loses is_remote (security-T-0011.md:20). (4) Remote tool names are not constrained before they become a registry key or, if served, a URL path segment /tools/{name} (app.py:277; inferred, not exercised). (5) export_as_mcp_server exposes tool bodies without hooks or validate_args, same as B5 (security-T-0017.md:25). |
| B7. Documentation / notebooks / scripts -> student machine | (1) quickstart-desktop teaches cantus serve --host 0.0.0.0 with no --auth-mode (docs/site/quickstart-desktop.md:78; same in zh-tw and docs/quickstart-desktop.md:72); flagged as SEC-T0020-6, not changed, a follow-up docs ticket was suggested (security-T-0020.md:23). (2) The channel cookbooks start cantus serve without --auth-mode and then tunnel the whole port publicly (docs/site/channels/line.md:55-59, 69; telegram.md:61; discord.md:72), which publishes every /tools/{name} and /skills/{name} route unauthenticated and hook-free on the internet; flagged as SEC-T0018-5, not changed (security-T-0018.md:18). No ticket for either was found in this pass (inferred; tickets not searched). (3) Docs on main lead the published package: channel pages require cantus-agent[serve]>=0.7.0, which is not on PyPI (line.md:8; spec.en.md:271-273), and the notebook tells students to switch cantus_version to a moving ref to get the new API (task_template.ipynb:69, 76; README.md:46; security-T-0020.md:21). (4) scripts/smoke_install.sh installs with uv pip install --system into the user's system interpreter and, from the repo root, python -c imports the source tree rather than the installed package (scripts/smoke_install.sh:30-39, 33; security-T-0020.md:25). |
| B8. CI / PR author -> repository credentials and PyPI release | (1) cross-platform-install.yml, docs.yml, repo-hygiene.yml and supply-chain.yml check out without persist-credentials: false while running PR-controlled code (cross-platform-install.yml:27, 39; docs.yml:18, 24; repo-hygiene.yml:18, 31; supply-chain.yml:66, 84); the token is read-only, so impact is low; accepted as SEC-T0020-3 with a suggested maintenance ticket (security-T-0020.md:20). (2) Actions are pinned to mutable tags, including pypa/gh-action-pypi-publish@release/v1 in the job that holds id-token: write (release.yml:47, 51) and actions/checkout@v6, setup-python@v6, setup-uv@v8.1.0. (3) workflow_dispatch with target pypi publishes from whatever ref is dispatched (release.yml:6-15, 46); whether the pypi environment has required reviewers or branch rules is a GitHub setting not visible in the repository (inferred unknown). (4) CI installs unpinned dependencies (security-T-0006.md:21). (5) v0.7.0 is unreleased and the package still reports 0.6.0, so installs from main cannot be told apart by version (MIGRATION V5, :2098-2103). |
| B9. Pickled / persisted events -> cantus process | (1) A v0.6 pickle still loads through the legacy module __getattr__ (W4/W5) into half-formed objects: CallToolAction with tool_name silently '', ToolObservation / ToolErrorObservation raising AttributeError on .tool_name or repr (MIGRATION:1583-1588; round-1 R-23) - a robustness and integrity gap, not code execution added by cantus. (2) Any user code that unpickles event files from an untrusted source has the usual pickle code-execution risk; cantus neither does this nor warns about it beyond X10. (3) GET /events returns whatever dicts the persistence file holds, including argument and result values if the host wrote them, and with auth none it is open (dashboard.py:122-152; inferred from code, no persistence is attached by default). |
| B10. Deprecation machinery -> process-global warning state | (1) Under -W error or pytest filterwarnings=error every legacy use except W13 raises, including inside cantus serve start-up paths (MIGRATION V9, :2086-2091; security-T-0007.md:22). (2) A first import inside warnings.catch_warnings() loses the filter (spec.en.md:201-202; MIGRATION V2). (3) _insert_locked relies on CPython-private names (_deprecation.py:196-222). (4) Silencing the whole category hides nothing security-relevant from serve (the open-introspection notice is a UserWarning, app.py:199-206), but a blanket -W ignore would hide that UserWarning too (security-T-0019.md:16). (the blanket-ignore remark is this analysis's inference, not in the cited report) |

## Chains that cross a trust boundary

### C1 — Documented exposure, no auth, and a tool body any reachable client can run (P1, pre-existing)

1. `cantus serve` defaults to `auth_mode` none (`cantus/config.py:76`); in that mode the tool,
   dashboard and introspection routes carry no auth dependency (`cantus/serve/app.py:153-156`,
   `:173-176`, `:207-210`).
2. The CLI's only warning is for auth none together with the dashboard; it never looks at the host
   (`cantus/cli.py:307-313`), so a non-loopback bind gets no warning of its own and is not refused.
3. The quickstart teaches `cantus serve --host 0.0.0.0` with no `--auth-mode`
   (`docs/site/quickstart-desktop.md:78`, the zh-tw page, `docs/quickstart-desktop.md:72`). Its
   tunnel section does carry a security note that the quick tunnel is unauthenticated and should be
   paired with `--auth-mode bearer` (`docs/site/quickstart-desktop.md:93`), but the note sits fifteen
   lines below the `0.0.0.0` command and speaks only of the tunnel. The LINE, Telegram and Discord
   cookbooks bind `127.0.0.1` and then tunnel the port (`docs/site/channels/line.md:55-59`, `:69`
   and siblings); their commands have no `--auth-mode` and they point back to the quickstart's tunnel
   section instead of repeating its note.
4. `POST /tools/{name}` and its alias call `tool_instance.run(**body)` (`cantus/serve/app.py:249`):
   neither `validate_args` nor a hook runs, which the spec states is intended, as in v0.6.

Boundary crossed: network client to `cantus serve` (B1), then tool arguments to tool body (B5).
Attacker: anyone on the same network after a `0.0.0.0` bind, or anyone who learns the tunnel URL.
Impact: every registered tool body runs with attacker-chosen, unvalidated arguments; a check a
student wrote as a `pre_hook` is skipped. The crossing does not depend on link 4: an unauthenticated
call of the body is already across B1; link 4 makes it worse. The project has recorded that hooks are
not access control (`security-T-0020.md:22`, the guide's V6).

Epic 0001: unchanged in code. It added the written warnings (V6, X11) and recorded the quickstart line
as SEC-T0020-6; the follow-up ticket T-0020 promised is not open yet.

### C2 — A web page the user visits can run tools on the default loopback server (P1, pre-existing)

1. Defaults: host `127.0.0.1`, auth none (`cantus/config.py:59`, `:76`).
2. The tool endpoint reads the body with `await request.json()` and never looks at `Content-Type`
   (`cantus/serve/app.py:245`), nor at `Origin` or `Host`; the app installs no CORS, trusted-host or
   CSRF control.
3. Reproduced on `main`: `POST /tools/add` with `Content-Type: text/plain`,
   `Origin: https://evil.example` and `Host: attacker.example:8765` returns 200 `{"result":3}` and the
   tool body runs. A CORS preflight returns 405, so a request that needs one is stopped by the browser.
4. Inferred, not run in a browser: a `text/plain` POST is a "simple request" that a browser sends
   cross-site without a preflight. The page cannot read the response, but the tool body has run.
   With DNS rebinding the page could also read responses, since `Host` is not checked.

Boundary crossed: a third-party web origin to the user's local server (B1), then B5 as in C1.
Attacker: a web page open in a browser on the machine that runs `cantus serve`, with the server in
its default, documented configuration, in a browser that lets a public page send requests to
loopback. Browser-side controls on such requests (for example a local-network permission prompt)
differ between browsers and were not checked. The P1 grade assumes link 4 holds; one run in a real
browser would settle it and is worth doing before the runtime ticket is specified.
Impact: blind invocation of any registered tool with chosen arguments. For the calculator tools of
the tutorials this is harmless; for a student's file, shell or channel-sending tool it is not.

Epic 0001: unchanged; it only added a second path per tool. This chain was not raised in the two
adversarial rounds or in any of the fifteen reports; it is new in this analysis.

### C5 — With bearer auth on, the tool catalogue is still public (P2, pre-existing)

1. `/docs`, `/openapi.json` and `/redoc` are created by FastAPI from settings, outside the per-route
   auth dependencies (`cantus/serve/app.py:137-143`; defaults at `cantus/config.py:71-73`).
2. Reproduced on `main`: in bearer mode, without a token, the tool routes return 401 and
   `/openapi.json` returns 200 with every tool's name, description and argument schema.
3. The three URLs can be switched off: the serve page says to set them to `None`
   (`docs/site/protocols/serve.md:56-58`), and an empty environment variable does the same (checked:
   404). The page does not show the environment form, the quickstart's security note says bearer auth
   protects `/introspection` and `/tools` without mentioning these routes, and nothing tells an
   operator who turns auth on that they stay public.

Boundary crossed: unauthenticated client to the authenticated server (B1). Impact: disclosure of the
tool inventory and schemas, no invocation. It is one defect, not a composition, but it crosses the
boundary by itself, so it needs a ticket although it is P2, and it combines with C1's tunnel
instructions.

Epic 0001: unchanged, apart from doubling the listed operations with the alias routes.

## Chains that hold without crossing a boundary

### M1 — A dispatch override assigned under the old name is skipped silently (P2, introduced by the epic)

The rename of `Agent._dispatch_skill` to `_dispatch_tool` has no shim (X8). T-0009's guard is
`Agent.__init_subclass__` (`cantus/core/agent.py:136-155`): it catches a subclass that defines the old
method, not a method assigned to the class or instance afterwards, and the loop calls only
`_dispatch_tool` (`agent.py:282`). An override that carried a student's permission check would then
never run. The verifier lowered it from P1: no v0.6 code is known to assign the method, the v0.6 docs
never taught it, and the gap is already OQ-013. Smallest hardening, if wanted: one `hasattr` check at
the top of `Agent.run`.

### M2 — A fallback agent silently gains tools a library registers later (P2, pre-existing, narrowed)

`Agent(model)` built while the global registry is empty keeps that live registry and warns (W11) only
if it is non-empty at construction (`cantus/core/agent.py:97-104`). A later `register_skill()` from any
imported module adds a tool the model can call, with only W3 at the registration site. Reproduced in
memory. It does not cross a boundary: registering needs code already running in the process, and the
model can only pick names that exist. Same family as R2-4, T0008-SEC-01 and SEC-T0019-3; changing it
means changing AC-11, which is for a later epic to decide.

## Proposed chains that are not chains

| Proposal | Why it fails | Carry-over |
|---|---|---|
| C3 — a proxy rule that covers one route family leaves the other open | The "control" is a rule cantus neither ships nor documents as a control; both families are identical by design and documented (X11) | Optional: one sentence on the serve page |
| C4 — an unauthenticated client spoils the operator's session view and spends the once-only log line | The parts do not depend on each other; the bounded history evicts by design and stale records age out | Hardening, runtime: parse the body before `tracker.start`, and answer 400 rather than 500 for a body that is not JSON (`cantus/serve/app.py:244-248`) |
| Both action keys in one model reply | The filter said to be bypassed is hypothetical; every control cantus owns acts on the parsed name; documented as A5 | Optional: emit W13 when both keys are present and differ |
| A remote tool's description steers the model to a hookless tool | Unreachable on `main`: the MCP adapters do not work against MCP SDK 1.x | Input for the async-core epic's spec, which makes the MCP path live |
| The wrong PyPI name `cantus` reached through runtime hints and documents | The documents do not lead to the hint; the hint appears only when an optional SDK is missing | Already OQ-012 |
| Documents lead the release, so students install from `main` | `@main` is the same trusted repository as the tag; a release-hygiene matter | The v0.7.0 release step |
| The release job builds with an unpinned toolchain inside the job that holds the PyPI identity | No finding of this epic is a link, and the exploitable step is unconfirmed | Optional P2 hardening: split build and publish jobs |
| The artefact that reaches PyPI is not the thing the gate tests | Not a boundary of this epic's spec; the facts hold | The install-smoke ticket T-0020 promised, before v0.7.0 |

## Tickets this analysis asks for

`review.md` requires a ticket for each crossing chain before the epic is called done. Proposed, for the
user to open or decline:

1. **Documentation, lightweight path (C1, C5).** Quickstart pages: bind `127.0.0.1`, or keep
   `0.0.0.0` only together with `--auth-mode bearer`, and move or repeat the existing tunnel security
   note beside the commands it concerns. Channel pages: repeat that note at the tunnel step and add
   `--auth-mode bearer` to the command; bearer auth does not affect the `/channels/*` webhooks. Serve
   page and security note: say that `/docs`, `/openapi.json` and `/redoc` stay public under auth and
   show how to switch them off through settings and through the environment. This is the ticket
   T-0020 promised for SEC-T0020-6, widened by the channel pages and C5.
2. **Runtime, needs a spec (C2).** Refuse cross-site browser requests on the tool routes (an `Origin`
   check, and a `Host` check for the loopback default); optionally require `application/json`. It
   changes HTTP behaviour, so it is contract surface: full pipeline, CHANGELOG, migration note. An
   open question does not satisfy `review.md` here: C2 needs a ticket, which may be `status: pending`
   in the epic that will carry it, or the user records an explicit exception.
3. **Open questions to record with ticket 1.** Whether `cantus serve` warns or refuses on a non-loopback
   host with auth none; whether the three documentation routes come under auth when auth is on; whether
   HTTP dispatch runs `validate_args` and hooks (R2-5 family, beside OQ-010).

Until the user decides, the epic is not called done.

## Finding inventory

Every finding and candidate read for this analysis. The text of each is in the per-ticket report named
by its ticket; "on main" is the collecting agent's re-read of the cited line at `61ed932`.

Families, by count: deprecation-signal 15, docs-example 12, dual-route-rules 10, test-hygiene 9, ci-credentials 7, model-output-key 7, registry-fallback 6, untested-surface 5, http-skips-hooks 4, serve-no-auth 4, supply-chain 3, frame-check 3, log-injection 3, availability 3, registry-replace-drops-hook 2, hook-gating-gap 2, remote-tool-name 2, route-misidentification 2, install-smoke 2, shared-registry 2, type-gate-rebind 1, error-message-exposure 1, validation-bypass 1, dos-local 1, dispatch-override-skip 1, string-match-migration 1, pickle 1, introspection-redaction 1, provenance-loss 1, input-validation 1, information-disclosure 1, alias-auth-parity 1, middleware-composition 1, tool-name-path-syntax 1, stale-session-state 1, tui-markup-injection 1, tui-malformed-snapshot 1, debug-prints-args 1, http-skips-hooks / serve-no-auth 1, model-output-key / remote-tool-prompt-injection 1, registry-fallback / shared-registry 1, serve-no-auth / http-skips-hooks 1, memory-untrusted 1, http-skips-hooks / install-smoke 1.

| Id | Ticket | Family | Grade and disposition | On main |
|---|---|---|---|---|
| SEC-1 | T-0006 | ci-credentials | candidate medium/medium; filter: not a defect (0.1); not a defect; taken as hardening (ADR rule added) | no (mitigated): :23-24 still ask for headers/auth settings, but :56-58 require `<redacted>` header values, mode-only auth settings and a throwaway token |
| SEC-2 | T-0006 | ci-credentials | candidate low/low; filter: not a defect (0.15); not a defect; covered by the same ADR rule | partly: :22 unchanged; the general rule at :56-58 ('Evidence never carries a credential') applies, but notebook cells are not named explicitly (inferred coverage) |
| SEC-3 | T-0006 | supply-chain | candidate low/low; filter: not a defect (0.08); not a defect; not handled (CI does not pin either) | yes: no lock/constraints/freeze wording in ADR-0018 (grep), and test.yml:38,67 still `pip install -e ".[dev,...]"` |
| SEC-4 | T-0006 | registry-replace-drops-hook | candidate low/low; filter: not a defect (0.85); not a defect (AC-04, pre-existing in v0.6); teaching side recorded for T-0017 (R2-15) | yes: registry.py:175 `self._by_kind[kind][name] = instance` with no warning; tool.py:218 documents the replacement |
| SEC-5 | T-0006 | hook-gating-gap | candidate low/medium; filter: not a defect (0.08); not a defect (pre-existing limit); AutoMemory docstring fixed by T-0014 (R2-7) | partly: _remote_tool.py:48-49 still set hooks to None, memory_auto.py:25 `__init__(self, backend)` takes no hook, tool.py:193-196 message unchanged; the docstring at memory_auto.py:144-162 now shows the working wrapper pattern |
| SEC-6 | T-0006 | hook-gating-gap | candidate low/low; filter: not a defect (0.95); not a defect; not handled (hooks are set by the developer) | yes: `_to_tool` (tool.py:185-206) has no callable check on hooks; post_hook is called after the body at agent.py:528-538 |
| SEC-7 | T-0006 | type-gate-rebind | candidate low/low; filter: not a defect (0.93); not a defect (compatibility change); recorded for T-0015/T-0019 | yes: huggingface.py:40 `from smolagents import Tool as SmolagentsTool`, :49 imports cantus Tool; documented in docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md:1834 (I7) |
| T0007-SEC-01 | T-0007 | deprecation-signal | candidate low/0.7; filter: not a security defect (0.85), correctness defect real; fixed (stage-6/7 fix on the T-0007 branch; commit not identified here) | no: :149-152 `try: number = int(lineno) except (ValueError, OverflowError): return False` |
| T0007-SEC-02 | T-0007 | deprecation-signal | candidate low/0.5; filter: not a security defect (0.85), semantic gap real; fixed (same change as SEC-01; test row 44 gained `::+0`) | no: lineno is parsed with `int()` and only non-zero values are treated as scoped (:149-154) |
| T0007-SEC-03 | T-0007 | deprecation-signal | candidate low/0.45; filter: not a defect (0.9); recorded (ticket Comments for T-0012 and T-0019); not changed | yes: cli.py:185 catches only `ImportError`; app.py:250-259 re-raises any tool exception; documented in the migration guide at :1985 (A2) |
| T0007-SEC-04 | T-0007 | deprecation-signal | candidate low/0.25; filter: not a defect (0.9); fixed for the file-name substring match; the `cantus.` prefix rule is spec 2.4 and stays | partly: import machinery is now matched by exact module name (:225-232, :240); a third-party module named `cantus.<x>` is still skipped (:238) |
| T0007-SEC-05 | T-0007 | deprecation-signal | candidate low/0.2; filter: not a defect (0.9); not a defect; taken as hardening (insert under `warnings._lock`) | hardened: :198-199,218-220 take `warnings._lock` when it exists; free-threaded and context-aware behaviour remains unverified per the ticket's coverage table |
| T0007-SEC-06 | T-0007 | model-output-key | candidate low/0.15; filter: not a defect (0.93); not a defect (AC-22 by design); trace question passed to T-0010, decided there as D10 (no trace) | yes: `except CantusDeprecationWarning: if w_id != "W13": raise` at :105-109, and W13 is now reachable from model output via tool_call.py:52-53 |
| T0007-SEC-07 | T-0007 | deprecation-signal | candidate low/0.1; filter: not a defect (0.95); not a defect; not handled | yes: unchanged loop at _deprecation.py:245-249 |
| T0007-SEC-08 | T-0007 | ci-credentials | candidate low/0.2; filter: not a defect (0.9); not a defect; taken as hardening (`--host 127.0.0.1`, drop `CANTUS_SERVE_*`) | mostly no: test_warning_visibility.py:370 drops `CANTUS_SERVE_*` and :381 passes `--host`; residue: `run_python` still says 'clean environment' while removing only three variables (support.py:137-142) and `_free_port` bind-then-release remains (:348) |
| T0008-SEC-01 | T-0008 | registry-fallback | candidate medium/0.5; filter: not a defect (0.85); not a defect (AC-11, v0.6 fallback kept for the alias period) | yes: agent.py:98-101 `value = _get_global_registry(); if value.names_for("tool"): warn_legacy("W11")`; documented in the migration guide at :411 and :854-857 |
| T0008-SEC-02 | T-0008 | registry-fallback | candidate low/0.8; filter: not a security defect (0.9), correctness defect real (stage-6 SPEC-01); fixed (identity check added) | no: `_both_keywords_allowed` now also requires `tools is original.tools` (agent.py:119-120) |
| T0008-SEC-03 | T-0008 | frame-check | candidate low/0.25; filter: not a defect (0.93); not a defect (misuse guard, not an authorization boundary) | yes, narrowed: frame-name check remains at :117 but is now combined with the identity check at :119-120; known limit stated in the docstring :114-115 |
| T0008-SEC-04 | T-0008 | error-message-exposure | candidate low/0.6; filter: not a security defect (0.85); not a defect; taken as hardening (no `repr()` of elements) | no: :123-134 use `__name__` only when it is an identifier, otherwise `type(item).__name__` |
| T0008-SEC-05 | T-0008 | remote-tool-name | candidate low/0.35; filter: not a defect (0.85); not a defect; taken as hardening (empty-name ValueError) | partly: empty names are now rejected (:136-140); neither `Registry(tools=)` nor `register` (:170-172) requires `name` to be a `str`, and `item.name` is still read more than once (:136,:144,:155) |
| T0008-SEC-06 | T-0008 | registry-replace-drops-hook | candidate low/0.4; filter: not a defect (0.9); not a defect (AC-09/TR-35 and AC-04 by spec) | yes: getter/setter at agent.py:193-210 return and accept the live Registry; a passed Registry is kept as-is (:102-104) |
| T0008-SEC-07 | T-0008 | validation-bypass | candidate low/0.3; filter: not a defect (0.9); not a defect; taken as hardening (slot renamed, AttributeError) | no: slot is `_cantus_tools` (:87) and an unset slot raises `AttributeError` (:92-95) |
| T0008-SEC-08 | T-0008 | dos-local | candidate low/0.2; filter: not a defect (0.95); not a defect; taken as hardening (validate while iterating) | hardened: elements are validated in the loop at :113-141 so the first invalid one fails; an infinite iterable of valid Tools still hangs (author-supplied input) |
| T0008-SEC-09 | T-0008 | remote-tool-name | candidate low/0.25; filter: not a defect (0.9); not a defect (near-name shadowing pre-existing; exact duplicates fail closed) | yes: `if name in seen` exact match at :145, no normalization |
| SEC-T0009-01 | T-0009 | frame-check | candidate low/0.75; filter: not a security defect (0.9), logic gap real; recorded (docstring and ticket); not changed | yes: identity test at :38; the limit is written in the docstring at :30-31 and in the migration guide A5 (:2013) |
| SEC-T0009-02 | T-0009 | dispatch-override-skip | candidate low/0.6; filter: not a security defect (0.8), mechanism real; recorded (ticket readings and OQ-013, open, for the async-core epic) | yes: guard is `hasattr(cls, "_dispatch_skill")` at class-creation time only (agent.py:145-146); OQ-013 status open at OPEN-QUESTIONS.md:485 |
| SEC-T0009-03 | T-0009 | string-match-migration | candidate low/0.35; filter: not a defect (0.85); recorded for T-0019 (X1 upgrade note) | yes: `type=type(event).__name__` at introspection.py:395 (now yields the new names) |
| SEC-T0009-04 | T-0009 | deprecation-signal | candidate low/0.55; filter: not a security defect (0.9); recorded for T-0019 | yes: property getter calls `warn_legacy("W7")` at :69; documented in the migration guide at :2019 (A5) |
| SEC-T0009-05 | T-0009 | pickle | candidate low/0.5; filter: not a security defect (0.9); recorded (X10, measured in the ticket) | yes: aliases at action.py:49-54 and observation.py:86-91; `grep -rnE 'pickle\|marshal\|shelve' cantus` returns nothing; guide section X10 at :1580 |
| SEC-T0009-06 | T-0009 | frame-check | candidate low/0.4; filter: not a defect (0.95); not a defect | yes: `caller.f_globals.get("__name__") != "dataclasses"` at :35 |
| SEC-T0010-01 | T-0010 | model-output-key | candidate low/0.35; filter: not a defect (0.88); not a defect (TR-83); recorded for T-0019 | yes: tool_call.py:50-54 |
| SEC-T0010-02 | T-0010 | model-output-key | candidate low/0.3; filter: not a defect (0.9); not a defect (TR-85; D10 approved: no trace); recorded for T-0019 | yes: see _deprecation.py:105-109; stated in the migration guide at :557 |
| SEC-T0010-03 | T-0010 | model-output-key | candidate low/0.3; filter: not a security defect (0.9); not a defect | yes: `warn_legacy("W13")` on each legacy-key action at tool_call.py:53 |
| SEC-T0010-04 | T-0010 | registry-fallback | candidate low/0.25; filter: not a defect (0.95); not a defect (AC-19/AC-22: only W13 is exempt) | yes: fallback at :76-79; no call site inside `cantus/` omits `registry` (grep finds only the two definitions' own `_resolve_registry` calls; `Agent` does not call either function) |
| SEC-T0010-05 | T-0010 | model-output-key | candidate low/0.2; filter: not introduced by this change (0.9); not a defect (v0.6 wording kept by D7) | yes: tool_call.py:190 `f"tool_name '{tool_name}' not registered; "`, agent.py:438 `{tool_name!r}` |
| T0006-CHK-http-no-hooks | T-0006 | http-skips-hooks | not graded (listed under 'checked, nothing found' as known behaviour R2-5); recorded (pre-existing; owner T-0012) | yes: app.py:249 `result: Any = tool_instance.run(**body)`; hooks are applied only in agent.py:503-538 |
| T0006-CHK-legacy-global-registration | T-0006 | registry-fallback | not graded (checked, nothing found); recorded | yes: skill.py:90 `_get_global_registry().register("tool", instance)`; the `register_skill(SomeToolSubclass)` detail in the report was not re-read on main (unknown) |
| T0007-CHK-introspection-redaction | T-0007 | introspection-redaction | not graded (checked, nothing found); recorded | yes: app.py:257 stores `message=str(exc)`; introspection.py:379-382 returns only `ToolErrorObservation tool=<name>` |
| T0007-TKT-warning-visibility-limits | T-0007 | deprecation-signal | not graded (ticket note only); recorded for T-0019 | unknown (behavioural claims not re-run); the insertion logic they describe is unchanged in shape at cantus/_deprecation.py:115-129,174-193 |
| T0008-TKT-known-limits | T-0008 | deprecation-signal | not graded (ticket known limits); recorded (known limit, characterization tests) | yes for the first (docstring at agent.py:114-115); attribution claims not re-run (inferred from the unchanged frame rule at cantus/_deprecation.py:235-249) |
| T0009-TKT-dataclass-subclass-keyword | T-0009 | deprecation-signal | not graded (ticket known limit, accepted by the user); recorded for T-0019 | inferred yes: the wrapper is installed on the decorated class's own `__init__` only (_legacy_events.py:49,79); not executed |
| T0010-TKT-empty-registry-accepts-any-name | T-0010 | model-output-key | not graded (approved reading); recorded (v0.6 behaviour kept) | yes: `if registered and tool_name not in registered` at agent.py:432 and the same shape at tool_call.py:188; lookup miss handled at agent.py:483-489 |
| SEC-T0011-1 | T-0011 | provenance-loss | low / 0.25 (filtered: not valid, 0.9); not a defect; recorded for close-out chain analysis (same class as R2-15) | yes - _arguments.py:36 checks only isinstance(tool, Tool); grep is_remote in cantus/ returns tool.py:65, _remote_tool.py:31 and docstrings |
| SEC-T0011-2 | T-0011 | input-validation | low / 0.3 (filtered: not valid, 0.93); not a defect (user-approved reading C2-F18-d); pre-existing in v0.6 | yes - mcp_server.py:110-111 assign name/version as given; _checked_iterable (48-62) allows empty |
| SEC-T0011-3 | T-0011 | log-injection | low / 0.1 (filtered: not valid, 0.97); not a defect | yes - _arguments.py:27 and :37, mcp_server.py:54, :60, :75 |
| SEC-T0011-4 | T-0011 | availability | low / 0.1 (filtered: not valid, 0.95); not a defect; pre-existing | yes - mcp_server.py:51 |
| T0011-LIMIT-MCP-SDK | T-0011 | untested-surface | coverage limit (ungraded); recorded; deferred to epic 2 (ticket line 71) | yes - mcp.py:68 server.tool(, mcp.py:118-121 list_tools lookup raising when missing |
| T0011-LIMIT-FAKE-SDK | T-0011 | untested-surface | coverage limit (ungraded); recorded | unknown - inferred from the report and ticket line 140; test suite not re-inspected for real-SDK DSPy/OpenHands runs |
| SEC-T0012-1 | T-0012 | route-misidentification | low / 0.35 (filtered: not valid, 0.88); not a defect | yes - _aliases.py:51 and :57 |
| SEC-T0012-2 | T-0012 | deprecation-signal | low / 0.6 (filtered: not valid, 0.88); not a defect (approved reading D3); recorded for close-out chain analysis and T-0019 guide | yes - _aliases.py:61-64 logs once per template; note_use called at :91 on any http.response.start |
| SEC-T0012-3 | T-0012 | information-disclosure | low / 0.4 (filtered: not valid, 0.85); not a defect | yes - _aliases.py:92 appends DEPRECATION_HEADERS regardless of status; dashboard.py:96 returns cantus_version |
| SEC-T0012-4 | T-0012 | alias-auth-parity | low / 0.3 (filtered: not valid, 0.93); not a defect; stage-6 design suggestion S6-19 (one factory for primary+alias) not adopted, shown to user | yes - app.py:283 and :297 both route_dependencies; dashboard.py:75 and :86 both deps; introspection.py:457 and :468 both deps |
| SEC-T0012-5 | T-0012 | route-misidentification | low / 0.2 (filtered: not valid, 0.95); not a defect | yes - _aliases.py:143 |
| SEC-T0012-6 | T-0012 | middleware-composition | low / 0.3 (filtered: not valid, 0.93); not a defect (approved D1); recorded for T-0019 | yes - _aliases.py:106-108 build_middleware_stack wraps in AliasNotice; :89 reads scope.get("route") |
| SEC-T0012-7 | T-0012 | availability | low / 0.2 (filtered: not valid, 0.9); not a defect | yes - _aliases.py:91 inside send_marked |
| SEC-T0012-8 | T-0012 | tool-name-path-syntax | low / 0.25 (filtered: not valid, 0.9); not a defect; pre-existing in v0.6; recorded for close-out chain analysis (maintenance ticket for a name allow-list suggested) | yes - app.py:159-165 only reserved-name checks; :277 path=f"/tools/{name}", :289 f"/skills/{name}" |
| SEC-T0012-9 | T-0012 | test-hygiene | low / 0.2 (filtered: not valid, 0.95); not a defect; timeout shortened to 30 s in the fix | yes - test_w06_w16_serve.py:206 drops CANTUS_SERVE_*, :219 127.0.0.1, :225 timeout=30 |
| SEC-T0012-10 | T-0012 | availability | low / 0.15 (filtered: not valid, 0.95); fixed (29e017f), although not confirmed as a defect | no - _aliases.py:104 self.state.alias_state = AliasState() in __init__ |
| R2-5 | T-0012 | http-skips-hooks | ungraded (coverage-limit note; v0.6 behaviour pinned by test); recorded for close-out chain analysis; documented in migration guide V6 (MIGRATION_v0.6.0_to_v0.7.0.md:2105-2109) | yes - app.py:249 result = tool_instance.run(**body); validate_args only at agent.py:493 |
| T0012-D8 | T-0012 | stale-session-state | ungraded (ticket Comments, 'Close-out' line 244); recorded for close-out; pre-existing in v0.6 | yes - app.py:244 start then :245 await request.json() outside the try at :248; introspection.py:181 DEFAULT_MAX_ENTRIES = 100 |
| T0012-S6-27 | T-0012 | untested-surface | ungraded (stage-6 leftover); deferred - needs its own ticket (CI matrix entry for the FastAPI lower bound); S6-16 also notes starlette is not a declared dependency | yes for the pin - pyproject.toml:120; CI matrix not inspected (unknown) |
| SEC-T0013-1 | T-0013 | tui-markup-injection | low / 0.3 (filtered: not introduced here, 0.9); not a defect of this change; pre-existing sink; recorded for close-out chain analysis with a suggested ticket to handle all panes | yes - widgets.py:191-196 add_row(name, str(tool.get("description", "")), args_summary, ...) with no escaping |
| SEC-T0013-2 | T-0013 | tui-malformed-snapshot | low / 0.35 (filtered: not introduced here, 0.9); not a defect of this change; pre-existing; recorded for close-out (a malicious or broken server can end the TUI) | yes - app.py:139-142 passes rows through unchecked; widgets.py:188 tool.get(...) with no type guard |
| SEC-T0013-3 | T-0013 | deprecation-signal | low / 0.15 (filtered: not valid, 0.95); not a defect | yes - widgets.py:198-201 |
| T0013-LIMIT-CREDS | T-0013 | untested-surface | coverage limit (ungraded); recorded | yes (limit unchanged) - PermissionsPane reads only four named keys, widgets.py:270-273; no malicious-content test found by this pass (not searched exhaustively: inferred) |
| T0013-TEXTUAL-LB | T-0013 | untested-surface | ungraded (ticket Comments, 'Close-out'); recorded for close-out | yes for the pin - pyproject.toml:195; CI matrix not inspected (unknown) |
| SEC-T0014-1 | T-0014 | docs-example | medium / 0.6 (filtered: not valid, 0.88); not a defect of this change (docstring only); wording decision left to the user (D4b); recorded for close-out chain analysis | yes - memory_auto.py:157-159; docs/site/protocols/memory.md example block after line 95 carries the same docstring and check |
| SEC-T0014-2 | T-0014 | docs-example | low / 0.5 (filtered: not valid, 0.85); not a defect of this change; recorded for close-out; recommendation to T-0017 to say read-back content is untrusted | yes - memory_auto.py:162; no 'untrusted'/'prompt injection' match in docs/site/protocols/memory.md |
| SEC-T0014-3 | T-0014 | docs-example | low / 0.4 (filtered: not valid, 0.9); not a defect | yes - memory_auto.py:159 raise ValueError("refusing to store a password") |
| SEC-T0014-4 | T-0014 | docs-example | low / 0.35 (filtered: not valid, 0.9); not a defect; non-security suggestion left to the user (D4b); recorded for close-out | yes - memory_auto.py:153 unpacks all four, :162 hands out [view, remember]; docs page says str_replace 'remembers a corrected copy' (memory.md:95) |
| SEC-T0014-5 | T-0014 | test-hygiene | low / 0.15 (filtered: not valid, 0.95); not a defect | yes - tests/test_memory_auto.py:159 exec( |
| T0014-EXCL-1 | T-0014 | log-injection | excluded by candidate reviewer (ungraded); not a defect (self-excluded) | yes - agent.py:56-58 |
| T0014-EXCL-2 | T-0014 | log-injection | excluded by candidate reviewer (ungraded); not a defect (self-excluded) | yes - debug.py:39 raise TypeError( (message body not re-read beyond the grep hit: inferred it still carries only the type name) |
| T0014-EXCL-3 | T-0014 | debug-prints-args | excluded by candidate reviewer (ungraded); teaching note; recorded as a teaching caution; pre-existing v0.6 behaviour | yes - debug.py:55-57 prints args on raise, :60-62 prints args and result |
| SEC-T0015-1 | T-0015 | test-hygiene | low / 0.3 (filtered: not valid, 0.92); not a defect | yes - test_internal_paths_silent.py:317-330 Popen with --host 127.0.0.1 |
| SEC-T0015-2 | T-0015 | test-hygiene | low / 0.25 (filtered: not valid, 0.92); not a defect (also stage-6 S-24, left as is) | yes - _free_port at :284-288, used at :316 before Popen |
| SEC-T0015-3 | T-0015 | test-hygiene | low / 0.35 (filtered: not valid, 0.93); fixed (post-review test commit): requests use a proxy-less opener | no - test_internal_paths_silent.py:346 build_opener(ProxyHandler({})) |
| SEC-T0015-4 | T-0015 | test-hygiene | low / 0.15 (filtered: not valid, 0.93); not a defect | yes - test_internal_paths_silent.py:239 filters only a dropped set and CANTUS_SERVE_* |
| SEC-T0015-5 | T-0015 | test-hygiene | low / 0.1 (filtered: not valid, 0.95); not a defect | yes - tests/legacy/support.py:121 sys.path.insert(0, str(tmp_path)) |
| SEC-T0015-6 | T-0015 | test-hygiene | low / 0.3 (filtered: not valid, 0.93); not a defect; not changed | yes - Popen at :317, reader.start() at :344, try: at :349 |
| SEC-T0015-7 | T-0015 | test-hygiene | low / 0.2 (filtered: not valid, 0.97); not a defect (also stage-6 S-15, left as is) | yes - test_matrix_w01_w18.py:479 only sys.modules.pop(f"cantus.adapters.{name}", None) |
| SEC-T0016-1 | T-0016 | docs-example | low/0.35 candidate; rejected (0.9); not a defect; wording fixed at stage 6 | no - ludus-migration.md:152 names `cantus-agent`; :72, :128 also `cantus-agent>=0.7` |
| SEC-T0016-2 | T-0016 | docs-example | low/0.4 candidate; rejected (0.9); not a defect; not changed | yes - ludus-migration.md:275 still only says "Commit and open a PR only as the ludus maintainer's own rules allow" |
| SEC-T0016-3 | T-0016 | docs-example | low/0.45 candidate; rejected (0.85); not a defect; not changed (user decision D8) | yes - checks unchanged at ludus-migration.md:163, :187 (name list not extended) |
| SEC-T0016-4 | T-0016 | install-smoke | low/0.3 candidate; rejected (0.9); not a defect; not changed | yes - ludus-migration.md:163 and :258 still run `python -c ... runpy.run_path(...)` from the repo root; the optional `cantus.__file__` print was not added (T-0016 ticket Comments, open items) |
| SEC-T0016-5 | T-0016 | http-skips-hooks / serve-no-auth | low/0.35 candidate; rejected (0.9); CHAIN INPUT; not a defect; recorded as chain-analysis input | yes - app.py:249 calls `tool_instance.run(**body)` directly (no validate_args/hooks); default host 127.0.0.1 (cantus/config.py:59), default auth NONE (config.py:76); the UserWarning at app.py:198-206 fires only when introspection is enabled and names only /introspection, not the tool routes; no host-based warning exists |
| SEC-T0016-6 | T-0016 | docs-example | low/0.2 candidate; rejected (0.92); not a security defect; doc-quality fix (P-08) | mitigated - ludus-migration.md:147 and :255 tell the reader to keep the venv outside the repo or name it `.venv` |
| SEC-T0017-1 | T-0017 | dual-route-rules | medium/0.45 candidate; rejected (0.8); CHAIN INPUT; not a defect; operator note added in both directions (0fb8419) | partly - serve.md has no `/skills` mention (grep: only /tools at :41, :53, :62); the two-direction operator note is on tool.md:193. Both families are mounted with the same dependencies: cantus/serve/app.py:277-297, dashboard.py:70-86, introspection.py:452-468 |
| SEC-T0017-2 | T-0017 | dual-route-rules | low/0.15 candidate; rejected (0.85); not a defect; not changed, optional hardening sentence left open (ticket Comments, open items at push) | yes - no normalisation/allow-list sentence in tool.md (grep for normali\|percent\|allow-list: no hit) |
| SEC-T0017-3 | T-0017 | model-output-key / remote-tool-prompt-injection | low/0.3 candidate; rejected (0.88); CHAIN INPUT; not a defect; not changed, optional doc sentence left open | yes - adapters.md:83-84 `Agent(model, tools=remote_tools)`; :91 says the server's content is not validated, but no sentence marks names/descriptions/results as untrusted (grep `untrusted`: no hit) |
| SEC-T0017-4 | T-0017 | registry-fallback | low/0.3 candidate; rejected (0.85); not a defect; wording fix adopted (0fb8419) | yes (behaviour) - agent.py:98-101 uses `_get_global_registry()` and warns W11 only if it already holds a tool; documented at tool.md:179, wording `Available: [...]` at tool.md:149 |
| SEC-T0017-5 | T-0017 | registry-fallback / shared-registry | low/0.2 candidate; rejected (0.88); CHAIN INPUT; not a defect; doc sentence adopted (0fb8419) | yes - registry.py:175 `self._by_kind[kind][name] = instance` (no duplicate check); agent.py:102-103 keeps a passed Registry as is; tool.md:79 now states it |
| T-0017 F-02/F-03 (stage 6, chain input) | T-0017 | http-skips-hooks | stage 6 finding, no security grade; CHAIN INPUT; fixed in the pages at stage 6; recorded as chain input (R2-5 family) | yes - hooks/validate_args only at agent.py:493-532; serve calls `tool_instance.run(**body)` at app.py:249; llms.txt:110 and the guide (:1478, V6) say so. Workflow/adapter paths not read line by line (inferred from grep: no hook call under cantus/workflows/) |
| SEC-T0018-1 | T-0018 | dual-route-rules | low/0.45 candidate; rejected (0.85); CHAIN INPUT; not a defect; not changed (R15) | yes - quickstart-desktop.md:93 unchanged in substance; no `/skills` on the page (grep) |
| SEC-T0018-2 | T-0018 | dual-route-rules | low/0.35 candidate; rejected (0.85); CHAIN INPUT; not a defect; not changed | yes - google-chat.md:147 names only `/tools` |
| SEC-T0018-3 | T-0018 | shared-registry | medium/0.5 candidate; rejected (0.8); CHAIN INPUT; not a defect; doc suggestion adopted (04d108e) | yes (behaviour, now documented) - tips.md:157 `agent.registry is reg`, :169 warns about later additions; registry.py:175 still overwrites |
| SEC-T0018-4 | T-0018 | registry-fallback | low/0.4 candidate; rejected (0.85); not a defect; wording aligned to the Tool page (04d108e) | yes (behaviour) - agent.md:20 documents it; agent.py:98-101 |
| SEC-T0018-5 | T-0018 | serve-no-auth | low/0.55 candidate; rejected (0.85); CHAIN INPUT; not a defect (pre-existing); shown to the user, not changed; left for retrospective (ticket Comments) | yes - line.md:55-59 has no `--auth-mode`, :69 `cloudflared tunnel --url http://127.0.0.1:8765`; grep `auth-mode` in docs/site/channels/ hits only google-chat.md:147 |
| SEC-T0018-6 | T-0018 | docs-example | low/0.15 candidate; rejected (0.95); not a defect; not changed (R16) | yes - line.md:8; pyproject.toml:7 `version = "0.6.0"` |
| SEC-T0018-7 | T-0018 | docs-example | low/0.25 candidate; rejected (0.9); not a defect; sentence added (04d108e) | no (addressed) - quickstart-agent.md:175 says an agent built before keeps the unguarded tool |
| SEC-T0018-8 | T-0018 | shared-registry | low/0.2 candidate; rejected (0.9); not a defect; not changed | yes - tips.md:71-72; registry.py:175 |
| SEC-T0019-1 | T-0019 | http-skips-hooks | low/0.5 candidate; rejected (0.85); CHAIN INPUT; not a defect; sentence adopted (73fd75c) | addressed in doc - guide :1477-1478; behaviour remains at cantus/serve/app.py:249 |
| SEC-T0019-2 | T-0019 | deprecation-signal | low/0.55 candidate; rejected (0.85); not a defect; doc fix adopted (73fd75c) | no (doc fixed) - guide :1475 "assigned to the class or to an instance after the class exists"; the guard gap itself remains by design (not read in agent.py; inferred from the guide) |
| SEC-T0019-3 | T-0019 | deprecation-signal | low/0.45 candidate; rejected (0.85); CHAIN INPUT; not a defect; doc fix adopted (73fd75c) | yes (design) - guide :2042-2044 now warns and suggests `message=`; W11 raised at cantus/core/agent.py:100-101 only |
| SEC-T0019-4 | T-0019 | dual-route-rules | low/0.6 candidate; rejected (0.85); not a defect; doc fix adopted (73fd75c) | no (doc fixed) - guide :1056-1058 lists both families and the auth conditions |
| SEC-T0019-5 | T-0019 | dual-route-rules | low/0.6 candidate; rejected (0.85); CHAIN INPUT; not a defect; regenerated entry (b994485) | no (doc fixed) - CHANGELOG.md:17 gives `/skills`→`/tools` and the alias-period reverse direction |
| SEC-T0019-6 | T-0019 | dual-route-rules | low/0.55 candidate; rejected (0.85); CHAIN INPUT; not a defect; doc fix adopted (73fd75c) | no (doc fixed) - guide :2200 and X11 at :1591-1593 |
| SEC-T0019-7 | T-0019 | model-output-key | low/0.45 candidate; rejected (0.85); CHAIN INPUT; not a defect (frozen-spec decision); doc sentence adopted (73fd75c) | yes (by design) - tool_call.py:50-54 checks `tool_name` first; guide :2022-2024 warns |
| SEC-T0019-8 | T-0019 | dual-route-rules | low/0.3 candidate; rejected (0.85); not a defect; not changed | yes - no normalisation sentence in the guide (grep percent\|normali: no hit) |
| SEC-T0019-9 | T-0019 | serve-no-auth | low/0.3 candidate; rejected (0.9); CHAIN INPUT (via T-0020); not a defect; note adopted (73fd75c) | yes (example) with note - guide :907-909 says examples run without authentication and to keep a real server's `--host` and auth settings; :912 command |
| SEC-T0019-10 | T-0019 | deprecation-signal | low/0.3 candidate; rejected (0.93); not a defect; not changed (T-0012 design D3) | yes (by design) - _aliases.py:61-64 returns if the template is already in `_logged`; guide :1043 states it |
| SEC-T0019-11 | T-0019 | docs-example | low/0.15 candidate; rejected (0.92); not a defect; not changed | yes - guide :912 `PYTHONPATH=. cantus serve --registry-import mytools:registry` |
| SEC-T0020-1 | T-0020 | ci-credentials | low/0.2 candidate; rejected (0.92); not a defect; recorded as known | yes - test_rename_sweep.py:186 `file_path.read_bytes()`; no is_symlink check (grep) |
| SEC-T0020-2 | T-0020 | ci-credentials | low/0.25 candidate; rejected (0.9); fixed as robustness (5791a62) | no - `_git_env()` drops `GIT_*` (:115); `_TMP_GIT_ENV` sets GIT_CONFIG_GLOBAL=devnull and GIT_CONFIG_NOSYSTEM (:210). The report notes tests/test_check_no_dev_paths.py has the same pattern on base; that file was not read (inferred) |
| SEC-T0020-3 | T-0020 | ci-credentials | low/0.15 candidate; rejected (0.95); CHAIN INPUT; not a defect (pre-existing); deferred to a low-priority 0000-maintenance ticket, user decision 2026-11-20 (ticket Comments) | yes - six steps without it: docs.yml:18, release.yml:27, cross-platform-install.yml:27, supply-chain.yml:66, repo-hygiene.yml:18 and :31; only test.yml:28, :57 set it |
| SEC-T0020-4 | T-0020 | supply-chain | low/0.3 candidate; rejected (0.9); not a defect; not changed (approved N3) | yes - cell 4: `cantus_version = "v0.6.0"`, the note about `main`, and `%pip install -q "git+https://github.com/schola-cantorum/cantus@{cantus_version}"` |
| SEC-T0020-5 | T-0020 | serve-no-auth / http-skips-hooks | low/0.3 candidate; rejected (0.88); partly adopted (fc3be11) | partly - llms.txt:110 states no hook via `cantus serve`; :204 serve line still has no auth mention |
| SEC-T0020-6 | T-0020 | serve-no-auth | low/0.3 candidate; rejected (0.85); CHAIN INPUT; not a defect (pre-existing, D15); deferred to a 0000-maintenance docs ticket plus an OPEN-QUESTIONS entry on whether serve should warn or refuse on non-loopback host with auth none (user decision 2026-11-20) | yes - the three lines above; security note at docs/quickstart-desktop.md:87 and site :93; no host/auth guard in cantus/serve/app.py (only the /introspection warning at :198-206) |
| SEC-T0020-7 | T-0020 | dual-route-rules | low/0.2 candidate; rejected (0.9); CHAIN INPUT; not a defect; not changed (consistent with T-0018 R15) | yes - no `/skills` in docs/quickstart-desktop.md (grep); both families share dependencies at cantus/serve/app.py:283, :297 |
| SEC-T0020-8 | T-0020 | install-smoke | low/0.15 candidate; rejected (0.9); CHAIN INPUT; not a defect (verification credibility, pre-existing); deferred to a 0000-maintenance ticket before the v0.7.0 release (user decision 2026-11-20; ADR-0013 item 4 relies on this smoke) | yes - smoke_install.sh:33 and cross-platform-install.yml:42 `python -c "from cantus import tool, Agent, load_chat_model"` with no cd outside the tree |
| SEC-T0020-9 | T-0020 | memory-untrusted | low/0.15 candidate; rejected (0.92); CHAIN INPUT; not a defect; doc fix adopted (fc3be11) | yes (behaviour) - llms.txt:148 documents `auto.tools` with corrected `delete`/`str_replace` wording; the AutoMemory source was not opened (behaviour inferred from the report and llms.txt) |
| T-0020 CI fix outside reviewed range (Comments only) | T-0020 | supply-chain | ungraded; not reviewed at stage 6/7; recorded in ticket Comments for the user to weigh at landing; landed with PR #71 | yes - supply-chain.yml:54-56 and :127 record the removal; CHANGELOG.md:40 still says the audit lists the pillow 12.3.0 advisories as known (stale against the workflow; T-0021's ticket likewise per the Comments, not re-read) |
| T-0020 pyproject ruff per-file ignore (Comments only) | T-0020 | ci-credentials | ungraded; lint config only; recorded in ticket Comments | unknown - not checked in pyproject.toml |
| T-0016 open items (Comments only) | T-0016 | http-skips-hooks / install-smoke | ungraded; left as is; raise at the retrospective | yes - ludus-migration.md:26 and :67-68 state the gate is not enforced over HTTP, but check 1 (:163) prints no `cantus.__file__` |
| T-0018/T-0020 Known, not changed: missing PYTHONPATH and grammar claims (Comments only) | T-0018, T-0020 | docs-example | ungraded; documentation accuracy, not security; recorded as known, not changed | yes for the quickstart command lines (docs/quickstart-desktop.md:72, site :78 have no PYTHONPATH); the others not re-read (unknown) |
| T-0018 coverage note: /docs and /openapi.json unauthenticated | T-0018 | serve-no-auth | not a candidate; listed as pre-existing and not covered; recorded (coverage limitation) | yes - config.py:71-72 defaults `/docs`, `/openapi.json`; app.py:140-141 passes them to FastAPI with no dependencies (app-level; that no global dependency is attached is inferred from app.py:153-216, which attaches auth per route group) |
| T-0019/T-0020 stage 8 coverage gaps (Comments only) | T-0019, T-0020 | dual-route-rules | ungraded; recorded | n/a (evidence gap, not code) - bearer/none parity matches code at cantus/serve/app.py:153-156, :283, :297 |
