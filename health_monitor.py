#!/usr/bin/env python3
"""
Health monitoring and auto-restart system for Claude Code Multi-Provider Proxy
"""

import asyncio
import time
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
import json
import subprocess
import requests
from datetime import datetime, timedelta
import psutil
import threading
import queue


class HealthMetrics:
    """Collects and manages health metrics"""
    
    def __init__(self):
        self.startup_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
        self.last_request_time: Optional[datetime] = None
        self.response_times: List[float] = []
        self.memory_usage: List[float] = []
        self.cpu_usage: List[float] = []
        self.restart_count = 0
        self.last_restart_time: Optional[datetime] = None
        
    def record_request(self, response_time: float, success: bool = True):
        """Record a request with its response time and success status"""
        self.request_count += 1
        self.last_request_time = datetime.now()
        self.response_times.append(response_time)
        
        if not success:
            self.error_count += 1
        
        # Keep only last 100 response times
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]
    
    def record_system_metrics(self):
        """Record current system metrics"""
        try:
            # Memory usage
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.memory_usage.append(memory_mb)
            
            # CPU usage
            cpu_percent = process.cpu_percent()
            self.cpu_usage.append(cpu_percent)
            
            # Keep only last 100 measurements
            if len(self.memory_usage) > 100:
                self.memory_usage = self.memory_usage[-100:]
            if len(self.cpu_usage) > 100:
                self.cpu_usage = self.cpu_usage[-100:]
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    def record_restart(self):
        """Record a restart event"""
        self.restart_count += 1
        self.last_restart_time = datetime.now()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current health metrics"""
        uptime = datetime.now() - self.startup_time
        
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        error_rate = (self.error_count / self.request_count) if self.request_count > 0 else 0
        avg_memory = sum(self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0
        avg_cpu = sum(self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0
        
        return {
            'uptime_seconds': uptime.total_seconds(),
            'uptime_formatted': str(uptime),
            'startup_time': self.startup_time.isoformat(),
            'request_count': self.request_count,
            'error_count': self.error_count,
            'error_rate': error_rate,
            'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None,
            'avg_response_time_ms': avg_response_time * 1000,
            'avg_memory_usage_mb': avg_memory,
            'avg_cpu_usage_percent': avg_cpu,
            'restart_count': self.restart_count,
            'last_restart_time': self.last_restart_time.isoformat() if self.last_restart_time else None
        }


class HealthChecker:
    """Performs health checks on the proxy server"""
    
    def __init__(self, base_url: str = "http://localhost:8082", timeout: int = 10):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
    async def check_health_endpoint(self) -> Dict[str, Any]:
        """Check the /health endpoint"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return {
                    'status': 'healthy',
                    'response_time': response_time,
                    'data': response.json()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'response_time': response_time,
                    'error': f"HTTP {response.status_code}"
                }
        except requests.exceptions.RequestException as e:
            return {
                'status': 'unreachable',
                'error': str(e)
            }
    
    async def check_test_connection(self) -> Dict[str, Any]:
        """Check the /test-connection endpoint"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/test-connection", timeout=self.timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return {
                    'status': 'healthy',
                    'response_time': response_time,
                    'data': response.json()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'response_time': response_time,
                    'error': f"HTTP {response.status_code}"
                }
        except requests.exceptions.RequestException as e:
            return {
                'status': 'unreachable',
                'error': str(e)
            }
    
    async def check_process_alive(self, pid: int) -> bool:
        """Check if process is still alive"""
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    async def perform_full_health_check(self, pid: Optional[int] = None) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy'
        }
        
        # Check process
        if pid:
            process_alive = await self.check_process_alive(pid)
            results['process'] = {
                'alive': process_alive,
                'pid': pid
            }
            if not process_alive:
                results['overall_status'] = 'unhealthy'
        
        # Check health endpoint
        health_check = await self.check_health_endpoint()
        results['health_endpoint'] = health_check
        if health_check['status'] != 'healthy':
            results['overall_status'] = 'unhealthy'
        
        # Check test connection
        connection_check = await self.check_test_connection()
        results['test_connection'] = connection_check
        if connection_check['status'] != 'healthy':
            results['overall_status'] = 'degraded'
        
        return results


class AutoRestarter:
    """Handles automatic restart of the proxy server"""
    
    def __init__(self, install_dir: Path, max_restarts: int = 5, restart_window: int = 300):
        self.install_dir = Path(install_dir)
        self.max_restarts = max_restarts
        self.restart_window = restart_window  # seconds
        self.restart_times: List[datetime] = []
        self.logger = logging.getLogger(__name__)
        
    def can_restart(self) -> bool:
        """Check if restart is allowed based on rate limiting"""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.restart_window)
        
        # Remove old restart times
        self.restart_times = [t for t in self.restart_times if t > window_start]
        
        # Check if we've hit the limit
        return len(self.restart_times) < self.max_restarts
    
    def record_restart(self):
        """Record a restart attempt"""
        self.restart_times.append(datetime.now())
    
    async def restart_server(self, pid: Optional[int] = None) -> bool:
        """Restart the server process"""
        if not self.can_restart():
            self.logger.error(f"Maximum restart limit ({self.max_restarts}) reached within {self.restart_window}s")
            return False
        
        self.logger.info("Attempting to restart server...")
        self.record_restart()
        
        try:
            # Stop existing process
            if pid:
                try:
                    process = psutil.Process(pid)
                    process.terminate()
                    process.wait(timeout=10)
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    # Force kill if still running
                    try:
                        process.kill()
                    except psutil.NoSuchProcess:
                        pass
            
            # Start new process
            env = os.environ.copy()
            server_py = self.install_dir / 'server.py'
            python_exe = self.install_dir / 'venv' / 'bin' / 'python'
            
            if not python_exe.exists():
                python_exe = 'python3'
            
            proc = subprocess.Popen(
                [str(python_exe), str(server_py)],
                cwd=str(self.install_dir),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # Save new PID
            pid_file = self.install_dir / '.claude-proxy.pid'
            with open(pid_file, 'w') as f:
                f.write(str(proc.pid))
            
            self.logger.info(f"Server restarted with PID {proc.pid}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restart server: {e}")
            return False


class HealthMonitor:
    """Main health monitoring service"""
    
    def __init__(self, install_dir: Path, config: Dict[str, Any]):
        self.install_dir = Path(install_dir)
        self.config = config
        self.running = False
        self.metrics = HealthMetrics()
        self.checker = HealthChecker(
            base_url=f"http://localhost:{config.get('server', {}).get('port', 8082)}"
        )
        self.restarter = AutoRestarter(install_dir)
        self.logger = self._setup_logging()
        
        # Configuration
        self.check_interval = config.get('reliability', {}).get('health_check_interval', 30)
        self.auto_restart_enabled = config.get('reliability', {}).get('auto_restart', True)
        self.max_failures = config.get('reliability', {}).get('max_consecutive_failures', 3)
        
        # State
        self.consecutive_failures = 0
        self.pid_file = self.install_dir / '.claude-proxy.pid'
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for health monitor"""
        logger = logging.getLogger('health_monitor')
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        log_file = self.install_dir / 'logs' / 'health-monitor.log'
        log_file.parent.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def get_current_pid(self) -> Optional[int]:
        """Get current server PID from PID file"""
        try:
            if self.pid_file.exists():
                with open(self.pid_file, 'r') as f:
                    return int(f.read().strip())
        except (ValueError, FileNotFoundError):
            pass
        return None
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        self.logger.info("Health monitor started")
        
        while self.running:
            try:
                # Record system metrics
                self.metrics.record_system_metrics()
                
                # Get current PID
                current_pid = self.get_current_pid()
                
                # Perform health check
                health_result = await self.checker.perform_full_health_check(current_pid)
                
                if health_result['overall_status'] == 'healthy':
                    self.consecutive_failures = 0
                    self.logger.debug("Health check passed")
                else:
                    self.consecutive_failures += 1
                    self.logger.warning(f"Health check failed ({self.consecutive_failures}/{self.max_failures}): {health_result}")
                    
                    # Auto-restart if enabled and threshold reached
                    if (self.auto_restart_enabled and 
                        self.consecutive_failures >= self.max_failures):
                        
                        self.logger.error("Maximum failures reached, attempting restart...")
                        if await self.restarter.restart_server(current_pid):
                            self.metrics.record_restart()
                            self.consecutive_failures = 0
                        else:
                            self.logger.error("Restart failed, monitoring will continue")
                
                # Save health report
                await self.save_health_report(health_result)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
            
            # Wait for next check
            await asyncio.sleep(self.check_interval)
    
    async def save_health_report(self, health_result: Dict[str, Any]):
        """Save health report to file"""
        report = {
            'health_check': health_result,
            'metrics': self.metrics.get_metrics(),
            'consecutive_failures': self.consecutive_failures
        }
        
        report_file = self.install_dir / 'logs' / 'health-report.json'
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
    
    def start(self):
        """Start the health monitor"""
        self.running = True
        asyncio.run(self.monitor_loop())
    
    def stop(self):
        """Stop the health monitor"""
        self.running = False
        self.logger.info("Health monitor stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current monitor status"""
        return {
            'running': self.running,
            'check_interval': self.check_interval,
            'auto_restart_enabled': self.auto_restart_enabled,
            'consecutive_failures': self.consecutive_failures,
            'max_failures': self.max_failures,
            'metrics': self.metrics.get_metrics()
        }


def signal_handler(monitor: HealthMonitor):
    """Handle shutdown signals"""
    def handler(signum, frame):
        logging.info(f"Received signal {signum}, shutting down...")
        monitor.stop()
        sys.exit(0)
    return handler


if __name__ == '__main__':
    import argparse
    import os
    from config_manager import ConfigManager
    
    parser = argparse.ArgumentParser(description='Claude Code Multi-Provider Proxy Health Monitor')
    parser.add_argument('--install-dir', default=Path.home() / '.local/claude-proxy',
                       help='Installation directory')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon')
    
    args = parser.parse_args()
    
    install_dir = Path(args.install_dir)
    config_manager = ConfigManager(install_dir)
    config = config_manager.load_config()
    
    monitor = HealthMonitor(install_dir, config)
    
    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler(monitor))
    signal.signal(signal.SIGINT, signal_handler(monitor))
    
    if args.daemon:
        # Daemonize
        import daemon
        import daemon.pidfile
        
        pid_file = install_dir / '.health-monitor.pid'
        
        with daemon.DaemonContext(
            pidfile=daemon.pidfile.PIDLockFile(str(pid_file)),
            working_directory=str(install_dir)
        ):
            monitor.start()
    else:
        monitor.start()