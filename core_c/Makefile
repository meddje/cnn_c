# SilentTrace Audio Capture Makefile
# Compiles the C audio capture module with ALSA support

CC = gcc
CFLAGS = -Wall -Wextra -O2 -std=c99
LIBS = -lasound -lm
TARGET = audio_capture
SOURCE = audio_capture.c

# Default target
all: $(TARGET)

# Build the audio capture executable
$(TARGET): $(SOURCE)
	@echo "Compiling SilentTrace audio capture module..."
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCE) $(LIBS)
	@echo "Build complete: $(TARGET)"

# Install ALSA development libraries (Ubuntu/Debian)
install-deps:
	@echo "Installing ALSA development libraries..."
	sudo apt-get update
	sudo apt-get install -y libasound2-dev build-essential

# Clean build artifacts
clean:
	rm -f $(TARGET)
	rm -f /tmp/silenttrace.sock
	@echo "Cleaned build artifacts"

# Test compilation without running
test-compile: $(TARGET)
	@echo "Test compilation successful"

# Debug build with additional debugging symbols
debug: CFLAGS += -g -DDEBUG
debug: $(TARGET)
	@echo "Debug build complete"

# Help target
help:
	@echo "SilentTrace Audio Capture Build System"
	@echo ""
	@echo "Available targets:"
	@echo "  all          - Build the audio capture module (default)"
	@echo "  install-deps - Install required ALSA development libraries"
	@echo "  clean        - Remove build artifacts and socket files"
	@echo "  debug        - Build with debugging symbols"
	@echo "  test-compile - Test compilation without running"
	@echo "  help         - Show this help message"
	@echo ""
	@echo "Usage: make [target]"

.PHONY: all clean install-deps debug test-compile help