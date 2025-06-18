# SilentTrace Usage Guide

## Quick Start Checklist

### ✅ Prerequisites
- [ ] Linux system with ALSA support
- [ ] GCC compiler installed
- [ ] Python 3.7+ installed
- [ ] Audio device accessible to your user account

### ✅ Installation Steps
1. **Clone and setup**:
   ```bash
   git clone <repository-url> SilentTrace
   cd SilentTrace
   ```

2. **Build C module**:
   ```bash
   cd core_c
   make install-deps
   make
   ```

3. **Install Python dependencies**:
   ```bash
   cd ../analysis_python
   pip3 install -r requirements.txt
   ```

4. **Test audio access**:
   ```bash
   arecord -D default -f S16_LE -r 44100 -c 1 -d 1 test.wav
   ```

## Running SilentTrace

### Basic Operation
```bash
# Terminal 1: Audio capture
cd core_c && ./audio_capture

# Terminal 2: Analysis
cd analysis_python && python3 analyze.py
```

### With Web Dashboard
```bash
# Terminal 1: Audio capture
cd core_c && ./audio_capture

# Terminal 2: Analysis + Dashboard
cd analysis_python && python3 analyze.py --with-dashboard
```

## Understanding Detection Levels

### 🟢 Normal Operation
```
✅ Listening... | 🔊 Normal ambient noise
```
- System is monitoring successfully
- No ultrasonic signals detected above threshold
- Background noise is within normal parameters

### 🟡 Warning Level
```
⚠️  Ultrasound spike at 19.6kHz detected!
```
- Single ultrasonic signal detected
- May be environmental noise or electronic interference
- Monitor for repetition to determine if it's a beacon

### 🔴 Alert Level
```
🚨 Repetitive ultrasonic pulses detected (possible beacon signal)
```
- Multiple detections in short time window
- High probability of tracking beacon activity
- Immediate investigation recommended

## Configuration Tuning

### Sensitivity Adjustment
```yaml
# silenttrace_config.yaml
detection:
  threshold_db: -40.0    # Default: -40dB
  # -50dB = More sensitive (more false positives)
  # -30dB = Less sensitive (may miss weak signals)
```

### Beacon Detection Parameters
```yaml
detection:
  repetition_threshold: 3      # Detections needed for beacon alert
  repetition_window_sec: 10    # Time window to count repetitions
```

### Frequency Range Customization
```yaml
audio:
  ultrasonic_min_freq: 18000   # Lower bound (Hz)
  ultrasonic_max_freq: 22000   # Upper bound (Hz)
```

## Web Dashboard Features

### Real-time Spectrum View
- **Blue line**: Current ultrasonic spectrum
- **Red dashed line**: Detection threshold
- **Red triangles**: Detected peaks

### Detection History
- **Green bars**: Normal operation periods
- **Orange bars**: Warning level detections
- **Red bars**: Alert level detections

### System Statistics
- **Runtime**: How long system has been running
- **Processed Chunks**: Number of audio segments analyzed
- **Total Detections**: Cumulative detection count

## Common Use Cases

### 1. Privacy Audit of Smart Devices
```bash
# Place near smart speakers, TVs, or IoT devices
./audio_capture & python3 analyze.py --with-dashboard
```

### 2. Retail Environment Monitoring
```bash
# Check for retail analytics beacons
SILENTTRACE_THRESHOLD_DB=-45 python3 analyze.py
```

### 3. Office/Public Space Scanning
```bash
# Monitor for corporate tracking systems
python3 analyze.py --with-dashboard
```

## Troubleshooting Common Issues

### Audio Device Problems

**Error**: `Cannot open audio device`
```bash
# Solution: Check audio permissions
sudo usermod -a -G audio $USER
# Log out and back in
```

**Error**: `Device or resource busy`
```bash
# Solution: Close other audio applications
sudo fuser -k /dev/snd/*
```

### Connection Issues

**Error**: `Failed to connect to audio source`
```bash
# Solution: Ensure audio_capture is running first
cd core_c && ./audio_capture &
cd ../analysis_python && python3 analyze.py
```

**Error**: `Socket connection refused`
```bash
# Solution: Remove stale socket file
rm -f /tmp/silenttrace.sock
```

### Performance Issues

**High CPU Usage**:
```bash
# Solution: Reduce FFT window size
# Edit config.py: fft_window_size: 2048  # (was 4096)
```

**Memory Leaks**:
```bash
# Solution: Restart long-running sessions periodically
# Or reduce max_history_points in dashboard config
```

## Advanced Configuration

### Environment Variables
```bash
# Detection sensitivity
export SILENTTRACE_THRESHOLD_DB=-35

# Dashboard port
export SILENTTRACE_DASHBOARD_PORT=8080

# Debug mode
export SILENTTRACE_DEBUG=true
```

### Custom Frequency Ranges
For specialized tracking systems that might use different frequencies:

```yaml
# Modify silenttrace_config.yaml
audio:
  ultrasonic_min_freq: 17000   # Extended lower range
  ultrasonic_max_freq: 24000   # Extended upper range
```

### Alert Customization
```yaml
alerts:
  enable_cli_alerts: true      # Terminal notifications
  enable_audio_alerts: false   # System beep (future feature)
  enable_file_logging: true    # Save to log file
  alert_cooldown_sec: 5        # Prevent spam
```

## Log File Analysis

Detection logs are saved to `silenttrace_detections.log`:

```json
{
  "timestamp": "2025-01-XX...",
  "type": "repetitive_ultrasonic_beacon",
  "frequency": 19650.5,
  "magnitude": -32.1,
  "threat_level": "alert",
  "features": {
    "peak_magnitude": -30.2,
    "spectral_centroid": 19800.3,
    "spectral_flatness": 0.12
  }
}
```

## Performance Optimization

### For Continuous Monitoring
```bash
# Run as background service with lower priority
nice -n 10 ./audio_capture &
nice -n 10 python3 analyze.py &
```

### For Resource-Constrained Systems
```yaml
# Reduce processing load
audio:
  frames_per_buffer: 1024      # Smaller buffer
  fft_window_size: 2048        # Smaller FFT
dashboard:
  auto_refresh_ms: 2000        # Slower refresh
```

## Security Considerations

### Data Privacy
- Audio data is never written to disk
- Only detection metadata is logged
- All processing happens locally

### Network Security
- Dashboard only binds to localhost by default
- No external network connections made
- No telemetry or analytics sent

### Access Control
```bash
# Restrict log file access
chmod 600 silenttrace_detections.log

# Run with minimal privileges
# (avoid running as root)
```

## Integration Examples

### Custom Alert Scripts
```bash
# Monitor log file for new detections
tail -f silenttrace_detections.log | while read line; do
    echo "New detection: $line" | mail -s "SilentTrace Alert" admin@example.com
done
```

### Automated Reporting
```python
# daily_report.py
import json
from datetime import datetime, timedelta

# Parse logs and generate summary
# Send to monitoring system
```

## FAQ

**Q: Will this detect all ultrasonic tracking?**
A: SilentTrace detects signals in the 18-22kHz range, which covers most commercial ultrasonic beacons. Some systems may use different frequencies.

**Q: How much CPU does it use?**
A: Typically 5-15% CPU on modern systems. The C audio capture is very efficient, and Python analysis can be tuned for performance.

**Q: Can I run this on a Raspberry Pi?**
A: Yes, but you may need to reduce the FFT window size and refresh rate for optimal performance.

**Q: Will this interfere with my other audio applications?**
A: No, SilentTrace only listens to audio input and doesn't affect audio output or other recording applications.