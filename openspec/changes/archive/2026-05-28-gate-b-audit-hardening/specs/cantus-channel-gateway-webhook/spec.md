## MODIFIED Requirements

### Requirement: Webhook channel constructors fail fast on missing or blank secrets

`LineWebhookChannel(channel_secret, channel_access_token, ...)` SHALL resolve each secret value in the order: constructor argument when not `None`, then `Settings()` field's `get_secret_value()` when not `None` and not whitespace-only. If neither source yields a non-empty, non-whitespace string the constructor SHALL raise `ValueError` whose message contains the literal substring `channel secret not configured` and names the missing field. The same fail-fast resolution SHALL apply to `TelegramWebhookChannel(secret_token, bot_token, ...)` with its corresponding fields.

After the fail-fast resolution above succeeds for `TelegramWebhookChannel`, the constructor SHALL additionally validate the format of both resolved Telegram token values. The resolved `bot_token` value SHALL match the regular expression `^\d+:[A-Za-z0-9_-]{20,}$` AND SHALL have length less than or equal to 255 characters. The resolved `secret_token` value SHALL match the regular expression `^[A-Za-z0-9_-]+$` AND SHALL have length between 1 and 256 characters inclusive. When the resolved `bot_token` fails either check, the constructor SHALL raise `ValueError` whose message contains the literal substring `telegram bot_token has invalid format` and SHALL NOT contain any character of the rejected `bot_token` value. When the resolved `secret_token` fails either check, the constructor SHALL raise `ValueError` whose message contains the literal substring `telegram secret_token has invalid format` and SHALL NOT contain any character of the rejected `secret_token` value. The format validation SHALL run after blank-or-missing checks, so that an empty configuration continues to raise `channel secret not configured` rather than `invalid format`.

#### Scenario: Empty configuration raises with actionable message

- **GIVEN** no `channel_secret` constructor argument is provided
- **AND** the env variable `CANTUS_SERVE_CHANNEL_LINE_SECRET` is unset
- **WHEN** `LineWebhookChannel()` is constructed
- **THEN** `ValueError` is raised
- **AND** the exception message contains the literal substring `channel secret not configured`
- **AND** the exception message contains the literal substring `channel_line_secret`

#### Scenario: TelegramWebhookChannel accepts a well-formed bot_token and secret_token

- **GIVEN** `bot_token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_-"` and `secret_token = "Sample_Secret-Token"`
- **WHEN** `TelegramWebhookChannel(secret_token=secret_token, bot_token=bot_token)` is constructed
- **THEN** the constructor returns without raising
- **AND** the channel instance is usable for subsequent `send()` calls

#### Scenario: TelegramWebhookChannel rejects a bot_token with invalid structure

- **GIVEN** `bot_token = "not-a-valid-token"` and `secret_token = "Sample_Secret-Token"`
- **WHEN** `TelegramWebhookChannel(secret_token=secret_token, bot_token=bot_token)` is constructed
- **THEN** `ValueError` is raised
- **AND** the exception message contains the literal substring `telegram bot_token has invalid format`
- **AND** the exception message does NOT contain the literal substring `not-a-valid-token`

##### Example: bot_token rejection cases

| Input bot_token | Reason | Resulting exception |
| --------------- | ------ | ------------------- |
| `"abc:def"` | digits prefix missing AND suffix too short | `ValueError(... telegram bot_token has invalid format ...)` |
| `"123:short"` | suffix shorter than 20 characters | `ValueError(... telegram bot_token has invalid format ...)` |
| `"123456789:VALID-Suffix_ofLength22"` | accepted | constructor returns |
| 260-character string of digits with valid prefix | length exceeds 255 | `ValueError(... telegram bot_token has invalid format ...)` |

#### Scenario: TelegramWebhookChannel rejects a secret_token with disallowed characters

- **GIVEN** `bot_token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_-"` and `secret_token = "has spaces and !@#"`
- **WHEN** `TelegramWebhookChannel(secret_token=secret_token, bot_token=bot_token)` is constructed
- **THEN** `ValueError` is raised
- **AND** the exception message contains the literal substring `telegram secret_token has invalid format`
- **AND** the exception message does NOT contain the literal substring `has spaces`

##### Example: secret_token boundary cases

| Input secret_token | Reason | Resulting exception |
| ------------------ | ------ | ------------------- |
| `""` | empty after strip (caught by existing blank-check) | `ValueError(... channel secret not configured ...)` |
| `"valid_secret-1"` | accepted | constructor returns |
| 257-character `A`-only string | length exceeds 256 | `ValueError(... telegram secret_token has invalid format ...)` |
| `"with space"` | contains disallowed space | `ValueError(... telegram secret_token has invalid format ...)` |
