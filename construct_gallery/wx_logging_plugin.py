import wx
import logging
import typing as t


class CustomLogHandler(logging.Handler):
    def __init__(self, handler: t.Callable[[str], None]):
        logging.Handler.__init__(self)
        self.handler = handler

    def emit(self, record):
        msg = self.format(record)
        self.handler(msg.translate(str.maketrans({"%":  r"%%"})))


class WxLogging():
    log = None

    def __init__(self, frame, logger):
        self.frame = frame
        self.logger = logger
        wx_log_handler = CustomLogHandler(self.wx_log_handler)
        self.logger.addHandler(wx_log_handler)

    @property
    def log_window(self):
        return self.log

    def wx_log_handler(self, log_msg):
        if not self.log:
            self.log = wx.LogWindow(self.frame, "Debug Window", True, False)
            self.log.Frame.Lower()

            m = self.log.GetFrame().GetMenuBar()
            log_menu = wx.Menu()
            self.log_menu_debug_item = log_menu.Append(
                wx.ID_ANY, 'Debug', 'Set Debug Level', kind=wx.ITEM_CHECK)
            self.log_menu_info_item = log_menu.Append(
                wx.ID_ANY, 'Info', 'Set Info Level', kind=wx.ITEM_CHECK)
            self.log_menu_warning_item = log_menu.Append(
                wx.ID_ANY, 'Warning', 'Set Warning Level', kind=wx.ITEM_CHECK)
            self.log_menu_error_item = log_menu.Append(
                wx.ID_ANY, 'Error', 'Set Error Level', kind=wx.ITEM_CHECK)
            self.log_menu_critical_item = log_menu.Append(
                wx.ID_ANY, 'Critical', 'Set Critical Level', kind=wx.ITEM_CHECK)
            m.Append(log_menu, 'L&evel')
            self.log.GetFrame().Bind(
                wx.EVT_MENU, self.on_debug_menu, self.log_menu_debug_item)
            self.log.GetFrame().Bind(
                wx.EVT_MENU, self.on_info_menu, self.log_menu_info_item)
            self.log.GetFrame().Bind(
                wx.EVT_MENU, self.on_warning_menu, self.log_menu_warning_item)
            self.log.GetFrame().Bind(
                wx.EVT_MENU, self.on_error_menu, self.log_menu_error_item)
            self.log.GetFrame().Bind(
                wx.EVT_MENU, self.on_critical_menu, self.log_menu_critical_item)
        if logging.root.level == logging.DEBUG:
            self.on_debug_menu(None)
        if logging.root.level == logging.INFO:
            self.on_info_menu(None)
        if logging.root.level == logging.WARNING:
            self.on_warning_menu(None)
        if logging.root.level == logging.ERROR:
            self.on_critical_menu(None)
        if logging.root.level == logging.CRITICAL:
            self.on_critical_menu(None)
        wx.LogMessage(log_msg)

    def on_debug_menu(self, event):
        self.log_menu_debug_item.Check(True)
        self.log_menu_info_item.Check(False)
        self.log_menu_warning_item.Check(False)
        self.log_menu_error_item.Check(False)
        self.log_menu_critical_item.Check(False)
        self.logger.setLevel(logging.DEBUG)

    def on_info_menu(self, event):
        self.log_menu_debug_item.Check(False)
        self.log_menu_info_item.Check(True)
        self.log_menu_warning_item.Check(False)
        self.log_menu_error_item.Check(False)
        self.log_menu_critical_item.Check(False)
        self.logger.setLevel(logging.INFO)

    def on_warning_menu(self, event):
        self.log_menu_debug_item.Check(False)
        self.log_menu_info_item.Check(False)
        self.log_menu_warning_item.Check(True)
        self.log_menu_error_item.Check(False)
        self.log_menu_critical_item.Check(False)
        self.logger.setLevel(logging.WARNING)

    def on_error_menu(self, event):
        self.log_menu_debug_item.Check(False)
        self.log_menu_info_item.Check(False)
        self.log_menu_warning_item.Check(False)
        self.log_menu_error_item.Check(True)
        self.log_menu_critical_item.Check(False)
        self.logger.setLevel(logging.ERROR)

    def on_critical_menu(self, event):
        self.log_menu_debug_item.Check(False)
        self.log_menu_info_item.Check(False)
        self.log_menu_warning_item.Check(False)
        self.log_menu_error_item.Check(False)
        self.log_menu_critical_item.Check(True)
        self.logger.setLevel(logging.CRITICAL)
