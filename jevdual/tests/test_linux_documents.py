"""Mousepad-specific scope requires explicit path, retained app/window and file identity."""

import os
from dataclasses import replace
from types import SimpleNamespace

import pytest
from jevdual import linux_documents as documents
from jevdual.ax import AXError


@pytest.fixture
def world(monkeypatch, tmp_path):
    document = tmp_path / "document.txt"
    document.write_text("original\n")
    process = documents.ProcessIdentity(42, "start-1", "/usr/bin/mousepad", "mousepad", os.getuid())
    element = SimpleNamespace(chain=((":1.1", "/app"), (":1.1", "/window")), process_start="start-1")
    state = {"process": process, "title": str(document) + " - Mousepad", "element": element}
    monkeypatch.setattr(documents, "_process_identity", lambda pid: state["process"])
    monkeypatch.setattr(documents, "_window_title", lambda el: state["title"])
    monkeypatch.setattr(documents.linux_ax, "resolve", lambda *args: state["element"])
    return document, state


def test_explicit_owned_path_binds_without_persistence_claim(world):
    document, state = world
    binding = documents.bind(42, 123, document)
    assert binding.path == str(document)
    assert binding.file.inode == document.stat().st_ino
    assert binding.process == state["process"]
    assert binding.binding_basis == "mousepad_full_path_window_title"
    assert binding.persistence == "not_checked"
    documents.revalidate(binding)


@pytest.mark.parametrize("title", ["document.txt - Mousepad", "~/document.txt - Mousepad",
                                   "{path} - OtherApp", "**{path} - Mousepad", "{path} - Mousepad extra",
                                   "* {path} - Mousepad", "{path}* - Mousepad",
                                   "/different/document.txt - Mousepad"])
def test_unqualified_title_never_selects_document(world, title):
    document, state = world
    state["title"] = title.format(path=document)
    with pytest.raises(AXError) as error:
        documents.bind(42, 123, document)
    assert error.value.reason == "lost_identity"


def test_observed_leading_modified_marker_keeps_scoped_binding(world):
    document, state = world
    binding = documents.bind(42, 123, document)
    state["title"] = "*" + str(document) + " - Mousepad"
    documents.revalidate(binding)
    modified_binding = documents.bind(42, 123, document)
    assert modified_binding.file == binding.file
    assert modified_binding.persistence == "not_checked"
    assert document.read_text() == "original\n"
    state["title"] = str(document) + " - Mousepad"
    documents.revalidate(modified_binding)


def test_symlinks_and_missing_document_refuse(world, tmp_path):
    document, _state = world
    link = tmp_path / "link.txt"
    link.symlink_to(document)
    with pytest.raises(AXError, match="canonical"):
        documents.bind(42, 123, link)
    with pytest.raises(AXError, match="unavailable"):
        documents.bind(42, 123, tmp_path / "absent.txt")


def test_relative_and_control_path_refuse():
    for path in ("document.txt", "/tmp/a\nfile", "/tmp/a\x00file"):
        with pytest.raises(AXError):
            documents.bind(42, 123, path)


def test_directory_not_a_document(world, tmp_path):
    _document, state = world
    state["title"] = str(tmp_path) + " - Mousepad"
    with pytest.raises(AXError, match="regular file"):
        documents.bind(42, 123, tmp_path)


def test_process_restart_or_tab_switch_invalidates_retained_binding(world):
    document, state = world
    binding = documents.bind(42, 123, document)
    state["process"] = replace(state["process"], start="start-2")
    with pytest.raises(AXError, match="process"):
        documents.revalidate(binding)
    state["process"] = binding.process
    state["title"] = "/another/file - Mousepad"
    with pytest.raises(AXError, match="exact scoped path"):
        documents.revalidate(binding)


def test_replaced_inode_requires_new_binding(world, tmp_path):
    document, _state = world
    binding = documents.bind(42, 123, document)
    replacement = tmp_path / "replacement"
    replacement.write_text(document.read_text())
    replacement.replace(document)
    with pytest.raises(AXError, match="document changed"):
        documents.revalidate(binding)
    fresh = documents.bind(42, 123, document)
    assert fresh.file != binding.file
    assert fresh.persistence == "not_checked"


def test_nested_frame_or_changed_incarnation_is_not_top_level(world):
    document, state = world
    state["element"] = SimpleNamespace(chain=(1, 2, 3), process_start="start-1")
    with pytest.raises(AXError, match="top-level"):
        documents.bind(42, 123, document)
    state["element"] = SimpleNamespace(chain=(1, 2), process_start="start-2")
    with pytest.raises(AXError, match="original process"):
        documents.bind(42, 123, document)


@pytest.mark.parametrize("executable,name", [("/tmp/mousepad", "mousepad"),
                                            ("/usr/bin/mousepad", "other"), ("/usr/bin/other", "mousepad")])
def test_wrong_application_never_qualifies(monkeypatch, executable, name):
    import psutil

    class Process:
        def oneshot(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def create_time(self):
            return 123.0

        def exe(self):
            return executable

        def name(self):
            return name

        def uids(self):
            return SimpleNamespace(effective=os.getuid())

    monkeypatch.setattr(psutil, "Process", lambda pid: Process())
    with pytest.raises(AXError) as error:
        documents._process_identity(42)
    assert error.value.reason == "application_unqualified"
