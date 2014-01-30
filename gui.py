# -*- coding: utf-8 -*-

from PyQt4.QtGui import QApplication, QSystemTrayIcon, QIcon, QPixmap, QMenu
from PyQt4.QtCore import QTextCodec
from os import _exit
from logging import debug
import icons

_icons = dict()


class RightMenu(QMenu):

    def __init__(self):
        super(RightMenu, self).__init__()

        exitact = self.addAction(_icons['delete'], self.tr('Exit'))
        exitact.triggered.connect(self.DoExit)

    def DoExit(self):
        _exit(0)


class TrayIcon(QSystemTrayIcon):

    def __init__(self):
        super(TrayIcon, self).__init__()

        self.rmenu = RightMenu()
        self.setContextMenu(self.rmenu)


class Backend():

    def __init__(self):
        super(Backend, self).__init__()

        self._app = QApplication([])
        self.loadicons()
        QTextCodec.setCodecForTr(QTextCodec.codecForName("UTF-8"))
        self._tray = TrayIcon()
        self._tray.setIcon(_icons['wait'])

        debug('Backend initialized')

    def loadicons(self):
        _icons['add'] = self.loadicon(icons.add_icon)
        _icons['delete'] = self.loadicon(icons.delete_icon)
        _icons['free'] = self.loadicon(icons.free_icon)
        _icons['remote'] = self.loadicon(icons.remote_icon)
        _icons['run'] = self.loadicon(icons.run_icon)
        _icons['wait'] = self.loadicon(icons.wait_icon)

    def run(self):
        pass
        self._tray.show()
        self._app.exec_()

    def loadicon(self, icon):
        p = QPixmap()
        p.loadFromData(icon)
        return QIcon(p)

    def signal(self, *signal):
        pass