#!/usr/bin/env python3
"""
Twingate Linux Desktop Client - System tray application for managing Twingate VPN profiles.

An unofficial, lightweight KDE Plasma system tray application that provides quick access
to Twingate VPN profile switching using Service Keys for headless authentication.
"""

import os
import sys
import time
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QFileDialog
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer

__version__ = "1.0.0"
__author__ = "xfn"

SCRIPT_DIR = Path(__file__).parent
TG_SWITCH = Path("/usr/local/bin/tg-switch")
KEYS_DIR = Path("/etc/twingate/keys")
ACTIVE_PROFILE = Path("/etc/twingate/active_profile")


class TwingateManager:
    """Main application class for the Twingate system tray manager."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("Twingate Linux Desktop Client")
        self.app.setApplicationVersion(__version__)

        self.connect_time = None
        self.profile_actions = []

        self._init_icons()
        self._init_tray()
        self._init_timers()
        self._refresh_status()

        self.tray.show()

    def _init_icons(self):
        """Load tray icons for connected and disconnected states."""
        icon_on = SCRIPT_DIR / "icons" / "twingate_on.png"
        icon_off = SCRIPT_DIR / "icons" / "twingate_off.png"

        self.icon_on = QIcon(str(icon_on)) if icon_on.exists() else QIcon.fromTheme("network-vpn")
        self.icon_off = QIcon(str(icon_off)) if icon_off.exists() else QIcon.fromTheme("network-offline")

    def _init_tray(self):
        """Initialize the system tray icon and context menu."""
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self.icon_off)
        self.tray.setToolTip("Twingate Manager")

        self.menu = QMenu()
        self._build_menu()
        self.tray.setContextMenu(self.menu)

    def _init_timers(self):
        """Set up status polling and duration update timers."""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._refresh_status)
        self.status_timer.start(2000)

        self.duration_timer = QTimer()
        self.duration_timer.timeout.connect(self._update_duration)
        self.duration_timer.start(1000)

    def _build_menu(self):
        """Construct the context menu."""
        self.status_action = QAction("Status: Checking...")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        self.duration_action = QAction("Connected: --:--:--")
        self.duration_action.setEnabled(False)
        self.duration_action.setVisible(False)
        self.menu.addAction(self.duration_action)

        self.menu.addSeparator()
        self.profile_separator = self.menu.addSeparator()

        self.stop_action = QAction("Stop Twingate")
        self.stop_action.triggered.connect(self._handle_stop)
        self.menu.addAction(self.stop_action)

        self.menu.addSeparator()

        self.add_action = QAction("Add Profile...")
        self.add_action.triggered.connect(self._handle_add_profile)
        self.menu.addAction(self.add_action)

        self.menu.addSeparator()

        self.quit_action = QAction("Quit")
        self.quit_action.triggered.connect(self._handle_quit)
        self.menu.addAction(self.quit_action)

        self._refresh_profiles()

    def _get_profiles(self):
        """Retrieve available profile names from the keys directory."""
        profiles = []
        try:
            if KEYS_DIR.exists():
                profiles = [f.stem for f in KEYS_DIR.glob("*.json")]
        except (PermissionError, OSError):
            pass
        return sorted(profiles)

    def _get_active_profile(self):
        """Get the currently active profile name."""
        try:
            if ACTIVE_PROFILE.exists():
                return ACTIVE_PROFILE.read_text().strip()
        except (PermissionError, OSError):
            pass
        return ""

    def _is_connected(self):
        """Check if Twingate service is currently active."""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "twingate"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() == "active"
        except (subprocess.TimeoutExpired, OSError):
            return False

    def _run_backend(self, *args):
        """Execute the tg-switch backend script with sudo."""
        try:
            result = subprocess.run(
                ["sudo", str(TG_SWITCH)] + list(args),
                capture_output=True, text=True, timeout=60
            )
            return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Operation timed out"
        except OSError as e:
            return False, str(e)

    def _refresh_profiles(self):
        """Update the profile list in the menu."""
        for action in self.profile_actions:
            self.menu.removeAction(action)
        self.profile_actions.clear()

        profiles = self._get_profiles()
        current = self._get_active_profile()

        if not profiles:
            action = QAction("No profiles found")
            action.setEnabled(False)
            self.menu.insertAction(self.profile_separator, action)
            self.profile_actions.append(action)
            return

        for name in profiles:
            action = QAction(name)
            action.triggered.connect(lambda _, p=name: self._handle_switch(p))
            if name == current:
                action.setCheckable(True)
                action.setChecked(True)
            self.menu.insertAction(self.profile_separator, action)
            self.profile_actions.append(action)

    def _refresh_status(self):
        """Update connection status and UI elements."""
        connected = self._is_connected()
        profile = self._get_active_profile()

        if connected:
            self.tray.setIcon(self.icon_on)
            label = f"Connected: {profile}" if profile else "Status: Connected"
            tooltip = f"Twingate - {profile}" if profile else "Twingate - Connected"
            self.duration_action.setVisible(True)
            if self.connect_time is None:
                self.connect_time = time.time()
        else:
            self.tray.setIcon(self.icon_off)
            label = "Status: Disconnected"
            tooltip = "Twingate - Disconnected"
            self.duration_action.setVisible(False)
            self.connect_time = None

        self.status_action.setText(label)
        self.tray.setToolTip(tooltip)
        self.stop_action.setEnabled(connected)
        self._refresh_profiles()

    def _update_duration(self):
        """Update the connection duration display."""
        if self.connect_time:
            elapsed = int(time.time() - self.connect_time)
            h, remainder = divmod(elapsed, 3600)
            m, s = divmod(remainder, 60)
            self.duration_action.setText(f"Connected: {h:02d}:{m:02d}:{s:02d}")

    def _notify(self, title, message, error=False):
        """Show a system notification."""
        icon = QSystemTrayIcon.MessageIcon.Warning if error else QSystemTrayIcon.MessageIcon.Information
        self.tray.showMessage(title, message, icon, 3000)

    def _handle_switch(self, profile):
        """Handle profile switch request."""
        ok, msg = self._run_backend(profile)
        if ok:
            self.connect_time = time.time()
            self._notify("Twingate", f"Connected to {profile}")
        else:
            self._notify("Twingate", msg, error=True)
        self._refresh_status()

    def _handle_stop(self):
        """Handle stop request."""
        ok, msg = self._run_backend("stop")
        if ok:
            self._notify("Twingate", "Disconnected")
        else:
            self._notify("Twingate", msg, error=True)
        self._refresh_status()

    def _handle_add_profile(self):
        """Handle add profile request."""
        path, _ = QFileDialog.getOpenFileName(
            None, "Select Twingate Profile",
            os.path.expanduser("~"), "JSON Files (*.json)"
        )
        if not path:
            return

        name = Path(path).stem
        ok, msg = self._run_backend("add", name, path)
        if ok:
            self._notify("Twingate", f"Profile '{name}' added")
            self._refresh_profiles()
        else:
            self._notify("Twingate", msg, error=True)

    def _handle_quit(self):
        """Handle quit request."""
        self._run_backend("stop")
        self.tray.hide()
        self.app.quit()

    def run(self):
        """Start the application event loop."""
        return self.app.exec()


def main():
    """Application entry point."""
    manager = TwingateManager()
    sys.exit(manager.run())


if __name__ == "__main__":
    main()
