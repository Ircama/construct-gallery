#############################################################################
# construct_gallery module (main)
#############################################################################

import re
from pkgutil import iter_modules
from importlib import import_module
from collections import OrderedDict
import sys
import argparse
import logging
import importlib.util
import wx
import construct as cs
import construct_editor.gallery
from construct_gallery import (
    ConstructGallery, GalleryItem, ConfigEditorPanel, BleakScannerConstruct
)
from construct_editor.core.model import IntegerFormat
try:
    import bleak.uuids
except ImportError:
    pass


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
    title = "Config Editor"
    if construct_module:
        title += " - " + construct_module.__file__
    frame = wx.Frame(
        None,
        pos=(int(width * 5 / 100), int(height * 5 / 100)),
        title=title,
        size=(int(width * 90 / 100), int(height * 90 / 100))
    )
    frame.CreateStatusBar()
    main_panel = ConfigEditorPanel(
        frame,
        editing_structure=editing_structure,
        name_size=180,
        type_size=160,
        value_size=200
    )
    frame.Show(True)
    app.MainLoop()
    for char in main_panel.editor_panel:
        editing_structure[char][
            "new_binary"] = main_panel.editor_panel[char].binary
    for i in editing_structure:
        print(
            f'{i}: {editing_structure[i]["binary"]} --> '
            f'{editing_structure[i]["new_binary"]}'
        )


def bleak_app(construct_module, args):
    class SDBleakScannerConstruct(BleakScannerConstruct):
        sep = " \u250a "  # thin vertical dotted bar

        def bleak_advertising(self, device, advertisement_data):
            def get_uuid(uuid_str):
                uuid = bleak.uuids.uuidstr_to_str(uuid_str)
                if uuid == "Vendor specific":
                    uuid += " "
                    try:
                        uuid += re.findall(r'\d+', uuid_str)[0].lstrip('0')
                    except ValueError:
                        uuid += uuid_str
                return uuid

            logging.warning(
                "mac: %s. adv.data: %s. RSSI: %s",
                device.address,
                advertisement_data,
                advertisement_data.rssi,
            )
            local_name = ""
            if advertisement_data.local_name:
                local_name += advertisement_data.local_name + self.sep
            if advertisement_data.service_uuids:
                for i in advertisement_data.service_uuids:
                    local_name += get_uuid(i) + self.sep
            if (
                args.detect_manuf_data or args.not_detect_svc_data
            ) and advertisement_data.manufacturer_data:
                for adv_id, data in advertisement_data.manufacturer_data.items():
                    str_name = f"{local_name}Manufacturer {adv_id}"
                    self.add_packet_frame(
                        data=data,
                        append_label=str_name,
                        date_separator=self.sep,
                        reference=device.address,
                    )
            if not args.not_detect_svc_data and advertisement_data.service_data:
                for name, data in advertisement_data.service_data.items():
                    str_name = local_name + get_uuid(name)
                    self.add_packet_frame(
                        data=data,
                        append_label=str_name,
                        date_separator=self.sep,
                        reference=device.address,
                    )

    app = wx.App(False)
    width, height = wx.GetDisplaySize()
    title = "BLE Advertising Editor"
    if construct_module:
        title += " - " + construct_module.__file__
    frame = wx.Frame(
        None,
        pos=(int(width * 5 / 100), int(height * 5 / 100)),
        title=title,
        size=(int(width * 90 / 100), int(height * 90 / 100)),
    )
    frame.CreateStatusBar()
    main_panel = SDBleakScannerConstruct(
        frame,
        gallery_descriptor=construct_module,
        reference_label=args.reference_label or "MAC Address",
        key_label=args.key_label,
        description_label=args.description_label or "Description",
        gallery_descriptor_var=args.gallery_descriptor_var,
        construct_format_var=args.construct_format_var
    )
    frame.Bind(wx.EVT_CLOSE, lambda event: on_close(main_panel, event))
    frame.Show(True)
    app.MainLoop()


def on_close(frame, event):
    frame.on_application_close()
    event.Skip()


def gallery_app(construct_module, args):
    app = wx.App(False)
    width, height = wx.GetDisplaySize()
    title = "Construct Gallery Editor"
    if construct_module:
        title += " - " + construct_module.__file__
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
                ordered_sample_bytes=OrderedDict(  # OrderedDict format
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
                ordered_sample_bytes={  # dictionary format
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
                module: GalleryItem(
                    construct=sample_modules[module].gallery_item.construct,
                    contextkw=sample_modules[module].gallery_item.contextkw,
                    clear_log=True,
                    ordered_sample_bytes=sample_modules[
                        module].gallery_item.example_binarys
                ) for module in sample_modules
            }
        )
    main_panel = ConstructGallery(
        frame,
        gallery_descriptor=gallery_descriptor,
        reference_label=args.reference_label,
        key_label=args.key_label,
        description_label=args.description_label,
        gallery_descriptor_var=args.gallery_descriptor_var,
        construct_format_var=args.construct_format_var
    )
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
        help="construct Python module pathname.",
        default=0,
        nargs='?',
        metavar='CONSTRUCT_MODULE')
    parser.add_argument(
        "-R"
        '--reference_label',
        dest='reference_label',
        action='store',
        type=str,
        help='"reference_label" string.'
    )
    parser.add_argument(
        '-K',
        '--key_label',
        dest='key_label',
        action='store',
        type=str,
        help='"key_label" string'
    )
    parser.add_argument(
        '-D',
        '--description_label',
        dest='description_label',
        action='store',
        type=str,
        help='"description_label" string.'
    )
    if BleakScannerConstruct.BLEAK_IS_USED:
        parser.add_argument(
            '-M',
            "--not_detect_svc_data",
            dest='not_detect_svc_data',
            action='store_true',
            help="Only used with -b/--bleak option. "
            "Do not detect service data with -b option and detect "
            "manufacturer data. Default is to detect service data and not to "
            "detect manufacturer data."
        )
        parser.add_argument(
            '-m',
            "--detect_manuf_data",
            dest='detect_manuf_data',
            action='store_true',
            help="Only used with -b/--bleak option. "
            "Detect both manufacturer and service data with -b option. "
            "Default is not to detect manufacturer data "
            "and only detect service data."
        )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-g',
        "--gallery",
        dest='gallery',
        action='store_true',
        help="Construct Gallery Editor (default)")
    parser.add_argument(
        '-F',
        '--gallery_descriptor',
        dest='gallery_descriptor_var',
        action='store',
        type=str,
        default=None,
        help='Custom "gallery_descriptor" variable name.'
    )
    parser.add_argument(
        '-f',
        '--construct_format',
        dest='construct_format_var',
        action='store',
        type=str,
        default=None,
        help='Custom "construct_format" variable name.'
    )
    if BleakScannerConstruct.BLEAK_IS_USED:
        group.add_argument(
            '-b',
            "--bleak",
            dest='bleak',
            action='store_true',
            help="BLE Advertising Editor.")
        group.add_argument(
            '-c',
            "--config",
            dest='config',
            action='store_true',
            help="Config Editor.")
    args = parser.parse_args()
    if BleakScannerConstruct.BLEAK_IS_USED:
        if (
            (args.not_detect_svc_data or args.detect_manuf_data)
            and not (args.bleak or run_bleak)
        ):
            print(
                "Options -M/--not_detect_svc_data and -m/--detect_manuf_data "
                "can only be used with the -b/--bleak option."
            )
            sys.exit(2)
    if (
        args.gallery_descriptor_var or args.construct_format_var
    ) and not args.construct_module:
        print(
            "Missing Python module referred to options "
            "'--gallery_descriptor'/'--construct_format'."
        )
        sys.exit(2)
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
            print("Cannot identify module:", str(e))
            sys.exit(2)
        sys.modules['construct_module'] = construct_module
        try:
            spec.loader.exec_module(construct_module)
        except Exception as e:
            print("Construct module import error:", str(e))
            sys.exit(2)

    if BleakScannerConstruct.BLEAK_IS_USED and (args.bleak or run_bleak):
        sys.exit(bleak_app(construct_module, args))
    elif args.config:
        sys.exit(config_app(construct_module))
    else:
        sys.exit(gallery_app(construct_module, args))


if __name__ == "__main__":
    main()
