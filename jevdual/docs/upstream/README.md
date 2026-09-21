# Upstream change drafts

Patches prepared against the pinned browser-use submodule (0.13.10, d8110c5). They are not
opened as pull requests from this repo; opening one is a separate, explicit step.

- `browser-use-drop-unused-node-uuid.patch`: removes `EnhancedDOMTreeNode.uuid`, a uuid7
  generated per DOM node and never read anywhere in the package (pinned by
  `tests/contract/test_upstream_seams.py::test_node_uuid_is_never_read_upstream`). Measured
  cost on the Wikipedia fixture: 22 ms per step for 14,860 nodes. jevdual carries the same
  effect locally as `patch.install_lazy_uuid()` until upstream takes it.
