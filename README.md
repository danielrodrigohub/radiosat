# RadioSAT XP - Radio Automation Suite

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-6.5+-green?logo=qt&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)

> **Professional radio automation suite** with a nostalgic Windows XP aesthetic. Real-time audio playback, DTMF tone detection, live streaming, playlist management, and broadcast control — all in one application.

<p align="center">
  <img src="winxpicons/SoundandAudioDevices.png" width="80" alt="RadioSAT"/>
</p>

---

## Windows XP Icons Used

<p align="center">
  <img src="winxpicons/Play.png" width="32" alt="Play"/> 
  <img src="winxpicons/Pause.png" width="32" alt="Pause"/> 
  <img src="winxpicons/Stop.png" width="32" alt="Stop"/> 
  <img src="winxpicons/Back.png" width="32" alt="Previous"/> 
  <img src="winxpicons/Forward.png" width="32" alt="Next"/> 
  <img src="winxpicons/Volume.png" width="32" alt="Volume"/> 
  <img src="winxpicons/Volume Level.png" width="32" alt="Volume Level"/> 
  <img src="winxpicons/AudioDevices.png" width="32" alt="Audio Devices"/> 
  <img src="winxpicons/SoundandAudioDevices.png" width="32" alt="Sound"/> 
  <img src="winxpicons/Audio CD.png" width="32" alt="Audio CD"/> 
  <img src="winxpicons/AudioCD.png" width="32" alt="AudioCD"/> 
  <img src="winxpicons/Record.png" width="32" alt="Record"/> 
  <img src="winxpicons/Chip.png" width="32" alt="Chip"/> 
  <img src="winxpicons/DateandTime.png" width="32" alt="Clock"/> 
  <img src="winxpicons/MyMusic.png" width="32" alt="Music"/> 
  <img src="winxpicons/Network Folder.png" width="32" alt="Playlist"/> 
  <img src="winxpicons/Remote Desktop.png" width="32" alt="Remote"/> 
  <img src="winxpicons/VPN Connection.png" width="32" alt="VPN"/> 
  <img src="winxpicons/System Properties.png" width="32" alt="Settings"/> 
  <img src="winxpicons/Add.png" width="32" alt="Add"/> 
  <img src="winxpicons/Delete.png" width="32" alt="Delete"/> 
  <img src="winxpicons/Search.png" width="32" alt="Search"/> 
  <img src="winxpicons/Save.png" width="32" alt="Save"/> 
  <img src="winxpicons/Open.png" width="32" alt="Open"/> 
  <img src="winxpicons/IE Refresh.png" width="32" alt="Refresh"/> 
  <img src="winxpicons/OE Send.png" width="32" alt="Send"/> 
  <img src="winxpicons/Alert.png" width="32" alt="Alert"/> 
  <img src="winxpicons/MediaPlayer.png" width="32" alt="Media Player"/> 
  <img src="winxpicons/WindowsMediaPlayer.png" width="32" alt="WMP"/> 
</p>

---

## Table of Contents

- [Description](#description)
- [Features](#features)
- [Architecture](#architecture)
- [Main Workflow](#main-workflow)
- [DTMF Detection](#dtmf-detection)
- [System States](#system-states)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
  - [Console Panel](#-console-panel)
  - [DTMF Configuration](#-dtmf-configuration)
  - [Player & Playlist](#-player--playlist)
  - [Media Library](#-media-library)
  - [Audio Control](#-audio-control)
  - [Main Signal](#-main-signal-senal-principal)
  - [Remote Signal](#-remote-signal-senal-remota)
  - [Local Break](#-local-break-pauta-local)
- [Theme System](#theme-system)
- [Data Persistence](#data-persistence)
- [Dependencies](#dependencies)
- [License](#license)
- [Versión en Español](#versión-en-español)

---

## Description

RadioSAT XP is a complete radio broadcast automation system built with **PyQt6**. It combines real-time audio processing, DTMF tone detection for remote triggering, playlist management, and live streaming support — all wrapped in a beautiful Windows XP-inspired interface with original XP icons.

### Use Cases

- **Community Radio Stations** — Automate music, ads, and live programming
- **Internet Radio** — Manage streaming playlists with remote control
- **Broadcast Engineering** — DTMF-triggered automation for remote sites
- **Podcast Production** — Audio playback with professional controls

---

## Features

| Feature | Icon | Description |
|---------|------|-------------|
| **Audio Playback** | <img src="winxpicons/Play.png" width="24"/> | Play, pause, stop, next, previous with QtMultimedia |
| **DTMF Detection** | <img src="winxpicons/Chip.png" width="24"/> | Real-time FFT-based DTMF tone decoding |
| **VU Meters** | <img src="winxpicons/Volume Level.png" width="24"/> | Animated 60 FPS level meters with peak hold |
| **Playlist Manager** | <img src="winxpicons/Network Folder.png" width="24"/> | Add, remove, reorder, save/load M3U files |
| **Media Library** | <img src="winxpicons/MyMusic.png" width="24"/> | Import folders, search, filter by artist/title/album |
| **Microphone** | <img src="winxpicons/AudioDevices.png" width="24"/> | ON/OFF mute with real-time monitoring |
| **Volume Control** | <img src="winxpicons/Volume.png" width="24"/> | Multiple independent volume sliders |
| **TTS** | <img src="winxpicons/Alert.png" width="24"/> | Text-to-Speech via pyttsx3 |
| **Live Clock** | <img src="winxpicons/DateandTime.png" width="24"/> | Real-time HH:MM:SS display |
| **Remote Streaming** | <img src="winxpicons/Remote Desktop.png" width="24"/> | Play internet radio streams with DTMF control |
| **Audio Passthrough** | <img src="winxpicons/Audio CD.png" width="24"/> | Live mic-to-output signal routing |
| **Ad Scheduling** | <img src="winxpicons/VPN Connection.png" width="24"/> | Scheduled ad breaks with auto-return |
| **Dark/Light Theme** | <img src="winxpicons/System Properties.png" width="24"/> | Switchable dark and light UI themes |
| **XP Icons** | <img src="winxpicons/Activate Windows.ico" width="24"/> | Original Windows XP icon set throughout the UI |

---

## Architecture

<p align="center">
  <img src="winxpicons/SoundandAudioDevices.png" width="48" alt="Architecture"/>
</p>

```mermaid
graph TD
    MW[MainWindow<br/>RadioSAT XP] --> AE[AudioEngine<br/>QtMultimedia]
    MW --> DTMF[DTMFDetector<br/>FFT + sounddevice]
    MW --> PT[AudioPassthrough<br/>Input → Output]
    MW --> RE[RemoteStreamEngine<br/>Stream Playback]
    MW --> RD[StreamDTMFDetector<br/>Remote DTMF]
    MW --> TTS[TTSWorker<br/>pyttsx3]

    AE -->|track_changed| UI[UI Updates]
    AE -->|playback_state| UI
    AE -->|position_tick| UI
    AE -->|level_update| VU[VU Meters]

    DTMF -->|digit_detected| SEQ[Sequence Matcher]
    DTMF -->|level_update| VU

    PT -->|level_update| VU

    RE -->|state_changed| UI
    RE -->|metadata_update| UI

    RD -->|action_detected| ACT[Action Handler]
    RD -->|level_update| VU

    SEQ -->|play_seq| PAUTA[Activate Pauta]
    SEQ -->|stop_seq| SIGNAL[Activate Signal]

    ACT -->|start_seq| PAUTA
    ACT -->|return_seq| REMOTE[Return to Remote]

    style MW fill:#2A4A8A,stroke:#1E3A7A,color:#fff
    style AE fill:#3366BB,stroke:#2255AA,color:#fff
    style DTMF fill:#FFB020,stroke:#E09000,color:#000
    style PT fill:#00CC66,stroke:#00AA55,color:#fff
    style RE fill:#4A9EFF,stroke:#2A7FFF,color:#fff
    style RD fill:#FF4444,stroke:#DD2222,color:#fff
    style TTS fill:#8888A0,stroke:#666680,color:#fff
```

### Component Overview

| Component | Icon | Purpose | Thread |
|-----------|------|---------|--------|
| `AudioEngine` | <img src="winxpicons/MediaPlayer.png" width="20"/> | Local file/stream playback via QMediaPlayer | Main (Qt) |
| `DTMFDetector` | <img src="winxpicons/Chip.png" width="20"/> | Captures mic input, decodes DTMF via FFT | Background |
| `AudioPassthrough` | <img src="winxpicons/Audio CD.png" width="20"/> | Routes mic input to audio output in real-time | Background |
| `RemoteStreamEngine` | <img src="winxpicons/Remote Desktop.png" width="20"/> | Plays remote HTTP streams | Main (Qt) |
| `StreamDTMFDetector` | <img src="winxpicons/Chip.png" width="20"/> | Analyzes remote audio for DTMF via FFmpeg | Main (Qt) |
| `TTSWorker` | <img src="winxpicons/Alert.png" width="20"/> | Text-to-Speech in isolated thread | QThread |

---

## Main Workflow

<p align="center">
  <img src="winxpicons/System Properties.png" width="48" alt="Workflow"/>
</p>

```mermaid
flowchart TD
    START([Application Start]) --> LOAD[Load Saved Data<br/>Library, Playlist, Remotes]
    LOAD --> CONFIG[Configure Audio Devices<br/>Input & Output]
    CONFIG --> READY{System Ready}

    READY -->|User Action| CHOICE{Choose Mode}

    CHOICE -->|Signal Button| SIGNAL[Señal Principal<br/>Live Audio Passthrough]
    CHOICE -->|Pauta Button| PAUTA[Pauta Local<br/>Playlist Playback]
    CHOICE -->|Remote Button| REMOTE[Señal Remota<br/>Stream + DTMF Monitor]
    CHOICE -->|DTMF Button| DTMF_MODE[DTMF Detection<br/>Listen for Tones]

    SIGNAL --> MONITOR[Monitor VU Meters]
    PAUTA --> MONITOR
    REMOTE --> MONITOR
    DTMF_MODE --> MONITOR

    MONITOR --> DTMF_CHECK{DTMF Sequence<br/>Detected?}

    DTMF_CHECK -->|Play Sequence| TRIGGER_PAUTA[Trigger Pauta Local]
    DTMF_CHECK -->|Stop Sequence| TRIGGER_SIGNAL[Trigger Signal / Return]
    DTMF_CHECK -->|No| MONITOR

    TRIGGER_PAUTA --> PAUTA
    TRIGGER_SIGNAL --> SIGNAL
    TRIGGER_SIGNAL -->|If Remote Active| REMOTE

    PAUTA -->|Playlist Ends| CHECK_REMOTE{Remote<br/>Pending?}
    CHECK_REMOTE -->|Yes| REMOTE
    CHECK_REMOTE -->|No| READY

    style START fill:#00CC66,color:#fff
    style READY fill:#4A9EFF,color:#fff
    style SIGNAL fill:#FF4444,color:#fff
    style PAUTA fill:#00CC66,color:#fff
    style REMOTE fill:#4A9EFF,color:#fff
    style DTMF_MODE fill:#FFB020,color:#000
```

---

## DTMF Detection

<p align="center">
  <img src="winxpicons/Chip.png" width="48" alt="DTMF"/>
</p>

RadioSAT uses **dual-tone multi-frequency signaling (DTMF)** to remotely trigger actions. This is commonly used in radio broadcasting for remote control of automation systems.

### How It Works

```mermaid
flowchart LR
    MIC[🎤 Audio Input] --> CAPTURE[Capture Block<br/>1024/2048 samples]
    CAPTURE --> RMS{RMS > Threshold?}

    RMS -->|No| SILENCE[Silence Counter]
    SILENCE --> RESET[Reset Last Digit]
    RESET --> CAPTURE

    RMS -->|Yes| WINDOW[Hanning Window]
    WINDOW --> FFT[FFT Analysis]
    FFT --> ROW[Find Best Row Freq<br/>697, 770, 852, 941 Hz]
    FFT --> COL[Find Best Col Freq<br/>1209, 1336, 1477, 1633 Hz]

    ROW --> MATCH{Row + Col<br/>Valid Match?}
    COL --> MATCH

    MATCH -->|Yes| DIGIT[Decode DTMF Digit<br/>0-9, *, #, A-D]
    MATCH -->|No| CAPTURE

    DIGIT --> BUFFER[Add to Sequence Buffer]
    BUFFER --> SEQ_CHECK{Sequence Matches<br/>Play or Stop?}

    SEQ_CHECK -->|Play Seq| ACTIVATE[Activate Pauta/Remote Action]
    SEQ_CHECK -->|Stop Seq| DEACTIVATE[Activate Signal/Return]
    SEQ_CHECK -->|Partial| CAPTURE

    style MIC fill:#FF4444,color:#fff
    style FFT fill:#4A9EFF,color:#fff
    style DIGIT fill:#FFB020,color:#000
    style ACTIVATE fill:#00CC66,color:#fff
    style DEACTIVATE fill:#FF4444,color:#fff
```

### DTMF Frequency Matrix

| | **1209 Hz** | **1336 Hz** | **1477 Hz** | **1633 Hz** |
|---|:---:|:---:|:---:|:---:|
| **697 Hz** | 1 | 2 | 3 | A |
| **770 Hz** | 4 | 5 | 6 | B |
| **852 Hz** | 7 | 8 | 9 | C |
| **941 Hz** | * | 0 | # | D |

### Default Trigger Sequences

| Sequence | Icon | Action |
|----------|------|--------|
| `420590` | <img src="winxpicons/Play.png" width="16"/> | Start Pauta Local (ad break) |
| `609700` | <img src="winxpicons/Stop.png" width="16"/> | Stop Pauta / Return to Signal |

These can be customized in the **DTMF Configuration** panel.

---

## System States

<p align="center">
  <img src="winxpicons/System Restore.png" width="48" alt="States"/>
</p>

```mermaid
stateDiagram-v2
    [*] --> Ready: App Start

    Ready --> MainSignal: Signal Button ON
    Ready --> LocalPauta: Pauta Button ON
    Ready --> RemoteSignal: Remote Button ON
    Ready --> DTMFListening: DTMF Button ON

    MainSignal --> Ready: Signal Button OFF
    MainSignal --> LocalPauta: DTMF Play Seq

    LocalPauta --> Ready: Pauta Button OFF
    LocalPauta --> MainSignal: DTMF Stop Seq
    LocalPauta --> RemoteSignal: Playlist Ends + Remote Pending
    LocalPauta --> DTMFWaitReturn: Playlist Ends + Break Active

    RemoteSignal --> Ready: Remote Button OFF
    RemoteSignal --> RemotePautaBreak: DTMF Start Seq

    RemotePautaBreak --> RemoteSignal: DTMF Return Seq
    RemotePautaBreak --> DTMFWaitReturn: Playlist Ends

    DTMFWaitReturn --> RemoteSignal: DTMF Return Seq

    DTMFListening --> Ready: DTMF Button OFF
    DTMFListening --> LocalPauta: DTMF Play Seq
    DTMFListening --> MainSignal: DTMF Stop Seq

    state RemotePautaBreak {
        [*] --> MuteRemote
        MuteRemote --> PlayLocalPauta
        PlayLocalPauta --> WaitReturnTone
    }

    note right of MainSignal
        Live audio passthrough
        Input → Output
    end note

    note right of LocalPauta
        Playlist playback
        Auto-advances tracks
    end note

    note right of RemoteSignal
        Internet stream + DTMF
        monitoring
    end note
```

### State Descriptions

| State | Icon | LED | Description |
|-------|------|-----|-------------|
| **Ready** | <img src="winxpicons/Success.png" width="16"/> | 🟢 Green | System idle, waiting for input |
| **Main Signal** | <img src="winxpicons/Record.png" width="16"/> | 🔴 Red | Live audio passthrough active (ON AIR) |
| **Local Pauta** | <img src="winxpicons/Play.png" width="16"/> | 🟢 Green | Playing local playlist (ads/music) |
| **Remote Signal** | <img src="winxpicons/Remote Desktop.png" width="16"/> | 🔵 Blue | Remote stream playing with DTMF monitoring |
| **DTMF Listening** | <img src="winxpicons/Chip.png" width="16"/> | 🟡 Amber | Microphone active, detecting DTMF tones |

---

## Installation

<p align="center">
  <img src="winxpicons/Add New Programs.png" width="48" alt="Install"/>
</p>

### Prerequisites

- **Python 3.10+**
- **FFmpeg** (required for remote stream DTMF detection)
- **PortAudio** (required by sounddevice)

### macOS

```bash
# Install Homebrew dependencies
brew install python ffmpeg portaudio

# Clone the repository
git clone https://github.com/danielrodrigohub/radiosat.git
cd radiosat

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install PyQt6 numpy sounddevice mutagen pyttsx3

# Run RadioSAT
python main.py
```

### Windows

```bash
# Install Python from python.org
# Install FFmpeg from ffmpeg.org and add to PATH

# Clone and setup
git clone https://github.com/danielrodrigohub/radiosat.git
cd radiosat

python -m venv .venv
.venv\Scripts\activate

pip install PyQt6 numpy sounddevice mutagen pyttsx3

python main.py
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3 python3-venv ffmpeg portaudio19-dev

git clone https://github.com/danielrodrigohub/radiosat.git
cd radiosat

python3 -m venv .venv
source .venv/bin/activate

pip install PyQt6 numpy sounddevice mutagen pyttsx3

python main.py
```

---

## Usage Guide

### Main Window Layout

<p align="center">
  <img src="winxpicons/My Computer.png" width="48" alt="Main Window"/>
</p>

The RadioSAT interface is organized into 5 main panels:

```
┌─────────────────┬──────────────────┬──────────────────┐
│   CONSOLE       │  DTMF CONFIG     │  PLAYER &        │
│   (Clock, LEDs, │  (Devices,       │  PLAYLIST        │
│    Controls)    │   Parameters)    │  (Transport,     │
│                 │                  │   Table)         │
├─────────────────┴──────────────────┼──────────────────┤
│         MEDIA LIBRARY              │  AUDIO CONTROL   │
│  (Music Library + Ad Scheduling)   │  (VU, Mic, Vol)  │
└────────────────────────────────────┴──────────────────┘
```

---

### <img src="winxpicons/DateandTime.png" width="28"/> Console Panel

The **Console** is the command center for your radio station.

<p align="center">
  <img src="winxpicons/DateandTime.png" width="64" alt="Console"/>
  <img src="winxpicons/Date and Time.png" width="64" alt="Clock"/>
</p>

#### Components

| Component | Icon | Function |
|-----------|------|----------|
| **Live Clock** | <img src="winxpicons/DateandTime.png" width="20"/> | Real-time HH:MM:SS display |
| **ON AIR LED** | <img src="winxpicons/Record.png" width="20"/> | Red when broadcasting |
| **SEÑAL LED** | <img src="winxpicons/Audio CD.png" width="20"/> | Green when main signal active |
| **DTMF LED** | <img src="winxpicons/Chip.png" width="20"/> | Amber when detecting tones |
| **REMOTO LED** | <img src="winxpicons/Remote Desktop.png" width="20"/> | Blue when remote stream active |

#### Action Buttons

| Button | Icon | Action |
|--------|------|--------|
| **SEÑAL PRINCIPAL** | <img src="winxpicons/Audio CD.png" width="20"/> | Toggle live audio passthrough (mic → output) |
| **PAUTA LOCAL** | <img src="winxpicons/VPN Connection.png" width="20"/> | Start/stop local playlist playback |
| **DETECTAR DTMF** | <img src="winxpicons/Chip.png" width="20"/> | Enable/disable DTMF tone detection |
| **SEÑAL REMOTA** | <img src="winxpicons/Remote Desktop.png" width="20"/> | Open remote stream controls |

#### DTMF Display

Shows detected DTMF digits in real-time. Changes color to indicate:
- 🟢 **Green** — Sequence matched (Pauta activated)
- 🔴 **Red** — Sequence matched (Signal activated)
- 🟡 **Amber** — Warning state
- ⚪ **Default** — Normal digit display

---

### <img src="winxpicons/Chip.png" width="28"/> DTMF Configuration

<p align="center">
  <img src="winxpicons/Chip.png" width="64" alt="DTMF Config"/>
  <img src="winxpicons/Manage your Server.ico" width="64" alt="Server"/>
</p>

Three tabs for configuring DTMF detection:

#### Tab: Devices

| Setting | Icon | Description |
|---------|------|-------------|
| **Input Device** | <img src="winxpicons/AudioDevices.png" width="16"/> | Microphone/audio input for tone detection |
| **Output Device** | <img src="winxpicons/Volume.png" width="16"/> | Speaker/headphone for local playback |
| **Remote Output** | <img src="winxpicons/Remote Desktop.png" width="16"/> | Dedicated output for remote stream |
| **Refresh** | <img src="winxpicons/IE Refresh.png" width="16"/> | Update device list |

#### Tab: Parameters

| Parameter | Icon | Default | Description |
|-----------|------|---------|-------------|
| Start Frequency | <img src="winxpicons/Volume Level.png" width="16"/> | 697 Hz | Lower bound of DTMF frequency range |
| End Frequency | <img src="winxpicons/Volume Level.png" width="16"/> | 1633 Hz | Upper bound of DTMF frequency range |
| Minimum Duration | <img src="winxpicons/DateandTime.png" width="16"/> | 40 ms | Minimum tone duration to detect |
| Noise Threshold | <img src="winxpicons/Volume.png" width="16"/> | -30 dB | Minimum signal level to process |
| Tolerance | <img src="winxpicons/System Properties.png" width="16"/> | ±20 Hz | Frequency matching tolerance |
| Play Sequence | <img src="winxpicons/Play.png" width="16"/> | `420590` | DTMF sequence to trigger Pauta |
| Stop Sequence | <img src="winxpicons/Stop.png" width="16"/> | `609700` | DTMF sequence to trigger Signal |

#### Tab: Test

Send test DTMF tones to verify detection:
1. Select digit from dropdown
2. Set duration (50-2000 ms)
3. Click **Send** <img src="winxpicons/OE Send.png" width="16"/>

---

### <img src="winxpicons/Network Folder.png" width="28"/> Player & Playlist

<p align="center">
  <img src="winxpicons/Network Folder.png" width="64" alt="Playlist"/>
  <img src="winxpicons/MediaPlayer.png" width="64" alt="Player"/>
  <img src="winxpicons/WindowsMediaPlayer.png" width="64" alt="WMP"/>
</p>

Full-featured audio player with playlist management.

#### Transport Controls

| Button | Icon | Action |
|--------|------|--------|
| Previous | <img src="winxpicons/Back.png" width="20"/> | Go to previous track |
| Play/Pause | <img src="winxpicons/Play.png" width="20"/> / <img src="winxpicons/Pause.png" width="20"/> | Toggle playback |
| Stop | <img src="winxpicons/Stop.png" width="20"/> | Stop playback |
| Next | <img src="winxpicons/Forward.png" width="20"/> | Go to next track |

#### Playlist Table

| Column | Description |
|--------|-------------|
| # | Track number |
| Artist | Artist name (from ID3 tags) |
| Title | Song title |
| Duration | Track length |
| Status | Current state (Queued/Playing/Played) |

#### Playlist Operations

- **Double-click** a track to play it
- **Drag slider** to seek within track
- **Volume slider** controls playback volume

#### Marquee Display

The scrolling text display shows:
- Current track metadata during playback
- `"ON AIR"` badge when broadcasting
- `"LISTO"` when idle

---

### <img src="winxpicons/MyMusic.png" width="28"/> Media Library

<p align="center">
  <img src="winxpicons/MyMusic.png" width="64" alt="Library"/>
  <img src="winxpicons/My Music.png" width="64" alt="My Music"/>
  <img src="winxpicons/VPN Connection.png" width="64" alt="Pautas"/>
</p>

Organize your audio files and schedule ad breaks.

#### Music Library

| Button | Icon | Action |
|--------|------|--------|
| **Add** | <img src="winxpicons/Add.png" width="16"/> | Add audio files |
| **Import** | <img src="winxpicons/Folder Opened.png" width="16"/> | Import entire folder |
| **URL Streaming** | <img src="winxpicons/Network and Internet.png" width="16"/> | Add streaming URL |
| **Delete** | <img src="winxpicons/Delete.png" width="16"/> | Remove from library |
| **→ Playlist** | <img src="winxpicons/Network Folder.png" width="16"/> | Add to playlist |

#### Search & Filter

| Component | Icon | Description |
|-----------|------|-------------|
| Search box | <img src="winxpicons/Search.png" width="16"/> | Filter by artist, title, or album |
| Filter dropdown | <img src="winxpicons/Document Search.png" width="16"/> | Search in specific field |

#### Ad Scheduling (Pautas)

Manage advertising spots with metadata:

| Column | Description |
|--------|-------------|
| File | Audio filename |
| Client | Advertiser name |
| Spot | Spot/campaign name |
| Duration | Length of ad |
| Schedule | Air times (e.g., "18:00, 20:00") |
| Days | Days of week (e.g., "L-V") |

---

### <img src="winxpicons/AudioDevices.png" width="28"/> Audio Control

<p align="center">
  <img src="winxpicons/AudioDevices.png" width="64" alt="Audio"/>
  <img src="winxpicons/SoundandAudioDevices.png" width="64" alt="Sound"/>
  <img src="winxpicons/Volume.png" width="64" alt="Volume"/>
  <img src="winxpicons/Volume Level.png" width="64" alt="Level"/>
</p>

Monitor and control audio levels.

#### VU Meter

<p align="center">
  <img src="winxpicons/Volume Level.png" width="32" alt="VU"/>
</p>

- **60 FPS** animated horizontal bar
- **Color zones**: Green (safe) → Amber (hot) → Red (peak)
- **Peak hold** indicator with decay
- **dB scale**: −∞, −18, −12, −6, 0

#### Microphone Control

| Component | Icon | Description |
|-----------|------|-------------|
| **ON/OFF Button** | <img src="winxpicons/Volume.png" width="16"/> | Toggle microphone mute |
| **Source Selector** | <img src="winxpicons/AudioDevices.png" width="16"/> | Choose input device |
| **Mic Volume** | <img src="winxpicons/Volume.png" width="16"/> | Input level control |
| **Monitor Volume** | <img src="winxpicons/Volume Level.png" width="16"/> | Output monitoring level |
| **Input Gain** | <img src="winxpicons/System Properties.png" width="16"/> | Signal amplification |

---

### <img src="winxpicons/Audio CD.png" width="28"/> Main Signal (Señal Principal)

<p align="center">
  <img src="winxpicons/Audio CD.png" width="64" alt="Signal"/>
  <img src="winxpicons/AudioCD.png" width="64" alt="AudioCD"/>
  <img src="winxpicons/Record.png" width="64" alt="Record"/>
</p>

The **Main Signal** routes live audio from your microphone/input directly to the output.

```
┌──────────┐      ┌──────────────┐      ┌──────────┐
│ Microphone├─────→│ AudioPassthrough├─────→│ Speaker  │
│  / Input  │      │   (Real-time) │      │ / Output │
└──────────┘      └──────────────┘      └──────────┘
```

**Use case**: Live broadcasting — your voice goes directly to the transmitter/stream.

**Activation**:
1. Click **SEÑAL PRINCIPAL** button <img src="winxpicons/Audio CD.png" width="16"/>
2. LED turns red, button turns red
3. Status bar shows "En Aire"
4. VU meters show live levels

**Deactivation**: Click button again or trigger DTMF stop sequence.

---

### <img src="winxpicons/Remote Desktop.png" width="28"/> Remote Signal (Señal Remota)

<p align="center">
  <img src="winxpicons/Remote Desktop.png" width="64" alt="Remote"/>
  <img src="winxpicons/Remote Desktop Server.png" width="64" alt="Server"/>
  <img src="winxpicons/Remote Assistance.png" width="64" alt="Assist"/>
</p>

Connect to an internet radio stream and monitor it for DTMF commands.

#### How It Works

```mermaid
flowchart LR
    STREAM[🌐 HTTP Stream] --> PLAY[QMediaPlayer<br/>Stream Playback]
    STREAM --> DTMF_MON[FFmpeg Process<br/>PCM Extraction]
    DTMF_MON --> DETECT[StreamDTMFDetector<br/>DTMF Analysis]

    PLAY --> OUTPUT[🔊 Audio Output]
    DETECT --> ACTION{DTMF<br/>Sequence?}

    ACTION -->|Start Seq| BREAK[Start Local Pauta<br/>Mute Remote]
    ACTION -->|Return Seq| RETURN[Resume Remote<br/>Stop Pauta]

    BREAK --> LOCAL[🎵 Local Playlist]
    LOCAL --> RETURN

    style STREAM fill:#4A9EFF,color:#fff
    style DETECT fill:#FFB020,color:#000
    style BREAK fill:#00CC66,color:#fff
    style RETURN fill:#FF4444,color:#fff
```

**Activation**:
1. Click **SEÑAL REMOTA** button <img src="winxpicons/Remote Desktop.png" width="16"/>
2. Enter stream URL in the text field
3. Click **Play** <img src="winxpicons/Play.png" width="16"/>
4. DTMF monitoring starts automatically

**Dedicated Output**: Configure a separate audio device for the remote stream in the DTMF Devices tab.

---

### <img src="winxpicons/VPN Connection.png" width="28"/> Local Break (Pauta Local)

<p align="center">
  <img src="winxpicons/VPN Connection.png" width="64" alt="Pauta"/>
  <img src="winxpicons/Network Folder.png" width="64" alt="Playlist"/>
</p>

The **Pauta** system manages scheduled ad breaks during remote streaming.

#### Break Flow

```mermaid
sequenceDiagram
    participant R as Remote Stream
    participant D as DTMF Detector
    participant P as Pauta Engine
    participant O as Audio Output

    R->>O: Remote audio playing
    R->>D: Monitoring for DTMF

    D->>D: Detects "420590"
    D->>P: Trigger pauta

    P->>R: Mute remote
    P->>O: Start local playlist
    Note over O: Playing ad break

    P->>P: Playlist ends
    P->>D: Wait for return tone

    D->>D: Detects "609700"
    D->>R: Unmute remote
    D->>P: Stop pauta
    Note over O: Back to remote stream
```

**Manual Activation**:
1. Ensure playlist has tracks
2. Click **PAUTA LOCAL** button <img src="winxpicons/VPN Connection.png" width="16"/>
3. Playlist plays sequentially
4. When done, system returns to previous state

---

## Theme System

<p align="center">
  <img src="winxpicons/System Properties.png" width="48" alt="Themes"/>
  <img src="winxpicons/Display Properties.png" width="48" alt="Display"/>
  <img src="winxpicons/Appearance.png" width="48" alt="Appearance"/>
</p>

RadioSAT supports **dark** and **light** themes.

### Toggle Theme

`Configuración → Tema Oscuro` (checkbox)

### Color Palette

| Element | Icon | Dark Theme | Light Theme |
|---------|------|-----------|-------------|
| Background | <img src="winxpicons/Desktop.png" width="16"/> | `#1E1E2E` | `#F5F5F7` |
| Surface | <img src="winxpicons/Application Window.png" width="16"/> | `#2A2A3C` | `#FFFFFF` |
| Accent | <img src="winxpicons/Color Profile.png" width="16"/> | `#4A9EFF` | `#2A7FFF` |
| Success | <img src="winxpicons/Success.png" width="16"/> | `#00CC66` | `#00AA55` |
| Danger | <img src="winxpicons/Critical.png" width="16"/> | `#FF4444` | `#DD2222` |
| Warning | <img src="winxpicons/Important.png" width="16"/> | `#FFB020` | `#E09000` |

---

## Data Persistence

<p align="center">
  <img src="winxpicons/Save.png" width="48" alt="Save"/>
  <img src="winxpicons/Folder Closed.png" width="48" alt="Folder"/>
  <img src="winxpicons/Local Disk.png" width="48" alt="Disk"/>
</p>

RadioSAT automatically saves and loads data on exit/startup:

| File | Icon | Location | Contents |
|------|------|----------|----------|
| `library.json` | <img src="winxpicons/MyMusic.png" width="16"/> | `data/` | Media library entries |
| `playlist.json` | <img src="winxpicons/Network Folder.png" width="16"/> | `data/` | Current playlist tracks |
| `remotes.json` | <img src="winxpicons/Remote Desktop.png" width="16"/> | `data/` | Remote stream URLs |

### Backup

To backup your data, copy the `data/` folder:

```bash
cp -r data/ data_backup/
```

---

## Dependencies

| Package | Icon | Version | Required | Purpose |
|---------|------|---------|----------|---------|
| [PyQt6](https://pypi.org/project/PyQt6/) | <img src="winxpicons/Application Window.png" width="16"/> | ≥6.5 | ✅ Yes | UI framework |
| [numpy](https://pypi.org/project/numpy/) | <img src="winxpicons/Calculator.png" width="16"/> | ≥1.24 | ✅ Yes | FFT for DTMF detection |
| [sounddevice](https://pypi.org/project/sounddevice/) | <img src="winxpicons/SoundandAudioDevices.png" width="16"/> | ≥0.4 | ✅ Yes | Audio capture/playback |
| [mutagen](https://pypi.org/project/mutagen/) | <img src="winxpicons/WindowsMediaPlayer.png" width="16"/> | ≥1.47 | ⚪ Optional | Audio metadata (ID3 tags) |
| [pyttsx3](https://pypi.org/project/pyttsx3/) | <img src="winxpicons/Speech.png" width="16"/> | ≥2.90 | ⚪ Optional | Text-to-Speech |
| [FFmpeg](https://ffmpeg.org/) | <img src="winxpicons/Windows Media Encoder.png" width="16"/> | ≥5.0 | ⚪ Optional | Remote stream DTMF analysis |

### Install All

```bash
pip install PyQt6 numpy sounddevice mutagen pyttsx3
```

### Graceful Degradation

RadioSAT handles missing optional dependencies gracefully:
- Without **mutagen**: <img src="winxpicons/WindowsMediaPlayer.png" width="16"/> Metadata shows filename instead of ID3 tags
- Without **pyttsx3**: <img src="winxpicons/Speech.png" width="16"/> TTS button is disabled
- Without **sounddevice/numpy**: <img src="winxpicons/Chip.png" width="16"/> DTMF detection is disabled
- Without **FFmpeg**: <img src="winxpicons/Remote Desktop.png" width="16"/> Remote stream DTMF is disabled

---

## Project Structure

```
radiosat/
├── main.py                 # Application entry point (3400+ lines)
├── README.md               # This file
├── data/                   # Persisted data (auto-created)
│   ├── library.json
│   ├── playlist.json
│   └── remotes.json
├── icons/                  # Windows XP icons (521 files)
│   ├── AudioDevices.png
│   ├── Chip.png
│   ├── Play.png
│   └── ...
├── winxpicons/             # Windows XP icons with .ico files (556 files)
│   ├── SoundandAudioDevices.png
│   ├── Chip.png
│   ├── Play.png
│   └── ...
├── playlist.m3u            # Sample playlist
└── Test.m3u                # Test playlist
```

---

## License

<p align="center">
  <img src="winxpicons/Key.png" width="48" alt="License"/>
</p>

This project is licensed under the MIT License.

```
MIT License

Copyright (c) 2024 RadioSAT

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Versión en Español

<p align="center">
  <img src="winxpicons/SoundandAudioDevices.png" width="64" alt="RadioSAT"/>
</p>

### Descripción

**RadioSAT XP** es una suite profesional de automatización de radio con estética Windows XP. Combina reproducción de audio en tiempo real, detección de tonos DTMF para activación remota, gestión de playlists y soporte para streaming en vivo.

### Características Principales

| Característica | Icono | Descripción |
|----------------|-------|-------------|
| **Reproducción** | <img src="winxpicons/Play.png" width="20"/> | Play/pausa/stop/siguiente/anterior con QtMultimedia |
| **DTMF** | <img src="winxpicons/Chip.png" width="20"/> | Detección de tonos DTMF en tiempo real vía FFT |
| **VU Meters** | <img src="winxpicons/Volume Level.png" width="20"/> | Medidores de nivel animados a 60 FPS |
| **Playlist** | <img src="winxpicons/Network Folder.png" width="20"/> | Añadir, eliminar, reordenar, guardar/cargar M3U |
| **Biblioteca** | <img src="winxpicons/MyMusic.png" width="20"/> | Importar carpetas, buscar, filtrar por artista/título/álbum |
| **Micrófono** | <img src="winxpicons/AudioDevices.png" width="20"/> | Activar/silenciar con monitoreo en tiempo real |
| **Streaming** | <img src="winxpicons/Remote Desktop.png" width="20"/> | Reproducir streams de internet con control DTMF |
| **Pauta** | <img src="winxpicons/VPN Connection.png" width="20"/> | Pausas publicitarias programadas con retorno automático |
| **Señal** | <img src="winxpicons/Audio CD.png" width="20"/> | Enrutamiento en vivo micrófono → salida |
| **Temas** | <img src="winxpicons/System Properties.png" width="20"/> | Temas oscuro y claro intercambiables |

### Iconos XP del Proyecto

<p align="center">
  <img src="winxpicons/Play.png" width="24"/> 
  <img src="winxpicons/Pause.png" width="24"/> 
  <img src="winxpicons/Stop.png" width="24"/> 
  <img src="winxpicons/Volume.png" width="24"/> 
  <img src="winxpicons/AudioDevices.png" width="24"/> 
  <img src="winxpicons/Chip.png" width="24"/> 
  <img src="winxpicons/DateandTime.png" width="24"/> 
  <img src="winxpicons/MyMusic.png" width="24"/> 
  <img src="winxpicons/Network Folder.png" width="24"/> 
  <img src="winxpicons/Remote Desktop.png" width="24"/> 
  <img src="winxpicons/VPN Connection.png" width="24"/> 
  <img src="winxpicons/System Properties.png" width="24"/> 
  <img src="winxpicons/Add.png" width="24"/> 
  <img src="winxpicons/Delete.png" width="24"/> 
  <img src="winxpicons/Search.png" width="24"/> 
  <img src="winxpicons/Save.png" width="24"/> 
  <img src="winxpicons/Record.png" width="24"/> 
  <img src="winxpicons/Audio CD.png" width="24"/> 
  <img src="winxpicons/MediaPlayer.png" width="24"/> 
  <img src="winxpicons/WindowsMediaPlayer.png" width="24"/> 
</p>

El proyecto utiliza **556 iconos originales de Windows XP** para crear una interfaz nostálgica y profesional.

### Instalación Rápida

```bash
git clone https://github.com/danielrodrigohub/radiosat.git
cd radiosat
python3 -m venv .venv
source .venv/bin/activate
pip install PyQt6 numpy sounddevice mutagen pyttsx3
python main.py
```

### Diagrama de Flujo Principal

```
┌─────────────────────────────────────────────────────────────┐
│                    RADIOSAT XP WORKFLOW                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  Inicio  │───→│  Configurar  │───→│  Elegir Modo     │  │
│  └──────────┘    │  Dispositivos│    └────────┬─────────┘  │
│                  └──────────────┘             │             │
│                                               ▼             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────┐ │   │
│  │  │ SEÑAL   │  │ PAUTA   │  │ REMOTO  │  │ DTMF  │ │   │
│  │  │Principal│  │ Local   │  │ Señal   │  │Detect │ │   │
│  │  │  <img>  │  │  <img>  │  │  <img>  │  │ <img> │ │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └───┬───┘ │   │
│  │       │            │            │            │      │   │
│  │       └────────────┴────────────┴────────────┘      │   │
│  │                        │                            │   │
│  │                        ▼                            │   │
│  │              ┌─────────────────┐                    │   │
│  │              │  Monitor VU     │                    │   │
│  │              │  Meters         │                    │   │
│  │              └────────┬────────┘                    │   │
│  │                       │                             │   │
│  │                       ▼                             │   │
│  │              ┌─────────────────┐                    │   │
│  │              │ DTMF Detectado? │                    │   │
│  │              └────────┬────────┘                    │   │
│  │                       │                             │   │
│  │         ┌─────────────┼─────────────┐               │   │
│  │         ▼             ▼             ▼               │   │
│  │    ┌─────────┐  ┌─────────┐  ┌─────────┐           │   │
│  │    │  Play   │  │  Stop   │  │  No     │           │   │
│  │    │ Sequence│  │ Sequence│  │ Action  │           │   │
│  │    └────┬────┘  └────┬────┘  └────┬────┘           │   │
│  │         │            │            │                 │   │
│  │         ▼            ▼            │                 │   │
│  │    ┌─────────┐  ┌─────────┐      │                 │   │
│  │    │ Activar │  │ Activar │      │                 │   │
│  │    │ Pauta   │  │ Señal   │      │                 │   │
│  │    └─────────┘  └─────────┘      │                 │   │
│  │                                   │                 │   │
│  └───────────────────────────────────┘                 │   │
│                                                         │   │
└─────────────────────────────────────────────────────────┘   │
                                                               │
```

---

<p align="center">
  <b>Built with PyQt6 and Windows XP nostalgia</b>
</p>

<p align="center">
  <img src="winxpicons/SoundandAudioDevices.png" width="48"/> 
  <img src="winxpicons/MediaPlayer.png" width="48"/> 
  <img src="winxpicons/WindowsMediaPlayer.png" width="48"/> 
</p>
