"""Capsomnia tray application for KDE Plasma."""

from __future__ import annotations

import signal
import subprocess
import time

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import (
    QApplication,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

from . import APP_ID, APP_NAME, __version__
from . import i18n
from .capslock import read_capslock
from .config import Preferences, RecoveryState
from .display import blank_display, lid_is_closed
from .power import PowerController
from .trayicon import icon_for

POLL_INTERVAL_MS = 250
VERIFY_INTERVAL_S = 10.0
RETRY_INTERVAL_S = 5.0
SERVICE_UNIT = "capsomnia.service"


class CapsomniaApp:
    def __init__(self, app: QApplication) -> None:
        self._app = app
        self._prefs = Preferences()
        self._power = PowerController(RecoveryState())
        self._strings = i18n.strings(self._prefs.language)

        # State machine
        self._applied: bool | None = None
        self._error = False
        self._next_verify = 0.0
        self._next_retry = 0.0
        self._blanked_for_lid = False
        self._should_quit = False

        # Recover from a previous crashed run before we touch anything.
        self._power.recover_on_startup()

        self._tray = QSystemTrayIcon()
        self._tray.setIcon(icon_for("off"))
        self._build_menu()
        if self._prefs.show_tray_icon:
            self._tray.show()

        self._app.aboutToQuit.connect(self._on_quit)
        self._install_signal_handlers()

        self._timer = QTimer()
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._tick()

    # --- menu ------------------------------------------------------------
    def _build_menu(self) -> None:
        s = self._strings
        menu = QMenu()

        self._status_action = QAction(s.status_off, menu)
        self._status_action.setEnabled(False)
        menu.addAction(self._status_action)
        menu.addSeparator()

        self._display_action = QAction(s.menu_display_off, menu, checkable=True)
        self._display_action.setChecked(self._prefs.display_off_on_lid_close)
        self._display_action.toggled.connect(self._on_toggle_display_off)
        menu.addAction(self._display_action)

        self._login_action = QAction(s.menu_launch_at_login, menu, checkable=True)
        self._login_action.setChecked(self._prefs.launch_at_login)
        self._login_action.toggled.connect(self._on_toggle_launch_at_login)
        menu.addAction(self._login_action)

        lang_menu = menu.addMenu(s.menu_language)
        group = QActionGroup(lang_menu)
        group.setExclusive(True)
        for code, label in i18n.LANGUAGES:
            action = QAction(label, lang_menu, checkable=True)
            action.setChecked(self._prefs.language == code)
            action.triggered.connect(lambda _checked, c=code: self._on_select_language(c))
            group.addAction(action)
            lang_menu.addAction(action)

        menu.addSeparator()
        about_action = QAction(s.menu_about, menu)
        about_action.triggered.connect(self._on_about)
        menu.addAction(about_action)

        quit_action = QAction(s.menu_quit, menu)
        quit_action.triggered.connect(self._app.quit)
        menu.addAction(quit_action)

        self._menu = menu
        self._tray.setContextMenu(menu)

    def _refresh_menu_language(self) -> None:
        self._strings = i18n.strings(self._prefs.language)
        # Rebuild is simplest and cheap.
        self._build_menu()
        self._render(self._applied)

    # --- state machine ---------------------------------------------------
    def _tick(self) -> None:
        if self._should_quit:
            self._app.quit()
            return

        now = time.monotonic()
        caps = read_capslock()

        if caps is None:
            self._set_error()
            return

        if self._error and now < self._next_retry:
            return

        if self._error:
            self._apply(caps)
        elif caps != self._applied:
            self._apply(caps)
        elif caps and now >= self._next_verify:
            if self._power.verify():
                self._next_verify = now + VERIFY_INTERVAL_S
            else:
                self._apply(caps)  # drift — reapply

        self._handle_lid_display(caps)

    def _apply(self, desired: bool) -> None:
        if desired:
            ok = self._power.engage() and self._power.verify()
        else:
            ok = self._power.disengage()

        if ok:
            self._applied = desired
            self._error = False
            self._next_verify = time.monotonic() + VERIFY_INTERVAL_S
            self._render(desired)
        else:
            self._set_error()

    def _set_error(self) -> None:
        self._error = True
        self._next_retry = time.monotonic() + RETRY_INTERVAL_S
        self._tray.setIcon(icon_for("error"))
        self._tray.setToolTip(f"{APP_NAME} — {self._strings.tooltip_error}")
        self._status_action.setText(self._strings.status_error)

    def _render(self, applied: bool | None) -> None:
        if applied:
            self._tray.setIcon(icon_for("on"))
            self._tray.setToolTip(f"{APP_NAME} — {self._strings.tooltip_on}")
            self._status_action.setText(self._strings.status_on)
        else:
            self._tray.setIcon(icon_for("off"))
            self._tray.setToolTip(f"{APP_NAME} — {self._strings.tooltip_off}")
            self._status_action.setText(self._strings.status_off)

    def _handle_lid_display(self, caps: bool) -> None:
        if not (caps and self._prefs.display_off_on_lid_close):
            self._blanked_for_lid = False
            return
        closed = lid_is_closed()
        if closed is True and not self._blanked_for_lid:
            blank_display()
            self._blanked_for_lid = True
        elif closed is False:
            self._blanked_for_lid = False

    # --- menu handlers ---------------------------------------------------
    def _on_toggle_display_off(self, checked: bool) -> None:
        self._prefs.display_off_on_lid_close = checked

    def _on_toggle_launch_at_login(self, checked: bool) -> None:
        self._prefs.launch_at_login = checked
        self._set_service_enabled(checked)

    def _on_select_language(self, code: str) -> None:
        if code == self._prefs.language:
            return
        self._prefs.language = code
        self._refresh_menu_language()

    def _on_about(self) -> None:
        QMessageBox.information(
            None,
            self._strings.menu_about,
            f"{APP_NAME} for KDE {__version__}\n\n"
            "Turn Caps Lock into a physical keep-awake switch.\n"
            "https://github.com/fuji-mak/Capsomnia",
        )

    @staticmethod
    def _set_service_enabled(enabled: bool) -> None:
        verb = "enable" if enabled else "disable"
        try:
            subprocess.run(
                ["systemctl", "--user", verb, SERVICE_UNIT],
                capture_output=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            pass

    # --- lifecycle -------------------------------------------------------
    def _install_signal_handlers(self) -> None:
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._on_signal)

    def _on_signal(self, _signum, _frame) -> None:
        # Defer the actual quit to the timer thread-safely.
        self._should_quit = True

    def _on_quit(self) -> None:
        # Always restore normal sleep behavior on exit.
        self._power.disengage()


def main() -> int:
    app = QApplication([])
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setDesktopFileName(APP_ID)
    app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        # No tray (rare on KDE). Run headless — suppression still works.
        pass

    CapsomniaApp(app)
    return app.exec()
