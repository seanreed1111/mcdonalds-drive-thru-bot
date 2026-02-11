# ADR-004: Operator Overloading on Pydantic Domain Models

**Status:** Accepted

[Back to ADR Index](./adr.md)

---

## Context

The ordering system needs to support:
- Adding items to an order
- Merging duplicate items (same item with same modifiers should combine quantities, not create separate entries)
- Comparing items for equality based on business identity (not Python object identity)

These operations happen in the `update_order` node when processing tool results. The question is how to express these operations in code.

**Options considered:**
1. **Utility functions** — `add_item_to_order(order, item)`, `items_are_equal(a, b)`
2. **Methods on models** — `order.add_item(item)`, `item.matches(other)`
3. **Operator overloading** — `order + item`, `item_a == item_b`

## Decision

Use Python operator overloading (`__add__`, `__eq__`, `__hash__`) on Pydantic `BaseModel` subclasses for natural, Pythonic order manipulation.

### `Order.__add__(Item)` — Add item to order with duplicate merging

```python
# models.py:123-139

class Order(BaseModel):
    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    items: list[Item] = Field(default_factory=list)

    def __add__(self, other: object) -> "Order":
        if not isinstance(other, Item):
            return NotImplemented
        updated_items = list(self.items)
        for i, existing in enumerate(updated_items):
            if existing._is_same_item(other):
                updated_items[i] = existing + other   # Delegates to Item.__add__
                return Order(order_id=self.order_id, items=updated_items)
        updated_items.append(other)
        return Order(order_id=self.order_id, items=updated_items)
```

### `Item.__add__(Item)` — Merge quantities of same item

```python
# models.py:104-116

def __add__(self, other: object) -> "Item":
    if not isinstance(other, Item) or not self._is_same_item(other):
        return NotImplemented
    return Item(
        item_id=self.item_id,
        name=self.name,
        category_name=self.category_name,
        default_size=self.default_size,
        size=self.size,
        quantity=self.quantity + other.quantity,
        modifiers=list(self.modifiers),
        available_modifiers=list(self.available_modifiers),
    )
```

### `Item.__eq__` — Business identity, not object identity

```python
# models.py:60-68

def __eq__(self, other: object) -> bool:
    if not isinstance(other, Item):
        return NotImplemented
    return (
        self.item_id == other.item_id
        and self.name == other.name
        and self.category_name == other.category_name
        and set(self.modifiers) == set(other.modifiers)  # Order-independent
    )
```

Two items are "the same" when they share `item_id`, `name`, `category_name`, and the same set of `modifiers`. Size and quantity do not affect equality — an Egg McMuffin (small, qty 1) and an Egg McMuffin (small, qty 3) are the "same item" and should merge.

### Auto-size via model validator

```python
# models.py:54-58

@model_validator(mode="after")
def set_size_from_default(self) -> Self:
    if self.size is None:
        self.size = self.default_size
    return self
```

### Resulting usage in `update_order`

```python
current_order = current_order + new_item
# If Egg McMuffin (qty=1) exists and new_item is Egg McMuffin (qty=2):
#   -> single Egg McMuffin entry with qty=3
# If Hash Browns doesn't exist yet:
#   -> appended as new entry
```

**Why utility functions were rejected:**
- `add_item_to_order(order, item)` is less discoverable and separates logic from the models it operates on
- Encourages procedural style over object-oriented domain modeling

**Why methods were rejected:**
- `order.add_item(item)` implies mutation. Methods named `add` strongly suggest the object changes in place. The `+` operator has a well-understood immutable semantics in Python.

## Consequences

**Benefits:**
- Natural, readable syntax: `order + item` reads like English
- Immutable semantics: `__add__` returns new objects, never mutates — critical for LangGraph state management which tracks changes through returned values
- Business equality (`__eq__`) and hashability (`__hash__`) enable set operations on modifiers and correct deduplication
- `_is_same_item()` helper consolidates the identity check used by `__eq__`, `__add__`, and comparison operators

**Tradeoffs:**
- Operator overloading can be surprising to developers unfamiliar with the pattern
- `Order + Item` is asymmetric (`Order.__add__` accepts `Item`, not `Order`), which is unusual for `+`
- Custom `__eq__` and `__hash__` override Pydantic's defaults, requiring care to keep them consistent

---

[Back to ADR Index](./adr.md)
