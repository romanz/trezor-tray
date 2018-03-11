#!/usr/bin/env python3
"""Small Qt tool for unlocking TREZOR device when plugged."""

import logging
import pathlib
import sys

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTimer

from pyudev import Context, Monitor
from pyudev.pyqt5 import MonitorObserver

from libagent import device, util
from libagent.device import trezor

log = logging.getLogger(__name__)


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):

    INTERVAL = 4 * 60 * 1000  # [ms]

    def __init__(self, icons, parent, app):
        super().__init__(icons[0], parent)
        self.red_icon, self.green_icon = icons
        self.app = app
        menu = QtWidgets.QMenu(parent)
        menu.addAction("Exit").triggered.connect(self.on_exit)
        self.setContextMenu(menu)
        self.activated.connect(self.on_click)
        self.show()

        self.device = device.trezor.Trezor()
        self.device.ui = device.ui.UI(device_type=self.device.__class__)
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
                self.setIcon(self.green_icon)
        except Exception as e:
            log.exception('ping failed: %s', e)
            self.setToolTip('Failed to unlock: {}'.format(e))
            self.setIcon(self.red_icon)

    def on_timer(self):
        self.ping()

    def on_exit(self):
        self.hide()
        self.app.quit()

    def on_click(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.ping()

    def on_device_event(self, d):
        log.info('%s %s: %s', d.action, d, list(sorted(d.items())))
        if (d.get('HID_NAME') == 'SatoshiLabs TREZOR' and
            d.get('HID_PHYS', '').endswith('/input1')):
            if d.action == 'add':
                self.ping()
            else:
                self.setToolTip('Disconnected')
                self.setIcon(self.red_icon)


def _load_icon(name):
    icon_path = pathlib.Path(__file__).with_name(name)
    return QtGui.QIcon(str(icon_path))

def main():
    util.setup_logging(verbosity=2)
    sys.stdin.close()
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = QtWidgets.QWidget()
    tray = SystemTrayIcon([_load_icon(p) for p in ('red.png', 'green.png')],
                          parent=window, app=app)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
