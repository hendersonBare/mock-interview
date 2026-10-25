# KEY_BUGS: rep2_bug_squash_paykit (self-written paykit, walkthrough rebuild)

Ten fixed plants, one per failing visible test, in four groups. Line numbers refer to the
practice repo (bugged build). `patches/<id>.patch` turns the reference into reference+that plant
only (reference -> bugged direction); `fix_only/<id>.patch` applies to a fresh clone of the
practice repo and removes just that plant; `reference.patch` removes all ten.

| # | id | file:line | failing visible test | symptom in pytest |
|---|---|---|---|---|
| 1 | `b01_pagination_stops_early` | `paykit/gateway.py:93` | `tests/test_gateway.py::test_list_charges_follows_pagination` | `['ch_1001', 'ch_1002'] == [... 5 ids]` |
| 2 | `b02_retries_client_errors` | `paykit/gateway.py:67` | `tests/test_gateway.py::test_does_not_retry_client_error` | `assert 3 == 1` |
| 3 | `b03_idempotency_key_per_attempt` | `paykit/gateway.py:63` | `tests/test_gateway.py::test_retry_reuses_idempotency_key` | two different hex keys |
| 4 | `b04_convert_ignores_exponent` | `paykit/money.py:67-68` | `tests/test_money.py::test_convert_across_exponents` | `Money(150000, 'jpy') == Money(1500, 'jpy')` |
| 5 | `b05_add_mixes_currencies` | `paykit/money.py:54-57` (check missing after line 56) | `tests/test_money.py::test_add_rejects_currency_mismatch` | `DID NOT RAISE ValueError` |
| 6 | `b06_signature_payload_only` | `paykit/webhooks.py:45` | `tests/test_webhooks.py::test_verify_accepts_valid_signature` | `SignatureError: signature mismatch` |
| 7 | `b07_dispatch_wrong_key` | `paykit/webhooks.py:57` | `tests/test_webhooks.py::test_dispatch_routes_to_handler` | `assert [] == ['evt_9']` |
| 8 | `b08_balance_counts_unsettled` | `paykit/ledger.py:31` | `tests/test_ledger.py::test_balance_excludes_non_succeeded` | `assert 700 == 200` |
| 9 | `b09_refund_bound_original` | `paykit/ledger.py:37` | `tests/test_ledger.py::test_can_refund_blocks_over_refund` | `assert True is False` |
| 10 | `b10_refund_unvalidated` | `paykit/ledger.py:39-42` (guard missing after line 40) | `tests/test_ledger.py::test_refund_rejects_over_refund` | `DID NOT RAISE ValueError` |

Independence (verified, gate G3): fixing any one plant turns exactly its own test green and
leaves the other nine red; adding any one plant to the reference turns exactly its own test red.
The 9 passing tests guard behaviour each fix must keep (USD->EUR conversion, same-currency add,
case-insensitive currency codes, 500 retry until success, tampered payload rejected, timestamp
tolerance, refund accumulation, can_refund for the remaining amount).

Suggested order under time pressure: the one-liners with an obvious symptom first (7, 8, 2,
9, 10, 5), then 1 and 3 (need the request log), then 4 and 6 (need a small calculation).
Group by module so each file is read once.

---

## Gateway client

Model narration: "Three red tests in `test_gateway.py`. All three talk to the fake gateway, so
before reading code I run one with `-s` to see the request log: that tells me what actually
went over the wire. Then I compare the log with what the test expects."

### 1. `b01_pagination_stops_early`: `return` indented into the loop

- **Planted diff** (`paykit/gateway.py`, `list_charges`):
  ```diff
               if not page["has_more"]:
                   break
               query["starting_after"] = page["data"][-1]["id"]
  -        return charges
  +            return charges
  ```
- **Root cause:** the `return` sits inside `while True`, so the function returns right after it
  stores the cursor for page 2, i.e. after the first page whenever `has_more` is true. (When the
  first page is also the last, `break` skips the `return` and the function returns `None`, which
  the hidden tests catch.)
- **Minimal fix:** dedent `return charges` one level, back under `while`.
- **Localization path:** `pytest -q -s tests/test_gateway.py::test_list_charges_follows_pagination`
  shows exactly one `GET /v1/charges?limit=2 -> 200`, no second request with `starting_after`.
  So the loop body runs once: read the loop and look at what can leave it.
- **Regression tests:** visible `test_list_charges_follows_pagination`; hidden
  `test_hidden_p1_gateway.py::test_list_charges_returns_every_charge_for_any_page_size[1|2|3|6]`,
  `test_list_charges_default_page_size_still_returns_everything`,
  `test_list_charges_sends_last_id_as_cursor`, `test_list_charges_single_page`,
  `test_list_charges_empty_account`; neighbour (passes on both)
  `test_list_charges_first_request_uses_page_size_without_cursor`.

### 2. `b02_retries_client_errors`: every GatewayError is retried

- **Planted diff** (`paykit/gateway.py`, `_request`):
  ```diff
               except GatewayError as exc:
  -                if exc.status not in RETRYABLE_STATUS or attempt == MAX_ATTEMPTS:
  +                if attempt == MAX_ATTEMPTS:
                       raise
  ```
- **Root cause:** the retry decision ignores the status code, so a 400 (and 401, 404, ...) is sent
  `MAX_ATTEMPTS` times. `RETRYABLE_STATUS` is defined but no longer used in the module.
- **Minimal fix:** restore `exc.status not in RETRYABLE_STATUS or` in the condition.
- **Localization path:** `-s` on the test shows three `POST /rejecting/v1/charges -> 400`. The
  retry loop is the only place that sends the same request again; read the `except` branch.
  `git grep RETRYABLE_STATUS` shows it is only defined and exported, never consulted.
- **Strong-hire point:** a retried 4xx is not just wasteful. If the 400 came after a partial
  write, or the error is a 409/402, retrying can duplicate side effects; retries are only safe
  for "did not happen / try later" statuses (5xx, 429) and only with an idempotency key.
- **Regression tests:** visible `test_does_not_retry_client_error`; hidden
  `test_client_error_is_not_retried`, `test_not_found_is_not_retried`,
  `test_rejected_amount_is_not_retried`; neighbours (pass on both)
  `test_persistent_server_error_gives_up_after_max_attempts`, `test_rate_limited_request_is_retried`,
  `test_server_error_then_success_on_get`.

### 3. `b03_idempotency_key_per_attempt`: key generated inside the retry loop

- **Planted diff** (`paykit/gateway.py`, `_request`):
  ```diff
  +        idempotency_key = new_idempotency_key() if method == "POST" else None
           for attempt in range(1, MAX_ATTEMPTS + 1):
  -            idempotency_key = new_idempotency_key() if method == "POST" else None
               try:
  ```
  (shown in the fix direction: the bugged build has the line inside the loop at line 63.)
- **Root cause:** each attempt gets a fresh UUID, so the gateway cannot tell the retry is the same
  logical request and may create a second charge.
- **Minimal fix:** move the assignment above the `for` (one key per call, reused by every attempt;
  GET still sends none).
- **Localization path:** the test prints two different keys. `-s` shows `POST /flaky/... -> 500`
  then `-> 200`. Find where the header value is produced (`_do_request` only forwards
  `idempotency_key`), walk up to `_request`, notice the assignment's scope.
- **Strong-hire point:** the key identifies the *operation*, not the HTTP attempt; it must be
  stable across retries (and ideally supplied by the caller so it survives a process crash).
- **Regression tests:** visible `test_retry_reuses_idempotency_key`; hidden
  `test_retry_after_500_reuses_key`, `test_all_attempts_share_one_key`; neighbours (pass on both)
  `test_separate_charges_use_separate_keys`, `test_get_requests_carry_no_idempotency_key`,
  `test_requests_carry_auth_and_json_headers`.

## Money and currency

Model narration: "USD to EUR passes and USD to JPY is off by exactly 100. A factor of 100 is
10 to the power of the difference in decimal places, so I suspect minor units are being
treated as major units somewhere. Let me print the intermediate values."

### 4. `b04_convert_ignores_exponent`: rate applied to raw minor units

- **Planted diff** (`paykit/money.py`, `convert`):
  ```diff
  -        usd = self.to_decimal() / rate_for(rates, self.currency)
  -        amount = usd * rate_for(rates, to_currency)
  -        minor = amount.scaleb(EXPONENT[to_currency])
  +        usd = Decimal(self.minor_units) / rate_for(rates, self.currency)
  +        minor = usd * rate_for(rates, to_currency)
  ```
- **Root cause:** the rate (units per 1 USD) is a ratio of *major* units, but it is applied to
  minor units and the result is used as minor units of the target. That is only correct when
  both currencies have the same exponent: 1000 cents * 150 = 150000 "yen" instead of
  10.00 USD * 150 = 1500 yen.
- **Minimal fix:** go through the real amount and re-scale: either restore the three lines, or
  keep the two lines and use `self.to_decimal()` plus `.scaleb(EXPONENT[to_currency])` on the
  result (equivalently multiply by `10 ** (EXPONENT[to] - EXPONENT[from])`).
- **Localization path:** `pytest -q tests/test_money.py::test_convert_across_exponents --pdb`,
  `p usd, minor` inside `convert`. Compare with `Money(1000, "usd").to_decimal()` (`10.00`).
  `EXPONENT` is defined at the top of the file and not used in `convert`.
- **Strong-hire point:** yen and dollars use different exponents (JPY 0, USD 2, KWD 3); a test with
  only two-decimal currencies hides this. Mention rounding half-up at the target unit.
- **Regression tests:** visible `test_convert_across_exponents`; hidden
  `test_hidden_p1_money.py::test_convert_respects_minor_unit_exponents[usd-jpy|jpy-usd|usd-kwd|kwd-jpy|jpy-kwd|one-cent-rounds-half-up]`,
  `test_convert_accepts_uppercase_target`; neighbours (pass on both)
  `test_convert_between_two_decimal_currencies[usd-gbp|eur-usd|same-currency]`.

### 5. `b05_add_mixes_currencies`: currency check removed from `__add__`

- **Planted diff** (`paykit/money.py`, `__add__`):
  ```diff
           if not isinstance(other, Money):
               return NotImplemented
  -        if other.currency != self.currency:
  -            raise ValueError(f"cannot add {other.currency} to {self.currency}")
           return Money(self.minor_units + other.minor_units, self.currency)
  ```
- **Root cause:** the sum silently keeps the left operand's currency.
- **Minimal fix:** put the two-line guard back (raise `ValueError` on mismatch).
- **Localization path:** the test is a one-liner; read `Money.__add__`.
- **Regression tests:** visible `test_add_rejects_currency_mismatch`; hidden
  `test_adding_different_currencies_raises[usd-eur|eur-usd|jpy-kwd]`; neighbours (pass on both)
  `test_add_ignores_case_of_currency_code`, `test_add_non_money_is_type_error`.

## Webhooks

Model narration: "Bad signature and stale timestamp are rejected correctly, but a good
signature is rejected too, so the comparison itself works and the expected value is wrong. The
test signs `f'{t}.{payload}'`; let me see what the library signs."

### 6. `b06_signature_payload_only`: HMAC over the body without the timestamp

- **Planted diff** (`paykit/webhooks.py`, `verify_signature`):
  ```diff
  -    signed_payload = f"{timestamp}.{payload}"
  -    expected = hmac.new(
  -        secret.encode(), signed_payload.encode(), hashlib.sha256
  -    ).hexdigest()
  +    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
  ```
- **Root cause:** the sender signs `"<t>.<body>"` (module docstring and ISSUE say so); the
  verifier signs only the body, so no genuine signature can ever match. (Also a security
  issue if "fixed" the other way: without the timestamp in the MAC, an attacker could replay an
  old body with a fresh `t=`.)
- **Minimal fix:** sign `f"{timestamp}.{payload}"` (black wraps the call over three lines).
- **Localization path:** `--pdb` at the SignatureError, `p expected, signature`; recompute in the
  debugger with `hmac.new(secret.encode(), f"{timestamp}.{payload}".encode(), hashlib.sha256).hexdigest()`
  and see it equals `signature`.
- **Strong-hire point:** the signed string must match byte for byte what the sender signed; keep
  `compare_digest` and the tolerance check before the MAC.
- **Regression tests:** visible `test_verify_accepts_valid_signature`; hidden
  `test_valid_signature_returns_event`, `test_valid_signature_with_bytes_payload`,
  `test_valid_signature_at_tolerance_edge`, `test_signature_over_body_alone_is_rejected`,
  `test_dispatch_verified_event_end_to_end`; neighbours (pass on both) `test_wrong_secret_is_rejected`,
  `test_replayed_signature_with_new_timestamp_is_rejected`,
  `test_stale_timestamp_rejected_before_signature_check`.

### 7. `b07_dispatch_wrong_key`: handler looked up under `event_type`

- **Planted diff** (`paykit/webhooks.py`, `dispatch`):
  ```diff
  -    handler = handlers.get(event.get("type"))
  +    handler = handlers.get(event.get("event_type"))
  ```
- **Root cause:** events carry their type in `"type"`; `.get("event_type")` is `None`, so no
  handler matches and dispatch returns `None` silently.
- **Minimal fix:** `"event_type"` -> `"type"`.
- **Localization path:** `p handler` / `p event` in `dispatch`; the docstring says `event["type"]`.
- **Regression tests:** visible `test_dispatch_routes_to_handler`; hidden
  `test_dispatch_returns_handler_result`, `test_dispatch_uses_type_field_only`,
  `test_dispatch_verified_event_end_to_end`; neighbour (passes on both)
  `test_dispatch_unknown_type_returns_none`.

## Ledger

Model narration: "Three ledger failures. 700 vs 200 is exactly the failed 500 charge added on
top, so balance is counting it. The refund ones: can_refund says yes to 300 when only 200 is left,
and refund does not raise at all, even for more than the original amount, so those are two
different problems."

### 8. `b08_balance_counts_unsettled`: status filter dropped

- **Planted diff** (`paykit/ledger.py`, `balance`):
  ```diff
  -            if charge.status == "succeeded" and charge.currency == currency
  +            if charge.currency == currency
  ```
- **Root cause / fix:** failed and pending charges never collected money; restore the
  `status == "succeeded"` condition.
- **Localization path:** 700 - 200 = 500 = the failed charge. Read the generator in `balance`.
- **Regression tests:** visible `test_balance_excludes_non_succeeded`; hidden
  `test_balance_ignores_unsettled_status[failed|pending|canceled]`,
  `test_balance_nets_refunds_of_succeeded_only`; neighbour (passes on both)
  `test_balance_filters_by_currency`.

### 9. `b09_refund_bound_original`: bound by the original amount

- **Planted diff** (`paykit/ledger.py`, `can_refund`):
  ```diff
           charge = self.get(charge_id)
  -        remaining = charge.amount - charge.refunded
  -        return 0 < amount <= remaining
  +        return 0 < amount <= charge.amount
  ```
- **Root cause / fix:** earlier refunds are ignored; compare against `amount - refunded`.
- **Localization path:** test builds the charge with `refunded=800`; `p charge` in `can_refund`.
- **Regression tests:** visible `test_can_refund_blocks_over_refund`; hidden
  `test_can_refund_bounded_by_remaining[201-False|300-False]`,
  `test_fully_refunded_charge_cannot_be_refunded`, `test_refunds_through_api_accumulate_toward_limit`;
  neighbours (pass on both) `test_can_refund_bounded_by_remaining[1-True|200-True]`.

### 10. `b10_refund_unvalidated`: refund mutates without checking

- **Planted diff** (`paykit/ledger.py`, `refund`):
  ```diff
       def refund(self, charge_id, amount):
           """Refund part of a charge and return the new refunded total."""
  -        if not self.can_refund(charge_id, amount):
  -            raise ValueError(f"cannot refund {amount} on {charge_id}")
           charge = self.get(charge_id)
           charge.refunded += amount
  ```
- **Root cause / fix:** any amount (0, negative, more than charged) is accepted; restore the
  guard that calls `can_refund` and raises `ValueError` before mutating.
- **Localization path:** the visible test refunds 1200 on a fresh 1000 charge, so it does not
  depend on #9; read `refund`.
- **Regression tests:** visible `test_refund_rejects_over_refund`; hidden
  `test_refund_rejects_invalid_amount_and_keeps_state[0|-5|1001]`,
  `test_refunds_through_api_accumulate_toward_limit`; neighbour (passes on both)
  `test_refund_exact_remaining_amount`.

---

## Method the walkthrough describes (what good looks like)

1. Run the suite, read the short summary as a map: 10 red tests, 4 modules, group them.
2. Take one failing test, rerun only it, read the assertion and the real values.
3. Reproduce in the debugger or a two-line script; confirm the hypothesis before editing.
4. Make the smallest change that explains the values; rerun that test, then the whole suite.
5. Narrate each step and summarize the fix in one sentence.

## Strong-hire signals

- Explains why retrying a 4xx can duplicate writes, and why the idempotency key must be stable
  across retries (and why GET needs none).
- Spots that yen and dollars use different exponents (factor 100 = 10^(2-0)).
- States that the signed string must match exactly what the sender signed, keeps
  `compare_digest` and the tolerance-first order.
- Separates #9 from #10 (different symptoms, independent tests) instead of one big change.
- Uses `-s` to read the fake gateway's request log rather than guessing.

## No-hire traps

- Editing a test, `tests/dummy_gateway.py`, `data/` or `pytest.ini` to get green.
- Rewriting a module (e.g. replacing the retry loop or the Money class) instead of a 1-3 line fix.
- Guessing without reproducing: e.g. "fixing" #4 by dividing by 100, which breaks KWD and
  JPY -> USD (hidden tests), or "fixing" #6 by dropping the timestamp check.
- Catching `GatewayError` around the whole loop or removing `MAX_ATTEMPTS`.

## Hidden tests

`hidden_tests/test_hidden_p1_{gateway,money,webhooks,ledger}.py` (61 cases) with their own server
`hidden_tests/hidden_gateway_server.py` (seven embedded charges, extra `/down/` and `/throttled/`
modes). 41 fail on the practice repo, 61 pass after `reference.patch`. Every plant alone makes at
least two hidden cases fail; every group has neighbours that pass on both builds.
