#############################################################################
# construct_gallery module (examples)
#############################################################################

import wx
from pkgutil import iter_modules
import construct_editor.gallery
from importlib import import_module
from construct_gallery import (
    ConstructGallery, GalleryItem, BleakScannerConstruct, ConfigEditorPanel)
from construct_editor.core.model import IntegerFormat
import construct as cs
from collections import OrderedDict
import sys
import argparse


def config_main(args=None):

    editing_structure = {
        0: {
            "name": "A string",
            "binary": b"My string",
            "construct": cs.Struct(
                "My string" / cs.GreedyString("utf8"),
            ),
            "read_only": False,
            "size": 130,
            "IntegerFormat": IntegerFormat.Hex,
        },
        1: {
            "name": "An unsigned integer",
            "binary": b'\x01\x00\x00\x00',
            "construct": cs.Struct(
                "Int32ul" / cs.Int32ul,
            ),
            "read_only": True,
            "size": 130,
            "IntegerFormat": IntegerFormat.Dec,
        },
        2: {
            "name": "Two numbers",
            "binary": b'\x00\x01\x01',
            "construct": cs.Struct(
                "Int16ub" / cs.Int16ub,
                "Int8ub" / cs.Int8ub
            ),
            "read_only": False,
            "size": 130,
            "IntegerFormat": IntegerFormat.Dec,
        },
    }

    app = wx.App(False)
    frame = wx.Frame(
        None, title="ConfigEditorPanelFrame demo", size=(1000, 600))
    frame.CreateStatusBar()
    main_panel = ConfigEditorPanel(frame,
        editing_structure=editing_structure,
        name_size=180,
        type_size=160,
        value_size=200)
    frame.Show(True)
    app.MainLoop()
    for char in main_panel.editor_panel:
        editing_structure[char][
            "new_binary"] = main_panel.editor_panel[char].binary
    for i in editing_structure:
        print(f'{i}: {editing_structure[i]["binary"]} --> '
            f'{editing_structure[i]["new_binary"]}')

def bleak_main(args=None):
    app = wx.App(False)
    frame = wx.Frame(
        None, title="BleakScannerConstructFrame demo", size=(1000, 600))
    frame.CreateStatusBar()
    main_panel = BleakScannerConstruct(frame)
    frame.Bind(wx.EVT_CLOSE, lambda event: on_close(main_panel, event))
    frame.Show(True)
    app.MainLoop()

def on_close(frame, event):
    frame.on_application_close()
    event.Skip()

def main(args=None):
    app = wx.App(False)
    frame = wx.Frame(
        None, title="ConstructGalleryFrame demo", size=(1000, 600))
    frame.CreateStatusBar()
    sample_modules = {
        submodule.name: import_module(
            "construct_editor.gallery." + submodule.name)
            for submodule in iter_modules(construct_editor.gallery.__path__,)
    }
    gallery_descriptor = {  
        "Signed little endian int (64, 32, 16, 8)": GalleryItem(
            construct=cs.Struct(
                "Int64sl" / cs.Int64sl,
                "Int32sl" / cs.Int32sl,
                "Int16sl" / cs.Int16sl,
                "Int8sl" / cs.Int8sl
            ),
            clear_log=True,
            example_bytes=OrderedDict(  # OrderedDict format
                [
                    ('A number', bytes.fromhex(
                        "15 81 e9 7d f4 10 22 11 d2 02 96 49 39 30 0c")),
                    ('All 1', bytes.fromhex(
                        "01 00 00 00 00 00 00 00 01 00 00 00 01 00 01")),
                    ('All 0', bytes(8 + 4 + 2 + 1)),
                ]
            )
        ),
        "Unsigned big endian int (16, 8)": GalleryItem(
            construct=cs.Struct(
                "Int16ub" / cs.Int16ub,
                "Int8ub" / cs.Int8ub
            ),
            clear_log=True,
            example_bytes={  # dictionary format
                "A number": bytes.fromhex("04 d2 7b"),
                "All 1": bytes.fromhex("00 01 01"),
                "All 0": bytes(2 + 1),
            },
        )
    }
    gallery_descriptor.update(
        {
            module : GalleryItem(
                        construct=sample_modules[module].gallery_item.construct,
                        contextkw=sample_modules[module].gallery_item.contextkw,
                        clear_log=True,
                        example_bytes=sample_modules[
                            module].gallery_item.example_binarys
                    )
            for module in sample_modules
        }
    )
    main_panel = ConstructGallery(frame, gallery_descriptor=gallery_descriptor)
    frame.Bind(wx.EVT_CLOSE, lambda event: on_close(main_panel, event))
    frame.Show(True)
    app.MainLoop()


if __name__ == "__main__":
    package = sys.modules[ConstructGallery.__module__].__package__
    parser = argparse.ArgumentParser(
        prog=package,
        description="Run as python3 -m %s ..." % package,
        epilog='%s demo programs' % package)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-g',
        "--gallery",
        dest='gallery',
        action='store_true',
        help="ConstructGallery demo (default)")
    group.add_argument(
        '-b',
        "--bleak",
        dest='bleak',
        action='store_true',
        help="BleakScannerConstruct demo")
    group.add_argument(
        '-c',
        "--config",
        dest='config',
        action='store_true',
        help="ConfigEditorPanel demo")
    args = parser.parse_args()

    if args.bleak:
        sys.exit(bleak_main())
    elif args.config:
        sys.exit(config_main())
    else:
        sys.exit(main())
