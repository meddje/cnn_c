"""
SilentTrace Utility Functions
Common utilities for signal processing, logging, and data management
"""

import numpy as np
import time
import logging
import json
from datetime import datetime
from typing import List, Tuple, Dict, Any
from scipy import signal
from scipy.fft import fft, fftfreq
from colorama import init, Fore, Back, Style
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Rich console for enhanced CLI output
console = Console()

class SignalProcessor:
    """Advanced signal processing utilities for ultrasonic detection"""
    
    def __init__(self, sample_rate: int = 44100, window_size: int = 4096):
        self.sample_rate = sample_rate
        self.window_size = window_size
        self.window = signal.windows.hann(window_size)
        
    def compute_fft(self, audio_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute FFT with proper windowing and normalization
        Returns: (frequencies, magnitudes)
        """
        # Apply window function to reduce spectral leakage
        windowed_data = audio_data * self.window[:len(audio_data)]
        
        # Compute FFT
        fft_result = fft(windowed_data, n=self.window_size)
        frequencies = fftfreq(self.window_size, 1/self.sample_rate)
        
        # Take only positive frequencies and compute magnitude
        positive_freq_idx = frequencies >= 0
        frequencies = frequencies[positive_freq_idx]
        magnitudes = np.abs(fft_result[positive_freq_idx])
        
        # Convert to dB scale
        magnitudes_db = 20 * np.log10(magnitudes + 1e-10)  # Add small value to avoid log(0)
        
        return frequencies, magnitudes_db
    
    def extract_ultrasonic_band(self, frequencies: np.ndarray, magnitudes: np.ndarray, 
                               min_freq: int = 18000, max_freq: int = 22000) -> Tuple[np.ndarray, np.ndarray]:
        """Extract the ultrasonic frequency band"""
        mask = (frequencies >= min_freq) & (frequencies <= max_freq)
        return frequencies[mask], magnitudes[mask]
    
    def detect_peaks(self, magnitudes: np.ndarray, threshold_db: float = -40.0, 
                    min_height: float = 0.1, min_distance: int = 100) -> np.ndarray:
        """Detect significant peaks in the spectrum"""
        # Normalize magnitudes for peak detection
        normalized_mag = (magnitudes - np.min(magnitudes)) / (np.max(magnitudes) - np.min(magnitudes))
        
        # Find peaks above threshold
        peaks, properties = signal.find_peaks(
            normalized_mag,
            height=min_height,
            distance=min_distance
        )
        
        # Filter peaks by dB threshold
        valid_peaks = peaks[magnitudes[peaks] > threshold_db]
        
        return valid_peaks
    
    def calculate_spectral_features(self, magnitudes: np.ndarray) -> Dict[str, float]:
        """Calculate various spectral features for signal characterization"""
        return {
            'peak_magnitude': np.max(magnitudes),
            'mean_magnitude': np.mean(magnitudes),
            'std_magnitude': np.std(magnitudes),
            'spectral_centroid': np.sum(magnitudes * np.arange(len(magnitudes))) / np.sum(magnitudes),
            'spectral_rolloff': self._spectral_rolloff(magnitudes, 0.85),
            'spectral_flatness': self._spectral_flatness(magnitudes)
        }
    
    def _spectral_rolloff(self, magnitudes: np.ndarray, rolloff_percent: float = 0.85) -> float:
        """Calculate spectral rolloff frequency"""
        cumulative_sum = np.cumsum(magnitudes)
        rolloff_threshold = rolloff_percent * cumulative_sum[-1]
        rolloff_idx = np.where(cumulative_sum >= rolloff_threshold)[0]
        return rolloff_idx[0] if len(rolloff_idx) > 0 else len(magnitudes) - 1
    
    def _spectral_flatness(self, magnitudes: np.ndarray) -> float:
        """Calculate spectral flatness (Wiener entropy)"""
        # Convert back from dB to linear scale for calculation
        linear_mag = 10 ** (magnitudes / 20)
        geometric_mean = np.power(np.prod(linear_mag + 1e-10), 1.0 / len(linear_mag))
        arithmetic_mean = np.mean(linear_mag)
        return geometric_mean / (arithmetic_mean + 1e-10)

class DetectionLogger:
    """Handles logging of ultrasonic signal detections"""
    
    def __init__(self, log_file: str = "silenttrace_detections.log"):
        self.log_file = log_file
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('SilentTrace')
    
    def log_detection(self, detection_data: Dict[str, Any]):
        """Log a detection event"""
        timestamp = datetime.now().isoformat()
        detection_data['timestamp'] = timestamp
        
        log_message = f"ULTRASONIC DETECTION: {json.dumps(detection_data, indent=2)}"
        self.logger.warning(log_message)
    
    def log_info(self, message: str):
        """Log general information"""
        self.logger.info(message)
    
    def log_error(self, message: str):
        """Log error messages"""
        self.logger.error(message)

class CLIDisplay:
    """Enhanced CLI display with colors and formatting"""
    
    def __init__(self):
        self.detection_count = 0
        self.last_status_time = 0
        
    def show_banner(self):
        """Display the SilentTrace banner"""
        banner = Panel.fit(
            "[bold cyan]🔍 SilentTrace Ultrasonic Detector[/bold cyan]\n"
            "[dim]Monitoring frequencies 18kHz - 22kHz[/dim]",
            style="cyan"
        )
        console.print(banner)
    
    def show_status(self, status: str, detection_level: str = "normal"):
        """Display current status with appropriate coloring"""
        current_time = time.time()
        
        # Throttle status updates to avoid spam
        if current_time - self.last_status_time < 0.5:
            return
        
        self.last_status_time = current_time
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if detection_level == "normal":
            icon = "✅"
            color = "green"
        elif detection_level == "warning":
            icon = "⚠️ "
            color = "yellow"
        elif detection_level == "alert":
            icon = "🚨"
            color = "red"
        else:
            icon = "ℹ️ "
            color = "blue"
        
        status_text = Text(f"{timestamp} | {icon} {status}")
        status_text.stylize(f"bold {color}")
        console.print(status_text)
    
    def show_detection(self, frequency: float, magnitude: float, features: Dict[str, Any]):
        """Display detailed detection information"""
        self.detection_count += 1
        
        detection_panel = Panel(
            f"[bold red]🚨 ULTRASONIC SIGNAL DETECTED #{self.detection_count}[/bold red]\n\n"
            f"[yellow]Frequency:[/yellow] {frequency:.1f} Hz\n"
            f"[yellow]Magnitude:[/yellow] {magnitude:.1f} dB\n"
            f"[yellow]Peak Height:[/yellow] {features.get('peak_magnitude', 0):.2f}\n"
            f"[yellow]Spectral Centroid:[/yellow] {features.get('spectral_centroid', 0):.1f}\n"
            f"[yellow]Time:[/yellow] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            style="red",
            title="⚠️  DETECTION ALERT",
            title_align="center"
        )
        console.print(detection_panel)
    
    def show_statistics(self, stats: Dict[str, Any]):
        """Display running statistics"""
        stats_text = (
            f"[dim]Runtime: {stats.get('runtime', '0')}s | "
            f"Processed: {stats.get('chunks_processed', 0)} chunks | "
            f"Detections: {self.detection_count}[/dim]"
        )
        console.print(stats_text)

class DataBuffer:
    """Circular buffer for storing historical data"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.data = []
        self.timestamps = []
    
    def add(self, data: Any, timestamp: float = None):
        """Add data point to buffer"""
        if timestamp is None:
            timestamp = time.time()
        
        self.data.append(data)
        self.timestamps.append(timestamp)
        
        # Remove old data if buffer is full
        if len(self.data) > self.max_size:
            self.data.pop(0)
            self.timestamps.pop(0)
    
    def get_recent(self, seconds: float = 60.0) -> Tuple[List[Any], List[float]]:
        """Get data from the last N seconds"""
        current_time = time.time()
        cutoff_time = current_time - seconds
        
        recent_data = []
        recent_timestamps = []
        
        for i, timestamp in enumerate(self.timestamps):
            if timestamp >= cutoff_time:
                recent_data.append(self.data[i])
                recent_timestamps.append(timestamp)
        
        return recent_data, recent_timestamps
    
    def clear(self):
        """Clear all data from buffer"""
        self.data.clear()
        self.timestamps.clear()
    
    def size(self) -> int:
        """Get current buffer size"""
        return len(self.data)

def format_frequency(freq_hz: float) -> str:
    """Format frequency for display"""
    if freq_hz >= 1000:
        return f"{freq_hz/1000:.1f}kHz"
    else:
        return f"{freq_hz:.0f}Hz"

def format_magnitude(mag_db: float) -> str:
    """Format magnitude for display"""
    return f"{mag_db:.1f}dB"

def calculate_runtime(start_time: float) -> str:
    """Calculate and format runtime"""
    runtime_seconds = int(time.time() - start_time)
    hours = runtime_seconds // 3600
    minutes = (runtime_seconds % 3600) // 60
    seconds = runtime_seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"