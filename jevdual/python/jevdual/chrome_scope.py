"""Read Chrome's trusted toolbar separately from the page accessibility snapshot.

The SDK can truncate a page without losing the browser toolbar. That is not proof
that the toolbar is complete: this producer walks the bound AX window itself,
stops at every web area, and records failures rather than silently dropping nodes.
It performs no input and supplies no delivery or task-success evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from . import ax

METHOD = "chrome.ax-toolbar/v1"
_ADDRESS_NAME = "Address and search bar"
_FIELD_ROLES = frozenset({"AXTextField", "AXComboBox"})


class _Reader(Protocol):
    def key(self, element: Any) -> int: ...
    def attributes(self, element: Any) -> frozenset[str]: ...
    def read(self, element: Any, name: str) -> Any: ...


class _AXReader:
    def key(self, element: Any) -> int:
        import objc

        return int(objc.pyobjc_id(element))

    def attributes(self, element: Any) -> frozenset[str]:
        from ApplicationServices import AXUIElementCopyAttributeNames

        error, names = AXUIElementCopyAttributeNames(element, None)
        if error or names is None:
            raise ax.AXError("scope_read_failed", f"AX attribute inventory refused ({error})")
        return frozenset(str(name) for name in names)

    def read(self, element: Any, name: str) -> Any:
        from ApplicationServices import AXUIElementCopyAttributeValue

        error, value = AXUIElementCopyAttributeValue(element, name, None)
        if error:
            raise ax.AXError("scope_read_failed", f"{name} refused ({error})")
        return value


@dataclass(frozen=True)
class AddressBar:
    value: str | None
    role: str
    identifier: str | None
    ancestry: tuple[str, ...]


@dataclass(frozen=True)
class ChromeScopeEvidence:
    pid: int
    window_id: int
    method: str
    complete: bool
    visited: int
    excluded_web_areas: int
    address_bars: tuple[AddressBar, ...]
    errors: tuple[str, ...]

    def to_record(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "address_bars": [{**asdict(bar), "ancestry": list(bar.ancestry)} for bar in self.address_bars],
            "errors": list(self.errors),
        }


def capture(pid: int, window_id: int, *, max_nodes: int = 2048, max_depth: int = 32) -> ChromeScopeEvidence:
    """Capture the exact bound native window; AX lookup/read failures fail closed."""
    try:
        root = ax.window_element(pid, window_id)
    except ax.AXError as error:
        return ChromeScopeEvidence(pid, window_id, METHOD, False, 0, 0, (), (error.reason,))
    return capture_tree(
        root, pid=pid, window_id=window_id, reader=_AXReader(), max_nodes=max_nodes, max_depth=max_depth
    )


def capture_tree(
    root: Any,
    *,
    pid: int,
    window_id: int,
    reader: _Reader,
    max_nodes: int = 2048,
    max_depth: int = 32,
) -> ChromeScopeEvidence:
    """Strict, bounded traversal, injectable for platform-independent contract tests.

    Only fields under a native AXToolbar and outside all AXWebArea descendants
    can supply the URL. Names are deliberately limited to the observed English
    Chrome contract; an unknown localization refuses rather than guessing.
    """
    if type(max_nodes) is not int or max_nodes < 1 or type(max_depth) is not int or max_depth < 0:
        raise ValueError("positive node budget and nonnegative depth budget required")
    stack: list[tuple[Any, tuple[str, ...]]] = [(root, ())]
    seen: set[int] = set()
    # AXChildren creates transient CF wrappers. Keep each inspected object alive
    # for this capture so a released wrapper's pointer cannot be recycled and
    # mistaken for a repeated element later in the same traversal.
    retained: list[Any] = []
    bars: list[AddressBar] = []
    errors: list[str] = []
    excluded = 0
    while stack:
        if len(seen) >= max_nodes:
            errors.append("node_limit")
            break
        element, ancestry = stack.pop()
        if len(ancestry) > max_depth:
            errors.append("depth_limit")
            break
        try:
            retained.append(element)
            key = reader.key(element)
            if key in seen:
                errors.append("repeated_element")
                break
            seen.add(key)
            names = reader.attributes(element)
            if "AXRole" not in names:
                errors.append("role_missing")
                break
            role = reader.read(element, "AXRole")
            if not isinstance(role, str) or not role:
                errors.append("role_invalid")
                break
            if not ancestry and role != "AXWindow":
                errors.append("window_role_invalid")
                break
            if role == "AXWebArea":
                excluded += 1
                continue
            if role in _FIELD_ROLES and "AXToolbar" in ancestry:
                labels = tuple(
                    reader.read(element, name) for name in ("AXTitle", "AXDescription") if name in names
                )
                if _ADDRESS_NAME in labels:
                    value = reader.read(element, "AXValue") if "AXValue" in names else None
                    identifier = reader.read(element, "AXIdentifier") if "AXIdentifier" in names else None
                    bars.append(
                        AddressBar(
                            value if isinstance(value, str) else None,
                            role,
                            identifier if isinstance(identifier, str) else None,
                            ancestry,
                        )
                    )
            if "AXChildren" in names:
                children = reader.read(element, "AXChildren")
                if children is None or isinstance(children, (str, bytes)):
                    errors.append("children_invalid")
                    break
                try:
                    if len(children) > max_nodes:
                        errors.append("node_limit")
                        break
                    children = tuple(children)
                except TypeError:
                    errors.append("children_invalid")
                    break
                stack.extend((child, (*ancestry, role)) for child in reversed(children))
        except ax.AXError as error:
            errors.append(error.reason)
            break
    return ChromeScopeEvidence(
        pid, window_id, METHOD, not errors, len(seen), excluded, tuple(bars), tuple(errors)
    )
