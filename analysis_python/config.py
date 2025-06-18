"""
SilentTrace Configuration Module
Manages all configuration settings for the ultrasonic signal detector
"""

import os
import yaml
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class AudioConfig:
    """Audio processing configuration"""
    sample_rate: int = 44100
    channels: int = 1
    frames_per_buffer: int = 2048
    ultrasonic_min_freq: int = 18000  # 18kHz
    ultrasonic_max_freq: int = 22000  # 22kHz
    fft_window_size: int = 4096
    overlap_ratio: float = 0.5

@dataclass
class DetectionConfig:
    """Signal detection configuration"""
    threshold_db: float = -40.0  # dB threshold for detection
    min_peak_height: float = 0.1  # Normalized peak height
    min_peak_distance: int = 100  # FFT bins
    repetition_threshold: int = 3  # Number of detections to consider repetitive
    repetition_window_sec: int = 10  # Time window for repetition detection
    
@dataclass
class AlertConfig:
    """Alert and notification configuration"""
    enable_cli_alerts: bool = True
    enable_audio_alerts: bool = False
    enable_file_logging: bool = True
    log_file_path: str = "silenttrace_detections.log"
    alert_cooldown_sec: int = 5  # Minimum time between alerts

@dataclass
class DashboardConfig:
    """Web dashboard configuration"""
    host: str = "localhost"
    port: int = 5000
    debug: bool = False
    auto_refresh_ms: int = 1000  # Dashboard refresh rate
    max_history_points: int = 1000  # Maximum data points to keep

@dataclass
class SystemConfig:
    """System-level configuration"""
    socket_path: str = "/tmp/silenttrace.sock"
    max_reconnect_attempts: int = 5
    reconnect_delay_sec: int = 2
    enable_debug_logging: bool = False

class Config:
    """Main configuration manager"""
    
    def __init__(self, config_file: str = None):
        self.audio = AudioConfig()
        self.detection = DetectionConfig()
        self.alerts = AlertConfig()
        self.dashboard = DashboardConfig()
        self.system = SystemConfig()
        
        if config_file and os.path.exists(config_file):
            self.load_from_file(config_file)
        
        # Override with environment variables if present
        self._load_from_env()
    
    def load_from_file(self, config_file: str):
        """Load configuration from YAML file"""
        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if 'audio' in config_data:
                self._update_dataclass(self.audio, config_data['audio'])
            if 'detection' in config_data:
                self._update_dataclass(self.detection, config_data['detection'])
            if 'alerts' in config_data:
                self._update_dataclass(self.alerts, config_data['alerts'])
            if 'dashboard' in config_data:
                self._update_dataclass(self.dashboard, config_data['dashboard'])
            if 'system' in config_data:
                self._update_dataclass(self.system, config_data['system'])
                
        except Exception as e:
            print(f"Warning: Could not load config file {config_file}: {e}")
    
    def _update_dataclass(self, dataclass_obj, config_dict: Dict[str, Any]):
        """Update dataclass fields from dictionary"""
        for key, value in config_dict.items():
            if hasattr(dataclass_obj, key):
                setattr(dataclass_obj, key, value)
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Detection thresholds
        if 'SILENTTRACE_THRESHOLD_DB' in os.environ:
            self.detection.threshold_db = float(os.environ['SILENTTRACE_THRESHOLD_DB'])
        
        # Dashboard settings
        if 'SILENTTRACE_DASHBOARD_PORT' in os.environ:
            self.dashboard.port = int(os.environ['SILENTTRACE_DASHBOARD_PORT'])
        
        # Debug mode
        if 'SILENTTRACE_DEBUG' in os.environ:
            debug_enabled = os.environ['SILENTTRACE_DEBUG'].lower() in ('true', '1', 'yes')
            self.system.enable_debug_logging = debug_enabled
            self.dashboard.debug = debug_enabled
    
    def save_to_file(self, config_file: str):
        """Save current configuration to YAML file"""
        config_data = {
            'audio': self.audio.__dict__,
            'detection': self.detection.__dict__,
            'alerts': self.alerts.__dict__,
            'dashboard': self.dashboard.__dict__,
            'system': self.system.__dict__
        }
        
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            print(f"Configuration saved to {config_file}")
        except Exception as e:
            print(f"Error saving config file {config_file}: {e}")
    
    def get_frequency_range(self):
        """Get the ultrasonic frequency range as a tuple"""
        return (self.audio.ultrasonic_min_freq, self.audio.ultrasonic_max_freq)
    
    def is_ultrasonic_freq(self, frequency: float) -> bool:
        """Check if a frequency is in the ultrasonic range"""
        return self.audio.ultrasonic_min_freq <= frequency <= self.audio.ultrasonic_max_freq

# Global configuration instance
config = Config()

# Create default config file if it doesn't exist
DEFAULT_CONFIG_FILE = 'silenttrace_config.yaml'
if not os.path.exists(DEFAULT_CONFIG_FILE):
    config.save_to_file(DEFAULT_CONFIG_FILE)