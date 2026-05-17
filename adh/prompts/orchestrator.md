The Orchestrator is not a single LLM call — it's a LangGraph state machine. These are the routing guidelines its conditional edges must implement.

## State graph
START
  → scout (per saved search, scheduled)
  → researcher (parallel, max 5 concurrent)
  → qualifier
  → IF score < 60 → archive END
  → IF do_not_contact → archive END
  → writer
  → IF self_check fails → writer (retry, max 2 times) → archive if still failing
  → approval_queue (human gate)
  → IF approved → sender
  → IF edited → sender (with edited content)
  → IF rejected → log feedback, archive
  → sender
  → wait_for_reply (timeout 4 working days)
  → IF reply received → reply_handler
  → IF no reply within timeout → followup_writer (variant 1)
  → wait_for_reply (timeout 10 working days)
  → IF no reply → followup_writer (variant 2, final)
  → wait_for_reply (timeout 14 days)
  → IF no reply → archive END

## Persistence
Every state transition is persisted to PostgreSQL via LangGraph checkpointer. Resume-on-failure must work.

## Concurrency
- Scout: serial (rate limits)
- Researcher: max 5 parallel
- Qualifier/Writer: serial per lead (cheap)
- Sender: serial with daily cap (30/day during warm-up, then configurable)

## Observability
Every node emits LangSmith traces. Every transition writes to `audit_log` table with `(lead_id, from_state, to_state, timestamp, reason)`.

## Kill switch
A boolean flag `system.outreach_enabled` is checked before any send. If false — freeze, log, notify operator.
