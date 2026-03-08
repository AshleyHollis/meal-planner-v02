# Audit Snapshot Pattern

## Problem
When tracking changes to mutable entities (like inventory items), relying on the *current* state of the entity to explain *past* changes is brittle. If an item is moved or its freshness basis changes, the historical adjustment record becomes ambiguous if it only records the delta.

## Solution
Store "before" and "after" snapshots of critical metadata directly on the adjustment/audit record. Do not rely on joins to the current entity to infer historical state.

## Implementation
In `InventoryAdjustment`:
```python
class InventoryAdjustment(Base):
    # ...
    quantity_before: Mapped[Optional[Decimal]]
    quantity_after: Mapped[Optional[Decimal]]
    
    # Snapshot location
    storage_location_before: Mapped[Optional[str]]
    storage_location_after: Mapped[Optional[str]]
    
    # Snapshot freshness state
    freshness_basis_before: Mapped[Optional[str]]
    expiry_date_before: Mapped[Optional[date]]
    freshness_basis_after: Mapped[Optional[str]]
    expiry_date_after: Mapped[Optional[date]]
```

## Benefits
1.  **Self-contained History:** Audit logs can be rendered without fetching the current item.
2.  **Ambiguity Resolution:** We know exactly *where* an item was when it was consumed, even if it has since been moved.
3.  **Debugging:** Easier to trace "how did we get here" when the audit log preserves the full state transition.
