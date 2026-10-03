# API Design Patterns

> When to read: when designing a REST or RPC endpoint surface: pagination, error envelopes, idempotency, versioning, contract-first vs code-first.

## Pagination

| Use case | Type | Why |
|----------|------|-----|
| Admin dashboards, <10K rows | Offset (`?page=2&limit=20`) | Users expect page numbers |
| Infinite scroll, feeds, large datasets | Cursor (`?cursor=abc&limit=20`) | Stable under concurrent writes |
| Search results | Offset | Users need "page 3 of 12" |

**Cursor implementation:**
```sql
SELECT * FROM items
WHERE id > :cursor_id
ORDER BY id ASC
LIMIT :limit + 1;  -- fetch N+1 to determine has_next
```

Response: `{ data, pagination: { next_cursor, has_next } }`. Base64 encodes cursor state but supplies no integrity. Validate decoded fields and bind the cursor to the authorized tenant, filters, and sort order. When cursor state must resist modification, authenticate it with a signature/MAC or use a server-stored opaque token. Always reapply authorization independently of cursor contents.

## Filtering

Bracket notation for comparison operators:
```
?price[gte]=10&price[lte]=100
?status[in]=active,pending
?customer.country=US          # dot notation for nested fields
```

Comma-separated for multi-value equality:
```
?category=electronics,clothing
```

## Sorting

Prefix `-` for descending, comma-separated for multi-field:
```
?sort=-created_at,name        # newest first, then alphabetical
```

## Sparse Fieldsets

```
?fields=id,name,email         # return only these fields
```

## Deprecation Protocol

1. Add `Sunset` header with retirement date: `Sunset: Sat, 01 Jan 2028 00:00:00 GMT`
2. Minimum 6-month notice before removal
3. After sunset: return `410 Gone` with migration guidance

**Breaking vs non-breaking changes:**

| Non-breaking (no new version) | Breaking (requires new version) |
|-------------------------------|--------------------------------|
| Adding optional fields/params | Removing or renaming fields |
| Adding new endpoints | Changing field types |
| Widening accepted input enum values | Removing endpoints |
| Relaxing validation | Tightening validation |
| Extending response with new keys | Changing response structure |

Adding an emitted response enum member is compatible only when existing clients demonstrably tolerate unknown members; closed validators and exhaustive switches can reject it. Verify client behavior before classifying that change as nonbreaking.

## Pre-Ship Endpoint Checklist

Before shipping any new endpoint, verify:

- [ ] Resource naming: plural nouns, max 2 nesting levels
- [ ] HTTP method matches semantics (GET reads, POST creates, etc.)
- [ ] Status codes correct (201 + Location on create, 204 on delete, 404 vs 400 distinction)
- [ ] Request validation with schema (rejects invalid input with 400 + detail)
- [ ] Response schema defined (controls serialized fields, no raw objects)
- [ ] Pagination on list endpoints (cursor or offset with has_next)
- [ ] Auth/authz enforced (401 vs 403 distinction)
- [ ] Rate limiting configured
- [ ] Error envelope matches project standard
- [ ] Idempotency for non-safe methods (POST with idempotency key where needed); see Idempotency Keys below
- [ ] External API responses validated before use
- [ ] OpenAPI/docs updated

## Idempotency Keys

Accepting an `Idempotency-Key` header is the easy half. Four things decide whether it works:

- **Derive the key from intent, not from the attempt.** `charge:v1:${orderId}` is stable across retries; `randomUUID()` or a timestamp generated per attempt gives every retry a fresh key and dedupes nothing. If the caller supplies the key, the caller has the same obligation; document it.
- **Claim the key atomically.** `INSERT` the key and let a unique constraint reject the duplicate. A read-to-check-then-write is the exact race the header exists to close: two concurrent retries both read "unused" and both proceed.
- **Reject key reuse with a different payload.** Store a hash of the request body beside the key and return 422 on mismatch. Without it, a client bug that reuses one key for two different charges gets the first charge's response for both, and the second charge silently never happens.
- **Decide what an in-flight duplicate gets.** The first request holds the claim and has not finished. Pick one and state it: 409 and let the client retry, block on the claim and return the same response, or 202 with a status URL. Leaving it undefined means the second request usually falls through and double-executes.

Treat every outbound call as three-way: success, failure, and **unknown** (timeout, connection reset after the request was sent). Record the intent before calling out, so an unknown outcome can be reconciled rather than guessed at. Set key retention to outlive the longest path that can replay the request, including a dead-letter queue drained days later; sizing it by storage cost rather than by replay window is how a "already processed" guarantee expires early.

## Webhook Acceptance

Verify the webhook signature against the required request bytes before accepting an event. Durably commit the verified event ID and complete payload as recoverable pending work before returning `2xx`. A durable queue can provide this guarantee; an additional inbox table is unnecessary when the queue already does. A duplicate event must preserve pending work and completed state. An event ID recorded before processing is an acceptance receipt, not proof that the business effect completed.

Reclaim expired worker leases after crashes. Keep failed work retryable or move exhausted attempts to an inspectable failure state. Mark the event complete only after the required effects succeed. Deduplicate each business operation across distinct event IDs as well as retries of the same event; a crash after fulfillment but before completion must not fulfill the order again.

Test storage failure before durable acceptance, duplicate delivery while pending, worker failure before the effect, and a crash after the effect but before completion. Verify recovery produces the required effect once. Return a retryable failure when durable acceptance fails; after `2xx`, recovery must work without depending on the provider sending the event again.
