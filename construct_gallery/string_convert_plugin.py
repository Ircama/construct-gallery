# string_convert_plugin for the HexEditorGrid

import wx
from construct_editor.wx_widgets.wx_hex_editor import ContextMenuItem
import construct
import re


class HexDump:
    def __init__(self, buf, off=0):
        self.buf = buf
        self.off = off

    def __iter__(self):
        last_bs, last_line = None, None
        for i in range(0, len(self.buf), 16):
            bs = bytearray(self.buf[i : i + 16])
            addr = "{:08x}".format(self.off + i)
            line = "  {:23}  {:23}  ".format(
                " ".join(("{:02x}".format(x) for x in bs[:8])),
                " ".join(("{:02x}".format(x) for x in bs[8:])),
            )
            str_repr = "{:16}".format(
                "".join((chr(x) if 32 <= x < 127 else "." for x in bs)),
            )
            if bs == last_bs:
                addr = "*"
                line = ""
                str_repr = ""
            if bs != last_bs or line != last_line:
                yield addr, line, str_repr
            last_bs, last_line = bs, line
        yield "{:08x}".format(self.off + len(self.buf)), "", ""

    def __str__(self):
        buf = ""
        for addr, line, str_repr in self:
            if str_repr:
                buf += addr + line + '[' + str_repr + ']\n'
            else:
                buf += addr + line + '\n'
        return buf

    def __repr__(self):
        return self.__str__()


class StringConvertDialog(wx.Dialog):
    def _add_text_line(self, sizer, left_label, center_label, right_label):
        box = wx.BoxSizer(wx.HORIZONTAL)
        text_left = wx.StaticText(self, -1, left_label)
        text_left.SetFont(self.font)
        text_left.SetForegroundColour('BLACK')
        text_center = wx.StaticText(self, -1, center_label)
        text_center.SetFont(self.font)
        text_center.SetForegroundColour('RED')
        text_right = wx.StaticText(self, -1, right_label)
        text_right.SetFont(self.font)
        text_right.SetForegroundColour('BLUE')
        box.Add(text_left, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        box.Add(text_center, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        box.Add(text_right, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        sizer.Add(box, 0, wx.GROW|wx.ALL, 0)

    def __init__(
            self,
            parent,
            caption,
            value_bytes,
            button_style):
        dialog_style = wx.DEFAULT_DIALOG_STYLE
        super(StringConvertDialog, self).__init__(
            parent, -1, caption, style=dialog_style)

        self.font = self.GetFont()
        self.font.SetFamily(wx.FONTFAMILY_MODERN)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(wx.StaticLine(self), 0, wx.ALL | wx.EXPAND, 5)
        """
        try:
            text_val = " ".join("%02x" % b for b in value_bytes).upper()
            n = 81
            text_val = [text_val[i:i+n] for i in range(0, len(text_val), n)]
        except Exception:
            text_val = ["error, improper selection"]
        head = "Input value"
        for i in text_val:
            self._add_text_line(main_sizer, head, "", i)
            head = "           "
        main_sizer.Add(wx.StaticLine(self), 0, wx.ALL | wx.EXPAND, 5)
        """
        n = 70
        bytes_val = [value_bytes[i:i+n] for i in range(0, len(value_bytes), n)]
        head = "UTF-8"
        for i in bytes_val:
            self._add_text_line(
                main_sizer, head, "", i.decode(errors='ignore'))
            head = "     "
        main_sizer.Add(wx.StaticLine(self), 0, wx.ALL | wx.EXPAND, 5)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer = wx.BoxSizer(wx.VERTICAL)

        for addr, bytes_dump, str_dump in HexDump(value_bytes):
            self._add_text_line(
                sizer, addr, bytes_dump, str_dump)
        hsizer.Add(sizer, 0, wx.ALL | wx.EXPAND, 2)

        main_sizer.Add(hsizer, 1, wx.EXPAND)
        main_sizer.Add(
            wx.StaticLine(self), 0, wx.TOP | wx.BOTTOM | wx.EXPAND, 5)

        buttons = self.CreateButtonSizer(button_style)
        main_sizer.Add(buttons, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizerAndFit(main_sizer)
        if self.GetSize()[0] < 150:
            self.SetSize(wx.Size(150, -1))
        if self.GetSize()[1] < 100:
            self.SetSize(wx.Size(-1, 100))

class HexEditorGrid:
    def _on_string_convert(self) -> bool:
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
        dlg = StringConvertDialog(
            self,
            "UTF-8 string conversion",
            value_bytes,
            button_style=wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def build_context_menu(self):
        menus = super().build_context_menu()
        menus.append(
            ContextMenuItem(
                wx_id=wx.ID_ANY,
                name="Convert to UTF-8 string",
                callback=lambda event: self._on_string_convert(),
                toggle_state=None,
                enabled=True,
            )
        )
        return menus
