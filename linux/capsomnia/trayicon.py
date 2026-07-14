"""Tray icon rendering — a glowing LED dot, drawn at runtime.

Three states, using the macOS app's brand colors (docs/styles.css :root):
  on    -> lime-green LED (#B8FF1F) with a soft bloom  — sleep suppressed
  off   -> dim grey dot                                 — normal sleep
  error -> red dot                                       — could not apply / drifted
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap, QRadialGradient

_LED = QColor(0xB8, 0xFF, 0x1F)
_LED_BRIGHT = QColor(0xD8, 0xFF, 0x63)
_OFF = QColor(0x94, 0x94, 0x94)
_ERROR = QColor(0xE5, 0x3E, 0x3E)

_SIZE = 64


def _draw_dot(color: QColor, glow: bool) -> QPixmap:
    pixmap = QPixmap(_SIZE, _SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    center = QPointF(_SIZE / 2, _SIZE / 2)

    if glow:
        gradient = QRadialGradient(center, _SIZE / 2)
        glow_color = QColor(color)
        glow_color.setAlpha(150)
        gradient.setColorAt(0.0, glow_color)
        edge = QColor(color)
        edge.setAlpha(0)
        gradient.setColorAt(1.0, edge)
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, _SIZE / 2, _SIZE / 2)

    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    radius = _SIZE * 0.23
    painter.drawEllipse(center, radius, radius)
    painter.end()
    return pixmap


def icon_for(state: str) -> QIcon:
    """state in {"on", "off", "error"}."""
    if state == "on":
        return QIcon(_draw_dot(_LED, glow=True))
    if state == "error":
        return QIcon(_draw_dot(_ERROR, glow=False))
    return QIcon(_draw_dot(_OFF, glow=False))
