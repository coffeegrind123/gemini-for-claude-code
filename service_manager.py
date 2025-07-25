#!/usr/bin/env python3
"""
Service management for Claude Code Multi-Provider Proxy
Handles systemd (Linux) and launchd (macOS) services
"""

import os
import platform
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import tempfile
import shutil


class ServiceManager:
    """Manages system services for Claude Code Multi-Provider Proxy"""
    
    def __init__(self, install_dir: Path, service_name: str = "claude-proxy"):
        self.install_dir = Path(install_dir)
        self.service_name = service_name
        self.system = platform.system().lower()
        
        # Service file paths
        if self.system == "linux":
            self.service_dir = Path.home() / ".config/systemd/user"
            self.service_file = self.service_dir / f"{service_name}.service"
        elif self.system == "darwin":
            self.service_dir = Path.home() / "Library/LaunchAgents"
            self.service_file = self.service_dir / f"com.{service_name}.proxy.plist"
        else:
            self.service_dir = None
            self.service_file = None

    def is_supported(self) -> bool:
        """Check if service management is supported on this platform"""
        return self.system in ["linux", "darwin"]

    def create_systemd_service(self, config: Dict[str, Any]) -> bool:
        """Create systemd service file (Linux)"""
        if self.system != "linux":
            return False
        
        self.service_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate environment variables from config
        env_vars = []
        if config.get('api', {}).get('gemini_api_key'):
            env_vars.append(f"Environment=GEMINI_API_KEY={config['api']['gemini_api_key']}")
        
        for section, values in config.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    env_key = f"{section.upper()}_{key.upper()}"
                    env_vars.append(f"Environment={env_key}={value}")
        
        service_content = f"""[Unit]
Description=Claude Code Multi-Provider Proxy Server
After=network.target
Wants=network.target

[Service]
Type=simple
User={os.environ.get('USER', 'nobody')}
Group={os.environ.get('USER', 'nobody')}
WorkingDirectory={self.install_dir}
ExecStart={self.install_dir}/venv/bin/python {self.install_dir}/server.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
TimeoutStartSec=30
TimeoutStopSec=30

# Environment variables
{chr(10).join(env_vars)}

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier={self.service_name}

[Install]
WantedBy=default.target
"""
        
        with open(self.service_file, 'w') as f:
            f.write(service_content)
        
        # Reload systemd
        try:
            subprocess.run(['systemctl', '--user', 'daemon-reload'], 
                         check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def create_launchd_service(self, config: Dict[str, Any]) -> bool:
        """Create launchd plist file (macOS)"""
        if self.system != "darwin":
            return False
        
        self.service_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logs directory
        logs_dir = self.install_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Generate environment variables
        env_dict = {}
        if config.get('api', {}).get('gemini_api_key'):
            env_dict['GEMINI_API_KEY'] = config['api']['gemini_api_key']
        
        # Flatten config to environment variables
        for section, values in config.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    env_key = f"{section.upper()}_{key.upper()}"
                    env_dict[env_key] = str(value)
        
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{self.service_name}.proxy</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>{self.install_dir}/venv/bin/python</string>
        <string>{self.install_dir}/server.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>{self.install_dir}</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        {self._dict_to_plist(env_dict)}
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>{logs_dir}/stdout.log</string>
    
    <key>StandardErrorPath</key>
    <string>{logs_dir}/stderr.log</string>
    
    <key>ThrottleInterval</key>
    <integer>5</integer>
    
</dict>
</plist>
"""
        
        with open(self.service_file, 'w') as f:
            f.write(plist_content)
        
        return True

    def _dict_to_plist(self, d: Dict[str, str]) -> str:
        """Convert dictionary to plist XML format"""
        items = []
        for key, value in d.items():
            items.append(f"        <key>{key}</key>")
            items.append(f"        <string>{value}</string>")
        return '\n'.join(items)

    def install_service(self, config: Dict[str, Any]) -> bool:
        """Install system service"""
        if not self.is_supported():
            return False
        
        if self.system == "linux":
            success = self.create_systemd_service(config)
            if success:
                try:
                    subprocess.run(['systemctl', '--user', 'enable', self.service_name],
                                 check=True, capture_output=True)
                    return True
                except subprocess.CalledProcessError:
                    return False
        elif self.system == "darwin":
            return self.create_launchd_service(config)
        
        return False

    def uninstall_service(self) -> bool:
        """Remove system service"""
        if not self.is_supported():
            return False
        
        # Stop service first
        self.stop_service()
        
        if self.system == "linux":
            try:
                subprocess.run(['systemctl', '--user', 'disable', self.service_name],
                             capture_output=True)
                if self.service_file.exists():
                    self.service_file.unlink()
                subprocess.run(['systemctl', '--user', 'daemon-reload'],
                             capture_output=True)
                return True
            except subprocess.CalledProcessError:
                return False
        elif self.system == "darwin":
            if self.service_file.exists():
                self.service_file.unlink()
                return True
        
        return False

    def start_service(self) -> bool:
        """Start the service"""
        if not self.is_supported():
            return False
        
        try:
            if self.system == "linux":
                subprocess.run(['systemctl', '--user', 'start', self.service_name],
                             check=True, capture_output=True)
            elif self.system == "darwin":
                subprocess.run(['launchctl', 'load', str(self.service_file)],
                             check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def stop_service(self) -> bool:
        """Stop the service"""
        if not self.is_supported():
            return False
        
        try:
            if self.system == "linux":
                subprocess.run(['systemctl', '--user', 'stop', self.service_name],
                             check=True, capture_output=True)
            elif self.system == "darwin":
                subprocess.run(['launchctl', 'unload', str(self.service_file)],
                             check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def restart_service(self) -> bool:
        """Restart the service"""
        if not self.is_supported():
            return False
        
        if self.system == "linux":
            try:
                subprocess.run(['systemctl', '--user', 'restart', self.service_name],
                             check=True, capture_output=True)
                return True
            except subprocess.CalledProcessError:
                return False
        else:
            # For macOS, stop and start
            return self.stop_service() and self.start_service()

    def is_service_running(self) -> bool:
        """Check if service is running"""
        if not self.is_supported():
            return False
        
        try:
            if self.system == "linux":
                result = subprocess.run(['systemctl', '--user', 'is-active', self.service_name],
                                      capture_output=True, text=True)
                return result.stdout.strip() == "active"
            elif self.system == "darwin":
                result = subprocess.run(['launchctl', 'list'], 
                                      capture_output=True, text=True)
                return f"com.{self.service_name}.proxy" in result.stdout
        except subprocess.CalledProcessError:
            return False
        
        return False

    def get_service_status(self) -> Dict[str, Any]:
        """Get detailed service status"""
        if not self.is_supported():
            return {"supported": False, "running": False}
        
        status = {
            "supported": True,
            "installed": self.service_file.exists() if self.service_file else False,
            "running": self.is_service_running(),
            "system": self.system
        }
        
        # Get additional status information
        if self.system == "linux":
            try:
                result = subprocess.run(['systemctl', '--user', 'status', self.service_name],
                                      capture_output=True, text=True)
                status["status_output"] = result.stdout
            except subprocess.CalledProcessError as e:
                status["status_output"] = e.stdout
        elif self.system == "darwin":
            try:
                result = subprocess.run(['launchctl', 'list', f"com.{self.service_name}.proxy"],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    status["launchctl_info"] = result.stdout
            except subprocess.CalledProcessError:
                pass
        
        return status

    def get_service_logs(self, lines: int = 50) -> List[str]:
        """Get service logs"""
        if not self.is_supported():
            return []
        
        logs = []
        
        try:
            if self.system == "linux":
                result = subprocess.run(['journalctl', '--user', '-u', self.service_name, 
                                       '-n', str(lines), '--no-pager'],
                                      capture_output=True, text=True, check=True)
                logs = result.stdout.split('\n')
            elif self.system == "darwin":
                # Check stdout log
                stdout_log = self.install_dir / "logs" / "stdout.log"
                stderr_log = self.install_dir / "logs" / "stderr.log"
                
                if stdout_log.exists():
                    with open(stdout_log, 'r') as f:
                        stdout_lines = f.readlines()
                        logs.extend([f"STDOUT: {line.rstrip()}" for line in stdout_lines[-lines//2:]])
                
                if stderr_log.exists():
                    with open(stderr_log, 'r') as f:
                        stderr_lines = f.readlines()
                        logs.extend([f"STDERR: {line.rstrip()}" for line in stderr_lines[-lines//2:]])
        
        except subprocess.CalledProcessError:
            pass
        
        return logs[-lines:] if logs else []

    def enable_auto_start(self) -> bool:
        """Enable service to start automatically on boot"""
        if not self.is_supported():
            return False
        
        try:
            if self.system == "linux":
                subprocess.run(['systemctl', '--user', 'enable', self.service_name],
                             check=True, capture_output=True)
                return True
            elif self.system == "darwin":
                # For launchd, modify the plist to set RunAtLoad to true
                if self.service_file.exists():
                    with open(self.service_file, 'r') as f:
                        content = f.read()
                    
                    # Simple string replacement (not robust XML parsing)
                    content = content.replace('<key>RunAtLoad</key>\n    <false/>', 
                                            '<key>RunAtLoad</key>\n    <true/>')
                    
                    with open(self.service_file, 'w') as f:
                        f.write(content)
                    
                    # Reload the service
                    if self.is_service_running():
                        self.stop_service()
                        self.start_service()
                    
                    return True
        except subprocess.CalledProcessError:
            return False
        
        return False

    def disable_auto_start(self) -> bool:
        """Disable service from starting automatically on boot"""
        if not self.is_supported():
            return False
        
        try:
            if self.system == "linux":
                subprocess.run(['systemctl', '--user', 'disable', self.service_name],
                             check=True, capture_output=True)
                return True
            elif self.system == "darwin":
                # For launchd, modify the plist to set RunAtLoad to false
                if self.service_file.exists():
                    with open(self.service_file, 'r') as f:
                        content = f.read()
                    
                    # Simple string replacement
                    content = content.replace('<key>RunAtLoad</key>\n    <true/>', 
                                            '<key>RunAtLoad</key>\n    <false/>')
                    
                    with open(self.service_file, 'w') as f:
                        f.write(content)
                    
                    return True
        except subprocess.CalledProcessError:
            return False
        
        return False


if __name__ == '__main__':
    # CLI for service management
    import argparse
    from config_manager import ConfigManager
    
    parser = argparse.ArgumentParser(description='Claude Code Multi-Provider Proxy Service Manager')
    parser.add_argument('action', choices=['install', 'uninstall', 'start', 'stop', 
                                         'restart', 'status', 'logs', 'enable', 'disable'])
    parser.add_argument('--install-dir', default=Path.home() / '.local/gemini-code',
                       help='Installation directory')
    parser.add_argument('--lines', type=int, default=50, help='Number of log lines to show')
    
    args = parser.parse_args()
    
    service_manager = ServiceManager(args.install_dir)
    config_manager = ConfigManager(Path(args.install_dir))
    
    if not service_manager.is_supported():
        print(f"Service management not supported on {platform.system()}")
        exit(1)
    
    if args.action == 'install':
        config = config_manager.load_config()
        if service_manager.install_service(config):
            print("Service installed successfully")
        else:
            print("Failed to install service")
    
    elif args.action == 'uninstall':
        if service_manager.uninstall_service():
            print("Service uninstalled successfully")
        else:
            print("Failed to uninstall service")
    
    elif args.action == 'start':
        if service_manager.start_service():
            print("Service started successfully")
        else:
            print("Failed to start service")
    
    elif args.action == 'stop':
        if service_manager.stop_service():
            print("Service stopped successfully")
        else:
            print("Failed to stop service")
    
    elif args.action == 'restart':
        if service_manager.restart_service():
            print("Service restarted successfully")
        else:
            print("Failed to restart service")
    
    elif args.action == 'status':
        status = service_manager.get_service_status()
        print(json.dumps(status, indent=2))
    
    elif args.action == 'logs':
        logs = service_manager.get_service_logs(args.lines)
        for log in logs:
            print(log)
    
    elif args.action == 'enable':
        if service_manager.enable_auto_start():
            print("Auto-start enabled")
        else:
            print("Failed to enable auto-start")
    
    elif args.action == 'disable':
        if service_manager.disable_auto_start():
            print("Auto-start disabled")
        else:
            print("Failed to disable auto-start")