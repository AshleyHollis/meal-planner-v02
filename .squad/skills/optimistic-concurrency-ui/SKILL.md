---
name: "optimistic-concurrency-ui"
description: "Standard pattern for handling optimistic concurrency conflicts in UI"
domain: "frontend-architecture"
confidence: "high"
source: "code-review"
---

## Context
The inventory system uses optimistic concurrency control. Mutations must include the last known version of the item. If the version on the server has changed, the API returns a 409 Conflict with a `stale_inventory_version` error code. The UI must handle this gracefully.

## Patterns

### Mutation Payload
All existing-item mutations must include `lastKnownVersion`.

### Error Handling
Catch 409 errors and check for `stale_inventory_version`. Display a user-friendly message that includes the new server version if available, and trigger a data reload.

## Examples

```typescript
// Correct: Handle 409 and show user-friendly message
try {
  await mutateInventory(householdId, {
    ...mutation,
    lastKnownVersion: item.serverVersion, // Must include version
  });
  await reload(); // Success: refresh data
} catch (error) {
  await reload(); // Always refresh to get latest state
  if (error instanceof ApiError && error.status === 409) {
    const detail = error.detail as InventoryConflictDetail;
    if (detail?.code === 'stale_inventory_version') {
      setMessage(`Conflict: Item has changed. Server version is ${detail.currentVersion}. Data reloaded.`);
      return;
    }
  }
  setMessage(error.message);
}
```

## Anti-Patterns
- **Ignoring Version:** Sending mutations without `lastKnownVersion` (will likely be rejected by API or overwrite data blindly if API allows).
- **Generic Error:** Treating 409 as a generic "Something went wrong" error without explaining the conflict or reloading data.
