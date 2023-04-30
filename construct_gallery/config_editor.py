#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
# config_editor module
#############################################################################

import wx
from construct_editor.wx_widgets import WxConstructHexEditor
import wx.lib.scrolledpanel as scrolled

from construct_editor.core.model import IntegerFormat
import construct_editor.wx_widgets.wx_hex_editor
from construct_gallery import HexEditorGrid


class ConfigEditorPanel(scrolled.ScrolledPanel):
    def __init__(
            self,
            parent,
            editing_structure={},
            name_size=None,
            type_size=None,
            value_size=None,
            run_hex_editor_plugins=True):
        scrolled.ScrolledPanel.__init__(self, parent, -1)

        # monkey-patch HexEditorGrid
        if run_hex_editor_plugins:
            construct_editor.wx_widgets.wx_hex_editor.HexEditorGrid = HexEditorGrid

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.editor_panel = {}
        for i in editing_structure:
            item = editing_structure[i]
            if not {
                "name",
                "binary",
                "construct",
                "size",
                "IntegerFormat",
                "read_only"
            }.issubset({key for key in item}):
                continue
            hsizer = wx.BoxSizer(wx.HORIZONTAL)

            # Text
            text_sizer = wx.BoxSizer(wx.VERTICAL)
            text_label_size = 90
            text_char = wx.StaticText(
                self,
                -1,
                "Characteristic {:02x}".format(i),
                style=wx.TE_READONLY | wx.TE_MULTILINE,
                size=(text_label_size, -1))
            text_char.Wrap(text_label_size)
            text_char.SetForegroundColour('BLUE')
            text_sizer.Add(
                text_char,
                proportion=0,
                flag=wx.ALIGN_LEFT | wx.TOP,
                border=8)
            text_name = wx.StaticText(
                self,
                -1,
                item["name"],
                style=wx.TE_READONLY | wx.TE_MULTILINE,
                size=(text_label_size, -1))
            text_name.Wrap(text_label_size)
            font = text_name.GetFont()
            font.SetWeight(wx.FONTWEIGHT_BOLD)
            text_name.SetFont(font)
            text_sizer.Add(
                text_name,
                proportion=0,
                flag=wx.ALIGN_LEFT | wx.TOP,
                border=6)
            if item["read_only"]:
                text_readonly = wx.StaticText(
                    self,
                    -1,
                    "(read only)",
                    style=wx.TE_READONLY | wx.TE_MULTILINE,
                    size=(text_label_size, -1))
                text_sizer.Add(
                    text_readonly,
                    proportion=0,
                    flag=wx.ALIGN_LEFT | wx.TOP,
                    border=6)
                text_readonly.Wrap(text_label_size)
                text_readonly.SetForegroundColour(wx.Colour(9, 90, 20))
            hsizer.Add(
                text_sizer, proportion=0, flag=wx.EXPAND|wx.ALL, border=0)

            # Construct Editor
            self.editor_panel[i] = WxConstructHexEditor(
                self,
                construct=item["construct"],
                binary=item["binary"])
            ce = self.editor_panel[i].construct_editor
            if item["IntegerFormat"] == IntegerFormat.Hex:
                ce.model.integer_format = IntegerFormat.Hex
                ce.reload()
            cols = ce._dvc.GetColumns()
            if name_size:
                cols[0].SetWidth(name_size)
            if type_size:
                cols[1].SetWidth(type_size)
            if value_size:
                cols[2].SetWidth(value_size)
            self.editor_panel[i].toggle_hex_visibility()
            ce.expand_all()
            self.editor_panel[i].SetMinSize((-1, item["size"]))
            hsizer.Add(self.editor_panel[i], 1, wx.EXPAND|wx.ALL, 5)

            vsizer.Add(hsizer, 0, wx.EXPAND|wx.ALL, 5)
            vsizer.Add(
                wx.StaticLine(self, style=wx.LI_HORIZONTAL),
                0,
                wx.TOP | wx.BOTTOM | wx.EXPAND,
                5)

        self.SetSizer(vsizer)
        self.SetupScrolling()
