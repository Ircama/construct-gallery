# edit_plugin for the HexEditorGrid

import wx
from construct_editor.wx_widgets.wx_hex_editor import ContextMenuItem
from .string_convert_plugin import HexDump
import construct
import re


class MultiLineTextEntryDialog(wx.Dialog):
    def __init__(
        self, parent, title, label='', value_bytes='', input_bytes=False
    ):
        super(MultiLineTextEntryDialog, self).__init__(parent, title=title)

        self.parent = parent
        self.input_bytes = input_bytes
        self.panel = wx.Panel(self)
        self.label = wx.StaticText(self.panel, label=label)
        default_value = value_bytes
        if input_bytes:
            default_value = value_bytes.hex(' ')
        try:
            self.text_ctrl = wx.TextCtrl(
                self.panel,
                style=wx.TE_MULTILINE,
                value=default_value
            )
        except UnicodeDecodeError:
            self.text_ctrl = wx.TextCtrl(
                self.panel,
                style=wx.TE_MULTILINE
            )
        current_font = self.text_ctrl.GetFont()
        fixed_font = wx.Font(
            current_font.GetPointSize(),
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL
        )
        self.text_ctrl.SetFont(fixed_font)
        self.text_ctrl.Bind(wx.EVT_TEXT, self.on_text_change)

        if self.parent._selection[1] is not None:
            label = "Insert/shrink replacing selection"
        else:
            label = "Insert before"
        self.insert_button = wx.Button(
            self.panel, wx.ID_OK, label=label
        )
        self.replace_button = wx.Button(
            self.panel, wx.ID_OK, label='Replace'
        )
        self.overwrite_all_button = wx.Button(
            self.panel, wx.ID_OK, label='Overwrite all'
        )
        self.cancel_button = wx.Button(
            self.panel, wx.ID_CANCEL, label='Cancel'
        )

        char_width, char_height = self.text_ctrl.GetTextExtent('A')
        self.dump = wx.TextCtrl(
            self.panel,
            size=wx.Size(char_width * 90, char_height * 5.5),
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            value=""
        )

        save = self.parent.allow_python
        self.parent.allow_python = None
        self.on_text_change(False)
        self.parent.allow_python = save

        self.dump.SetFont(fixed_font)
        self.dump.SetBackgroundColour(wx.LIGHT_GREY)

        self.insert_button.Bind(wx.EVT_BUTTON, self.on_insert)
        self.replace_button.Bind(wx.EVT_BUTTON, self.on_replace)
        self.overwrite_all_button.Bind(wx.EVT_BUTTON, self.on_overwrite_all)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)

        self.setup_layout(value_bytes)

    def string_to_byts_no_python(self, entered_text):
        save = self.parent.allow_python
        self.parent.allow_python = None
        value_bytes = self.parent.string_to_byts(entered_text)
        self.parent.allow_python = save
        return value_bytes

    def on_text_change(self, event):
        sep = u"\u250a"  # thin vertical dotted bar
        entered_text = self.text_ctrl.GetValue()
        if self.input_bytes:
            value_bytes = self.string_to_byts_no_python(entered_text)
        else:
            value_bytes = entered_text.encode()
        text = ""
        for addr, bytes_dump, str_dump in HexDump(value_bytes):
            text += (
                f"{addr:<9}"
                + sep
                + f"{bytes_dump:<52}"
                + sep
                + f" {str_dump:<16}\n"
            )
        self.dump.SetValue(text)

        self.panel.SetSizer(None)
        self.panel.Layout()
        self.hsizer = wx.BoxSizer(wx.HORIZONTAL)

    def setup_layout(self, value_bytes):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.label, 0, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(self.text_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(wx.StaticLine(self.panel), 0, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(self.dump, 1, wx.ALL | wx.EXPAND, 5)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.insert_button, 0, wx.ALL, 5)
        button_sizer.Add(self.replace_button, 0, wx.ALL, 5)
        button_sizer.Add(self.overwrite_all_button, 0, wx.ALL, 5)
        button_sizer.Add(self.cancel_button, 0, wx.ALL, 5)

        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        self.panel.SetSizer(main_sizer)
        main_sizer.Fit(self)

    def on_insert(self, event):
        value = self.text_ctrl.GetValue().encode()
        if self.input_bytes:
            value = self.parent.string_to_byts(self.text_ctrl.GetValue())
            if value is False:
                value = self.string_to_byts_no_python(self.text_ctrl.GetValue())
        if not value or not len(value):
            self.EndModal(wx.ID_CANCEL)
            return
        if self.parent._selection[1] is not None:
            length = self.parent._selection[1] - self.parent._selection[0] + 1
            self.parent._binary_data.overwrite_range(
                self.parent._selection[0], value[:length]
            )
            if len(value) > length:
                self.parent._binary_data.insert_range(
                    self.parent._selection[1] + 1, value[length:]
                )
            self.parent.select_range(
                self.parent._selection[0],
                self.parent._selection[0] + len(value) - 1
            )
            if len(value) < length:
                self.parent._binary_data.remove_range(
                    self.parent._selection[1] + len(value),
                    length - len(value)
                )
        else:
            self.parent._binary_data.insert_range(
                self.parent._selection[0], value
            )
        self.EndModal(wx.ID_OK)

    def on_replace(self, event):
        value = self.text_ctrl.GetValue().encode()
        if self.input_bytes:
            value = self.parent.string_to_byts(self.text_ctrl.GetValue())
            if value is False:
                value = self.string_to_byts_no_python(self.text_ctrl.GetValue())
        if not value or not len(value):
            self.EndModal(wx.ID_CANCEL)
            return
        self.parent._binary_data.overwrite_range(
            self.parent._selection[0], value
        )
        self.EndModal(wx.ID_OK)

    def on_overwrite_all(self, event):
        value = self.text_ctrl.GetValue().encode()
        if self.input_bytes:
            value = self.parent.string_to_byts(self.text_ctrl.GetValue())
            if value is False:
                value = self.string_to_byts_no_python(self.text_ctrl.GetValue())
        if not value or not len(value):
            self.EndModal(wx.ID_CANCEL)
            return
        self.parent._binary_data.overwrite_all(value)
        self.parent.select_range(0, len(value) - 1)
        self.EndModal(wx.ID_OK)

    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)


class HexEditorGrid:
    def _on_write_string(self, title, label, input_bytes) -> bool:
        sel = self._selection
        if sel[0] is None:
            return False
        if sel[1] == None:
            length = 1
        else:
            length = sel[1] - sel[0] + 1
        value_bytes = self._binary_data.get_range(sel[0], length)

        dlg = MultiLineTextEntryDialog(
            self,
            title=title,
            label=label,
            value_bytes=value_bytes,
            input_bytes=input_bytes
        )
        dlg.ShowModal()
        dlg.Destroy()

    def build_context_menu(self):
        menus = super().build_context_menu()
        menus.append(
            ContextMenuItem(
                wx_id=wx.ID_ANY,
                name="Edit UTF-8 text",
                callback=lambda event: self._on_write_string(
                    title='Edit UTF-8 text',
                    label='Enter UTF-8 text:',
                    input_bytes=False
                ),
                toggle_state=None,
                enabled=True,
            )
        )
        menus.append(
            ContextMenuItem(
                wx_id=wx.ID_ANY,
                name="Edit bytes",
                callback=lambda event: self._on_write_string(
                    title='Edit bytes',
                    label='Enter bytes:',
                    input_bytes=True
                ),
                toggle_state=None,
                enabled=True,
            )
        )
        return menus
