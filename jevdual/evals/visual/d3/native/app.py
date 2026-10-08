"""Run-owned AppKit development fixture. Never opens or activates user documents."""

import json
import sys
from pathlib import Path

import AppKit as A


class Controller(A.NSObject):
    def pressed_(self, sender):
        state = dict(self.config)
        state["last_action"] = str(sender.title())
        if self.config["family"] == "document_identity":
            import shutil

            destination = self.directory / "selected.pdf"
            shutil.copyfile(self.directory / f"source-{sender.tag() + 1}.pdf", destination)
            state["selected_hash"] = __import__("hashlib").sha256(destination.read_bytes()).hexdigest()
        elif self.config["family"] == "crop_boundary":
            from PIL import Image

            state["saved_crop"] = (
                self.config["proposed_crop"] if sender.tag() == 0 else self.config["valid_crop"]
            )
            Image.open(self.directory / "view.png").crop(state["saved_crop"]).save(
                self.directory / "cropped.png"
            )
        else:
            output = self.directory / "export.txt"
            output.write_text("D3 fixture exported content\n")
            state["output_hash"] = __import__("hashlib").sha256(output.read_bytes()).hexdigest()
            state["phase"] = "complete"
        (self.directory / "effect.json").write_text(json.dumps(state))


def main():
    directory = Path(sys.argv[1])
    config = json.loads((directory / "config.json").read_text())
    app = A.NSApplication.sharedApplication()
    app.setActivationPolicy_(A.NSApplicationActivationPolicyAccessory)
    window = A.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        A.NSMakeRect(50, 80, 660, 440),
        A.NSWindowStyleMaskTitled | A.NSWindowStyleMaskClosable,
        A.NSBackingStoreBuffered,
        False,
    )
    window.setTitle_("D3 run-owned visual fixture")
    window.setReleasedWhenClosed_(False)
    controller = Controller.alloc().init()
    controller.config, controller.directory = config, directory
    content = window.contentView()
    label = A.NSTextField.labelWithString_(config["caption"])
    label.setFrame_(A.NSMakeRect(20, 388, 620, 40))
    content.addSubview_(label)
    image = A.NSImageView.alloc().initWithFrame_(A.NSMakeRect(20, 62, 620, 316))
    image.setImage_(A.NSImage.alloc().initWithContentsOfFile_(str(directory / "view.png")))
    image.setImageScaling_(A.NSImageScaleProportionallyUpOrDown)
    image.setAccessibilityLabel_(
        "Document previews" if config["family"] == "document_identity" else "Task canvas"
    )
    content.addSubview_(image)
    for index, title in enumerate(config["buttons"]):
        button = A.NSButton.alloc().initWithFrame_(A.NSMakeRect(20 + 200 * index, 15, 190, 32))
        button.setTitle_(title)
        button.setBezelStyle_(A.NSBezelStyleRounded)
        button.setTag_(index)
        button.setTarget_(controller)
        button.setAction_("pressed:")
        content.addSubview_(button)
    window.orderBack_(None)
    (directory / "ready.json").write_text(
        json.dumps({"window_id": int(window.windowNumber()), "pid": __import__("os").getpid()})
    )
    app.run()


if __name__ == "__main__":
    main()
