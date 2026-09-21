"""Native adapter for R3: batched element hashes.

Same signature and return type as the pure twin
``jevdual._pure.element_hashes.element_hashes(nodes) -> list[(element, stable, parent)]``.
The three strings upstream hashes are assembled here, byte for byte as
``EnhancedDOMTreeNode.__hash__``, ``compute_stable_hash`` and
``parent_branch_hash`` build them, and ``_core.element_hashes_flat`` hashes the
whole batch. ``element_hash`` upstream is ``hash(self)``: CPython returns ``__hash__``'s
int unchanged when it fits in ``Py_ssize_t`` and otherwise reduces it with the
integer hash (modulo 2**61 - 1), so that rule is applied to that one value.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from browser_use.dom.views import STATIC_ATTRIBUTES, NodeType, filter_dynamic_classes

from jevdual import _native

if TYPE_CHECKING:
    from browser_use.dom.views import EnhancedDOMTreeNode

HashTriple = tuple[int, int, int]
_available: bool | None = None
_PY_SSIZE_MAX = 2**63 - 1


def _slot_hash(value: int) -> int:
    """What ``hash(obj)`` returns when ``obj.__hash__()`` returns ``value`` (CPython slot_tp_hash)."""
    return value if value <= _PY_SSIZE_MAX else hash(value)


def available() -> bool:
    """True once the real R3 export is built (the placeholder takes no arguments)."""
    global _available
    if _available is None:
        core = _native.core
        try:
            _available = core is not None and core.element_hashes_flat([]) == []
        except (TypeError, NotImplementedError):
            _available = False
    return _available


def _parent_branch_path(node: EnhancedDOMTreeNode) -> str:
    tags: list[str] = []
    current = node
    while current is not None:
        if current.node_type == NodeType.ELEMENT_NODE:
            tags.append(current.tag_name)
        current = current.parent_node
    tags.reverse()
    return "/".join(tags)


def hash_strings(node: EnhancedDOMTreeNode) -> tuple[str, str, str]:
    """The (element, stable, parent-branch) strings upstream feeds to SHA-256."""
    branch = _parent_branch_path(node)
    attrs = node.attributes
    static_items = sorted((k, v) for k, v in attrs.items() if k in STATIC_ATTRIBUTES)
    attributes_string = "".join(f"{k}={v}" for k, v in static_items)

    filtered: dict[str, str] = {}
    for k, v in attrs.items():
        if k not in STATIC_ATTRIBUTES:
            continue
        if k == "class":
            v = filter_dynamic_classes(v)
            if not v:
                continue
        filtered[k] = v
    stable_attributes = "".join(f"{k}={v}" for k, v in sorted(filtered.items()))

    ax_name = f"|ax_name={node.ax_node.name}" if node.ax_node and node.ax_node.name else ""
    return f"{branch}|{attributes_string}{ax_name}", f"{branch}|{stable_attributes}{ax_name}", branch


def element_hashes(nodes: Sequence[EnhancedDOMTreeNode]) -> list[HashTriple]:
    inputs: list[str] = []
    for n in nodes:
        inputs.extend(hash_strings(n))
    digests = _native.core.element_hashes_flat(inputs)  # type: ignore[union-attr]
    out: list[HashTriple] = []
    for i in range(0, len(digests), 3):
        out.append((_slot_hash(digests[i]), digests[i + 1], digests[i + 2]))
    return out
