#############################################################################
# construct_gallery module (example)
#############################################################################

import wx
from pkgutil import iter_modules
import construct_editor.gallery
from importlib import import_module
from construct_gallery import (
    ConstructGallery, GalleryItem, BleakScannerConstruct)
import construct as cs
from collections import OrderedDict
import sys


def bleak_main(args=None):
    app = wx.App(False)
    frame = wx.Frame(
        None, title="BleakScannerConstructFrame", size=(1000, 600))
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
        None, title="ConstructGalleryFrame", size=(1000, 600))
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
    if len(sys.argv) > 1:
        sys.exit(bleak_main())
    sys.exit(main())
