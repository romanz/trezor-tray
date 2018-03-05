#!/usr/bin/env python3
import logging
import sys

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTimer

from libagent.device import trezor
from libagent import util

log = logging.getLogger(__name__)


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):

    def __init__(self, icon, parent, app):
        super().__init__(icon, parent)
        self.app = app
        menu = QtWidgets.QMenu(parent)
        menu.addAction("Exit").triggered.connect(self.on_exit)
        self.setContextMenu(menu)
        self.activated.connect(self.on_click)

        self.show()

        self.device = trezor.Trezor()
        self.ping()

        self.timer = QTimer()
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(60e3)  # ping every minute (in ms)

    def ping(self):
        try:
            with self.device:
                log.info('unlocked')
        except Exception as e:
            self.showMessage('Failed to unlock', str(e))

    def on_timer(self):
        self.ping()

    def on_exit(self):
        self.hide()
        self.app.quit()

    def on_click(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.ping()


def main():
    util.setup_logging(verbosity=2)
    sys.stdin.close()
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = QtWidgets.QWidget()
    tray = SystemTrayIcon(QtGui.QIcon('trezor.png'),
                          parent=window, app=app)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()