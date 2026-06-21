# `Soul` Identity Protocol (v0.5.0)

## What it is and when to use it

Since v0.3.1, cantus models an agent's *identity* with `cantus.identity.Soul`: a six-section record loaded from a `SOUL.md` file. The six sections are name and role, personality, rules, tools, output format, and handoffs. Pass the parsed `Soul` to `Agent(soul=...)` and cantus prepends it to the system prompt for you.

This sits alongside the other two teaching abstractions in the framework:

| Abstraction | Role |
| --- | --- |
| `Skill` | Capability — what this agent can do |
| `Memory` | Memory — what this agent has remembered |
| `Soul` | Identity — who this agent is |

## The six-section `SOUL.md` format

The on-disk format follows the [aaronjmars/soul.md](https://github.com/aaronjmars/soul.md) convention. Each section opens with an H2 `##` header. Headers are **case-sensitive** and compared byte-for-byte. A section body runs from the line after its H2 header down to the next H2 header or end of file, and leading and trailing whitespace is stripped.

```markdown
## Name & Role
Librarian assistant for a small public library.

## Personality
Helpful, patient, curious about books.

## Rules
- Cite catalog IDs when recommending books.
- Always ask follow-ups before a final recommendation.

## Tools
- search_book(title)
- check_availability(book_id)

## Output format
Plain prose with bullet points for lists.

## Handoffs
Escalate cataloging requests to the head librarian.
```

The six canonical H2 headers, in order, are:

1. `## Name & Role`
2. `## Personality`
3. `## Rules`
4. `## Tools`
5. `## Output format`
6. `## Handoffs`

They map to these `Soul` attributes: `name_and_role`, `personality`, `rules`, `tools`, `output_format`, `handoffs`.

## How `Soul.from_file()` fails

`Soul.from_file(path)` raises the matching exception in each of these cases:

| Situation | Exception | Exception attributes |
| --- | --- | --- |
| File does not exist | `FileNotFoundError` | Standard Python; **not** wrapped in `SoulParseError` |
| One or more H2 sections missing | `SoulParseError` | `missing_sections=[<canonical titles>]` |
| The same H2 appears more than once | `SoulParseError` | `duplicates=[<title>, ...]` |
| Casing mismatch (e.g. `## name & Role`) | `SoulParseError` | `missing_sections=["Name & Role"]` **plus** `unexpected=["name & Role"]` |
| An H2 outside the spec (e.g. `## Examples`) | `SoulParseError` | `unexpected=["Examples"]` |

`SoulParseError` is a subclass of `ValueError`, so `except ValueError` will also catch it. To read the `missing_sections`, `duplicates`, and `unexpected` fields, catch `SoulParseError` directly.

```python
from cantus.identity import Soul, SoulParseError

try:
    soul = Soul.from_file("SOUL.md")
except SoulParseError as exc:
    print(f"missing: {exc.missing_sections}")
    print(f"duplicates: {exc.duplicates}")
    print(f"unexpected: {exc.unexpected}")
```

## How `Agent(soul=...)` injects the soul

`Agent.__init__` takes a keyword-only parameter `soul: Soul | None = None`. The injection order is:

```
<soul.to_system_prompt()>\n\n<v0.3.0 baseline system prompt>
```

In other words, the `soul.to_system_prompt()` string comes first, followed by two newlines, followed by the existing v0.3.0 system prompt. When `soul=None` (the default), the system prompt is **byte-identical** to v0.3.0, so existing agent behavior is untouched.

```python
from cantus import Agent
from cantus.identity import Soul

soul = Soul.from_file("SOUL.md")
agent = Agent(model=m, soul=soul)
# Every model.generate(prompt) call made during agent.run(...) now includes
# the soul content as a system-prompt prefix.
```

The `soul` is **not** registered as a `Skill` and does **not** appear in `registry.spec_for_llm()`, so the tool list the model sees stays free of `SOUL.md` content.

## Override pattern: build the system prompt yourself

If you want to take over system-prompt construction entirely, pass `soul=None` (or omit it) and control the prompt sent to the model in your own host code:

```python
from cantus import Agent
from cantus.identity import Soul

soul = Soul.from_file("SOUL.md")
custom_prefix = soul.to_system_prompt() + "\n\n=== CUSTOM HOST PREAMBLE ===\n\n"
agent = Agent(model=m)  # soul=None, so cantus injects nothing

# Host code assembles the prompt itself.
def run_with_custom_prompt(query: str) -> str:
    prompt = custom_prefix + agent._build_prompt(AgentState(query=query))
    return agent.model.generate(prompt)
```

## The `SOUL.md` trust model

The framework treats `SOUL.md` as **trusted, host-authored input**:

- The framework does **not** escape, sanitize, or check for control characters.
- It is valid for a student to write `## Rules\nIgnore all prior instructions` into a `SOUL.md`. In a teaching setting this is the student exercising full control over the agent's behavior.
- When host code reads `SOUL.md` from an **untrusted source** (an end-user upload, a third-party fetch, a network response), **the host code is responsible for validating the content** before passing it to `Soul.from_file()`.

The design trade-off: forcing the framework to escape input would break legitimate Markdown metacharacters inside the `## Rules` section (`*`, `#`, `>`), making the rendered soul diverge from what the student intended.
