"""P0: the footwork command's argument surface, without a Driver."""

from __future__ import annotations

from jevdual.cli import _paused_label, _secrets, _split, build_parser


def test_run_arguments_have_the_operator_defaults():
    args = build_parser().parse_args(
        ["run", "Do the thing", "--app", "Calculator", "--require", "a; b", "--authorize", "Save,Confirm"]
    )
    assert args.task == "Do the thing" and args.app == "Calculator"
    assert _split(args.require, ";") == ("a", "b") and _split(args.authorize, ",") == ("Save", "Confirm")
    assert args.steps == 20 and not args.no_s2 and args.url is None and args.out is None


def test_paused_reason_names_the_label_to_authorize():
    assert _paused_label("keyword 'delete' on click 'Delete account'") == "Delete account"
    assert _paused_label("judgment p=0.91 on menu 'File > Move to Trash'") == "File > Move to Trash"
    assert _paused_label("replaces 40 characters of existing content in 'text area'") == "text area"
    assert _paused_label("no quotes here") is None


def test_secrets_are_scoped_to_the_app_and_never_printed():
    store = _secrets(["sauce_password=hunter2"], "Google Chrome")
    assert store is not None and store.allowed_for("app://Google Chrome", "sauce_password")
    assert "hunter2" not in repr(store)
