#!/usr/bin/env python3
"""
SilentTrace Main Analysis Module
Real-time ultrasonic signal detection and analysis system
"""

import sys
import time
import socket
import struct
import numpy as np
import threading
from typing import Dict, Any, List
from collections import deque

from config import config
from utils import SignalProcessor, DetectionLogger, CLIDisplay, DataBuffer

class UltrasonicDetector:
    """Main ultrasonic signal detector class"""
    
    def __init__(self):
        self.config = config
        self.processor = SignalProcessor(
            sample_rate=self.config.audio.sample_rate,
            window_size=self.config.audio.fft_window_size
        )
        self.logger = DetectionLogger(self.config.alerts.log_file_path)
        self.display = CLIDisplay()
        self.data_buffer = DataBuffer(self.config.dashboard.max_history_points)
        
        # Detection state
        self.detection_history = deque(maxlen=50)
        self.last_alert_time = 0
        self.running = False
        self.stats = {
            'start_time': time.time(),
            'chunks_processed': 0,
            'total_detections': 0,
            'false_positives': 0
        }
        
        # Socket connection
        self.socket = None
        self.connect_attempts = 0
        
    def connect_to_audio_source(self) -> bool:
        """Connect to the C audio capture module via Unix socket"""
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(self.config.system.socket_path)
            self.logger.log_info("Connected to audio capture module")
            return True
        except Exception as e:
            self.logger.log_error(f"Failed to connect to audio source: {e}")
            return False
    
    def receive_audio_data(self) -> Dict[str, Any]:
        """Receive audio data from C module"""
        try:
            # Receive header (timestamp, sample_rate, buffer_length, channels)
            header_data = self.socket.recv(16)  # 8+4+4 bytes
            if len(header_data) != 16:
                raise ConnectionError("Incomplete header received")
            
            timestamp, sample_rate, buffer_length, channels = struct.unpack('QII', header_data)
            
            # Receive audio data
            data_size = buffer_length * channels * 2  # 2 bytes per sample (int16)
            audio_data_bytes = b''
            
            while len(audio_data_bytes) < data_size:
                chunk = self.socket.recv(data_size - len(audio_data_bytes))
                if not chunk:
                    raise ConnectionError("Connection closed by audio source")
                audio_data_bytes += chunk
            
            # Convert to numpy array
            audio_data = np.frombuffer(audio_data_bytes, dtype=np.int16)
            
            # Normalize to [-1, 1] range
            audio_data = audio_data.astype(np.float32) / 32768.0
            
            return {
                'timestamp': timestamp,
                'sample_rate': sample_rate,
                'audio_data': audio_data,
                'channels': channels
            }
            
        except Exception as e:
            self.logger.log_error(f"Error receiving audio data: {e}")
            return None
    
    def analyze_audio_chunk(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Analyze audio chunk for ultrasonic signals"""
        # Compute FFT
        frequencies, magnitudes = self.processor.compute_fft(audio_data)
        
        # Extract ultrasonic band
        us_freq, us_mag = self.processor.extract_ultrasonic_band(
            frequencies, magnitudes,
            self.config.audio.ultrasonic_min_freq,
            self.config.audio.ultrasonic_max_freq
        )
        
        # Detect peaks
        peaks = self.processor.detect_peaks(
            us_mag,
            self.config.detection.threshold_db,
            self.config.detection.min_peak_height,
            self.config.detection.min_peak_distance
        )
        
        # Calculate spectral features
        features = self.processor.calculate_spectral_features(us_mag)
        
        # Determine if detection is significant
        detections = []
        if len(peaks) > 0:
            for peak_idx in peaks:
                detection = {
                    'frequency': us_freq[peak_idx],
                    'magnitude': us_mag[peak_idx],
                    'peak_index': peak_idx,
                    'timestamp': time.time(),
                    'features': features
                }
                detections.append(detection)
        
        return {
            'frequencies': frequencies,
            'magnitudes': magnitudes,
            'ultrasonic_frequencies': us_freq,
            'ultrasonic_magnitudes': us_mag,
            'peaks': peaks,
            'detections': detections,
            'features': features
        }
    
    def evaluate_detection_pattern(self, detections: List[Dict[str, Any]]) -> str:
        """Evaluate detection pattern to determine threat level"""
        if not detections:
            return "normal"
        
        current_time = time.time()
        
        # Add detections to history
        for detection in detections:
            self.detection_history.append(detection)
        
        # Count recent detections
        recent_detections = [
            d for d in self.detection_history
            if current_time - d['timestamp'] <= self.config.detection.repetition_window_sec
        ]
        
        # Check for repetitive pattern
        if len(recent_detections) >= self.config.detection.repetition_threshold:
            # Check if frequencies are similar (potential beacon)
            frequencies = [d['frequency'] for d in recent_detections]
            freq_std = np.std(frequencies)
            
            if freq_std < 100:  # Frequencies within 100Hz - likely same source
                return "alert"
            else:
                return "warning"
        elif len(detections) > 0:
            return "warning"
        else:
            return "normal"
    
    def handle_detections(self, analysis: Dict[str, Any]):
        """Handle detection events with appropriate alerts and logging"""
        detections = analysis['detections']
        threat_level = self.evaluate_detection_pattern(detections)
        
        current_time = time.time()
        
        # Update statistics
        self.stats['total_detections'] += len(detections)
        
        # Display status
        if threat_level == "normal":
            self.display.show_status("Listening... | 🔊 Normal ambient noise", "normal")
        elif threat_level == "warning" and detections:
            freq = detections[0]['frequency']
            mag = detections[0]['magnitude']
            self.display.show_status(f"Ultrasound spike at {freq:.1f}Hz detected!", "warning")
            
            # Detailed detection display
            if current_time - self.last_alert_time > self.config.alerts.alert_cooldown_sec:
                self.display.show_detection(freq, mag, detections[0]['features'])
                self.last_alert_time = current_time
        elif threat_level == "alert":
            self.display.show_status("Repetitive ultrasonic pulses detected (possible beacon signal)", "alert")
            
            # Log critical detection
            if self.config.alerts.enable_file_logging:
                for detection in detections:
                    self.logger.log_detection({
                        'type': 'repetitive_ultrasonic_beacon',
                        'frequency': detection['frequency'],
                        'magnitude': detection['magnitude'],
                        'threat_level': threat_level,
                        'features': detection['features']
                    })
        
        # Store data for dashboard
        self.data_buffer.add({
            'analysis': analysis,
            'threat_level': threat_level,
            'detections': detections
        })
    
    def run_analysis_loop(self):
        """Main analysis loop"""
        self.display.show_banner()
        self.logger.log_info("SilentTrace analysis started")
        
        self.running = True
        
        while self.running:
            try:
                # Receive audio data
                audio_packet = self.receive_audio_data()
                if audio_packet is None:
                    break
                
                # Analyze audio
                analysis = self.analyze_audio_chunk(audio_packet['audio_data'])
                
                # Handle detections
                self.handle_detections(analysis)
                
                # Update statistics
                self.stats['chunks_processed'] += 1
                
                # Display periodic statistics
                if self.stats['chunks_processed'] % 10 == 0:
                    runtime = time.time() - self.stats['start_time']
                    stats_display = {
                        'runtime': f"{runtime:.0f}",
                        'chunks_processed': self.stats['chunks_processed']
                    }
                    self.display.show_statistics(stats_display)
                
            except KeyboardInterrupt:
                self.logger.log_info("Analysis interrupted by user")
                break
            except Exception as e:
                self.logger.log_error(f"Analysis error: {e}")
                if self.config.system.enable_debug_logging:
                    import traceback
                    traceback.print_exc()
                break
        
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.socket:
            self.socket.close()
        self.logger.log_info("SilentTrace analysis stopped")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for web dashboard"""
        recent_data, timestamps = self.data_buffer.get_recent(60.0)  # Last minute
        
        dashboard_data = {
            'status': 'running' if self.running else 'stopped',
            'stats': self.stats.copy(),
            'recent_detections': recent_data[-10:] if recent_data else [],
            'config': {
                'ultrasonic_range': self.config.get_frequency_range(),
                'threshold_db': self.config.detection.threshold_db,
            }
        }
        
        dashboard_data['stats']['runtime'] = time.time() - self.stats['start_time']
        
        return dashboard_data

class DashboardDataProvider:
    """Thread-safe data provider for the web dashboard"""
    
    def __init__(self, detector: UltrasonicDetector):
        self.detector = detector
        self._lock = threading.Lock()
    
    def get_data(self) -> Dict[str, Any]:
        """Thread-safe data access for dashboard"""
        with self._lock:
            return self.detector.get_dashboard_data()

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--dashboard-only':
        # Start dashboard in standalone mode for testing
        from dashboard import create_dashboard_app
        app = create_dashboard_app(None)
        app.run(host=config.dashboard.host, port=config.dashboard.port, debug=config.dashboard.debug)
        return
    
    # Create detector instance
    detector = UltrasonicDetector()
    
    # Connect to audio source
    print("Connecting to audio capture module...")
    max_attempts = config.system.max_reconnect_attempts
    
    for attempt in range(max_attempts):
        if detector.connect_to_audio_source():
            break
        
        print(f"Connection attempt {attempt + 1}/{max_attempts} failed. Retrying in {config.system.reconnect_delay_sec}s...")
        time.sleep(config.system.reconnect_delay_sec)
    else:
        print("Failed to connect to audio capture module. Make sure it's running.")
        print("Start with: cd core_c && make && ./audio_capture")
        sys.exit(1)
    
    # Start dashboard in background thread if requested
    if '--with-dashboard' in sys.argv:
        from dashboard import create_dashboard_app
        dashboard_provider = DashboardDataProvider(detector)
        app = create_dashboard_app(dashboard_provider)
        
        dashboard_thread = threading.Thread(
            target=lambda: app.run(
                host=config.dashboard.host,
                port=config.dashboard.port,
                debug=False,  # Don't use debug mode in thread
                use_reloader=False
            )
        )
        dashboard_thread.daemon = True
        dashboard_thread.start()
        
        print(f"Web dashboard available at http://{config.dashboard.host}:{config.dashboard.port}")
    
    # Start main analysis
    try:
        detector.run_analysis_loop()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        detector.cleanup()

if __name__ == "__main__":
    main()