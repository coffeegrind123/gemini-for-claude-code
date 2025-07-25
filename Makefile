# Claude Code Multi-Provider Proxy Makefile
# Provides convenient commands for development and deployment

.PHONY: help install uninstall dev test clean build lint format

# Default target
help:
	@echo "Claude Code Multi-Provider Proxy - Available Commands"
	@echo "===================================================="
	@echo ""
	@echo "Installation:"
	@echo "  install     - Install the proxy system-wide"
	@echo "  uninstall   - Remove the installation"
	@echo ""
	@echo "Development:"
	@echo "  dev         - Start development server with auto-reload"
	@echo "  test        - Run full proxy test suite"
	@echo "  test-quick  - Run quick tests (no API calls)"
	@echo "  test-minimal- Run minimal API tests (avoid rate limits)"
	@echo "  lint        - Run code linting"
	@echo "  format      - Format code"
	@echo ""
	@echo "Utilities:"
	@echo "  clean       - Clean temporary files"
	@echo "  build       - Build distribution packages"

# Installation commands
install:
	@echo "Installing Claude Code Multi-Provider Proxy..."
	./install.sh

uninstall:
	@echo "Uninstalling Claude Code Multi-Provider Proxy..."
	./install.sh --uninstall

# Development commands
dev:
	@echo "Starting development server..."
	@echo "Note: Configuration is now managed via 'claude-proxy config'"
	@echo "If you need to configure, run: claude-proxy config"
	uvicorn server:app --host 0.0.0.0 --port 8082 --reload

test:
	@echo "Running proxy tests..."
	@if [ ! -f test_proxy.py ]; then \
		echo "Error: test_proxy.py not found"; \
		exit 1; \
	fi
	python3 test_proxy.py

test-quick:
	@echo "Running quick proxy tests..."
	python3 test_proxy.py --quick

test-minimal:
	@echo "Running minimal API tests..."
	python3 test_proxy.py --minimal-api

lint:
	@echo "Running linting..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 server.py config_manager.py claude-proxy; \
	else \
		echo "flake8 not installed. Install with: pip install flake8"; \
	fi

format:
	@echo "Formatting code..."
	@if command -v black >/dev/null 2>&1; then \
		black server.py config_manager.py; \
	else \
		echo "black not installed. Install with: pip install black"; \
	fi

# Utility commands
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	rm -f .claude-proxy.pid
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

build:
	@echo "Building distribution packages..."
	@if command -v setuptools >/dev/null 2>&1; then \
		python setup.py sdist bdist_wheel; \
	else \
		echo "setuptools not installed. Install with: pip install setuptools wheel"; \
	fi

# Configuration commands
config:
	@echo "Running configuration wizard..."
	./claude-proxy config

# Service management (Linux/macOS)
start-service:
	@if [ "$(shell uname)" = "Linux" ]; then \
		systemctl --user start claude-proxy; \
	elif [ "$(shell uname)" = "Darwin" ]; then \
		launchctl load ~/Library/LaunchAgents/com.claude-proxy.plist; \
	else \
		echo "Service management not supported on this platform"; \
	fi

stop-service:
	@if [ "$(shell uname)" = "Linux" ]; then \
		systemctl --user stop claude-proxy; \
	elif [ "$(shell uname)" = "Darwin" ]; then \
		launchctl unload ~/Library/LaunchAgents/com.claude-proxy.plist; \
	else \
		echo "Service management not supported on this platform"; \
	fi

status-service:
	@if [ "$(shell uname)" = "Linux" ]; then \
		systemctl --user status claude-proxy; \
	elif [ "$(shell uname)" = "Darwin" ]; then \
		launchctl list | grep com.claude-proxy; \
	else \
		echo "Service management not supported on this platform"; \
	fi

# Quick setup for new users
quick-setup: install config
	@echo ""
	@echo "Quick setup complete!"
	@echo "Run 'make dev' to start the development server"
	@echo "Or run 'claude-proxy start' to start the proxy"