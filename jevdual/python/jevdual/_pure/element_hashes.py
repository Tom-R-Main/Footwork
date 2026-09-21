"""Pure twin of the R3 port: batched element hashes.

For each node returns ``(element_hash, stable_hash, parent_branch_hash)`` exactly as
upstream computes them (SHA-256 over the parent branch path, static attributes
and ax name; first 16 hex chars as int). History replay depends on byte-equality.
"""

from __future__ import annotations

from collections.abc import Sequence

from browser_use.dom.views import EnhancedDOMTreeNode

HashTriple = tuple[int, int, int]


def element_hashes(nodes: Sequence[EnhancedDOMTreeNode]) -> list[HashTriple]:
    return [(n.element_hash, n.compute_stable_hash(), n.parent_branch_hash()) for n in nodes]
