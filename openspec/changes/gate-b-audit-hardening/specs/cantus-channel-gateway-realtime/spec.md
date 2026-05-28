## MODIFIED Requirements

### Requirement: Discord Gateway WebSocket connect implements IDENTIFY, HEARTBEAT, RESUME, and exponential backoff

`DiscordRealtimeChannel.connect()` SHALL, when awaited, open a WebSocket connection to `wss://gateway.discord.gg/?v=10&encoding=json` using the `websockets` library. Upon receiving Discord opcode 10 (HELLO), the channel SHALL begin sending opcode 1 (HEARTBEAT) every `heartbeat_interval` milliseconds reported by HELLO and SHALL track receipt of opcode 11 (HEARTBEAT ACK). The channel SHALL send opcode 2 (IDENTIFY) once, carrying `bot_token` and `intents`. When the connection drops, the channel SHALL attempt opcode 6 (RESUME) using the stored `session_id` and last `seq`; if Discord responds with opcode 9 (INVALID SESSION) and payload `d == false`, the channel SHALL fall back to a fresh IDENTIFY. Reconnect attempts SHALL wait `min(60, 2 ** attempts)` seconds where `attempts` is the consecutive failure count. After 10 consecutive IDENTIFY failures, the channel SHALL set `self.last_error` to the most recent exception and stop attempting reconnect; the channel SHALL NOT raise out of the `connect()` coroutine when reconnect stops, to avoid crashing the lifespan.

Upon receiving HELLO, before any HEARTBEAT is scheduled, the channel SHALL validate that the integer value reported for `heartbeat_interval` (in milliseconds) is greater than or equal to `100` AND less than or equal to `120000`. When the reported `heartbeat_interval` falls outside that inclusive range, the channel SHALL raise an internal resumable exception of type `_ResumableError` so that the existing reconnect-with-exponential-backoff path handles the violation. The channel SHALL NOT begin any HEARTBEAT loop when the validation fails, and SHALL NOT spin or thrash on the malformed HELLO frame.

The channel SHALL advance the stored `seq` cursor (which is later used by RESUME) only from frames whose opcode equals `0` (DISPATCH). The acceptance and dispatch of DISPATCH frames SHALL be reified as a private helper named `_accept_dispatch_frame(frame)` on `DiscordRealtimeChannel`; that helper SHALL be the only call site that mutates `self._seq`. Frames whose opcode is not DISPATCH SHALL NOT cause `self._seq` to change, even when their JSON payload contains an integer field named `s`.

#### Scenario: Heartbeat tracks ACK and re-establishes connection on miss

- **GIVEN** a Discord Gateway WebSocket session has been established and the most recent HEARTBEAT was sent
- **WHEN** Discord fails to send opcode 11 (HEARTBEAT ACK) before the next heartbeat interval
- **THEN** the channel closes the current WebSocket with close code 1011
- **AND** the channel attempts a RESUME with the stored `session_id` and `seq`

#### Scenario: RESUME failure falls back to IDENTIFY

- **GIVEN** a Discord Gateway connection has dropped and the channel attempts RESUME
- **WHEN** Discord responds with opcode 9 (INVALID SESSION) and `d == false`
- **THEN** the channel discards the stored `session_id` and `seq`
- **AND** the channel sends a fresh opcode 2 (IDENTIFY) on the next connection

#### Scenario: Ten consecutive IDENTIFY failures stop reconnect without raising

- **GIVEN** the channel has just attempted its 10th consecutive IDENTIFY and Discord rejected each
- **WHEN** the 10th failure resolves
- **THEN** `self.last_error` is set to the most recent exception
- **AND** the `connect()` coroutine continues running without raising
- **AND** no further reconnect attempts are made

#### Scenario: HELLO frame with heartbeat_interval below the lower bound triggers reconnect

- **GIVEN** the channel has just connected and the next inbound frame is opcode 10 (HELLO) with payload `{"heartbeat_interval": 0}`
- **WHEN** the channel processes the HELLO frame
- **THEN** the channel raises `_ResumableError` internally
- **AND** no HEARTBEAT loop is started for this connection attempt
- **AND** the existing reconnect-with-exponential-backoff path is entered

#### Scenario: HELLO frame with heartbeat_interval above the upper bound triggers reconnect

- **GIVEN** the channel has just connected and the next inbound frame is opcode 10 (HELLO) with payload `{"heartbeat_interval": 200000}`
- **WHEN** the channel processes the HELLO frame
- **THEN** the channel raises `_ResumableError` internally
- **AND** no HEARTBEAT loop is started for this connection attempt

##### Example: heartbeat_interval boundary cases

| heartbeat_interval (ms) | Action |
| ----------------------- | ------ |
| 0 | reject, raise `_ResumableError` |
| 99 | reject, raise `_ResumableError` |
| 100 | accept, start HEARTBEAT loop |
| 41250 | accept (typical Discord value) |
| 120000 | accept |
| 120001 | reject, raise `_ResumableError` |
| 200000 | reject, raise `_ResumableError` |

#### Scenario: Non-DISPATCH frame carrying integer s does not advance seq

- **GIVEN** the channel has `self._seq` set to `42` and an inbound frame has `op = 11` (HEARTBEAT ACK) with payload `{"s": 999}`
- **WHEN** the channel processes the frame
- **THEN** `self._seq` remains `42`
- **AND** `_accept_dispatch_frame(frame)` is NOT invoked for this frame

#### Scenario: DISPATCH frame carrying integer s advances seq via the helper

- **GIVEN** the channel has `self._seq` set to `42` and an inbound frame has `op = 0` (DISPATCH) with payload `{"s": 43, "t": "MESSAGE_CREATE", "d": {...}}`
- **WHEN** the channel processes the frame
- **THEN** `_accept_dispatch_frame(frame)` is invoked exactly once with that frame
- **AND** `self._seq` becomes `43`
