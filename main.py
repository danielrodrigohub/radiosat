"""
RadioSAT XP  –  Suite de Automatización de Radio
=================================================
Funcionalidades implementadas:
  • Reproducción de audio (pygame)          – play / pause / stop / siguiente / anterior
  • Detección DTMF en tiempo real           – via FFT con sounddevice
  • VU Meters en tiempo real                – del stream de audio actual
  • Osciloscopio animado                    – refleja nivel real
  • Gestión de Playlist                     – añadir / eliminar / reordenar archivos
  • Biblioteca de Medios                    – importar, buscar, añadir a playlist
  • Micrófono ON/OFF                        – mute de captura con sounddevice
  • Control de volumen                      – pygame mixer volume
  • Texto a Voz (TTS)                       – pyttsx3 en hilo aparte
  • Reloj en tiempo real                    – QTimer cada segundo
  • Menú completo (Archivo / Ver / Config / Ayuda)
"""

import sys
import os
import re
import math
import random
import threading
import queue
import time
import subprocess
import traceback
from datetime import datetime
from pathlib import Path

# ── PyQt6 ──────────────────────────────────────────────────────────────────
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QSplitter, QPushButton, QLabel, QLCDNumber,
    QProgressBar, QTabWidget, QComboBox, QSpinBox, QDoubleSpinBox,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QSlider,
    QFrame, QSizePolicy, QFileDialog, QMessageBox, QInputDialog,
    QStatusBar, QToolBar, QStyle, QDialog, QGroupBox, QStackedWidget,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QObject, QThread, QUrl, QProcess, QRectF
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QFont,
    QLinearGradient, QPen, QBrush, QPainterPath, QRadialGradient
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData, QMediaDevices

# ── Dependencias opcionales (con degradación elegante) ─────────────────────
try:
    # Retiramos pygame porque la versión actual compila sin módulo mixer
    # Utilizamos QtMultimedia en su lugar
    QT_AUDIO_OK = True
except Exception:
    QT_AUDIO_OK = False

try:
    import numpy as np
    import sounddevice as sd
    SOUND_OK = True
except Exception:
    SOUND_OK = False

try:
    from mutagen import File as MutagenFile
    MUTAGEN_OK = True
except Exception:
    MUTAGEN_OK = False

try:
    import pyttsx3
    TTS_OK = True
except Exception:
    TTS_OK = False

# ── Rutas compatibles con PyInstaller ───────────────────────────────────────
def resource_path(relative_path: str) -> str:
    """Devuelve la ruta absoluta a un recurso empaquetado o de desarrollo."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def data_path(filename: str) -> str:
    """Devuelve la ruta a un archivo de datos persistente (writable)."""
    if getattr(sys, 'frozen', False):
        base = os.path.join(os.path.expanduser("~"), ".radiosat")
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, filename)

def ffmpeg_path() -> str:
    """Devuelve la ruta al binario de FFmpeg (bundled o del sistema)."""
    if getattr(sys, 'frozen', False):
        exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        
        # Check _MEIPASS (internal dir in PyInstaller 6+ or root in earlier versions)
        bundled_meipass = os.path.join(sys._MEIPASS, exe_name)
        if os.path.exists(bundled_meipass):
            return bundled_meipass
            
        # Check executable directory (where RadioSAT.exe is)
        bundled_exe_dir = os.path.join(os.path.dirname(sys.executable), exe_name)
        if os.path.exists(bundled_exe_dir):
            return bundled_exe_dir
            
    return "ffmpeg"

# ── Íconos XP ──────────────────────────────────────────────────────────────
WINXP_DIR = resource_path("winxpicons")
ICONS_DIR = resource_path("icons")

XP_ICON_MAP = {
    "AudioDevices.png": "Sounds, Speech, and Audio Devices.ico",
    "AudioCD.png": "Music File.ico",
    "Chip.png": "Manage your Server.ico",
    "Volume.png": "Sounds, Speech, and Audio Devices.ico",
    "NewFolder.png": "Folder Closed.ico",
    "Open.png": "Folder Open.ico",
    "Save.png": "Disk Image File.ico",
    "ControlPanel.png": "System Properties.ico",
    "Alert.png": "User Support.ico",
    "Record.png": "Camera.ico",
    "MyMusic.png": "Music File.ico",
    "Settings.png": "System Properties.ico",
    "Refresh.png": "IE Refresh.png",
    "Apply.png": "Properties.png",
    "Send.png": "OE Send.png",
    "Prev.png": "Back.png",
    "Next.png": "Forward.png",
    "Stop.png": "Stop.png",
    "Play.png": "Play.png",
    "Pause.png": "Standby.png",
    "Playlist.png": "Network Folder.png",
    "Pauta.png": "VPN Connection.png",
    "RemoteDesktop.png": "Remote Desktop.png",
}

# ══════════════════════════════════════════════════════════════════════════════
#  SISTEMA DE TEMAS
# ══════════════════════════════════════════════════════════════════════════════
THEME_DARK = {
    "background":         "#101820",
    "surface":            "#151F2A",
    "surface_raised":     "#1D2936",
    "border":             "#354657",
    "text_primary":       "#EDF3F8",
    "text_secondary":     "#B2C0CD",
    "text_dim":           "#7A8A9A",
    "accent":             "#1689DF",
    "accent_text":        "#63C6FF",
    "success":            "#39DD69",
    "warning":            "#FFC34D",
    "danger":             "#F06464",
    "focus":              "#8AD4FF",
    "bg_primary":         "#101820",
    "bg_surface":         "#151F2A",
    "bg_surface_alt":     "#1D2936",
    "bg_hover":           "#253342",
    "bg_input":           "#1A2632",
    "border_focus":       "#1689DF",
    "text":               "#EDF3F8",
    "menu_bg":            "#151F2A",
    "menu_hover":         "#253342",
    "scrollbar_bg":       "#151F2A",
    "scrollbar_handle":   "#354657",
    "scrollbar_hover":    "#4A5D70",
    "header_bg":          "#1D2936",
    "slider_groove":      "#354657",
    "slider_sub":         "#1689DF",
    "clock_bg":           "#0A0F14",
    "clock_color":        "#FFC34D",
    "vu_bg":              "#0A1018",
    "vu_green":           "#39DD69",
    "vu_amber":           "#FFC34D",
    "vu_red":             "#F06464",
    "vu_label":           "#7A8A9A",
    "wave_bg":            "#0A1018",
    "wave_text":          "#39DD69",
    "titlebar_start":     "#1D2936",
    "titlebar_mid":       "#253342",
    "titlebar_end":       "#151F2A",
    "panel_bg":           "#151F2A",
    "panel_border":       "#354657",
}

THEME_LIGHT = {
    "background":         "#F5F7FA",
    "surface":            "#FFFFFF",
    "surface_raised":     "#F0F4F8",
    "border":             "#D0D8E0",
    "text_primary":       "#1A2332",
    "text_secondary":     "#5A6A7A",
    "text_dim":           "#8A9AAA",
    "accent":             "#1689DF",
    "accent_text":        "#0A6ABF",
    "success":            "#2BBF55",
    "warning":            "#E0A030",
    "danger":             "#D04040",
    "focus":              "#1689DF",
    "bg_primary":         "#F5F7FA",
    "bg_surface":         "#FFFFFF",
    "bg_surface_alt":     "#F0F4F8",
    "bg_hover":           "#E8EEF4",
    "bg_input":           "#FFFFFF",
    "border_focus":       "#1689DF",
    "text":               "#1A2332",
    "menu_bg":            "#FFFFFF",
    "menu_hover":         "#E8EEF4",
    "scrollbar_bg":       "#F0F4F8",
    "scrollbar_handle":   "#D0D8E0",
    "scrollbar_hover":    "#B0B8C0",
    "header_bg":          "#F0F4F8",
    "slider_groove":      "#D0D8E0",
    "slider_sub":         "#1689DF",
    "clock_bg":           "#1A2332",
    "clock_color":        "#FFC34D",
    "vu_bg":              "#E8EEF4",
    "vu_green":           "#2BBF55",
    "vu_amber":           "#E0A030",
    "vu_red":             "#D04040",
    "vu_label":           "#5A6A7A",
    "wave_bg":            "#E8EEF4",
    "wave_text":          "#2BBF55",
    "titlebar_start":     "#1689DF",
    "titlebar_mid":       "#2A9AEF",
    "titlebar_end":       "#0A6ABF",
    "panel_bg":           "#FFFFFF",
    "panel_border":       "#D0D8E0",
}

_current_theme = THEME_DARK

def set_theme(dark: bool = True):
    global _current_theme
    _current_theme = THEME_DARK if dark else THEME_LIGHT

def T(key: str) -> str:
    return _current_theme.get(key, "")

def generate_qss() -> str:
    t = _current_theme
    return f"""
QMainWindow {{ background: {t.get('background', t.get('bg_primary', '#101820'))}; }}
QWidget {{ font-family: "Helvetica Neue", "Segoe UI", "SF Pro Display", Helvetica, Arial; font-size: 9pt; color: {t.get('text_primary', t.get('text', '#EDF3F8'))}; }}
QMenuBar {{
    background: {t.get('surface', t.get('bg_surface', '#151F2A'))};
    border-bottom: 1px solid {t['border']};
}}
QMenuBar::item {{ padding: 6px 12px; }}
QMenuBar::item:selected {{ background: {t['accent']}; color: white; border-radius: 4px; }}
QMenu {{ background: {t.get('menu_bg', t.get('surface', '#151F2A'))}; border: 1px solid {t['border']}; border-radius: 6px; padding: 4px; }}
QMenu::item {{ padding: 6px 28px; border-radius: 4px; }}
QMenu::item:selected {{ background: {t['accent']}; color: white; }}
QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 8px; }}
QToolBar {{
    background: {t.get('surface', t.get('bg_surface', '#151F2A'))};
    border-bottom: 1px solid {t['border']};
    spacing: 4px; padding: 4px;
}}
QToolBar::separator {{ width: 1px; background: {t['border']}; margin: 4px 6px; }}
QToolButton {{
    background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 4px;
}}
QToolButton:hover {{ background: {t.get('bg_hover', '#253342')}; border: 1px solid {t['border']}; }}
QToolButton:pressed {{ background: {t['border']}; }}
QPushButton {{
    background: {t.get('surface', t.get('bg_surface', '#151F2A'))};
    border: 1px solid {t['border']};
    border-radius: 4px;
    padding: 6px 14px; min-height: 36px;
}}
QPushButton:hover {{
    background: {t.get('bg_hover', '#253342')};
    border-color: {t['accent']};
}}
QPushButton:pressed {{
    background: {t['border']};
}}
QPushButton:checked {{
    background: {t['accent']};
    color: white; font-weight: bold;
    border-color: {t['accent']};
}}
QPushButton:disabled {{ color: {t.get('text_dim', '#7A8A9A')}; background: {t.get('bg_surface_alt', '#1D2936')}; border-color: {t['border']}; }}
QTabWidget::pane {{ border: 1px solid {t['border']}; background: {t.get('surface', t.get('bg_surface', '#151F2A'))}; border-radius: 4px; }}
QTabBar::tab {{
    background: {t.get('bg_surface_alt', '#1D2936')};
    border: 1px solid {t['border']};
    border-bottom-color: {t.get('surface', t.get('bg_surface', '#151F2A'))};
    padding: 7px 16px; margin-right: 2px;
    border-top-left-radius: 4px; border-top-right-radius: 4px;
}}
QTabBar::tab:selected {{ background: {t.get('surface', t.get('bg_surface', '#151F2A'))}; font-weight: bold; color: {t['accent']}; border-bottom: none; }}
QTabBar::tab:hover:!selected {{ background: {t.get('bg_hover', '#253342')}; }}
QTableWidget {{
    background: {t.get('bg_input', '#1A2632')};
    gridline-color: {t['border']};
    border: 1px solid {t['border']};
    border-radius: 4px;
    alternate-background-color: {t.get('bg_surface_alt', '#1D2936')};
    selection-background-color: {t['accent']};
    selection-color: white;
}}
QTableWidget::item {{ padding: 4px 6px; }}
QTableWidget::item:hover {{ background: {t.get('bg_hover', '#253342')}; }}
QHeaderView::section {{
    background: {t['header_bg']};
    border: 1px solid {t['border']};
    padding: 5px 8px; font-weight: bold;
    border-radius: 0;
}}
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {t.get('bg_input', '#1A2632')};
    color: {t.get('text_primary', t.get('text', '#EDF3F8'))};
    border: 1px solid {t['border']};
    border-radius: 4px;
    padding: 5px 8px;
}}
QComboBox {{
    background-color: {t.get('bg_input', '#1A2632')};
    color: {t.get('text_primary', t.get('text', '#EDF3F8'))};
    border: 1px solid {t['border']};
    border-radius: 4px;
    padding: 5px 8px;
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {t['border_focus']};
}}
QComboBox QAbstractItemView {{
    background-color: {t.get('bg_input', '#1A2632')};
    color: {t.get('text_primary', t.get('text', '#EDF3F8'))};
    selection-background-color: {t['accent']};
    selection-color: #FFFFFF;
    border: 1px solid {t['border']};
    border-radius: 4px;
}}
QDialog, QMessageBox {{
    background-color: {t.get('background', t.get('bg_primary', '#101820'))};
    color: {t.get('text_primary', t.get('text', '#EDF3F8'))};
}}
QSlider::groove:horizontal {{
    height: 6px; background: {t['slider_groove']}; border: 1px solid {t['border']}; border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {t['accent']};
    border: 2px solid {t['border_focus']};
    width: 16px; height: 16px; margin: -6px 0; border-radius: 9px;
}}
QSlider::sub-page:horizontal {{
    background: {t['slider_sub']};
    border: 1px solid {t['border']}; border-radius: 3px;
}}
QStatusBar {{
    background: {t.get('surface', t.get('bg_surface', '#151F2A'))};
    border-top: 1px solid {t['border']};
    color: {t.get('text_secondary', '#B2C0CD')};
}}
QScrollBar:vertical {{
    background: {t.get('scrollbar_bg', '#151F2A')}; width: 12px; border: none; border-radius: 6px;
}}
QScrollBar::handle:vertical {{
    background: {t.get('scrollbar_handle', '#354657')}; border: none; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {t.get('scrollbar_hover', '#4A5D70')}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    background: none; height: 0px; border: none;
}}
QScrollBar:horizontal {{
    background: {t.get('scrollbar_bg', '#151F2A')}; height: 12px; border: none; border-radius: 6px;
}}
QScrollBar::handle:horizontal {{
    background: {t.get('scrollbar_handle', '#354657')}; border: none; border-radius: 5px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {t.get('scrollbar_hover', '#4A5D70')}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    background: none; width: 0px; border: none;
}}
QSplitter::handle {{
    background: {t['border']};
    width: 3px; height: 3px; border-radius: 1px;
}}
QSplitter::handle:hover {{
    background: {t['accent']};
}}
QToolTip {{
    color: {t['text_primary']};
    background-color: {t['surface_raised']};
    border: 1px solid {t['border_focus']};
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 11px;
    opacity: 255;
}}
QLabel {{
    color: {t['text']};
}}
"""


def xp_icon(name: str) -> QIcon:
    mapped = XP_ICON_MAP.get(name, name)
    path = os.path.join(WINXP_DIR, mapped)
    if os.path.exists(path) and os.path.getsize(path) > 100:
        return QIcon(path)
    
    path = os.path.join(ICONS_DIR, name)
    if os.path.exists(path) and os.path.getsize(path) > 100:
        return QIcon(path)
        
    return QIcon()

def xp_pixmap(name: str, size=24) -> QPixmap:
    mapped = XP_ICON_MAP.get(name, name)
    path = os.path.join(WINXP_DIR, mapped)
    if os.path.exists(path) and os.path.getsize(path) > 100:
        return QPixmap(path).scaled(size, size,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
                                    
    path = os.path.join(ICONS_DIR, name)
    if os.path.exists(path) and os.path.getsize(path) > 100:
        return QPixmap(path).scaled(size, size,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
                                    
    return QPixmap()

# ══════════════════════════════════════════════════════════════════════════════
#  MOTOR DE AUDIO
# ══════════════════════════════════════════════════════════════════════════════
class AudioEngine(QObject):
    """
    Controla la reproducción de audio con pygame.mixer.
    Emite señales para actualizar la UI.
    """
    track_changed  = pyqtSignal(int, str, str, str)
    playback_state = pyqtSignal(str)
    position_tick  = pyqtSignal(int, int)
    level_update   = pyqtSignal(float, float)
    error_signal   = pyqtSignal(str)
    metadata_update= pyqtSignal(str)
    sequence_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playlist: list[dict] = []
        self._index    = -1
        self._state    = "stopped"
        self._volume   = 0.8
        self._stop_at_end = False
        
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(self._volume)
        
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.metaDataChanged.connect(self._on_metadata_changed)
        self.player.errorOccurred.connect(self._on_error)

        self._poll = QTimer(self)
        self._poll.timeout.connect(self._on_poll)
        self._poll.start(100)

    # ── Playlist ───────────────────────────────────────────────────────────
    def add_file(self, path: str) -> dict | None:
        info = self._read_tags(path)
        if info:
            self._playlist.append(info)
        return info

    def remove_index(self, idx: int):
        if 0 <= idx < len(self._playlist):
            if idx == self._index:
                self.stop()
                self._index = -1
            elif idx < self._index:
                self._index -= 1
            del self._playlist[idx]

    def clear_playlist(self):
        self.stop()
        self._playlist.clear()
        self._index = -1

    def _read_tags(self, path: str) -> dict | None:
        if path.startswith("http"):
            return {
                "path": path,
                "artist": "Web Radio",
                "title": "Streaming",
                "duration": "∞",
                "duration_ms": 0,
            }
        p = Path(path)
        if not p.exists():
            return None
        artist, title = "Desconocido", p.stem
        duration_ms = 0
        if MUTAGEN_OK:
            try:
                tag = MutagenFile(path)
                if tag:
                    artist = str(tag.get("TPE1", tag.get("artist", ["Desconocido"]))[0])
                    title  = str(tag.get("TIT2", tag.get("title",  [p.stem]))[0])
                    if hasattr(tag.info, "length"):
                        duration_ms = int(tag.info.length * 1000)
            except Exception:
                pass
        secs = duration_ms // 1000
        dur_str = f"{secs//60}:{secs%60:02d}" if secs else "?"
        return {
            "path": path,
            "artist": artist,
            "title": title,
            "duration": dur_str,
            "duration_ms": duration_ms,
        }

    # ── Transporte ─────────────────────────────────────────────────────────
    def play(self, index: int = None, stop_at_end: bool | None = None):
        if stop_at_end is not None:
            self._stop_at_end = stop_at_end
        if index is not None:
            self._index = index
        if not self._playlist:
            return
        if self._index < 0:
            self._index = 0

        track = self._playlist[self._index]
        try:
            url = track["path"]
            if url.startswith("http"):
                self.player.setSource(QUrl(url))
            else:
                self.player.setSource(QUrl.fromLocalFile(url))
                
            self.player.play()
            self.track_changed.emit(
                self._index,
                track["artist"],
                track["title"],
                track["duration"]
            )
        except Exception as e:
            self.error_signal.emit(f"Error reproduciendo: {e}")

    def pause(self):
        if self._state == "playing":
            self.player.pause()
        elif self._state == "paused":
            self.player.play()

    def stop(self):
        self._stop_at_end = False
        self.player.stop()

    def next_track(self):
        if not self._playlist:
            return
        self._index = (self._index + 1) % len(self._playlist)
        self.play()

    def prev_track(self):
        if not self._playlist:
            return
        self._index = (self._index - 1) % len(self._playlist)
        self.play()

    def set_output_device(self, device):
        """Cambia el dispositivo de salida de audio (QAudioDevice)."""
        was_playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        current_source = self.player.source()
        current_pos = self.player.position()
        
        if was_playing:
            self.player.stop()
        
        if device is not None:
            self.audio_output.setDevice(device)
        else:
            from PyQt6.QtMultimedia import QMediaDevices
            self.audio_output.setDevice(QMediaDevices.defaultAudioOutput())
            
        self.player.setAudioOutput(self.audio_output)
        
        if was_playing:
            self.player.setSource(current_source)
            self.player.setPosition(current_pos)
            self.player.play()

    def set_volume(self, vol: float):
        """vol: 0.0 a 1.0"""
        self._volume = max(0.0, min(1.0, vol))
        self.audio_output.setVolume(self._volume)

    def seek(self, pct: float):
        """pct: 0.0 a 1.0"""
        track = self._playlist[self._index] if self._index >= 0 and self._index < len(self._playlist) else None
        if track and track["duration_ms"] > 0:
            self.player.setPosition(int(pct * track["duration_ms"]))

    @property
    def state(self): return self._state
    @property
    def playlist(self): return self._playlist
    @property
    def current_index(self): return self._index

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._state = "playing"
            self.playback_state.emit("playing")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._state = "paused"
            self.playback_state.emit("paused")
        else:
            self._state = "stopped"
            self.playback_state.emit("stopped")

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self._stop_at_end and self._index >= len(self._playlist) - 1:
                self._stop_at_end = False
                self.player.stop()
                self.sequence_finished.emit()
                return
            self.next_track()

    def _on_position_changed(self, pos_ms):
        track = self._playlist[self._index] if self._playlist and self._index >= 0 else None
        total = track["duration_ms"] if track else 0
        if total == 0:
            total = self.player.duration()
        self.position_tick.emit(pos_ms, total)

    def _on_metadata_changed(self):
        meta = self.player.metaData()
        if meta:
            title = meta.stringValue(QMediaMetaData.Key.Title)
            artist = meta.stringValue(QMediaMetaData.Key.ContributingArtist)
            if not artist:
                artist = meta.stringValue(QMediaMetaData.Key.Author)
            if title or artist:
                text = f"{artist} - {title}" if artist else title
                self.metadata_update.emit(text)

    def _on_error(self, error, error_string=""):
        msg = error_string or str(error)
        if msg:
            print(f"[AudioEngine] Error: {msg}")
            self.error_signal.emit(f"Error de audio: {msg}")

    def _on_poll(self):
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  MOTOR DE STREAM REMOTO
# ══════════════════════════════════════════════════════════════════════════════
class RemoteStreamEngine(QObject):
    state_changed   = pyqtSignal(str)
    metadata_update = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._volume = 0.8
        self._muted = False
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self._apply_output_volume()
        self.player.playbackStateChanged.connect(self._on_state_changed)
        self.player.errorOccurred.connect(self._on_error)
        self.player.metaDataChanged.connect(self._on_metadata_changed)

    @property
    def is_playing(self):
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def set_output_device(self, device):
        was_playing = self.is_playing
        current_source = self.player.source()
        
        if was_playing:
            self.player.stop()
            
        if device is not None:
            self.audio_output.setDevice(device)
        else:
            from PyQt6.QtMultimedia import QMediaDevices
            self.audio_output.setDevice(QMediaDevices.defaultAudioOutput())
            
        self.player.setAudioOutput(self.audio_output)
        
        if was_playing:
            self.player.setSource(current_source)
            self.player.play()

    def play(self, url: str):
        self.stop()
        self.player.setSource(QUrl(url))
        self.player.play()
        self.metadata_update.emit("Conectando...")

    def stop(self):
        self.player.stop()

    def set_volume(self, vol: float):
        self._volume = max(0.0, min(1.0, vol))
        self._apply_output_volume()

    def set_muted(self, muted: bool):
        self._muted = muted
        self._apply_output_volume()

    def _apply_output_volume(self):
        self.audio_output.setVolume(0.0 if self._muted else self._volume)

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.state_changed.emit("playing")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.state_changed.emit("paused")
        else:
            self.state_changed.emit("stopped")

    def _on_error(self, error, error_string=""):
        msg = error_string or str(error)
        if msg:
            self.metadata_update.emit(f"Error remoto: {msg}")
        self.state_changed.emit("error")

    def _on_metadata_changed(self):
        meta = self.player.metaData()
        if meta:
            title = meta.stringValue(QMediaMetaData.Key.Title)
            artist = meta.stringValue(QMediaMetaData.Key.ContributingArtist)
            if not artist:
                artist = meta.stringValue(QMediaMetaData.Key.Author)
            if title or artist:
                text = f"{artist} - {title}" if artist else title
                self.metadata_update.emit(text)


class StreamDTMFDetector(QObject):
    """Analiza audio remoto o muestras internas y detecta una secuencia DTMF."""
    action_detected = pyqtSignal(str)
    digit_detected  = pyqtSignal(str)
    level_update    = pyqtSignal(float, float)
    status_update   = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc   = None
        self._timer  = None
        self._sr     = 44100
        self._block  = 2048
        self._tol    = 30
        self._thresh = 0.02
        self._buf    = b""
        self._seq    = []
        self._seq_progress = {}
        self._tone_refs = {}
        self._log    = []
        self._last_emitted = ""
        self._silence_count = 0
        self._last_digit_time = 0.0
        self._cooldown_until = 0.0
        self._sequence_cooldown = 0.8
        self._last_action_seq = ""
        self._last_action_time = 0.0

    def set_params(self, freq_tol: int = 20, rms_threshold: float = 0.01):
        self._tol = freq_tol
        self._thresh = max(0.0001, rms_threshold * 0.05)

    def arm(self, stop_seq):
        self._buf = b""
        self._log = []
        if isinstance(stop_seq, (list, tuple, set)):
            self._seq = [str(s).strip() for s in stop_seq if str(s).strip()]
        else:
            seq = str(stop_seq).strip()
            self._seq = [seq] if seq else []
        self._seq_progress = {seq: 0 for seq in self._seq}
        self._last_emitted = ""
        self._silence_count = 0
        self._last_digit_time = 0.0
        self._cooldown_until = 0.0
        self._feed_buf = np.array([], dtype=np.float32)
        self._last_action_seq = ""
        self._last_action_time = 0.0

    def start(self, url: str, stop_seq: str):
        self.stop()
        self.arm(stop_seq)
        if "np" not in globals():
            self.status_update.emit("Detector remoto: numpy no disponible")
            return
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.ForwardedErrorChannel)
        self._proc.errorOccurred.connect(
            lambda err: self.status_update.emit(f"Detector remoto: error FFmpeg ({err})")
        )
        self._proc.finished.connect(
            lambda code, status: self.status_update.emit("Detector remoto: detenido")
        )
        self._proc.start(ffmpeg_path(), [
            "-hide_banner", "-nostdin", "-loglevel", "error",
            "-reconnect", "1", "-reconnect_streamed", "1",
            "-reconnect_at_eof", "1", "-reconnect_on_network_error", "1",
            "-reconnect_delay_max", "5",
            "-rw_timeout", "10000000",
            "-i", url,
            "-vn", "-sn", "-dn", "-map", "0:a:0",
            "-f", "f32le", "-acodec", "pcm_f32le",
            "-ar", str(self._sr), "-ac", "1",
            "-"
        ])
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_data)
        self._timer.start(50)
        self.status_update.emit("Detector remoto: escuchando salida/stream")

    def stop(self):
        if self._timer:
            self._timer.stop()
            self._timer = None
        if self._proc:
            try: self._proc.kill()
            except: pass
            self._proc.waitForFinished(1000)
            self._proc = None
        self._last_emitted = ""
        self._silence_count = 0

    def feed_samples(self, samples, final_silence: bool = True):
        if "np" not in globals():
            return
        arr = np.asarray(samples, dtype=np.float32)
        if arr.ndim > 1:
            arr = arr.mean(axis=1)
        if arr.size == 0:
            return
            
        if not hasattr(self, '_feed_buf'):
            self._feed_buf = np.array([], dtype=np.float32)
            
        self._feed_buf = np.concatenate((self._feed_buf, arr))
        
        while len(self._feed_buf) >= self._block:
            chunk = self._feed_buf[:self._block]
            self._feed_buf = self._feed_buf[self._block:]
            self._process_block(chunk)
            
        if final_silence:
            self._process_block(np.zeros(self._block, dtype=np.float32))

    def feed_digit(self, digit: str, bypass_cooldown: bool = False):
        digit = str(digit).strip()
        if not digit:
            return
        self._last_emitted = ""
        self._silence_count = 0
        self._last_digit_time = time.time()
        self.status_update.emit(f"DTMF remoto: {digit}")
        self.digit_detected.emit(digit)
        self._append_digit(digit)

    def _on_data(self):
        if not self._proc:
            return
        self._buf += bytes(self._proc.readAllStandardOutput())
        chunk_bytes = self._block * 4
        while len(self._buf) >= chunk_bytes:
            raw = self._buf[:chunk_bytes]
            self._buf = self._buf[chunk_bytes:]
            samples = np.frombuffer(raw, dtype=np.float32)
            self._process_block(samples)

    def _process_block(self, samples):
        rms = float(np.sqrt(np.mean(samples ** 2)))
        self.level_update.emit(rms * 5, rms * 4.8)

        if rms <= self._thresh:
            self._silence_count += 1
            if self._silence_count >= 1:
                self._last_emitted = ""
            return

        digit = self._decode(samples)
        if digit:
            if digit != self._last_emitted:
                now = time.time()
                if now - self._last_digit_time > 5.0:
                    self._log.clear()
                    self._seq_progress = {seq: 0 for seq in self._seq}
                self._last_digit_time = now
                self._last_emitted = digit
                self._silence_count = 0
                self._append_digit(digit)
            else:
                self._silence_count = 0
        else:
            self._silence_count += 1
            if self._silence_count >= 1:
                self._last_emitted = ""

    def _append_digit(self, digit: str):
        for target in self._seq:
            if not target:
                continue
            pos = self._seq_progress.get(target, 0)
            expected = target[pos] if pos < len(target) else target[0]

            if digit == expected:
                pos += 1
            elif digit == target[0]:
                pos = 1
            elif digit not in target:
                self._seq_progress[target] = pos
                continue
            else:
                pos = 0

            if pos >= len(target):
                self._seq_progress[target] = 0
                self._log.clear()
                now = time.time()
                repeated = (
                    target == self._last_action_seq and
                    now - self._last_action_time < self._sequence_cooldown
                )
                self._last_action_seq = target
                self._last_action_time = now
                if not repeated:
                    self.status_update.emit("Secuencia remota detectada")
                    self.action_detected.emit(target)
                break
            self._seq_progress[target] = pos

    def _decode(self, samples):
        samples = np.asarray(samples, dtype=np.float32)
        if samples.size == 0:
            return ""
        centered = samples - float(np.mean(samples))
        energy = float(np.sum(centered * centered)) + 1e-12

        row_vals = [(self._dtmf_power(centered, f), f) for f in ROW_FREQS]
        col_vals = [(self._dtmf_power(centered, f), f) for f in COL_FREQS]
        row_vals.sort(reverse=True)
        col_vals.sort(reverse=True)
        best_row = row_vals[0]
        best_col = col_vals[0]
        second_row = row_vals[1][0] if len(row_vals) > 1 else 0.0
        second_col = col_vals[1][0] if len(col_vals) > 1 else 0.0

        min_power = energy * 1.5
        if best_row[0] < min_power or best_col[0] < min_power:
            return ""
        if second_row > 0 and best_row[0] < second_row * 1.08:
            return ""
        if second_col > 0 and best_col[0] < second_col * 1.08:
            return ""
        twist = best_row[0] / max(best_col[0], 1e-9)
        if twist < 0.05 or twist > 20.0:
            return ""
        return DTMF_FREQS.get((best_row[1], best_col[1]), "")

    def _dtmf_power(self, samples, freq: int) -> float:
        power = 0.0
        for candidate in (freq - self._tol, freq, freq + self._tol):
            if candidate <= 0:
                continue
            ref = self._tone_reference(len(samples), candidate)
            real = float(np.dot(samples, ref[0]))
            imag = float(np.dot(samples, ref[1]))
            power = max(power, real * real + imag * imag)
        return power

    def _tone_reference(self, n: int, freq: int):
        key = (n, freq)
        ref = self._tone_refs.get(key)
        if ref is None:
            t = np.arange(n, dtype=np.float32) / self._sr
            window = np.hanning(n).astype(np.float32)
            ref = (
                np.cos(2 * np.pi * freq * t).astype(np.float32) * window,
                np.sin(2 * np.pi * freq * t).astype(np.float32) * window,
            )
            self._tone_refs[key] = ref
        return ref


DTMF_FREQS = {
    (697, 1209): "1", (697, 1336): "2", (697, 1477): "3", (697, 1633): "A",
    (770, 1209): "4", (770, 1336): "5", (770, 1477): "6", (770, 1633): "B",
    (852, 1209): "7", (852, 1336): "8", (852, 1477): "9", (852, 1633): "C",
    (941, 1209): "*", (941, 1336): "0", (941, 1477): "#", (941, 1633): "D",
}
ROW_FREQS = [697, 770, 852, 941]
COL_FREQS = [1209, 1336, 1477, 1633]


class DTMFDetector(QObject):
    """Detecta tonos DTMF mediante FFT.
    Enfoque simple: emite dígito cuando cambia, requiere silencio entre dígitos."""
    digit_detected = pyqtSignal(str)
    level_update   = pyqtSignal(float, float)
    status_update  = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running  = False
        self._thread   = None
        self._sr       = 44100
        self._block    = 2048
        self._tol      = 30
        self._thresh   = 0.008
        self._device   = None
        self._heartbeat_counter = 0
        self._last_emitted = ""
        self._silence_count = 0
        self._external_mode = False
        self._tone_refs = {}

    def set_params(self, freq_tol: int = 20, rms_threshold: float = 0.01,
                   device=None):
        self._tol    = freq_tol
        self._thresh = rms_threshold
        self._device = device
        if self._running and not self._external_mode:
            self.stop()
            self.start()

    def start(self):
        if not SOUND_OK:
            return
        if self._running:
            return
        self._running = True
        self._last_emitted = ""
        self._silence_count = 0
        self._thread  = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _run(self):
        try:
            print(f"[DTMF] Iniciando detector en dispositivo {self._device}")
            self.status_update.emit(f"Detector: activo (dev={self._device})")
            with sd.InputStream(samplerate=self._sr, channels=1,
                                blocksize=self._block, device=self._device,
                                dtype="float32") as stream:
                self._stream = stream
                print(f"[DTMF] Stream abierto")
                while self._running:
                    data, _ = stream.read(self._block)
                    mono = data[:, 0]
                    rms  = float(np.sqrt(np.mean(mono ** 2)))
                    self.level_update.emit(rms * 5, rms * 4.8)

                    self._heartbeat_counter += 1
                    if self._heartbeat_counter % 100 == 0:
                        self.status_update.emit(f"rms={rms:.4f}")

                    digit = self._decode(mono) if rms > self._thresh else ""
                    if digit:
                        if digit != self._last_emitted:
                            self._last_emitted = digit
                            self._silence_count = 0
                            # print(f"[DTMF] >>> EMITIDO: {digit} <<<")
                            self.status_update.emit(f"DTMF: {digit}")
                            self.digit_detected.emit(digit)
                        else:
                            self._silence_count = 0
                    else:
                        self._silence_count += 1
                        if self._silence_count >= 1:
                            self._last_emitted = ""
        except Exception as e:
            print(f"[DTMF] ERROR: {e}")
            self.status_update.emit(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

    def _decode(self, samples: "np.ndarray") -> str:
        samples = np.asarray(samples, dtype=np.float32)
        if samples.size == 0:
            return ""
        centered = samples - float(np.mean(samples))
        energy = float(np.sum(centered * centered)) + 1e-12

        row_vals = [(self._dtmf_power(centered, f), f) for f in ROW_FREQS]
        col_vals = [(self._dtmf_power(centered, f), f) for f in COL_FREQS]
        row_vals.sort(reverse=True)
        col_vals.sort(reverse=True)
        best_row = row_vals[0]
        best_col = col_vals[0]
        second_row = row_vals[1][0] if len(row_vals) > 1 else 0.0
        second_col = col_vals[1][0] if len(col_vals) > 1 else 0.0

        min_power = energy * 1.5
        if best_row[0] < min_power or best_col[0] < min_power:
            return ""
        if second_row > 0 and best_row[0] < second_row * 1.08:
            return ""
        if second_col > 0 and best_col[0] < second_col * 1.08:
            return ""
        twist = best_row[0] / max(best_col[0], 1e-9)
        if twist < 0.05 or twist > 20.0:
            return ""
        return DTMF_FREQS.get((best_row[1], best_col[1]), "")

    def _dtmf_power(self, samples, freq: int) -> float:
        power = 0.0
        for candidate in (freq - self._tol, freq, freq + self._tol):
            if candidate <= 0:
                continue
            ref = self._tone_reference(len(samples), candidate)
            real = float(np.dot(samples, ref[0]))
            imag = float(np.dot(samples, ref[1]))
            power = max(power, real * real + imag * imag)
        return power

    def _tone_reference(self, n: int, freq: int):
        key = (n, freq)
        ref = self._tone_refs.get(key)
        if ref is None:
            t = np.arange(n, dtype=np.float32) / self._sr
            window = np.hanning(n).astype(np.float32)
            ref = (
                np.cos(2 * np.pi * freq * t).astype(np.float32) * window,
                np.sin(2 * np.pi * freq * t).astype(np.float32) * window,
            )
            self._tone_refs[key] = ref
        return ref

    def start_external(self):
        """Inicia en modo externo (recibe muestras del passthrough, sin abrir stream propio)."""
        self._running = True
        self._external_mode = True
        self._last_emitted = ""
        self._silence_count = 0
        self._heartbeat_counter = 0
        self._ext_buf = np.array([], dtype=np.float32)
        print("[DTMF] Iniciado en modo externo (alimentado por passthrough)")

    def stop_external(self):
        """Detiene modo externo."""
        self._running = False
        self._external_mode = False
        print("[DTMF] Modo externo detenido")

    def feed_samples(self, indata):
        """Recibe muestras del passthrough en lugar de su propio stream."""
        if not self._running:
            return
            
        if not hasattr(self, '_ext_buf'):
            self._ext_buf = np.array([], dtype=np.float32)
            
        mono = np.mean(indata, axis=1) if indata.ndim > 1 else indata
        self._ext_buf = np.concatenate((self._ext_buf, mono))
        
        while len(self._ext_buf) >= self._block:
            chunk = self._ext_buf[:self._block]
            self._ext_buf = self._ext_buf[self._block:]
            
            rms = float(np.sqrt(np.mean(chunk ** 2)))
            self.level_update.emit(rms * 5, rms * 4.8)

            self._heartbeat_counter += 1
            if self._heartbeat_counter % 100 == 0:
                self.status_update.emit(f"rms={rms:.4f}")

            digit = self._decode(chunk) if rms > self._thresh else ""
            if digit:
                if digit != self._last_emitted:
                    self._last_emitted = digit
                    self._silence_count = 0
                    self.status_update.emit(f"DTMF: {digit}")
                    self.digit_detected.emit(digit)
                else:
                    self._silence_count = 0
            else:
                self._silence_count += 1
                if self._silence_count >= 1:
                    self._last_emitted = ""

    def feed_digit(self, digit: str):
        """Inyecta un dígito DTMF generado internamente por la app."""
        if not self._running:
            return
        digit = str(digit).strip()
        if not digit:
            return
        self._last_emitted = ""
        self._silence_count = 0
        self.status_update.emit(f"DTMF: {digit}")
        self.digit_detected.emit(digit)


class AudioPassthrough(QObject):
    """Pasa audio de entrada a salida en tiempo real (Señal Principal)."""
    level_update = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._thread = None
        self._sr = 44100
        self._block = 2048
        self._in_device = None
        self._out_device = None
        self._volume = 1.0
        self._muted = False
        self._audio_queue = queue.Queue(maxsize=100)
        self._external_input_callbacks = []

    def register_input_callback(self, cb):
        if not any(existing == cb for existing in self._external_input_callbacks):
            self._external_input_callbacks.append(cb)

    def unregister_input_callback(self, cb):
        self._external_input_callbacks = [c for c in self._external_input_callbacks if c != cb]

    @property
    def is_running(self):
        return self._running

    def set_devices(self, in_device, out_device):
        self._in_device = in_device
        self._out_device = out_device
        if self._running:
            self.stop()
            self.start()

    def set_volume(self, vol: float):
        self._volume = max(0.0, min(1.0, vol))

    def set_muted(self, muted: bool):
        self._muted = bool(muted)

    def start(self):
        if not SOUND_OK:
            return
        if self._running:
            return
        if self._in_device is None or self._out_device is None:
            print("[Passthrough] ERROR: dispositivos no configurados")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _run(self):
        try:
            print(f"[Passthrough] Iniciando: in={self._in_device}, out={self._out_device}")
            
            in_dev_info = sd.query_devices(self._in_device)
            out_dev_info = sd.query_devices(self._out_device)
            max_in = in_dev_info['max_input_channels']
            max_out = out_dev_info['max_output_channels']
            # Forzar stereo (2 canales) si el dispositivo lo soporta
            in_channels = min(max_in, 2) if max_in >= 2 else max_in
            out_channels = min(max_out, 2) if max_out >= 2 else max_out
            
            print(f"[Passthrough] Input: {in_channels} ch, Output: {out_channels} ch")
            
            def input_callback(indata, frames, callback_time, status):
                if status:
                    print(f"[Passthrough] Input status: {status}")
                try:
                    self._audio_queue.put_nowait(indata.copy())
                except queue.Full:
                    pass
                # Alimentar callbacks externos (DTMF)
                for cb in list(self._external_input_callbacks):
                    try:
                        cb(indata.copy())
                    except Exception:
                        pass
                # Calcular niveles stereo L/R
                if indata.ndim > 1 and indata.shape[1] >= 2:
                    left = indata[:, 0]
                    right = indata[:, 1]
                else:
                    left = indata[:, 0] if indata.ndim > 1 else indata
                    right = left
                rms_l = float(np.sqrt(np.mean(left ** 2)))
                rms_r = float(np.sqrt(np.mean(right ** 2)))
                self.level_update.emit(rms_l * 5, rms_r * 5)
            
            def output_callback(outdata, frames, callback_time, status):
                if status:
                    print(f"[Passthrough] Output status: {status}")
                try:
                    data = self._audio_queue.get_nowait()
                    output_volume = 0.0 if self._muted else self._volume
                    if data.shape[1] == out_channels:
                        outdata[:] = data * output_volume
                    else:
                        for ch in range(out_channels):
                            outdata[:, ch] = data[:, 0] * output_volume
                except queue.Empty:
                    outdata.fill(0)
            
            with sd.InputStream(device=self._in_device, samplerate=self._sr,
                               channels=in_channels, blocksize=self._block,
                               dtype="float32", callback=input_callback) as in_stream, \
                 sd.OutputStream(device=self._out_device, samplerate=self._sr,
                                channels=out_channels, blocksize=self._block,
                                dtype="float32", callback=output_callback) as out_stream:
                self._in_stream = in_stream
                self._out_stream = out_stream
                print(f"[Passthrough] Streams duplex abiertos")
                while self._running:
                    sd.sleep(100)
        except Exception as e:
            print(f"[Passthrough] ERROR: {e}")
            import traceback
            traceback.print_exc()


# ══════════════════════════════════════════════════════════════════════════════
#  CAPTURA LOOPBACK (captura la salida de audio del sistema)
# ══════════════════════════════════════════════════════════════════════════════
class AudioLoopbackCapture(QObject):
    """Captura audio de salida del sistema (loopback) para transmitir."""
    audio_data = pyqtSignal(bytes)
    level_update = pyqtSignal(float, float)
    error_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._thread = None
        self._sr = 44100
        self._block = 4096
        self._device = None
        self._channels = 2
        self._external_callbacks = []

    def register_callback(self, cb):
        if cb not in self._external_callbacks:
            self._external_callbacks.append(cb)

    def unregister_callback(self, cb):
        self._external_callbacks = [c for c in self._external_callbacks if c != cb]

    def set_device(self, device_id):
        self._device = device_id

    def set_sample_rate(self, sr):
        self._sr = sr

    def set_channels(self, ch):
        self._channels = ch

    @property
    def is_running(self):
        return self._running

    def start(self):
        if not SOUND_OK:
            self.error_signal.emit("sounddevice no disponible")
            return
        if self._running:
            return
        if self._device is None:
            self.error_signal.emit("Dispositivo loopback no configurado")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self):
        try:
            print(f"[Loopback] Iniciando captura: device={self._device}, sr={self._sr}, ch={self._channels}")

            def callback(indata, frames, time_info, status):
                if status:
                    print(f"[Loopback] Status: {status}")
                data = indata.copy()
                raw_bytes = data.tobytes()
                self.audio_data.emit(raw_bytes)
                for cb in list(self._external_callbacks):
                    try:
                        cb(data)
                    except Exception:
                        pass
                if data.ndim > 1 and data.shape[1] >= 2:
                    left = data[:, 0]
                    right = data[:, 1]
                else:
                    left = data[:, 0] if data.ndim > 1 else data
                    right = left
                rms_l = float(np.sqrt(np.mean(left ** 2)))
                rms_r = float(np.sqrt(np.mean(right ** 2)))
                self.level_update.emit(rms_l * 5, rms_r * 5)

            with sd.InputStream(
                device=self._device,
                samplerate=self._sr,
                channels=self._channels,
                blocksize=self._block,
                dtype="float32",
                callback=callback
            ) as stream:
                self._stream = stream
                print(f"[Loopback] Stream abierto")
                while self._running:
                    sd.sleep(100)
        except Exception as e:
            print(f"[Loopback] ERROR: {e}")
            self.error_signal.emit(f"Error captura loopback: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  ENCODER DE AUDIO (FFmpeg subprocess)
# ══════════════════════════════════════════════════════════════════════════════
class StreamEncoder(QObject):
    """Codifica audio PCM a Opus o MP3 usando FFmpeg."""
    encoded_data = pyqtSignal(bytes)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc = None
        self._running = False
        self._thread = None
        self._codec = "opus"
        self._bitrate = 128
        self._sample_rate = 44100
        self._channels = 2

    def set_codec(self, codec):
        self._codec = codec

    def set_bitrate(self, bitrate):
        self._bitrate = bitrate

    def set_sample_rate(self, sr):
        self._sample_rate = sr

    def set_channels(self, ch):
        self._channels = ch

    @property
    def is_running(self):
        return self._running

    def start(self):
        if self._running:
            return
        try:
            ff = ffmpeg_path()
            if self._codec == "opus":
                codec_args = ["-c:a", "libopus", "-b:a", f"{self._bitrate}k",
                              "-vbr", "on", "-compression_level", "10"]
                fmt = "opus"
            else:
                codec_args = ["-c:a", "libmp3lame", "-b:a", f"{self._bitrate}k"]
                fmt = "mp3"

            args = [
                ff, "-hide_banner", "-nostdin", "-loglevel", "error",
                "-f", "f32le",
                "-ar", str(self._sample_rate),
                "-ac", str(self._channels),
                "-i", "pipe:0",
                "-vn", "-sn", "-dn",
            ] + codec_args + [
                "-f", fmt,
                "pipe:1"
            ]

            self._proc = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=65536
            )
            self._running = True
            self._thread = threading.Thread(target=self._read_output, daemon=True)
            self._thread.start()
            self.status_signal.emit(f"Encoder {self._codec.upper()} iniciado")
            print(f"[Encoder] Iniciado: {self._codec} @ {self._bitrate}k, {self._sample_rate}Hz, {self._channels}ch")
        except Exception as e:
            self.error_signal.emit(f"Error iniciando encoder: {e}")

    def stop(self):
        self._running = False
        if self._proc:
            try:
                self._proc.stdin.close()
            except:
                pass
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except:
                try:
                    self._proc.kill()
                except:
                    pass
            self._proc = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        self.status_signal.emit("Encoder detenido")

    def write_pcm(self, data: bytes):
        if self._proc and self._running:
            try:
                self._proc.stdin.write(data)
                self._proc.stdin.flush()
            except Exception as e:
                self.error_signal.emit(f"Error escribiendo al encoder: {e}")

    def _read_output(self):
        try:
            while self._running:
                chunk = self._proc.stdout.read(65536)
                if not chunk:
                    break
                self.encoded_data.emit(chunk)
        except Exception as e:
            if self._running:
                self.error_signal.emit(f"Error leyendo encoder: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  CLIENTE DE STREAMING (Icecast/Shoutcast)
# ══════════════════════════════════════════════════════════════════════════════
class StreamClient(QObject):
    """Envía datos codificados a servidor Icecast/Shoutcast vía HTTP PUT."""
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    bytes_sent = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._url = ""
        self._username = "source"
        self._password = ""
        self._mount = "/live"
        self._server_type = "icecast"
        self._name = "RadioSAT XP"
        self._genre = "Various"
        self._description = ""
        self._content_type = "audio/mpeg"
        self._running = False
        self._thread = None
        self._conn = None
        self._total_sent = 0
        self._reconnect_delay = 1
        self._max_reconnect_delay = 30
        self._data_queue = queue.Queue(maxsize=256)

    def set_server(self, url, port, mount, username, password, server_type="icecast",
                   content_type="audio/mpeg"):
        self._url = f"{url}:{port}"
        self._mount = mount if mount.startswith("/") else f"/{mount}"
        self._username = username
        self._password = password
        self._server_type = server_type
        self._content_type = content_type

    def set_metadata(self, name, genre, description):
        self._name = name
        self._genre = genre
        self._description = description

    @property
    def is_connected(self):
        return self._running and self._conn is not None

    @property
    def total_bytes_sent(self):
        return self._total_sent

    def start(self):
        if self._running:
            return
        if not self._url or not self._password:
            self.error_signal.emit("URL o contraseña no configurada")
            return
        self._total_sent = 0
        while not self._data_queue.empty():
            try:
                self._data_queue.get_nowait()
            except queue.Empty:
                break
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._conn:
            try:
                self._conn.close()
            except:
                pass
            self._conn = None
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        self.disconnected.emit()
        self.status_signal.emit("Desconectado")

    def send_data(self, data: bytes):
        if not self._running or not data:
            return False
        try:
            self._data_queue.put_nowait(data)
            return True
        except queue.Full:
            try:
                self._data_queue.get_nowait()
                self._data_queue.put_nowait(data)
                self.status_signal.emit("Buffer de transmisión lleno; descartando audio antiguo")
                return True
            except queue.Empty:
                return False

    def _connect(self):
        import base64
        import socket
        import ssl
        import urllib.parse

        try:
            parsed = urllib.parse.urlparse(self._url if "://" in self._url else f"http://{self._url}")
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 8000)
            sock = socket.create_connection((host, port), timeout=10)
            if parsed.scheme == "https":
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
            auth = base64.b64encode(f"{self._username}:{self._password}".encode()).decode()
            path = self._mount if self._server_type == "icecast" else "/"
            method = "PUT" if self._server_type == "icecast" else "SOURCE"
            headers = [
                f"{method} {path} HTTP/1.0", f"Host: {host}:{port}",
                f"Authorization: Basic {auth}", f"Content-Type: {self._content_type}",
                "User-Agent: RadioSAT XP/1.0", f"Ice-Name: {self._name}",
                f"Ice-Genre: {self._genre}", f"Ice-Description: {self._description}",
                "Ice-Public: 0", "Connection: keep-alive", "", "",
            ]
            sock.sendall("\r\n".join(headers).encode("utf-8"))
            response = b""
            while b"\r\n\r\n" not in response and len(response) < 16384:
                chunk = sock.recv(2048)
                if not chunk:
                    break
                response += chunk
            status_line = response.split(b"\r\n", 1)[0].decode("latin-1", errors="replace")
            accepted = " 200 " in f" {status_line} " or " 201 " in f" {status_line} " or status_line.startswith("OK2")
            if accepted:
                sock.settimeout(10)
                self._conn = sock
                self._reconnect_delay = 1
                self.status_signal.emit(f"Conectado a {host}:{port}{path}")
                self.connected.emit()
                return True
            sock.close()
            self.error_signal.emit(f"Servidor rechazó conexión: {status_line or 'sin respuesta'}")
            return False
        except Exception as e:
            self._conn = None
            self.error_signal.emit(f"Error conectando: {e}")
            return False

    def _reconnect(self):
        if self._conn:
            try:
                self._conn.close()
            except:
                pass
            self._conn = None
        import time
        self.status_signal.emit(f"Reconectando en {self._reconnect_delay}s...")
        time.sleep(self._reconnect_delay)
        self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)
        self._connect()

    def _run(self):
        while self._running:
            if self._conn is None and not self._connect():
                time.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)
                continue
            try:
                data = self._data_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._conn.sendall(data)
                self._total_sent += len(data)
                self.bytes_sent.emit(len(data))
            except Exception as e:
                self.error_signal.emit(f"Error enviando datos: {e}")
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None
                self.disconnected.emit()


# ══════════════════════════════════════════════════════════════════════════════
#  WORKER TTS (hilo aparte para no bloquear UI)
# ══════════════════════════════════════════════════════════════════════════════
class TTSWorker(QThread):
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = text

    def run(self):
        if not TTS_OK:
            self.error.emit("pyttsx3 no disponible")
            return
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 160)
            engine.setProperty("volume", 0.9)
            engine.say(self._text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            self.error.emit(str(e))
        self.finished.emit()


# ══════════════════════════════════════════════════════════════════════════════
#  WIDGETS VISUALES
# ══════════════════════════════════════════════════════════════════════════════

class LEDIndicator(QWidget):
    def __init__(self, color=QColor(0, 220, 0), parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self._on    = False
        self._color = color

    def set_on(self, s: bool):
        self._on = s
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self._color if self._on else QColor(50, 50, 60)
        # Outer glow when on
        if self._on:
            glow = QRadialGradient(9, 9, 12)
            glow.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 80))
            glow.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(0, 0, 18, 18)
        # Main LED
        g = QRadialGradient(7, 6, 8)
        g.setColorAt(0, color.lighter(200) if self._on else QColor(70, 70, 80))
        g.setColorAt(0.7, color if self._on else QColor(50, 50, 60))
        g.setColorAt(1, color.darker(180) if self._on else QColor(35, 35, 45))
        p.setBrush(QBrush(g))
        p.setPen(QPen(color.darker(200) if self._on else QColor(40, 40, 50), 1))
        p.drawEllipse(2, 2, 14, 14)
        # Specular highlight
        if self._on:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 100))
            p.drawEllipse(5, 4, 5, 4)


class MediaLibraryTable(QTableWidget):
    """Tabla origen para arrastrar uno o varios audios de la biblioteca."""

    MIME_TYPE = "application/x-radiosat-audio-paths"

    def __init__(self, rows=0, columns=0, parent=None):
        super().__init__(rows, columns, parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def mimeData(self, items):
        mime = super().mimeData(items)
        paths = []
        for row in sorted({item.row() for item in items}):
            path_item = self.item(row, 5)
            if path_item and path_item.text() and path_item.text() not in paths:
                paths.append(path_item.text())
        if paths:
            import json
            mime.setData(self.MIME_TYPE, json.dumps(paths).encode("utf-8"))
        return mime


class AudioDropTable(QTableWidget):
    """Tabla destino que recibe audios desde la biblioteca o Finder."""

    filesDropped = pyqtSignal(list)

    def __init__(self, rows=0, columns=0, parent=None):
        super().__init__(rows, columns, parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    @staticmethod
    def _paths_from_mime(mime):
        paths = []
        if mime.hasFormat(MediaLibraryTable.MIME_TYPE):
            try:
                import json
                paths.extend(json.loads(bytes(mime.data(MediaLibraryTable.MIME_TYPE)).decode("utf-8")))
            except (TypeError, ValueError, UnicodeDecodeError):
                pass
        if mime.hasUrls():
            paths.extend(url.toLocalFile() for url in mime.urls() if url.isLocalFile())
        return [path for path in dict.fromkeys(paths) if path]

    def dragEnterEvent(self, event):
        if self._paths_from_mime(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._paths_from_mime(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = self._paths_from_mime(event.mimeData())
        if not paths:
            event.ignore()
            return
        self.filesDropped.emit(paths)
        event.acceptProposedAction()


class VUBar(QWidget):
    """Barra VU horizontal animada a 60 FPS para máxima fluidez."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(18)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._target_val = 0.0
        self._val = 0.0
        self._peak = 0.0
        self._peak_hold = 0
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(16)  # ~60 FPS

    def set_value(self, v: float):
        self._target_val = max(0.0, min(1.0, v))

    def _animate(self):
        if not self.isVisible():
            return
            
        # Animación súper fluida: ataque rápido, decaimiento suave
        if self._target_val > self._val:
            self._val += (self._target_val - self._val) * 0.4
        else:
            self._val += (self._target_val - self._val) * 0.08

        # Mantenimiento del pico
        if self._val >= self._peak:
            self._peak = self._val
            self._peak_hold = 60
        else:
            if self._peak_hold > 0:
                self._peak_hold -= 1
            else:
                self._peak = max(0, self._peak - 0.005)
                
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = _current_theme
        w, h = self.width(), self.height()
        
        bar_x = 0
        bar_y = 0
        bar_w = w
        bar_h = h
        radius = 2
        
        # Fondo de la barra (rectangular con bordes mínimos)
        bg_rect = QRectF(bar_x, bar_y, bar_w, bar_h)
        path_bg = QPainterPath()
        path_bg.addRoundedRect(bg_rect, radius, radius)
        p.fillPath(path_bg, QColor(t["vu_bg"]))
        
        filled = self._val * bar_w
        if filled > 0:
            # Gradiente continuo
            g = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            g.setColorAt(0.0, QColor(t["vu_green"]))
            g.setColorAt(0.70, QColor(t["vu_green"]))
            g.setColorAt(0.85, QColor(t["vu_amber"]))
            g.setColorAt(0.95, QColor(t["vu_red"]))
            g.setColorAt(1.0, QColor(t["vu_red"]))
            
            # Recortar la parte llena
            p.save()
            p.setClipRect(QRectF(bar_x, bar_y, filled, bar_h))
            
            p.fillPath(path_bg, g)
            p.restore()

        # Brillo superior sutil
        highlight = QLinearGradient(0, bar_y, 0, bar_y + bar_h)
        highlight.setColorAt(0.0, QColor(255, 255, 255, 30))
        highlight.setColorAt(0.5, QColor(255, 255, 255, 0))
        p.fillPath(path_bg, highlight)
        
        # Borde
        p.setPen(QPen(QColor(t["border"]), 1))
        p.drawPath(path_bg)

        # Indicador de Pico (Peak Hold)
        if self._peak > 0.01:
            peak_x = bar_x + self._peak * bar_w
            peak_color = QColor(t["vu_red"]) if self._peak > 0.9 else (
                QColor(t["vu_amber"]) if self._peak > 0.75 else QColor(t["vu_green"]))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(peak_color)
            p.drawRect(QRectF(peak_x - 2, bar_y, 2, bar_h))


class WaveformWidget(QWidget):
    """Muestra el metadata en formato Scrolling (tipo marquesina) con estilo moderno."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(50)
        self._text = ""
        self._scrolling_offset = 0
        self._active = False
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update_scroll)
        self._timer.start(40)

    def set_metadata(self, text: str):
        if text != self._text:
            self._text = text
            self._scrolling_offset = self.width()
            self.update()

    def push_level(self, lvl: float):
        pass

    def set_idle(self):
        self._active = False
        self._text = "LISTO"
        self.update()

    def update_scroll(self):
        if not self._text or self._text == "LISTO":
            return
        self._scrolling_offset -= 2.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = _current_theme
        # Background with subtle gradient
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor(t["wave_bg"]).lighter(120))
        g.setColorAt(1, QColor(t["wave_bg"]))
        p.fillRect(self.rect(), g)
        # Inner border
        p.setPen(QPen(QColor(t["border"]), 1))
        p.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1, 6, 6)
        
        if not self._text:
            return

        # Text with glow effect
        p.setPen(QColor(t["wave_text"]))
        p.setFont(QFont("Menlo", 13, QFont.Weight.Bold))
        fm = p.fontMetrics()
        w = fm.horizontalAdvance(self._text)
        
        if self._scrolling_offset < -w:
            self._scrolling_offset = self.width()
            
        text_y = int(self.height()/2 + fm.height()/4)
        if w > self.width():
            # Glow behind text
            p.setPen(QColor(t["wave_text"]).darker(200))
            p.drawText(int(self._scrolling_offset) + 1, text_y + 1, self._text)
            p.setPen(QColor(t["wave_text"]))
            p.drawText(int(self._scrolling_offset), text_y, self._text)
        else:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._text)


class LiveClock(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("liveClock")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAccessibleName("Hora local")
        t = _current_theme
        clock_background = t['surface_raised'] if t is THEME_LIGHT else t['clock_bg']
        self.setStyleSheet(f"""
            QLabel#liveClock {{
                background: {clock_background};
                color: {t['text_primary']};
                border: 1px solid {t['border']};
                border-radius: 5px;
                padding: 6px 14px;
                font-size: 28px;
                font-weight: 700;
            }}
        """)
        self.setMinimumSize(210, 52)
        t2 = QTimer(self)
        t2.timeout.connect(self._tick)
        t2.start(1000)
        self._timer = t2
        self._tick()

    def _tick(self):
        self.setText(datetime.now().strftime("%H:%M:%S"))


class XPTitleBar(QFrame):
    def __init__(self, title: str, icon_px: QPixmap = None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 8, 0)
        lay.setSpacing(6)

        if icon_px and not icon_px.isNull():
            lbl = QLabel()
            lbl.setPixmap(icon_px)
            lbl.setFixedSize(16, 16)
            lbl.setScaledContents(True)
            lay.addWidget(lbl)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(f"color:white; font-weight:bold; font-size:9pt; background:transparent;")
        lay.addWidget(lbl_t)
        lay.addStretch()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = _current_theme
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0.0, QColor(t["titlebar_start"]))
        g.setColorAt(0.5, QColor(t["titlebar_mid"]))
        g.setColorAt(1.0, QColor(t["titlebar_end"]))
        p.fillRect(self.rect(), g)
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.drawLine(0, 0, self.width(), 0)


class XPPanel(QFrame):
    def __init__(self, title: str, icon_name: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("XPPanel")
        t = _current_theme
        self.setStyleSheet(f"""
            QFrame#XPPanel {{
                border: 1px solid {t['panel_border']};
                border-radius: 8px;
                background: {t['panel_bg']};
            }}
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        icon_px = xp_pixmap(icon_name, 16) if icon_name else None
        self.title_bar = XPTitleBar(title, icon_px)
        outer.addWidget(self.title_bar)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{t['border']};")
        outer.addWidget(sep)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background:transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(7)
        outer.addWidget(self.content_widget)

    def add_widget(self, w):  self.content_layout.addWidget(w)
    def add_layout(self, l):  self.content_layout.addLayout(l)





# ── Filtro de dispositivos de audio virtuales ──────────────────────────────
_VIRTUAL_AUDIO_PATTERNS = [
    r'(?i)microsoft sound mapper',
    r'(?i)primary sound (capture\s+)?driver',
    r'\[Loopback\]',
    r'(?i)^baddev\d*$',
    r'(?i)default directsound device',
    r'(?i)default wave device',
    r'^\s*$',
]

def _is_real_audio_device(dev_dict):
    """Filtra dispositivos virtuales/duplicados de PortAudio en Windows."""
    name = dev_dict.get("name", "")
    for pat in _VIRTUAL_AUDIO_PATTERNS:
        if re.search(pat, name):
            return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  DIÁLOGO DE CONFIGURACIÓN DEL ENCODER
# ══════════════════════════════════════════════════════════════════════════════
class EncoderSettingsDialog(QDialog):
    """Diálogo para configurar el encoder de streaming."""

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración del Encoder")
        self.setModal(True)
        self.resize(840, 690)
        self.setMinimumSize(760, 650)
        self._settings = settings or {}
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        t = _current_theme
        self.setObjectName("encoderDialog")
        self.setStyleSheet(f"""
            QDialog#encoderDialog {{ background:{t['background']}; color:{t['text_primary']}; }}
            QGroupBox {{ background:{t['surface']}; border:1px solid {t['border']};
                border-radius:7px; margin-top:12px; padding-top:12px;
                font-size:13px; font-weight:700; }}
            QGroupBox::title {{ subcontrol-origin:margin; left:12px; padding:0 6px;
                color:{t['accent_text']}; background:{t['surface']}; }}
            QGroupBox QLabel {{ color:{t['text_secondary']}; font-size:12px; font-weight:500; }}
            QLineEdit, QComboBox, QSpinBox {{ min-height:26px; max-height:30px;
                padding:2px 7px; font-size:12px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 18, 20, 16)

        header = QHBoxLayout(); header.setSpacing(10)
        icon = QLabel(); icon_pixmap = xp_pixmap("Chip.png", 38)
        if not icon_pixmap.isNull(): icon.setPixmap(icon_pixmap)
        icon.setFixedSize(42, 42); header.addWidget(icon)
        heading = QVBoxLayout(); heading.setSpacing(1)
        title = QLabel("Encoder y streaming")
        title.setStyleSheet(f"font-size:21px;font-weight:800;color:{t['text_primary']};")
        subtitle = QLabel("Configura la calidad, el servidor y la captura de programa.")
        subtitle.setStyleSheet(f"font-size:12px;color:{t['text_secondary']};")
        heading.addWidget(title); heading.addWidget(subtitle)
        header.addLayout(heading, 1); layout.addLayout(header)

        columns = QHBoxLayout(); columns.setSpacing(12)

        server_group = QGroupBox("Servidor de streaming")
        server_layout = QGridLayout(server_group)
        server_layout.setContentsMargins(14, 18, 14, 14)
        server_layout.setHorizontalSpacing(12); server_layout.setVerticalSpacing(8)
        server_layout.setColumnMinimumWidth(0, 86); server_layout.setColumnStretch(1, 1)
        self._server_type_combo = QComboBox(); self._server_type_combo.addItems(["Icecast", "Shoutcast"])
        self._host_edit = QLineEdit(); self._host_edit.setPlaceholderText("stream.ejemplo.com")
        self._port_spin = QSpinBox(); self._port_spin.setRange(1, 65535); self._port_spin.setValue(8000)
        self._mount_edit = QLineEdit(); self._mount_edit.setPlaceholderText("/live"); self._mount_edit.setText("/live")
        self._username_edit = QLineEdit(); self._username_edit.setText("source")
        self._password_edit = QLineEdit(); self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        for row, (label, field) in enumerate((
            ("Tipo", self._server_type_combo), ("URL / Host", self._host_edit),
            ("Puerto", self._port_spin), ("Mount point", self._mount_edit),
            ("Usuario", self._username_edit), ("Contraseña", self._password_edit),
        )):
            server_layout.addWidget(QLabel(label), row, 0); server_layout.addWidget(field, row, 1)
        columns.addWidget(server_group, 56)

        right_column = QVBoxLayout(); right_column.setSpacing(12)
        codec_group = QGroupBox("Codificación")
        codec_group.setMinimumHeight(185)
        codec_layout = QGridLayout(codec_group)
        codec_layout.setContentsMargins(14, 18, 14, 14)
        codec_layout.setHorizontalSpacing(12); codec_layout.setVerticalSpacing(8)
        codec_layout.setColumnMinimumWidth(0, 96); codec_layout.setColumnStretch(1, 1)
        self._codec_combo = QComboBox(); self._codec_combo.addItems(["Opus", "MP3"])
        self._codec_combo.currentTextChanged.connect(self._on_codec_changed)
        self._bitrate_spin = QSpinBox(); self._bitrate_spin.setRange(32, 320)
        self._bitrate_spin.setValue(128); self._bitrate_spin.setSuffix(" kbps")
        self._samplerate_combo = QComboBox(); self._samplerate_combo.addItems(["44100 Hz", "48000 Hz"])
        self._channels_combo = QComboBox(); self._channels_combo.addItems(["Stereo (2)", "Mono (1)"])
        for row, (label, field) in enumerate((
            ("Codec", self._codec_combo), ("Bitrate", self._bitrate_spin),
            ("Sample rate", self._samplerate_combo), ("Canales", self._channels_combo),
        )):
            codec_layout.addWidget(QLabel(label), row, 0); codec_layout.addWidget(field, row, 1)
        right_column.addWidget(codec_group)

        loopback_group = QGroupBox("Captura de audio")
        loopback_group.setMinimumHeight(150)
        loopback_layout = QGridLayout(loopback_group)
        loopback_layout.setContentsMargins(14, 18, 14, 14)
        loopback_layout.setHorizontalSpacing(10); loopback_layout.setVerticalSpacing(8)
        self._loopback_combo = QComboBox()
        loopback_layout.addWidget(QLabel("Dispositivo"), 0, 0)
        loopback_layout.addWidget(self._loopback_combo, 0, 1)
        btn_refresh = QPushButton("↻  Actualizar dispositivos"); btn_refresh.setFixedHeight(34)
        btn_refresh.clicked.connect(self._refresh_loopback_devices)
        loopback_layout.addWidget(btn_refresh, 1, 1)
        bus_note = QLabel("Debe recibir la mezcla completa: cadena, pauta local y retorno.")
        bus_note.setWordWrap(True); bus_note.setStyleSheet(f"font-size:10px;color:{t['text_dim']};")
        loopback_layout.addWidget(bus_note, 2, 0, 1, 2)
        right_column.addWidget(loopback_group); right_column.addStretch()
        columns.addLayout(right_column, 44); layout.addLayout(columns, 1)

        meta_group = QGroupBox("Metadatos del stream")
        meta_layout = QGridLayout(meta_group)
        meta_layout.setContentsMargins(14, 18, 14, 14)
        meta_layout.setHorizontalSpacing(10); meta_layout.setVerticalSpacing(8)
        self._name_edit = QLineEdit(); self._name_edit.setPlaceholderText("RadioSAT XP")
        self._genre_edit = QLineEdit(); self._genre_edit.setPlaceholderText("Various")
        self._desc_edit = QLineEdit(); self._desc_edit.setPlaceholderText("Descripción del stream…")
        meta_layout.addWidget(QLabel("Nombre"), 0, 0); meta_layout.addWidget(self._name_edit, 0, 1)
        meta_layout.addWidget(QLabel("Género"), 0, 2); meta_layout.addWidget(self._genre_edit, 0, 3)
        meta_layout.addWidget(QLabel("Descripción"), 1, 0); meta_layout.addWidget(self._desc_edit, 1, 1, 1, 3)
        layout.addWidget(meta_group)

        btn_layout = QHBoxLayout()
        hint = QLabel("La contraseña se guarda localmente en este equipo.")
        hint.setStyleSheet(f"font-size:11px;color:{t['text_dim']};")
        btn_layout.addWidget(hint); btn_layout.addStretch()
        btn_cancel = QPushButton("Cancelar"); btn_cancel.setFixedHeight(38); btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Guardar configuración"); btn_ok.setDefault(True); btn_ok.setFixedHeight(38)
        btn_ok.setStyleSheet(f"background:{t['accent']};color:white;font-weight:700;padding:0 18px;")
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel); btn_layout.addWidget(btn_ok); layout.addLayout(btn_layout)

        self._refresh_loopback_devices()

    def _on_codec_changed(self, codec):
        if codec == "Opus":
            self._bitrate_spin.setRange(32, 256)
            self._bitrate_spin.setValue(128)
        else:
            self._bitrate_spin.setRange(64, 320)
            self._bitrate_spin.setValue(192)

    def _refresh_loopback_devices(self):
        self._loopback_combo.clear()
        if not SOUND_OK:
            return
        try:
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    name = dev['name']
                    if any(p in name.lower() for p in ['loopback', 'blackhole', 'soundflower', 'virtual']):
                        self._loopback_combo.addItem(f"[Loopback] {name}", i)
            if self._loopback_combo.count() == 0:
                for i, dev in enumerate(devices):
                    if dev['max_input_channels'] > 0:
                        self._loopback_combo.addItem(dev['name'], i)
        except Exception as e:
            print(f"[EncoderDialog] Error listando dispositivos: {e}")

    def _load_settings(self):
        s = self._settings
        if 'codec' in s:
            idx = self._codec_combo.findText(s['codec'])
            if idx >= 0:
                self._codec_combo.setCurrentText(s['codec'])
        if 'bitrate' in s:
            self._bitrate_spin.setValue(s['bitrate'])
        if 'samplerate' in s:
            idx = self._samplerate_combo.findText(f"{s['samplerate']} Hz")
            if idx >= 0:
                self._samplerate_combo.setCurrentIndex(idx)
        if 'channels' in s:
            ch_text = "Stereo (2)" if s['channels'] == 2 else "Mono (1)"
            idx = self._channels_combo.findText(ch_text)
            if idx >= 0:
                self._channels_combo.setCurrentIndex(idx)
        if 'server_type' in s:
            idx = self._server_type_combo.findText(s['server_type'].title())
            if idx >= 0:
                self._server_type_combo.setCurrentIndex(idx)
        if 'host' in s:
            self._host_edit.setText(s['host'])
        if 'port' in s:
            self._port_spin.setValue(s['port'])
        if 'mount' in s:
            self._mount_edit.setText(s['mount'])
        if 'username' in s:
            self._username_edit.setText(s['username'])
        if 'password' in s:
            self._password_edit.setText(s['password'])
        if 'name' in s:
            self._name_edit.setText(s['name'])
        if 'genre' in s:
            self._genre_edit.setText(s['genre'])
        if 'description' in s:
            self._desc_edit.setText(s['description'])
        if 'loopback_device' in s:
            idx = self._loopback_combo.findData(s['loopback_device'])
            if idx >= 0:
                self._loopback_combo.setCurrentIndex(idx)
        if 'loopback_device_name' in s:
            saved_name = s['loopback_device_name']
            for idx in range(self._loopback_combo.count()):
                if saved_name and saved_name in self._loopback_combo.itemText(idx):
                    self._loopback_combo.setCurrentIndex(idx)
                    break

    def get_settings(self):
        codec = self._codec_combo.currentText()
        sr_text = self._samplerate_combo.currentText()
        samplerate = int(sr_text.split()[0])
        ch_text = self._channels_combo.currentText()
        channels = 2 if "Stereo" in ch_text else 1
        server_type = self._server_type_combo.currentText().lower()
        loopback_dev = self._loopback_combo.currentData()

        return {
            'codec': codec,
            'bitrate': self._bitrate_spin.value(),
            'samplerate': samplerate,
            'channels': channels,
            'server_type': server_type,
            'host': self._host_edit.text().strip(),
            'port': self._port_spin.value(),
            'mount': self._mount_edit.text().strip() or '/live',
            'username': self._username_edit.text().strip() or 'source',
            'password': self._password_edit.text(),
            'name': self._name_edit.text().strip() or 'RadioSAT XP',
            'genre': self._genre_edit.text().strip() or 'Various',
            'description': self._desc_edit.text().strip(),
            'loopback_device': loopback_dev,
            'loopback_device_name': self._loopback_combo.currentText(),
        }


# ══════════════════════════════════════════════════════════════════════════════
#  VENTANA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Radio XP Automator  —  Automatización de emisoras filiales")
        self.resize(1680, 910)
        self.setMinimumSize(1280, 720)
        app_icon_path = resource_path(os.path.join("assets", "icon.png"))
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))
        else:
            px = xp_pixmap("AudioDevices.png", 32)
            if not px.isNull():
                self.setWindowIcon(QIcon(px))

        # ── Motores ────────────────────────────────────────────────────────
        self.engine  = AudioEngine(self)
        self.dtmf    = DTMFDetector(self)
        self.passthrough = AudioPassthrough(self)
        self.remote_engine = RemoteStreamEngine(self)
        self.remote_dtmf   = StreamDTMFDetector(self)
        self.loopback = AudioLoopbackCapture(self)
        self.encoder = StreamEncoder(self)
        self.stream_client = StreamClient(self)
        self._tts_worker: TTSWorker | None = None
        self._dtmf_activating = False
        self._remote_dtmf_active = False
        self._remote_resume_pending = False
        self._remote_resume_url: str | None = None
        self._remote_break_active = False
        self._remote_break_start_seq = ""
        self._remote_break_return_seq = ""
        self._main_signal_monitoring_for_pauta = False
        self._encoder_on = False
        self._encoder_settings: dict = {}

        # ── Variables de estado ────────────────────────────────────────────
        self._dtmf_log: list[str]  = []
        self._dtmf_seq_progress: dict[str, int] = {}
        self._dtmf_cooldown_until: float = 0.0
        self._last_digit_time: float = 0.0
        self._seeking  = False
        self._mic_on   = False
        self._dtmf_on  = False
        self._signal_on = False
        self._pauta_on  = False
        self._remote_on = False
        self._main_signal_url: str | None = None
        self._was_playing_before_signal = False

        # ── Conectar señales del motor ─────────────────────────────────────
        self.engine.track_changed.connect(self._on_track_changed)
        self.engine.playback_state.connect(self._on_playback_state)
        self.engine.position_tick.connect(self._on_position_tick)
        self.engine.level_update.connect(self._on_engine_level)
        self.engine.error_signal.connect(self._show_error)
        self.engine.sequence_finished.connect(self._on_pauta_sequence_finished)

        self.dtmf.digit_detected.connect(self._on_dtmf_digit)
        self.dtmf.level_update.connect(self._on_dtmf_level)
        self.dtmf.status_update.connect(self._on_dtmf_status)
        
        self.passthrough.level_update.connect(self._on_passthrough_level)
        
        # Connect metadata update
        self.engine.metadata_update.connect(self._on_metadata_update)

        # ── Señales del stream remoto ─────────────────────────────────────
        self.remote_engine.state_changed.connect(self._on_remote_state)
        self.remote_engine.metadata_update.connect(self._on_remote_metadata)
        self.remote_dtmf.action_detected.connect(self._remote_dtmf_action)
        self.remote_dtmf.level_update.connect(self._on_remote_level)

        # ── Señales del encoder ───────────────────────────────────────────
        self.loopback.audio_data.connect(self._on_loopback_audio)
        self.loopback.error_signal.connect(self._on_loopback_error)
        self.encoder.encoded_data.connect(self._on_encoded_data)
        self.encoder.error_signal.connect(self._on_encoder_error)
        self.encoder.status_signal.connect(self._on_encoder_status)
        self.stream_client.connected.connect(self._on_stream_connected)
        self.stream_client.disconnected.connect(self._on_stream_disconnected)
        self.stream_client.error_signal.connect(self._on_stream_error)
        self.stream_client.status_signal.connect(self._on_stream_status)
        self.stream_client.bytes_sent.connect(self._on_stream_bytes)

        print("[INIT] Señales DTMF conectadas correctamente")
        print("[INIT] Señales de botones conectadas correctamente")

        # ── UI ─────────────────────────────────────────────────────────────
        self._ensure_status_contract()
        self._setup_menus()
        self._setup_ui()
        self._setup_statusbar()

        # ── Cargar datos persistidos ─────────────────────────────────────
        self._load_library_from_disk()
        self._load_pautas_from_disk()
        self._load_remotes_from_disk()
        self._load_playlist_from_disk()
        self._load_encoder_settings()
        self._load_settings_from_disk()
        self._sync_dashboard()

        # ── Timer VU demo (cuando no hay audio real) ───────────────────────
        self._demo_vu = QTimer(self)
        self._demo_vu.timeout.connect(self._demo_vu_tick)
        # Los medidores sólo representan telemetría real. Se conserva el timer
        # para compatibilidad, pero no se arranca una animación de demostración.

    def _on_metadata_update(self, meta_text: str):
        if meta_text:
            self._wave.set_metadata(f"♪ STREAMING: {meta_text}  •  RadioSAT XP")
        else:
            self._wave.set_metadata("♪ STREAMING...")

    # ═══════════════════════════════════════════════════
    #  MENÚS Y TOOLBAR
    # ═══════════════════════════════════════════════════
    def _setup_menus(self):
        mb = self.menuBar()

        # ── Archivo ──
        m_arch = mb.addMenu("&Archivo")
        m_arch.addAction(xp_icon("NewFolder.png"), "&Nuevo Proyecto",  self._new_project)
        m_arch.addAction(xp_icon("Open.png"),      "&Abrir Proyecto…", self._open_project)
        m_arch.addAction(xp_icon("Save.png"),      "&Guardar Proyecto", self._save_project)
        m_arch.addSeparator()
        m_arch.addAction("&Salir", self.close)

        # ── Biblioteca ──
        m_bib = mb.addMenu("&Biblioteca")
        m_bib.addAction(xp_icon("Add.png"),   "Añadir archivos de audio…", self._add_audio_files)
        m_bib.addAction(xp_icon("Open.png"),  "Importar carpeta…",          self._import_folder)
        m_bib.addAction(xp_icon("Delete.png"),"Limpiar biblioteca",          self._clear_library)

        # ── Config ──
        m_cfg = mb.addMenu("&Configuración")
        m_cfg.addAction(xp_icon("AudioDevices.png"), "Dispositivos de Audio…",
                        self._config_audio)
        m_cfg.addAction(xp_icon("Chip.png"), "Configurar Encoder…",
                        self._config_encoder)
        m_cfg.addSeparator()
        self._theme_action = m_cfg.addAction("Tema Oscuro")
        self._theme_action.setCheckable(True)
        self._theme_action.setChecked(True)
        self._theme_action.triggered.connect(self._toggle_theme)
        m_cfg.addAction(xp_icon("ControlPanel.png"), "Preferencias…",
                        lambda: QMessageBox.information(self, "Preferencias",
                                                        "Próximamente…"))

        # ── Ayuda ──
        m_help = mb.addMenu("A&yuda")
        m_help.addAction(xp_icon("Alert.png"), "Acerca de RadioXP…", self._about)

        # ── ToolBar ──
        tb: QToolBar = self.addToolBar("Herramientas")
        tb.setIconSize(QSize(24, 24))
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        def ta(icon, lbl, fn, tip=""):
            a = tb.addAction(xp_icon(icon), lbl)
            a.triggered.connect(fn)
            a.setToolTip(tip or lbl)

        ta("Add.png",       "Añadir",   self._add_audio_files,  "Añadir archivos de audio a la biblioteca")
        ta("Open.png",      "Abrir",    self._open_project,     "Abrir proyecto existente")
        ta("Save.png",      "Guardar",  self._save_project,     "Guardar proyecto actual")
        ta("Delete.png",    "Eliminar", self._delete_selected,  "Eliminar elemento seleccionado")
        tb.addSeparator()
        ta("Chip.png",      "DTMF",     self._toggle_dtmf_panel,"Panel de detección DTMF")
        ta("Playlist.png",  "Playlist", lambda: None,           "Gestionar playlist")
        ta("MyMusic.png",   "Biblioteca",lambda: None,          "Biblioteca de medios")

    # ═══════════════════════════════════════════════════
    #  UI PRINCIPAL - REDISEÑO
    # ═══════════════════════════════════════════════════
    def _setup_ui(self):
        if hasattr(self, "_dashboard_timer"):
            self._dashboard_timer.stop()
            self._dashboard_timer.deleteLater()
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header superior ──
        header = self._build_header()
        main_layout.addWidget(header)

        # ── Contenido principal con navegación lateral ──
        content_wrapper = QWidget()
        content_layout = QHBoxLayout(content_wrapper)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Navegación lateral
        nav = self._build_navigation()
        content_layout.addWidget(nav)

        # Área de páginas
        self._content_area = QStackedWidget()
        content_layout.addWidget(self._content_area, 1)

        main_layout.addWidget(content_wrapper, 1)

        # ── Barra de estado inferior ──
        statusbar = self._build_statusbar_bottom()
        main_layout.addWidget(statusbar)

        # ── Crear páginas ──
        self._page_emision = self._build_emision_page()
        self._page_pautas = self._build_pautas_page()
        self._page_biblioteca = self._build_biblioteca_page()
        self._page_dtmf = self._build_dtmf_page()
        self._page_registro = self._build_registro_page()
        self._page_dispositivos = self._build_dispositivos_page()

        self._content_area.addWidget(self._page_emision)
        self._content_area.addWidget(self._page_pautas)
        self._content_area.addWidget(self._page_biblioteca)
        self._content_area.addWidget(self._page_dtmf)
        self._content_area.addWidget(self._page_registro)
        self._content_area.addWidget(self._page_dispositivos)
        self._content_area.setCurrentIndex(0)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(64)
        header.setStyleSheet(f"""
            QWidget {{
                background: {T('surface')};
                border-bottom: 1px solid {T('border')};
            }}
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(20)

        # Logo y título
        logo_row = QHBoxLayout()
        logo_row.setSpacing(12)
        px_logo = xp_pixmap("AudioDevices.png", 36)
        lbl_logo = QLabel()
        if not px_logo.isNull():
            lbl_logo.setPixmap(px_logo)
        logo_row.addWidget(lbl_logo)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_title = QLabel("RADIO LOCAL")
        lbl_title.setStyleSheet(f"""
            font-size: 18pt;
            font-weight: bold;
            color: {T('text_primary')};
        """)
        title_col.addWidget(lbl_title)
        lbl_subtitle = QLabel("Control de emisión")
        lbl_subtitle.setStyleSheet(f"""
            font-size: 9pt;
            color: {T('text_secondary')};
        """)
        title_col.addWidget(lbl_subtitle)
        logo_row.addLayout(title_col)
        layout.addLayout(logo_row)

        layout.addStretch()

        # Botón AUTOMÁTICO
        btn_auto = QPushButton("▶ AUTOMÁTICO")
        btn_auto.setStyleSheet(f"""
            QPushButton {{
                background: {T('success')};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 10pt;
            }}
        """)
        layout.addWidget(btn_auto)

        # Indicador DTMF
        dtmf_row = QHBoxLayout()
        dtmf_row.setSpacing(8)
        led_dtmf = LEDIndicator(QColor(57, 221, 105))
        led_dtmf.set_on(True)
        dtmf_row.addWidget(led_dtmf)
        lbl_dtmf = QLabel("DTMF activo")
        lbl_dtmf.setStyleSheet(f"color: {T('text_primary')}; font-size: 10pt;")
        dtmf_row.addWidget(lbl_dtmf)
        layout.addLayout(dtmf_row)

        # Indicador Streaming
        stream_row = QHBoxLayout()
        stream_row.setSpacing(8)
        led_stream = LEDIndicator(QColor(57, 221, 105))
        led_stream.set_on(True)
        stream_row.addWidget(led_stream)
        lbl_stream = QLabel("Streaming conectado")
        lbl_stream.setStyleSheet(f"color: {T('text_primary')}; font-size: 10pt;")
        stream_row.addWidget(lbl_stream)
        layout.addLayout(stream_row)

        # Reloj
        clock_col = QVBoxLayout()
        clock_col.setSpacing(2)
        clock_col.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._header_clock = LiveClock()
        self._header_clock.setFixedHeight(40)
        clock_col.addWidget(self._header_clock)
        self._header_date = QLabel()
        self._header_date.setStyleSheet(f"color: {T('text_secondary')}; font-size: 9pt;")
        self._header_date.setAlignment(Qt.AlignmentFlag.AlignRight)
        clock_col.addWidget(self._header_date)
        layout.addLayout(clock_col)

        return header

    def _build_navigation(self) -> QWidget:
        nav = QWidget()
        nav.setFixedWidth(200)
        nav.setStyleSheet(f"""
            QWidget {{
                background: {T('bg_primary')};
                border-right: 1px solid {T('border')};
            }}
        """)
        layout = QVBoxLayout(nav)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(4)

        nav_items = [
            ("Emisión", "AudioCD.png", 0),
            ("Pautas locales", "Pauta.png", 1),
            ("Biblioteca", "MyMusic.png", 2),
            ("Reglas DTMF", "Chip.png", 3),
            ("Registro", "Alert.png", 4),
            ("Dispositivos", "AudioDevices.png", 5),
        ]

        self._nav_buttons = []
        for text, icon, idx in nav_items:
            btn = QPushButton()
            px = xp_pixmap(icon, 20)
            if not px.isNull():
                btn.setIcon(QIcon(px))
                btn.setIconSize(QSize(20, 20))
            btn.setText(f"  {text}")
            btn.setCheckable(True)
            btn.setFixedHeight(44)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    text-align: left;
                    padding-left: 20px;
                    font-size: 11pt;
                    color: {T('text_secondary')};
                }}
                QPushButton:hover {{
                    background: {T('bg_hover')};
                    color: {T('text_primary')};
                }}
                QPushButton:checked {{
                    background: {T('accent')};
                    color: white;
                    font-weight: bold;
                }}
            """)
            btn.clicked.connect(lambda checked, i=idx: self._navigate_to(i))
            layout.addWidget(btn)
            self._nav_buttons.append(btn)

        if self._nav_buttons:
            self._nav_buttons[0].setChecked(True)

        layout.addStretch()
        return nav

    def _navigate_to(self, index: int):
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)
        self._content_area.setCurrentIndex(index)

    def _build_emision_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ── Fila superior: Banner AL AIRE + Reloj próximo evento ──
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # Banner AL AIRE
        banner = QWidget()
        banner.setStyleSheet(f"""
            QWidget {{
                background: {T('success')};
                border-radius: 6px;
            }}
        """)
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(20, 16, 20, 16)
        banner_layout.setSpacing(16)

        px_antenna = xp_pixmap("AudioDevices.png", 48)
        lbl_antenna = QLabel()
        if not px_antenna.isNull():
            lbl_antenna.setPixmap(px_antenna)
        banner_layout.addWidget(lbl_antenna)

        banner_info = QVBoxLayout()
        banner_info.setSpacing(4)
        lbl_banner_title = QLabel("AL AIRE · SEÑAL DE CADENA")
        lbl_banner_title.setStyleSheet("""
            font-size: 16pt;
            font-weight: bold;
            color: white;
        """)
        banner_info.addWidget(lbl_banner_title)
        lbl_banner_source = QLabel("Fuente: Cadena principal")
        lbl_banner_source.setStyleSheet("""
            font-size: 10pt;
            color: rgba(255,255,255,0.9);
        """)
        banner_info.addWidget(lbl_banner_source)
        lbl_banner_desc = QLabel("La señal de cadena se transmite a la audiencia")
        lbl_banner_desc.setStyleSheet("""
            font-size: 9pt;
            color: rgba(255,255,255,0.8);
        """)
        banner_info.addWidget(lbl_banner_desc)
        banner_layout.addLayout(banner_info, 1)

        # Medidores VU en el banner
        vu_widget = QWidget()
        vu_widget.setFixedWidth(280)
        vu_layout = QVBoxLayout(vu_widget)
        vu_layout.setContentsMargins(0, 0, 0, 0)
        vu_layout.setSpacing(6)

        self._vu_bars = []
        for label in ["L", "R"]:
            vu_row = QHBoxLayout()
            vu_row.setSpacing(8)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: white; font-size: 10pt; font-weight: bold;")
            lbl.setFixedWidth(12)
            vu_row.addWidget(lbl)
            vu_bar = VUBar()
            vu_row.addWidget(vu_bar, 1)
            vu_layout.addLayout(vu_row)
            self._vu_bars.append(vu_bar)

        # Escala dB
        db_row = QHBoxLayout()
        db_row.setSpacing(0)
        for db in ["-60", "-40", "-20", "-10", "-6", "-3", "0 dB"]:
            lbl = QLabel(db)
            lbl.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 7pt;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            db_row.addWidget(lbl, 1)
        vu_layout.addLayout(db_row)
        banner_layout.addWidget(vu_widget)

        top_row.addWidget(banner, 68)

        # Panel próximo evento
        next_panel = QWidget()
        next_panel.setStyleSheet(f"""
            QWidget {{
                background: {T('surface')};
                border: 1px solid {T('border')};
                border-radius: 6px;
            }}
        """)
        next_layout = QHBoxLayout(next_panel)
        next_layout.setContentsMargins(16, 12, 16, 12)
        next_layout.setSpacing(16)

        px_clock = xp_pixmap("Alert.png", 32)
        lbl_clock_icon = QLabel()
        if not px_clock.isNull():
            lbl_clock_icon.setPixmap(px_clock)
        next_layout.addWidget(lbl_clock_icon)

        next_info = QVBoxLayout()
        next_info.setSpacing(4)
        lbl_next_title = QLabel("Próxima desconexión")
        lbl_next_title.setStyleSheet(f"color: {T('warning')}; font-size: 10pt;")
        next_info.addWidget(lbl_next_title)
        self._lbl_next_time = QLabel("17:30:00")
        self._lbl_next_time.setStyleSheet(f"""
            font-size: 22pt;
            font-weight: bold;
            color: {T('warning')};
        """)
        next_info.addWidget(self._lbl_next_time)
        next_layout.addLayout(next_info, 1)

        next_countdown = QVBoxLayout()
        next_countdown.setSpacing(4)
        next_countdown.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_en = QLabel("En")
        lbl_en.setStyleSheet(f"color: {T('text_secondary')}; font-size: 9pt;")
        lbl_en.setAlignment(Qt.AlignmentFlag.AlignRight)
        next_countdown.addWidget(lbl_en)
        self._lbl_countdown = QLabel("00:32")
        self._lbl_countdown.setStyleSheet(f"""
            font-size: 22pt;
            font-weight: bold;
            color: {T('warning')};
        """)
        self._lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignRight)
        next_countdown.addWidget(self._lbl_countdown)
        next_layout.addLayout(next_countdown)

        top_row.addWidget(next_panel, 32)
        layout.addLayout(top_row)

        # ── Contenido principal dos columnas ──
        main_content = QHBoxLayout()
        main_content.setSpacing(16)

        # Columna izquierda (68%)
        left_col = QVBoxLayout()
        left_col.setSpacing(16)

        # Pauta local
        pauta_panel = self._build_pauta_panel()
        left_col.addWidget(pauta_panel)

        # Biblioteca
        bib_panel = self._build_biblioteca_inline()
        left_col.addWidget(bib_panel)

        left_col.setStretch(0, 1)
        left_col.setStretch(1, 1)
        main_content.addLayout(left_col, 68)

        # Columna derecha (32%)
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        # Control DTMF
        dtmf_panel = self._build_dtmf_panel()
        right_col.addWidget(dtmf_panel)

        # Salida y respaldo
        output_panel = self._build_output_panel()
        right_col.addWidget(output_panel)

        # Registro
        log_panel = self._build_log_panel()
        right_col.addWidget(log_panel)

        right_col.setStretch(0, 0)
        right_col.setStretch(1, 0)
        right_col.setStretch(2, 1)
        main_content.addLayout(right_col, 32)

        layout.addLayout(main_content, 1)
        return page

    def _build_pauta_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"""
            QWidget {{
                background: {T('surface')};
                border: 1px solid {T('border')};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        px_pauta = xp_pixmap("Pauta.png", 24)
        lbl_icon = QLabel()
        if not px_pauta.isNull():
            lbl_icon.setPixmap(px_pauta)
        header.addWidget(lbl_icon)

        pauta_info = QVBoxLayout()
        pauta_info.setSpacing(2)
        lbl_title = QLabel("Pauta local preparada")
        lbl_title.setStyleSheet(f"""
            font-size: 12pt;
            font-weight: bold;
            color: {T('accent_text')};
        """)
        pauta_info.addWidget(lbl_title)
        lbl_subtitle = QLabel("Tanda 17:30 · 4 audios · Total 02:00")
        lbl_subtitle.setStyleSheet(f"color: {T('text_secondary')}; font-size: 9pt;")
        pauta_info.addWidget(lbl_subtitle)
        header.addLayout(pauta_info, 1)
        layout.addLayout(header)

        # Tabla de pauta
        self._pauta_table = QTableWidget()
        self._pauta_table.setColumnCount(5)
        self._pauta_table.setHorizontalHeaderLabels(["Orden", "Audio / Cliente", "Duración", "Inicio", "Estado"])
        self._pauta_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._pauta_table.setAlternatingRowColors(True)
        self._pauta_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._pauta_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._pauta_table.verticalHeader().setVisible(False)
        layout.addWidget(self._pauta_table)

        # Línea de tiempo
        timeline_label = QLabel("Línea de tiempo de la pauta (02:00)")
        timeline_label.setStyleSheet(f"color: {T('text_secondary')}; font-size: 9pt;")
        layout.addWidget(timeline_label)

        timeline = QWidget()
        timeline.setFixedHeight(24)
        timeline.setStyleSheet(f"background: {T('bg_input')}; border-radius: 4px;")
        tl_layout = QHBoxLayout(timeline)
        tl_layout.setContentsMargins(0, 0, 0, 0)
        tl_layout.setSpacing(2)

        colors = [T('accent'), T('success'), T('warning'), "#9B59B6"]
        durations = ["00:10", "00:30", "00:40", "00:40"]
        for color, dur in zip(colors, durations):
            seg = QWidget()
            seg.setStyleSheet(f"background: {color}; border-radius: 2px;")
            tl_layout.addWidget(seg, int(dur.split(':')[1]))
        layout.addWidget(timeline)

        # Labels de timeline
        tl_labels = QHBoxLayout()
        tl_labels.setSpacing(0)
        labels = ["Identificación emisora", "Ferretería del Puerto", "Mercado Central", "Promoción local"]
        for lbl_text in labels:
            lbl = QLabel(lbl_text)
            lbl.setStyleSheet(f"color: {T('text_secondary')}; font-size: 8pt;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            tl_labels.addWidget(lbl, 1)
        layout.addLayout(tl_labels)

        # Info DTMF
        lbl_dtmf_info = QLabel("Inicio por DTMF · Retorno automático al finalizar")
        lbl_dtmf_info.setStyleSheet(f"color: {T('text_secondary')}; font-size: 9pt; margin-top: 8px;")
        layout.addWidget(lbl_dtmf_info)

        # Botones de acción
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_emitir = QPushButton("▶ Emitir pauta local")
        btn_emitir.setStyleSheet(f"""
            QPushButton {{
                background: {T('success')};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background: #2BBF55;
            }}
        """)
        btn_emitir.clicked.connect(self._toggle_pauta)
        btn_row.addWidget(btn_emitir)

        btn_cadena = QPushButton("⏹ Volver a cadena")
        btn_cadena.setStyleSheet(f"""
            QPushButton {{
                background: {T('surface_raised')};
                color: {T('text_primary')};
                border: 1px solid {T('border')};
                border-radius: 4px;
                padding: 12px 24px;
                font-size: 10pt;
            }}
        """)
        btn_cadena.clicked.connect(self._toggle_signal)
        btn_row.addWidget(btn_cadena)

        btn_row.addStretch()

        btn_preescuchar = QPushButton("🎧 Preescuchar")
        btn_preescuchar.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {T('text_secondary')};
                border: 1px solid {T('border')};
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 9pt;
            }}
        """)
        btn_preescuchar.clicked.connect(self._toggle_mic)
        btn_row.addWidget(btn_preescuchar)

        layout.addLayout(btn_row)
        return panel

    def _build_biblioteca_inline(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"""
            QWidget {{
                background: {T('surface')};
                border: 1px solid {T('border')};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        px_bib = xp_pixmap("MyMusic.png", 24)
        lbl_icon = QLabel()
        if not px_bib.isNull():
            lbl_icon.setPixmap(px_bib)
        header.addWidget(lbl_icon)

        lbl_title = QLabel("Biblioteca de medios")
        lbl_title.setStyleSheet(f"""
            font-size: 12pt;
            font-weight: bold;
            color: {T('accent_text')};
        """)
        header.addWidget(lbl_title)
        header.addStretch()
        layout.addLayout(header)

        # Búsqueda y filtros
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        search_edit = QLineEdit()
        search_edit.setPlaceholderText("Buscar audio, cliente o campaña...")
        search_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {T('bg_input')};
                color: {T('text_primary')};
                border: 1px solid {T('border')};
                border-radius: 4px;
                padding: 6px 12px;
            }}
        """)
        search_row.addWidget(search_edit, 1)

        filter_combo = QComboBox()
        filter_combo.addItems(["Todos", "Comerciales", "Identificaciones", "Música"])
        search_row.addWidget(filter_combo)

        btn_import = QPushButton("↑ Importar audios")
        btn_import.setStyleSheet(f"""
            QPushButton {{
                background: {T('accent')};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 9pt;
            }}
        """)
        btn_import.clicked.connect(self._add_audio_files)
        search_row.addWidget(btn_import)

        layout.addLayout(search_row)

        # Tabla de biblioteca
        self._table_library = QTableWidget()
        self._table_library.setColumnCount(5)
        self._table_library.setHorizontalHeaderLabels(["Nombre del archivo", "Duración", "Cliente / Campaña", "Categoría", "Acción"])
        self._table_library.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table_library.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table_library.setAlternatingRowColors(True)
        self._table_library.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table_library.verticalHeader().setVisible(False)
        layout.addWidget(self._table_library, 1)

        return panel

    def _build_dtmf_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"""
            QWidget {{
                background: {T('surface')};
                border: 1px solid {T('border')};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        px_dtmf = xp_pixmap("Chip.png", 20)
        lbl_icon = QLabel()
        if not px_dtmf.isNull():
            lbl_icon.setPixmap(px_dtmf)
        header.addWidget(lbl_icon)

        lbl_title = QLabel("Control DTMF")
        lbl_title.setStyleSheet(f"""
            font-size: 11pt;
            font-weight: bold;
            color: {T('accent_text')};
        """)
        header.addWidget(lbl_title)
        layout.addLayout(header)

        # Estado
        status_row = QHBoxLayout()
        led_dtmf = LEDIndicator(QColor(57, 221, 105))
        led_dtmf.set_on(True)
        status_row.addWidget(led_dtmf)
        self._lbl_dtmf_status = QLabel("Escuchando entrada de cadena")
        self._lbl_dtmf_status.setStyleSheet(f"""
            color: {T('success')};
            font-size: 10pt;
            font-weight: bold;
        """)
        status_row.addWidget(self._lbl_dtmf_status, 1)
        layout.addLayout(status_row)

        # Último código
        lbl_last = QLabel("Último código:")
        lbl_last.setStyleSheet(f"color: {T('text_secondary')}; font-size: 9pt;")
        layout.addWidget(lbl_last)

        self._lbl_last_code = QLabel("*90# · 17:00:00")
        self._lbl_last_code.setStyleSheet(f"""
            background: {T('bg_input')};
            color: {T('text_primary')};
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 10pt;
        """)
        layout.addWidget(self._lbl_last_code)

        # Tabla de códigos
        code_table = QTableWidget()
        code_table.setColumnCount(2)
        code_table.setHorizontalHeaderLabels(["Código DTMF", "Acción"])
        code_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        code_table.setRowCount(2)
        code_table.setItem(0, 0, QTableWidgetItem("*90#"))
        code_table.setItem(0, 1, QTableWidgetItem("Iniciar pauta local"))
        code_table.setItem(1, 0, QTableWidgetItem("*91#"))
        code_table.setItem(1, 1, QTableWidgetItem("Volver a cadena"))
        code_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        code_table.verticalHeader().setVisible(False)
        layout.addWidget(code_table)

        # Nota informativa
        info_row = QHBoxLayout()
        px_info = xp_pixmap("Alert.png", 16)
        lbl_info_icon = QLabel()
        if not px_info.isNull():
            lbl_info_icon.setPixmap(px_info)
        info_row.addWidget(lbl_info_icon)
        lbl_info = QLabel("La cadena continúa al aire hasta recibir el tono de corte.")
        lbl_info.setStyleSheet(f"color: {T('text_secondary')}; font-size: 9pt;")
        info_row.addWidget(lbl_info, 1)
        layout.addLayout(info_row)

        return panel

    def _build_output_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"""
            QWidget {{
                background: {T('surface')};
                border: 1px solid {T('border')};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        px_output = xp_pixmap("AudioDevices.png", 20)
        lbl_icon = QLabel()
        if not px_output.isNull():
            lbl_icon.setPixmap(px_output)
        header.addWidget(lbl_icon)

        lbl_title = QLabel("Salida y respaldo")
        lbl_title.setStyleSheet(f"""
            font-size: 11pt;
            font-weight: bold;
            color: {T('accent_text')};
        """)
        header.addWidget(lbl_title)
        layout.addLayout(header)

        # Programa (salida al aire)
        lbl_program = QLabel("Programa (salida al aire)")
        lbl_program.setStyleSheet(f"color: {T('text_secondary')}; font-size: 9pt;")
        layout.addWidget(lbl_program)

        # Medidores pequeños
        vu_widget = QWidget()
        vu_widget.setFixedHeight(50)
        vu_layout = QVBoxLayout(vu_widget)
        vu_layout.setContentsMargins(0, 0, 0, 0)
        vu_layout.setSpacing(4)

        self._vu_output = []
        for label in ["L", "R"]:
            vu_row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {T('text_secondary')}; font-size: 8pt;")
            lbl.setFixedWidth(10)
            vu_row.addWidget(lbl)
            vu_bar = VUBar()
            vu_row.addWidget(vu_bar, 1)
            vu_layout.addLayout(vu_row)
            self._vu_output.append(vu_bar)

        db_row = QHBoxLayout()
        for db in ["-60", "-40", "-20", "-10", "-6", "-3", "0 dB"]:
            lbl = QLabel(db)
            lbl.setStyleSheet(f"color: {T('text_dim')}; font-size: 6pt;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            db_row.addWidget(lbl, 1)
        vu_layout.addLayout(db_row)
        layout.addWidget(vu_widget)

        # Encoder
        encoder_row = QHBoxLayout()
        led_encoder = LEDIndicator(QColor(57, 221, 105))
        led_encoder.set_on(True)
        encoder_row.addWidget(led_encoder)

        encoder_info = QVBoxLayout()
        encoder_info.setSpacing(2)
        lbl_encoder_title = QLabel("Encoder")
        lbl_encoder_title.setStyleSheet(f"color: {T('text_primary')}; font-size: 10pt; font-weight: bold;")
        encoder_info.addWidget(lbl_encoder_title)
        self._lbl_encoder_status = QLabel("Conectado")
        self._lbl_encoder_status.setStyleSheet(f"color: {T('success')}; font-size: 9pt;")
        encoder_info.addWidget(self._lbl_encoder_status)
        encoder_row.addLayout(encoder_info, 1)

        self._lbl_encoder_codec = QLabel("MP3 · 128 kbps")
        self._lbl_encoder_codec.setStyleSheet(f"color: {T('text_secondary')}; font-size: 9pt;")
        encoder_row.addWidget(self._lbl_encoder_codec)
        layout.addLayout(encoder_row)

        # Audio de respaldo
        backup_row = QHBoxLayout()
        led_backup = LEDIndicator(QColor(57, 221, 105))
        led_backup.set_on(True)
        backup_row.addWidget(led_backup)

        backup_info = QVBoxLayout()
        backup_info.setSpacing(2)
        lbl_backup_title = QLabel("Audio de respaldo")
        lbl_backup_title.setStyleSheet(f"color: {T('text_primary')}; font-size: 10pt;")
        backup_info.addWidget(lbl_backup_title)
        lbl_backup_status = QLabel("Listo · respaldo_emisora.mp3")
        lbl_backup_status.setStyleSheet(f"color: {T('success')}; font-size: 9pt;")
        backup_info.addWidget(lbl_backup_status)
        backup_row.addLayout(backup_info, 1)
        layout.addLayout(backup_row)

        # Botón configurar
        btn_config = QPushButton("⚙ Configurar audio")
        btn_config.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {T('text_secondary')};
                border: 1px solid {T('border')};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 9pt;
            }}
        """)
        btn_config.clicked.connect(self._config_encoder)
        layout.addWidget(btn_config)

        return panel

    def _build_log_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"""
            QWidget {{
                background: {T('surface')};
                border: 1px solid {T('border')};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        px_log = xp_pixmap("Alert.png", 20)
        lbl_icon = QLabel()
        if not px_log.isNull():
            lbl_icon.setPixmap(px_log)
        header.addWidget(lbl_icon)

        lbl_title = QLabel("Registro de emisión")
        lbl_title.setStyleSheet(f"""
            font-size: 11pt;
            font-weight: bold;
            color: {T('accent_text')};
        """)
        header.addWidget(lbl_title)
        header.addStretch()

        btn_clear = QPushButton(" Limpiar")
        btn_clear.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {T('text_secondary')};
                border: none;
                font-size: 9pt;
            }}
        """)
        btn_clear.clicked.connect(self._clear_log_view)
        header.addWidget(btn_clear)
        layout.addLayout(header)

        # Tabla de registro
        self._log_table = QTableWidget()
        self._log_table.setColumnCount(2)
        self._log_table.setHorizontalHeaderLabels(["Hora", "Evento"])
        self._log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._log_table.setAlternatingRowColors(True)
        self._log_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._log_table.verticalHeader().setVisible(False)
        layout.addWidget(self._log_table, 1)

        return panel

    def _build_statusbar_bottom(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(32)
        bar.setStyleSheet(f"""
            QWidget {{
                background: {T('surface')};
                border-top: 1px solid {T('border')};
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        items = [
            ("Entrada: USB Audio 1/2", T('success')),
            ("Salida: Programa 1/2", T('success')),
            ("Monitoreo: 3/4", T('text_secondary')),
        ]

        for text, color in items:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {color}; font-size: 9pt;")
            layout.addWidget(lbl)

        layout.addStretch()

        lbl_backup = QLabel("Respaldo listo")
        lbl_backup.setStyleSheet(f"color: {T('success')}; font-size: 9pt;")
        layout.addWidget(lbl_backup)

        lbl_version = QLabel("Radio XP Automator v1.6.0")
        lbl_version.setStyleSheet(f"color: {T('text_dim')}; font-size: 9pt;")
        layout.addWidget(lbl_version)

        return bar

    def _build_pautas_page(self) -> QWidget:
        return self._build_emision_page()

    def _build_biblioteca_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)

        bib_panel = self._build_biblioteca_inline()
        layout.addWidget(bib_panel, 1)
        return page

    def _build_dtmf_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)

        dtmf_panel = self._build_dtmf_panel()
        layout.addWidget(dtmf_panel)
        layout.addStretch()
        return page

    def _build_registro_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)

        log_panel = self._build_log_panel()
        layout.addWidget(log_panel, 1)
        return page

    def _build_dispositivos_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        lbl_title = QLabel("DISPOSITIVOS DE AUDIO")
        lbl_title.setStyleSheet(f"""
            font-size: 14pt;
            font-weight: bold;
            color: {T('text_primary')};
        """)
        layout.addWidget(lbl_title)

        # Dispositivos de entrada
        grp_input = QGroupBox("Dispositivos de entrada")
        grp_input.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {T('border')};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
                font-weight: bold;
                color: {T('text_primary')};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
        """)
        input_layout = QGridLayout(grp_input)

        input_layout.addWidget(QLabel("Micrófono:"), 0, 0)
        self._mic_dev_combo = QComboBox()
        input_layout.addWidget(self._mic_dev_combo, 0, 1)

        input_layout.addWidget(QLabel("Entrada DTMF:"), 1, 0)
        self._dtmf_dev_combo = QComboBox()
        input_layout.addWidget(self._dtmf_dev_combo, 1, 1)

        layout.addWidget(grp_input)

        # Dispositivos de salida
        grp_output = QGroupBox("Dispositivos de salida")
        grp_output.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {T('border')};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
                font-weight: bold;
                color: {T('text_primary')};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
        """)
        output_layout = QGridLayout(grp_output)

        output_layout.addWidget(QLabel("Reproductor:"), 0, 0)
        self._out_dev_combo = QComboBox()
        self._out_dev_combo.currentIndexChanged.connect(self._on_out_dev_changed)
        output_layout.addWidget(self._out_dev_combo, 0, 1)

        output_layout.addWidget(QLabel("Señal principal:"), 1, 0)
        self._sd_out_dev_combo = QComboBox()
        output_layout.addWidget(self._sd_out_dev_combo, 1, 1)

        output_layout.addWidget(QLabel("Stream remoto:"), 2, 0)
        self._remote_out_dev_combo = QComboBox()
        self._remote_out_dev_combo.currentIndexChanged.connect(self._on_remote_out_dev_changed)
        output_layout.addWidget(self._remote_out_dev_combo, 2, 1)

        layout.addWidget(grp_output)

        # Botón actualizar
        btn_refresh = QPushButton("Actualizar dispositivos")
        btn_refresh.clicked.connect(self._refresh_devices)
        layout.addWidget(btn_refresh)

        layout.addStretch()
        return page

    def _clear_log_view(self):
        if hasattr(self, '_log_table'):
            self._log_table.setRowCount(0)

    # ─────────────────────── PANEL: CONSOLA ────────────────────────────────
    def _build_consola(self) -> XPPanel:
        p = XPPanel("Consola de Emisión", "DateandTime.png")
        lay = p.content_layout
        lay.setSpacing(5)

        # ── Fila 1: Reloj + LEDs ──
        top = QHBoxLayout()
        top.setSpacing(8)

        self._clock = LiveClock()
        self._clock.setFixedHeight(58)
        top.addWidget(self._clock, 1)

        self._led_onair  = LEDIndicator(QColor(255, 30,  30))
        self._led_signal = LEDIndicator(QColor(0,  210,  0))
        self._led_dtmf   = LEDIndicator(QColor(255, 180,  0))
        self._led_remote = LEDIndicator(QColor(100, 180, 255))
        self._led_encoder = LEDIndicator(QColor(255, 100, 200))

        led_wrap = QHBoxLayout()
        led_wrap.setSpacing(6)
        for led, txt in [(self._led_onair,"ON AIR"),(self._led_signal,"SEÑAL"),
                         (self._led_dtmf,"DTMF"),(self._led_remote,"REMOTO"),
                         (self._led_encoder,"STREAM")]:
            c = QVBoxLayout()
            c.setSpacing(1)
            c.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            l = QLabel(txt)
            l.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            l.setStyleSheet(f"font-size:6pt; font-weight:bold; color:{T('text_secondary')};")
            c.addWidget(led, 0, Qt.AlignmentFlag.AlignHCenter)
            c.addWidget(l, 0, Qt.AlignmentFlag.AlignHCenter)
            led_wrap.addLayout(c)
        top.addLayout(led_wrap)
        lay.addLayout(top)

        # ── Fila 2: Botones principales en grid 2x3 ──
        btn_grid = QGridLayout()
        btn_grid.setSpacing(4)

        def make_btn(text, icon_name, tip, slot):
            b = QPushButton(f"  {text}")
            px = xp_pixmap(icon_name, 18)
            if not px.isNull():
                b.setIcon(QIcon(px))
                b.setIconSize(QSize(18, 18))
            b.setCheckable(True)
            b.setFixedHeight(34)
            b.setFont(QFont("Helvetica Neue", 8, QFont.Weight.Bold))
            b.setToolTip(tip)
            b.toggled.connect(slot)
            return b

        self.btn_signal = make_btn("SEÑAL PRINCIPAL", "AudioCD.png",
            "Activa/desactiva la señal de emisión principal", self._toggle_signal)
        self.btn_pauta = make_btn("PAUTA LOCAL", "Pauta.png",
            "Inicia/detiene la reproducción de pauta local", self._toggle_pauta)
        self.btn_dtmf_main = make_btn("DETECTAR DTMF", "Chip.png",
            "Activa/desactiva la detección de tonos DTMF", self._toggle_dtmf)
        self.btn_remote = make_btn("SEÑAL REMOTA", "RemoteDesktop.png",
            "Reproduce un stream remoto y detecta DTMF", self._toggle_remote)
        self.btn_encoder = make_btn("ENCODER", "Record.png",
            "Inicia/detiene la transmisión del encoder (streaming)", self._toggle_encoder)

        btn_grid.addWidget(self.btn_signal,    0, 0)
        btn_grid.addWidget(self.btn_pauta,     0, 1)
        btn_grid.addWidget(self.btn_encoder,   0, 2)
        btn_grid.addWidget(self.btn_dtmf_main, 1, 0)
        btn_grid.addWidget(self.btn_remote,    1, 1)
        lay.addLayout(btn_grid)

        # ── Controles de Señal Remota (ocultos hasta activar) ──
        self._remote_controls = QWidget()
        rc = QVBoxLayout(self._remote_controls)
        rc.setContentsMargins(0, 0, 0, 0)
        rc.setSpacing(3)

        self._remote_url_edit = QLineEdit()
        self._remote_url_edit.setPlaceholderText("URL del stream...")
        self._remote_url_edit.setFixedHeight(24)
        rc.addWidget(self._remote_url_edit)

        ctrl = QHBoxLayout()
        self.btn_remote_play = QPushButton("  Play")
        pxp = xp_pixmap("Play.png", 12)
        if not pxp.isNull(): self.btn_remote_play.setIcon(QIcon(pxp))
        self.btn_remote_play.setFixedSize(60, 24)
        self.btn_remote_play.setIconSize(QSize(12, 12))
        self.btn_remote_play.clicked.connect(self._remote_play)
        ctrl.addWidget(self.btn_remote_play)

        self.btn_remote_stop = QPushButton("  Stop")
        pxs = xp_pixmap("Stop.png", 12)
        if not pxs.isNull(): self.btn_remote_stop.setIcon(QIcon(pxs))
        self.btn_remote_stop.setFixedSize(60, 24)
        self.btn_remote_stop.setIconSize(QSize(12, 12))
        self.btn_remote_stop.setEnabled(False)
        self.btn_remote_stop.clicked.connect(lambda: self._remote_stop(manual=True))
        ctrl.addWidget(self.btn_remote_stop)

        self._remote_vol = QSlider(Qt.Orientation.Horizontal)
        self._remote_vol.setRange(0, 100)
        self._remote_vol.setValue(80)
        self._remote_vol.setFixedWidth(50)
        self._remote_vol.valueChanged.connect(lambda v: self.remote_engine.set_volume(v / 100))
        ctrl.addWidget(QLabel("Vol:"))
        ctrl.addWidget(self._remote_vol)
        ctrl.addStretch()
        rc.addLayout(ctrl)

        self._lbl_remote_status = QLabel("Inactivo")
        self._lbl_remote_status.setStyleSheet(f"color:{T('text_dim')}; font-size:7pt;")
        rc.addWidget(self._lbl_remote_status)

        self._remote_controls.setVisible(False)
        lay.addWidget(self._remote_controls)

        # ── DTMF Display ──
        self._dtmf_display = QLineEdit()
        self._dtmf_display.setReadOnly(True)
        self._dtmf_display.setPlaceholderText("Dígitos DTMF...")
        self._dtmf_display.setFixedHeight(26)
        self._apply_dtmf_display_style()
        lay.addWidget(self._dtmf_display)

        # ── Limpiar + Estado ──
        bot = QHBoxLayout()
        btn_clr = QPushButton("  Limpiar")
        pxcl = xp_pixmap("Delete.png", 12)
        if not pxcl.isNull(): btn_clr.setIcon(QIcon(pxcl))
        btn_clr.setFixedSize(96, 30)
        btn_clr.setIconSize(QSize(12, 12))
        btn_clr.clicked.connect(lambda: (self._dtmf_log.clear(), self._dtmf_display.clear()))
        bot.addWidget(btn_clr)
        self._lbl_detector_status = QLabel("Inactivo")
        self._lbl_detector_status.setStyleSheet(f"color:{T('text_dim')}; font-size:7pt;")
        bot.addWidget(self._lbl_detector_status, 1)
        lay.addLayout(bot)

        lay.addStretch()
        return p

    # ─────────────────────── PANEL: DTMF ───────────────────────────────────
    def _build_dtmf(self) -> XPPanel:
        p = XPPanel("Configuración DTMF", "Chip.png")
        lay = p.content_layout

        tabs = QTabWidget()

        # Tab Dispositivos
        t1 = QWidget()
        g1 = QGridLayout(t1)
        g1.setSpacing(6)

        g1.addWidget(QLabel("Entrada (escucha tonos):"), 0, 0)
        self._dtmf_dev_combo = QComboBox()
        self._dtmf_dev_combo.setToolTip("Dispositivo de entrada para detección DTMF")
        g1.addWidget(self._dtmf_dev_combo, 0, 1)

        g1.addWidget(QLabel("Salida (Señal Principal):"), 1, 0)
        self._sd_out_dev_combo = QComboBox()
        self._sd_out_dev_combo.setToolTip("Dispositivo de salida para la señal principal (passthrough de audio en vivo)")
        g1.addWidget(self._sd_out_dev_combo, 1, 1)

        g1.addWidget(QLabel("Salida (Reproductor):"), 2, 0)
        self._out_dev_combo = QComboBox()
        self._out_dev_combo.setToolTip("Dispositivo de salida para el reproductor local")
        self._out_dev_combo.currentIndexChanged.connect(self._on_out_dev_changed)
        g1.addWidget(self._out_dev_combo, 2, 1)

        g1.addWidget(QLabel("Salida (Reproductor Remoto):"), 3, 0)
        self._remote_out_dev_combo = QComboBox()
        self._remote_out_dev_combo.setToolTip("Dispositivo de salida exclusivo para la señal remota")
        self._remote_out_dev_combo.currentIndexChanged.connect(self._on_remote_out_dev_changed)
        g1.addWidget(self._remote_out_dev_combo, 3, 1)

        btn_ref = QPushButton("  Actualizar")
        btn_ref.setIcon(xp_icon("Refresh.png"))
        btn_ref.setToolTip("Actualizar lista de dispositivos de audio")
        btn_ref.clicked.connect(self._refresh_devices)
        g1.addWidget(btn_ref, 4, 0, 1, 2)
        tabs.addTab(t1, "  Dispositivos")
        self._refresh_devices()

        # Tab Parámetros
        t2 = QWidget()
        g2 = QGridLayout(t2)
        g2.setSpacing(6)

        g2.addWidget(QLabel("Frecuencia Inicio (Hz):"), 0, 0)
        self._dtmf_freq_lo = QSpinBox(); self._dtmf_freq_lo.setRange(300,4000); self._dtmf_freq_lo.setValue(697)
        g2.addWidget(self._dtmf_freq_lo, 0, 1)

        g2.addWidget(QLabel("Frecuencia Fin (Hz):"), 1, 0)
        self._dtmf_freq_hi = QSpinBox(); self._dtmf_freq_hi.setRange(300,4000); self._dtmf_freq_hi.setValue(1633)
        g2.addWidget(self._dtmf_freq_hi, 1, 1)

        g2.addWidget(QLabel("Duración Mínima (ms):"), 2, 0)
        self._dtmf_dur = QSpinBox(); self._dtmf_dur.setRange(10,500); self._dtmf_dur.setValue(40)
        g2.addWidget(self._dtmf_dur, 2, 1)

        g2.addWidget(QLabel("Umbral Ruido (dB):"), 3, 0)
        self._dtmf_thresh = QDoubleSpinBox()
        self._dtmf_thresh.setRange(-80,0); self._dtmf_thresh.setValue(-30); self._dtmf_thresh.setSuffix(" dB")
        g2.addWidget(self._dtmf_thresh, 3, 1)

        g2.addWidget(QLabel("Tolerancia (±Hz):"), 4, 0)
        self._dtmf_tol = QSpinBox(); self._dtmf_tol.setRange(1,100); self._dtmf_tol.setValue(20)
        g2.addWidget(self._dtmf_tol, 4, 1)

        g2.addWidget(QLabel("DTMF Inicio (Play):"), 5, 0)
        self._dtmf_seq_play = QLineEdit("420590")
        g2.addWidget(self._dtmf_seq_play, 5, 1)

        g2.addWidget(QLabel("DTMF Fin (Stop):"), 6, 0)
        self._dtmf_seq_stop = QLineEdit("609700")
        g2.addWidget(self._dtmf_seq_stop, 6, 1)

        btn_apply = QPushButton(" Aplicar parámetros")
        btn_apply.setIcon(xp_icon("Apply.png"))
        btn_apply.setToolTip("Aplicar los parámetros de detección al motor DTMF")
        btn_apply.clicked.connect(self._apply_dtmf_params)
        g2.addWidget(btn_apply, 7, 0, 1, 2)
        tabs.addTab(t2, "  Parámetros")

        # Tab Prueba
        t3 = QWidget()
        v3 = QVBoxLayout(t3)
        v3.setSpacing(8)

        v3.addWidget(QLabel("Enviar tono de prueba DTMF:"))
        row3 = QHBoxLayout()
        self._test_tone_cb = QComboBox()
        for key, (r, c) in [
            ("1 (697/1209)", (697,1209)), ("2 (697/1336)", (697,1336)),
            ("3 (697/1477)", (697,1477)), ("4 (770/1209)", (770,1209)),
            ("5 (770/1336)", (770,1336)), ("6 (770/1477)", (770,1477)),
            ("7 (852/1209)", (852,1209)), ("8 (852/1336)", (852,1336)),
            ("9 (852/1477)", (852,1477)), ("* (941/1209)", (941,1209)),
            ("0 (941/1336)", (941,1336)), ("# (941/1477)", (941,1477)),
        ]:
            self._test_tone_cb.addItem(key, (r, c))
        row3.addWidget(self._test_tone_cb)
        btn_send = QPushButton(" Enviar")
        btn_send.setIcon(xp_icon("Send.png"))
        btn_send.setToolTip("Reproducir tono DTMF seleccionado")
        btn_send.clicked.connect(self._send_test_tone)
        row3.addWidget(btn_send)
        v3.addLayout(row3)

        v3.addWidget(QLabel("Duración (ms):"))
        self._test_dur_spin = QSpinBox()
        self._test_dur_spin.setRange(50, 2000)
        self._test_dur_spin.setValue(250)
        v3.addWidget(self._test_dur_spin)
        v3.addStretch()
        tabs.addTab(t3, "  Prueba")

        lay.addWidget(tabs)
        return p

    # ─────────────────────── PANEL: REPRODUCTOR ────────────────────────────
    def _build_reproductor(self) -> XPPanel:
        p = XPPanel("Reproductor  &  Playlist", "Playlist.png")
        lay = p.content_layout

        tools = QHBoxLayout()
        tools.setContentsMargins(0,0,0,0)
        self._lbl_current_track = QLabel("♪  Sin canción cargada")
        self._lbl_current_track.setStyleSheet(f"color:{T('accent')}; font-weight:bold;")
        tools.addWidget(self._lbl_current_track)
        tools.addStretch()
        lay.addLayout(tools)

        self._wave = WaveformWidget()
        
        self._lbl_on_air = QLabel("ON AIR")
        self._lbl_on_air.setStyleSheet(f"""
            background: {T('danger')}; color: white; font-weight: bold; 
            font-size: 16pt; border-radius: 6px; padding: 6px 12px;
        """)
        self._lbl_on_air.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_on_air.setVisible(False)
        
        info_lay = QHBoxLayout()
        info_lay.addWidget(self._wave, 1)
        info_lay.addWidget(self._lbl_on_air)
        lay.addLayout(info_lay)

        prog_row = QHBoxLayout()
        self._lbl_pos = QLabel("0:00")
        self._lbl_pos.setStyleSheet(f"font-size:8pt; color:{T('text_secondary')}; min-width:32px;")
        prog_row.addWidget(self._lbl_pos)

        self._song_slider = QSlider(Qt.Orientation.Horizontal)
        self._song_slider.setRange(0, 1000)
        self._song_slider.setValue(0)
        self._song_slider.setToolTip("Posición de reproducción")
        self._song_slider.sliderPressed.connect(lambda: setattr(self, "_seeking", True))
        self._song_slider.sliderReleased.connect(self._on_seek_released)
        prog_row.addWidget(self._song_slider, 1)

        self._lbl_dur = QLabel("0:00")
        self._lbl_dur.setStyleSheet(f"font-size:8pt; color:{T('text_secondary')}; min-width:32px;")
        prog_row.addWidget(self._lbl_dur)
        lay.addLayout(prog_row)

        # Transporte
        transport = QHBoxLayout()
        transport.setSpacing(6)
        transport.addStretch()

        self.btn_prev  = QPushButton("")
        self.btn_prev.setIcon(xp_icon("Prev.png"))
        self.btn_play  = QPushButton("")
        self.btn_play.setIcon(xp_icon("Play.png"))
        self.btn_stop  = QPushButton("")
        self.btn_stop.setIcon(xp_icon("Stop.png"))
        self.btn_next  = QPushButton("")
        self.btn_next.setIcon(xp_icon("Next.png"))

        for b in [self.btn_prev, self.btn_play, self.btn_stop, self.btn_next]:
            b.setFixedSize(44, 34)
            b.setIconSize(QSize(18, 18))

        self.btn_prev.clicked.connect(self.engine.prev_track)
        self.btn_play.clicked.connect(self._toggle_play_pause)
        self.btn_stop.clicked.connect(self._stop_playback)
        self.btn_next.clicked.connect(self.engine.next_track)

        for b in [self.btn_prev, self.btn_play, self.btn_stop, self.btn_next]:
            transport.addWidget(b)

        transport.addSpacing(12)
        lbl_vol = QLabel("Vol:")
        lbl_vol.setStyleSheet(f"font-size:8pt; color:{T('text_secondary')};")
        transport.addWidget(lbl_vol)
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(80)
        self._vol_slider.setFixedWidth(80)
        self._vol_slider.setToolTip("Volumen de reproducción")
        self._vol_slider.valueChanged.connect(lambda v: self.engine.set_volume(v / 100))
        transport.addWidget(self._vol_slider)
        transport.addStretch()
        lay.addLayout(transport)

        # Tabla playlist
        self._table_playlist = AudioDropTable(0, 5)
        self._table_playlist.setHorizontalHeaderLabels(["#", "Artista", "Título", "Duración", "Estado"])
        self._table_playlist.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table_playlist.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table_playlist.setAlternatingRowColors(True)
        self._table_playlist.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table_playlist.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table_playlist.verticalHeader().setVisible(False)
        self._table_playlist.verticalHeader().setDefaultSectionSize(28)
        self._table_playlist.doubleClicked.connect(self._playlist_double_click)
        self._table_playlist.filesDropped.connect(self._add_paths_to_playlist)
        self._table_playlist.setToolTip("Arrastra audios desde la biblioteca o Finder. Doble clic para reproducir.")
        lay.addWidget(self._table_playlist)
        return p

    # ─────────────────────── PANEL: BIBLIOTECA ─────────────────────────────
    def _build_biblioteca(self) -> XPPanel:
        p  = XPPanel("Biblioteca de Medios", "MyMusic.png")
        lay = p.content_layout

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Música ──────────────────────────────────
        wm = QWidget()
        vm = QVBoxLayout(wm)
        vm.setContentsMargins(0,0,0,0)
        vm.setSpacing(5)

        sr = QHBoxLayout()
        lbl_s = QLabel()
        px_s = xp_pixmap("Search.png", 16)
        if not px_s.isNull(): lbl_s.setPixmap(px_s)
        sr.addWidget(lbl_s)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Buscar canción, artista o álbum…")
        self._search_edit.textChanged.connect(self._filter_library)
        sr.addWidget(self._search_edit, 1)
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["Todos", "Artista", "Título", "Álbum"])
        self._filter_combo.setFixedWidth(90)
        sr.addWidget(self._filter_combo)
        vm.addLayout(sr)

        br = QHBoxLayout()
        for icon_name, lbl_txt, fn, tip in [
            ("Add.png",    "Añadir",   self._add_audio_files, "Añadir archivos de audio"),
            ("Open.png",   "Importar", self._import_folder,   "Importar carpeta de audio"),
            ("NetworkandInternet.png", "URL Streaming", self._add_streaming_url, "Añadir señal de streaming"),
            ("Delete.png", "Eliminar", self._del_from_library,"Eliminar de la biblioteca"),
            ("Playlist.png", "→ Playlist",self._add_lib_to_playlist,"Añadir selección a Playlist"),
        ]:
            btn = QPushButton(f"  {lbl_txt}")
            px2 = xp_pixmap(icon_name, 16)
            if not px2.isNull(): btn.setIcon(QIcon(px2))
            btn.setToolTip(tip)
            btn.clicked.connect(fn)
            br.addWidget(btn)
        br.addStretch()
        vm.addLayout(br)

        self._table_library = QTableWidget(0, 6)
        self._table_library.setHorizontalHeaderLabels(["Artista","Título","Álbum","Duración","Año","Ruta"])
        self._table_library.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table_library.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._table_library.setAlternatingRowColors(True)
        self._table_library.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table_library.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table_library.verticalHeader().setVisible(False)
        self._table_library.verticalHeader().setDefaultSectionSize(28)
        self._table_library.doubleClicked.connect(self._library_double_click)
        self._table_library.setToolTip("Doble clic para añadir a la playlist")
        vm.addWidget(self._table_library)

        self._lbl_lib_count = QLabel("  0 archivos")
        self._lbl_lib_count.setStyleSheet(f"color:{T('text_dim')}; font-size:8pt;")
        vm.addWidget(self._lbl_lib_count)
        splitter.addWidget(wm)

        # ── Pautas ──────────────────────────────────
        wp = QWidget()
        vp = QVBoxLayout(wp)
        vp.setContentsMargins(0,0,0,0)
        vp.setSpacing(5)

        lbl_p = QLabel("  Pautas Publicitarias")
        lbl_p.setStyleSheet(f"font-weight:bold; color:{T('accent')}; font-size:10pt;")
        vp.addWidget(lbl_p)

        br2 = QHBoxLayout()
        for icon_name, lbl_txt, fn, tip in [
            ("Add.png",    "Nueva Pauta", self._new_pauta,  "Crear nueva pauta publicitaria"),
            ("Delete.png", "Eliminar",    self._del_pauta,  "Eliminar pauta seleccionada"),
        ]:
            btn = QPushButton(f"  {lbl_txt}")
            px3 = xp_pixmap(icon_name, 16)
            if not px3.isNull(): btn.setIcon(QIcon(px3))
            btn.setToolTip(tip)
            btn.clicked.connect(fn)
            br2.addWidget(btn)
        br2.addStretch()
        vp.addLayout(br2)

        self._table_pautas = QTableWidget(0, 6)
        self._table_pautas.setHorizontalHeaderLabels(
            ["Archivo","Cliente","Spot","Duración","Horario","Días"])
        self._table_pautas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table_pautas.setAlternatingRowColors(True)
        self._table_pautas.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table_pautas.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self._table_pautas.verticalHeader().setVisible(False)
        self._table_pautas.verticalHeader().setDefaultSectionSize(28)
        vp.addWidget(self._table_pautas)

        splitter.addWidget(wp)
        splitter.setSizes([650, 350])
        lay.addWidget(splitter)
        return p

    # ─────────────────────── PANEL: AUDIO ──────────────────────────────────
    def _build_audio(self) -> XPPanel:
        p  = XPPanel("Encoder / Streaming", "Record.png")
        lay = p.content_layout

        # Lista vacía para compatibilidad con código existente
        self._vu_bars: list[VUBar] = []

        # Encoder status row
        enc_row = QHBoxLayout()
        enc_row.setSpacing(8)

        px_enc = xp_pixmap("Record.png", 28)
        lbl_enc_icon = QLabel()
        if not px_enc.isNull(): lbl_enc_icon.setPixmap(px_enc)
        enc_row.addWidget(lbl_enc_icon)

        col_enc = QVBoxLayout()
        col_enc.setSpacing(2)
        lbl_enc_t = QLabel("Encoder")
        lbl_enc_t.setStyleSheet(f"font-weight:bold; color:{T('text')};")
        col_enc.addWidget(lbl_enc_t)
        self._lbl_enc_status = QLabel("Desconectado")
        self._lbl_enc_status.setStyleSheet(f"color:{T('text_dim')}; font-size:8pt;")
        col_enc.addWidget(self._lbl_enc_status)
        enc_row.addLayout(col_enc, 1)

        self.btn_encoder = QPushButton(" OFF")
        _px_enc_btn = xp_pixmap("Record.png", 18)
        if not _px_enc_btn.isNull():
            self.btn_encoder.setIcon(QIcon(_px_enc_btn))
            self.btn_encoder.setIconSize(QSize(18, 18))
        self.btn_encoder.setCheckable(True)
        self.btn_encoder.setFixedSize(76, 36)
        self.btn_encoder.setToolTip("Iniciar/detener transmisión del encoder")
        self.btn_encoder.toggled.connect(self._toggle_encoder)
        self._update_encoder_style(False)
        enc_row.addWidget(self.btn_encoder)
        lay.addLayout(enc_row)

        # Info del encoder
        self._lbl_enc_info = QLabel("—")
        self._lbl_enc_info.setStyleSheet(f"color:{T('text_secondary')}; font-size:7pt; margin-top:4px;")
        lay.addWidget(self._lbl_enc_info)

        # Botón configurar
        btn_config = QPushButton("  Configurar Encoder…")
        px_cfg = xp_pixmap("Settings.png", 12)
        if not px_cfg.isNull():
            btn_config.setIcon(QIcon(px_cfg))
            btn_config.setIconSize(QSize(12, 12))
        btn_config.setFixedHeight(24)
        btn_config.setToolTip("Abrir configuración del encoder (codec, servidor, etc.)")
        btn_config.clicked.connect(self._config_encoder)
        lay.addWidget(btn_config)

        # Micrófono compacto
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"background:{T('border')}; max-height:1px; margin-top:6px;")
        lay.addWidget(sep2)

        mic_row = QHBoxLayout()
        mic_row.setSpacing(6)
        px_mic = xp_pixmap("AudioDevices.png", 20)
        lbl_mic_icon = QLabel()
        if not px_mic.isNull(): lbl_mic_icon.setPixmap(px_mic)
        mic_row.addWidget(lbl_mic_icon)

        col_mic = QVBoxLayout()
        col_mic.setSpacing(1)
        lbl_mic_t = QLabel("Micrófono")
        lbl_mic_t.setStyleSheet(f"font-weight:bold; color:{T('text')}; font-size:9pt;")
        col_mic.addWidget(lbl_mic_t)
        mic_row.addLayout(col_mic, 1)

        self.btn_mic = QPushButton(" OFF")
        _px_mic_btn = xp_pixmap("Volume.png", 14)
        if not _px_mic_btn.isNull():
            self.btn_mic.setIcon(QIcon(_px_mic_btn))
            self.btn_mic.setIconSize(QSize(14, 14))
        self.btn_mic.setCheckable(True)
        self.btn_mic.setFixedSize(60, 28)
        self.btn_mic.setToolTip("Activar / silenciar micrófono")
        self.btn_mic.toggled.connect(self._toggle_mic)
        self._update_mic_style(False)
        mic_row.addWidget(self.btn_mic)
        lay.addLayout(mic_row)

        # Fuente de entrada micrófono
        self._mic_src_combo = QComboBox()
        self._mic_src_combo.setToolTip("Seleccionar dispositivo de micrófono")
        self._mic_src_combo.setFixedHeight(24)
        lay.addWidget(self._mic_src_combo)
        self._populate_mic_sources()

        # Slider volumen micrófono
        lbl_vol_mic = QLabel("Volumen Micrófono")
        lbl_vol_mic.setStyleSheet(f"color:{T('text_secondary')}; font-size:7pt; margin-top:4px;")
        lay.addWidget(lbl_vol_mic)
        row_v = QHBoxLayout()
        sl_mic = QSlider(Qt.Orientation.Horizontal)
        sl_mic.setRange(0, 100)
        sl_mic.setValue(80)
        sl_mic.setToolTip("Volumen Micrófono: 80%")
        row_v.addWidget(sl_mic, 1)
        val_lbl = QLabel("80%")
        val_lbl.setFixedWidth(38)
        val_lbl.setStyleSheet(f"font-size:7pt; color:{T('text_secondary')};")
        row_v.addWidget(val_lbl)
        sl_mic.valueChanged.connect(lambda v, l=val_lbl, s=sl_mic: (
            l.setText(f"{v}%"),
            s.setToolTip(f"Volumen Micrófono: {v}%")
        ))
        sl_mic.valueChanged.connect(lambda v: self.passthrough.set_volume(v / 100))
        lay.addLayout(row_v)
        self._vol_sliders = {"mic": sl_mic}

        lay.addStretch()
        return p

    def _update_encoder_style(self, active: bool):
        if active:
            self.btn_encoder.setText(" ON")
            self.btn_encoder.setStyleSheet(
                f"QPushButton {{ background:{T('success')}; color:#fff; border:1px solid {T('border')}; "
                f"border-radius:3px; font-weight:bold; padding:4px; }}"
            )
        else:
            self.btn_encoder.setText(" OFF")
            self.btn_encoder.setStyleSheet(
                f"QPushButton {{ background:{T('bg_surface')}; color:{T('text_secondary')}; "
                f"border:1px solid {T('border')}; border-radius:3px; padding:4px; }}"
            )

    # ═══════════════════════════════════════════════════
    #  STATUS BAR
    # ═══════════════════════════════════════════════════
    def _setup_statusbar(self):
        sb = self.statusBar()
        self._sb_led = LEDIndicator(QColor(255,30,30))
        self._sb_led.set_on(True)
        sb.addWidget(self._sb_led)
        sb.addWidget(QLabel("  ON AIR  "))

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color:{T('border')};")
        sb.addWidget(sep)

        self._sb_dtmf_lbl = QLabel("  DTMF: inactivo  ")
        sb.addWidget(self._sb_dtmf_lbl)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet(f"color:{T('border')};")
        sb.addWidget(sep2)

        self._sb_track_lbl = QLabel("  Sin reproducción  ")
        sb.addWidget(self._sb_track_lbl)

        sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet(f"color:{T('border')};")
        sb.addWidget(sep3)

        self._sb_state_lbl = QLabel("  ● Listo  ")
        self._sb_state_lbl.setStyleSheet(f"color:{T('success')}; font-weight:bold;")
        sb.addPermanentWidget(self._sb_state_lbl)

    def _apply_dtmf_display_style(self, mode: str = "default", text: str = ""):
        t = _current_theme
        if text:
            self._dtmf_display.setText(text)
        if mode == "success":
            self._dtmf_display.setStyleSheet(
                f"background:#002200; color:{t['success']}; font-family:Menlo,monospace;"
                f"font-size:11pt; font-weight:bold; border-radius:6px; padding:4px;"
            )
        elif mode == "danger":
            self._dtmf_display.setStyleSheet(
                f"background:#220000; color:{t['danger']}; font-family:Menlo,monospace;"
                f"font-size:11pt; font-weight:bold; border-radius:6px; padding:4px;"
            )
        elif mode == "warning":
            self._dtmf_display.setStyleSheet(
                f"background:#221100; color:{t['warning']}; font-family:Menlo,monospace;"
                f"font-size:11pt; font-weight:bold; border-radius:6px; padding:4px;"
            )
        else:
            self._dtmf_display.setStyleSheet(
                f"background:{t['bg_input']}; color:{t['wave_text']}; font-family:Menlo,monospace;"
                f"font-size:11pt; font-weight:bold; border-radius:6px; padding:4px;"
            )
        if mode != "default":
            QTimer.singleShot(2500, lambda: self._apply_dtmf_display_style("default"))

    # ═══════════════════════════════════════════════════
    #  ACCIONES: CONSOLA
    # ═══════════════════════════════════════════════════
    def _toggle_signal(self, checked: bool):
        if self._dtmf_activating:
            print("[SIGNAL] Toggle ignorado (DTMF activando)")
            return
        if checked and self._remote_on:
            print("[SIGNAL] Ignorado: Señal Remota activa")
            old = self.btn_signal.blockSignals(True)
            self.btn_signal.setChecked(False)
            self.btn_signal.blockSignals(old)
            self._signal_on = False
            self._led_signal.set_on(False)
            self._sb_led.set_on(False)
            self.btn_signal.setStyleSheet("")
            self._sb_state_lbl.setText("  ● Señal Remota  ")
            self._sb_state_lbl.setStyleSheet(f"color:{T('accent')}; font-weight:bold;")
            self._apply_dtmf_display_style("warning", ">>> SEÑAL PRINCIPAL BLOQUEADA: REMOTO ACTIVO <<<")
            return
        print(f"[SIGNAL] Toggle llamado con checked={checked}")
        self._signal_on = checked
        self._led_signal.set_on(checked)
        self._sb_led.set_on(checked)
        if checked:
            if self._pauta_on:
                print("[SIGNAL] Deteniendo Pauta Local...")
                self._pauta_on = False
                self.engine.stop()
                self._set_pauta_checked(False)
                self.btn_pauta.setStyleSheet("")
            print("[SIGNAL] Activando señal principal...")
            t = _current_theme
            self.btn_signal.setStyleSheet(f"""
                QPushButton {{ background:{t['danger']};
                    color:white; font-weight:bold; border-radius:6px; border:2px solid {t['danger']}; }}
            """)
            self._sb_state_lbl.setText("  ● En Aire  ")
            self._sb_state_lbl.setStyleSheet(f"color:{T('danger')}; font-weight:bold;")
            self._start_main_signal()
        else:
            print("[SIGNAL] Desactivando señal principal...")
            self.btn_signal.setStyleSheet("")
            self._sb_state_lbl.setText("  ● Listo  ")
            self._sb_state_lbl.setStyleSheet(f"color:{T('success')}; font-weight:bold;")
            self._stop_main_signal()

    def _start_main_signal(self):
        in_dev = self._dtmf_dev_combo.currentData()
        out_dev = self._sd_out_dev_combo.currentData()
        print(f"[SIGNAL] _start_main_signal: in_dev={in_dev}, out_dev={out_dev}")
        if in_dev is None or out_dev is None:
            print("[SIGNAL] ERROR: Dispositivos no configurados")
            QMessageBox.warning(self, "Dispositivos no configurados",
                "Configura los dispositivos de entrada y salida en Configuración DTMF → Dispositivos")
            self.btn_signal.setChecked(False)
            return
        # Guardar estado del reproductor antes de activar señal
        self._was_playing_before_signal = self.engine.state == "playing"
        print(f"[SIGNAL] Iniciando passthrough: in={in_dev}, out={out_dev}")
        self.passthrough.set_devices(in_dev, out_dev)
        self.passthrough.set_muted(False)
        self._main_signal_monitoring_for_pauta = False
        # Si DTMF está activo, alimentarlo desde el passthrough
        if self._dtmf_on:
            self._attach_dtmf_to_passthrough()
        self.passthrough.start()
        self._wave.set_metadata("♪ SEÑAL PRINCIPAL: Audio en vivo  •  RadioSAT XP")
        self._set_dashboard_source("AL AIRE · SEÑAL DE CADENA", "Fuente: cadena principal",
                                   "La señal de cadena se transmite a la audiencia")
        print("[SIGNAL] ✓ Passthrough iniciado")

    def _stop_main_signal(self):
        self._main_signal_monitoring_for_pauta = False
        self.passthrough.set_muted(False)
        self._detach_dtmf_from_passthrough()
        self.passthrough.stop()
        if not self._pauta_on and not self._remote_on:
            self._set_dashboard_source("SIN FUENTE CONFIRMADA", "Fuente: sin datos",
                                       "Configura o activa una fuente de programa")
        self._wave.set_idle()
        # Reanudar reproductor si estaba reproduciendo antes
        if self._was_playing_before_signal:
            self.engine.play()
            self._was_playing_before_signal = False

    def _attach_dtmf_to_passthrough(self):
        """Usa el audio de Señal Principal como fuente DTMF sin abrir otro input."""
        self._apply_dtmf_params()
        self.passthrough.unregister_input_callback(self.dtmf.feed_samples)
        self.dtmf.stop()
        self.dtmf.start_external()
        self.passthrough.register_input_callback(self.dtmf.feed_samples)
        self._on_dtmf_status("Escuchando señal principal")
        status_label = getattr(self, "_sb_dtmf_lbl", None)
        if status_label is not None:
            status_label.setText("  DTMF: Señal Principal  ")

    def _detach_dtmf_from_passthrough(self):
        """Desconecta el DTMF del passthrough y restaura modo normal si aplica."""
        self.passthrough.unregister_input_callback(self.dtmf.feed_samples)
        if self.dtmf._external_mode:
            self.dtmf.stop_external()
            if self._dtmf_on:
                print("[DTMF] Programando reinicio del detector interno en 1000ms...")
                QTimer.singleShot(1000, self._start_dtmf_safe)

    def _hold_main_signal_for_pauta(self):
        """Silencia Señal Principal, pero mantiene su entrada viva para DTMF."""
        if not self._signal_on:
            return False

        print("[SIGNAL] Señal Principal queda monitoreando en silencio para DTMF...")
        self._signal_on = False
        self._led_signal.set_on(False)
        self._sb_led.set_on(False)
        old = self.btn_signal.blockSignals(True)
        self.btn_signal.setChecked(False)
        self.btn_signal.blockSignals(old)
        self.btn_signal.setStyleSheet("")

        if self._dtmf_on and not self.passthrough.is_running:
            in_dev = self._dtmf_dev_combo.currentData()
            out_dev = self._sd_out_dev_combo.currentData()
            if in_dev is not None and out_dev is not None:
                self.passthrough.set_devices(in_dev, out_dev)
                self.passthrough.start()

        if self._dtmf_on and self.passthrough.is_running:
            self._main_signal_monitoring_for_pauta = True
            self.passthrough.set_muted(True)
            self._attach_dtmf_to_passthrough()
            self._sb_state_lbl.setText("  ● Pauta Local  ")
            self._sb_state_lbl.setStyleSheet(f"color:{T('success')}; font-weight:bold;")
            return True

        self._main_signal_monitoring_for_pauta = False
        self._detach_dtmf_from_passthrough()
        self.passthrough.stop()
        return False

    def _restore_main_signal_from_monitor(self):
        if not self._main_signal_monitoring_for_pauta or not self.passthrough.is_running:
            return False
        print("[SIGNAL] Restaurando Señal Principal desde monitor silencioso...")
        self._main_signal_monitoring_for_pauta = False
        self.passthrough.set_muted(False)
        if self._dtmf_on:
            self._attach_dtmf_to_passthrough()
        self._wave.set_metadata("♪ SEÑAL PRINCIPAL: Audio en vivo  •  RadioSAT XP")
        return True

    def _return_to_main_signal_from_dtmf(self):
        print("[DTMF→SIGNAL] Retornando desde Pauta Local a Señal Principal...")
        self._dtmf_activating = True
        self._remote_resume_pending = False

        if self._pauta_on or self.engine.state != "stopped":
            self._pauta_on = False
            self.engine.stop()
            self._set_pauta_checked(False)
            self.btn_pauta.setStyleSheet("")

        restored = self._restore_main_signal_from_monitor()
        if not restored:
            in_dev = self._dtmf_dev_combo.currentData()
            out_dev = self._sd_out_dev_combo.currentData()
            if in_dev is not None and out_dev is not None:
                self.passthrough.set_devices(in_dev, out_dev)
                self.passthrough.set_muted(False)
                if self._dtmf_on:
                    self._attach_dtmf_to_passthrough()
                self.passthrough.start()
                restored = True

        if restored:
            self._signal_on = True
            self._led_signal.set_on(True)
            self._sb_led.set_on(True)
            old = self.btn_signal.blockSignals(True)
            self.btn_signal.setChecked(True)
            self.btn_signal.blockSignals(old)
            t = _current_theme
            self.btn_signal.setStyleSheet(f"""
                QPushButton {{ background:{t['danger']};
                    color:white; font-weight:bold; border-radius:6px; border:2px solid {t['danger']}; }}
            """)
            self._sb_state_lbl.setText("  ● En Aire  ")
            self._sb_state_lbl.setStyleSheet(f"color:{T('danger')}; font-weight:bold;")
            self._apply_dtmf_display_style("danger", ">>> SEÑAL PRINCIPAL <<<")
            self._wave.set_metadata("♪ SEÑAL PRINCIPAL: Audio en vivo  •  RadioSAT XP")
        else:
            self._apply_dtmf_display_style("danger", ">>> ERROR: CONFIGURA DISPOSITIVOS <<<")
        self._dtmf_activating = False

    def _start_dtmf_safe(self):
        """Reinicia el detector DTMF de forma segura asegurando los parámetros correctos."""
        if self._dtmf_on and not self.dtmf._running and not self.dtmf._external_mode:
            print("[DTMF] Reiniciando detector de forma segura...")
            self._apply_dtmf_params()
            self.dtmf.start()

    def _toggle_pauta(self, checked: bool, from_dtmf: bool = False):
        if self._dtmf_activating:
            print("[PAUTA] Toggle ignorado (DTMF activando)")
            return
        print(f"[PAUTA] Toggle llamado con checked={checked}, from_dtmf={from_dtmf}")
        self._pauta_on = checked
        if checked:
            self._remote_resume_pending = False
            if not self.engine.playlist:
                if from_dtmf:
                    print("[PAUTA] ERROR: Playlist vacía, no se puede activar Pauta Local")
                    self._apply_dtmf_display_style("warning", ">>> ERROR: PLAYLIST VACÍA <<<")
                else:
                    QMessageBox.information(self,"Sin playlist",
                        "La playlist está vacía.\nAñade archivos de audio primero.")
                self.btn_pauta.setChecked(False)
                return
            if self._signal_on:
                print("[PAUTA] Deteniendo señal principal...")
                self._hold_main_signal_for_pauta()
            if self._remote_on and self.remote_engine.is_playing:
                self.remote_engine.set_muted(True)
            print("[PAUTA] Iniciando reproducción desde el inicio...")
            self.engine.play(0)
            t = _current_theme
            self.btn_pauta.setStyleSheet(f"""
                QPushButton {{ background:{t['success']};
                    color:white; font-weight:bold; border-radius:6px; border:2px solid {t['success']}; }}
            """)
        else:
            print("[PAUTA] Deteniendo reproducción...")
            self._remote_resume_pending = False
            self.engine.stop()
            self.btn_pauta.setStyleSheet("")
            if self._main_signal_monitoring_for_pauta:
                self._restore_main_signal_from_monitor()
                self._signal_on = True
                self._led_signal.set_on(True)
                self._sb_led.set_on(True)
                old = self.btn_signal.blockSignals(True)
                self.btn_signal.setChecked(True)
                self.btn_signal.blockSignals(old)
                t = _current_theme
                self.btn_signal.setStyleSheet(f"""
                    QPushButton {{ background:{t['danger']};
                        color:white; font-weight:bold; border-radius:6px; border:2px solid {t['danger']}; }}
                """)
            if self._remote_on and not self._remote_break_active:
                self.remote_engine.set_muted(False)

    def _toggle_dtmf(self, checked: bool):
        print(f"[DTMF] Toggle llamado con checked={checked}")
        self._dtmf_on = checked
        self._led_dtmf.set_on(checked)
        if checked:
            if not SOUND_OK:
                QMessageBox.warning(self,"Sin sounddevice",
                    "Instala sounddevice y numpy:\n  pip install sounddevice numpy")
                self.btn_dtmf_main.setChecked(False)
                return
            print("[DTMF] Aplicando parámetros...")
            self._apply_dtmf_params()
            if self._signal_on and self.passthrough.is_running:
                print("[DTMF] Enganchando detector a Señal Principal...")
                self._attach_dtmf_to_passthrough()
            else:
                print("[DTMF] Iniciando detector...")
                self.dtmf.start()
                self._on_dtmf_status("Escuchando entrada DTMF")
                status_label = getattr(self, "_sb_dtmf_lbl", None)
                if status_label is not None:
                    status_label.setText("  DTMF: Escuchando…  ")
            t = _current_theme
            self.btn_dtmf_main.setStyleSheet(f"""
                QPushButton {{ background:{t['warning']};
                    color:white; font-weight:bold; border-radius:6px; border:2px solid {t['warning']}; }}
            """)
            print(f"[DTMF] Secuencia PLAY configurada: {self._dtmf_seq_play.text().strip()}")
            print(f"[DTMF] Secuencia STOP configurada: {self._dtmf_seq_stop.text().strip()}")
        else:
            print("[DTMF] Deteniendo detector...")
            self._detach_dtmf_from_passthrough()
            self.dtmf.stop()
            self._on_dtmf_status("Detector DTMF inactivo")
            status_label = getattr(self, "_sb_dtmf_lbl", None)
            if status_label is not None:
                status_label.setText("  DTMF: inactivo  ")
            self.btn_dtmf_main.setStyleSheet("")

    def _toggle_dtmf_panel(self):
        self.btn_dtmf_main.setChecked(not self.btn_dtmf_main.isChecked())

    # ═══════════════════════════════════════════════════
    #  ACCIONES: SEÑAL REMOTA
    # ═══════════════════════════════════════════════════
    def _toggle_remote(self, checked: bool):
        self._remote_on = checked
        self._led_remote.set_on(checked)
        self._remote_controls.setVisible(checked)
        if not checked:
            self._remote_stop(manual=True)

    def _remote_play(self):
        url = self._remote_url_edit.text().strip()
        if not url:
            QMessageBox.information(self, "URL requerida",
                "Introduce la URL del stream de audio remoto.")
            return
        self._remote_resume_pending = False
        self._start_remote_playback(url)

    def _start_remote_playback(self, url: str, from_resume: bool = False):
        self._remote_resume_url = url
        if self._pauta_on:
            self._pauta_on = False
            self.engine.stop()
            self._set_pauta_checked(False)
            self.btn_pauta.setStyleSheet("")
        self.btn_remote_play.setEnabled(False)
        self.btn_remote_stop.setEnabled(True)
        self._lbl_remote_status.setText("Conectando...")
        self._lbl_remote_status.setStyleSheet(f"color:{T('warning')}; font-size:7pt;")
        msg = ">>> VOLVIENDO A SEÑAL REMOTA <<<" if from_resume else ">>> SEÑAL REMOTA ACTIVADA <<<"
        self._apply_dtmf_display_style("success", msg)
        self._apply_dtmf_params()
        connect_seq = self._dtmf_seq_play.text().strip()
        fallback_seq = self._dtmf_seq_stop.text().strip()
        self._remote_break_start_seq = connect_seq
        self._remote_break_return_seq = fallback_seq
        remote_sequences = [seq for seq in (connect_seq, fallback_seq) if seq]
        if hasattr(self, "_remote_out_dev_combo"):
            self.remote_engine.set_output_device(self._remote_out_dev_combo.currentData())
        self.remote_engine.set_muted(False)
        self.remote_engine.play(url)
        self.remote_dtmf.start(url, remote_sequences)
        self._remote_dtmf_active = True
        self._remote_on = True
        self._led_remote.set_on(True)
        self._remote_controls.setVisible(True)
        if not self.btn_remote.isChecked():
            old = self.btn_remote.blockSignals(True)
            self.btn_remote.setChecked(True)
            self.btn_remote.blockSignals(old)
        t = _current_theme
        self.btn_remote.setStyleSheet(f"""
            QPushButton {{ background:{t['accent']};
                color:white; font-weight:bold; border-radius:6px; border:2px solid {t['accent']}; }}
        """)

    def _remote_stop(self, manual: bool = True, paused_for_pauta: bool = False):
        if manual:
            self._remote_resume_pending = False
            self._remote_break_active = False
            self.remote_engine.set_muted(False)
        self._remote_dtmf_active = False
        self.remote_engine.stop()
        self.remote_dtmf.stop()
        self.btn_remote_play.setEnabled(True)
        self.btn_remote_stop.setEnabled(False)
        if paused_for_pauta:
            self._lbl_remote_status.setText("Pauta local en curso...")
            self._lbl_remote_status.setStyleSheet(f"color:{T('warning')}; font-size:7pt;")
        else:
            self._lbl_remote_status.setText("Inactivo")
            self._lbl_remote_status.setStyleSheet(f"color:{T('text_dim')}; font-size:7pt;")
            self.btn_remote.setStyleSheet("")

    def _on_remote_state(self, state: str):
        if state == "playing":
            self._lbl_remote_status.setText("Reproduciendo")
            self._lbl_remote_status.setStyleSheet(f"color:{T('success')}; font-size:7pt;")
            self._set_dashboard_source("AL AIRE · SEÑAL REMOTA", "Fuente: streaming remoto",
                                       "La señal remota se transmite a la audiencia")
        elif state == "error":
            self._lbl_remote_status.setText("Error de conexión")
            self._lbl_remote_status.setStyleSheet(f"color:{T('danger')}; font-size:7pt;")
            self._remote_stop()
        else:
            if self._remote_break_active:
                self._lbl_remote_status.setText("Monitoreando tono de conexión...")
                self._lbl_remote_status.setStyleSheet(f"color:{T('warning')}; font-size:7pt;")
            elif self._remote_resume_pending:
                self._lbl_remote_status.setText("Pauta local en curso...")
                self._lbl_remote_status.setStyleSheet(f"color:{T('warning')}; font-size:7pt;")
            else:
                self._lbl_remote_status.setText("Inactivo")
                self._lbl_remote_status.setStyleSheet(f"color:{T('text_dim')}; font-size:7pt;")

    def _on_remote_level(self, l: float, r: float):
        if len(self._vu_bars) >= 2:
            self._vu_bars[0].set_value(min(l, 1.0))
            self._vu_bars[1].set_value(min(r * 0.9, 1.0))

    def _remote_dtmf_action(self, sequence: str):
        self._dtmf_log.clear()
        if self._remote_break_active:
            return_seq = self._remote_break_return_seq
            if not return_seq or sequence == return_seq or sequence != self._remote_break_start_seq:
                self._return_to_remote_from_dtmf()
            return

        start_seq = self._remote_break_start_seq
        if start_seq and sequence != start_seq:
            return

        if not self.engine.playlist:
            self._apply_dtmf_display_style("warning", ">>> ERROR: PLAYLIST VACÍA <<<")
            return
        self._remote_resume_url = self._remote_url_edit.text().strip() or self._remote_resume_url
        self._remote_resume_pending = bool(self._remote_resume_url)
        self._start_remote_pauta()

    def _start_remote_pauta(self):
        if self._signal_on:
            self._signal_on = False
            self._led_signal.set_on(False)
            self._sb_led.set_on(False)
            self.btn_signal.setChecked(False)
            self.btn_signal.setStyleSheet("")
            self._detach_dtmf_from_passthrough()
            self.passthrough.stop()
        self._remote_break_active = True
        self.remote_engine.set_muted(True)
        self._pauta_on = True
        self._set_pauta_checked(True)
        t = _current_theme
        self.btn_pauta.setStyleSheet(f"""
            QPushButton {{ background:{t['success']};
                color:white; font-weight:bold; border-radius:6px; border:2px solid {t['success']}; }}
        """)
        self._apply_dtmf_display_style("success", ">>> PAUTA LOCAL ACTIVADA <<<")
        self.engine.play(0, stop_at_end=True)

    def _return_to_remote_from_dtmf(self):
        self._remote_resume_pending = False
        self._remote_break_active = False
        self.remote_engine.set_muted(False)
        if self._signal_on:
            self._signal_on = False
            self._detach_dtmf_from_passthrough()
            self.passthrough.stop()
            self._led_signal.set_on(False)
            self._sb_led.set_on(False)
            old = self.btn_signal.blockSignals(True)
            self.btn_signal.setChecked(False)
            self.btn_signal.blockSignals(old)
            self.btn_signal.setStyleSheet("")
        if self._pauta_on:
            self._pauta_on = False
            self.engine.stop()
            self._set_pauta_checked(False)
            self.btn_pauta.setStyleSheet("")
        self._apply_dtmf_display_style("success", ">>> SEÑAL REMOTA ACTIVADA <<<")
        self._lbl_remote_status.setText("Reproduciendo")
        self._lbl_remote_status.setStyleSheet(f"color:{T('success')}; font-size:7pt;")

    def _set_pauta_checked(self, checked: bool):
        old = self.btn_pauta.blockSignals(True)
        self.btn_pauta.setChecked(checked)
        self.btn_pauta.blockSignals(old)

    def _on_pauta_sequence_finished(self):
        if self._main_signal_monitoring_for_pauta:
            self._pauta_on = False
            self._set_pauta_checked(False)
            self.btn_pauta.setStyleSheet("")
            self.passthrough.set_muted(True)
            self._apply_dtmf_display_style("warning", ">>> ESPERANDO TONO DE SEÑAL PRINCIPAL <<<")
            self._sb_state_lbl.setText("  ● Esperando Señal Principal  ")
            self._sb_state_lbl.setStyleSheet(f"color:{T('warning')}; font-weight:bold;")
            return
        if not self._remote_resume_pending and not self._remote_break_active:
            return
        self._pauta_on = False
        self._set_pauta_checked(False)
        self.btn_pauta.setStyleSheet("")
        if self._remote_break_active:
            self.remote_engine.set_muted(True)
            self._apply_dtmf_display_style("warning", ">>> ESPERANDO TONO DE CONEXIÓN <<<")
            self._lbl_remote_status.setText("Monitoreando tono de conexión...")
            self._lbl_remote_status.setStyleSheet(f"color:{T('warning')}; font-size:7pt;")
            return
        url = self._remote_resume_url or self._remote_url_edit.text().strip()
        self._remote_resume_pending = False
        if url:
            self._apply_dtmf_display_style("success", ">>> VOLVIENDO A SEÑAL REMOTA <<<")
            QTimer.singleShot(500, lambda u=url: self._start_remote_playback(u, from_resume=True))
        else:
            self._apply_dtmf_display_style("warning", ">>> URL REMOTA NO DISPONIBLE <<<")

    def _on_remote_metadata(self, text: str):
        if self._remote_break_active:
            return
        self._lbl_remote_status.setText(text[:60])
        self._lbl_remote_status.setStyleSheet(f"color:{T('text_secondary')}; font-size:7pt;")

    # ═══════════════════════════════════════════════════
    #  ACCIONES: DTMF
    # ═══════════════════════════════════════════════════
    def _refresh_devices(self):
        self._dtmf_dev_combo.clear()
        self._out_dev_combo.clear()
        self._remote_out_dev_combo.clear()
        self._sd_out_dev_combo.clear()

        # --- Dispositivos sounddevice (para DTMF entrada + passthrough salida) ---
        if SOUND_OK:
            try:
                devs = sd.query_devices()
                for i, d in enumerate(devs):
                    name = d["name"]
                    if d["max_input_channels"] > 0 and _is_real_audio_device(d):
                        ch = d["max_input_channels"]
                        tag = " [Stereo]" if ch >= 2 else " [Mono]"
                        self._dtmf_dev_combo.addItem(f"{name}{tag}", i)
                    if d["max_output_channels"] > 0 and _is_real_audio_device(d):
                        self._sd_out_dev_combo.addItem(f"{name}", i)
            except Exception:
                pass
        if self._dtmf_dev_combo.count() == 0:
            self._dtmf_dev_combo.addItem("(sin dispositivos)", None)
        if self._sd_out_dev_combo.count() == 0:
            self._sd_out_dev_combo.addItem("(sin dispositivos)", None)

        # --- Dispositivos QtMultimedia (para reproductor local + remoto) ---
        try:
            default_output = QMediaDevices.defaultAudioOutput()
            # Reproductor local
            self._out_dev_combo.addItem("Sistema predeterminado", None)
            for device in QMediaDevices.audioOutputs():
                label = device.description()
                self._out_dev_combo.addItem(label, device)
                if not default_output.isNull() and device.id() == default_output.id():
                    self._out_dev_combo.setCurrentIndex(self._out_dev_combo.count() - 1)
            # Reproductor remoto
            self._remote_out_dev_combo.addItem("Sistema predeterminado", None)
            for device in QMediaDevices.audioOutputs():
                label = device.description()
                self._remote_out_dev_combo.addItem(label, device)
                if not default_output.isNull() and device.id() == default_output.id():
                    self._remote_out_dev_combo.setCurrentIndex(self._remote_out_dev_combo.count() - 1)
        except Exception:
            self._out_dev_combo.addItem("Sistema predeterminado", None)
            self._remote_out_dev_combo.addItem("Sistema predeterminado", None)
        if hasattr(self, "_lbl_status_input"):
            self._sync_dashboard_status()

    def _on_out_dev_changed(self, idx):
        """Aplica el dispositivo de salida seleccionado al reproductor local."""
        if not hasattr(self, "engine"):
            return
        device = self._out_dev_combo.currentData()
        self.engine.set_output_device(device)
        print(f"[DEVICES] Reproductor local → {self._out_dev_combo.currentText()}")

    def _on_remote_out_dev_changed(self, idx):
        if not hasattr(self, "remote_engine"):
            return
        self.remote_engine.set_output_device(self._remote_out_dev_combo.currentData())

    def _apply_dtmf_params(self):
        tol    = self._dtmf_tol.value()
        thresh_db = self._dtmf_thresh.value()
        thresh = 10 ** (thresh_db / 20) * 0.5
        thresh = max(0.008, thresh)
        dev    = self._dtmf_dev_combo.currentData()
        self.dtmf.set_params(freq_tol=tol, rms_threshold=thresh, device=dev)
        self.remote_dtmf.set_params(freq_tol=tol, rms_threshold=thresh)
        self._sync_dashboard_dtmf_rules()

    def _send_test_tone(self):
        if not SOUND_OK:
            QMessageBox.warning(self,"Sin sounddevice","Instala sounddevice y numpy para enviar tonos.")
            return
        digit = self._test_tone_cb.currentText().split(" ", 1)[0]
        freqs = self._test_tone_cb.currentData()
        dur   = self._test_dur_spin.value() / 1000.0
        sr    = 44100
        t     = [i / sr for i in range(int(sr * dur))]
        try:
            import numpy as np
            samples = np.zeros((len(t), 2), dtype=np.float32)
            tone = (0.5 * np.sin(2 * np.pi * freqs[0] * np.array(t)) +
                    0.5 * np.sin(2 * np.pi * freqs[1] * np.array(t)))
            samples[:, 0] = tone
            samples[:, 1] = tone
        except Exception as e:
            QMessageBox.warning(self,"Error de tono", str(e))
            return

        play_error = None
        try:
            out_dev = self._sd_out_dev_combo.currentData()
            sd.play(samples, sr, device=out_dev)
        except Exception as e:
            play_error = e

        self._feed_generated_dtmf_digit(digit)

        if play_error is not None:
            QMessageBox.warning(self,"Error de tono", str(play_error))

    def _feed_generated_dtmf_digit(self, digit: str):
        remote_listening = (
            self._remote_on and
            (self._remote_dtmf_active or self._remote_break_active or self.remote_engine.is_playing)
        )
        if remote_listening:
            play_seq = self._dtmf_seq_play.text().strip()
            stop_seq = self._dtmf_seq_stop.text().strip()
            remote_sequences = [seq for seq in (play_seq, stop_seq) if seq]
            if remote_sequences and self.remote_dtmf._seq != remote_sequences:
                self._remote_break_start_seq = play_seq
                self._remote_break_return_seq = stop_seq
                self.remote_dtmf.arm(remote_sequences)
            self.remote_dtmf.feed_digit(digit, bypass_cooldown=True)
        elif self._dtmf_on:
            self.dtmf.feed_digit(digit)

    def _matched_dtmf_sequence(self, digit: str, targets: list[str]) -> str:
        matched = ""
        active_targets = [target for target in targets if target]
        for target in active_targets:
            pos = self._dtmf_seq_progress.get(target, 0)
            expected = target[pos] if pos < len(target) else target[0]

            if digit == expected:
                pos += 1
            elif digit == target[0]:
                pos = 1
            elif digit not in target:
                self._dtmf_seq_progress[target] = pos
                continue
            else:
                pos = 0

            if pos >= len(target):
                matched = target
                pos = 0
            self._dtmf_seq_progress[target] = pos

        stale_targets = set(self._dtmf_seq_progress) - set(active_targets)
        for target in stale_targets:
            self._dtmf_seq_progress.pop(target, None)
        return matched

    def _on_dtmf_digit(self, digit: str):
        now = time.time()

        # Si pasaron más de 5 segundos sin dígitos, limpiar buffer
        if now - self._last_digit_time > 5.0 and self._dtmf_log:
            self._dtmf_log.clear()
            self._dtmf_seq_progress.clear()

        self._last_digit_time = now
        self._dtmf_log.append(digit)
        seq = "".join(self._dtmf_log[-10:])

        # Actualizar último código en el nuevo panel DTMF
        if hasattr(self, '_lbl_last_code'):
            from datetime import datetime
            time_str = datetime.now().strftime("%H:%M:%S")
            self._lbl_last_code.setText(f"{seq} · {time_str}")

        play_seq = self._dtmf_seq_play.text().strip()
        stop_seq = self._dtmf_seq_stop.text().strip()
        matched_seq = self._matched_dtmf_sequence(digit, [play_seq, stop_seq])

        # Modo normal: mostrar dígitos en display
        if hasattr(self, '_dtmf_display'):
            self._dtmf_display.setText(seq)
        if hasattr(self, '_sb_dtmf_lbl'):
            self._sb_dtmf_lbl.setText(f"  DTMF: [{digit}] {seq}")
        
        if play_seq and matched_seq == play_seq:
            print(f"[DTMF] === SECUENCIA PLAY DETECTADA: {play_seq} ===")
            self._dtmf_log.clear()
            self._dtmf_seq_progress.clear()
            self._dtmf_cooldown_until = now + 3.0
            if self._remote_on:
                self._apply_dtmf_display_style("success", ">>> PAUTA LOCAL ACTIVADA <<<")
                self._remote_dtmf_action(play_seq)
            else:
                self._apply_dtmf_display_style("success", ">>> PAUTA LOCAL ON <<<")
                self._activate_pauta_from_dtmf()
                
        elif stop_seq and matched_seq == stop_seq:
            print(f"[DTMF] === SECUENCIA STOP DETECTADA: {stop_seq} ===")
            self._dtmf_log.clear()
            self._dtmf_seq_progress.clear()
            self._dtmf_cooldown_until = now + 3.0
            if self._remote_on:
                self._apply_dtmf_display_style("success", ">>> SEÑAL REMOTA <<<")
                self._return_to_remote_from_dtmf()
            elif self._main_signal_monitoring_for_pauta or self._pauta_on:
                self._return_to_main_signal_from_dtmf()
            else:
                self._apply_dtmf_display_style("danger", ">>> SEÑAL PRINCIPAL <<<")
                self._activate_signal_from_dtmf()

    def _activate_pauta_from_dtmf(self):
        print("[DTMF→PAUTA] === ACTIVANDO PAUTA LOCAL ===")
        self._dtmf_activating = True
        # 1. Verificar playlist
        if not self.engine.playlist:
            print("[DTMF→PAUTA] ERROR: Playlist vacía")
            self._apply_dtmf_display_style("warning", ">>> ERROR: PLAYLIST VACÍA <<<")
            self._dtmf_activating = False
            return
        
        # 2. Detener Señal Principal si está activa
        if self._signal_on:
            print("[DTMF→PAUTA] Deteniendo Señal Principal...")
            self._hold_main_signal_for_pauta()
        
        # 3. Activar Pauta Local
        self._pauta_on = True
        self.btn_pauta.setChecked(True)
        t = _current_theme
        self.btn_pauta.setStyleSheet(f"""
            QPushButton {{ background:{t['success']};
                color:white; font-weight:bold; border-radius:6px; border:2px solid {t['success']}; }}
        """)
        self.engine.play(0, stop_at_end=True)
        print("[DTMF→PAUTA] ✓ Pauta Local activada correctamente (desde audio 1)")
        self._dtmf_activating = False

    def _activate_signal_from_dtmf(self):
        if self._remote_on:
            print("[DTMF→SIGNAL] Ignorado: Señal Remota activa")
            self._return_to_remote_from_dtmf()
            return
        print("[DTMF→SIGNAL] === ACTIVANDO SEÑAL PRINCIPAL ===")
        self._dtmf_activating = True
        # Guardar estado del reproductor antes de activar señal
        self._was_playing_before_signal = self.engine.state == "playing"
        # 1. Detener Pauta Local si está activa
        if self._pauta_on:
            print("[DTMF→SIGNAL] Deteniendo Pauta Local...")
            self._pauta_on = False
            self.engine.stop()
            self._set_pauta_checked(False)
            self.btn_pauta.setStyleSheet("")
        
        # 2. Actualizar estado
        self._signal_on = True
        self._led_signal.set_on(True)
        self._sb_led.set_on(True)
        self.btn_signal.setChecked(True)
        t = _current_theme
        self.btn_signal.setStyleSheet(f"""
            QPushButton {{ background:{t['danger']};
                color:white; font-weight:bold; border-radius:6px; border:2px solid {t['danger']}; }}
        """)
        self._sb_state_lbl.setText("  ● En Aire  ")
        self._sb_state_lbl.setStyleSheet(f"color:{T('danger')}; font-weight:bold;")
        
        # 3. Iniciar passthrough directamente
        if self._restore_main_signal_from_monitor():
            self._wave.set_metadata("♪ SEÑAL PRINCIPAL: Audio en vivo  •  RadioSAT XP")
            print("[DTMF→SIGNAL] ✓ Señal Principal restaurada correctamente")
        else:
            in_dev = self._dtmf_dev_combo.currentData()
            out_dev = self._sd_out_dev_combo.currentData()
            print(f"[DTMF→SIGNAL] Dispositivos: in={in_dev}, out={out_dev}")
            if in_dev is not None and out_dev is not None:
                self.passthrough.set_devices(in_dev, out_dev)
                self.passthrough.set_muted(False)
                # DTMF ya está activo — ponerlo en modo externo (alimentado por passthrough)
                self._attach_dtmf_to_passthrough()
                self.passthrough.start()
                self._wave.set_metadata("♪ SEÑAL PRINCIPAL: Audio en vivo  •  RadioSAT XP")
                print("[DTMF→SIGNAL] ✓ Señal Principal activada correctamente")
            else:
                print("[DTMF→SIGNAL] ERROR: Dispositivos no configurados")
                self._apply_dtmf_display_style("danger", ">>> ERROR: CONFIGURA DISPOSITIVOS <<<")
        self._dtmf_activating = False

    def _on_dtmf_level(self, l: float, r: float):
        if len(self._vu_bars) >= 2:
            self._vu_bars[0].set_value(min(l, 1.0))
            self._vu_bars[1].set_value(min(r * 0.9, 1.0))

    def _on_dtmf_status(self, status: str):
        display_status = status
        if status.lower().startswith("rms=") or status.lower().startswith("detector: activo"):
            display_status = "Escuchando entrada DTMF" if self._dtmf_on else "Detector DTMF inactivo"
        elif status.upper().startswith("DTMF:"):
            display_status = f"Tono detectado: {status.split(':', 1)[1].strip()}"
        if hasattr(self, '_lbl_dtmf_state'):
            self._lbl_dtmf_state.setText(display_status)
        if hasattr(self, '_lbl_dtmf_status'):
            self._lbl_dtmf_status.setText(display_status)
        active = self._dtmf_on and "error" not in status.lower() and "inactiv" not in status.lower()
        if hasattr(self, '_dashboard_dtmf_led'):
            self._dashboard_dtmf_led.set_on(active)
            self._lbl_dtmf_status.setStyleSheet(
                f"font-size:13px;font-weight:700;color:{T('success') if active else T('text_secondary')};")
        if hasattr(self, '_header_dtmf_led'):
            self._header_dtmf_led.set_on(active)
            self._lbl_header_dtmf.setText("DTMF activo" if active else "DTMF inactivo")

    def _on_passthrough_level(self, l: float, r: float):
        if len(self._vu_bars) >= 2:
            self._vu_bars[0].set_value(min(l, 1.0))
            self._vu_bars[1].set_value(min(r * 0.9, 1.0))

    # ═══════════════════════════════════════════════════
    #  ACCIONES: REPRODUCTOR
    # ═══════════════════════════════════════════════════
    def _toggle_play_pause(self):
        if self.engine.state == "stopped":
            idx = self._table_playlist.currentRow()
            self.engine.play(idx if idx >= 0 else None)
        else:
            self.engine.pause()

    def _stop_playback(self):
        self.engine.stop()
        self._wave.set_idle()
        self._song_slider.setValue(0)
        self._lbl_pos.setText("0:00")

    def _playlist_double_click(self, index):
        self.engine.play(index.row())

    def _new_playlist(self):
        if self.engine.playlist and QMessageBox.question(
            self, "Nueva Playlist",
            "¿Descartar la playlist actual?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        self.engine.clear_playlist()
        self._table_playlist.setRowCount(0)
        self._lbl_current_track.setText("♪  Sin canción cargada")
        self._save_playlist_to_disk()
        self._sync_dashboard()

    def _add_to_playlist(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Añadir archivos de audio",
            str(Path.home() / "Music"),
            "Audio (*.mp3 *.wav *.ogg *.flac *.aac *.m4a *.wma);;Todos (*)"
        )
        for f in files:
            info = self.engine.add_file(f)
            if info:
                self._add_playlist_row(info)
        self._save_playlist_to_disk()

    def _add_paths_to_playlist(self, paths: list[str]):
        """Añade un drop a la pauta preparada y lo persiste de inmediato."""
        added = 0
        for path in paths:
            info = self.engine.add_file(path)
            if info:
                self._add_playlist_row(info)
                added += 1
        if added:
            self._save_playlist_to_disk()
            self._sync_dashboard()

    def _remove_from_playlist(self):
        row = self._table_playlist.currentRow()
        if row < 0:
            return
        self.engine.remove_index(row)
        self._table_playlist.removeRow(row)
        self._renumber_playlist()
        self._save_playlist_to_disk()
        self._sync_dashboard()

    def _open_playlist_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir Playlist", "",
            "Playlist M3U (*.m3u *.m3u8);;Todos (*)"
        )
        if not path:
            return
        self.engine.clear_playlist()
        self._table_playlist.setRowCount(0)
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Aceptar tanto archivos locales como URLs
                    is_url = line.startswith("http://") or line.startswith("https://")
                    if is_url or os.path.exists(line):
                        info = self.engine.add_file(line)
                        if info:
                            self._add_playlist_row(info)
        except Exception as e:
            self._show_error(str(e))
        self._sync_dashboard()

    def _save_playlist_file(self):
        if not self.engine.playlist:
            QMessageBox.information(self,"Playlist vacía","No hay canciones en la playlist.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Playlist", "playlist.m3u",
            "Playlist M3U (*.m3u)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for t in self.engine.playlist:
                    f.write(f"#EXTINF:-1,{t['artist']} - {t['title']}\n")
                    f.write(t["path"] + "\n")
        except Exception as e:
            self._show_error(str(e))

    def _add_playlist_row(self, info: dict):
        row = self._table_playlist.rowCount()
        self._table_playlist.insertRow(row)
        for col, val in enumerate([str(row + 1), info["artist"],
                                    info["title"], info["duration"], "En cola"]):
            item = QTableWidgetItem(val)
            item.setToolTip(info["path"])
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table_playlist.setItem(row, col, item)
        self._sync_dashboard()

    def _renumber_playlist(self):
        for r in range(self._table_playlist.rowCount()):
            item = self._table_playlist.item(r, 0)
            if item:
                item.setText(str(r + 1))

    def _on_seek_released(self):
        self._seeking = False
        pct = self._song_slider.value() / 1000.0
        self.engine.seek(pct)

    # ═══════════════════════════════════════════════════
    #  SEÑALES DEL MOTOR
    # ═══════════════════════════════════════════════════
    def _on_track_changed(self, idx: int, artist: str, title: str, duration: str):
        if hasattr(self, '_lbl_current_track'):
            self._lbl_current_track.setText(f"♪  {title}  –  {artist}  [{duration}]")
        if hasattr(self, '_lbl_dur'):
            self._lbl_dur.setText(duration)
        if hasattr(self, '_sb_track_lbl'):
            self._sb_track_lbl.setText(f"  ▶ {artist} – {title}  ")
        # Actualizar estado en tabla de pauta
        if hasattr(self, '_pauta_table'):
            t = _current_theme
            for r in range(self._pauta_table.rowCount()):
                st_item = self._pauta_table.item(r, 4)
                if st_item:
                    if r == idx:
                        st_item.setText("▶ Reproduciendo")
                        st_item.setBackground(QBrush(QColor(t["accent"]).lighter(180)))
                    elif r < idx:
                        st_item.setText("✓ Emitido")
                        st_item.setBackground(QBrush(QColor(t["bg_surface_alt"])))
                    else:
                        st_item.setText("Preparado")
                        st_item.setBackground(QBrush(QColor(0,0,0,0)))

    def _on_playback_state(self, state: str):
        if hasattr(self, 'btn_play'):
            if state == "playing":
                self.btn_play.setIcon(QIcon(xp_pixmap("Pause.png", 16)))
            elif state == "paused":
                self.btn_play.setIcon(QIcon(xp_pixmap("Play.png", 16)))
            else:
                self.btn_play.setIcon(QIcon(xp_pixmap("Play.png", 16)))
        if hasattr(self, '_lbl_on_air'):
            self._lbl_on_air.setVisible(state == "playing")
        if hasattr(self, '_wave'):
            if state == "paused":
                self._wave._active = False
            elif state == "stopped":
                self._wave.set_idle()
        if hasattr(self, '_pauta_table') and state == "stopped":
            for r in range(self._pauta_table.rowCount()):
                st = self._pauta_table.item(r, 4)
                if st and st.text() == "▶ Reproduciendo":
                    st.setText("Preparado")
                    st.setBackground(QBrush(QColor(0,0,0,0)))
        if state == "playing":
            self._set_dashboard_source("AL AIRE · PAUTA LOCAL", "Fuente: reproductor local",
                                       "La pauta local se transmite a la audiencia")
        elif state == "stopped" and not self._signal_on and not self._remote_on:
            self._set_dashboard_source("SIN FUENTE CONFIRMADA", "Fuente: sin datos",
                                       "Configura o activa una fuente de programa")

    def _on_position_tick(self, ms_cur: int, ms_total: int):
        if self._seeking:
            return
        if hasattr(self, '_song_slider') and ms_total > 0:
            pct = ms_cur / ms_total
            self._song_slider.setValue(int(pct * 1000))
        if hasattr(self, '_lbl_pos'):
            secs = ms_cur // 1000
            self._lbl_pos.setText(f"{secs//60}:{secs%60:02d}")

    def _on_engine_level(self, l: float, r: float):
        if len(self._vu_bars) >= 2:
            self._vu_bars[0].set_value(l)
            self._vu_bars[1].set_value(r)
        if hasattr(self, '_wave'):
            self._wave.push_level((l + r) / 2)
        if hasattr(self, '_vu_output') and len(self._vu_output) >= 2:
            self._vu_output[0].set_value(l)
            self._vu_output[1].set_value(r)

    # ═══════════════════════════════════════════════════
    #  ACCIONES: BIBLIOTECA
    # ═══════════════════════════════════════════════════
    def _add_streaming_url(self):
        url, ok = QInputDialog.getText(self, "Añadir URL Streaming", "Introduce la URL de la señal de streaming:")
        if ok and url.strip():
            url = url.strip()
            # Evitar duplicados
            for r in range(self._table_library.rowCount()):
                item = self._table_library.item(r, 5)
                if item and item.text() == url:
                    return
            row = self._table_library.rowCount()
            self._table_library.insertRow(row)
            vals = ["Streaming", "Web Radio", "Internet", "∞", "", url]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setToolTip(url)
                self._table_library.setItem(row, c, item)
            self._lbl_lib_count.setText(f"  {self._table_library.rowCount()} archivos")
            self._save_library_to_disk()
            self._sync_dashboard()

    def _add_audio_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Añadir archivos de audio a la biblioteca",
            str(Path.home() / "Music"),
            "Audio (*.mp3 *.wav *.ogg *.flac *.aac *.m4a *.wma);;Todos (*)"
        )
        for f in files:
            self._add_to_library(f)

    def _import_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Importar carpeta de audio", str(Path.home() / "Music"))
        if not folder:
            return
        exts = {".mp3",".wav",".ogg",".flac",".aac",".m4a",".wma"}
        count = 0
        for root, _, files in os.walk(folder):
            for fn in files:
                if Path(fn).suffix.lower() in exts:
                    self._add_to_library(os.path.join(root, fn))
                    count += 1
        if count:
            QMessageBox.information(self, "Importación completa",
                f"Se importaron {count} archivos.")

    def _add_to_library(self, path: str):
        # Evitar duplicados
        for r in range(self._table_library.rowCount()):
            item = self._table_library.item(r, 5)
            if item and item.text() == path:
                return

        info = self.engine._read_tags(path)
        if not info:
            return
        row = self._table_library.rowCount()
        self._table_library.insertRow(row)
        vals = [info["artist"], info["title"], "", info["duration"],
                "", path]
        # Intentar álbum y año con mutagen
        if MUTAGEN_OK:
            try:
                tag = MutagenFile(path)
                if tag:
                    vals[2] = str(tag.get("TALB", tag.get("album",  [""]))[0])
                    vals[4] = str(tag.get("TDRC", tag.get("date",   [""]))[0])
            except Exception:
                pass
        for c, v in enumerate(vals):
            item = QTableWidgetItem(v)
            item.setToolTip(path)
            self._table_library.setItem(row, c, item)
        self._lbl_lib_count.setText(f"  {self._table_library.rowCount()} archivos")
        self._save_library_to_disk()
        self._sync_dashboard()

    def _del_from_library(self):
        row = self._table_library.currentRow()
        if row >= 0:
            self._table_library.removeRow(row)
            self._lbl_lib_count.setText(f"  {self._table_library.rowCount()} archivos")
            self._save_library_to_disk()
            self._sync_dashboard()

    def _clear_library(self):
        if QMessageBox.question(self, "Limpiar Biblioteca",
            "¿Eliminar todos los elementos de la biblioteca?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self._table_library.setRowCount(0)
            self._lbl_lib_count.setText("  0 archivos")
            self._save_library_to_disk()
            self._sync_dashboard()

    def _library_double_click(self, index):
        row = index.row()
        path_item = self._table_library.item(row, 5)
        if path_item:
            info = self.engine.add_file(path_item.text())
            if info:
                self._add_playlist_row(info)
                self._save_playlist_to_disk()

    def _add_lib_to_playlist(self):
        rows = set(i.row() for i in self._table_library.selectedIndexes())
        for row in sorted(rows):
            path_item = self._table_library.item(row, 5)
            if path_item:
                info = self.engine.add_file(path_item.text())
                if info:
                    self._add_playlist_row(info)
        self._save_playlist_to_disk()

    def _filter_library(self, text: str):
        col_map = {"Todos": -1, "Artista": 0, "Título": 1, "Álbum": 2}
        col = col_map.get(self._filter_combo.currentText(), -1)
        text = text.lower()
        for r in range(self._table_library.rowCount()):
            if not text:
                self._table_library.setRowHidden(r, False)
                continue
            match = False
            cols = range(5) if col == -1 else [col]
            for c in cols:
                item = self._table_library.item(r, c)
                if item and text in item.text().lower():
                    match = True
                    break
            self._table_library.setRowHidden(r, not match)

    # ═══════════════════════════════════════════════════
    #  ACCIONES: PAUTAS
    # ═══════════════════════════════════════════════════
    def _new_pauta(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar audio para pauta",
            str(Path.home() / "Music"),
            "Audio (*.mp3 *.wav *.ogg *.flac);;Todos (*)"
        )
        for f in files:
            info = self.engine._read_tags(f)
            if not info:
                continue
            cliente, ok = QInputDialog.getText(self, "Nueva Pauta", "Nombre del cliente:")
            if not ok:
                cliente = "Sin cliente"
            spot, ok2 = QInputDialog.getText(self, "Nueva Pauta", "Nombre del spot:")
            if not ok2:
                spot = Path(f).stem

            self._insert_pauta_row(f, cliente, spot, info["duration"], "18:00, 20:00", "L-V")
        self._save_pautas_to_disk()

    def _insert_pauta_row(self, path: str, cliente: str, spot: str,
                          duration: str, horario: str = "", dias: str = ""):
        table = self._table_pautas
        previous = table.blockSignals(True)
        try:
            row = table.rowCount()
            table.insertRow(row)
            values = [Path(path).name, cliente, spot, duration, horario, dias, path]
            for column, value in enumerate(values[:table.columnCount()]):
                item = QTableWidgetItem(str(value))
                item.setToolTip(path)
                table.setItem(row, column, item)
        finally:
            table.blockSignals(previous)

    def _add_paths_to_pautas(self, paths: list[str]):
        """Crea pautas editables al soltar audios desde biblioteca o Finder."""
        added = 0
        existing = {
            self._table_pautas.item(row, 6).text()
            for row in range(self._table_pautas.rowCount())
            if self._table_pautas.columnCount() > 6 and self._table_pautas.item(row, 6)
        }
        for path in paths:
            if path in existing:
                continue
            info = self.engine._read_tags(path)
            if not info:
                continue
            artist = info.get("artist", "")
            cliente = "" if artist in ("", "Desconocido") else artist
            self._insert_pauta_row(
                path, cliente, info.get("title") or Path(path).stem,
                info.get("duration", "0:00")
            )
            existing.add(path)
            added += 1
        if added:
            self._save_pautas_to_disk()

    def _on_pauta_item_changed(self, _item):
        self._save_pautas_to_disk()

    def _del_pauta(self):
        row = self._table_pautas.currentRow()
        if row >= 0:
            self._table_pautas.removeRow(row)
            self._save_pautas_to_disk()

    # ═══════════════════════════════════════════════════
    #  ACCIONES: AUDIO / MIC
    # ═══════════════════════════════════════════════════
    def _toggle_mic(self, checked: bool):
        self._mic_on = checked
        self._update_mic_style(checked)
        # Actualizar texto e ícono XP del botón
        self.btn_mic.setText(" ON" if checked else " OFF")
        _px_v = xp_pixmap("Volume.png", 18)
        if not _px_v.isNull():
            self.btn_mic.setIcon(QIcon(_px_v))
            self.btn_mic.setIconSize(QSize(18, 18))
        # sounddevice: no hay API directa de mute; sólo actualizamos UI
        if checked:
            if len(self._vu_bars) >= 1:
                self._vu_bars[0].set_value(0.5)
        else:
            if len(self._vu_bars) >= 1:
                self._vu_bars[0].set_value(0.0)

    def _update_mic_style(self, on: bool):
        t = _current_theme
        if on:
            self.btn_mic.setStyleSheet(f"""
                QPushButton {{
                    background:{t['success']};
                    color:white; font-weight:bold; border-radius:6px;
                    border:2px solid {t['success']};
                }}
            """)
        else:
            self.btn_mic.setStyleSheet(f"""
                QPushButton {{
                    background:{t['bg_surface']};
                    color:{t['text_secondary']}; font-weight:bold; border-radius:6px;
                    border:1px solid {t['border']};
                }}
                QPushButton:hover {{ background:{t['bg_hover']}; color:{t['text']}; }}
            """)

    def _populate_mic_sources(self):
        self._mic_src_combo.clear()
        if SOUND_OK:
            try:
                for i, d in enumerate(sd.query_devices()):
                    if d["max_input_channels"] > 0 and _is_real_audio_device(d):
                        ch = d["max_input_channels"]
                        tag = " [Stereo]" if ch >= 2 else " [Mono]"
                        self._mic_src_combo.addItem(f"{d['name']}{tag}", i)
            except Exception:
                pass
        if self._mic_src_combo.count() == 0:
            self._mic_src_combo.addItem("(sin dispositivos)", None)

    # ═══════════════════════════════════════════════════
    #  TTS (deshabilitado - widgets removidos)
    # ═══════════════════════════════════════════════════
    def _speak_tts(self):
        pass

    # ═══════════════════════════════════════════════════
    #  VU DEMO (fallback cuando no hay audio real)
    # ═══════════════════════════════════════════════════
    def _demo_vu_tick(self):
        if self.engine.state == "playing":
            return  # el motor real alimenta los VU
        if self._dtmf_on and SOUND_OK:
            return  # DTMF real alimenta VU
        # Animación demo suave
        for i, vb in enumerate(self._vu_bars):
            phase = time.time() * (1.3 + i * 0.4)
            v = max(0.0, 0.15 * abs(math.sin(phase)) + 0.05 * random.random())
            vb.set_value(v)

    # ═══════════════════════════════════════════════════
    #  MENÚ: ARCHIVO
    # ═══════════════════════════════════════════════════
    def _new_project(self):
        if QMessageBox.question(
            self,"Nuevo Proyecto","¿Descartar el proyecto actual?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.engine.clear_playlist()
            self._table_playlist.setRowCount(0)
            self._table_library.setRowCount(0)
            self._lbl_lib_count.setText("  0 archivos")
            self._lbl_current_track.setText("♪  Sin canción cargada")

    def _open_project(self):
        self._open_playlist_file()

    def _save_project(self):
        self._save_playlist_file()

    def _delete_selected(self):
        """Eliminar de tabla activa."""
        self._remove_from_playlist()

    def _config_audio(self):
        self._refresh_devices()
        self._populate_mic_sources()
        QMessageBox.information(self,"Dispositivos actualizados",
            "Lista de dispositivos de audio actualizada.")

    def _toggle_theme(self):
        dark = self._theme_action.isChecked()
        set_theme(dark)
        QApplication.instance().setStyleSheet(generate_qss())
        # Refresh theme-dependent widgets
        self._apply_dtmf_display_style()
        self._update_mic_style(self._mic_on)
        self._led_onair.update()
        self._led_signal.update()
        self._led_dtmf.update()
        for vb in self._vu_bars:
            vb.update()
        self._wave.update()
        clock_background = T('surface_raised') if _current_theme is THEME_LIGHT else T('clock_bg')
        self._clock.setStyleSheet(f"""
            QLabel#liveClock {{
                background: {clock_background};
                color: {T('text_primary')};
                border: 1px solid {T('border')};
                border-radius: 5px;
                padding: 6px 14px;
                font-size: 28px;
                font-weight: 700;
            }}
        """)

    def _about(self):
        QMessageBox.about(self,"Acerca de Radio XP Automator",
            "<b>Radio XP Automator</b><br>"
            "Suite de Automatización de Radio<br><br>"
            "Características:<br>"
            "• Reproducción de audio (pygame)<br>"
            "• Detección DTMF en tiempo real (sounddevice + numpy)<br>"
            "• Gestor de playlist y biblioteca<br>"
            "• Control de micrófono<br>"
            "• Texto a Voz (pyttsx3)<br>"
            "• Íconos Windows XP originales<br><br>"
            "Construido con PyQt6")

    def _show_error(self, msg: str):
        QMessageBox.critical(self,"Error", msg)

    def closeEvent(self, event):
        # Guardar datos antes de cerrar
        self._save_library_to_disk()
        self._save_pautas_to_disk()
        self._save_remotes_to_disk()
        self._save_playlist_to_disk()
        self._save_settings_to_disk()
        self.remote_dtmf.stop()
        self.remote_engine.stop()
        self.dtmf.stop()
        self.passthrough.stop()
        self.engine.stop()
        event.accept()

    # ═══════════════════════════════════════════════════
    #  PERSISTENCIA DE DATOS
    # ═══════════════════════════════════════════════════
    def _get_data_dir(self) -> str:
        if getattr(sys, 'frozen', False):
            data_dir = os.path.join(os.path.expanduser("~"), ".radiosat")
        else:
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def _write_json_atomic(self, filename: str, data):
        """Evita archivos JSON incompletos si la aplicación se interrumpe."""
        import json
        path = os.path.join(self._get_data_dir(), filename)
        temporary = path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)

    def _save_settings_to_disk(self):
        settings = {
            "dtmf_dev": self._dtmf_dev_combo.currentText(),
            "sd_out_dev": self._sd_out_dev_combo.currentText(),
            "out_dev": self._out_dev_combo.currentText(),
            "remote_out_dev": self._remote_out_dev_combo.currentText(),
            "dtmf_seq_play": getattr(self, '_dtmf_seq_play', None) and self._dtmf_seq_play.text() or "",
            "dtmf_seq_stop": getattr(self, '_dtmf_seq_stop', None) and self._dtmf_seq_stop.text() or "",
            "theme": getattr(self, '_theme_action', None) and self._theme_action.isChecked() or True
        }
        self._write_json_atomic("settings.json", settings)

    def _load_settings_from_disk(self):
        import json
        path = os.path.join(self._get_data_dir(), "settings.json")
        if not os.path.exists(path): return
        try:
            with open(path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            
            for combo, key in [
                (self._dtmf_dev_combo, "dtmf_dev"),
                (self._sd_out_dev_combo, "sd_out_dev"),
                (self._out_dev_combo, "out_dev"),
                (self._remote_out_dev_combo, "remote_out_dev"),
            ]:
                text = settings.get(key, "")
                if text:
                    idx = combo.findText(text)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                        
            if "dtmf_seq_play" in settings and hasattr(self, '_dtmf_seq_play'):
                self._dtmf_seq_play.setText(settings["dtmf_seq_play"])
            if "dtmf_seq_stop" in settings and hasattr(self, '_dtmf_seq_stop'):
                self._dtmf_seq_stop.setText(settings["dtmf_seq_stop"])
            
            if "theme" in settings and hasattr(self, '_theme_action'):
                if self._theme_action.isChecked() != settings["theme"]:
                    self._theme_action.setChecked(settings["theme"])
                    self._toggle_theme()
                    
        except Exception as e:
            print(f"Error loading settings: {e}")

    def _save_library_to_disk(self):
        import json
        try:
            items = []
            for r in range(self._table_library.rowCount()):
                row_data = {}
                for c in range(self._table_library.columnCount()):
                    item = self._table_library.item(r, c)
                    header = self._table_library.horizontalHeaderItem(c)
                    if item and header:
                        row_data[header.text()] = item.text()
                if row_data:
                    items.append(row_data)
            
            self._write_json_atomic("library.json", items)
        except Exception as e:
            print(f"Error guardando biblioteca: {e}")

    def _save_pautas_to_disk(self):
        try:
            if not hasattr(self, "_table_pautas"):
                return
            headers = ["Archivo", "Cliente", "Spot", "Duración", "Horario", "Días", "Ruta"]
            items = []
            for row in range(self._table_pautas.rowCount()):
                values = {}
                for column, header in enumerate(headers[:self._table_pautas.columnCount()]):
                    item = self._table_pautas.item(row, column)
                    values[header] = item.text() if item else ""
                if values.get("Archivo"):
                    items.append(values)
            self._write_json_atomic("pautas.json", items)
        except Exception as e:
            print(f"Error guardando pautas: {e}")

    def _load_pautas_from_disk(self):
        import json
        path = os.path.join(self._get_data_dir(), "pautas.json")
        if not os.path.exists(path) or not hasattr(self, "_table_pautas"):
            return
        try:
            with open(path, encoding="utf-8") as handle:
                items = json.load(handle)
            previous = self._table_pautas.blockSignals(True)
            try:
                for values in items:
                    ruta = values.get("Ruta", "")
                    is_url = ruta.startswith("http://") or ruta.startswith("https://")
                    if ruta and not is_url and not os.path.exists(ruta):
                        continue
                    self._insert_pauta_row(
                        ruta or values.get("Archivo", ""), values.get("Cliente", ""),
                        values.get("Spot", ""), values.get("Duración", ""),
                        values.get("Horario", ""), values.get("Días", "")
                    )
            finally:
                self._table_pautas.blockSignals(previous)
        except Exception as e:
            print(f"Error cargando pautas: {e}")

    def _load_library_from_disk(self):
        import json
        path = os.path.join(self._get_data_dir(), "library.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as f:
                items = json.load(f)
            
            headers = ["Artista","Título","Álbum","Duración","Año","Ruta"]
            for row_data in items:
                # Verificar que el archivo o URL siga existiendo
                ruta = row_data.get("Ruta", "")
                is_url = ruta.startswith("http://") or ruta.startswith("https://")
                if not is_url and not os.path.exists(ruta):
                    continue
                
                row = self._table_library.rowCount()
                self._table_library.insertRow(row)
                for c, h in enumerate(headers):
                    val = row_data.get(h, "")
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self._table_library.setItem(row, c, item)
            
            self._lbl_lib_count.setText(f"  {self._table_library.rowCount()} archivos")
        except Exception as e:
            print(f"Error cargando biblioteca: {e}")

    def _save_remotes_to_disk(self):
        import json
        try:
            data = {
                "main_signal_url": self._main_signal_url,
                "remote_url": None
            }
            # Guardar URL del stream remoto si está configurado
            if hasattr(self, '_remote_url_edit'):
                data["remote_url"] = self._remote_url_edit.text().strip() or None
            
            path = os.path.join(self._get_data_dir(), "remotes.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error guardando streams remotos: {e}")

    def _load_remotes_from_disk(self):
        import json
        path = os.path.join(self._get_data_dir(), "remotes.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            
            # Restaurar URL de señal principal
            url = data.get("main_signal_url")
            if url and hasattr(self, '_signal_url_edit'):
                self._signal_url_edit.setText(url)
            
            # Restaurar URL de stream remoto
            remote_url = data.get("remote_url")
            if remote_url and hasattr(self, '_remote_url_edit'):
                self._remote_url_edit.setText(remote_url)
        except Exception as e:
            print(f"Error cargando streams remotos: {e}")

    def _save_playlist_to_disk(self):
        import json
        try:
            items = []
            for t in self.engine.playlist:
                items.append({
                    "path": t.get("path", ""),
                    "artist": t.get("artist", ""),
                    "title": t.get("title", ""),
                    "duration": t.get("duration", ""),
                    "duration_ms": t.get("duration_ms", 0)
                })
            
            self._write_json_atomic("playlist.json", items)
        except Exception as e:
            print(f"Error guardando playlist: {e}")

    def _load_playlist_from_disk(self):
        import json
        path = os.path.join(self._get_data_dir(), "playlist.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as f:
                items = json.load(f)

            for item in items:
                ruta = item.get("path", "")
                is_url = ruta.startswith("http://") or ruta.startswith("https://")
                if not is_url and not os.path.exists(ruta):
                    continue
                info = self.engine.add_file(ruta)
                if info:
                    self._add_playlist_row(info)
        except Exception as e:
            print(f"Error cargando playlist: {e}")

    # ═══════════════════════════════════════════════════
    #  ENCODER / STREAMING
    # ═══════════════════════════════════════════════════
    def _config_encoder(self):
        dialog = EncoderSettingsDialog(self, self._encoder_settings)
        if dialog.exec():
            self._encoder_settings = dialog.get_settings()
            self._save_encoder_settings()
            if self._encoder_on:
                self._stop_encoder()
                self._start_encoder()

    def _toggle_encoder(self, checked):
        if checked:
            if not self._encoder_settings:
                self._load_encoder_settings()
            if not self._encoder_settings.get('host') or not self._encoder_settings.get('password'):
                QMessageBox.warning(self, "Encoder",
                    "Configura el encoder primero (Configuración → Configurar Encoder)")
                self.btn_encoder.setChecked(False)
                return
            self._start_encoder()
        else:
            self._stop_encoder()

    def _start_encoder(self):
        s = self._encoder_settings
        if not s:
            return

        loopback_dev = self._resolve_loopback_device(s)
        if loopback_dev is None:
            self._show_error("No se encontró el dispositivo que contiene el bus de programa. "
                             "Abre Configurar encoder y selecciona el loopback nuevamente.")
            self.btn_encoder.setChecked(False)
            return

        self.loopback.set_device(loopback_dev)
        self.loopback.set_sample_rate(s.get('samplerate', 44100))
        self.loopback.set_channels(s.get('channels', 2))

        codec = s.get('codec', 'Opus').lower()
        bitrate = s.get('bitrate', 128)
        samplerate = s.get('samplerate', 44100)
        channels = s.get('channels', 2)

        self.encoder.set_codec(codec)
        self.encoder.set_bitrate(bitrate)
        self.encoder.set_sample_rate(samplerate)
        self.encoder.set_channels(channels)

        server_type = s.get('server_type', 'icecast')
        self.stream_client.set_server(
            s.get('host', ''),
            s.get('port', 8000),
            s.get('mount', '/live'),
            s.get('username', 'source'),
            s.get('password', ''),
            server_type,
            "audio/mpeg" if codec == "mp3" else "audio/ogg"
        )
        self.stream_client.set_metadata(
            s.get('name', 'RadioSAT XP'),
            s.get('genre', 'Various'),
            s.get('description', '')
        )

        self.loopback.start()
        self.encoder.start()
        self.stream_client.start()

        self._encoder_on = True
        self._led_encoder.set_on(True)
        self._update_encoder_style(True)
        if hasattr(self, '_lbl_enc_info'):
            ch_str = "Stereo" if channels == 2 else "Mono"
            self._lbl_enc_info.setText(f"{codec.upper()} @ {bitrate}kbps | {samplerate}Hz | {ch_str}")
        if hasattr(self, '_lbl_enc_status'):
            self._lbl_enc_status.setText("Conectando...")
            self._lbl_enc_status.setStyleSheet(f"color:{T('warning')}; font-size:8pt;")
        print("[Encoder] Iniciado")

    def _resolve_loopback_device(self, settings: dict):
        """Resuelve por nombre para no depender de índices PortAudio cambiantes."""
        device_id = settings.get("loopback_device")
        saved_name = settings.get("loopback_device_name", "").replace("[Loopback] ", "")
        if not SOUND_OK:
            return None
        try:
            devices = sd.query_devices()
            if saved_name:
                for index, device in enumerate(devices):
                    if device.get("max_input_channels", 0) > 0 and device.get("name", "") == saved_name:
                        settings["loopback_device"] = index
                        return index
            if isinstance(device_id, int) and 0 <= device_id < len(devices):
                if devices[device_id].get("max_input_channels", 0) > 0:
                    return device_id
        except Exception as error:
            print(f"[Loopback] No se pudo resolver el dispositivo: {error}")
        return None

    def _stop_encoder(self):
        self.loopback.stop()
        self.encoder.stop()
        self.stream_client.stop()
        self._encoder_on = False
        self._led_encoder.set_on(False)
        self.btn_encoder.setChecked(False)
        self._update_encoder_style(False)
        if hasattr(self, '_lbl_enc_info'):
            self._lbl_enc_info.setText("—")
        if hasattr(self, '_lbl_enc_status'):
            self._lbl_enc_status.setText("Detenido")
            self._lbl_enc_status.setStyleSheet(f"color:{T('text_dim')}; font-size:8pt;")
        print("[Encoder] Detenido")

    def _on_loopback_audio(self, data: bytes):
        if self._encoder_on:
            self.encoder.write_pcm(data)

    def _on_encoded_data(self, data: bytes):
        if self._encoder_on:
            self.stream_client.send_data(data)

    def _set_encoder_feedback(self, text: str, color_key: str = "warning"):
        for name in ("_lbl_enc_status", "_lbl_encoder_status", "_lbl_stream_status"):
            label = getattr(self, name, None)
            if label is not None:
                label.setText(text)
                label.setStyleSheet(f"color:{T(color_key)};font-size:9pt;")

    def _on_loopback_error(self, message: str):
        print(f"[Loopback] {message}")
        self._set_encoder_feedback("Sin audio del bus de programa", "danger")
        if self._encoder_on:
            self._stop_encoder()
        QMessageBox.critical(self, "Captura del programa", message)

    def _on_encoder_error(self, message: str):
        print(f"[Encoder] {message}")
        self._set_encoder_feedback("Error de codificación", "danger")
        QMessageBox.critical(self, "Encoder", message)

    def _on_stream_error(self, message: str):
        print(f"[Stream] {message}")
        self._set_encoder_feedback("No conectado a Icecast", "danger")

    def _on_stream_bytes(self, _chunk_size: int):
        total = self.stream_client.total_bytes_sent
        if total < 1024:
            amount = f"{total} B"
        elif total < 1024 * 1024:
            amount = f"{total / 1024:.1f} KB"
        else:
            amount = f"{total / (1024 * 1024):.1f} MB"
        text = f"Conectado · {amount} enviados"
        for name in ("_lbl_enc_status", "_lbl_encoder_status"):
            label = getattr(self, name, None)
            if label is not None:
                label.setText(text)
                label.setStyleSheet(f"color:{T('success')};font-size:9pt;")

    def _on_encoder_status(self, status: str):
        print(f"[Encoder] {status}")
        if hasattr(self, '_lbl_enc_status'):
            self._lbl_enc_status.setText(status)
        if hasattr(self, '_lbl_encoder_status'):
            self._lbl_encoder_status.setText(status)

    def _on_stream_connected(self):
        self._led_encoder.set_on(True)
        self._update_encoder_style(True)
        if hasattr(self, '_lbl_enc_status'):
            self._lbl_enc_status.setText("Conectado")
            self._lbl_enc_status.setStyleSheet(f"color:{T('success')}; font-size:8pt;")
        if hasattr(self, '_lbl_encoder_status'):
            self._lbl_encoder_status.setText("Conectado")
            self._lbl_encoder_status.setStyleSheet(f"color: {T('success')}; font-size: 9pt;")
        if hasattr(self, '_lbl_stream_status'):
            self._lbl_stream_status.setText("Streaming conectado")
            self._lbl_stream_status.setStyleSheet(f"color: {T('text_primary')}; font-size: 10pt;")
        if hasattr(self, '_dashboard_encoder_led'):
            self._dashboard_encoder_led.set_on(True)
        if hasattr(self, '_header_stream_led'):
            self._header_stream_led.set_on(True)
        print("[Stream] Conectado al servidor")

    def _on_stream_disconnected(self):
        self._led_encoder.set_on(False)
        self._update_encoder_style(False)
        if hasattr(self, '_lbl_enc_status'):
            self._lbl_enc_status.setText("Detenido")
            self._lbl_enc_status.setStyleSheet(f"color:{T('text_dim')}; font-size:8pt;")
        if hasattr(self, '_lbl_encoder_status'):
            self._lbl_encoder_status.setText("Desconectado")
            self._lbl_encoder_status.setStyleSheet(f"color: {T('text_secondary')}; font-size: 9pt;")
        if hasattr(self, '_lbl_stream_status'):
            self._lbl_stream_status.setText("Encoder desconectado")
            self._lbl_stream_status.setStyleSheet(f"color: {T('text_secondary')}; font-size: 10pt;")
        if hasattr(self, '_dashboard_encoder_led'):
            self._dashboard_encoder_led.set_on(False)
        if hasattr(self, '_header_stream_led'):
            self._header_stream_led.set_on(False)
        print("[Stream] Desconectado del servidor")
        self._led_encoder.set_on(False)
        self._update_encoder_style(False)
        if hasattr(self, '_lbl_enc_status'):
            self._lbl_enc_status.setText("Desconectado")
            self._lbl_enc_status.setStyleSheet(f"color:{T('text_dim')}; font-size:8pt;")
        print("[Stream] Desconectado del servidor")

    def _on_stream_status(self, status: str):
        print(f"[Stream] {status}")
        if hasattr(self, '_lbl_enc_status'):
            self._lbl_enc_status.setText(status)

    def _save_encoder_settings(self):
        import json
        try:
            path = os.path.join(self._get_data_dir(), "encoder.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._encoder_settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error guardando configuración encoder: {e}")

    def _load_encoder_settings(self):
        import json
        path = os.path.join(self._get_data_dir(), "encoder.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as f:
                self._encoder_settings = json.load(f)
        except Exception as e:
            print(f"Error cargando configuración encoder: {e}")

    # ══════════════════════════════════════════════════════════════════════════════
    #  RADIO XP DASHBOARD — implementación visual final
    #  Estas definiciones sustituyen las primeras versiones del rediseño y
    #  mantienen los paneles operativos originales en las vistas secundarias.
    # ═════════════════════════════════════════════════════════════════════════════

    def _setup_menus(self):
        """Conserva las acciones históricas sin añadir chrome sobre la consola."""
        mb = self.menuBar()
        m_arch = mb.addMenu("Archivo")
        m_arch.addAction(xp_icon("NewFolder.png"), "Nuevo proyecto", self._new_project)
        m_arch.addAction(xp_icon("Open.png"), "Abrir proyecto…", self._open_project)
        m_arch.addAction(xp_icon("Save.png"), "Guardar proyecto", self._save_project)
        m_arch.addSeparator()
        m_arch.addAction("Salir", self.close)
        m_bib = mb.addMenu("Biblioteca")
        m_bib.addAction(xp_icon("Add.png"), "Añadir audios…", self._add_audio_files)
        m_bib.addAction(xp_icon("Open.png"), "Importar carpeta…", self._import_folder)
        m_cfg = mb.addMenu("Configuración")
        m_cfg.addAction(xp_icon("AudioDevices.png"), "Dispositivos de audio…", self._config_audio)
        m_cfg.addAction(xp_icon("Chip.png"), "Configurar encoder…", self._config_encoder)
        self._theme_action = m_cfg.addAction("Tema oscuro")
        self._theme_action.setCheckable(True)
        self._theme_action.setChecked(True)
        self._theme_action.triggered.connect(self._toggle_theme)
        mb.hide()

    def _setup_statusbar(self):
        # La referencia usa una única barra de estado integrada.
        self._ensure_status_contract()
        self.statusBar().hide()

    def _ensure_status_contract(self):
        """Crea siempre los receptores usados por los controladores antiguos."""
        status_bar = self.statusBar()
        if not hasattr(self, "_sb_led"):
            self._sb_led = LEDIndicator(QColor(255,30,30), status_bar)
            self._sb_led.hide()
        for name, text in (
            ("_sb_dtmf_lbl", "DTMF: inactivo"),
            ("_sb_track_lbl", "Sin reproducción"),
            ("_sb_state_lbl", "● Listo"),
        ):
            if not hasattr(self, name):
                label = QLabel(text, status_bar)
                label.hide()
                setattr(self, name, label)

    def _setup_ui(self):
        self._ensure_status_contract()
        if hasattr(self, "_dashboard_timer"):
            self._dashboard_timer.stop()
            self._dashboard_timer.deleteLater()
        central = QWidget()
        central.setObjectName("radioRoot")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)
        body_lay.addWidget(self._build_navigation())
        workspace = QWidget()
        workspace_lay = QVBoxLayout(workspace)
        workspace_lay.setContentsMargins(0, 0, 0, 0)
        workspace_lay.setSpacing(0)
        workspace_lay.addWidget(self._build_header())
        self._content_area = QStackedWidget()
        workspace_lay.addWidget(self._content_area, 1)
        body_lay.addWidget(workspace, 1)
        root.addWidget(body, 1)
        root.addWidget(self._build_statusbar_bottom())

        # Las vistas completas se construyen primero: crean todos los controles
        # de la aplicación original. Emisión se construye al final para que sus
        # indicadores sean los que reciben las actualizaciones en tiempo real.
        self._page_pautas = self._build_pautas_page()
        self._page_biblioteca = self._build_biblioteca_page()
        self._page_dtmf = self._build_dtmf_page()
        self._page_registro = self._build_registro_page()
        self._page_dispositivos = self._build_dispositivos_page()
        self._page_emision = self._build_emision_page()
        for page in (self._page_emision, self._page_pautas, self._page_biblioteca,
                     self._page_dtmf, self._page_registro, self._page_dispositivos):
            self._content_area.addWidget(page)
        self._content_area.setCurrentIndex(0)

        self._dashboard_timer = QTimer(self)
        self._dashboard_timer.timeout.connect(self._update_dashboard_clock)
        self._dashboard_timer.start(1000)
        self._update_dashboard_clock()

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("operationBar")
        header.setFixedHeight(58)
        header.setStyleSheet(f"""
            QWidget#operationBar {{ background:{T('surface')}; border-bottom:1px solid {T('border')}; }}
            QLabel {{ border:none; background:transparent; }}
        """)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(0, 0, 18, 0)
        lay.setSpacing(0)

        title_box = QWidget()
        title_box.setFixedWidth(700)
        title_lay = QHBoxLayout(title_box)
        title_lay.setContentsMargins(14, 0, 0, 0)
        title_lay.setSpacing(14)
        divider = QFrame()
        divider.setFixedSize(1, 24)
        divider.setStyleSheet(f"background:{T('border')};")
        title_lay.addWidget(divider)
        station = QLabel("RADIO LOCAL")
        station.setStyleSheet(f"font-size:20px; font-weight:700; color:{T('text_primary')};")
        title_lay.addWidget(station)
        context = QLabel("Control de emisión")
        context.setStyleSheet(f"font-size:13px; color:#9FC9EC;")
        title_lay.addWidget(context)
        title_lay.addStretch()
        lay.addWidget(title_box)
        lay.addStretch()

        self._btn_automatic = QPushButton("▶  AUTOMÁTICO")
        self._btn_automatic.setCheckable(True)
        self._btn_automatic.setFixedSize(126, 36)
        self._btn_automatic.setStyleSheet(f"""
            QPushButton {{ color:{T('success')}; background:#0D211B; border:1px solid #246845;
                border-radius:5px; font-size:12px; font-weight:700; min-height:0; padding:0; }}
            QPushButton:checked {{ background:#0A4A2C; border-color:{T('success')}; }}
        """)
        self._btn_automatic.toggled.connect(
            lambda on: self.btn_dtmf_main.setChecked(on) if hasattr(self, "btn_dtmf_main") else None)
        lay.addWidget(self._btn_automatic)
        lay.addSpacing(20)

        self._header_dtmf_led, self._lbl_header_dtmf = self._header_status("DTMF inactivo")
        lay.addWidget(self._header_dtmf_led)
        lay.addSpacing(8)
        lay.addWidget(self._lbl_header_dtmf)
        lay.addSpacing(22)
        self._header_stream_led, self._lbl_stream_status = self._header_status("Streaming desconectado")
        lay.addWidget(self._header_stream_led)
        lay.addSpacing(8)
        lay.addWidget(self._lbl_stream_status)
        lay.addSpacing(26)

        clock_box = QWidget()
        clock_box.setFixedWidth(172)
        clock_lay = QVBoxLayout(clock_box)
        clock_lay.setContentsMargins(16, 3, 0, 2)
        clock_lay.setSpacing(0)
        self._header_clock_label = QLabel("--:--:--")
        self._header_clock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._header_clock_label.setStyleSheet(
            f"font-size:28px; font-weight:700; color:{T('text_primary')};")
        self._header_date = QLabel("")
        self._header_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._header_date.setStyleSheet(f"font-size:12px; color:{T('text_secondary')};")
        clock_lay.addWidget(self._header_clock_label)
        clock_lay.addWidget(self._header_date)
        lay.addWidget(clock_box)
        return header

    def _header_status(self, text: str):
        led = LEDIndicator(QColor(T('success')))
        led.set_on(False)
        label = QLabel(text)
        label.setStyleSheet(f"font-size:12px; color:{T('text_primary')};")
        return led, label

    def _build_navigation(self) -> QWidget:
        nav = QWidget()
        nav.setObjectName("sideNavigation")
        nav.setFixedWidth(192)
        nav_bg = T('surface') if _current_theme is THEME_LIGHT else "#121C27"
        nav_hover = T('surface_raised') if _current_theme is THEME_LIGHT else "#1B2A38"
        nav.setStyleSheet(f"""
            QWidget#sideNavigation {{ background:{nav_bg}; border-right:1px solid {T('border')}; }}
            QPushButton {{ border:none; border-radius:0; background:transparent; color:{T('text_secondary')};
                text-align:left; padding-left:16px; min-height:40px; max-height:40px; font-size:14px; }}
            QPushButton:hover {{ background:{nav_hover}; color:{T('text_primary')}; }}
            QPushButton:checked {{ background:#0D67B2; border-left:3px solid #42AFFF; color:white; font-weight:600; }}
        """)
        lay = QVBoxLayout(nav)
        lay.setContentsMargins(0, 10, 0, 10)
        lay.setSpacing(2)
        entries = [
            ("Emisión", "Play.png"), ("Pautas locales", "Pauta.png"),
            ("Biblioteca", "MyMusic.png"), ("Reglas DTMF", "Chip.png"),
            ("Registro", "Alert.png"), ("Dispositivos", "AudioDevices.png"),
        ]
        self._nav_buttons = []
        for idx, (text, icon_name) in enumerate(entries):
            btn = QPushButton(f"   {text}")
            btn.setIcon(xp_icon(icon_name))
            btn.setIconSize(QSize(20, 20))
            btn.setCheckable(True)
            btn.setFixedHeight(52)
            btn.clicked.connect(lambda checked=False, i=idx: self._navigate_to(i))
            lay.addWidget(btn)
            self._nav_buttons.append(btn)
        self._nav_buttons[0].setChecked(True)
        lay.addStretch()
        return nav

    def _navigate_to(self, index: int):
        if not 0 <= index < len(self._nav_buttons):
            return
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)
        self._content_area.setCurrentIndex(index)

    def _panel(self, name: str) -> QWidget:
        panel = QWidget()
        panel.setObjectName(name)
        panel.setStyleSheet(f"""
            QWidget#{name} {{ background:{T('surface')}; border:1px solid {T('border')}; border-radius:5px; }}
            QWidget#{name} QLabel {{ border:none; background:transparent; }}
        """)
        return panel

    def _module_title(self, text: str, icon_name: str, size: int = 19) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(9)
        icon = QLabel()
        pix = xp_pixmap(icon_name, size)
        if not pix.isNull():
            icon.setPixmap(pix)
        icon.setFixedWidth(size + 2)
        row.addWidget(icon)
        label = QLabel(text)
        label.setStyleSheet(f"font-size:16px; font-weight:700; color:{T('accent_text')};")
        row.addWidget(label)
        row.addStretch()
        return row

    def _dashboard_table(self, headers: list[str], table_class=QTableWidget) -> QTableWidget:
        table = table_class(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setShowGrid(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(32)
        table.setStyleSheet(f"""
            QTableWidget {{ background:{T('bg_input')}; alternate-background-color:{T('surface')}; border:1px solid {T('border')};
                border-radius:4px; gridline-color:{T('border')}; font-size:12px; }}
            QTableWidget::item {{ padding:4px 8px; border:none; }}
            QHeaderView::section {{ background:{T('surface_raised')}; color:{T('text_primary')};
                border:0; border-right:1px solid {T('border')}; border-bottom:1px solid {T('border')};
                padding:6px 8px; font-size:12px; font-weight:600; }}
        """)
        return table

    def _build_emision_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background:{T('background')};")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(self._build_air_banner(), 68)
        top.addWidget(self._build_next_event(), 30)
        lay.addLayout(top)

        columns = QHBoxLayout()
        columns.setSpacing(12)
        left = QVBoxLayout(); left.setSpacing(10)
        right = QVBoxLayout(); right.setSpacing(10)
        left.addWidget(self._build_pauta_panel(), 63)
        left.addWidget(self._build_biblioteca_inline(), 34)
        right.addWidget(self._build_dtmf_panel(), 38)
        right.addWidget(self._build_output_panel(), 29)
        right.addWidget(self._build_log_panel(), 33)
        columns.addLayout(left, 68)
        columns.addLayout(right, 32)
        lay.addLayout(columns, 1)
        return page

    def _build_air_banner(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("airBanner")
        panel.setFixedHeight(98)
        air_bg = "#EAF7EF" if _current_theme is THEME_LIGHT else "#071B18"
        air_border = "#76B98C" if _current_theme is THEME_LIGHT else "#286748"
        panel.setStyleSheet(f"""
            QWidget#airBanner {{ background:{air_bg}; border:1px solid {air_border}; border-radius:5px; }}
            QWidget#airBanner QLabel {{ border:none; background:transparent; }}
        """)
        lay = QHBoxLayout(panel)
        lay.setContentsMargins(12, 0, 16, 0)
        lay.setSpacing(14)
        icon_tile = QWidget(); icon_tile.setObjectName("airIcon")
        icon_tile.setFixedSize(88, 82)
        icon_tile.setStyleSheet(f"QWidget#airIcon{{background:#05A94E;border:1px solid {T('success')};border-radius:6px;}}")
        icon_lay = QVBoxLayout(icon_tile); icon_lay.setContentsMargins(0,0,0,0)
        icon = QLabel(); icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = xp_pixmap("AudioCD.png", 48)
        if not pix.isNull(): icon.setPixmap(pix)
        icon_lay.addWidget(icon)
        lay.addWidget(icon_tile)
        copy = QVBoxLayout(); copy.setSpacing(3)
        self._lbl_air_title = QLabel("SIN FUENTE CONFIRMADA")
        self._lbl_air_title.setStyleSheet(f"font-size:20px;font-weight:800;color:{T('success')};")
        self._lbl_air_source = QLabel("Fuente: sin datos")
        self._lbl_air_source.setStyleSheet(f"font-size:14px;color:{T('text_primary')};")
        self._lbl_air_detail = QLabel("Configura o activa una fuente de programa")
        self._lbl_air_detail.setStyleSheet(f"font-size:12px;color:{T('text_secondary')};")
        copy.addWidget(self._lbl_air_title); copy.addWidget(self._lbl_air_source); copy.addWidget(self._lbl_air_detail)
        lay.addLayout(copy, 1)
        separator = QFrame(); separator.setFixedWidth(1); separator.setStyleSheet(f"background:{air_border};")
        lay.addWidget(separator)
        meter = QWidget(); meter.setFixedWidth(390)
        meter_lay = QVBoxLayout(meter); meter_lay.setContentsMargins(10,14,0,8); meter_lay.setSpacing(5)
        self._vu_bars = []
        for channel in ("L", "R"):
            row = QHBoxLayout(); row.setSpacing(10)
            lab = QLabel(channel); lab.setFixedWidth(15); lab.setStyleSheet("font-size:12px;font-weight:700;color:#DCE8F1;")
            bar = VUBar(); bar.setFixedHeight(17)
            row.addWidget(lab); row.addWidget(bar,1); meter_lay.addLayout(row); self._vu_bars.append(bar)
        scale = QHBoxLayout(); scale.setContentsMargins(26,0,0,0)
        for value in ("-60", "-40", "-20", "-10", "-6", "-3", "0 dB"):
            lab = QLabel(value); lab.setAlignment(Qt.AlignmentFlag.AlignCenter); lab.setStyleSheet("font-size:10px;color:#9EB0BF;")
            scale.addWidget(lab,1)
        meter_lay.addLayout(scale)
        lay.addWidget(meter)
        return panel

    def _build_next_event(self) -> QWidget:
        panel = QWidget(); panel.setObjectName("nextEvent"); panel.setFixedHeight(98)
        panel.setMinimumWidth(350)
        next_bg = "#FFF8E7" if _current_theme is THEME_LIGHT else "#12130E"
        next_border = "#D5A92F" if _current_theme is THEME_LIGHT else "#6B5620"
        panel.setStyleSheet(f"""
            QWidget#nextEvent {{ background:{next_bg};border:1px solid {next_border};border-radius:5px; }}
            QWidget#nextEvent QLabel {{ border:none;background:transparent; }}
        """)
        lay = QHBoxLayout(panel); lay.setContentsMargins(12,8,12,8); lay.setSpacing(9)
        icon = QLabel("◷"); icon.setFixedWidth(34); icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"font-size:31px;color:{T('warning')};"); lay.addWidget(icon)
        info = QVBoxLayout(); info.setSpacing(1)
        title = QLabel("Próxima desconexión"); title.setStyleSheet(f"font-size:12px;font-weight:600;color:{T('warning')};")
        self._lbl_next_time = QLabel("Esperando tono")
        self._lbl_next_time.setMinimumWidth(0)
        self._lbl_next_time.setStyleSheet(f"font-size:20px;font-weight:800;color:{T('warning')};")
        info.addWidget(title); info.addWidget(self._lbl_next_time); lay.addLayout(info,1)
        sep = QFrame(); sep.setFixedWidth(1); sep.setStyleSheet(f"background:{next_border};"); lay.addWidget(sep)
        count_box = QWidget(); count_box.setFixedWidth(116)
        count = QVBoxLayout(count_box); count.setContentsMargins(4,0,4,0); count.setSpacing(1)
        lbl_en = QLabel("En"); lbl_en.setAlignment(Qt.AlignmentFlag.AlignCenter); lbl_en.setStyleSheet(f"font-size:12px;color:{T('warning')};")
        self._lbl_countdown = QLabel("--:--"); self._lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_countdown.setStyleSheet(f"font-size:21px;font-weight:800;color:{T('warning')};")
        count.addWidget(lbl_en); count.addWidget(self._lbl_countdown); lay.addWidget(count_box)
        return panel

    def _build_pauta_panel(self) -> QWidget:
        panel = self._panel("pautaPanel")
        lay = QVBoxLayout(panel); lay.setContentsMargins(12,10,12,10); lay.setSpacing(7)
        head = self._module_title("Pauta local preparada", "Pauta.png", 22)
        self._lbl_pauta_summary = QLabel("Sin audios preparados")
        self._lbl_pauta_summary.setStyleSheet(f"font-size:12px;color:{T('text_secondary')};")
        head.insertWidget(2, self._lbl_pauta_summary)
        lay.addLayout(head)
        self._pauta_table = self._dashboard_table(
            ["Orden", "Audio / Cliente", "Duración", "Inicio", "Estado"], AudioDropTable)
        self._pauta_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._pauta_table.setColumnWidth(0,60); self._pauta_table.setColumnWidth(2,92)
        self._pauta_table.setColumnWidth(3,106); self._pauta_table.setColumnWidth(4,145)
        self._pauta_table.setMinimumHeight(145)
        self._pauta_table.filesDropped.connect(self._add_paths_to_playlist)
        self._pauta_table.setAccessibleDescription("Destino para soltar audios de la biblioteca")
        lay.addWidget(self._pauta_table,1)
        self._lbl_timeline = QLabel("Línea de tiempo de la pauta (00:00)")
        self._lbl_timeline.setStyleSheet(f"font-size:12px;color:{T('text_primary')};")
        lay.addWidget(self._lbl_timeline)
        self._timeline_bar = QWidget(); self._timeline_bar.setFixedHeight(24)
        self._timeline_layout = QHBoxLayout(self._timeline_bar); self._timeline_layout.setContentsMargins(0,0,0,0); self._timeline_layout.setSpacing(2)
        lay.addWidget(self._timeline_bar)
        self._timeline_labels = QWidget(); self._timeline_labels.setFixedHeight(22)
        self._timeline_labels_layout = QHBoxLayout(self._timeline_labels); self._timeline_labels_layout.setContentsMargins(0,0,0,0); self._timeline_labels_layout.setSpacing(2)
        lay.addWidget(self._timeline_labels)
        self._lbl_return_mode = QLabel("Inicio manual o por DTMF · retorno según configuración")
        self._lbl_return_mode.setStyleSheet(f"font-size:12px;color:{T('text_secondary')};")
        lay.addWidget(self._lbl_return_mode)
        actions = QHBoxLayout(); actions.setSpacing(10)
        self._btn_emitir_dashboard = QPushButton("▶   Emitir pauta local"); self._btn_emitir_dashboard.setCheckable(True)
        self._btn_emitir_dashboard.setFixedHeight(48)
        self._btn_emitir_dashboard.setStyleSheet(f"""
            QPushButton{{background:#078B36;color:white;border:2px solid {T('success')};border-radius:5px;
                font-size:15px;font-weight:700;min-height:0;padding:0 24px;}}
            QPushButton:checked{{background:#075E2A;}}""")
        self._btn_emitir_dashboard.toggled.connect(
            lambda on: self.btn_pauta.setChecked(on) if hasattr(self,"btn_pauta") else self._toggle_pauta(on))
        actions.addWidget(self._btn_emitir_dashboard)
        chain = QPushButton("■   Volver a cadena"); chain.setFixedHeight(48)
        chain.setStyleSheet(f"font-size:14px;font-weight:600;min-height:0;padding:0 24px;background:{T('surface_raised')};")
        chain.clicked.connect(lambda: self.btn_signal.setChecked(True) if hasattr(self,"btn_signal") else self._toggle_signal(True))
        actions.addWidget(chain); actions.addStretch()
        preview = QPushButton("♫   Preescuchar\nSolo monitoreo"); preview.setFixedSize(160,48); preview.setEnabled(False)
        preview.setToolTip("No hay una salida independiente de preescucha configurada")
        preview.setStyleSheet("font-size:12px;min-height:0;")
        actions.addWidget(preview); lay.addLayout(actions)
        return panel

    def _build_biblioteca_inline(self) -> QWidget:
        panel = self._panel("libraryPanel")
        lay = QVBoxLayout(panel); lay.setContentsMargins(12,9,12,9); lay.setSpacing(6)
        title_row = self._module_title("Biblioteca de medios", "MyMusic.png", 21)
        drag_hint = QLabel("Arrastra un audio hacia la pauta  ↑")
        drag_hint.setStyleSheet(f"font-size:10px;color:{T('text_dim')};")
        title_row.addWidget(drag_hint); lay.addLayout(title_row)
        controls = QHBoxLayout(); controls.setSpacing(6)
        self._dashboard_search = QLineEdit(); self._dashboard_search.setPlaceholderText("Buscar audio, cliente o campaña...")
        self._dashboard_search.setFixedHeight(32); self._dashboard_search.textChanged.connect(self._filter_dashboard_library)
        controls.addWidget(self._dashboard_search,1)
        self._dashboard_filter = QComboBox(); self._dashboard_filter.addItems(["Todos", "Comerciales", "Identificaciones", "Música"])
        self._dashboard_filter.setFixedSize(106,32); self._dashboard_filter.currentTextChanged.connect(lambda _: self._filter_dashboard_library(self._dashboard_search.text()))
        controls.addWidget(self._dashboard_filter)
        import_btn = QPushButton("↑  Importar audios"); import_btn.setFixedSize(150,34)
        import_btn.setStyleSheet(f"background:#126EB4;color:white;border:1px solid #299BEF;min-height:0;font-weight:600;")
        import_btn.clicked.connect(self._add_audio_files); controls.addWidget(import_btn)
        lay.addLayout(controls)
        self._dashboard_library_table = self._dashboard_table(
            ["Nombre del archivo", "Duración", "Cliente / Campaña", "Categoría", "Acción", "Ruta"],
            MediaLibraryTable)
        self._dashboard_library_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self._dashboard_library_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        self._dashboard_library_table.setColumnWidth(1,86); self._dashboard_library_table.setColumnWidth(3,150); self._dashboard_library_table.setColumnWidth(4,150)
        self._dashboard_library_table.setColumnHidden(5,True)
        self._dashboard_library_table.setAccessibleDescription("Origen de audios para arrastrar hacia la pauta")
        lay.addWidget(self._dashboard_library_table,1)
        return panel

    def _build_dtmf_panel(self) -> QWidget:
        panel = self._panel("dtmfPanel")
        lay = QVBoxLayout(panel); lay.setContentsMargins(10,9,10,9); lay.setSpacing(6)
        lay.addLayout(self._module_title("Control DTMF", "Chip.png", 20))
        status = QWidget(); status.setObjectName("dtmfStatus")
        dtmf_bg = "#EAF7EF" if _current_theme is THEME_LIGHT else "#09281F"
        status.setStyleSheet(f"QWidget#dtmfStatus{{background:{dtmf_bg};border:1px solid #4B9A6B;border-radius:4px;}}")
        status_lay = QHBoxLayout(status); status_lay.setContentsMargins(9,4,9,4); status_lay.setSpacing(8)
        self._dashboard_dtmf_led = LEDIndicator(QColor(T('success'))); self._dashboard_dtmf_led.set_on(False)
        self._lbl_dtmf_status = QLabel("Detector DTMF inactivo"); self._lbl_dtmf_status.setStyleSheet(f"font-size:13px;font-weight:700;color:{T('text_secondary')};")
        status_lay.addWidget(self._dashboard_dtmf_led); status_lay.addWidget(self._lbl_dtmf_status,1); lay.addWidget(status)
        last = QHBoxLayout(); last.addWidget(QLabel("Último código:"))
        self._lbl_last_code = QLabel("—  ·  sin detecciones"); self._lbl_last_code.setStyleSheet(f"font-size:13px;color:{T('text_primary')};font-weight:600;")
        last.addWidget(self._lbl_last_code,1); lay.addLayout(last)
        self._dtmf_rules_table = self._dashboard_table(["Código DTMF", "Acción"])
        self._dtmf_rules_table.verticalHeader().setDefaultSectionSize(27)
        self._dtmf_rules_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self._dtmf_rules_table.setColumnWidth(0,170); self._dtmf_rules_table.setFixedHeight(94)
        lay.addWidget(self._dtmf_rules_table)
        note = QLabel("ⓘ   La cadena continúa al aire hasta recibir el tono configurado.")
        note.setWordWrap(True); note.setStyleSheet(f"background:{T('bg_input')};border:1px solid {T('border')};border-radius:4px;padding:6px;font-size:11px;")
        lay.addWidget(note)
        return panel

    def _build_output_panel(self) -> QWidget:
        panel = self._panel("outputPanel")
        lay = QVBoxLayout(panel); lay.setContentsMargins(10,8,10,8); lay.setSpacing(5)
        lay.addLayout(self._module_title("Salida y respaldo", "AudioDevices.png", 20))
        row = QHBoxLayout(); row.setSpacing(10)
        meters = QWidget(); meters.setObjectName("programMeters"); meters.setStyleSheet(f"QWidget#programMeters{{background:{T('bg_input')};border:1px solid {T('border')};border-radius:4px;}}")
        ml = QVBoxLayout(meters); ml.setContentsMargins(7,5,7,4); ml.setSpacing(2)
        program = QLabel("Programa (salida al aire)"); program.setStyleSheet("font-size:11px;"); ml.addWidget(program)
        self._vu_output=[]
        for ch in ("L","R"):
            cr=QHBoxLayout(); lab=QLabel(ch); lab.setFixedWidth(12); lab.setStyleSheet("font-size:10px;")
            vb=VUBar(); vb.setFixedHeight(14); cr.addWidget(lab); cr.addWidget(vb,1); ml.addLayout(cr); self._vu_output.append(vb)
        row.addWidget(meters, 3)
        encoder = QWidget(); encoder.setObjectName("encoderBox"); encoder.setStyleSheet(f"QWidget#encoderBox{{background:{T('bg_input')};border:1px solid {T('border')};border-radius:4px;}}")
        el = QHBoxLayout(encoder); el.setContentsMargins(9,6,9,6)
        self._dashboard_encoder_led=LEDIndicator(QColor(T('success'))); self._dashboard_encoder_led.set_on(False); el.addWidget(self._dashboard_encoder_led)
        ec=QVBoxLayout(); ec.setSpacing(1); et=QLabel("Encoder"); et.setStyleSheet("font-size:12px;font-weight:700;")
        self._lbl_encoder_status=QLabel("Desconectado"); self._lbl_encoder_status.setStyleSheet(f"font-size:11px;color:{T('text_secondary')};")
        self._lbl_encoder_codec=QLabel("—"); self._lbl_encoder_codec.setStyleSheet(f"font-size:10px;color:{T('text_secondary')};")
        ec.addWidget(et); ec.addWidget(self._lbl_encoder_status); ec.addWidget(self._lbl_encoder_codec); el.addLayout(ec,1); row.addWidget(encoder,2)
        lay.addLayout(row)
        backup = QHBoxLayout(); self._dashboard_backup_led=LEDIndicator(QColor(T('success'))); self._dashboard_backup_led.set_on(False)
        backup.addWidget(self._dashboard_backup_led); bc=QVBoxLayout(); bc.setSpacing(0)
        bt=QLabel("Audio de respaldo"); bt.setStyleSheet("font-size:11px;")
        self._lbl_backup_status=QLabel("Respaldo no configurado"); self._lbl_backup_status.setStyleSheet(f"font-size:11px;color:{T('text_secondary')};")
        bc.addWidget(bt); bc.addWidget(self._lbl_backup_status); backup.addLayout(bc,1)
        cfg=QPushButton("⚙  Configurar audio"); cfg.setFixedHeight(34); cfg.setStyleSheet("font-size:11px;min-height:0;"); cfg.clicked.connect(lambda:self._navigate_to(5))
        backup.addWidget(cfg); lay.addLayout(backup)
        return panel

    def _build_log_panel(self) -> QWidget:
        panel = self._panel("logPanel")
        lay=QVBoxLayout(panel); lay.setContentsMargins(10,8,10,8); lay.setSpacing(6)
        title=self._module_title("Registro de emisión","Alert.png",20)
        clear=QPushButton("Limpiar"); clear.setFixedSize(82,28); clear.setStyleSheet("min-height:0;font-size:11px;"); clear.clicked.connect(self._clear_log_view)
        title.addWidget(clear); lay.addLayout(title)
        self._log_table=self._dashboard_table(["Hora","Evento"]); self._log_table.setColumnWidth(0,82)
        self._log_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch); lay.addWidget(self._log_table,1)
        return panel

    def _build_statusbar_bottom(self) -> QWidget:
        bar=QWidget(); bar.setObjectName("dashboardStatus"); bar.setFixedHeight(32)
        bar.setStyleSheet(f"QWidget#dashboardStatus{{background:{T('surface')};border-top:1px solid {T('border')};}} QWidget#dashboardStatus QLabel{{border:none;background:transparent;}}")
        lay=QHBoxLayout(bar); lay.setContentsMargins(16,0,16,0); lay.setSpacing(16)

        # Compatibilidad con los controladores operativos heredados. La barra de
        # estado anterior exponía estos widgets y varios manejadores todavía los
        # actualizan. El nuevo diseño presenta esa información en la cabecera y
        # los paneles, por lo que mantenemos los receptores ocultos pero vivos.
        self._sb_led=LEDIndicator(QColor(255,30,30),bar); self._sb_led.set_on(self._signal_on)
        self._sb_dtmf_lbl=QLabel("DTMF: inactivo",bar)
        self._sb_track_lbl=QLabel("Sin reproducción",bar)
        self._sb_state_lbl=QLabel("● Listo",bar)
        for compatibility_widget in (self._sb_led,self._sb_dtmf_lbl,self._sb_track_lbl,self._sb_state_lbl):
            compatibility_widget.setVisible(False)

        self._lbl_status_input=QLabel("Entrada: sin configurar"); self._lbl_status_output=QLabel("Salida: sistema predeterminado"); self._lbl_status_monitor=QLabel("Monitoreo: no configurado")
        for lab in (self._lbl_status_input,self._lbl_status_output,self._lbl_status_monitor): lab.setStyleSheet(f"font-size:11px;color:{T('text_secondary')};"); lay.addWidget(lab)
        lay.addStretch(); self._lbl_status_backup=QLabel("●  Respaldo no configurado"); self._lbl_status_backup.setStyleSheet(f"font-size:11px;color:{T('text_secondary')};"); lay.addWidget(self._lbl_status_backup)
        version=QLabel("Radio XP Automator v1.6.0"); version.setStyleSheet(f"font-size:10px;color:{T('text_dim')};"); lay.addWidget(version)
        return bar

    def _secondary_page(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        page=QWidget(); page.setStyleSheet(f"background:{T('background')};")
        lay=QVBoxLayout(page); lay.setContentsMargins(14,14,14,14); lay.setSpacing(10)
        heading=QLabel(title); heading.setStyleSheet(f"font-size:19px;font-weight:700;color:{T('text_primary')};")
        lay.addWidget(heading); return page,lay

    def _build_pautas_page(self) -> QWidget:
        page,lay=self._secondary_page("Pautas locales y fuentes")
        subtitle=QLabel("Prepara la secuencia, revisa la salida y activa la fuente correcta desde un solo lugar.")
        subtitle.setStyleSheet(f"font-size:12px;color:{T('text_secondary')};")
        lay.addWidget(subtitle)
        tools=QHBoxLayout(); tools.setSpacing(7)
        for label,fn in (("Nuevo",self._new_project),("Abrir…",self._open_project),("Guardar",self._save_project),("Añadir audio…",self._add_to_playlist)):
            b=QPushButton(label); b.setStyleSheet("min-height:32px;max-height:32px;padding:0 14px;font-size:12px;")
            b.clicked.connect(fn); tools.addWidget(b)
        tools.addStretch(); lay.addLayout(tools)
        row=QHBoxLayout(); row.setSpacing(12)
        console=self._build_consola(); player=self._build_reproductor()
        console.setMaximumHeight(570); player.setMaximumHeight(570)
        console.setMinimumWidth(390); player.setMinimumWidth(620)
        row.addWidget(console,36); row.addWidget(player,64)
        lay.addLayout(row); lay.addStretch()
        return page

    def _build_biblioteca_page(self) -> QWidget:
        page,lay=self._secondary_page("Biblioteca y pautas publicitarias")
        subtitle=QLabel("Importa una vez, encuentra rápido y envía el audio seleccionado directamente a la pauta.")
        subtitle.setStyleSheet(f"font-size:12px;color:{T('text_secondary')};")
        lay.addWidget(subtitle)
        workspace=self._panel("mediaWorkspace")
        work=QHBoxLayout(workspace); work.setContentsMargins(12,12,12,12); work.setSpacing(12)

        media=QWidget(); ml=QVBoxLayout(media); ml.setContentsMargins(0,0,0,0); ml.setSpacing(8)
        media_title=QLabel("Biblioteca de medios"); media_title.setStyleSheet(f"font-size:16px;font-weight:700;color:{T('accent_text')};")
        ml.addWidget(media_title)
        search=QHBoxLayout(); search.setSpacing(7)
        self._search_edit=QLineEdit(); self._search_edit.setPlaceholderText("Buscar canción, artista o álbum…")
        self._search_edit.setFixedHeight(34); self._search_edit.textChanged.connect(self._filter_library); search.addWidget(self._search_edit,1)
        self._filter_combo=QComboBox(); self._filter_combo.addItems(["Todos","Artista","Título","Álbum"]); self._filter_combo.setFixedSize(120,34)
        search.addWidget(self._filter_combo); ml.addLayout(search)
        actions=QHBoxLayout(); actions.setSpacing(6)
        for icon,label,fn in (("Add.png","Añadir",self._add_audio_files),("Open.png","Importar carpeta",self._import_folder),
                              ("NetworkandInternet.png","URL streaming",self._add_streaming_url),("Delete.png","Eliminar",self._del_from_library),
                              ("Playlist.png","Añadir a pauta",self._add_lib_to_playlist)):
            btn=QPushButton(label); btn.setIcon(xp_icon(icon)); btn.setIconSize(QSize(16,16)); btn.setFixedHeight(34)
            btn.setStyleSheet("min-height:30px;max-height:30px;padding:0 10px;font-size:11px;"); btn.clicked.connect(fn); actions.addWidget(btn)
        actions.addStretch(); ml.addLayout(actions)
        self._table_library=MediaLibraryTable(0,6)
        self._table_library.setHorizontalHeaderLabels(["Artista","Título","Álbum","Duración","Año","Ruta"])
        self._table_library.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table_library.horizontalHeader().setSectionResizeMode(5,QHeaderView.ResizeMode.ResizeToContents)
        self._table_library.setAlternatingRowColors(True); self._table_library.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table_library.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); self._table_library.verticalHeader().setVisible(False)
        self._table_library.doubleClicked.connect(self._library_double_click)
        self._table_library.setAccessibleDescription("Origen de audios para arrastrar hacia una pauta")
        ml.addWidget(self._table_library,1)
        self._lbl_lib_count=QLabel("0 archivos · arrastra a la pauta o usa doble clic")
        self._lbl_lib_count.setStyleSheet(f"font-size:11px;color:{T('text_dim')};"); ml.addWidget(self._lbl_lib_count)

        campaigns=QWidget(); cl=QVBoxLayout(campaigns); cl.setContentsMargins(0,0,0,0); cl.setSpacing(8)
        campaign_title=QLabel("Pautas publicitarias"); campaign_title.setStyleSheet(f"font-size:16px;font-weight:700;color:{T('accent_text')};")
        cl.addWidget(campaign_title)
        campaign_actions=QHBoxLayout(); campaign_actions.setSpacing(6)
        for icon,label,fn in (("Add.png","Nueva pauta",self._new_pauta),("Delete.png","Eliminar",self._del_pauta)):
            btn=QPushButton(label); btn.setIcon(xp_icon(icon)); btn.setIconSize(QSize(16,16)); btn.setFixedHeight(34)
            btn.setStyleSheet("min-height:30px;max-height:30px;padding:0 12px;font-size:11px;"); btn.clicked.connect(fn); campaign_actions.addWidget(btn)
        campaign_actions.addStretch(); cl.addLayout(campaign_actions)
        self._table_pautas=AudioDropTable(0,7)
        self._table_pautas.setHorizontalHeaderLabels(["Archivo","Cliente","Spot","Duración","Horario","Días","Ruta"])
        self._table_pautas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table_pautas.setAlternatingRowColors(True); self._table_pautas.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table_pautas.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked); self._table_pautas.verticalHeader().setVisible(False)
        self._table_pautas.setColumnHidden(6,True)
        self._table_pautas.filesDropped.connect(self._add_paths_to_pautas)
        self._table_pautas.itemChanged.connect(self._on_pauta_item_changed)
        self._table_pautas.setAccessibleDescription("Destino para soltar audios de la biblioteca")
        cl.addWidget(self._table_pautas,1)
        campaign_hint=QLabel("Arrastra audios desde la biblioteca · doble clic para editar · guardado automático")
        campaign_hint.setStyleSheet(f"font-size:11px;color:{T('text_dim')};"); cl.addWidget(campaign_hint)

        split=QSplitter(Qt.Orientation.Horizontal); split.addWidget(media); split.addWidget(campaigns); split.setSizes([900,430])
        work.addWidget(split,1); lay.addWidget(workspace,1)
        return page

    def _build_dtmf_page(self) -> QWidget:
        page,lay=self._secondary_page("Reglas y detector DTMF")
        subtitle=QLabel("Configura la entrada, valida las secuencias y prueba tonos sin abandonar el contexto operativo.")
        subtitle.setStyleSheet(f"font-size:12px;color:{T('text_secondary')};"); lay.addWidget(subtitle)
        row=QHBoxLayout(); row.setSpacing(12)
        config=self._panel("dtmfConfiguration"); cfg=QVBoxLayout(config); cfg.setContentsMargins(12,10,12,12); cfg.setSpacing(8)
        title=QLabel("Configuración DTMF"); title.setStyleSheet(f"font-size:16px;font-weight:700;color:{T('accent_text')};"); cfg.addWidget(title)
        tabs=QTabWidget(); tabs.setMinimumHeight(390); tabs.setMaximumHeight(520)

        devices=QWidget(); dg=QGridLayout(devices); dg.setContentsMargins(14,16,14,14); dg.setHorizontalSpacing(14); dg.setVerticalSpacing(11)
        device_rows=[("Entrada de tonos", "_dtmf_dev_combo"),("Salida de señal principal", "_sd_out_dev_combo"),
                     ("Salida del reproductor", "_out_dev_combo"),("Salida del reproductor remoto", "_remote_out_dev_combo")]
        for r,(label,attr) in enumerate(device_rows):
            lab=QLabel(label); lab.setStyleSheet(f"font-size:12px;color:{T('text_secondary')};"); combo=QComboBox(); combo.setFixedHeight(34)
            setattr(self,attr,combo); dg.addWidget(lab,r,0); dg.addWidget(combo,r,1)
        self._out_dev_combo.currentIndexChanged.connect(self._on_out_dev_changed)
        self._remote_out_dev_combo.currentIndexChanged.connect(self._on_remote_out_dev_changed)
        refresh=QPushButton("Actualizar dispositivos"); refresh.setIcon(xp_icon("Refresh.png")); refresh.setFixedHeight(34)
        refresh.setStyleSheet("min-height:32px;max-height:32px;padding:0 14px;"); refresh.clicked.connect(self._refresh_devices); dg.addWidget(refresh,4,1,alignment=Qt.AlignmentFlag.AlignRight)
        dg.setColumnStretch(1,1); dg.setRowStretch(5,1); tabs.addTab(devices,"Dispositivos")

        params=QWidget(); pg=QGridLayout(params); pg.setContentsMargins(14,16,14,14); pg.setHorizontalSpacing(14); pg.setVerticalSpacing(8)
        self._dtmf_freq_lo=QSpinBox(); self._dtmf_freq_lo.setRange(300,4000); self._dtmf_freq_lo.setValue(697)
        self._dtmf_freq_hi=QSpinBox(); self._dtmf_freq_hi.setRange(300,4000); self._dtmf_freq_hi.setValue(1633)
        self._dtmf_dur=QSpinBox(); self._dtmf_dur.setRange(10,500); self._dtmf_dur.setValue(40)
        self._dtmf_thresh=QDoubleSpinBox(); self._dtmf_thresh.setRange(-80,0); self._dtmf_thresh.setValue(-30); self._dtmf_thresh.setSuffix(" dB")
        self._dtmf_tol=QSpinBox(); self._dtmf_tol.setRange(1,100); self._dtmf_tol.setValue(20)
        self._dtmf_seq_play=QLineEdit("420590"); self._dtmf_seq_stop=QLineEdit("609700")
        param_rows=[("Frecuencia inicial (Hz)",self._dtmf_freq_lo),("Frecuencia final (Hz)",self._dtmf_freq_hi),
                    ("Duración mínima (ms)",self._dtmf_dur),("Umbral de ruido",self._dtmf_thresh),
                    ("Tolerancia (±Hz)",self._dtmf_tol),("Secuencia para iniciar pauta",self._dtmf_seq_play),
                    ("Secuencia para volver",self._dtmf_seq_stop)]
        for r,(label,widget) in enumerate(param_rows):
            lab=QLabel(label); lab.setStyleSheet(f"font-size:12px;color:{T('text_secondary')};"); widget.setFixedHeight(32); pg.addWidget(lab,r,0); pg.addWidget(widget,r,1)
        apply_btn=QPushButton("Aplicar parámetros"); apply_btn.setIcon(xp_icon("Apply.png")); apply_btn.setFixedHeight(34)
        apply_btn.setStyleSheet("min-height:32px;max-height:32px;padding:0 14px;"); apply_btn.clicked.connect(self._apply_dtmf_params); pg.addWidget(apply_btn,7,1,alignment=Qt.AlignmentFlag.AlignRight)
        pg.setColumnStretch(1,1); pg.setRowStretch(8,1); tabs.addTab(params,"Parámetros")

        test=QWidget(); tg=QGridLayout(test); tg.setContentsMargins(14,16,14,14); tg.setHorizontalSpacing(14); tg.setVerticalSpacing(10)
        self._test_tone_cb=QComboBox()
        for digit,freqs in (("1",(697,1209)),("2",(697,1336)),("3",(697,1477)),("4",(770,1209)),("5",(770,1336)),("6",(770,1477)),("7",(852,1209)),("8",(852,1336)),("9",(852,1477)),("*",(941,1209)),("0",(941,1336)),("#",(941,1477))):
            self._test_tone_cb.addItem(f"{digit}  ·  {freqs[0]}/{freqs[1]} Hz",freqs)
        self._test_dur_spin=QSpinBox(); self._test_dur_spin.setRange(50,2000); self._test_dur_spin.setValue(250); self._test_dur_spin.setSuffix(" ms")
        tg.addWidget(QLabel("Tono"),0,0); tg.addWidget(self._test_tone_cb,0,1); tg.addWidget(QLabel("Duración"),1,0); tg.addWidget(self._test_dur_spin,1,1)
        send=QPushButton("Enviar tono de prueba"); send.setIcon(xp_icon("Send.png")); send.setFixedHeight(36); send.clicked.connect(self._send_test_tone)
        tg.addWidget(send,2,1,alignment=Qt.AlignmentFlag.AlignRight); tg.setColumnStretch(1,1); tg.setRowStretch(3,1); tabs.addTab(test,"Prueba")
        cfg.addWidget(tabs); cfg.addStretch(); row.addWidget(config,72)

        state=self._panel("dtmfStateCard"); sl=QVBoxLayout(state); sl.setContentsMargins(16,14,16,16); sl.setSpacing(10)
        st=QLabel("Estado del detector"); st.setStyleSheet(f"font-size:16px;font-weight:700;color:{T('accent_text')};"); sl.addWidget(st)
        self._lbl_dtmf_state=QLabel("Inactivo"); self._lbl_dtmf_state.setStyleSheet(f"font-size:13px;color:{T('text_secondary')};"); sl.addWidget(self._lbl_dtmf_state)
        self._btn_dtmf_secondary=QPushButton("Activar detector DTMF"); self._btn_dtmf_secondary.setCheckable(True); self._btn_dtmf_secondary.setFixedHeight(42)
        self._btn_dtmf_secondary.setStyleSheet(f"QPushButton{{min-height:38px;max-height:38px;padding:0 12px;font-weight:700;border-color:#23784C;}} QPushButton:checked{{background:#08763A;color:white;border-color:{T('success')};}}")
        self._btn_dtmf_secondary.toggled.connect(lambda on:self.btn_dtmf_main.setChecked(on)); self.btn_dtmf_main.toggled.connect(self._btn_dtmf_secondary.setChecked)
        sl.addWidget(self._btn_dtmf_secondary)
        sep=QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setStyleSheet(f"color:{T('border')};"); sl.addWidget(sep)
        last=QLabel("Las secuencias activas aparecen también en el resumen de Emisión."); last.setWordWrap(True); last.setStyleSheet(f"font-size:12px;color:{T('text_secondary')};"); sl.addWidget(last)
        sl.addStretch(); row.addWidget(state,28)
        lay.addLayout(row); lay.addStretch(); self._refresh_devices()
        return page

    def _build_registro_page(self) -> QWidget:
        page,lay=self._secondary_page("Registro")
        subtitle=QLabel("Consulta los eventos recientes sin perder de vista el resultado de cada operación.")
        subtitle.setStyleSheet(f"font-size:12px;color:{T('text_secondary')};"); lay.addWidget(subtitle)
        card=self._panel("historyCard"); cl=QVBoxLayout(card); cl.setContentsMargins(12,10,12,12); cl.setSpacing(8)
        empty=QLabel("Aún no hay eventos en esta sesión")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter); empty.setStyleSheet(f"font-size:15px;font-weight:600;color:{T('text_secondary')};")
        detail=QLabel("Las detecciones DTMF, cambios de fuente y resultados del encoder aparecerán aquí.")
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter); detail.setWordWrap(True); detail.setStyleSheet(f"font-size:12px;color:{T('text_dim')};")
        cl.addStretch(); cl.addWidget(empty); cl.addWidget(detail); cl.addStretch(); lay.addWidget(card,1); return page

    def _build_dispositivos_page(self) -> QWidget:
        page,lay=self._secondary_page("Dispositivos, micrófono y streaming")
        subtitle=QLabel("Controla captura y transmisión por separado; el estado al aire no depende del estado del encoder.")
        subtitle.setStyleSheet(f"font-size:12px;color:{T('text_secondary')};"); lay.addWidget(subtitle)
        cards=QHBoxLayout(); cards.setSpacing(12)

        encoder=self._panel("encoderSettingsCard"); el=QVBoxLayout(encoder); el.setContentsMargins(16,14,16,16); el.setSpacing(10)
        et=QLabel("Encoder y streaming"); et.setStyleSheet(f"font-size:16px;font-weight:700;color:{T('accent_text')};"); el.addWidget(et)
        status=QHBoxLayout(); self._lbl_enc_status=QLabel("Desconectado"); self._lbl_enc_status.setStyleSheet(f"font-size:13px;color:{T('text_secondary')};")
        status.addWidget(self._lbl_enc_status); status.addStretch(); self.btn_encoder=QPushButton("OFF"); self.btn_encoder.setCheckable(True); self.btn_encoder.setFixedSize(88,40)
        self.btn_encoder.toggled.connect(self._toggle_encoder); status.addWidget(self.btn_encoder); el.addLayout(status)
        self._lbl_enc_info=QLabel("Configura servidor, codec y bitrate antes de iniciar."); self._lbl_enc_info.setWordWrap(True); self._lbl_enc_info.setStyleSheet(f"font-size:12px;color:{T('text_secondary')};")
        el.addWidget(self._lbl_enc_info); config=QPushButton("Configurar encoder…"); config.setIcon(xp_icon("Settings.png")); config.setFixedHeight(38)
        config.setStyleSheet("min-height:36px;max-height:36px;padding:0 12px;"); config.clicked.connect(self._config_encoder); el.addWidget(config); el.addStretch(); self._update_encoder_style(False)

        microphone=self._panel("microphoneCard"); ml=QVBoxLayout(microphone); ml.setContentsMargins(16,14,16,16); ml.setSpacing(10)
        mt=QLabel("Micrófono y monitoreo"); mt.setStyleSheet(f"font-size:16px;font-weight:700;color:{T('accent_text')};"); ml.addWidget(mt)
        mic_status=QHBoxLayout(); mic_status.addWidget(QLabel("Captura de micrófono")); mic_status.addStretch(); self.btn_mic=QPushButton("OFF"); self.btn_mic.setCheckable(True); self.btn_mic.setFixedSize(88,40)
        self.btn_mic.toggled.connect(self._toggle_mic); mic_status.addWidget(self.btn_mic); ml.addLayout(mic_status)
        source_label=QLabel("Fuente de entrada"); source_label.setStyleSheet(f"font-size:11px;color:{T('text_secondary')};"); ml.addWidget(source_label)
        self._mic_src_combo=QComboBox(); self._mic_src_combo.setFixedHeight(34); ml.addWidget(self._mic_src_combo); self._populate_mic_sources()
        volume_label=QLabel("Volumen de micrófono"); volume_label.setStyleSheet(f"font-size:11px;color:{T('text_secondary')};"); ml.addWidget(volume_label)
        volume=QHBoxLayout(); mic_slider=QSlider(Qt.Orientation.Horizontal); mic_slider.setRange(0,100); mic_slider.setValue(80); volume.addWidget(mic_slider,1)
        mic_value=QLabel("80%"); mic_value.setFixedWidth(42); mic_value.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter); volume.addWidget(mic_value)
        mic_slider.valueChanged.connect(lambda v: (mic_value.setText(f"{v}%"),self.passthrough.set_volume(v/100))); ml.addLayout(volume); ml.addStretch()
        self._vol_sliders={"mic":mic_slider}
        cards.addWidget(encoder,1); cards.addWidget(microphone,1); lay.addLayout(cards)

        routing=self._panel("routingCard"); rl=QHBoxLayout(routing); rl.setContentsMargins(16,12,16,12); rl.setSpacing(12)
        routing_copy=QVBoxLayout(); rt=QLabel("Ruteo de audio"); rt.setStyleSheet(f"font-size:14px;font-weight:700;color:{T('text_primary')};")
        rd=QLabel("Selecciona entrada DTMF y salidas de programa en Reglas DTMF → Dispositivos."); rd.setStyleSheet(f"font-size:12px;color:{T('text_secondary')};")
        routing_copy.addWidget(rt); routing_copy.addWidget(rd); rl.addLayout(routing_copy,1)
        go=QPushButton("Abrir dispositivos DTMF"); go.setStyleSheet("min-height:34px;max-height:34px;padding:0 12px;"); go.clicked.connect(lambda:self._navigate_to(3)); rl.addWidget(go)
        lay.addWidget(routing); lay.addStretch(); return page

    def _table_snapshot(self, table: QTableWidget) -> list[list[str]]:
        if table is None:
            return []
        return [[table.item(r,c).text() if table.item(r,c) else ""
                 for c in range(table.columnCount())]
                for r in range(table.rowCount())]

    def _restore_table_snapshot(self, table: QTableWidget, rows: list[list[str]]):
        previous=table.blockSignals(True)
        try:
            table.setRowCount(0)
            for values in rows:
                row=table.rowCount(); table.insertRow(row)
                for col,value in enumerate(values[:table.columnCount()]):
                    table.setItem(row,col,QTableWidgetItem(value))
        finally:
            table.blockSignals(previous)

    def _toggle_theme(self):
        """Cambia de tema reconstruyendo sólo widgets, nunca motores ni datos."""
        dark=self._theme_action.isChecked()
        current_page=self._content_area.currentIndex() if hasattr(self,"_content_area") else 0
        library_rows=self._table_snapshot(getattr(self,"_table_library",None))
        pauta_rows=self._table_snapshot(getattr(self,"_table_pautas",None))
        remote_url=self._remote_url_edit.text() if hasattr(self,"_remote_url_edit") else ""
        device_texts={name:getattr(self,name).currentText() for name in
                      ("_dtmf_dev_combo","_sd_out_dev_combo","_out_dev_combo","_remote_out_dev_combo","_mic_src_combo")
                      if hasattr(self,name)}
        dtmf_values={
            "lo": self._dtmf_freq_lo.value() if hasattr(self,"_dtmf_freq_lo") else 697,
            "hi": self._dtmf_freq_hi.value() if hasattr(self,"_dtmf_freq_hi") else 1633,
            "dur": self._dtmf_dur.value() if hasattr(self,"_dtmf_dur") else 40,
            "threshold": self._dtmf_thresh.value() if hasattr(self,"_dtmf_thresh") else -30,
            "tolerance": self._dtmf_tol.value() if hasattr(self,"_dtmf_tol") else 20,
            "play": self._dtmf_seq_play.text() if hasattr(self,"_dtmf_seq_play") else "420590",
            "stop": self._dtmf_seq_stop.text() if hasattr(self,"_dtmf_seq_stop") else "609700",
        }

        set_theme(dark)
        QApplication.instance().setStyleSheet(generate_qss())
        self._setup_ui()

        self._restore_table_snapshot(self._table_library,library_rows)
        self._restore_table_snapshot(self._table_pautas,pauta_rows)
        self._lbl_lib_count.setText(f"{self._table_library.rowCount()} archivos · doble clic para añadir a la pauta")
        for track in self.engine.playlist:
            self._add_playlist_row(track)

        self._dtmf_freq_lo.setValue(dtmf_values["lo"]); self._dtmf_freq_hi.setValue(dtmf_values["hi"])
        self._dtmf_dur.setValue(dtmf_values["dur"]); self._dtmf_thresh.setValue(dtmf_values["threshold"])
        self._dtmf_tol.setValue(dtmf_values["tolerance"]); self._dtmf_seq_play.setText(dtmf_values["play"])
        self._dtmf_seq_stop.setText(dtmf_values["stop"])
        if remote_url:
            self._remote_url_edit.setText(remote_url)
        for name,text in device_texts.items():
            combo=getattr(self,name,None)
            if combo is not None:
                index=combo.findText(text)
                if index >= 0: combo.setCurrentIndex(index)

        for widget,state in ((getattr(self,"btn_signal",None),self._signal_on),
                             (getattr(self,"btn_pauta",None),self._pauta_on),
                             (getattr(self,"btn_dtmf_main",None),self._dtmf_on),
                             (getattr(self,"btn_remote",None),self._remote_on),
                             (getattr(self,"btn_encoder",None),self._encoder_on),
                             (getattr(self,"btn_mic",None),self._mic_on),
                             (getattr(self,"_btn_automatic",None),self._dtmf_on)):
            if widget is not None:
                previous=widget.blockSignals(True); widget.setChecked(state); widget.blockSignals(previous)
        self._update_encoder_style(self._encoder_on); self._update_mic_style(self._mic_on)
        self._sync_dashboard(); self._navigate_to(current_page)
        self._on_dtmf_status("Escuchando entrada de cadena" if self._dtmf_on else "Detector DTMF inactivo")
        self._on_playback_state(self.engine.state)

    def _update_dashboard_clock(self):
        now=datetime.now()
        if hasattr(self,"_header_clock_label"):
            self._header_clock_label.setText(now.strftime("%H:%M:%S"))
            dias=("lun","mar","mié","jue","vie","sáb","dom")
            meses=("ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic")
            self._header_date.setText(f"{dias[now.weekday()].capitalize()} {now.day} de {meses[now.month-1]}. de {now.year}")

    def _set_dashboard_source(self, title: str, source: str, detail: str):
        if hasattr(self, "_lbl_air_title"):
            self._lbl_air_title.setText(title)
            self._lbl_air_source.setText(source)
            self._lbl_air_detail.setText(detail)

    def _clear_layout_widgets(self, layout):
        while layout.count():
            item=layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout(): self._clear_layout_widgets(item.layout())

    def _duration_seconds(self, value: str) -> int:
        try:
            parts=[int(float(p)) for p in str(value).split(":")]
            return parts[-1] + (parts[-2]*60 if len(parts)>1 else 0) + (parts[-3]*3600 if len(parts)>2 else 0)
        except (ValueError,TypeError):
            return 0

    def _sync_dashboard(self):
        if not hasattr(self,"_pauta_table"):
            return
        playlist=list(self.engine.playlist)
        self._pauta_table.setRowCount(0)
        total=0
        for i,track in enumerate(playlist):
            row=self._pauta_table.rowCount(); self._pauta_table.insertRow(row)
            total += self._duration_seconds(track.get("duration","0:00"))
            values=(f"{i+1:02d}", track.get("title") or Path(track.get("path","")).stem,
                    track.get("duration","0:00"), "—", "Preparado")
            for col,value in enumerate(values):
                item=QTableWidgetItem(str(value)); self._pauta_table.setItem(row,col,item)
        mins,secs=divmod(total,60)
        self._lbl_pauta_summary.setText(f"{len(playlist)} audios · Total {mins:02d}:{secs:02d}" if playlist else "Sin audios preparados")
        self._lbl_timeline.setText(f"Línea de tiempo de la pauta ({mins:02d}:{secs:02d})")
        self._clear_layout_widgets(self._timeline_layout); self._clear_layout_widgets(self._timeline_labels_layout)
        colors=("#36BDF2","#46D879","#F5B942","#9A63D4")
        if playlist:
            for i,track in enumerate(playlist):
                duration=max(1,self._duration_seconds(track.get("duration","0:00")))
                seg=QLabel(track.get("duration","0:00")); seg.setAlignment(Qt.AlignmentFlag.AlignCenter)
                seg.setStyleSheet(f"background:{colors[i%len(colors)]};color:#071019;font-size:10px;font-weight:700;border-radius:2px;")
                self._timeline_layout.addWidget(seg,duration)
                name=QLabel(track.get("title") or "Audio"); name.setAlignment(Qt.AlignmentFlag.AlignCenter)
                name.setStyleSheet(f"font-size:10px;color:{T('text_secondary')};"); self._timeline_labels_layout.addWidget(name,duration)
        else:
            empty=QLabel("Sin audios"); empty.setAlignment(Qt.AlignmentFlag.AlignCenter); empty.setStyleSheet(f"background:{T('surface_raised')};color:{T('text_dim')};border-radius:2px;")
            self._timeline_layout.addWidget(empty)

        if hasattr(self,"_dashboard_library_table") and hasattr(self,"_table_library"):
            self._dashboard_library_table.setRowCount(0)
            for r in range(self._table_library.rowCount()):
                title=self._table_library.item(r,1).text() if self._table_library.item(r,1) else ""
                duration=self._table_library.item(r,3).text() if self._table_library.item(r,3) else ""
                artist=self._table_library.item(r,0).text() if self._table_library.item(r,0) else ""
                path=self._table_library.item(r,5).text() if self._table_library.item(r,5) else ""
                row=self._dashboard_library_table.rowCount(); self._dashboard_library_table.insertRow(row)
                for c,value in enumerate((Path(path).name or title,duration,artist,"Audio","",path)):
                    self._dashboard_library_table.setItem(row,c,QTableWidgetItem(value))
                add=QPushButton("Añadir a pauta"); add.setFixedHeight(24); add.setStyleSheet("font-size:10px;min-height:0;padding:0 8px;")
                add.clicked.connect(lambda checked=False,p=path:self._dashboard_add_path(p))
                self._dashboard_library_table.setCellWidget(row,4,add)
        self._sync_dashboard_dtmf_rules()
        self._sync_dashboard_status()

    def _dashboard_add_path(self, path: str):
        info=self.engine.add_file(path)
        if info:
            self._add_playlist_row(info)
            self._save_playlist_to_disk()

    def _sync_dashboard_dtmf_rules(self):
        if not hasattr(self,"_dtmf_rules_table"):
            return
        play=self._dtmf_seq_play.text().strip() if hasattr(self,"_dtmf_seq_play") else ""
        stop=self._dtmf_seq_stop.text().strip() if hasattr(self,"_dtmf_seq_stop") else ""
        rules=[(play,"Iniciar pauta local"),(stop,"Volver a cadena")]
        rules=[r for r in rules if r[0]]
        self._dtmf_rules_table.setRowCount(len(rules))
        for row,(code,action) in enumerate(rules):
            self._dtmf_rules_table.setItem(row,0,QTableWidgetItem(code)); self._dtmf_rules_table.setItem(row,1,QTableWidgetItem(action))

    def _sync_dashboard_status(self):
        if hasattr(self,"_lbl_encoder_codec"):
            codec=str(self._encoder_settings.get("codec","")).upper()
            bitrate=self._encoder_settings.get("bitrate")
            self._lbl_encoder_codec.setText(f"{codec} · {bitrate} kbps" if codec and bitrate else "Sin configurar")
        if hasattr(self,"_lbl_status_input") and hasattr(self,"_dtmf_dev_combo"):
            self._lbl_status_input.setText(f"Entrada: {self._dtmf_dev_combo.currentText()}")
        if hasattr(self,"_lbl_status_output") and hasattr(self,"_out_dev_combo"):
            self._lbl_status_output.setText(f"Salida: {self._out_dev_combo.currentText()}")

    def _filter_dashboard_library(self, text: str):
        if not hasattr(self,"_dashboard_library_table"):
            return
        needle=text.strip().lower(); category=self._dashboard_filter.currentText() if hasattr(self,"_dashboard_filter") else "Todos"
        for row in range(self._dashboard_library_table.rowCount()):
            hay=" ".join(self._dashboard_library_table.item(row,c).text().lower() for c in range(4) if self._dashboard_library_table.item(row,c))
            category_ok=category=="Todos" or category.lower().rstrip("s") in hay
            self._dashboard_library_table.setRowHidden(row, bool(needle and needle not in hay) or not category_ok)


# ══════════════════════════════════════════════════════════════════════════════
#  PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════
def application_exception_hook(exc_type, value, tb):
    """Informa errores de slots Qt sin provocar el cierre total de la emisora."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, value, tb)
        return
    detail = "".join(traceback.format_exception(exc_type, value, tb))
    print(detail, file=sys.stderr, flush=True)
    app = QApplication.instance()
    if app is not None:
        message = f"{exc_type.__name__}: {value}"
        QTimer.singleShot(0, lambda: QMessageBox.critical(
            app.activeWindow(), "Error recuperable", message))


if __name__ == "__main__":
    sys.excepthook = application_exception_hook
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    app_icon_path = resource_path(os.path.join("assets", "icon.png"))
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))

    set_theme(dark=True)
    app.setStyleSheet(generate_qss())
    app.setFont(QFont("Helvetica Neue", 9))

    win = MainWindow()
    win.show()
    sys.exit(app.exec())
