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
from datetime import datetime
from pathlib import Path

# ── PyQt6 ──────────────────────────────────────────────────────────────────
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QSplitter, QPushButton, QLabel, QLCDNumber,
    QProgressBar, QTabWidget, QComboBox, QSpinBox, QDoubleSpinBox,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QSlider,
    QFrame, QSizePolicy, QFileDialog, QMessageBox, QInputDialog,
    QStatusBar, QToolBar, QStyle
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
        bundled = os.path.join(sys._MEIPASS, "ffmpeg")
        if sys.platform == "win32":
            bundled += ".exe"
        if os.path.exists(bundled):
            return bundled
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
    "bg_primary":     "#1E1E2E",
    "bg_surface":     "#2A2A3C",
    "bg_surface_alt": "#232336",
    "bg_hover":       "#32324A",
    "bg_input":       "#1A1A2C",
    "border":         "#3A3A4C",
    "border_focus":   "#4A9EFF",
    "text":           "#E0E0E0",
    "text_secondary": "#8888A0",
    "text_dim":       "#666680",
    "accent":         "#4A9EFF",
    "success":        "#00CC66",
    "danger":         "#FF4444",
    "warning":        "#FFB020",
    "menu_bg":        "#252538",
    "menu_hover":     "#3A3A54",
    "scrollbar_bg":   "#2A2A3C",
    "scrollbar_handle":"#444460",
    "scrollbar_hover":"#5A5A78",
    "header_bg":      "#282840",
    "slider_groove":  "#3A3A4C",
    "slider_sub":     "#4A9EFF",
    "clock_bg":       "#0A0F14",
    "clock_color":    "#FFB020",
    "vu_bg":          "#0E0E14",
    "vu_green":       "#00CC66",
    "vu_amber":       "#FFB020",
    "vu_red":         "#FF4444",
    "vu_label":       "#8888A0",
    "wave_bg":        "#0A0A12",
    "wave_text":      "#00FF88",
    "titlebar_start": "#2A4A8A",
    "titlebar_mid":   "#3366BB",
    "titlebar_end":   "#1E3A7A",
    "panel_bg":       "#2A2A3C",
    "panel_border":   "#3A3A4C",
}

THEME_LIGHT = {
    "bg_primary":     "#F5F5F7",
    "bg_surface":     "#FFFFFF",
    "bg_surface_alt": "#F0F0F4",
    "bg_hover":       "#E8E8F0",
    "bg_input":       "#FFFFFF",
    "border":         "#D0D0D8",
    "border_focus":   "#2A7FFF",
    "text":           "#1A1A2E",
    "text_secondary": "#666680",
    "text_dim":       "#9999AA",
    "accent":         "#2A7FFF",
    "success":        "#00AA55",
    "danger":         "#DD2222",
    "warning":        "#E09000",
    "menu_bg":        "#FFFFFF",
    "menu_hover":     "#E0E8F8",
    "scrollbar_bg":   "#F0F0F4",
    "scrollbar_handle":"#C8C8D0",
    "scrollbar_hover":"#A8A8B8",
    "header_bg":      "#E8E8F0",
    "slider_groove":  "#D0D0D8",
    "slider_sub":     "#2A7FFF",
    "clock_bg":       "#0A0F14",
    "clock_color":    "#FFB020",
    "vu_bg":          "#0E0E14",
    "vu_green":       "#00CC66",
    "vu_amber":       "#FFB020",
    "vu_red":         "#FF4444",
    "vu_label":       "#8888A0",
    "wave_bg":        "#0A0A12",
    "wave_text":      "#00FF88",
    "titlebar_start": "#3366CC",
    "titlebar_mid":   "#4488EE",
    "titlebar_end":   "#2255AA",
    "panel_bg":       "#FFFFFF",
    "panel_border":   "#D0D0D8",
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
QMainWindow {{ background: {t['bg_primary']}; }}
QWidget {{ font-family: "Helvetica Neue", "Segoe UI", "SF Pro Display", Helvetica, Arial; font-size: 9pt; color: {t['text']}; }}
QMenuBar {{
    background: {t['bg_surface']};
    border-bottom: 1px solid {t['border']};
}}
QMenuBar::item {{ padding: 6px 12px; }}
QMenuBar::item:selected {{ background: {t['accent']}; color: white; border-radius: 4px; }}
QMenu {{ background: {t['menu_bg']}; border: 1px solid {t['border']}; border-radius: 6px; padding: 4px; }}
QMenu::item {{ padding: 6px 28px; border-radius: 4px; }}
QMenu::item:selected {{ background: {t['accent']}; color: white; }}
QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 8px; }}
QToolBar {{
    background: {t['bg_surface']};
    border-bottom: 1px solid {t['border']};
    spacing: 4px; padding: 4px;
}}
QToolBar::separator {{ width: 1px; background: {t['border']}; margin: 4px 6px; }}
QToolButton {{
    background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 4px;
}}
QToolButton:hover {{ background: {t['bg_hover']}; border: 1px solid {t['border']}; }}
QToolButton:pressed {{ background: {t['border']}; }}
QPushButton {{
    background: {t['bg_surface']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 6px 14px; min-height: 24px;
}}
QPushButton:hover {{
    background: {t['bg_hover']};
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
QPushButton:disabled {{ color: {t['text_dim']}; background: {t['bg_surface_alt']}; border-color: {t['border']}; }}
QTabWidget::pane {{ border: 1px solid {t['border']}; background: {t['bg_surface']}; border-radius: 6px; }}
QTabBar::tab {{
    background: {t['bg_surface_alt']};
    border: 1px solid {t['border']};
    border-bottom-color: {t['bg_surface']};
    padding: 7px 16px; margin-right: 2px;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{ background: {t['bg_surface']}; font-weight: bold; color: {t['accent']}; border-bottom: none; }}
QTabBar::tab:hover:!selected {{ background: {t['bg_hover']}; }}
QTableWidget {{
    background: {t['bg_input']};
    gridline-color: {t['border']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    alternate-background-color: {t['bg_surface_alt']};
    selection-background-color: {t['accent']};
    selection-color: white;
}}
QTableWidget::item {{ padding: 4px 6px; }}
QTableWidget::item:hover {{ background: {t['bg_hover']}; }}
QHeaderView::section {{
    background: {t['header_bg']};
    border: 1px solid {t['border']};
    padding: 5px 8px; font-weight: bold;
    border-radius: 0;
}}
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {t['bg_input']};
    color: {t['text']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 5px 8px;
}}
QComboBox {{
    background-color: {t['bg_input']};
    color: {t['text']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 5px 8px;
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {t['border_focus']};
}}
QComboBox QAbstractItemView {{
    background-color: {t['bg_input']};
    color: {t['text']};
    selection-background-color: {t['accent']};
    selection-color: #FFFFFF;
    border: 1px solid {t['border']};
    border-radius: 6px;
}}
QDialog, QMessageBox {{
    background-color: {t['bg_primary']};
    color: {t['text']};
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
    background: {t['bg_surface']};
    border-top: 1px solid {t['border']};
    color: {t['text_secondary']};
}}
QScrollBar:vertical {{
    background: {t['scrollbar_bg']}; width: 12px; border: none; border-radius: 6px;
}}
QScrollBar::handle:vertical {{
    background: {t['scrollbar_handle']}; border: none; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {t['scrollbar_hover']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    background: none; height: 0px; border: none;
}}
QScrollBar:horizontal {{
    background: {t['scrollbar_bg']}; height: 12px; border: none; border-radius: 6px;
}}
QScrollBar::handle:horizontal {{
    background: {t['scrollbar_handle']}; border: none; border-radius: 5px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {t['scrollbar_hover']}; }}
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
        
        self.player.setAudioOutput(None)
        if device is not None:
            self.audio_output = QAudioOutput(device, self)
        else:
            self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(self._volume)
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
            
        self.player.setAudioOutput(None)
        if device is not None:
            self.audio_output = QAudioOutput(device, self)
        else:
            self.audio_output = QAudioOutput(self)
        self._apply_output_volume()
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

    def feed_digit(self, digit: str):
        digit = str(digit).strip()
        if not digit:
            return
        if time.time() < self._cooldown_until:
            return
        self._last_emitted = ""
        self._silence_count = 0
        self._last_digit_time = time.time()
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

        if time.time() < self._cooldown_until:
            return

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
                self._cooldown_until = time.time() + 3.0
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

    def set_params(self, freq_tol: int = 20, rms_threshold: float = 0.01,
                   device=None):
        self._tol    = freq_tol
        self._thresh = rms_threshold
        self._device = device
        if self._running:
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
        if hasattr(self, '_stream') and self._stream is not None:
            try:
                self._stream.abort()
            except Exception:
                pass
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
        fft   = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
        freqs = np.fft.rfftfreq(len(samples), 1 / self._sr)

        def peak_near(target):
            mask = (freqs >= target - self._tol) & (freqs <= target + self._tol)
            if not np.any(mask):
                return 0.0
            return float(np.max(fft[mask]))

        row_vals = [(peak_near(f), f) for f in ROW_FREQS]
        col_vals = [(peak_near(f), f) for f in COL_FREQS]
        best_row = max(row_vals, key=lambda x: x[0])
        best_col = max(col_vals, key=lambda x: x[0])

        if best_row[0] < 15 or best_col[0] < 15:
            return ""
        return DTMF_FREQS.get((best_row[1], best_col[1]), "")

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
            
        mono = indata[:, 0] if indata.ndim > 1 else indata
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
        self._audio_queue = queue.Queue(maxsize=100)
        self._external_input_callbacks = []

    def register_input_callback(self, cb):
        self._external_input_callbacks.append(cb)

    def unregister_input_callback(self, cb):
        self._external_input_callbacks = [c for c in self._external_input_callbacks if c is not cb]

    def set_devices(self, in_device, out_device):
        self._in_device = in_device
        self._out_device = out_device
        if self._running:
            self.stop()
            self.start()

    def set_volume(self, vol: float):
        self._volume = max(0.0, min(1.0, vol))

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
        if hasattr(self, '_in_stream') and self._in_stream is not None:
            try: self._in_stream.abort()
            except: pass
        if hasattr(self, '_out_stream') and self._out_stream is not None:
            try: self._out_stream.abort()
            except: pass
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
                for cb in self._external_input_callbacks:
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
                    if data.shape[1] == out_channels:
                        outdata[:] = data * self._volume
                    else:
                        for ch in range(out_channels):
                            outdata[:, ch] = data[:, 0] * self._volume
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


class LiveClock(QLCDNumber):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDigitCount(8)
        self.setSegmentStyle(QLCDNumber.SegmentStyle.Filled)
        t = _current_theme
        self.setStyleSheet(f"""
            QLCDNumber {{
                background: {t['clock_bg']};
                color: {t['clock_color']};
                border: 1px solid {t['border']};
                border-radius: 6px;
            }}
        """)
        self.setMinimumHeight(65)
        t2 = QTimer(self)
        t2.timeout.connect(self._tick)
        t2.start(1000)
        self._tick()

    def _tick(self):
        self.display(datetime.now().strftime("%H:%M:%S"))


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
#  VENTANA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Radio XP Automator  –  Suite de Automatización")
        self.resize(1200, 810)
        self.setMinimumSize(950, 680)
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
        self._tts_worker: TTSWorker | None = None
        self._dtmf_activating = False
        self._remote_dtmf_active = False
        self._remote_resume_pending = False
        self._remote_resume_url: str | None = None
        self._remote_break_active = False
        self._remote_break_start_seq = ""
        self._remote_break_return_seq = ""

        # ── Variables de estado ────────────────────────────────────────────
        self._dtmf_log: list[str]  = []
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
        
        print("[INIT] Señales DTMF conectadas correctamente")
        print("[INIT] Señales de botones conectadas correctamente")

        # ── UI ─────────────────────────────────────────────────────────────
        self._setup_menus()
        self._setup_ui()
        self._setup_statusbar()

        # ── Cargar datos persistidos ─────────────────────────────────────
        self._load_library_from_disk()
        self._load_remotes_from_disk()
        self._load_playlist_from_disk()

        # ── Timer VU demo (cuando no hay audio real) ───────────────────────
        self._demo_vu = QTimer(self)
        self._demo_vu.timeout.connect(self._demo_vu_tick)
        self._demo_vu.start(100)

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
    #  UI PRINCIPAL
    # ═══════════════════════════════════════════════════
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        grid = QGridLayout(central)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setSpacing(10)

        grid.addWidget(self._build_consola(),     0, 0)
        grid.addWidget(self._build_dtmf(),        0, 1)
        grid.addWidget(self._build_reproductor(), 0, 2)
        grid.addWidget(self._build_biblioteca(),  1, 0, 1, 2)
        grid.addWidget(self._build_audio(),       1, 2)

        grid.setRowStretch(0, 2)
        grid.setRowStretch(1, 3)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

    # ─────────────────────── PANEL: CONSOLA ────────────────────────────────
    def _build_consola(self) -> XPPanel:
        p = XPPanel("Consola de Emisión", "DateandTime.png")
        lay = p.content_layout
        lay.setSpacing(5)

        # ── Fila 1: Reloj + LEDs ──
        top = QHBoxLayout()
        top.setSpacing(8)

        self._clock = LiveClock()
        self._clock.setFixedHeight(45)
        top.addWidget(self._clock, 1)

        self._led_onair  = LEDIndicator(QColor(255, 30,  30))
        self._led_signal = LEDIndicator(QColor(0,  210,  0))
        self._led_dtmf   = LEDIndicator(QColor(255, 180,  0))
        self._led_remote = LEDIndicator(QColor(100, 180, 255))

        led_wrap = QHBoxLayout()
        led_wrap.setSpacing(6)
        for led, txt in [(self._led_onair,"ON AIR"),(self._led_signal,"SEÑAL"),
                         (self._led_dtmf,"DTMF"),(self._led_remote,"REMOTO")]:
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

        # ── Fila 2: Botones principales en grid 2x2 ──
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

        btn_grid.addWidget(self.btn_signal,    0, 0)
        btn_grid.addWidget(self.btn_pauta,     0, 1)
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
        btn_clr.setFixedSize(70, 22)
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
        self._table_playlist = QTableWidget(0, 5)
        self._table_playlist.setHorizontalHeaderLabels(["#", "Artista", "Título", "Duración", "Estado"])
        self._table_playlist.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table_playlist.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table_playlist.setAlternatingRowColors(True)
        self._table_playlist.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table_playlist.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table_playlist.verticalHeader().setVisible(False)
        self._table_playlist.verticalHeader().setDefaultSectionSize(28)
        self._table_playlist.doubleClicked.connect(self._playlist_double_click)
        self._table_playlist.setToolTip("Doble clic para reproducir la canción seleccionada")
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
        p  = XPPanel("Control de Audio", "AudioDevices.png")
        lay = p.content_layout

        # VU Meters
        vu_frame = QFrame()
        vu_frame.setObjectName("vuFrame")
        vu_frame.setStyleSheet(f"#vuFrame {{ background:{T('vu_bg')}; border:1px solid {T('border')}; border-radius:4px; }}")
        vu_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        vu_frame.setFixedHeight(80)
        vu_outer = QVBoxLayout(vu_frame)
        vu_outer.setSpacing(1)
        vu_outer.setContentsMargins(6,4,6,4)

        self._vu_bars: list[VUBar] = []
        
        # Barra VU L (arriba)
        vu_l_row = QHBoxLayout()
        lbl_l = QLabel("L")
        lbl_l.setStyleSheet(f"color:{T('vu_label')}; font-size:7pt; font-weight:bold;")
        lbl_l.setFixedWidth(10)
        vu_l_row.addWidget(lbl_l)
        main_vu_l = VUBar()
        vu_l_row.addWidget(main_vu_l)
        vu_outer.addLayout(vu_l_row)
        self._vu_bars.append(main_vu_l)
        
        # Barra VU R (abajo)
        vu_r_row = QHBoxLayout()
        lbl_r = QLabel("R")
        lbl_r.setStyleSheet(f"color:{T('vu_label')}; font-size:7pt; font-weight:bold;")
        lbl_r.setFixedWidth(10)
        vu_r_row.addWidget(lbl_r)
        main_vu_r = VUBar()
        vu_r_row.addWidget(main_vu_r)
        vu_outer.addLayout(vu_r_row)
        self._vu_bars.append(main_vu_r)
        
        # Crear 2 barras ocultas para no romper el resto del código
        for _ in range(2):
            vb = VUBar()
            vb.hide()
            self._vu_bars.append(vb)

        # dB scale integrada debajo de la barra
        dbl = QHBoxLayout()
        dbl.setSpacing(0)
        dbl.setContentsMargins(2, 0, 2, 0)
        
        labels = ["−∞", "−18", "−12", "−6", "0"]
        for i, dB in enumerate(labels):
            l = QLabel(dB)
            if i == 0:
                l.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            elif i == len(labels) - 1:
                l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            else:
                l.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
                
            l.setStyleSheet(f"color:{T('vu_label')}; font-size:7pt; background:transparent;")
            dbl.addWidget(l, 1)
        vu_outer.addLayout(dbl)
        lay.addWidget(vu_frame)

        # Separador visual
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{T('border')}; max-height:1px;")
        lay.addWidget(sep)

        # Micrófono
        mic_row = QHBoxLayout()
        mic_row.setSpacing(8)
        px_mic = xp_pixmap("AudioDevices.png", 28)
        lbl_mic_icon = QLabel()
        if not px_mic.isNull(): lbl_mic_icon.setPixmap(px_mic)
        mic_row.addWidget(lbl_mic_icon)

        col_mic = QVBoxLayout()
        col_mic.setSpacing(2)
        lbl_mic_t = QLabel("Micrófono")
        lbl_mic_t.setStyleSheet(f"font-weight:bold; color:{T('text')};")
        col_mic.addWidget(lbl_mic_t)
        lbl_mic_s = QLabel("Fuente principal de audio")
        lbl_mic_s.setStyleSheet(f"color:{T('text_secondary')}; font-size:8pt;")
        col_mic.addWidget(lbl_mic_s)
        mic_row.addLayout(col_mic, 1)

        self.btn_mic = QPushButton(" OFF")
        _px_mic_btn = xp_pixmap("Volume.png", 18)
        if not _px_mic_btn.isNull():
            self.btn_mic.setIcon(QIcon(_px_mic_btn))
            self.btn_mic.setIconSize(QSize(18, 18))
        self.btn_mic.setCheckable(True)
        self.btn_mic.setFixedSize(76, 36)
        self.btn_mic.setToolTip("Activar / silenciar micrófono")
        self.btn_mic.toggled.connect(self._toggle_mic)
        self._update_mic_style(False)
        mic_row.addWidget(self.btn_mic)
        lay.addLayout(mic_row)

        # Fuente
        lbl_src = QLabel("Fuente de entrada:")
        lbl_src.setStyleSheet(f"color:{T('text_secondary')}; font-size:8pt; margin-top:4px;")
        lay.addWidget(lbl_src)
        self._mic_src_combo = QComboBox()
        self._mic_src_combo.setToolTip("Seleccionar dispositivo de micrófono")
        lay.addWidget(self._mic_src_combo)
        self._populate_mic_sources()

        # Sliders de volumen
        self._vol_sliders: dict[str, QSlider] = {}
        for label, key, val in [
            ("Volumen Micrófono", "mic", 80),
            ("Volumen Monitor",   "mon", 60),
            ("Ganancia Entrada",  "gain",50),
        ]:
            lbl_v = QLabel(label)
            lbl_v.setStyleSheet(f"color:{T('text_secondary')}; font-size:8pt; margin-top:4px;")
            lay.addWidget(lbl_v)
            row_v = QHBoxLayout()
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(0, 100)
            sl.setValue(val)
            sl.setToolTip(f"{label}: {val}%")
            row_v.addWidget(sl, 1)
            val_lbl = QLabel(f"{val}%")
            val_lbl.setFixedWidth(38)
            val_lbl.setStyleSheet(f"font-size:8pt; color:{T('text_secondary')};")
            row_v.addWidget(val_lbl)
            sl.valueChanged.connect(lambda v, l=val_lbl, s=sl: (
                l.setText(f"{v}%"),
                s.setToolTip(f"{v}%")
            ))
            if key == "mic":
                sl.valueChanged.connect(lambda v: self.passthrough.set_volume(v / 100))
            elif key == "mon":
                sl.valueChanged.connect(lambda v: self.engine.set_volume(v / 100))
            lay.addLayout(row_v)
            self._vol_sliders[key] = sl

        lay.addStretch()
        return p

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
        # Si DTMF está activo, alimentarlo desde el passthrough
        if self._dtmf_on:
            self.dtmf.stop()
            self.dtmf.start_external()
            self.passthrough.register_input_callback(self.dtmf.feed_samples)
        self.passthrough.start()
        self._wave.set_metadata("♪ SEÑAL PRINCIPAL: Audio en vivo  •  RadioSAT XP")
        print("[SIGNAL] ✓ Passthrough iniciado")

    def _stop_main_signal(self):
        self._detach_dtmf_from_passthrough()
        self.passthrough.stop()
        self._wave.set_idle()
        # Reanudar reproductor si estaba reproduciendo antes
        if self._was_playing_before_signal:
            self.engine.play()
            self._was_playing_before_signal = False

    def _detach_dtmf_from_passthrough(self):
        """Desconecta el DTMF del passthrough y restaura modo normal si aplica."""
        self.passthrough.unregister_input_callback(self.dtmf.feed_samples)
        if self.dtmf._external_mode:
            self.dtmf.stop_external()
            if self._dtmf_on:
                print("[DTMF] Programando reinicio del detector interno en 1000ms...")
                QTimer.singleShot(1000, self._start_dtmf_safe)

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
                self.btn_signal.setChecked(False)
                self._signal_on = False
                self._led_signal.set_on(False)
                self._sb_led.set_on(False)
                self.btn_signal.setStyleSheet("")
                self._detach_dtmf_from_passthrough()
                self.passthrough.stop()
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
            print("[DTMF] Iniciando detector...")
            self.dtmf.start()
            self._sb_dtmf_lbl.setText("  DTMF: Escuchando…  ")
            t = _current_theme
            self.btn_dtmf_main.setStyleSheet(f"""
                QPushButton {{ background:{t['warning']};
                    color:white; font-weight:bold; border-radius:6px; border:2px solid {t['warning']}; }}
            """)
            print(f"[DTMF] Secuencia PLAY configurada: {self._dtmf_seq_play.text().strip()}")
            print(f"[DTMF] Secuencia STOP configurada: {self._dtmf_seq_stop.text().strip()}")
        else:
            print("[DTMF] Deteniendo detector...")
            self.dtmf.stop()
            self._sb_dtmf_lbl.setText("  DTMF: inactivo  ")
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
        if len(self._vu_bars) >= 4:
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
            out_dev = self._sd_out_dev_combo.currentData()
            sd.play(samples, sr, device=out_dev)
            if self._remote_dtmf_active:
                self.remote_dtmf.feed_digit(digit)
                self.remote_dtmf.feed_samples(samples)
        except Exception as e:
            QMessageBox.warning(self,"Error de tono", str(e))

    def _on_dtmf_digit(self, digit: str):
        now = time.time()
        
        # Si pasaron más de 5 segundos sin dígitos, limpiar buffer
        if now - self._last_digit_time > 5.0 and self._dtmf_log:
            self._dtmf_log.clear()
        
        self._last_digit_time = now
        self._dtmf_log.append(digit)
        seq = "".join(self._dtmf_log[-10:])
        
        play_seq = self._dtmf_seq_play.text().strip()
        stop_seq = self._dtmf_seq_stop.text().strip()
        
        # Modo normal: mostrar dígitos en display
        self._dtmf_display.setText(seq)
        self._sb_dtmf_lbl.setText(f"  DTMF: [{digit}] {seq}")
        
        if play_seq and seq.endswith(play_seq):
            print(f"[DTMF] === SECUENCIA PLAY DETECTADA: {play_seq} ===")
            self._dtmf_log.clear()
            self._dtmf_cooldown_until = now + 3.0
            if self._remote_on:
                self._apply_dtmf_display_style("success", ">>> PAUTA LOCAL ACTIVADA <<<")
                self._remote_dtmf_action(play_seq)
            else:
                self._apply_dtmf_display_style("success", ">>> PAUTA LOCAL ON <<<")
                self._activate_pauta_from_dtmf()
                
        elif stop_seq and seq.endswith(stop_seq):
            print(f"[DTMF] === SECUENCIA STOP DETECTADA: {stop_seq} ===")
            self._dtmf_log.clear()
            self._dtmf_cooldown_until = now + 3.0
            if self._remote_on:
                self._apply_dtmf_display_style("success", ">>> SEÑAL REMOTA <<<")
                self._return_to_remote_from_dtmf()
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
            self._signal_on = False
            self._led_signal.set_on(False)
            self._sb_led.set_on(False)
            self.btn_signal.setChecked(False)
            self.btn_signal.setStyleSheet("")
            self._detach_dtmf_from_passthrough()
            self.passthrough.stop()
        
        # 3. Activar Pauta Local
        self._pauta_on = True
        self.btn_pauta.setChecked(True)
        t = _current_theme
        self.btn_pauta.setStyleSheet(f"""
            QPushButton {{ background:{t['success']};
                color:white; font-weight:bold; border-radius:6px; border:2px solid {t['success']}; }}
        """)
        self.engine.play(0)
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
        in_dev = self._dtmf_dev_combo.currentData()
        out_dev = self._sd_out_dev_combo.currentData()
        print(f"[DTMF→SIGNAL] Dispositivos: in={in_dev}, out={out_dev}")
        if in_dev is not None and out_dev is not None:
            self.passthrough.set_devices(in_dev, out_dev)
            # DTMF ya está activo — ponerlo en modo externo (alimentado por passthrough)
            self.dtmf.stop()
            self.dtmf.start_external()
            self.passthrough.register_input_callback(self.dtmf.feed_samples)
            self.passthrough.start()
            self._wave.set_metadata("♪ SEÑAL PRINCIPAL: Audio en vivo  •  RadioSAT XP")
            print("[DTMF→SIGNAL] ✓ Señal Principal activada correctamente")
        else:
            print("[DTMF→SIGNAL] ERROR: Dispositivos no configurados")
            self._apply_dtmf_display_style("danger", ">>> ERROR: CONFIGURA DISPOSITIVOS <<<")
        self._dtmf_activating = False

    def _on_dtmf_level(self, l: float, r: float):
        if len(self._vu_bars) >= 4:
            # Micrófono — solo barras ocultas (no interfiere con visualización principal)
            self._vu_bars[2].set_value(min(l, 1.0))
            self._vu_bars[3].set_value(min(r * 0.9, 1.0))

    def _on_dtmf_status(self, status: str):
        if hasattr(self, '_lbl_detector_status'):
            self._lbl_detector_status.setText(status)
        # print(f"[DTMF STATUS] {status}")

    def _on_passthrough_level(self, l: float, r: float):
        if len(self._vu_bars) >= 4:
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

    def _remove_from_playlist(self):
        row = self._table_playlist.currentRow()
        if row < 0:
            return
        self.engine.remove_index(row)
        self._table_playlist.removeRow(row)
        self._renumber_playlist()
        self._save_playlist_to_disk()

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
        self._lbl_current_track.setText(f"♪  {title}  –  {artist}  [{duration}]")
        self._lbl_dur.setText(duration)
        self._sb_track_lbl.setText(f"  ▶ {artist} – {title}  ")
        # Actualizar estado en tabla
        t = _current_theme
        for r in range(self._table_playlist.rowCount()):
            st_item = self._table_playlist.item(r, 4)
            if st_item:
                if r == idx:
                    st_item.setText("▶ Sonando")
                    st_item.setBackground(QBrush(QColor(t["accent"]).lighter(180)))
                elif r < idx:
                    st_item.setText("✓ Emitida")
                    st_item.setBackground(QBrush(QColor(t["bg_surface_alt"])))
                else:
                    st_item.setText("En cola")
                    st_item.setBackground(QBrush(QColor(0,0,0,0)))

    def _on_playback_state(self, state: str):
        if state == "playing":
            self.btn_play.setIcon(QIcon(xp_pixmap("Pause.png", 16)))
            self._lbl_on_air.setVisible(True)
        elif state == "paused":
            self.btn_play.setIcon(QIcon(xp_pixmap("Play.png", 16)))
            self._lbl_on_air.setVisible(False)
            self._wave._active = False
        else:
            self.btn_play.setIcon(QIcon(xp_pixmap("Play.png", 16)))
            self._lbl_on_air.setVisible(False)
            self._wave.set_idle()
            for r in range(self._table_playlist.rowCount()):
                st = self._table_playlist.item(r, 4)
                if st and st.text() == "▶ Sonando":
                    st.setText("En cola")
                    st.setBackground(QBrush(QColor(0,0,0,0)))

    def _on_position_tick(self, ms_cur: int, ms_total: int):
        if self._seeking:
            return
        if ms_total > 0:
            pct = ms_cur / ms_total
            self._song_slider.setValue(int(pct * 1000))
        secs = ms_cur // 1000
        self._lbl_pos.setText(f"{secs//60}:{secs%60:02d}")

    def _on_engine_level(self, l: float, r: float):
        self._vu_bars[0].set_value(l)
        self._vu_bars[1].set_value(r)
        self._wave.push_level((l + r) / 2)

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

    def _del_from_library(self):
        row = self._table_library.currentRow()
        if row >= 0:
            self._table_library.removeRow(row)
            self._lbl_lib_count.setText(f"  {self._table_library.rowCount()} archivos")

    def _clear_library(self):
        if QMessageBox.question(self, "Limpiar Biblioteca",
            "¿Eliminar todos los elementos de la biblioteca?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self._table_library.setRowCount(0)
            self._lbl_lib_count.setText("  0 archivos")

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

            row = self._table_pautas.rowCount()
            self._table_pautas.insertRow(row)
            for c, v in enumerate([Path(f).name, cliente, spot,
                                    info["duration"], "18:00, 20:00", "L-V"]):
                item = QTableWidgetItem(v)
                item.setToolTip(f)
                self._table_pautas.setItem(row, c, item)

    def _del_pauta(self):
        row = self._table_pautas.currentRow()
        if row >= 0:
            self._table_pautas.removeRow(row)

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
            self._vu_bars[2].set_value(0.5)
        else:
            self._vu_bars[2].set_value(0.0)

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
        self._clock.setStyleSheet(f"""
            QLCDNumber {{
                background: {T('clock_bg')};
                color: {T('clock_color')};
                border: 1px solid {T('border')};
                border-radius: 6px;
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
        self._save_remotes_to_disk()
        self._save_playlist_to_disk()
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
            
            path = os.path.join(self._get_data_dir(), "library.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error guardando biblioteca: {e}")

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
            
            path = os.path.join(self._get_data_dir(), "playlist.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
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


# ══════════════════════════════════════════════════════════════════════════════
#  PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
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
