#!/usr/bin/env python3
"""Small Qt tool for unlocking TREZOR device when plugged."""

import logging
import pathlib
import sys

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTimer

from pyudev import Context, Monitor
from pyudev.pyqt5 import MonitorObserver

from libagent.device import trezor
from libagent import util

log = logging.getLogger(__name__)


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):

    INTERVAL = 4 * 60 * 1000  # [ms]

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

        self._observe()

        self.timer = QTimer()
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(self.INTERVAL)

    def _observe(self):
        self.context = Context()
        self.monitor = Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='hid')
        self.observer = MonitorObserver(self.monitor)
        self.observer.deviceEvent.connect(self.on_device_event)
        self.monitor.start()

    def ping(self):
        try:
            with self.device:
                log.info('unlocked')
                self.setToolTip('Unlocked')
        except Exception as e:
            log.exception('ping failed: %s', e)
            self.setToolTip('Failed to unlock: {}'.format(e))

    def on_timer(self):
        self.ping()

    def on_exit(self):
        self.hide()
        self.app.quit()

    def on_click(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.ping()

    def on_device_event(self, d):
        log.info('%s %s', d.action, d)
        if (d.get('HID_NAME') == 'SatoshiLabs TREZOR' and
            d.get('HID_PHYS', '').endswith('/input0')):
            if d.action == 'add':
                self.ping()


def main():
    util.setup_logging(verbosity=2)
    sys.stdin.close()
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = QtWidgets.QWidget()
    icon_path = pathlib.Path(__file__).with_name('trezor.png')
    tray = SystemTrayIcon(QtGui.QIcon(str(icon_path)),
                          parent=window, app=app)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
