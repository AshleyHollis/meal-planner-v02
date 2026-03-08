---
name: "idempotency-scope"
description: "Idempotency keys must be scoped by tenant/household to prevent collisions"
domain: "backend-architecture"
confidence: "high"
source: "incident-review"
---

## Context
In multi-tenant systems (like household meal planners), clients may generate random IDs for operations. If these IDs are treated as globally unique for idempotency checks, a collision between two unrelated tenants can cause one tenant's operation to return the other's result, or be silently ignored.

## Patterns

### Compound Keys
Idempotency checks must use a compound key of `(tenant_id, client_mutation_id)`.
- **Good:** `SELECT * FROM receipts WHERE household_id = ? AND client_mutation_id = ?`
- **Bad:** `SELECT * FROM receipts WHERE client_mutation_id = ?`

### Testing for Collisions
Regression tests must explicitly create the "impossible" collision:
1. Create a mutation in Tenant A with ID `X`.
2. Create a mutation in Tenant B with ID `X`.
3. Assert both succeed and produce distinct results.
4. Assert that replay in Tenant A returns Tenant A's result, and replay in Tenant B returns Tenant B's result.

## Examples

```python
# Correct: Scope by household
def _receipt_key(self, household_id: str, client_mutation_id: str) -> tuple[str, str]:
    return (household_id, client_mutation_id)

# Test pattern
def test_idempotency_is_scoped(client):
    id = str(uuid.uuid4())
    resp1 = client.post(..., headers={"X-Household": "A"}, json={"id": id})
    resp2 = client.post(..., headers={"X-Household": "B"}, json={"id": id})
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() != resp2.json()
```

## Anti-Patterns
- **Global Idempotency Maps:** Storing receipts in a simple `dict[str, Receipt]` or a table with `client_mutation_id` as the primary key.
- **Assuming UUIDs Never Collide:** While statistically true for random generation, malicious clients or buggy clients (reusing hardcoded IDs) can trigger collisions. The system must be robust against this.

