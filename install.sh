#!/bin/bash
set -e

# Claude Code Proxy Installation Script
# This script sets up the Claude Code Multi-Provider Proxy with all dependencies

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/claude-proxy}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
SERVICE_NAME="claude-proxy"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check Python
    if ! command_exists python3; then
        log_error "Python 3 is required but not installed."
        log_info "Please install Python 3.8+ and try again."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 8 ]]; then
        log_error "Python 3.8+ is required. Found: $PYTHON_VERSION"
        exit 1
    fi
    
    log_success "Python $PYTHON_VERSION found"
    
    # Check pip
    if ! command_exists pip3; then
        log_error "pip3 is required but not installed."
        exit 1
    fi
    
    # Check curl (for health checks)
    if ! command_exists curl; then
        log_warning "curl not found. Some features may not work properly."
    fi
    
    # Check git (optional)
    if ! command_exists git; then
        log_warning "git not found. Auto-updates will not be available."
    fi
}

# Create virtual environment
create_venv() {
    log_info "Creating Python virtual environment..."
    
    if [[ -d "$INSTALL_DIR/venv" ]]; then
        log_info "Virtual environment already exists. Removing old one..."
        rm -rf "$INSTALL_DIR/venv"
    fi
    
    mkdir -p "$INSTALL_DIR"
    python3 -m venv "$INSTALL_DIR/venv"
    
    # Activate virtual environment
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    log_success "Virtual environment created"
}

# Install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    source "$INSTALL_DIR/venv/bin/activate"
    
    if [[ -f "$SCRIPT_DIR/requirements.txt" ]]; then
        pip install -r "$SCRIPT_DIR/requirements.txt"
    else
        # Fallback to hardcoded requirements
        pip install \
            "fastapi[standard]>=0.115.11" \
            "uvicorn>=0.34.0" \
            "httpx>=0.25.0" \
            "pydantic>=2.0.0" \
            "litellm>=1.40.14" \
            "python-dotenv>=1.0.0" \
            "pyyaml>=6.0" \
            "requests>=2.31.0"
    fi
    
    log_success "Dependencies installed"
}

# Copy application files
copy_files() {
    log_info "Copying application files..."
    
    # Copy main files
    cp "$SCRIPT_DIR/server.py" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/config_manager.py" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/CLAUDE.md" "$INSTALL_DIR/"
    
    # Copy CLI script
    cp "$SCRIPT_DIR/claude-proxy" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/claude-proxy"
    
    # Copy configuration files
    if [[ -f "$SCRIPT_DIR/.env.example" ]]; then
        cp "$SCRIPT_DIR/.env.example" "$INSTALL_DIR/"
    fi
    
    log_success "Files copied to $INSTALL_DIR"
}

# Create wrapper script
create_wrapper() {
    log_info "Creating wrapper script..."
    
    mkdir -p "$BIN_DIR"
    
    cat > "$BIN_DIR/claude-proxy" << EOF
#!/bin/bash
# Claude Code Proxy Wrapper Script

# Activate virtual environment and run CLI
source "$INSTALL_DIR/venv/bin/activate"
cd "$INSTALL_DIR"
python "$INSTALL_DIR/claude-proxy" "\$@"
EOF
    
    chmod +x "$BIN_DIR/claude-proxy"
    
    log_success "Wrapper script created at $BIN_DIR/claude-proxy"
}

# Setup systemd service (Linux only)
setup_systemd_service() {
    if [[ "$(detect_os)" != "linux" ]]; then
        return
    fi
    
    log_info "Setting up systemd service..."
    
    SERVICE_FILE="$HOME/.config/systemd/user/$SERVICE_NAME.service"
    mkdir -p "$(dirname "$SERVICE_FILE")"
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Claude Code Multi-Provider Proxy Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin:\$PATH
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/server.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF
    
    # Reload systemd and enable service
    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE_NAME"
    
    log_success "Systemd service created and enabled"
    log_info "Use 'systemctl --user start $SERVICE_NAME' to start the service"
}

# Setup launchd service (macOS only)
setup_launchd_service() {
    if [[ "$(detect_os)" != "macos" ]]; then
        return
    fi
    
    log_info "Setting up launchd service..."
    
    PLIST_FILE="$HOME/Library/LaunchAgents/com.claude-proxy.plist"
    
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude-proxy</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/venv/bin/python</string>
        <string>$INSTALL_DIR/server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/logs/stderr.log</string>
</dict>
</plist>
EOF
    
    # Create logs directory
    mkdir -p "$INSTALL_DIR/logs"
    
    log_success "Launchd service created"
    log_info "Use 'launchctl load $PLIST_FILE' to start the service"
}

# Configure initial setup
configure_setup() {
    log_info "Running initial configuration..."
    
    # Note: Config is now stored in user config directory, not in install dir
    log_info "Configuration will be stored in user config directory (~/.config/gemini-code)"
    log_info "This keeps your API keys secure and separate from the installation."
    
    # Create logs directory
    mkdir -p "$INSTALL_DIR/logs"
    
    log_success "Initial configuration complete"
}

# Add to PATH
update_path() {
    log_info "Updating PATH..."
    
    # Detect shell
    SHELL_RC=""
    if [[ -n "$ZSH_VERSION" ]]; then
        SHELL_RC="$HOME/.zshrc"
    elif [[ -n "$BASH_VERSION" ]]; then
        SHELL_RC="$HOME/.bashrc"
    fi
    
    if [[ -n "$SHELL_RC" && -f "$SHELL_RC" ]]; then
        if ! grep -q "$BIN_DIR" "$SHELL_RC"; then
            echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$SHELL_RC"
            log_success "Added $BIN_DIR to PATH in $SHELL_RC"
            log_info "Please restart your shell or run: source $SHELL_RC"
        else
            log_info "$BIN_DIR already in PATH"
        fi
    else
        log_warning "Could not automatically update PATH. Please add $BIN_DIR to your PATH manually."
    fi
}

# Test installation
test_installation() {
    log_info "Testing installation..."
    
    # Test CLI
    if "$BIN_DIR/claude-proxy" --help >/dev/null 2>&1; then
        log_success "CLI tool is working"
    else
        log_error "CLI tool test failed"
        return 1
    fi
    
    # Test Python imports
    source "$INSTALL_DIR/venv/bin/activate"
    if python -c "import fastapi, uvicorn, litellm" >/dev/null 2>&1; then
        log_success "Python dependencies are working"
    else
        log_error "Python dependencies test failed"
        return 1
    fi
    
    log_success "Installation test passed"
}

# Print usage instructions
print_usage() {
    echo
    log_success "Installation completed successfully!"
    echo
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Configure your API key:"
    echo "   claude-proxy config"
    echo
    echo "2. Start the proxy server:"
    echo "   claude-proxy start"
    echo
    echo "3. Check server status:"
    echo "   claude-proxy status"
    echo
    echo "4. Use with Claude Code:"
    echo "   export ANTHROPIC_BASE_URL=http://localhost:8082"
    echo "   claude"
    echo
    echo -e "${BLUE}Service management:${NC}"
    if [[ "$(detect_os)" == "linux" ]]; then
        echo "   systemctl --user start $SERVICE_NAME"
        echo "   systemctl --user stop $SERVICE_NAME"
        echo "   systemctl --user status $SERVICE_NAME"
    elif [[ "$(detect_os)" == "macos" ]]; then
        echo "   launchctl load ~/Library/LaunchAgents/com.claude-proxy.plist"
        echo "   launchctl unload ~/Library/LaunchAgents/com.claude-proxy.plist"
    fi
    echo
    echo -e "${BLUE}Files installed to:${NC} $INSTALL_DIR"
    echo -e "${BLUE}CLI available at:${NC} $BIN_DIR/claude-proxy"
}

# Main installation function
main() {
    echo -e "${BLUE}Claude Code Multi-Provider Proxy Installer${NC}"
    echo "================================================"
    echo
    
    check_requirements
    create_venv
    install_dependencies
    copy_files
    create_wrapper
    configure_setup
    
    # Setup services based on OS
    setup_systemd_service
    setup_launchd_service
    
    update_path
    test_installation
    
    print_usage
}

# Handle command line arguments
case "${1:-}" in
    --uninstall)
        log_info "Uninstalling Claude Code Multi-Provider Proxy..."
        rm -rf "$INSTALL_DIR"
        rm -f "$BIN_DIR/claude-proxy"
        if [[ "$(detect_os)" == "linux" ]]; then
            systemctl --user disable --now "$SERVICE_NAME" 2>/dev/null || true
            rm -f "$HOME/.config/systemd/user/$SERVICE_NAME.service"
        elif [[ "$(detect_os)" == "macos" ]]; then
            launchctl unload "$HOME/Library/LaunchAgents/com.claude-proxy.plist" 2>/dev/null || true
            rm -f "$HOME/Library/LaunchAgents/com.claude-proxy.plist"
        fi
        log_success "Uninstallation complete"
        ;;
    --help)
        echo "Claude Code Multi-Provider Proxy Installer"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help       Show this help message"
        echo "  --uninstall  Remove the installation"
        echo
        echo "Environment variables:"
        echo "  INSTALL_DIR  Installation directory (default: $INSTALL_DIR)"
        echo "  BIN_DIR      Binary directory (default: $BIN_DIR)"
        ;;
    *)
        main
        ;;
esac