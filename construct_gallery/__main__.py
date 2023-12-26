#############################################################################
# construct_gallery module (main)
#############################################################################

import wx
from pkgutil import iter_modules
import construct_editor.gallery
from importlib import import_module
from construct_gallery import (
    ConstructGallery, GalleryItem, ConfigEditorPanel
)
from construct_editor.core.model import IntegerFormat
import construct as cs
from collections import OrderedDict
import sys
import argparse
import importlib.util
try:
    import bleak.uuids
    from construct_gallery import BleakScannerConstruct
except ImportError:
    class BleakScannerConstruct:
        BLEAK_IS_USED = False  # it means invalid class and black not installed


class SDBleakScannerConstruct(BleakScannerConstruct):
    def bleak_advertising(self, device, advertisement_data):
        if advertisement_data.service_data:
            for name, data in advertisement_data.service_data.items():
                str_name = bleak.uuids.uuidstr_to_str(name)
                self.add_packet_frame(
                    data=data,
                    append_label=str_name,
                    date_separator=" | ",
                    reference=device.address,
                )


def config_app(construct_module):

    if construct_module:
        editing_structure = construct_module.editing_structure
    else:
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
    width, height = wx.GetDisplaySize()
    title = "ConfigEditorPanelFrame demo"
    if construct_module:
        title = "Config Editor - " + construct_module.__file__
    frame = wx.Frame(
        None,
        pos=(int(width * 5 / 100), int(height * 5 / 100)),
        title=title,
        size=(int(width * 90 / 100), int(height * 90 / 100))
    )
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

def bleak_app(construct_module):
    app = wx.App(False)
    width, height = wx.GetDisplaySize()
    title = "BleakScannerConstructFrame demo"
    if construct_module:
        title = "BLE Advertising Editor - " + construct_module.__file__
    else:
        construct_module = {
            "Bytestream": GalleryItem(construct=cs.GreedyRange(cs.Byte)),
            "Bytearray": GalleryItem(construct=cs.GreedyBytes),
            "UTF8 string": GalleryItem(construct=cs.GreedyString("utf8")),
        }
    frame = wx.Frame(
        None,
        pos=(int(width * 5 / 100), int(height * 5 / 100)),
        title=title,
        size=(int(width * 90 / 100), int(height * 90 / 100))
    )
    frame.CreateStatusBar()
    main_panel = SDBleakScannerConstruct(
        frame, gallery_descriptor=construct_module
    )
    frame.Bind(wx.EVT_CLOSE, lambda event: on_close(main_panel, event))
    frame.Show(True)
    app.MainLoop()

def on_close(frame, event):
    frame.on_application_close()
    event.Skip()

def gallery_app(construct_module):
    app = wx.App(False)
    width, height = wx.GetDisplaySize()
    title = "ConstructGalleryFrame demo"
    if construct_module:
        title = "Construct Gallery Editor - " + construct_module.__file__
    frame = wx.Frame(
        None,
        pos=(int(width * 5 / 100), int(height * 5 / 100)),
        title=title,
        size=(int(width * 90 / 100), int(height * 90 / 100))
    )
    frame.CreateStatusBar()
    if construct_module:
        gallery_descriptor = construct_module
    else:
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
        sample_modules = {
            submodule.name: import_module(
                "construct_editor.gallery." + submodule.name
            )
            for submodule in iter_modules(construct_editor.gallery.__path__,)
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

def ble_main():
    return main(True)

def main(run_bleak=False):
    package = sys.modules[ConstructGallery.__module__].__package__
    parser = argparse.ArgumentParser(
        prog=package,
        description="Run as python3 -m %s ..." % package,
        epilog='%s utility' % package)
    parser.add_argument(
        "construct_module",
        type=argparse.FileType('r'),
        help="construct Python module",
        default=0,
        nargs='?',
        metavar='CONSTRUCT_MODULE')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-g',
        "--gallery",
        dest='gallery',
        action='store_true',
        help="ConstructGallery demo (default)")
    if BleakScannerConstruct.BLEAK_IS_USED:
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
    construct_module = None
    if args.construct_module:
        spec = importlib.util.spec_from_file_location(
            name=args.construct_module.name,
            location=args.construct_module.name
        )
        if not spec:
            print("Not a Python module:", args.construct_module.name)
            sys.exit(2)
        try:
            construct_module = importlib.util.module_from_spec(spec)
        except Exception as e:
            print("Cannot identify module:", str(e), s)
            sys.exit(2)
        sys.modules['construct_module'] = construct_module
        try:
            spec.loader.exec_module(construct_module)
        except Exception as e:
            print("Construct module import error:", str(e))
            sys.exit(2)

    if BleakScannerConstruct.BLEAK_IS_USED and (args.bleak or run_bleak):
        sys.exit(bleak_app(construct_module))
    elif args.config:
        sys.exit(config_app(construct_module))
    else:
        sys.exit(gallery_app(construct_module))


if __name__ == "__main__":
    main()
