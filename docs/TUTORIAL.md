# Build a corroborated due-diligence app on Telegraph

Thirty minutes, one file, no framework. You will end up with a CLI that buys the
same question from three independent miners, decides whether to trust the answer,
and leaves evidence a stranger can re-check.

This is the tutorial version of what Tina does. It uses the real devnode and spends
about six cents of test USDC.

## 0. What you need

- Python 3.10+
- A test wallet with escrow balance (see the README: mint test USDC, deposit into the
  Diamond that `/engine/v1/ask` settles to)
- No API keys. Telegraph miners are the API.

## 1. The shape of a paid call

Every ask is two HTTP requests. The first is refused on purpose:

```bash
curl -s -X POST https://devnode.telegraphprotocol.com/engine/v1/ask \
  -H 'Content-Type: application/json' -H 'User-Agent: my-agent/1.0' \
  -d '{"intent":"CRYPTO_PRICE_USD","params":{"symbol":"ETH"}}'
```

```json
{"error":"payment required","accepts":[{"scheme":"escrow","price":"$0.01", ...}]}
```

Send a User-Agent. Cloudflare refuses Python's default one with `403 error 1010`,
which looks like a ban and is not.

The challenge tells you the price, the network and a message template. Sign the
template with EIP-191, send the same body again with `X-PAYMENT`, and the node
answers. Escrow bills only a delivered answer, so a failed ask is free.

## 2. Pay from escrow in twenty lines

```python
import base64, json, secrets, time, urllib.request
from eth_account import Account
from eth_account.messages import encode_defunct

NODE = "https://devnode.telegraphprotocol.com"
UA = {"Content-Type": "application/json", "User-Agent": "my-agent/1.0"}

def post(path, payload, extra=None):
    headers = {**UA, **(extra or {})}
    req = urllib.request.Request(NODE + path, data=json.dumps(payload).encode(),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()

def ask(acct, intent, params):
    status, _, body = post("/engine/v1/ask", {"intent": intent, "params": params})
    if status != 402:
        return json.loads(body)

    accept = next(a for a in json.loads(body)["accepts"] if a["scheme"] == "escrow")
    price = float(accept["price"].lstrip("$"))
    now = int(time.time())
    auth = {"from": acct.address, "to": accept["payTo"],
            "value": str(int(price * 1e6)), "validAfter": str(now - 10),
            "validBefore": str(now + 55), "nonce": "0x" + secrets.token_hex(32)}
    message = (accept["extra"]["message"]
               .replace("{from}", auth["from"].lower())
               .replace("{nonce}", auth["nonce"])
               .replace("{validAfter}", auth["validAfter"])
               .replace("{validBefore}", auth["validBefore"]))
    sig = acct.sign_message(encode_defunct(text=message)).signature
    envelope = {"x402Version": 2, "scheme": "escrow", "network": accept["network"],
                "payload": {"signature": "0x" + sig.hex().removeprefix("0x"), "authorization": auth}}
    header = base64.b64encode(json.dumps(envelope).encode()).decode()
    status, headers, body = post("/engine/v1/ask", {"intent": intent, "params": params},
                                 {"X-PAYMENT": header})
    data = json.loads(body)
    return {"status": status, "result": data.get("result"),
            "cost_usd": data.get("cost_usd"), "signal_hash": data.get("signal_hash"),
            "receipt": headers.get("X-Payment-Response")}
```

Three details that cost an afternoon each if you get them wrong:

1. The message is rebuilt by the node with your wallet **lowercased**. Sign it the
   same way.
2. `value` is micro-USDC as a string (`"10000"`), and `validBefore` must be inside the
   node's two-minute window.
3. The receipt header is `X-Payment-Response`; HTTP header names are case-insensitive,
   so match case-insensitively or you will report "no receipt" for a paid call.

## 3. Ask the same question twice, then a third time

One miner's answer is an opinion. Pin different miners and compare:

```bash
curl -s "https://devnode.telegraphprotocol.com/api/miners?intent=CRYPTO_PRICE_USD&limit=10"
```

Pick three with a `rank`, ask each with `POST /engine/v1/ask/{minerId}`, and keep every
answer. That is the whole trick, and it is why the app can say something a
single-model tool cannot: *these three agreed to within 1%, so treat the number as
measured; these two disagreed by 40%, so treat it as unknown.*

Agreement rule that survives real data: numbers agree when they are within 1% of the
median, not when their strings match. Two miners returned `24873363.78` and one
`24873355` for the same pool; exact matching called that a disagreement.

## 4. Make missing data raise the risk

The most common mistake in a verification tool is treating "no answer" as "fine".

```python
if liquidity is None:
    risk += 20                     # not zero
    reasons.append("liquidity unavailable: slippage is unmeasured")

if len(values) < 2:
    risk += 35                     # a single source is not corroboration
    reasons.append("only one miner answered")
```

Then band the score: under 30 pass, 30-59 review, 60+ reject. A `REVIEW` that says
"one reading, no corroboration" is a better product than a confident `PASS` built on
one number.

## 5. Leave evidence, not claims

For every answer store: intent, params, miner id, `result`, `cost_usd`,
`X-Payment-Response` and `signal_hash`. The signal hash is the important one: the node
resolves it back to the payer, the miner and the timestamp, so anyone can check your
memo without trusting it.

```bash
curl -s https://devnode.telegraphprotocol.com/engine/v1/signal/<hash>
```

Write a memo with the verdict, the reasons, the cost, and the limits. Then a reviewer
can run it with a new input, check the number, inspect the receipt, break it, and
reproduce it: exactly what the Season II acceptance test asks for.

## 6. Cap the spending in code, not in a promise

```python
if price > MAX_PER_ASK:
    raise SystemExit("over the per-ask cap, nothing paid")
```

Caps belong before the signature, on the price the node quotes. A verification tool
that can spend without limit is a liability with a nice README.

## 7. What to build next

- A fourth workflow: `tina yield` was the weakest in practice because
  `CRYPTO_YIELD_RATE_GENERAL` is thinly supplied. Pick an intent with more rankings
  (`tina health <intent>` shows ranked miners) and the same pattern holds.
- Cache answers per intent for an hour: everything deterministic is charged per call.
- Compare against a truth source. `truth/` in this repo shows how to contribute one, and
  a truth source is what makes a deterministic intent scoreable at all.

The finished version, with tests and committed evidence, is this repository.
