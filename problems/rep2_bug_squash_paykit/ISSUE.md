# Open issues

Reports filed by teams using paykit since the last round of changes. Each one has
a short repro written against the public API. Amounts are integers in the
currency's minor unit (cents, yen, fils).

## Gateway client

### Only part of our charge history comes back

We sync every charge into our warehouse each night. Since upgrading, the sync
only ever sees the first couple of charges.

```python
gateway = PaymentGateway(base_url, api_key)
charges = gateway.list_charges(limit=2)
print([c.id for c in charges])
```

Expected: every charge on the account (five in the sandbox account).
Actual: `['ch_1001', 'ch_1002']`. The page size seems to have become a cap.

### Declined requests are sent three times

When the gateway refuses a request as invalid (HTTP 400), our gateway logs
show the same POST arriving three times before the client gives up.

```python
try:
    gateway.create_charge(500, "usd")   # the gateway answers 400
except GatewayError as exc:
    print(exc.status)
```

Expected: one request, then `GatewayError` with status 400.
Actual: three identical requests, then `GatewayError`. Our risk team worries
this could double-submit writes that partially went through.

### A retried charge is not recognised as a retry

During a gateway incident a charge got a 500 on the first try and succeeded on
the second. The gateway treated the second attempt as a brand new charge.
Looking at the request log, the two attempts carried different
`Idempotency-Key` headers.

Expected: every attempt of one `create_charge` call sends the same
`Idempotency-Key`.
Actual: each attempt sends a new one.

## Money and currency

### Converting dollars to yen is off by a factor of 100

```python
rates = load_rates()
print(Money(1000, "usd").convert("jpy", rates))   # $10.00, rate 150 JPY per USD
```

Expected: `Money(1500, 'jpy')`.
Actual: `Money(150000, 'jpy')`. Dollar to euro looks right, so it seems to
happen only between currencies with a different number of decimal places.

### Adding dollars and euros does not complain

```python
total = Money(1000, "usd") + Money(1000, "eur")
print(total)
```

Expected: `ValueError`; amounts in different currencies cannot be added.
Actual: `Money(2000, 'usd')`, silently.

## Webhooks

### Correctly signed webhooks are rejected

Every webhook from the gateway now fails verification, even though the secret
is right and the delivery is fresh. We double-checked by signing a payload
ourselves the way the gateway documents it: HMAC-SHA256 with the endpoint
secret over the timestamp, a dot, and the raw body.

```python
header = f"t={t},v1={hex_hmac_sha256(secret, f'{t}.{body}')}"
verify_signature(body, header, secret, now=t + 10)
```

Expected: the parsed event is returned.
Actual: `SignatureError: signature mismatch`.

### Handlers registered with `dispatch` never run

```python
seen = []
dispatch({"id": "evt_9", "type": "charge.refunded"},
         {"charge.refunded": lambda event: seen.append(event["id"])})
print(seen)
```

Expected: `['evt_9']`.
Actual: `[]`, and `dispatch` returns `None` as if no handler matched.

## Ledger

### Balance includes money we never collected

```python
ledger = Ledger([
    Charge("ch_a", 1000, "usd", "succeeded", refunded=800),
    Charge("ch_b", 500, "usd", "failed"),
])
print(ledger.balance())
```

Expected: `200` (only the succeeded charge counts, net of its refunds).
Actual: `700`.

### Over-refunds are allowed

Two related reports from the support tooling team:

```python
ledger = Ledger([Charge("ch_a", 1000, "usd", "succeeded", refunded=800)])
print(ledger.can_refund("ch_a", 300))   # only 200 is left to refund
```

Expected: `False`. Actual: `True`.

```python
ledger = Ledger([Charge("ch_a", 1000, "usd", "succeeded")])
ledger.refund("ch_a", 1200)
```

Expected: `ValueError` (1200 is more than the charge itself).
Actual: no error, and the charge now shows 1200 refunded.
