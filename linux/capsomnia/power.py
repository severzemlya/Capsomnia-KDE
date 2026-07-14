"""Sleep suppression for KDE Plasma.

Two independent mechanisms, engaged together while Caps Lock is on:

1. A systemd-logind *block* inhibitor (``sleep:idle:handle-lid-switch``), taken
   unprivileged via ``systemd-inhibit``. This blocks idle/automatic system sleep.

2. A temporary override of KDE PowerDevil's ``LidAction`` to 0 ("do nothing")
   for every power profile. On this hardware PowerDevil — not logind — owns the
   lid switch (it holds logind's handle-lid-switch inhibitor), so suppressing
   lid-close suspend means changing PowerDevil's own action. The original values
   are saved to the recovery state file and restored on disengage.

No root privileges are required for either mechanism — the whole macOS
sudo-helper / sudoers / signing dance is unnecessary on Linux.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import signal
import subprocess
from pathlib import Path

from . import APP_NAME

_PR_SET_PDEATHSIG = 1


def _die_with_parent() -> None:
    """preexec_fn: ask the kernel to SIGKILL this child if Capsomnia dies.

    Without this, a crash of the tray process would leave the systemd-inhibit
    child running and sleep blocked forever. With it, the inhibitor is released
    automatically. (The PowerDevil override is recovered separately on next
    launch via the state file.)
    """
    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        libc.prctl(_PR_SET_PDEATHSIG, signal.SIGKILL)
    except OSError:
        pass
from .config import ABSENT, RecoveryState

# PowerDevil power profiles that carry a lid action.
_PROFILES = ("AC", "Battery", "LowBattery")
_LID_DO_NOTHING = "0"

_INHIBIT_WHAT = "sleep:idle:handle-lid-switch"
_INHIBIT_WHY = "Caps Lock keep-awake (Capsomnia)"


def is_kde_session() -> bool:
    """True when running under KDE with the kconfig tools available."""
    if not (shutil.which("kwriteconfig6") and shutil.which("kreadconfig6")):
        return False
    desktop = (
        os.environ.get("XDG_CURRENT_DESKTOP", "")
        + os.environ.get("KDE_FULL_SESSION", "")
    ).lower()
    if "kde" in desktop:
        return True
    # Fall back to the config file existing (e.g. service started before the
    # session env was fully populated).
    return (Path.home() / ".config" / "powerdevilrc").exists()


class PowerController:
    """Owns the sleep-suppression lifecycle and its crash-recovery state."""

    def __init__(self, state: RecoveryState | None = None) -> None:
        self._state = state or RecoveryState()
        self._inhibitor: subprocess.Popen | None = None
        self._kde = is_kde_session()

    # --- public API ------------------------------------------------------
    @property
    def is_engaged(self) -> bool:
        return self._inhibitor is not None and self._inhibitor.poll() is None

    def engage(self) -> bool:
        """Suppress sleep. Returns True on success."""
        ok = self._start_inhibitor()
        if self._kde:
            ok = self._override_lid_action() and ok
        return ok

    def disengage(self) -> bool:
        """Restore normal sleep behavior. Returns True on success."""
        self._stop_inhibitor()
        ok = True
        if self._kde:
            ok = self._restore_lid_action()
        return ok

    def recover_on_startup(self) -> None:
        """Restore PowerDevil values left over from a previous crashed run.

        If the recovery state file still holds saved lid actions, a prior
        Capsomnia was killed while suppressing sleep. Put the machine back to
        normal before we begin.
        """
        if self._kde and self._state.has_saved_lid_actions():
            self._restore_lid_action()

    def verify(self) -> bool:
        """Confirm the suppression is actually in effect (drift detection).

        On KDE the authoritative check is PowerDevil's *in-memory* lid action
        (HandleButtonEvents.lidAction() over D-Bus), not just the config file:
        the config can say "do nothing" while PowerDevil still holds the old
        action in memory until refreshStatus() reloads it.
        """
        if not self.is_engaged:
            return False
        if self._kde:
            live = self._read_inmemory_lid_action()
            # If we cannot read the live value, fall back to the config value.
            if live is not None:
                return live == _LID_DO_NOTHING
            for profile in _PROFILES:
                if self._read_lid_action(profile) != _LID_DO_NOTHING:
                    return False
        return True

    @staticmethod
    def _read_inmemory_lid_action() -> str | None:
        """PowerDevil's live lid action, or None if it can't be read."""
        qdbus = shutil.which("qdbus6") or shutil.which("qdbus")
        if not qdbus:
            return None
        try:
            result = subprocess.run(
                [
                    qdbus,
                    "org.kde.Solid.PowerManagement",
                    "/org/kde/Solid/PowerManagement/Actions/HandleButtonEvents",
                    "lidAction",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        value = result.stdout.strip()
        return value if value.isdigit() else None

    # --- systemd inhibitor ----------------------------------------------
    def _start_inhibitor(self) -> bool:
        if self.is_engaged:
            return True
        try:
            self._inhibitor = subprocess.Popen(
                [
                    "systemd-inhibit",
                    f"--what={_INHIBIT_WHAT}",
                    f"--who={APP_NAME}",
                    f"--why={_INHIBIT_WHY}",
                    "--mode=block",
                    "sleep",
                    "infinity",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=_die_with_parent,
            )
        except OSError:
            self._inhibitor = None
            return False
        return True

    def _stop_inhibitor(self) -> None:
        proc = self._inhibitor
        self._inhibitor = None
        if proc is None:
            return
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    # --- PowerDevil lid action ------------------------------------------
    def _override_lid_action(self) -> bool:
        # Save originals only on the first engage (avoid clobbering saved state
        # if we somehow re-engage while already saved).
        if not self._state.has_saved_lid_actions():
            saved = {
                profile: self._read_lid_action(profile) or ABSENT
                for profile in _PROFILES
            }
            self._state.save_lid_actions(saved)

        ok = all(
            self._write_lid_action(profile, _LID_DO_NOTHING) for profile in _PROFILES
        )
        self._reparse_powerdevil()
        return ok

    def _restore_lid_action(self) -> bool:
        saved = self._state.saved_lid_actions()
        ok = True
        for profile in _PROFILES:
            original = saved.get(profile.lower())  # configparser lowercases keys
            if original is None:
                continue
            if original == ABSENT:
                ok = self._delete_lid_action(profile) and ok
            else:
                ok = self._write_lid_action(profile, original) and ok
        self._reparse_powerdevil()
        self._state.clear_lid_actions()
        return ok

    @staticmethod
    def _kconfig_groups() -> list[str]:
        return ["--group", "SuspendAndShutdown"]

    def _read_lid_action(self, profile: str) -> str | None:
        try:
            result = subprocess.run(
                [
                    "kreadconfig6",
                    "--file",
                    "powerdevilrc",
                    "--group",
                    profile,
                    *self._kconfig_groups(),
                    "--key",
                    "LidAction",
                    "--default",
                    ABSENT,
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        value = result.stdout.strip()
        return None if value == ABSENT else value

    def _write_lid_action(self, profile: str, value: str) -> bool:
        return self._run_kwrite(
            [
                "--file",
                "powerdevilrc",
                "--group",
                profile,
                *self._kconfig_groups(),
                "--key",
                "LidAction",
                value,
            ]
        )

    def _delete_lid_action(self, profile: str) -> bool:
        return self._run_kwrite(
            [
                "--file",
                "powerdevilrc",
                "--group",
                profile,
                *self._kconfig_groups(),
                "--key",
                "LidAction",
                "--delete",
            ]
        )

    @staticmethod
    def _run_kwrite(args: list[str]) -> bool:
        try:
            subprocess.run(
                ["kwriteconfig6", *args],
                capture_output=True,
                timeout=5,
                check=True,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return True

    @staticmethod
    def _reparse_powerdevil() -> None:
        """Make PowerDevil re-read the lid action from powerdevilrc.

        We must call refreshStatus(), NOT reparseConfiguration(): the latter only
        reloads global settings, while refreshStatus() runs loadProfile(force),
        which re-runs each action's onProfileLoad() and so re-reads LidAction.
        Calling the wrong one leaves the old lid action in memory and the machine
        suspends on lid close despite the config file saying "do nothing".
        See KDE/powerdevil daemon/powerdevilcore.cpp.
        """
        qdbus = shutil.which("qdbus6") or shutil.which("qdbus")
        if not qdbus:
            return
        try:
            subprocess.run(
                [
                    qdbus,
                    "org.kde.Solid.PowerManagement",
                    "/org/kde/Solid/PowerManagement",
                    "refreshStatus",
                ],
                capture_output=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            pass
