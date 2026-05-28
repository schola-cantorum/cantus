## MODIFIED Requirements

### Requirement: connect() opens a Pub/Sub streaming pull, acks after enqueue, and applies exponential backoff with a ten-failure ceiling

`GoogleChatPubSubChannel.connect()` SHALL, when awaited, open a `google.cloud.pubsub_v1.SubscriberClient` constructed from the resolved `credentials_path`, register a callback against the resolved `subscription`, and run a streaming pull loop for the lifetime of the channel. For each delivered `pubsub_v1.types.PubsubMessage`, the callback SHALL parse `message.data` as UTF-8 JSON, append the resulting `dict` to the channel's internal receive queue, and then call `message.ack()`. If `json.loads` raises or the parsed value is not a `dict`, the callback SHALL call `message.nack()` and SHALL NOT raise out of the callback. When the streaming pull future raises any exception, `connect()` SHALL increment a consecutive-failure counter `attempts`, sleep `min(60, 2 ** attempts)` seconds via `asyncio.sleep`, and re-open the streaming pull. The counter SHALL reset to zero after any successful message delivery. After 10 consecutive failures with no intervening successful delivery, `connect()` SHALL set `self.last_error` to the most recent exception and SHALL return cleanly without raising; no further reconnect attempts SHALL be made until a subsequent `disconnect()` plus `connect()` cycle.

The reset-on-successful-delivery rule above SHALL be implemented via a boolean instance attribute `self._success_since_last_failure` defined on `GoogleChatPubSubChannel` with initial value `False`. The callback SHALL set `self._success_since_last_failure` to `True` after invoking `message.ack()` for a successful enqueue. The except branch of `connect()`'s streaming pull loop SHALL, when handling a failure, check `self._success_since_last_failure` first; when the flag is `True`, the except branch SHALL set `attempts` to zero, set `self._success_since_last_failure` to `False`, and only then increment `attempts` for the current failure. This wiring SHALL produce the observable behaviour that any number of accumulated failures is reset by a single successful message delivery, so that the next failure thereafter sleeps `1` second (not the geometric continuation of the prior streak).

The `SubscriberClient` returned by the private helper that builds it SHALL be constructed from `google.oauth2.service_account.Credentials.from_service_account_file(self._credentials_path, scopes=["https://www.googleapis.com/auth/pubsub"])`. The `scopes` keyword argument SHALL be passed explicitly (rather than relying on google-cloud-pubsub's implicit default) so that a service-account file lacking that OAuth scope fails fast at `connect()` time rather than silently degrading later.

#### Scenario: Message arrives, is enqueued, then acked

- **GIVEN** a connected channel and a `PubsubMessage` with `data = b'{"event": "MESSAGE", "space": "spaces/AAA"}'`
- **WHEN** the SubscriberClient delivers the message to the channel callback
- **THEN** the channel's internal queue length increases by one
- **AND** `message.ack()` is invoked exactly once
- **AND** `message.nack()` is NOT invoked

#### Scenario: Malformed JSON is nacked, queue unchanged, no exception escapes

- **GIVEN** a connected channel and a `PubsubMessage` with `data = b'not-json'`
- **WHEN** the SubscriberClient delivers the message to the channel callback
- **THEN** `message.nack()` is invoked exactly once
- **AND** the channel's internal queue length is unchanged
- **AND** `connect()` continues running without raising

#### Scenario: Backoff between pull failures follows the bounded exponential schedule

- **GIVEN** a channel whose first three streaming pull attempts each raise `google.api_core.exceptions.Unknown`
- **WHEN** the third failure resolves
- **THEN** the sleep durations between attempts are `1`, `2`, and `4` seconds in order

##### Example: backoff schedule values

| attempts (after failure n) | sleep duration before next attempt |
| -------------------------- | ---------------------------------- |
| 1 | 1 second |
| 2 | 2 seconds |
| 3 | 4 seconds |
| 6 | 32 seconds |
| 7 | 60 seconds (clamped) |
| 10 | (no more attempts; last_error set) |

#### Scenario: Ten consecutive failures stop reconnect without raising

- **GIVEN** ten consecutive streaming pull attempts each raise `google.api_core.exceptions.PermissionDenied`
- **WHEN** the tenth failure resolves
- **THEN** `self.last_error` equals the tenth exception instance
- **AND** the `connect()` coroutine returns without raising
- **AND** no further streaming pull is opened

#### Scenario: Successful delivery resets the failure counter

- **GIVEN** a channel that has accumulated five consecutive failures
- **WHEN** a streaming pull succeeds and one message is delivered and acked
- **THEN** the internal failure counter is reset to zero
- **AND** the next failure causes a sleep of `1` second (not `64` seconds)

#### Scenario: The success-since-last-failure flag is set after ack and cleared in the except branch

- **GIVEN** a channel where `self._success_since_last_failure` is `False` and a `PubsubMessage` is about to be delivered
- **WHEN** the callback completes a successful enqueue and invokes `message.ack()`
- **THEN** `self._success_since_last_failure` becomes `True`
- **AND** the next time `connect()`'s except branch handles a failure, it observes the flag as `True`, resets `attempts` to zero, clears the flag back to `False`, and then increments `attempts` for the current failure

##### Example: failure-success-failure interleaving

| Step | Event | `attempts` before | `_success_since_last_failure` before | `attempts` after | `_success_since_last_failure` after | next sleep |
| ---- | ----- | ----------------- | ------------------------------------ | ---------------- | ----------------------------------- | ---------- |
| 1 | failure #1 | 0 | False | 1 | False | 1s |
| 2 | failure #2 | 1 | False | 2 | False | 2s |
| 3 | failure #3 | 2 | False | 3 | False | 4s |
| 4 | failure #4 | 3 | False | 4 | False | 8s |
| 5 | failure #5 | 4 | False | 5 | False | 16s |
| 6 | one message ack | 5 | False | 5 | True | n/a |
| 7 | failure #6 | 5 | True | 1 | False | 1s |

#### Scenario: SubscriberClient is built with explicit pubsub scope

- **GIVEN** a `GoogleChatPubSubChannel` instance whose `credentials_path` points at a valid service-account JSON file
- **WHEN** `connect()` is awaited and the channel invokes its private subscriber-builder helper
- **THEN** `google.oauth2.service_account.Credentials.from_service_account_file` is invoked exactly once with the credentials path AND the keyword argument `scopes=["https://www.googleapis.com/auth/pubsub"]`
- **AND** the resulting `SubscriberClient` carries credentials whose `scopes` attribute contains exactly the string `https://www.googleapis.com/auth/pubsub`
