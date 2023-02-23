# decimal_convert_plugin for the HexEditorGrid

import wx
from construct_editor.wx_widgets.wx_hex_editor import ContextMenuItem
import construct
import re


class DecimalConvertDialog(wx.Dialog):
    def _add_text_line(self, sizer, left_label, right_label):
        box = wx.BoxSizer(wx.HORIZONTAL)
        text_left = wx.StaticText(self, -1, left_label + ":")
        text_left.SetForegroundColour('BLACK')
        text_right = wx.StaticText(self, -1, right_label)
        text_right.SetForegroundColour('BLUE')
        box.Add(text_left, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        box.Add(text_right, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        sizer.Add(box, 0, wx.GROW|wx.ALL, 0)

    def _conv(self, constr, value_bytes, error="error, cannot convert"):
        try:
            return str(constr.parse(value_bytes))
        except Exception:
            return error

    def __init__(
            self,
            parent,
            caption,
            value_bytes,
            button_style):
        dialog_style = wx.DEFAULT_DIALOG_STYLE
        super(DecimalConvertDialog, self).__init__(
            parent, -1, caption, style=dialog_style)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        main_sizer.Add(wx.StaticLine(self), 0, wx.ALL | wx.EXPAND, 5)
        try:
            text_val = " ".join("%02x" % b for b in value_bytes).upper()
        except Exception:
            text_val = "error, improper selection"
        self._add_text_line(main_sizer, "Input value", text_val)
        main_sizer.Add(wx.StaticLine(self), 0, wx.ALL | wx.EXPAND, 5)

        int_set = [i for i in dir(construct)
            if re.search(r'^Int[0-9]|^Float[0-9]', i)]
        int_set += ["Byte", "Int", "Long", "Double", "Short"]

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer = wx.BoxSizer(wx.VERTICAL)
        count = 0
        for i in int_set:
            self._add_text_line(
                sizer, i, self._conv(getattr(construct, i), value_bytes))
            count += 1
            if count % 20 == 0:
                hsizer.Add(sizer, 0, wx.ALL | wx.EXPAND, 2)
                sizer = wx.BoxSizer(wx.VERTICAL)
        if count % 20:
            hsizer.Add(sizer, 0, wx.ALL | wx.EXPAND, 2)

        main_sizer.Add(hsizer, 1, wx.EXPAND)
        main_sizer.Add(
            wx.StaticLine(self), 0, wx.TOP | wx.BOTTOM | wx.EXPAND, 5)

        buttons = self.CreateButtonSizer(button_style)
        main_sizer.Add(buttons, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizerAndFit(main_sizer)
        if self.GetSize()[0] < 150:
            self.SetSize(wx.Size(150, -1))
        if self.GetSize()[1] < 500:
            self.SetSize(wx.Size(-1, 400))

class HexEditorGrid:
    def _on_decimal_convert(self) -> bool:
        """
        Convert selected data to values using construct fields
        """
        sel = self._selection
        if sel[0] is None:
            return False
        if sel[1] == None:
            length = 1
        else:
            length = sel[1] - sel[0] + 1
        value_bytes = self._binary_data.get_range(sel[0], length)
        dlg = DecimalConvertDialog(
            self,
            "Decimal conversion",
            value_bytes,
            button_style=wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def build_context_menu(self):
        menus = super().build_context_menu()
        menus.append(
            ContextMenuItem(
                wx_id=wx.ID_ANY,
                name="Convert to decimal",
                callback=lambda event: self._on_decimal_convert(),
                toggle_state=None,
                enabled=True,
            )
        )
        return menus
