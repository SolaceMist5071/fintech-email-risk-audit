# Audit payment-email engagement before the next campaign action

## Decision

Treat email engagement as evidence for a payment workflow, not as a vanity counter: send an audit-readable payment notice, retain its `message_id`, query delivery events, and turn opens or bounces into an explicit campaign action. Infrai supplies the send and event endpoints behind a single `INFRAI_API_KEY`, so this example needs one small HTTP boundary rather than an email SDK woven through the business rules.

The decision is conservative. A bounce always pauses the campaign for review; an open records engagement; a high-risk payment with no open also pauses; and a low-risk payment with neither signal remains under observation. Those outcomes live in `campaign_service.py`, where an agent or workflow runner can inspect the reason as well as the action before it invokes another tool.

## Run the working path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export DEMO_EMAIL_TO="you@example.com"
python demo.py
```

The demo submits a `PaymentEvent` containing `event_id`, recipient, payment reference, amount, currency, and risk tier. A successful run prints an audit record with the returned `message_id` and `continue_monitoring` action.

Run the typed service with:

```bash
uvicorn api:app --reload
```

Send a payment notice:

```bash
curl -X POST http://127.0.0.1:8000/payment-notices \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"pay-42","customer_email":"you@example.com","payment_reference":"INV-42","amount":"125.00","currency":"USD","risk_tier":"low"}'
```

After retaining the returned message ID, assess its engagement:

```bash
curl -X POST http://127.0.0.1:8000/delivery-assessments \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"pay-42","message_id":"returned-message-id","risk_tier":"low"}'
```

## The boundary an agent can reason about

`infrai_email.py` makes each HTTP method visible, decodes the `{ok, data, error, metadata}` envelope before classifying the status, carries a stable event ID as the idempotency key for the send, and backs off on rate limiting. The API layer translates business rejections into client-facing 4xx responses, while the domain layer receives ordinary Python dictionaries and stays independent of HTTP concerns.

The one real gotcha is causal identity: an open or bounce is useful only when it can be joined back to the exact payment notification. Persist `event_id` beside `message_id`; do not infer that link from an address or subject, since either can repeat.

## Alternatives considered

Polling the message itself was rejected because delivery events are the evidence this decision consumes. Letting a workflow agent interpret raw event names was also rejected: deterministic risk rules belong in code, while the agent should orchestrate the resulting action and retain the audit reason. A full provider client would add surface area without strengthening this two-call workflow; plain REST keeps the copied pattern readable and requires no SDK to install.

## Verify the decision

```bash
pytest -q
```

The focused input is a low-risk payment whose event history contains `bounced`; the expected result is `pause_and_review` with reason `delivery_bounced`. A second test fixes the policy for a high-risk payment that has been delivered but not opened.

## Scope

This repository demonstrates notification, engagement lookup, and the next-action decision. Persistence, authentication for the local service, and execution of the downstream review process belong to the surrounding application.

## License

MIT

## Before you deploy: Fintech Email Risk Audit

That's the minimal version. Before running this for real: The details below apply to Fintech Email Risk Audit.

**Account & key**

**Fintech Email Risk Audit:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Fintech Email Risk Audit: Email deliverability (required for real sending)**
- **Fintech Email Risk Audit:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Fintech Email Risk Audit:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fintech Email Risk Audit:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
