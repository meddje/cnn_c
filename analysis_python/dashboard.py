#!/usr/bin/env python3
"""
SilentTrace Web Dashboard
Real-time visualization of ultrasonic signal detection data
"""

import json
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import plotly
import plotly.graph_objs as go
import plotly.express as px
import numpy as np

from config import config

def create_dashboard_app(data_provider=None):
    """Create and configure Flask dashboard application"""
    
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes
    
    # Mock data provider for testing when running standalone
    if data_provider is None:
        data_provider = MockDataProvider()
    
    @app.route('/')
    def dashboard():
        """Main dashboard page"""
        return render_template('dashboard.html', config=get_dashboard_config())
    
    @app.route('/api/data')
    def get_data():
        """API endpoint for real-time data"""
        try:
            data = data_provider.get_data()
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/spectrum')
    def get_spectrum():
        """API endpoint for frequency spectrum data"""
        try:
            data = data_provider.get_data()
            recent_detections = data.get('recent_detections', [])
            
            if not recent_detections:
                return jsonify({'frequencies': [], 'magnitudes': []})
            
            # Get the most recent analysis
            latest_analysis = recent_detections[-1].get('analysis', {})
            
            spectrum_data = {
                'frequencies': latest_analysis.get('ultrasonic_frequencies', []).tolist() if hasattr(latest_analysis.get('ultrasonic_frequencies', []), 'tolist') else [],
                'magnitudes': latest_analysis.get('ultrasonic_magnitudes', []).tolist() if hasattr(latest_analysis.get('ultrasonic_magnitudes', []), 'tolist') else [],
                'timestamp': time.time()
            }
            
            return jsonify(spectrum_data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/detections')
    def get_detections():
        """API endpoint for detection history"""
        try:
            data = data_provider.get_data()
            recent_detections = data.get('recent_detections', [])
            
            # Format detections for display
            formatted_detections = []
            for item in recent_detections:
                detections = item.get('detections', [])
                threat_level = item.get('threat_level', 'normal')
                
                for detection in detections:
                    formatted_detections.append({
                        'timestamp': datetime.fromtimestamp(detection['timestamp']).strftime('%H:%M:%S'),
                        'frequency': round(detection['frequency'], 1),
                        'magnitude': round(detection['magnitude'], 1),
                        'threat_level': threat_level,
                        'features': detection.get('features', {})
                    })
            
            # Sort by timestamp (most recent first)
            formatted_detections.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return jsonify(formatted_detections[:20])  # Return last 20 detections
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/plot/spectrum')
    def plot_spectrum():
        """Generate spectrum plot"""
        try:
            data = data_provider.get_data()
            recent_detections = data.get('recent_detections', [])
            
            if not recent_detections:
                # Empty plot
                fig = go.Figure()
                fig.update_layout(title="No Data Available", xaxis_title="Frequency (Hz)", yaxis_title="Magnitude (dB)")
                return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
            # Get the most recent analysis
            latest_analysis = recent_detections[-1].get('analysis', {})
            frequencies = latest_analysis.get('ultrasonic_frequencies', [])
            magnitudes = latest_analysis.get('ultrasonic_magnitudes', [])
            
            if len(frequencies) == 0 or len(magnitudes) == 0:
                fig = go.Figure()
                fig.update_layout(title="No Ultrasonic Data", xaxis_title="Frequency (Hz)", yaxis_title="Magnitude (dB)")
                return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
            # Create spectrum plot
            fig = go.Figure()
            
            # Add main spectrum line
            fig.add_trace(go.Scatter(
                x=frequencies,
                y=magnitudes,
                mode='lines',
                name='Ultrasonic Spectrum',
                line=dict(color='cyan', width=2)
            ))
            
            # Add detection threshold line
            threshold = config.detection.threshold_db
            fig.add_hline(y=threshold, line_dash="dash", line_color="red", 
                         annotation_text=f"Detection Threshold ({threshold}dB)")
            
            # Highlight detected peaks
            peaks = latest_analysis.get('peaks', [])
            if len(peaks) > 0:
                peak_frequencies = frequencies[peaks]
                peak_magnitudes = magnitudes[peaks]
                
                fig.add_trace(go.Scatter(
                    x=peak_frequencies,
                    y=peak_magnitudes,
                    mode='markers',
                    name='Detected Peaks',
                    marker=dict(color='red', size=8, symbol='triangle-up')
                ))
            
            # Update layout
            fig.update_layout(
                title='Real-time Ultrasonic Spectrum (18-22kHz)',
                xaxis_title='Frequency (Hz)',
                yaxis_title='Magnitude (dB)',
                template='plotly_dark',
                height=400,
                showlegend=True
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            # Error plot
            fig = go.Figure()
            fig.update_layout(title=f"Error: {str(e)}", xaxis_title="Frequency (Hz)", yaxis_title="Magnitude (dB)")
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    @app.route('/api/plot/history')
    def plot_detection_history():
        """Generate detection history plot"""
        try:
            data = data_provider.get_data()
            recent_detections = data.get('recent_detections', [])
            
            # Extract detection counts over time
            detection_times = []
            detection_counts = []
            current_time = time.time()
            
            # Create time bins (every 10 seconds for the last 5 minutes)
            time_bins = np.arange(current_time - 300, current_time, 10)
            counts = np.zeros(len(time_bins))
            
            for item in recent_detections:
                detections = item.get('detections', [])
                for detection in detections:
                    det_time = detection['timestamp']
                    # Find appropriate time bin
                    bin_idx = np.digitize(det_time, time_bins) - 1
                    if 0 <= bin_idx < len(counts):
                        counts[bin_idx] += 1
            
            # Convert to datetime for plotting
            time_labels = [datetime.fromtimestamp(t).strftime('%H:%M:%S') for t in time_bins]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=time_labels,
                y=counts,
                name='Detections',
                marker_color='orange'
            ))
            
            fig.update_layout(
                title='Detection History (Last 5 Minutes)',
                xaxis_title='Time',
                yaxis_title='Detection Count',
                template='plotly_dark',
                height=300
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            fig = go.Figure()
            fig.update_layout(title=f"Error: {str(e)}")
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    @app.route('/api/config', methods=['GET', 'POST'])
    def handle_config():
        """Handle configuration updates"""
        if request.method == 'GET':
            return jsonify(get_dashboard_config())
        elif request.method == 'POST':
            try:
                new_config = request.json
                # Update configuration (implement validation as needed)
                # Note: This is a simplified implementation
                return jsonify({'status': 'success', 'message': 'Configuration updated'})
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 400
    
    return app

def get_dashboard_config():
    """Get configuration data for dashboard"""
    return {
        'ultrasonic_range': config.get_frequency_range(),
        'threshold_db': config.detection.threshold_db,
        'sample_rate': config.audio.sample_rate,
        'refresh_rate': config.dashboard.auto_refresh_ms,
        'detection_settings': {
            'min_peak_height': config.detection.min_peak_height,
            'repetition_threshold': config.detection.repetition_threshold,
            'repetition_window_sec': config.detection.repetition_window_sec
        }
    }

class MockDataProvider:
    """Mock data provider for testing dashboard without live detector"""
    
    def __init__(self):
        self.start_time = time.time()
        self.detection_count = 0
    
    def get_data(self):
        """Generate mock data for testing"""
        current_time = time.time()
        runtime = current_time - self.start_time
        
        # Generate some fake ultrasonic data
        frequencies = np.linspace(18000, 22000, 100)
        magnitudes = -60 + 20 * np.random.random(100) + 10 * np.sin(frequencies / 1000)
        
        # Add some fake peaks occasionally
        fake_detections = []
        if np.random.random() < 0.1:  # 10% chance of detection
            self.detection_count += 1
            peak_freq = 19000 + np.random.random() * 2000
            peak_mag = -30 + np.random.random() * 20
            
            fake_detections.append({
                'frequency': peak_freq,
                'magnitude': peak_mag,
                'timestamp': current_time,
                'features': {
                    'peak_magnitude': peak_mag,
                    'spectral_centroid': 20000,
                    'spectral_flatness': 0.1
                }
            })
        
        return {
            'status': 'running',
            'stats': {
                'runtime': runtime,
                'chunks_processed': int(runtime * 10),
                'total_detections': self.detection_count
            },
            'recent_detections': [{
                'analysis': {
                    'ultrasonic_frequencies': frequencies,
                    'ultrasonic_magnitudes': magnitudes,
                    'peaks': np.array([20, 50]) if fake_detections else np.array([])
                },
                'detections': fake_detections,
                'threat_level': 'warning' if fake_detections else 'normal'
            }],
            'config': {
                'ultrasonic_range': (18000, 22000),
                'threshold_db': -40.0
            }
        }

# Create template directory and HTML template
import os
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
os.makedirs(template_dir, exist_ok=True)

dashboard_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SilentTrace Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #1a1a1a;
            color: #ffffff;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .status-card {
            background-color: #2d2d2d;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #00ff88;
        }
        .status-card.warning { border-left-color: #ff9500; }
        .status-card.alert { border-left-color: #ff3333; }
        .chart-container {
            background-color: #2d2d2d;
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 10px;
        }
        .detection-log {
            background-color: #2d2d2d;
            padding: 20px;
            border-radius: 10px;
            max-height: 400px;
            overflow-y: auto;
        }
        .detection-item {
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 5px;
            background-color: #3d3d3d;
        }
        .detection-item.warning { background-color: #4d3d00; }
        .detection-item.alert { background-color: #4d0000; }
        .refresh-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px;
            background-color: #00ff88;
            color: #000;
            border-radius: 5px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 SilentTrace Dashboard</h1>
        <p>Real-time Ultrasonic Signal Detection Monitor</p>
    </div>
    
    <div class="refresh-indicator" id="refreshIndicator" style="display: none;">
        Updating...
    </div>
    
    <div class="status-grid">
        <div class="status-card" id="statusCard">
            <h3>System Status</h3>
            <p id="systemStatus">Loading...</p>
            <p id="runtime">Runtime: --</p>
        </div>
        <div class="status-card">
            <h3>Detection Stats</h3>
            <p id="totalDetections">Total Detections: --</p>
            <p id="processedChunks">Processed Chunks: --</p>
        </div>
        <div class="status-card">
            <h3>Configuration</h3>
            <p id="frequencyRange">Range: -- Hz</p>
            <p id="threshold">Threshold: -- dB</p>
        </div>
    </div>
    
    <div class="chart-container">
        <div id="spectrumPlot"></div>
    </div>
    
    <div class="chart-container">
        <div id="historyPlot"></div>
    </div>
    
    <div class="detection-log">
        <h3>Recent Detections</h3>
        <div id="detectionList">Loading...</div>
    </div>
    
    <script>
        let refreshInterval;
        
        function updateDashboard() {
            const indicator = document.getElementById('refreshIndicator');
            indicator.style.display = 'block';
            
            // Fetch main data
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    updateStatusCards(data);
                    updatePlots();
                    updateDetectionLog();
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                })
                .finally(() => {
                    indicator.style.display = 'none';
                });
        }
        
        function updateStatusCards(data) {
            const statusCard = document.getElementById('statusCard');
            const status = data.status || 'unknown';
            const stats = data.stats || {};
            
            // Update status
            document.getElementById('systemStatus').textContent = 
                status === 'running' ? '✅ Active' : '❌ Stopped';
            
            // Update runtime
            const runtime = Math.floor(stats.runtime || 0);
            const hours = Math.floor(runtime / 3600);
            const minutes = Math.floor((runtime % 3600) / 60);
            const seconds = runtime % 60;
            document.getElementById('runtime').textContent = 
                `Runtime: ${hours}h ${minutes}m ${seconds}s`;
            
            // Update detection stats
            document.getElementById('totalDetections').textContent = 
                `Total Detections: ${stats.total_detections || 0}`;
            document.getElementById('processedChunks').textContent = 
                `Processed Chunks: ${stats.chunks_processed || 0}`;
            
            // Update configuration
            const config = data.config || {};
            const range = config.ultrasonic_range || [18000, 22000];
            document.getElementById('frequencyRange').textContent = 
                `Range: ${range[0]/1000}-${range[1]/1000}kHz`;
            document.getElementById('threshold').textContent = 
                `Threshold: ${config.threshold_db || -40}dB`;
        }
        
        function updatePlots() {
            // Update spectrum plot
            fetch('/api/plot/spectrum')
                .then(response => response.json())
                .then(plotData => {
                    Plotly.newPlot('spectrumPlot', plotData.data, plotData.layout, {responsive: true});
                });
                
            // Update history plot
            fetch('/api/plot/history')
                .then(response => response.json())
                .then(plotData => {
                    Plotly.newPlot('historyPlot', plotData.data, plotData.layout, {responsive: true});
                });
        }
        
        function updateDetectionLog() {
            fetch('/api/detections')
                .then(response => response.json())
                .then(detections => {
                    const logContainer = document.getElementById('detectionList');
                    
                    if (detections.length === 0) {
                        logContainer.innerHTML = '<p>No recent detections</p>';
                        return;
                    }
                    
                    const logHtml = detections.map(det => `
                        <div class="detection-item ${det.threat_level}">
                            <strong>${det.timestamp}</strong> - 
                            ${det.frequency}Hz at ${det.magnitude}dB
                            <span style="float: right; text-transform: uppercase;">${det.threat_level}</span>
                        </div>
                    `).join('');
                    
                    logContainer.innerHTML = logHtml;
                });
        }
        
        // Initialize dashboard
        updateDashboard();
        refreshInterval = setInterval(updateDashboard, {{ config.refresh_rate or 2000 }});
        
        // Handle page visibility for performance
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                clearInterval(refreshInterval);
            } else {
                updateDashboard();
                refreshInterval = setInterval(updateDashboard, {{ config.refresh_rate or 2000 }});
            }
        });
    </script>
</body>
</html>'''

with open(os.path.join(template_dir, 'dashboard.html'), 'w') as f:
    f.write(dashboard_html)

if __name__ == '__main__':
    # Run dashboard in standalone mode for testing
    app = create_dashboard_app()
    app.run(host=config.dashboard.host, port=config.dashboard.port, debug=config.dashboard.debug)