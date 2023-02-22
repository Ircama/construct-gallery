import wx
import os
from wx.py.shell import ShellFrame


class PyShellPlugin():
    def py_shell(self):
        self.pyshell = None
        self.pyshell_help = None

        # Open Python Shell button
        self.open_shell_btn = wx.Button(
            self,
            wx.ID_ANY,
            "Open Python Shell",
            wx.DefaultPosition,
            wx.DefaultSize,
            0,
        )
        self.vsizer.Add(self.open_shell_btn, 0, wx.ALL | wx.EXPAND, 1)
        self.open_shell_btn.Bind(wx.EVT_BUTTON, self.on_open_shell_clicked)

    def on_pyshell_help(self, event):
        """Display a specific help window for the Packet Log Inspector Shell."""

        HELP_TEXT = """\
---------------------------------------
Help for the Packet Log Inspector Shell
---------------------------------------

All locals and globals can be used. "self" works for instance.
Use "frame" for the main frame, meaning "self.GetTopLevelParent()"

For multiline instructions, wrap them into a function and then call the function.

_________________________________________

To hide the construct_hex_editor:
self.construct_hex_editor.Hide()
_________________________________________

To show the construct_hex_editor:
self.construct_hex_editor.Show();self.construct_hex_editor.GetParent().Layout()
_________________________________________

To parse a new string:
frame.main_panel.construct_hex_editor.contextkw = { "key": "value", ... }
frame.main_panel.construct_hex_editor.binary = bytes.fromhex("...")
_________________________________________

To expand all fields:
frame.main_panel.construct_hex_editor.construct_editor.expand_all()
_________________________________________

To change the parser:
frame.main_panel.construct_hex_editor.construct = ...construct...
_________________________________________

To set the root variable to the parsed structure:
root = frame.main_panel.construct_hex_editor.construct_editor._model.root_obj
_________________________________________

To write data to the status line:

frame.SetStatusText("...")
_________________________________________

To read the status line:

frame.GetStatusBar().GetStatusText()
"""

        if self.pyshell_help:
            self.pyshell_help.Raise()
            self.pyshell_help.Show()
            return
        title = 'Packet Log Inspector Help'
        self.pyshell_help = wx.lib.dialogs.ScrolledMessageDialog(
            self, HELP_TEXT, title, size=((700, 540)),
            style=wx.DEFAULT_DIALOG_STYLE | wx.DIALOG_NO_PARENT)
        fnt = wx.Font(
            10,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL)
        self.pyshell_help.GetChildren()[0].SetFont(fnt)
        self.pyshell_help.GetChildren()[0].SetInsertionPoint(0)
        #self.pyshell_help.ShowModal()
        #self.pyshell_help.Destroy()
        self.pyshell_help.Show()

    def on_pyshell_close(self, event):
        if self.pyshell_help:
            self.pyshell_help.Destroy()
        event.Skip()

    def on_open_shell_clicked(self, event):
        if self.pyshell:
            self.pyshell.Raise()
            return
        confDir = wx.StandardPaths.Get().GetUserDataDir()
        os.makedirs(confDir, exist_ok=True)
        self.config = wx.FileConfig()
        main_locals = {
            **globals(), **locals(), "frame": self.GetTopLevelParent()}
        self.pyshell = ShellFrame(
            config=self.config,
            title="Packet Log Inspector Shell",
            dataDir=confDir,
            locals=main_locals)

        ID_LI_HELP = wx.NewIdRef()
        m = self.pyshell.helpMenu
        m.Insert(
            0,
            ID_LI_HELP,
            '&Log Inspector Help\tF9',
            'Specific help for the Log Inspector')
        self.pyshell.Bind(wx.EVT_MENU, self.on_pyshell_help, id=ID_LI_HELP)

        self.pyshell.shell.setStatusText(
            "Packet Log Inspector Shell. "
            "Press F9 for further help.")

        self.pyshell.LoadHistory()
        self.pyshell.LoadSettings()
        self.pyshell.Bind(wx.EVT_CLOSE, self.on_pyshell_close)
        self.pyshell.Show()
