---
name: good-taste-linked-list
description: Linus' indirect-pointer linked list example transposed to Python — bad taste version with special-case branching vs good taste version using a sentinel node
topic: coding_style
sources:
  - url: https://github.com/mkirchner/linked-list-good-taste
    title: "mkirchner/linked-list-good-taste — annotated C version of Linus' example"
  - url: https://docs.python.org/3/tutorial/datastructures.html
    title: Python Data Structures tutorial (list / dict primitives)
---

## The original C example (background)

Linus' canonical "good taste" example (per mkirchner annotated repo) deletes an entry from a single-linked list. The bad-taste version has two branches: one for "is the entry the head?" and one for "is it in the middle?". The good-taste version uses a pointer-to-pointer (`Entry **indirect`) so head and middle share one code path. The `if` disappears, and so does an entire class of off-by-one bugs.

Python has no raw pointers, but the same **data-structure-first** insight transposes cleanly to two Pythonic alternatives:

1. **Sentinel node** — prepend a dummy head so every real node has a previous node. Removal logic stops needing to branch on "is this the head?".
2. **`enumerate` + index removal** — when the list is small and lookup-by-identity is acceptable, build the result without ever branching on position.

Both alternatives eliminate the special case the same way Linus' indirect pointer does in C: by **changing the shape so the special case stops existing**.

## Bad taste (Python)

This version uses a hand-built singly-linked list and branches on "is this the head?":

```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class Node:
    value: int
    next: Optional["Node"] = None


def remove_bad_taste(head: Optional[Node], target: int) -> Optional[Node]:
    if head is None:
        return None
    # Special case: target is at the head.
    if head.value == target:
        return head.next
    # Normal case: walk and unlink.
    prev = head
    cur = head.next
    while cur is not None:
        if cur.value == target:
            prev.next = cur.next
            return head
        prev = cur
        cur = cur.next
    return head
```

Count the special cases: empty list, head match, mid-list match. Three. Each is a separate test, each is a separate place a bug can hide. This is exactly the C bad-taste version.

## Good taste (Python) — sentinel node

Prepend a sentinel node so every real node has a parent. The "is this the head?" branch dissolves:

```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class Node:
    value: int
    next: Optional["Node"] = None


def remove_good_taste(head: Optional[Node], target: int) -> Optional[Node]:
    # Sentinel removes the "head?" special case — every real node now has a parent.
    sentinel = Node(value=0, next=head)
    prev = sentinel
    while prev.next is not None:
        if prev.next.value == target:
            prev.next = prev.next.next
            return sentinel.next
        prev = prev.next
    return sentinel.next
```

One loop, one branch (the value match), one return. No "is this the head?" case. The data structure (sentinel-augmented list) made the special case stop existing — the same transformation Linus' indirect pointer performs in C.

## When to use which

- **Bad taste version**: never. There is no scenario where the branching version is preferable; it is included only as a counterexample.
- **Sentinel version**: when you genuinely need a linked list shape (rare in Python — built-in `list` and `collections.deque` cover almost all cases).
- **`enumerate` + new-list version**: for almost everything else, since Python's built-in `list` is a dynamic array and rebuilding via comprehension is faster than node-by-node mutation.

The lesson is the data-structure shift, not the linked list itself. Carry it forward when you find yourself writing `if special_case: ... else: ...` — almost always, a better structure exists.
