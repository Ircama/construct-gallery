#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
# construct_gallery module
#############################################################################

from importlib import reload, import_module
import wx
import wx.grid
import construct_editor.wx_widgets.wx_hex_editor
from construct_editor.wx_widgets import WxConstructHexEditor
import construct_editor.gallery
from importlib import reload, import_module
from datetime import datetime, timezone
import pickle
from collections import OrderedDict
from pathlib import Path
import sys
import typing as t
from types import TracebackType, ModuleType
import os
import wx.lib.dialogs
from . import allow_python_expr_plugin
from . import decimal_convert_plugin
from . import string_convert_plugin
from construct_editor.wx_widgets.wx_exception_dialog import (
    ExceptionInfo,
    WxExceptionDialog,
)
from construct_editor.wx_widgets.wx_hex_editor import ContextMenuItem
from .pyshell_plugin import PyShellPlugin
import re
import dataclasses
import construct as cs
import time
from pkgutil import iter_modules


@dataclasses.dataclass
class GalleryItem:
    construct: "cs.Construct[t.Any, t.Any]"
    clear_log: bool = False
    contextkw: t.Dict[str, t.Any] = dataclasses.field(
        default_factory=dict)
    example_bytes: t.OrderedDict[str, bytes] = dataclasses.field(
        default_factory=dict)
    example_dict: t.OrderedDict[str, dict] = dataclasses.field(
        default_factory=dict)
    example_key: t.Dict[str, dict] = dataclasses.field(
        default_factory=dict)


class HexEditorGrid(  # add plugins to HexEditorGrid
        string_convert_plugin.HexEditorGrid,
        decimal_convert_plugin.HexEditorGrid,
        allow_python_expr_plugin.HexEditorGrid,
        construct_editor.wx_widgets.wx_hex_editor.HexEditorGrid):
    def build_context_menu(self):
        menus = super().build_context_menu()
        menus.insert(-3, None)  # add an horizontal line before the two plugins
        return menus


class GalleryDict(object):
    @classmethod
    def init(self, reference_label, key_label, description_label):
        self.gallery_history = {}
        self.key_descr_dict = {}
        self.reference_label = reference_label
        self.key_label = key_label
        self.description_label = description_label
        self.fixed_contextkw = {}

    @classmethod
    def set_fixed_contextkw(self, fixed_contextkw):
        """
        If set with a construct dictionary, the contextkw remains fixed for any
        element of the gallery item, until the gallery item changes. Otherwise,
        if fixed_contextkw is {}, dynamic mode is used (key and description
        changes for each reference).
        """
        self.fixed_contextkw = fixed_contextkw

    @classmethod
    def get_contextkw(self, element):
        if self.fixed_contextkw:
            return self.fixed_contextkw
        ref_elm, reference, key_elm, key = GalleryDict.get_key(element)
        if not reference:
            return {}
        _, _, descr_elm, description = GalleryDict.get_description(element)
        try:
            ref_elm_value = bytes.fromhex(re.sub(r'[.:\- ]', '', reference))
        except Exception as e:
            dlg = wx.MessageDialog(
                None,
                ref_elm + ' value is "' + reference + '": ' + str(e),
                "Invalid data in " + self.reference_label,
                wx.OK | wx.ICON_WARNING
            )
            dlg.ShowModal()
            dlg.Destroy()
            return {}
        try:
            key_elm_value = bytes.fromhex(key)
        except Exception as e:
            dlg = wx.MessageDialog(
                None,
                key_elm + ' value is "' + key + '": ' + str(e),
                "Invalid data in " + self.key_label,
                wx.OK | wx.ICON_WARNING
            )
            dlg.ShowModal()
            dlg.Destroy()
            return {}
        contextkw = {
            ref_elm: ref_elm_value,
            key_elm: key_elm_value,
            descr_elm: description
        }
        if None in contextkw:
            contextkw.pop(None)
        return contextkw

    @classmethod
    def get_key_descr_dict(self):
        return self.key_descr_dict

    @classmethod
    def set_key_descr_dict(self, key_descr_dict):
        self.key_descr_dict = key_descr_dict

    @classmethod
    def update_key_descr_dict(self, key_descr_dict):
        self.key_descr_dict = {**self.key_descr_dict, **key_descr_dict}

    @classmethod
    def reset(self):
        self.gallery_history = {}

    @classmethod
    def update_dict(self, additional_dict):
        return self.gallery_history.update(additional_dict)

    @classmethod
    def exists(self, element):
        return element in self.gallery_history

    @classmethod
    def len(self):
        return len(self.gallery_history)

    @classmethod
    def get_binary(self, element):
        if element not in self.gallery_history:
            return None
        value = self.gallery_history[element]
        if isinstance(value, dict) and "binary" in value:
            value = value["binary"]
        if isinstance(value, bytes):
            return value
        return None

    @classmethod
    def set(self, element, binary, reference=None):
        if not self.gallery_history:
            self.gallery_history = {element: {"binary": binary}}
            GalleryDict.set_reference(element, reference)
            return
        if GalleryDict.exists(element):
            value = self.gallery_history[element]
            if isinstance(value, dict):
                if "binary" in value:
                    self.gallery_history[element]["binary"] = binary
                    GalleryDict.set_reference(element, reference)
                    return
        self.gallery_history[element] = {"binary": binary}
        GalleryDict.set_reference(element, reference)

    @classmethod
    def get_reference(self, element):
        if not self.reference_label:
            return None, None
        ref_elm = self.reference_label.lower().replace(" ", "_")
        if element not in self.gallery_history:
            return ref_elm, None
        if (isinstance(self.gallery_history[element], dict) and
                ref_elm in self.gallery_history[element]):
            return ref_elm, self.gallery_history[element][ref_elm]
        return ref_elm, ""

    @classmethod
    def set_reference(self, element, reference):
        if not self.reference_label:
            return
        if not reference:
            return
        if element not in self.gallery_history:
            return
        elm_dict = self.gallery_history[element]
        if not isinstance(elm_dict, dict):
            binary = elm_dict
            elm_dict = {"binary": binary}
        ref_elm = self.reference_label.lower().replace(" ", "_")
        elm_dict[ref_elm] = reference
        self.gallery_history[element] = elm_dict

    @classmethod
    def reference_exists(self, element, interactive=False):
        ref_elm, reference = GalleryDict.get_reference(element)
        if not reference and interactive:
            dlg = wx.MessageDialog(
                None,
                "Add the " + self.reference_label + " first.",
                "The " + self.reference_label + " of this element is missing",
                wx.OK | wx.ICON_WARNING
            )
            dlg.ShowModal()
            dlg.Destroy()
            return ref_elm, None
        return ref_elm, reference

    @classmethod
    def get_key(self, element, interactive=False):
        if not self.key_label:
            return None, None, None, None
        ref_elm, reference = GalleryDict.reference_exists(element, interactive)
        if not reference:
            return None, None, None, None
        key_elm = self.key_label.lower().replace(" ", "_")
        if (reference not in self.key_descr_dict or
                key_elm not in self.key_descr_dict[reference]):
            return ref_elm, reference, key_elm, ""
        return ref_elm, reference, key_elm, self.key_descr_dict[
            reference][key_elm]

    @classmethod
    def set_key(self, element, key):
        _, reference, key_elm, prev_key = GalleryDict.get_key(
            element, interactive=True)
        if prev_key == None:
            return None
        if reference not in self.key_descr_dict:
            self.key_descr_dict[reference] = {}
        self.key_descr_dict[reference][key_elm] = key

    @classmethod
    def get_description(self, element, interactive=False):
        if not self.description_label:
            return None, None, None, None
        ref_elm, reference = GalleryDict.reference_exists(element, interactive)
        if not reference:
            return None, None, None, None
        description_elm = self.description_label.lower().replace(" ", "_")
        if (reference not in self.key_descr_dict or
                description_elm not in self.key_descr_dict[reference]):
            return ref_elm, reference, description_elm, ""
        return ref_elm, reference, description_elm, self.key_descr_dict[
            reference][description_elm]

    @classmethod
    def set_description(self, element, description):
        _, reference, description_elm, prev_descr = GalleryDict.get_description(
            element, interactive=True)
        if prev_descr == None:
            return None
        if reference not in self.key_descr_dict:
            self.key_descr_dict[reference] = {}
        self.key_descr_dict[reference][description_elm] = description

    @classmethod
    def delete(self, element):
        del self.gallery_history[element]

    @classmethod
    def pop(self, element):
        return self.gallery_history.pop(element, None)

    @classmethod
    def keys(self):
        return self.gallery_history.keys()

    @classmethod
    def dump(self, items, file):
        gallery_history = OrderedDict()
        for i in items:
            gallery_history[i] = self.gallery_history[i]
        return pickle.dump([gallery_history, self.key_descr_dict], file,
            protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load_dict(self, file):
        try:
            gallery_history, key_descr_dict = pickle.load(file)
            self.key_descr_dict = {**self.key_descr_dict, **key_descr_dict}
        except ValueError:
            file.seek(0)
            gallery_history = pickle.load(file)
        return gallery_history


def MakeModal(self, modal=True):  # https://stackoverflow.com/a/43126586/10598800
    if modal and not hasattr(self, '_disabler'):
        self._disabler = wx.WindowDisabler(self)
    if not modal and hasattr(self, '_disabler'):
        del self._disabler


class RefKeyDescrFrame(wx.Frame):
    def __init__(
            self,
            parent,
            ID,
            title,
            pos=wx.DefaultPosition,
            style=(wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT)
                ^ wx.RESIZE_BORDER):
        wx.Frame.__init__(self, parent, ID, title, pos, style=style)
        self.parent = parent
        self.grid = EditableGrid(self)
        self.grid.CreateGrid(10, 3)
        self.grid.SetColSize(0, 130)
        self.grid.SetColSize(1, 300)
        self.grid.SetColSize(2, 300)
        self.grid.SetColLabelValue(0, parent.reference_label)
        self.grid.DisableDragRowSize()
        self.grid.DisableDragGridSize()
        self.grid.DisableDragColSize()
        self.key_elm = None
        self.desc_elm = None
        if parent.key_label:
            self.grid.SetColLabelValue(1, parent.key_label)
            self.key_elm = parent.key_label.lower().replace(" ", "_")
        else:
            self.grid.HideCol(1)
        if parent.description_label:
            self.grid.SetColLabelValue(2, parent.description_label)
            self.desc_elm = parent.description_label.lower().replace(" ", "_")
        else:
            self.grid.HideCol(2)

        row = 0
        key_descr_dict = GalleryDict.get_key_descr_dict()
        for key in key_descr_dict:
            key_elm_value = ""
            key_descr_value = ""
            if self.key_elm and self.key_elm in key_descr_dict[key]:
                key_elm_value = key_descr_dict[key][self.key_elm]
            if self.desc_elm and self.desc_elm in key_descr_dict[key]:
                key_descr_value = key_descr_dict[key][self.desc_elm]
            self.grid.SetCellValue(row, 0, key)
            self.grid.SetCellValue(row, 1, key_elm_value)
            self.grid.SetCellValue(row, 2, key_descr_value)
            row += 1

        self.frame_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.frame_sizer.Add(self.grid, 1, wx.EXPAND)
        self.SetSizerAndFit(self.frame_sizer)
        self.monotonic = 0
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_up)
        self.Bind(wx.EVT_CLOSE, self.on_completed_form)

    def on_key_up(self, event):
        keyCode = event.GetKeyCode()
        if keyCode == wx.WXK_ESCAPE:
            if time.monotonic() - self.monotonic < 2:
                self.on_completed_form(event)
            self.monotonic = time.monotonic()
        event.Skip()

    def on_completed_form(self, event):
        key_descr_dict = {}
        for row in range(self.grid.GetNumberRows()):
            ref = self.grid.GetCellValue(row, 0)
            if not ref:
                continue
            key_descr_dict[ref] = {
                self.key_elm: self.grid.GetCellValue(row, 1),
                self.desc_elm: self.grid.GetCellValue(row, 2)
            }
        GalleryDict.set_key_descr_dict(key_descr_dict)
        MakeModal(self, False)
        if self.parent.gallery_selector_lbx.GetSelection() >= 0:
            self.parent.on_gallery_selection_changed(None)
        self.Destroy()


class EditableGrid(wx.grid.Grid):
    def __init__(self, parent):
        wx.grid.Grid.__init__(
            self, parent, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        font = self.GetFont()
        font.SetFamily(wx.FONTFAMILY_MODERN)
        self.SetDefaultCellFont(font)
        self.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_ALWAYS)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.Bind(wx.grid.EVT_GRID_CELL_CHANGING, self.on_change)
        self.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.on_label_right_click)
        self.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.on_cell_right_click)
        self.selected_rows = []
        self.selected_cols = []
        self.history = []

    def get_col_headers(self):
        return [
            self.GetColLabelValue(col) for col in range(self.GetNumberCols())]

    def get_table(self):
        for row in range(self.GetNumberRows()):
            result = {}
            for col, header in enumerate(self.get_col_headers()):
                result[header] = self.GetCellValue(row, col)
            yield result

    def add_rows(self, event):
        for row in self.selected_rows:
            self.InsertRows(row)
        self.add_history({"type": "add_rows", "rows": self.selected_rows})

    def delete_rows(self, event):
        self.cut(event)
        rows = []
        for row in reversed(self.selected_rows):
            rows.append((
                row,
                {  # More attributes can be added
                    "label": self.GetRowLabelValue(row),
                    "size": self.GetRowSize(row)
                }
            ))
            self.DeleteRows(row)
        self.add_history({"type": "delete_rows", "rows": rows})

    def on_cell_right_click(self, event):
        menus = [(wx.NewId(), "Cut", self.cut),
                 (wx.NewId(), "Copy", self.copy),
                 (wx.NewId(), "Paste", self.paste)]
        popup_menu = wx.Menu()
        for menu in menus:
            if menu is None:
                popup_menu.AppendSeparator()
                continue
            popup_menu.Append(menu[0], menu[1])
            self.Bind(wx.EVT_MENU, menu[2], id=menu[0])

        self.PopupMenu(popup_menu, event.GetPosition())
        popup_menu.Destroy()
        return

    def on_label_right_click(self, event):
        menus = [(wx.NewId(), "Cut", self.cut),
                 (wx.NewId(), "Copy", self.copy),
                 (wx.NewId(), "Paste", self.paste),
                 None]

        # Select if right clicked row or column is not in selection
        if event.GetRow() > -1:
            if not self.IsInSelection(row=event.GetRow(), col=1):
                self.SelectRow(event.GetRow())
            self.selected_rows = self.GetSelectedRows()
            menus += [(wx.NewId(), "Add row", self.add_rows)]
            menus += [(wx.NewId(), "Delete row", self.delete_rows)]
        elif event.GetCol() > -1:
            if not self.IsInSelection(row=1, col=event.GetCol()):
                self.SelectCol(event.GetCol())
            self.selected_cols = self.GetSelectedCols()
            menus += [(wx.NewId(), "Add row", self.add_rows)]
            menus += [(wx.NewId(), "Delete row", self.delete_rows)]
        else:
            return

        popup_menu = wx.Menu()
        for menu in menus:
            if menu is None:
                popup_menu.AppendSeparator()
                continue
            popup_menu.Append(menu[0], menu[1])
            self.Bind(wx.EVT_MENU, menu[2], id=menu[0])

        self.PopupMenu(popup_menu, event.GetPosition())
        popup_menu.Destroy()
        return

    def on_change(self, event):
        cell = event.GetEventObject()
        row = cell.GetGridCursorRow()
        col = cell.GetGridCursorCol()
        attribute = {"value": self.GetCellValue(row, col)}
        self.add_history({"type": "change", "cells": [(row, col, attribute)]})

    def add_history(self, change):
        self.history.append(change)

    def undo(self):
        if not len(self.history):
            return

        action = self.history.pop()
        if action["type"] == "change" or action["type"] == "delete":
            for row, col, attribute in action["cells"]:
                self.SetCellValue(row, col, attribute["value"])
                if action["type"] == "delete":
                    self.SetCellAlignment(row, col, *attribute["alignment"])
                    # *attribute["alignment"] > horiz, vert

        elif action["type"] == "delete_rows":
            for row, attribute in reversed(action["rows"]):
                self.InsertRows(row)
                self.SetRowLabelValue(row, attribute["label"])
                self.SetRowSize(row, attribute["size"])

        elif action["type"] == "add_rows":
            for row in reversed(action["rows"]):
                self.DeleteRows(row)

        else:
            return

    def on_key(self, event):
        """
        Handles all key events.
        """
        # print(event.GetKeyCode())
        # Ctrl+C or Ctrl+Insert
        if event.ControlDown() and event.GetKeyCode() in [67, 322]:
            self.copy(event)

        # Ctrl+V
        elif event.ControlDown() and event.GetKeyCode() == 86:
            self.paste(event)

        # DEL
        elif event.GetKeyCode() == 127:
            self.delete(event)

        # Ctrl+A
        elif event.ControlDown() and event.GetKeyCode() == 65:
            self.SelectAll()

        # Ctrl+Z
        elif event.ControlDown() and event.GetKeyCode() == 90:
            self.undo()

        # Ctrl+X
        elif event.ControlDown() and event.GetKeyCode() == 88:
            # Call delete method
            self.cut(event)

        # Ctrl+V or Shift + Insert
        elif (event.ControlDown() and event.GetKeyCode() == 67) \
                or (event.ShiftDown() and event.GetKeyCode() == 322):
            self.paste(event)

        else:
            event.Skip()

    def get_selection(self):
        """
        Returns selected range's start_row, start_col, end_row, end_col
        If there is no selection, returns selected cell's start_row=end_row,
        start_col=end_col
        """
        if not len(self.GetSelectionBlockTopLeft()):
            selected_columns = self.GetSelectedCols()
            selected_rows = self.GetSelectedRows()
            if selected_columns:
                start_col = selected_columns[0]
                end_col = selected_columns[-1]
                start_row = 0
                end_row = self.GetNumberRows() - 1
            elif selected_rows:
                start_row = selected_rows[0]
                end_row = selected_rows[-1]
                start_col = 0
                end_col = self.GetNumberCols() - 1
            else:
                start_row = end_row = self.GetGridCursorRow()
                start_col = end_col = self.GetGridCursorCol()
        elif len(self.GetSelectionBlockTopLeft()) > 1:
            wx.MessageBox("Multiple selections are not supported", "Warning")
            return []
        else:
            start_row, start_col = self.GetSelectionBlockTopLeft()[0]
            end_row, end_col = self.GetSelectionBlockBottomRight()[0]

        return [start_row, start_col, end_row, end_col]

    def get_selected_cells(self):
        # returns a list of selected cells
        selection = self.get_selection()
        if not selection:
            return

        start_row, start_col, end_row, end_col = selection
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                yield [row, col]

    def copy(self, event):
        """
        Copies range of selected cells to clipboard.
        """

        selection = self.get_selection()
        if not selection:
            return []
        start_row, start_col, end_row, end_col = selection

        data = u''

        rows = range(start_row, end_row + 1)
        for row in rows:
            columns = range(start_col, end_col + 1)
            for idx, column in enumerate(columns, 1):
                if idx == len(columns):
                    # if we are at the last cell of the row, add new line instead
                    data += self.GetCellValue(row, column) + "\n"
                else:
                    data += self.GetCellValue(row, column) + "\t"

        text_data_object = wx.TextDataObject()
        text_data_object.SetText(data)

        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(text_data_object)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox("Can't open the clipboard", "Warning")

    def paste(self, event):
        if not wx.TheClipboard.Open():
            wx.MessageBox("Can't open the clipboard", "Warning")
            return False

        clipboard = wx.TextDataObject()
        wx.TheClipboard.GetData(clipboard)
        wx.TheClipboard.Close()
        data = clipboard.GetText()
        if not data:
            return
        if data[-1] == "\n":
            data = data[:-1]

        try:
            cells = self.get_selected_cells()
            cell = next(cells)
        except StopIteration:
            return False

        start_row = end_row = cell[0]
        start_col = end_col = cell[1]
        max_row = self.GetNumberRows()
        max_col = self.GetNumberCols()

        history = []
        out_of_range = False

        for row, line in enumerate(data.split("\n")):
            target_row = start_row + row
            if not (0 <= target_row < max_row):
                out_of_range = True
                break

            if target_row > end_row:
                end_row = target_row

            for col, value in enumerate(line.split("\t")):
                target_col = start_col + col
                if not (0 <= target_col < max_col):
                    out_of_range = True
                    break

                if target_col > end_col:
                    end_col = target_col

                # save previous value of the cell for undo
                history.append(
                    [
                        target_row,
                        target_col,
                        {"value": self.GetCellValue(target_row, target_col)}
                    ]
                )

                self.SetCellValue(target_row, target_col, value)

        self.SelectBlock(start_row, start_col, end_row, end_col)  # select pasted range
        if out_of_range:
            wx.MessageBox("Pasted data is out of Grid range", "Warning")

        self.add_history({"type": "change", "cells": history})

    def delete(self, event):
        cells = []
        for row, col in self.get_selected_cells():
            attributes = {
                "value": self.GetCellValue(row, col),
                "alignment": self.GetCellAlignment(row, col)
            }
            cells.append((row, col, attributes))
            self.SetCellValue(row, col, "")

        self.add_history({"type": "delete", "cells": cells})

    def cut(self, event):
        self.copy(event)
        self.delete(event)


class ConstructGallery(wx.Panel, PyShellPlugin):
    def __init__(self,
            parent,
            load_menu_label="Gallery Data",
            clear_label="Gallery",
            reference_label=None,
            key_label=None,
            description_label=None,
            added_data_label="",
            loadfile=None,
            gallery_descriptor=None,
            ordered_samples=None,
            ref_key_descriptor=None,
            default_gallery_selection=0,
            col_name_width=None,
            col_type_width=None,
            col_value_width=None,
            run_shell_plugin=True,
            run_hex_editor_plugins=True):
        super().__init__(parent)

        # show uncatched exceptions in a dialog...
        sys.excepthook = self.on_uncaught_exception

        # Define GUI elements #############################################
        self.load_menu_label = load_menu_label
        self.clear_label = clear_label
        self.reference_label = reference_label
        self.key_label = key_label
        self.description_label = description_label
        self.added_data_label = added_data_label
        self.loadfile = loadfile
        self.gallery_descriptor = gallery_descriptor
        self.default_gallery_selection = default_gallery_selection
        self.col_name_width = col_name_width
        self.col_type_width = col_type_width
        self.col_value_width = col_value_width

        self.skip_add_selection = False
        self.dlg_as = None
        self.previous_selection = None
        self.construct_hex_editor = None
        self.used_construct = None
        self.default_title = self.GetTopLevelParent().GetTitle()

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)  # it includes 3 vert. sizers
        self.vsizer = wx.BoxSizer(wx.VERTICAL)  # left side sizer

        GalleryDict.init(
            self.reference_label, self.key_label, self.description_label)

        # "construct" selector
        self.construct_selector_lbx = wx.ListBox(
            self,
            id=wx.ID_ANY,
            pos=wx.DefaultPosition,
            size=wx.Size(170, -1),
            choices=[],
            name="construct_selector",
            style=wx.LB_HSCROLL | wx.LB_NEEDED_SB
        )
        self.load_construct_selector()
        self.vsizer.Add(self.construct_selector_lbx, 0, wx.ALL | wx.EXPAND, 1)
        self.construct_selector_lbx.Bind(
            wx.EVT_LISTBOX, lambda event: self.change_gallery_selection())

        # horizontal line
        self.vsizer.Add(
            wx.StaticLine(self), 0, wx.TOP | wx.BOTTOM | wx.EXPAND, 5)

        # "Gallery" selector
        self.gallery_selector_lbx = wx.ListBox(
            self,
            id=wx.ID_ANY,
            pos=wx.DefaultPosition,
            size=wx.DefaultSize,
            choices=[],  # default values
            name="gallery_selector",
            style=wx.LB_HSCROLL | wx.LB_NEEDED_SB
        )
        self.vsizer.Add(self.gallery_selector_lbx, 1, wx.ALL | wx.EXPAND, 1)
        self.gallery_selector_lbx.Bind(
            wx.EVT_LISTBOX, self.on_gallery_selection_changed
        )
        self.gallery_tooltip_item = None
        self.gallery_selector_lbx.Bind(
            wx.EVT_MOTION, self.on_mouse_motion
        )
        self.gallery_selector_lbx.Bind(
            wx.EVT_ENTER_WINDOW, self.on_mouse_motion
        )
        self.gallery_selector_lbx.Bind(
            wx.EVT_LEAVE_WINDOW, self.on_leave_window
        )
        self.gallery_selector_lbx.Bind(wx.EVT_LEFT_DCLICK,
            self.on_doubleclick_not_selected_log)
        self.gallery_selector_lbx.Bind(wx.EVT_KEY_DOWN, self.on_key_down_log)
        self.gallery_selector_lbx.Bind(wx.EVT_LISTBOX_DCLICK,
            self.on_doubleclick_log)
        self.gallery_selector_lbx.Bind(wx.EVT_RIGHT_DOWN, self.on_right_clicked)

        self.control_position = self.vsizer.GetItemCount()

        # "Load from file" / "Save to file" buttons
        controlSizer = wx.StaticBoxSizer(
            wx.HORIZONTAL, self, label=self.load_menu_label)

        self.load_data_file_btn = wx.Button(self, wx.ID_ANY,
            label="Load from file", size=wx.Size(115, -1))
        self.load_data_file_btn.Bind(wx.EVT_BUTTON,
            self.on_load_data_file_clicked)
        controlSizer.Add(self.load_data_file_btn, 0, wx.EXPAND | wx.RIGHT, 5)

        self.save_data_file_btn = wx.Button(self, wx.ID_ANY,
            label="Save to file", size=wx.Size(115, -1))
        self.save_data_file_btn.Bind(wx.EVT_BUTTON,
            self.on_save_data_file_clicked)
        controlSizer.Add(self.save_data_file_btn, 0, wx.EXPAND | wx.LEFT, 5)

        self.vsizer.Add(controlSizer, 0, wx.EXPAND | wx.CENTER)

        # "Edit ref. attributes" button
        if self.reference_label and (self.key_label or self.description_label):
            self.ref_attr_btn = wx.Button(
                self, wx.ID_ANY, "Edit " + self.reference_label + " attributes",
                wx.DefaultPosition, wx.DefaultSize, 0
            )
            self.vsizer.Add(self.ref_attr_btn, 0, wx.ALL | wx.EXPAND, 1)
            self.ref_attr_btn.Bind(
                wx.EVT_BUTTON, lambda event: self.edit_ref_attr())

        # "Clear Gallery" button
        self.clear_gallery_btn = wx.Button(
            self, wx.ID_ANY, "Clear " + self.clear_label,
            wx.DefaultPosition, wx.DefaultSize, 0
        )
        self.vsizer.Add(self.clear_gallery_btn, 0, wx.ALL | wx.EXPAND, 1)
        self.clear_gallery_btn.Bind(
            wx.EVT_BUTTON, lambda event: self.clear_log())

        # "Clear Element Data" button
        self.clear_element_data_btn = wx.Button(
            self, wx.ID_ANY, "Clear Element Data",
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.vsizer.Add(self.clear_element_data_btn, 0, wx.ALL | wx.EXPAND, 1)
        self.clear_element_data_btn.Bind(wx.EVT_BUTTON,
            self.on_clear_element_data_clicked)

        if ref_key_descriptor:
            GalleryDict.update_key_descr_dict(ref_key_descriptor)
        if ordered_samples:
            GalleryDict.update_dict(ordered_samples)
            for sample in ordered_samples.keys():
                if sample not in self.gallery_selector_lbx.GetItems():
                    self.gallery_selector_lbx.Append(sample)

        # "Reload construct module" button
        if isinstance(gallery_descriptor, ModuleType):
            self.reload_btn = wx.Button(
                self, wx.ID_ANY, "Reload construct module",
                wx.DefaultPosition, wx.DefaultSize, 0
            )
            self.vsizer.Add(self.reload_btn, 0, wx.ALL | wx.EXPAND, 1)
            self.reload_btn.Bind(
                wx.EVT_BUTTON, lambda event: self.load_construct_selector())

        if run_shell_plugin:
            self.py_shell()  # Start PyShell plugin

        self.sizer.Add(self.vsizer, 0, wx.ALL | wx.EXPAND, 2)

        # Vertical line
        self.sizer.Add(
            wx.StaticLine(self, style=wx.LI_VERTICAL),
            0,
            wx.LEFT | wx.RIGHT | wx.EXPAND,
            5,
        )

        # monkey-patch HexEditorGrid
        if run_hex_editor_plugins:
            construct_editor.wx_widgets.wx_hex_editor.HexEditorGrid = HexEditorGrid

        if not self.used_construct:
            self.status_message("Missing gallery_descriptor parameter.")
            self.SetSizer(self.sizer)
            return

        # Add the construct hex editor
        self.construct_hex_editor = WxConstructHexEditor(
            self,
            construct=self.used_construct,
            contextkw={},
        )
        self.construct_hex_editor.construct_editor.expand_all()
        self.sizer.Add(self.construct_hex_editor, 1, wx.ALL | wx.EXPAND, 2)

        self.SetSizer(self.sizer)

        # Status bar initialization
        if GalleryDict.len() == 0:
            self.status_message("Empty list")
            self.previous_selection = None

        # Add calback fired each time binary is changed
        self.construct_hex_editor.hex_panel.hex_editor.on_binary_changed.append(
            self.on_edited_value
        )

        self.change_gallery_selection()
        
        if self.loadfile:
            for i in self.loadfile:
                try:
                    gallery_history = GalleryDict.load_dict(i)
                except IOError as e:
                    wx.LogError(
                        "Invalid format in file '%s'." % i.name)
                    return
                except Exception as e:
                    dlg = wx.MessageDialog(
                        None,
                        str(e),
                        "Archive with invalid format",
                        wx.OK | wx.ICON_WARNING
                    )
                    dlg.ShowModal()
                    dlg.Destroy()
                    return
                self.load_data_dict(gallery_history, i.name)

    def on_uncaught_exception(self,
            etype: t.Type[BaseException],
            value: BaseException,
            trace: TracebackType):
        """
        Handler for all unhandled exceptions.
        :param `etype`: the exception type (`SyntaxError`, `ZeroDivisionError`, etc...);
        :type `etype`: `Exception`
        :param string `value`: the exception error message;
        :param string `trace`: the traceback header, if any (otherwise, it prints the
        standard Python header: ``Traceback (most recent call last)``.
        """
        dial = WxExceptionDialog(
            None, "Uncaught Exception...", ExceptionInfo(etype, value, trace)
        )
        dial.ShowModal()
        dial.Destroy()

    def status_message(self, message):
        status_bar = self.GetTopLevelParent().GetStatusBar()
        if status_bar:
            status_bar.SetStatusText(message)

    def on_edited_value(self, binary_data):
        """
        Callback triggered each time the binary value is changed
        """
        # Static resize
        cols = self.construct_hex_editor.construct_editor._dvc.GetColumns()
        if self.col_name_width:
            cols[0].SetWidth(self.col_name_width)
        if self.col_type_width:
            cols[1].SetWidth(self.col_type_width)
        if self.col_value_width:
            cols[2].SetWidth(self.col_value_width)

        # Cancel selection in the gallery box...
        # ...if the changed value does not match selection
        try:
            sample_binary = GalleryDict.get_binary(
                self.gallery_selector_lbx.GetStringSelection())
            if sample_binary != binary_data.get_bytes():
                self.gallery_selector_lbx.SetSelection(-1)
        except Exception:
            self.gallery_selector_lbx.SetSelection(-1)

    def load_construct_selector(self):
        """ load data (construct labels) in the "construct" selector """
        if not self.gallery_descriptor:
            return
        if isinstance(self.gallery_descriptor, ModuleType):
            construct_module = reload(self.gallery_descriptor)
            self.gallery_descriptor = construct_module.gallery_descriptor
        self.construct_selector_lbx.Clear()
        self.construct_selector_lbx.InsertItems(
            list(self.gallery_descriptor.keys()), 0)
        self.gallery_selection = self.default_gallery_selection
        default_construct = list(
            self.gallery_descriptor.keys())[self.gallery_selection]
        GalleryDict.set_fixed_contextkw(
            self.gallery_descriptor[default_construct].contextkw)
        self.used_construct = self.gallery_descriptor[
            default_construct].construct
        self.construct_selector_lbx.SetStringSelection(default_construct)
        if self.construct_hex_editor:
            self.construct_hex_editor.construct = self.used_construct
            self.construct_hex_editor.binary = self.construct_hex_editor.binary
            self.construct_hex_editor.construct_editor.expand_all()

    def on_save_data_file_clicked(self, event):
        self.confirm_changed_data()
        self.confirm_added_data()
        if GalleryDict.len() == 0:
            wx.MessageDialog(
                self,
                'No data to save',
                'Cannot save data.',
                wx.OK | wx.ICON_WARNING).ShowModal()
            return
        with wx.FileDialog(
            self,
            "Filename to save with pickle format",
            wildcard="Pickle files (*.pickle)|*.pickle|All files|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind

            # save the current contents in the file
            pathname = fileDialog.GetPath()
            try:
                with open(pathname, "wb") as file:
                    GalleryDict.dump(self.gallery_selector_lbx.GetItems(), file)
            except IOError:
                wx.LogError(
                    "Cannot save current data in file '%s'." % pathname)
                return
            self.status_message(f"Saved {GalleryDict.len()} elements.")

    def confirm_added_data(self):
        if not self.construct_hex_editor:
            return
        if (self.gallery_selector_lbx.GetSelection() >= 0 or
                self.construct_hex_editor.binary == b''):
            return
        if (wx.MessageDialog(
                self,
                'Keep previously added data?',
                'You need to confirm adding values',
                wx.YES_NO | wx.ICON_WARNING).ShowModal() == wx.ID_YES):
            self.add_selection()
        else:
            self.construct_hex_editor.binary = b''

    def confirm_changed_data(self):
        if not self.construct_hex_editor:
            return
        if (self.previous_selection is not None and
                self.previous_selection and
                GalleryDict.exists(self.previous_selection) and
                self.construct_hex_editor.binary !=
                GalleryDict.get_binary(self.previous_selection)):
            if (wx.MessageDialog(
                    self,
                    'Keep previously modified data?',
                    'You need to confirm changing values',
                    wx.YES_NO | wx.ICON_WARNING).ShowModal() == wx.ID_YES):
                GalleryDict.set(self.previous_selection,
                    self.construct_hex_editor.binary)
            else:
                self.construct_hex_editor.contextkw = GalleryDict.get_contextkw(
                    self.previous_selection)
                self.construct_hex_editor.binary = GalleryDict.get_binary(
                    self.previous_selection)

    def on_load_data_file_clicked(self, event):
        self.confirm_changed_data()
        self.confirm_added_data()
        with wx.FileDialog(
            self,
            "Open data file (pickle format)",
            wildcard="Pickle files (*.pickle)|*.pickle|All files|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind

            # Proceed loading the file chosen by the user
            pathname = Path(fileDialog.GetPath())
            try:
                with open(pathname, "rb") as file:
                    gallery_history = GalleryDict.load_dict(file)
            except IOError as e:
                wx.LogError("Cannot open file '%s'." % str(pathname))
                return
            except Exception as e:
                dlg = wx.MessageDialog(
                    None,
                    str(e),
                    "Archive with invalid format",
                    wx.OK | wx.ICON_WARNING
                )
                dlg.ShowModal()
                dlg.Destroy()
                return
            self.load_data_dict(gallery_history, str(pathname))

    def load_data_dict(self, gallery_history, pathname):
        if pathname:
            title = self.GetTopLevelParent().GetTitle()
            self.GetTopLevelParent().SetTitle(pathname + " | " + title)
        GalleryDict.update_dict(gallery_history)
        self.status_message(f"Loaded {len(gallery_history)} elements. "
            f"Total of {GalleryDict.len()} elements available.")
        self.gallery_selector_lbx.Clear()
        for i in GalleryDict.keys():
            if i not in self.gallery_selector_lbx.GetItems():
                self.gallery_selector_lbx.Append(i)
        if (GalleryDict.len() > 0 and self.construct_hex_editor and
                not self.construct_hex_editor.IsShown()):
            self.construct_hex_editor.construct_editor.Show()
            self.gallery_selector_lbx.SetSelection(0)
            sample_binary = GalleryDict.get_binary(
                self.gallery_selector_lbx.GetStringSelection())
            self.construct_hex_editor.contextkw = GalleryDict.get_contextkw(
                self.gallery_selector_lbx.GetStringSelection())
            self.construct_hex_editor.binary = sample_binary
            self.construct_hex_editor.construct_editor.expand_all()

    def edit_ref_attr(self):
        frame = RefKeyDescrFrame(
            self, -1, self.reference_label + " Attribute Editor")
        frame.Show(True)
        gridSize = frame.GetVirtualSize()
        frame.SetSize(gridSize)
        frame.Fit()
        MakeModal(frame)

    def clear_log(self):
        self.GetTopLevelParent().SetTitle(self.default_title)
        GalleryDict.reset()
        self.gallery_selector_lbx.Clear()
        if GalleryDict.len() == 0:
            self.status_message("Empty list")
            self.previous_selection = None

    def on_clear_element_data_clicked(self, event):
        if not self.construct_hex_editor:
            return
        self.construct_hex_editor.binary = b''
        self.construct_hex_editor.construct_editor.expand_all()

    def on_doubleclick_log(self, event):
        self.change_selection()

    def on_doubleclick_not_selected_log(self, event):
        wx.CallLater(200, self.add_selection)
        event.Skip()

    def add_selection(self):
        if not self.construct_hex_editor:
            return
        if self.skip_add_selection:
            self.skip_add_selection = False
            return
        self.dlg_as = wx.TextEntryDialog(
            self,
            'Enter the new label',
            'ADD VALUE AND LABEL AT THE BOTTOM')
        utc_dt = datetime.now(timezone.utc)
        label = utc_dt.astimezone().strftime(
            '%Y-%m-%d %H:%M:%S.%f').strip()
        self.dlg_as.SetValue(label)
        for txt in self.dlg_as.Children:
            if isinstance(txt, wx._core.TextCtrl):
                txt.SelectAll()
                txt.SetFocus()
                break
        if self.dlg_as.ShowModal() == wx.ID_OK:
            if GalleryDict.exists(self.dlg_as.GetValue()):
                wx.MessageDialog(
                    self,
                    'Label already existing',
                    'Cannot duplicate value.',
                    wx.OK | wx.ICON_WARNING).ShowModal()
                self.dlg_as.Destroy()
                return
            _, org_reference = GalleryDict.get_reference(
                self.gallery_selector_lbx.GetStringSelection())
            if GalleryDict.len() == 0:
                self.status_message(self.added_data_label)
            GalleryDict.set(self.dlg_as.GetValue(),
                self.construct_hex_editor.binary,
                reference=org_reference)
            self.gallery_selector_lbx.Append(self.dlg_as.GetValue())
            self.previous_selection = self.dlg_as.GetValue()
            self.gallery_selector_lbx.SetSelection(
                self.gallery_selector_lbx.GetCount() - 1)
        self.dlg_as.Destroy()

    def change_selection(self):
        if not self.construct_hex_editor:
            return
        self.confirm_added_data()
        if self.dlg_as:
            self.dlg_as.Destroy()
        if self.gallery_selector_lbx.GetCount() == 0:
            self.add_selection()
            return
        self.skip_add_selection = True
        dlg = wx.TextEntryDialog(
            self,
            'Enter the new label or confirm the current one\n'
            'to only change its value with the edited fields',
            'Change label and value')
        dlg.SetValue(self.gallery_selector_lbx.GetStringSelection())
        for txt in dlg.Children:
            if isinstance(txt, wx._core.TextCtrl):
                txt.SelectAll()
                txt.SetFocus()
                break
        if dlg.ShowModal() == wx.ID_OK:
            if GalleryDict.exists(dlg.GetValue()):
                wx.MessageDialog(
                    self,
                    'Cannot rename with already existing label.',
                    'Label already existing',
                    wx.OK | wx.ICON_WARNING).ShowModal()
                dlg.Destroy()
                return
            _, org_reference = GalleryDict.get_reference(
                self.gallery_selector_lbx.GetStringSelection())
            GalleryDict.set(  # add a new entry with its binary and reference
                dlg.GetValue(),
                self.construct_hex_editor.binary,
                reference=org_reference)
            if dlg.GetValue() != self.gallery_selector_lbx.GetStringSelection():
                GalleryDict.delete(  # remove the old entry
                    self.gallery_selector_lbx.GetStringSelection())
            self.gallery_selector_lbx.SetString(  # change the label in the lbx
                self.gallery_selector_lbx.GetSelection(), dlg.GetValue())
        dlg.Destroy()
        self.skip_add_selection = False

    def duplicate_selection(self):
        if not self.construct_hex_editor:
            return
        if self.gallery_selector_lbx.GetCount() == 0:
            self.add_selection()
            return
        dlg = wx.TextEntryDialog(
            self,
            'Enter the label of the duplicated entry',
            'Duplicate label and value')
        dlg.SetValue(self.gallery_selector_lbx.GetStringSelection())
        for txt in dlg.Children:
            if isinstance(txt, wx._core.TextCtrl):
                txt.SelectAll()
                txt.SetFocus()
                break
        if dlg.ShowModal() == wx.ID_OK:
            if GalleryDict.exists(dlg.GetValue()):
                wx.MessageDialog(
                    self,
                    'Label already existing',
                    'Cannot duplicate value.',
                    wx.OK | wx.ICON_WARNING).ShowModal()
                dlg.Destroy()
                return
            _, org_reference = GalleryDict.get_reference(
                self.gallery_selector_lbx.GetStringSelection())
            if dlg.GetValue() != self.gallery_selector_lbx.GetStringSelection():
                GalleryDict.set(dlg.GetValue(),
                    self.construct_hex_editor.binary,
                    reference=org_reference)
                self.gallery_selector_lbx.InsertItems([dlg.GetValue()],
                    self.gallery_selector_lbx.GetSelection())
        dlg.Destroy()

    def move_selection_up(self):
        if not self.construct_hex_editor:
            return
        curr = self.gallery_selector_lbx.GetSelection()
        if curr <= 0:
            return
        self.gallery_selector_lbx.InsertItems(
            [self.gallery_selector_lbx.GetStringSelection()], curr - 1)
        self.gallery_selector_lbx.Delete(curr + 1)
        self.gallery_selector_lbx.SetSelection(curr - 1)

    def move_selection_down(self):
        if not self.construct_hex_editor:
            return
        curr = self.gallery_selector_lbx.GetSelection()
        if curr + 1 >= self.gallery_selector_lbx.GetCount():
            return
        if curr + 2 == self.gallery_selector_lbx.GetCount():
            self.gallery_selector_lbx.Append(
                self.gallery_selector_lbx.GetStringSelection())
            self.gallery_selector_lbx.Delete(curr)
            self.gallery_selector_lbx.SetSelection(curr + 1)
            return
        self.gallery_selector_lbx.InsertItems(
            [self.gallery_selector_lbx.GetStringSelection()], curr + 2)
        self.gallery_selector_lbx.Delete(curr)
        self.gallery_selector_lbx.SetSelection(curr + 1)

    def change_reference_selection(self):
        if not self.construct_hex_editor:
            return
        if not self.reference_label:
            return
        element = self.gallery_selector_lbx.GetStringSelection()
        _, org_reference = GalleryDict.get_reference(element)
        if org_reference is None:
            return
        org_key = None
        org_description = None
        confirm = ''
        if org_reference:
            _, _, _, org_key = GalleryDict.get_key(element, interactive=True)
            _, _, _, org_description = GalleryDict.get_description(
                element, interactive=True)
            confirm = ' or confirm the current one'
        dlg = wx.TextEntryDialog(
            self,
            'Enter the ' + self.reference_label + confirm + ':',
            'Change the ' + self.reference_label)
        dlg.SetValue(org_reference)
        for txt in dlg.Children:
            if isinstance(txt, wx._core.TextCtrl):
                txt.SelectAll()
                txt.SetFocus()
                break
        if dlg.ShowModal() == wx.ID_OK:
            GalleryDict.set_reference(element, dlg.GetValue())
            if org_key is not None:
                GalleryDict.set_key(element, org_key)
            if org_description is not None:
                GalleryDict.set_description(element, org_description)
            self.rebuild_bytes_selection()
        self.on_gallery_selection_changed(None)
        dlg.Destroy()

    def change_key_selection(self):
        if not self.construct_hex_editor:
            return
        if not self.key_label:
            return
        element = self.gallery_selector_lbx.GetStringSelection()
        _, _, _, org_key = GalleryDict.get_key(element, interactive=True)
        if org_key is None:
            return
        confirm = ''
        if org_key:
            confirm = ' or confirm the current one'
        dlg = wx.TextEntryDialog(
            self,
            'Enter the ' + self.key_label + confirm + ':',
            'Change the ' + self.key_label)
        dlg.SetValue(org_key)
        for txt in dlg.Children:
            if isinstance(txt, wx._core.TextCtrl):
                txt.SelectAll()
                txt.SetFocus()
                break
        if dlg.ShowModal() == wx.ID_OK:
            GalleryDict.set_key(element, dlg.GetValue())
            self.rebuild_bytes_selection()
        self.on_gallery_selection_changed(None)
        dlg.Destroy()

    def rebuild_bytes_selection(self):
        selection = self.gallery_selector_lbx.GetSelection()
        try:
            new_bytes = self.construct_hex_editor.construct_editor.build(
                **GalleryDict.get_contextkw(
                    self.gallery_selector_lbx.GetStringSelection()
                )
            )
        except ValueError as e:
            dlg = wx.MessageDialog(
                None,
                str(e),
                "Cannot build bytes after changing parameters",
                wx.OK | wx.ICON_WARNING
            )
            dlg.ShowModal()
            dlg.Destroy()
            return
        if new_bytes:
            self.construct_hex_editor.binary = new_bytes
            GalleryDict.set(
                self.gallery_selector_lbx.GetStringSelection(),
                new_bytes
            )
            self.gallery_selector_lbx.SetSelection(selection)

    def change_description_selection(self):
        if not self.construct_hex_editor:
            return
        if not self.description_label:
            return
        element = self.gallery_selector_lbx.GetStringSelection()
        _, _, _, org_description = GalleryDict.get_description(
            element, interactive=True)
        if org_description is None:
            return
        confirm = ''
        if org_description:
            confirm = ' or confirm the current one'
        dlg = wx.TextEntryDialog(
            self,
            'Enter the ' + self.description_label + confirm + ':',
            'Change the ' + self.description_label)
        dlg.SetValue(org_description)
        for txt in dlg.Children:
            if isinstance(txt, wx._core.TextCtrl):
                txt.SelectAll()
                txt.SetFocus()
                break
        if dlg.ShowModal() == wx.ID_OK:
            GalleryDict.set_description(element, dlg.GetValue())
            self.rebuild_bytes_selection()
        self.on_gallery_selection_changed(None)
        dlg.Destroy()

    def on_key_down_log(self, event):
        event.Skip()
        if not self.construct_hex_editor:
            return
        #print("KeyCode: %d" % event.GetKeyCode())
        #print("ListBox Item Index: %d" % event.GetEventObject().GetSelection())
        #print("ListBox count:", event.GetEventObject().GetCount())
        #print("log count:", GalleryDict.len())
        if event.ShiftDown():
            return
        if event.AltDown():
            return
        if event.ControlDown():
            return
        if event.GetKeyCode() == 341:  # F2
            self.change_selection()
        if event.GetKeyCode() == 342:  # F3
            self.duplicate_selection()
        if event.GetKeyCode() == 343:  # F4
            self.add_selection()
        if event.GetKeyCode() == 344:  # F5
            self.move_selection_up()
        if event.GetKeyCode() == 345:  # F6
            self.move_selection_down()
        if event.GetKeyCode() == 346:  # F7
            self.change_reference_selection()
        if event.GetKeyCode() == 347:  # F8
            self.change_key_selection()
        if event.GetKeyCode() == 348:  # F9
            self.change_description_selection()
        if event.GetKeyCode() == 127:  # Delete key
            obj = event.GetEventObject()
            self.delete_selection(obj)

    def delete_selection(self, obj):
        if not self.construct_hex_editor:
            return
        index = obj.GetSelection()
        GalleryDict.pop(self.gallery_selector_lbx.GetStringSelection())
        self.previous_selection = None
        if index < 0:
            if GalleryDict.len() == 0:
                self.status_message("Empty list")
            return
        self.gallery_selector_lbx.Delete(index)
        if obj.GetCount() > 0:
            if index < obj.GetCount():
                obj.SetSelection(index)
                self.construct_hex_editor.contextkw = GalleryDict.get_contextkw(
                    self.gallery_selector_lbx.GetStringSelection())
                self.construct_hex_editor.binary = (
                    GalleryDict.get_binary(
                        self.gallery_selector_lbx.GetStringSelection()))
                self.previous_selection = self.construct_hex_editor.binary
                self.status_message("Selected element n. " +
                    str(index + 1) + ': "' +
                    self.gallery_selector_lbx.GetStringSelection() + '"')
            else:
                obj.SetSelection(index - 1)
                self.construct_hex_editor.contextkw = GalleryDict.get_contextkw(
                    self.gallery_selector_lbx.GetStringSelection())
                self.construct_hex_editor.binary = (
                    GalleryDict.get_binary(
                        self.gallery_selector_lbx.GetStringSelection()))
                self.previous_selection = self.construct_hex_editor.binary
                self.status_message("Selected element n. " +
                    str(index) + ': "' +
                    self.gallery_selector_lbx.GetStringSelection() + '"')
        else:
            if GalleryDict.len() == 0:
                self.status_message("Empty list")
                self.previous_selection = None

    def change_gallery_selection(self):
        if not self.construct_hex_editor:
            return
        gallery_item = self.gallery_descriptor[
            self.construct_selector_lbx.GetStringSelection()]
        GalleryDict.set_fixed_contextkw(gallery_item.contextkw)
        self.used_construct = gallery_item.construct
        self.construct_hex_editor.construct = self.used_construct
        if gallery_item.clear_log:
            self.previous_selection = None
            self.clear_log()
        if len(gallery_item.example_bytes) > 0:
            for i in gallery_item.example_bytes:
                self.add_data(
                    data=gallery_item.example_bytes[i],
                    label=i,
                    discard_duplicates=True)
            self.gallery_selector_lbx.SetStringSelection(
                list(gallery_item.example_bytes.keys())[0]
            )
            self.previous_selection = self.gallery_selector_lbx.GetStringSelection()
        if len(gallery_item.example_dict) > 0:
            GalleryDict.update_dict(gallery_item.example_dict)
            for i in GalleryDict.keys():
                if i not in self.gallery_selector_lbx.GetItems():
                    self.gallery_selector_lbx.Append(i)
        if gallery_item.example_key:
            GalleryDict.update_key_descr_dict(gallery_item.example_key)
        if self.gallery_selector_lbx.GetStringSelection():
            sample_binary = GalleryDict.get_binary(
                self.gallery_selector_lbx.GetStringSelection())
            self.construct_hex_editor.contextkw = GalleryDict.get_contextkw(
                self.gallery_selector_lbx.GetStringSelection())
            self.construct_hex_editor.binary = sample_binary
            self.construct_hex_editor.construct_editor.expand_all()

    def on_right_clicked(self, event):
        if not self.construct_hex_editor:
            return
        obj = event.GetEventObject()
        if not isinstance(obj, wx.ListBox):
            return
        item = obj.HitTest(event.GetPosition())
        if item < 0:
            return
        self.gallery_selector_lbx.SetSelection(item)
        #value = self.gallery_selector_lbx.GetString(item)
        popup_menu = wx.Menu()
        for menu in self.build_list_context_menu(obj):
            if menu is None:
                popup_menu.AppendSeparator()
                continue
            if menu.toggle_state != None:  # checkbox boolean state
                item: wx.MenuItem = popup_menu.AppendCheckItem(menu.wx_id, menu.name)
                item.Check(menu.toggle_state)
            else:
                item: wx.MenuItem = popup_menu.Append(menu.wx_id, menu.name)
            self.Bind(wx.EVT_MENU, menu.callback, id=item.Id)
            item.Enable(menu.enabled)

        self.PopupMenu(popup_menu, event.GetPosition())
        popup_menu.Destroy()

    def build_list_context_menu(
        self, obj
    ) -> t.List[t.Optional[ContextMenuItem]]:
        """Build the context menu. Can be overridden."""

        menu_list = [
            ContextMenuItem(
                wx.ID_ANY,
                "Rename\tF2",
                lambda event: self.change_selection(),
                None,
                True,
            ),
            ContextMenuItem(
                wx.ID_ANY,
                "Duplicate below\tF3",
                lambda event: self.duplicate_selection(),
                None,
                True,
            ),
            ContextMenuItem(
                wx.ID_ANY,
                "Add at the bottom\tF4",
                lambda event: self.add_selection(),
                None,
                True,
            ),
            ContextMenuItem(
                wx.ID_ANY,
                "Delete\tDEL",
                lambda event: self.delete_selection(obj),
                None,
                True,
            ),
            ContextMenuItem(
                wx.ID_ANY,
                "Move up\tF5",
                lambda event: self.move_selection_up(),
                None,
                True,
            ),
            ContextMenuItem(
                wx.ID_ANY,
                "Move down\tF6",
                lambda event: self.move_selection_down(),
                None,
                True,
            )
        ]
        if self.reference_label or self.key_label or self.description_label:
            menu_list += [None]
        if self.reference_label:
            menu_list += [ContextMenuItem(
                wx.ID_ANY,
                "Change " + self.reference_label + "\tF7",
                lambda event: self.change_reference_selection(),
                None,
                True,
            )]
        if self.key_label:
            menu_list += [ContextMenuItem(
                wx.ID_ANY,
                "Change " + self.key_label + "\tF8",
                lambda event: self.change_key_selection(),
                None,
                True,
            )]
        if self.description_label:
            menu_list += [ContextMenuItem(
                wx.ID_ANY,
                "Change " + self.description_label + "\tF9",
                lambda event: self.change_description_selection(),
                None,
                True,
            )]
        return menu_list

    def on_mouse_motion(self, event):  # Add tooltip
        obj = event.GetEventObject()
        if isinstance(obj, wx.ListBox):
            item = obj.HitTest(event.GetPosition())
            if item == self.gallery_tooltip_item:
                return  # avoid tooltip flickering when moving mouse
            self.gallery_tooltip_item = item
            if item >= 0:
                value = self.gallery_selector_lbx.GetString(item)
                _, reference, _, description = GalleryDict.get_description(
                    value)
                if description:
                    reference = description
                obj.SetToolTip(reference)

    def on_leave_window(self, event):  # Remove tooltip
        obj = event.GetEventObject()
        self.gallery_tooltip_item = None
        if isinstance(obj, wx.ListBox):
            obj.SetToolTip(None)

    def on_gallery_selection_changed(self, event):
        if not self.construct_hex_editor:
            return
        if (GalleryDict.len() > 0 and
                self.previous_selection !=
                self.gallery_selector_lbx.GetStringSelection()):
            if (self.previous_selection is not None and
                    self.previous_selection and
                    GalleryDict.exists(self.previous_selection) and
                    self.construct_hex_editor.binary !=
                    GalleryDict.get_binary(self.previous_selection)):
                if (wx.MessageDialog(
                        self,
                        'Save previously modified data?',
                        'Data not saved',
                        wx.YES_NO | wx.ICON_WARNING).ShowModal() == wx.ID_YES):
                    GalleryDict.set(self.previous_selection,
                        self.construct_hex_editor.binary)
            elif (self.previous_selection is None and
                    GalleryDict.exists(
                        self.gallery_selector_lbx.GetStringSelection()) and
                    GalleryDict.get_binary(
                            self.gallery_selector_lbx.GetStringSelection()) !=
                        self.construct_hex_editor.binary and
                    self.construct_hex_editor.binary != b''):
                if (wx.MessageDialog(
                        self,
                        'Replace saved data with new value?',
                        'Value was changed',
                        wx.YES_NO | wx.ICON_WARNING).ShowModal() == wx.ID_YES):
                    GalleryDict.set(
                        self.gallery_selector_lbx.GetStringSelection(),
                        self.construct_hex_editor.binary
                    )
        else:
            if (GalleryDict.len() > 0 and
                    GalleryDict.exists(
                        self.gallery_selector_lbx.GetStringSelection()) and
                    GalleryDict.get_binary(
                            self.gallery_selector_lbx.GetStringSelection()) !=
                        self.construct_hex_editor.binary):
                if (wx.MessageDialog(
                        self,
                        'Replace saved data with new value?',
                        'Value was changed',
                        wx.YES_NO | wx.ICON_WARNING).ShowModal() == wx.ID_YES):
                    GalleryDict.set(
                        self.gallery_selector_lbx.GetStringSelection(),
                        self.construct_hex_editor.binary)
        self.previous_selection = self.gallery_selector_lbx.GetStringSelection()
        sample_binary = GalleryDict.get_binary(
            self.gallery_selector_lbx.GetStringSelection())

        # Set example binary
        self.construct_hex_editor.contextkw = GalleryDict.get_contextkw(
            self.gallery_selector_lbx.GetStringSelection())
        self.construct_hex_editor.binary = sample_binary
        self.construct_hex_editor.construct_editor.expand_all()

        if not event:
            return
        index = event.GetEventObject().GetSelection()
        self.status_message("Selected element n. " + str(index + 1) + ': "' +
            self.gallery_selector_lbx.GetStringSelection() + '"')

    def add_data(self,
            data,
            reference=None,
            label=None,
            append_label=None,
            discard_duplicates=False):
        if not self.construct_hex_editor.IsShown():
            self.construct_hex_editor.construct_editor.Show()
            self.construct_hex_editor.contextkw = GalleryDict.get_contextkw(
                reference)
            self.construct_hex_editor.binary = data
        if GalleryDict.len() == 0:
            self.status_message(self.added_data_label)
        if not label:
            utc_dt = datetime.now(timezone.utc)
            label = utc_dt.astimezone().strftime(
                '%y-%m-%d %H:%M:%S.%f').strip()
            if append_label:
                label = label + " " + append_label
        if GalleryDict.exists(label):
            if discard_duplicates:
                return True
            for i in range(1000):
                new_label = label + "-" + str(i)
                if not GalleryDict.exists(new_label):
                    label = new_label
                    break
            if GalleryDict.exists(label):
                return False
        GalleryDict.set(label, data, reference)
        self.gallery_selector_lbx.Append(label)
        return True


if __name__ == "__main__":
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
    ConstructGallery(frame, gallery_descriptor=gallery_descriptor)
    frame.Show(True)
    app.MainLoop()
