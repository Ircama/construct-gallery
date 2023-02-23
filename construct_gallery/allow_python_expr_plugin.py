# allow_python_expr_plugin for the HexEditorGrid

import wx
from construct_editor.wx_widgets.wx_hex_editor import ContextMenuItem
from tokenize import tokenize, NAME, STRING, TokenError
from io import BytesIO
from multiprocessing import Process, Queue


def python_expression(q, x):
    """Evaluate Python Expression 'x' and return result to queue 'q'."""
    try:
        q.put(eval(x, {}, {}))
    except Exception:
        q.put(None)


class HexEditorGrid:
    safe_tokens = [
        "bytes", "fromhex", "int", "False", "True", "len", "str", "strip",
        "not", "or", "and", "in", "for", "i", "range", "if", "else", "title",
        "lower", "upper", "count", "hex", "decode", "encode", "endswith",
        "startswith", "join", "lstrip", "replace", "rstrip", "split", "rsplit",
        "lsplit", "zfill", "n"
    ]
    allow_python = False

    def _on_allow_python(self) -> bool:
        """
        Toggle the "allow pasting Python from clipboard" checkbox
        on the context menu of the hex editor
        """
        self.allow_python = not self.allow_python

    def build_context_menu(self):
        menus = super().build_context_menu()
        menus.append(
            ContextMenuItem(
                wx_id=wx.ID_ANY,
                name="Allow pasting Python expression",
                callback=lambda event: self._on_allow_python(),
                toggle_state=self.allow_python,
                enabled=not self.read_only,
            )
        )
        return menus

    def string_to_byts(self, byts_str: str):
        if not self.allow_python:
            return super().string_to_byts(byts_str)
        self._editor._status_bar.SetStatusText(
            "Processing Python expression...", 1)
        try:
            g = tokenize(BytesIO(byts_str.encode('utf-8')).readline)
            for toknum, tokval, _, _, _ in g:
                if ((toknum == STRING and tokval.strip().startswith('f')) or
                        (toknum == NAME and tokval not in self.safe_tokens)):
                    self._editor._status_bar.SetStatusText("", 1)
                    wx.MessageBox(
                        f'Unauthorized token "{tokval}" included in '
                        f"input data.\n\nClipboard Data:\n{byts_str}",
                        "Warning",
                    )
                    return False
        except TokenError as e:
            self._editor._status_bar.SetStatusText("", 1)
            wx.MessageBox(
                f"Malformed input data.\n\n{str(e)}"
                f"\n\nClipboard Data:\n{byts_str}",
                "Warning",
            )
            return False
        try:
            q = Queue()
            p = Process(target=python_expression, args=(q, byts_str.strip()))
            p.start()
            byts = q.get(timeout=2.0)  # Stop too complex expression
            p.terminate()
            if isinstance(byts, tuple):
                try:
                    byts = bytes(byts)
                except Exception:
                    pass
            if not isinstance(byts, bytes):
                self._editor._status_bar.SetStatusText("", 1)
                wx.MessageBox(
                    f"Improper Python expression in the clipboard"
                    '\n\nData must be <class \'bytes\'> '
                    f'and not {type(byts)}.'
                    f"\n\nClipboard Data:\n{byts_str}",
                    "Warning",
                )
                return False
        except Exception as e:
            self._editor._status_bar.SetStatusText("", 1)
            wx.MessageBox(
                f"Can't convert data from clipboard to bytes.\n\n{str(e)}"
                f"\n\nClipboard Data:\n{byts_str}",
                "Warning",
            )
            return False
        return byts
