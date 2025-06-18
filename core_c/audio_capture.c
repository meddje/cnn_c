/*
 * SilentTrace - Ultrasonic Signal Detector
 * Audio Capture Layer (C)
 * 
 * This module captures real-time audio from the system microphone using ALSA
 * and streams the data to the Python analysis layer via UNIX socket.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <errno.h>
#include <signal.h>
#include <time.h>
#include <alsa/asoundlib.h>

// Audio configuration constants
#define SAMPLE_RATE 44100
#define CHANNELS 1
#define FRAMES_PER_BUFFER 2048
#define SOCKET_PATH "/tmp/silenttrace.sock"
#define BUFFER_DURATION_SEC 1

// Message header structure for C->Python communication
typedef struct {
    uint64_t timestamp;
    uint32_t sample_rate;
    uint32_t buffer_length;
    uint32_t channels;
} audio_header_t;

// Global variables for cleanup
static snd_pcm_t *capture_handle = NULL;
static int socket_fd = -1;
static int client_fd = -1;
static volatile int running = 1;

void cleanup_and_exit(int sig) {
    fprintf(stderr, "[INFO] Cleaning up resources...\n");
    running = 0;
    
    if (capture_handle) {
        snd_pcm_close(capture_handle);
        capture_handle = NULL;
    }
    
    if (client_fd >= 0) {
        close(client_fd);
        client_fd = -1;
    }
    
    if (socket_fd >= 0) {
        close(socket_fd);
        socket_fd = -1;
    }
    
    unlink(SOCKET_PATH);
    fprintf(stderr, "[INFO] Cleanup complete. Exiting.\n");
    exit(0);
}

int setup_audio_capture() {
    int err;
    snd_pcm_hw_params_t *hw_params;
    
    // Open PCM device for recording
    if ((err = snd_pcm_open(&capture_handle, "default", SND_PCM_STREAM_CAPTURE, 0)) < 0) {
        fprintf(stderr, "[ERROR] Cannot open audio device: %s\n", snd_strerror(err));
        return -1;
    }
    
    // Allocate hardware parameters object
    if ((err = snd_pcm_hw_params_malloc(&hw_params)) < 0) {
        fprintf(stderr, "[ERROR] Cannot allocate hardware parameter structure: %s\n", snd_strerror(err));
        return -1;
    }
    
    // Initialize hardware parameters
    if ((err = snd_pcm_hw_params_any(capture_handle, hw_params)) < 0) {
        fprintf(stderr, "[ERROR] Cannot initialize hardware parameter structure: %s\n", snd_strerror(err));
        return -1;
    }
    
    // Set access type
    if ((err = snd_pcm_hw_params_set_access(capture_handle, hw_params, SND_PCM_ACCESS_RW_INTERLEAVED)) < 0) {
        fprintf(stderr, "[ERROR] Cannot set access type: %s\n", snd_strerror(err));
        return -1;
    }
    
    // Set sample format
    if ((err = snd_pcm_hw_params_set_format(capture_handle, hw_params, SND_PCM_FORMAT_S16_LE)) < 0) {
        fprintf(stderr, "[ERROR] Cannot set sample format: %s\n", snd_strerror(err));
        return -1;
    }
    
    // Set sample rate
    unsigned int rate = SAMPLE_RATE;
    if ((err = snd_pcm_hw_params_set_rate_near(capture_handle, hw_params, &rate, 0)) < 0) {
        fprintf(stderr, "[ERROR] Cannot set sample rate: %s\n", snd_strerror(err));
        return -1;
    }
    
    if (rate != SAMPLE_RATE) {
        fprintf(stderr, "[WARNING] Sample rate set to %u instead of %d\n", rate, SAMPLE_RATE);
    }
    
    // Set number of channels
    if ((err = snd_pcm_hw_params_set_channels(capture_handle, hw_params, CHANNELS)) < 0) {
        fprintf(stderr, "[ERROR] Cannot set channel count: %s\n", snd_strerror(err));
        return -1;
    }
    
    // Set buffer size
    snd_pcm_uframes_t frames = FRAMES_PER_BUFFER;
    if ((err = snd_pcm_hw_params_set_period_size_near(capture_handle, hw_params, &frames, 0)) < 0) {
        fprintf(stderr, "[ERROR] Cannot set period size: %s\n", snd_strerror(err));
        return -1;
    }
    
    // Apply hardware parameters
    if ((err = snd_pcm_hw_params(capture_handle, hw_params)) < 0) {
        fprintf(stderr, "[ERROR] Cannot set parameters: %s\n", snd_strerror(err));
        return -1;
    }
    
    // Free hardware parameters
    snd_pcm_hw_params_free(hw_params);
    
    // Prepare audio interface for use
    if ((err = snd_pcm_prepare(capture_handle)) < 0) {
        fprintf(stderr, "[ERROR] Cannot prepare audio interface: %s\n", snd_strerror(err));
        return -1;
    }
    
    fprintf(stderr, "[INFO] Audio capture initialized: %dHz, %d channels, %d frames/buffer\n", 
            SAMPLE_RATE, CHANNELS, FRAMES_PER_BUFFER);
    
    return 0;
}

int setup_unix_socket() {
    struct sockaddr_un addr;
    
    // Create socket
    socket_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (socket_fd == -1) {
        fprintf(stderr, "[ERROR] Cannot create socket: %s\n", strerror(errno));
        return -1;
    }
    
    // Remove existing socket file
    unlink(SOCKET_PATH);
    
    // Setup address
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCKET_PATH, sizeof(addr.sun_path) - 1);
    
    // Bind socket
    if (bind(socket_fd, (struct sockaddr*)&addr, sizeof(addr)) == -1) {
        fprintf(stderr, "[ERROR] Cannot bind socket: %s\n", strerror(errno));
        return -1;
    }
    
    // Listen for connections
    if (listen(socket_fd, 1) == -1) {
        fprintf(stderr, "[ERROR] Cannot listen on socket: %s\n", strerror(errno));
        return -1;
    }
    
    fprintf(stderr, "[INFO] Unix socket created at %s\n", SOCKET_PATH);
    return 0;
}

int wait_for_client() {
    fprintf(stderr, "[INFO] Waiting for Python client connection...\n");
    
    client_fd = accept(socket_fd, NULL, NULL);
    if (client_fd == -1) {
        fprintf(stderr, "[ERROR] Cannot accept client connection: %s\n", strerror(errno));
        return -1;
    }
    
    fprintf(stderr, "[INFO] Python client connected successfully\n");
    return 0;
}

uint64_t get_timestamp_ms() {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (uint64_t)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}

int send_audio_data(int16_t *buffer, size_t frames) {
    audio_header_t header;
    size_t data_size = frames * sizeof(int16_t) * CHANNELS;
    
    // Prepare header
    header.timestamp = get_timestamp_ms();
    header.sample_rate = SAMPLE_RATE;
    header.buffer_length = frames;
    header.channels = CHANNELS;
    
    // Send header
    if (send(client_fd, &header, sizeof(header), 0) != sizeof(header)) {
        fprintf(stderr, "[ERROR] Failed to send header: %s\n", strerror(errno));
        return -1;
    }
    
    // Send audio data
    if (send(client_fd, buffer, data_size, 0) != data_size) {
        fprintf(stderr, "[ERROR] Failed to send audio data: %s\n", strerror(errno));
        return -1;
    }
    
    return 0;
}

void audio_capture_loop() {
    int16_t *buffer;
    int16_t *rolling_buffer;
    size_t rolling_buffer_size = SAMPLE_RATE * BUFFER_DURATION_SEC; // 1 second of audio
    size_t rolling_buffer_pos = 0;
    int frames_read;
    int chunks_processed = 0;
    
    // Allocate buffers
    buffer = malloc(FRAMES_PER_BUFFER * sizeof(int16_t) * CHANNELS);
    rolling_buffer = malloc(rolling_buffer_size * sizeof(int16_t) * CHANNELS);
    
    if (!buffer || !rolling_buffer) {
        fprintf(stderr, "[ERROR] Cannot allocate audio buffers\n");
        return;
    }
    
    memset(rolling_buffer, 0, rolling_buffer_size * sizeof(int16_t) * CHANNELS);
    
    fprintf(stderr, "[INFO] Starting audio capture loop...\n");
    
    while (running) {
        // Read audio frames
        frames_read = snd_pcm_readi(capture_handle, buffer, FRAMES_PER_BUFFER);
        
        if (frames_read == -EPIPE) {
            fprintf(stderr, "[WARNING] Buffer underrun occurred\n");
            snd_pcm_prepare(capture_handle);
            continue;
        } else if (frames_read < 0) {
            fprintf(stderr, "[ERROR] Error reading audio: %s\n", snd_strerror(frames_read));
            break;
        }
        
        // Copy to rolling buffer
        for (int i = 0; i < frames_read * CHANNELS; i++) {
            rolling_buffer[rolling_buffer_pos] = buffer[i];
            rolling_buffer_pos = (rolling_buffer_pos + 1) % rolling_buffer_size;
        }
        
        chunks_processed++;
        
        // Send data every ~1 second (approximate based on buffer size)
        if (chunks_processed >= (SAMPLE_RATE / FRAMES_PER_BUFFER)) {
            if (send_audio_data(rolling_buffer, rolling_buffer_size / CHANNELS) < 0) {
                fprintf(stderr, "[ERROR] Failed to send audio data to Python client\n");
                break;
            }
            
            chunks_processed = 0;
            fprintf(stderr, "[DEBUG] Sent 1-second audio chunk to Python\n");
        }
    }
    
    free(buffer);
    free(rolling_buffer);
}

int main() {
    // Setup signal handlers
    signal(SIGINT, cleanup_and_exit);
    signal(SIGTERM, cleanup_and_exit);
    
    fprintf(stderr, "[INFO] SilentTrace Audio Capture starting...\n");
    
    // Initialize ALSA
    if (setup_audio_capture() < 0) {
        fprintf(stderr, "[ERROR] Failed to setup audio capture\n");
        cleanup_and_exit(1);
    }
    
    // Setup Unix socket
    if (setup_unix_socket() < 0) {
        fprintf(stderr, "[ERROR] Failed to setup Unix socket\n");
        cleanup_and_exit(1);
    }
    
    // Wait for Python client
    if (wait_for_client() < 0) {
        fprintf(stderr, "[ERROR] Failed to connect to Python client\n");
        cleanup_and_exit(1);
    }
    
    // Start capturing audio
    audio_capture_loop();
    
    cleanup_and_exit(0);
    return 0;
}