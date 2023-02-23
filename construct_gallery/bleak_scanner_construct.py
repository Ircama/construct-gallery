#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
# bleak_scanner_construct module
#############################################################################

from bleak import BleakScanner  # pip3 install bleak
import wx
from .wx_logging_plugin import WxLogging
import logging
from construct_gallery import ConstructGallery
import re

import asyncio
from functools import partial
from threading import Thread


class FilterEntryDialog(wx.Dialog):
    def __init__(
            self,
            parent,
            caption,
            mac_title,
            mac_default_value,
            filter_hint_mac,
            name_title,
            name_default_value,
            filter_hint_name,
            button_style):
        dialog_style = wx.DEFAULT_DIALOG_STYLE
        super(FilterEntryDialog, self).__init__(
            parent, -1, caption, style=dialog_style)

        sizer = wx.BoxSizer(wx.VERTICAL)

        box = wx.BoxSizer(wx.HORIZONTAL)
        mac_text = wx.StaticText(self, -1, mac_title, size=(230,-1))
        box.Add(mac_text, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        mac_input = wx.TextCtrl(self, -1, mac_default_value, size=(200,-1))
        if filter_hint_mac:
            mac_input.SetHint(filter_hint_mac)
        box.Add(mac_input, 1, wx.ALIGN_CENTRE|wx.ALL, 5)
        sizer.Add(box, 0, wx.GROW|wx.ALL, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        name_text = wx.StaticText(self, -1, name_title, size=(230,-1))
        box.Add(name_text, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        name_input = wx.TextCtrl(self, -1, name_default_value, size=(200,-1))
        if filter_hint_name:
            name_input.SetHint(filter_hint_name)
        box.Add(name_input, 1, wx.ALIGN_CENTRE|wx.ALL, 5)
        buttons = self.CreateButtonSizer(button_style)
        sizer.Add(box, 0, wx.GROW|wx.ALL, 5)

        label = wx.StaticText(
            self, -1, "Multiple elements are allowed (separated by comma).")
        sizer.Add(label, 0, wx.ALIGN_RIGHT|wx.ALL, 15)

        sizer.Add(buttons, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizerAndFit(sizer)
        self.mac_input = mac_input
        self.name_input = name_input

    def SetMacValue(self, value):
        self.mac_input.SetValue(value)

    def GetMacValue(self):
        return self.mac_input.GetValue()

    def SetNameValue(self, value):
        self.name_input.SetValue(value)

    def GetNameValue(self):
        return self.name_input.GetValue()


class BleakScannerConstruct(ConstructGallery):
    bleak_stop_event = None
    bleak_event_loop = None
    bluetooth_thread = None
    filter_mac = ""
    filter_name = ""

    def __init__(
            self,
            *args,
            filter_hint_mac=None,
            filter_hint_name=None,
            reference_label="MAC address",
            load_menu_label="Log Data and Configuration",
            clear_label="Log Data",
            added_data_label="Logging data",
            logging_plugin=True,
            **kwargs):
        super().__init__(
            *args,
            reference_label=reference_label,
            load_menu_label=load_menu_label,
            clear_label=clear_label,
            added_data_label=added_data_label,
            **kwargs)
        self.filter_hint_mac = filter_hint_mac
        self.filter_hint_name = filter_hint_name

        # Start and stop buttons
        controlSizer = wx.StaticBoxSizer(
            wx.HORIZONTAL,
            self,
            label="BLE control")

        self.startButton = wx.Button(self, wx.ID_ANY, label="Start")
        self.startButton.Bind(wx.EVT_BUTTON, lambda event: self.ble_start())
        controlSizer.Add(self.startButton, 0, wx.EXPAND | wx.RIGHT, 5)

        self.filterButton = wx.Button(self, wx.ID_ANY, label="Filter")
        self.filterButton.Bind(wx.EVT_BUTTON, self.on_filter)
        controlSizer.Add(self.filterButton, 0)

        self.stopButton = wx.Button(self, wx.ID_ANY, label="Stop")
        self.stopButton.Enable(False)
        self.stopButton.Bind(wx.EVT_BUTTON, lambda event: self.ble_stop())
        controlSizer.Add(self.stopButton, 0, wx.EXPAND | wx.LEFT, 5)

        self.vsizer.Insert(self.control_position, controlSizer, 0, wx.CENTER)
        if logging_plugin:
            self.wx_log_window = WxLogging(self, logging.getLogger())

    def on_filter(self, event):
        mac = None
        name = None
        dlg = FilterEntryDialog(
            self,
            "Filtering Settings",
            'Enter a MAC or the initial portion of a MAC:',
            self.filter_mac,
            self.filter_hint_mac,
            'Enter a local name or its initial portion:',
            self.filter_name,
            self.filter_hint_name,
            button_style=wx.OK|wx.CANCEL)
        if dlg.ShowModal() == wx.ID_OK:
            mac = dlg.GetMacValue()
            name = dlg.GetNameValue()
        dlg.Destroy()
        if mac is not None:
            self.filter_mac = mac
        if name is not None:
            self.filter_name = name

    def ble_start(self):
        if self.bluetooth_thread and self.bluetooth_thread.is_alive():
            return
        self.bluetooth_thread = Thread(
            target=lambda: asyncio.run(self.bt_adv()))
        logging.warning("BLE thread started")
        self.bluetooth_thread.start()
        self.startButton.Enable(False)
        self.stopButton.Enable(True)
        self.wx_log_window.log_window.Show()
        self.status_message(f"BLE started.")

    def ble_stop(self):
        if (not self.bluetooth_thread or
                not self.bluetooth_thread.is_alive() or
                not self.bleak_stop_event):
            return
        if not self.bleak_stop_event.is_set():
            self.bleak_stop_event.set()
        if self.bluetooth_thread:
            self.bluetooth_thread.join(1)
        self.startButton.Enable(True)
        self.stopButton.Enable(False)
        logging.warning("stop")
        self.status_message(f"BLE stopped.")

    def on_application_close(self):
        self.ble_stop()
        if hasattr(self, 'pyshell') and self.pyshell:
            self.pyshell.Destroy()

    async def bt_adv(self):
        self.bleak_stop_event = asyncio.Event()
        self.bleak_event_loop = asyncio.get_event_loop()

        def detection_callback(device, advertisement_data):
            found = False
            for i in re.split('; |, ', self.filter_mac):
                if i and device.address.upper().startswith(i.upper()):
                    found = True
                    break
            if i and not found:
                return
            found = False
            for i in re.split('; |, ', self.filter_name):
                if (i and advertisement_data.local_name and
                        advertisement_data.local_name.startswith(i)):
                    found = True
                    break
            if i and not found:
                return
            self.bleak_advertising(device, advertisement_data)

        async with BleakScanner(
            detection_callback=partial(detection_callback)
        ) as scanner:
            await self.bleak_stop_event.wait()
        logging.warning("BLE thread stopped")

    # This method must be overridden
    def bleak_advertising(self, device, advertisement_data):
        logging.info(
            "Advertising: device=%s, advertisement_data=%s",
            device, advertisement_data)


if __name__ == "__main__":
    app = wx.App(False)
    frame = wx.Frame(
        None, title="BleakScannerConstructFrame", size=(1000, 600))
    frame.CreateStatusBar()
    BleakScannerConstruct(frame)
    frame.Show(True)
    app.MainLoop()
