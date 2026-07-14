"""English / Japanese strings (subset relevant to the KDE tray UI).

Mirrors the wording of the macOS app's AppStrings where it applies.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Strings:
    status_on: str
    status_off: str
    status_error: str
    tooltip_on: str
    tooltip_off: str
    tooltip_error: str
    menu_status: str
    menu_display_off: str
    menu_launch_at_login: str
    menu_language: str
    menu_about: str
    menu_quit: str
    notify_engaged_title: str
    notify_engaged_body: str
    notify_error_title: str
    notify_error_body: str


_EN = Strings(
    status_on="Caps Lock ON",
    status_off="Caps Lock OFF",
    status_error="Error",
    tooltip_on="Caps Lock ON: processes stay awake",
    tooltip_off="Caps Lock OFF: normal sleep",
    tooltip_error="Capsomnia could not update the sleep setting — retrying",
    menu_status="Status",
    menu_display_off="Turn display off when lid closes",
    menu_launch_at_login="Launch at login",
    menu_language="Language",
    menu_about="About Capsomnia",
    menu_quit="Quit",
    notify_engaged_title="Capsomnia",
    notify_engaged_body="Caps Lock is on — sleep is suppressed. Your laptop stays awake with the lid closed.",
    notify_error_title="Capsomnia",
    notify_error_body="Could not update the sleep setting. Retrying.",
)

_JA = Strings(
    status_on="Caps Lock ON",
    status_off="Caps Lock OFF",
    status_error="エラー",
    tooltip_on="Caps Lock ON: スリープ抑止中",
    tooltip_off="Caps Lock OFF: 通常のスリープ動作",
    tooltip_error="スリープ設定を更新できませんでした — 再試行中",
    menu_status="状態",
    menu_display_off="蓋を閉じたら画面をオフ",
    menu_launch_at_login="ログイン時に起動",
    menu_language="言語",
    menu_about="Capsomnia について",
    menu_quit="終了",
    notify_engaged_title="Capsomnia",
    notify_engaged_body="Caps Lock ON — スリープを抑止中。蓋を閉じても作業が走り続けます。",
    notify_error_title="Capsomnia",
    notify_error_body="スリープ設定を更新できませんでした。再試行します。",
)


def strings(language: str) -> Strings:
    return _JA if language == "ja" else _EN


LANGUAGES = (("en", "English"), ("ja", "日本語"))
