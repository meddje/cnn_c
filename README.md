# 🔍 SilentTrace - Ultrasonic Signal Detector

SilentTrace is a hybrid C + Python tool designed to detect and analyze ultrasonic audio signals (18kHz–22kHz) in real-time. These signals are often used by tracking technologies like ultrasound beacons and are typically inaudible to humans.

## 🎯 Purpose

SilentTrace helps identify potential privacy intrusions from ultrasonic tracking systems by:
- Monitoring ambient audio for ultrasonic signals
- Detecting repetitive patterns that suggest beacon activity  
- Providing real-time alerts and analysis
- Offering a web dashboard for visualization

## 🏗️ Architecture

The system consists of two main components:

### 🔷 Layer 1: Audio Capture (C)
- Real-time PCM audio capture using ALSA
- High-performance audio processing at 44.1kHz
- UNIX socket communication to Python layer
- Minimal CPU overhead for continuous monitoring

### 🟨 Layer 2: Analysis & Visualization (Python)
- FFT-based frequency analysis focused on 18-22kHz range
- Pattern recognition for beacon detection
- Real-time CLI notifications with color coding
- Web dashboard with live frequency graphs
- Historical detection logging

## 📋 Requirements

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y libasound2-dev build-essential python3 python3-pip

# CentOS/RHEL
sudo yum install alsa-lib-devel gcc python3 python3-pip

# Arch Linux
sudo pacman -S alsa-lib gcc python python-pip
```

### Python Dependencies
```bash
cd analysis_python
pip3 install -r requirements.txt
```

## 🚀 Quick Start

### 1. Build the Audio Capture Module
```bash
cd core_c
make install-deps  # Install ALSA development libraries
make               # Compile the audio capture binary
```

### 2. Install Python Dependencies
```bash
cd ../analysis_python
pip3 install -r requirements.txt
```

### 3. Run SilentTrace

#### Basic Mode (CLI only)
```bash
# Terminal 1: Start audio capture
cd core_c
./audio_capture

# Terminal 2: Start analysis
cd ../analysis_python
python3 analyze.py
```

#### With Web Dashboard
```bash
# Terminal 1: Start audio capture
cd core_c
./audio_capture

# Terminal 2: Start analysis with dashboard
cd ../analysis_python
python3 analyze.py --with-dashboard
```

The web dashboard will be available at `http://localhost:5000`

## 🎛️ Configuration

SilentTrace uses a YAML configuration file (`silenttrace_config.yaml`) that's automatically created on first run. Key settings include:

```yaml
detection:
  threshold_db: -40.0          # Detection sensitivity (lower = more sensitive)
  repetition_threshold: 3      # Detections needed to trigger beacon alert
  repetition_window_sec: 10    # Time window for pattern detection

audio:
  ultrasonic_min_freq: 18000   # Lower bound of ultrasonic range
  ultrasonic_max_freq: 22000   # Upper bound of ultrasonic range
  
alerts:
  enable_cli_alerts: true      # Show CLI notifications
  enable_file_logging: true    # Log detections to file
  alert_cooldown_sec: 5        # Minimum time between alerts
```

## 📊 Understanding the Output

### CLI Status Indicators
- ✅ **Normal**: `Listening... | 🔊 Normal ambient noise`
- ⚠️ **Warning**: `Ultrasound spike at 19.6kHz detected!`
- 🚨 **Alert**: `Repetitive ultrasonic pulses detected (possible beacon signal)`

### Web Dashboard Features
- **Real-time Spectrum**: Live frequency analysis graph
- **Detection History**: Timeline of ultrasonic events
- **System Statistics**: Runtime stats and performance metrics
- **Configuration Panel**: Adjust detection parameters

## 🛠️ Advanced Usage

### Custom Detection Thresholds
```bash
# More sensitive detection
SILENTTRACE_THRESHOLD_DB=-50 python3 analyze.py

# Less sensitive (reduce false positives)
SILENTTRACE_THRESHOLD_DB=-30 python3 analyze.py
```

### Debug Mode
```bash
SILENTTRACE_DEBUG=true python3 analyze.py
```

### Dashboard Only (Testing)
```bash
python3 analyze.py --dashboard-only
```

## 📁 Project Structure

```
SilentTrace/
├── core_c/                    # C audio capture layer
│   ├── audio_capture.c        # Main audio capture implementation
│   ├── Makefile              # Build configuration
│   └── silenttrace.sock      # Runtime socket (auto-created)
├── analysis_python/          # Python analysis layer
│   ├── analyze.py            # Main analysis script
│   ├── dashboard.py          # Web dashboard (Flask)
│   ├── utils.py              # Signal processing utilities
│   ├── config.py             # Configuration management
│   ├── requirements.txt      # Python dependencies
│   └── templates/            # Dashboard HTML templates
├── docs/                     # Documentation
├── silenttrace_config.yaml   # Configuration file (auto-created)
├── silenttrace_detections.log # Detection log (auto-created)
├── LICENSE
└── README.md
```

## 🔧 Troubleshooting

### Audio Device Issues
```bash
# List available audio devices
arecord -l

# Test audio capture
arecord -D default -f S16_LE -r 44100 -c 1 test.wav
```

### Permission Issues
```bash
# Add user to audio group
sudo usermod -a -G audio $USER
# Log out and back in
```

### Socket Connection Errors
```bash
# Remove stale socket
rm -f /tmp/silenttrace.sock

# Check if process is running
ps aux | grep audio_capture
```

### Memory/CPU Issues
```bash
# Monitor resource usage
top -p $(pgrep -f "audio_capture|analyze.py")
```

## 🔒 Privacy & Security

- **No Audio Recording**: Audio data is processed in real-time and not saved to disk
- **Local Processing**: All analysis happens locally, no data sent to external servers
- **Minimal Data Retention**: Only detection events are logged, not raw audio
- **Open Source**: Full source code available for security review

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional signal processing algorithms
- Machine learning-based classification
- Mobile device support
- Additional audio backend support (PulseAudio, etc.)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Legal Notice

SilentTrace is designed for educational and privacy protection purposes. Users are responsible for complying with local laws regarding audio monitoring and privacy. The tool should only be used to monitor environments where you have explicit permission to do so.

