# KEY_FOLLOWUPS: rep2_bug_squash_paykit

Likely interviewer follow-ups after each group, with answers worth giving.

## Gateway client

**"Which statuses should be retried, and how would you space the retries?"**
5xx and 429 (and connection errors / timeouts where the request may not have arrived). Not 4xx:
the request is wrong and will stay wrong; for 409 or 402 a retry can even repeat a side effect.
Space retries with exponential backoff plus jitter (e.g. `base * 2**attempt * random.uniform(0.5, 1.5)`),
honour `Retry-After` on 429/503, and cap total time. In tests, inject the sleep function so the
suite does not actually wait.

**"What happens on a timeout?"**
`urllib` raises `URLError`/`TimeoutError`, which this client does not catch, so it is not retried.
A timeout is ambiguous (the charge may have been created), which is exactly the case the
idempotency key is for: retry with the same key and the gateway returns the original result.
Worth proposing: catch `TimeoutError`/`URLError` in `_request` and treat them as retryable.

**"Why must the idempotency key be generated outside the loop? Should the caller pass it?"**
The key names the business operation. A new key per attempt makes every retry look like a new
charge (double charging during incidents). Better still: let the caller pass the key (e.g. derived
from the order id) so a crash and restart of the caller does not lose it. GET is naturally
idempotent and needs no key.

**"How would you test pagination without a server?"**
Inject a transport (or monkeypatch `_request`) that returns canned pages; assert the cursor
sequence (`None`, last id of page 1, ...). Edge cases: empty account, exact multiple of the page
size, `has_more` true with an empty page (guard against infinite loops), and a page size larger
than the data.

**"Should `list_charges` return a list?"**
A generator (`yield from page["data"]`) lets callers stream large histories and stop early. Keep a
list-returning helper for compatibility if existing callers index into the result.

## Money and currency

**"Why integers in minor units, and why Decimal in convert?"**
Floats cannot represent 0.10 exactly; summing floats drifts. Integer minor units make addition
exact; Decimal makes the one place that multiplies by a non-integer rate exact up to the explicit
rounding step.

**"Which rounding mode?"**
Half-up is common for display and most card networks; banker's rounding (half-even) avoids bias
in aggregates. The important part is that it is explicit and applied once, at the target minor
unit. Never round through an intermediate currency's minor unit (that would double-round).

**"Where would exponents come from in production?"**
ISO 4217 (JPY 0, USD 2, KWD/BHD/TND 3, some at 4 like CLF). Keep the table in data, not code, and
fail loudly for an unknown currency (this code raises ValueError).

**"Should Money support adding different currencies by converting?"**
No implicit conversion: it needs a rate and a timestamp, and silently picking one is how ledgers
drift. Make conversion an explicit call.

## Webhooks

**"Why is the timestamp part of the signed string?"**
It binds the signature to the time of sending; together with the tolerance window it stops
replaying an old captured delivery with a new `t=` value. Signing only the body would let an
attacker reuse an old signature forever.

**"Why compare_digest?"**
`==` on strings can return early at the first differing byte; timing differences can leak how
many leading hex digits are right. `compare_digest` takes constant time.

**"Why check the timestamp first?"**
Cheap rejection of stale deliveries, and it keeps the error message precise. Either order is safe
as long as both checks happen; the tests pin "tolerance" first.

**"What about secret rotation and multiple v1 values?"**
Real gateways can send several `v1=` entries during rotation; accept if any matches any active
secret. The parser here keeps the last `v1`; a follow-up change would collect all of them.

**"What should dispatch do with unknown event types?"**
Ignore and return quickly (acknowledge with 2xx so the gateway does not retry forever), but log at
debug level. Unknown types are normal: providers add new event types without notice.

## Ledger

**"Why does can_refund exist separately from refund?"**
UI and API layers ask before acting (to show the refundable amount); `refund` must still enforce
the same rule itself, because callers can skip the check. Single source of truth: `refund` calls
`can_refund`.

**"What about concurrency?"**
Two refunds racing can both pass `can_refund`. With a database: a row lock / `SELECT ... FOR UPDATE`
or a conditional update (`UPDATE ... SET refunded = refunded + :a WHERE refunded + :a <= amount`).
In memory: a lock around check-and-mutate.

**"Should a pending charge be refundable?"**
No: nothing was captured. The spec here only bounds the amount; a stricter version would require
`status == "succeeded"`, worth raising as a question rather than silently changing.

## Process

**"You fixed 7 of 10; what would you do with 10 more minutes?"**
Name the remaining failures, the hypothesis for each, and the first command you would run. This
is graded as highly as the fixes themselves.
