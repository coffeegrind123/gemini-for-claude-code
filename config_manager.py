#!/usr/bin/env python3
"""
Configuration management for Claude Code Multi-Provider Proxy
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml


class ConfigManager:
    """Manages configuration for Claude Code Multi-Provider Proxy"""
    
    SUPPORTED_MODELS = [
        'gemini-1.5-pro-latest',
        'gemini-1.5-pro',
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash',
        'gemini-1.0-pro-latest',
        'gemini-1.0-pro'
    ]
    
    LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    
    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Use XDG-compliant config directory structure
            if os.name == 'nt':  # Windows
                self.config_dir = Path.home() / 'AppData' / 'Local' / 'gemini-code'
            else:  # Unix-like (Linux, macOS)
                xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
                if xdg_config_home:
                    self.config_dir = Path(xdg_config_home) / 'gemini-code'
                else:
                    self.config_dir = Path.home() / '.config' / 'gemini-code'
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.env_file = self.config_dir / 'config.env'
        self.config_file = self.config_dir / 'config.json'
        self.yaml_config_file = self.config_dir / 'config.yml'
        
        self.default_config = {
            'api': {
                'gemini_api_key': '',
                'base_url': 'https://generativelanguage.googleapis.com'
            },
            'models': {
                'big_model': 'gemini-1.5-pro-latest',
                'small_model': 'gemini-1.5-flash-latest',
                'model_mappings': {
                    'haiku': 'gemini-1.5-flash-latest',
                    'sonnet': 'gemini-1.5-pro-latest',
                    'opus': 'gemini-1.5-pro-latest'
                }
            },
            'server': {
                'host': '0.0.0.0',
                'port': 8082,
                'log_level': 'WARNING',
                'max_tokens_limit': 8192,
                'request_timeout': 90
            },
            'reliability': {
                'max_retries': 2,
                'max_streaming_retries': 12,
                'force_disable_streaming': False,
                'emergency_disable_streaming': False,
                'auto_restart': True,
                'health_check_interval': 30
            },
            'advanced': {
                'enable_cors': False,
                'cors_origins': ['*'],
                'rate_limiting': {
                    'enabled': False,
                    'requests_per_minute': 60
                },
                'logging': {
                    'file_logging': True,
                    'log_file': 'claude-proxy.log',
                    'max_log_size': '10MB',
                    'backup_count': 5
                }
            }
        }

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from various sources in order of precedence"""
        config = self.default_config.copy()
        
        # 1. Load from YAML config (lowest precedence)
        if self.yaml_config_file.exists():
            with open(self.yaml_config_file, 'r') as f:
                yaml_config = yaml.safe_load(f)
                config = self._merge_configs(config, yaml_config)
        
        # 2. Load from JSON config
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                json_config = json.load(f)
                config = self._merge_configs(config, json_config)
        
        # 3. Load from .env file
        env_config = self._load_env_config()
        config = self._merge_configs(config, env_config)
        
        # 4. Load from environment variables (highest precedence)
        env_var_config = self._load_env_vars()
        config = self._merge_configs(config, env_var_config)
        
        return config

    def save_config(self, config: Dict[str, Any], format: str = 'json'):
        """Save configuration to file"""
        if format == 'json':
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        elif format == 'yaml':
            with open(self.yaml_config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
        elif format == 'env':
            self._save_env_config(config)

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result

    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from .env file"""
        config = {}
        if not self.env_file.exists():
            return config
        
        with open(self.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    
                    # Map env vars to config structure
                    if key == 'GEMINI_API_KEY':
                        config.setdefault('api', {})['gemini_api_key'] = value
                    elif key == 'BIG_MODEL':
                        config.setdefault('models', {})['big_model'] = value
                    elif key == 'SMALL_MODEL':
                        config.setdefault('models', {})['small_model'] = value
                    elif key == 'HOST':
                        config.setdefault('server', {})['host'] = value
                    elif key == 'PORT':
                        config.setdefault('server', {})['port'] = int(value)
                    elif key == 'LOG_LEVEL':
                        config.setdefault('server', {})['log_level'] = value
                    elif key == 'MAX_TOKENS_LIMIT':
                        config.setdefault('server', {})['max_tokens_limit'] = int(value)
                    elif key == 'REQUEST_TIMEOUT':
                        config.setdefault('server', {})['request_timeout'] = int(value)
                    elif key == 'MAX_RETRIES':
                        config.setdefault('reliability', {})['max_retries'] = int(value)
                    elif key == 'MAX_STREAMING_RETRIES':
                        config.setdefault('reliability', {})['max_streaming_retries'] = int(value)
                    elif key == 'FORCE_DISABLE_STREAMING':
                        config.setdefault('reliability', {})['force_disable_streaming'] = value.lower() == 'true'
                    elif key == 'EMERGENCY_DISABLE_STREAMING':
                        config.setdefault('reliability', {})['emergency_disable_streaming'] = value.lower() == 'true'
        
        return config

    def _load_env_vars(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}
        env_mappings = {
            'GEMINI_API_KEY': ('api', 'gemini_api_key'),
            'BIG_MODEL': ('models', 'big_model'),
            'SMALL_MODEL': ('models', 'small_model'),
            'HOST': ('server', 'host'),
            'PORT': ('server', 'port'),
            'LOG_LEVEL': ('server', 'log_level'),
            'MAX_TOKENS_LIMIT': ('server', 'max_tokens_limit'),
            'REQUEST_TIMEOUT': ('server', 'request_timeout'),
            'MAX_RETRIES': ('reliability', 'max_retries'),
            'MAX_STREAMING_RETRIES': ('reliability', 'max_streaming_retries'),
            'FORCE_DISABLE_STREAMING': ('reliability', 'force_disable_streaming'),
            'EMERGENCY_DISABLE_STREAMING': ('reliability', 'emergency_disable_streaming'),
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                config.setdefault(section, {})
                
                # Type conversion
                if key in ['port', 'max_tokens_limit', 'request_timeout', 'max_retries', 'max_streaming_retries']:
                    config[section][key] = int(value)
                elif key in ['force_disable_streaming', 'emergency_disable_streaming']:
                    config[section][key] = value.lower() == 'true'
                else:
                    config[section][key] = value
        
        return config

    def _save_env_config(self, config: Dict[str, Any]):
        """Save configuration to .env file"""
        lines = [
            "# Claude Code Multi-Provider Proxy Configuration",
            "# Generated automatically - edit with caution",
            "",
            "# API Configuration",
            f"GEMINI_API_KEY={config.get('api', {}).get('gemini_api_key', '')}",
            "",
            "# Model Configuration",
            f"BIG_MODEL={config.get('models', {}).get('big_model', 'gemini-1.5-pro-latest')}",
            f"SMALL_MODEL={config.get('models', {}).get('small_model', 'gemini-1.5-flash-latest')}",
            "",
            "# Server Configuration",
            f"HOST={config.get('server', {}).get('host', '0.0.0.0')}",
            f"PORT={config.get('server', {}).get('port', 8082)}",
            f"LOG_LEVEL={config.get('server', {}).get('log_level', 'WARNING')}",
            f"MAX_TOKENS_LIMIT={config.get('server', {}).get('max_tokens_limit', 8192)}",
            f"REQUEST_TIMEOUT={config.get('server', {}).get('request_timeout', 90)}",
            "",
            "# Reliability Configuration",
            f"MAX_RETRIES={config.get('reliability', {}).get('max_retries', 2)}",
            f"MAX_STREAMING_RETRIES={config.get('reliability', {}).get('max_streaming_retries', 12)}",
            f"FORCE_DISABLE_STREAMING={str(config.get('reliability', {}).get('force_disable_streaming', False)).lower()}",
            f"EMERGENCY_DISABLE_STREAMING={str(config.get('reliability', {}).get('emergency_disable_streaming', False)).lower()}",
        ]
        
        with open(self.env_file, 'w') as f:
            f.write('\n'.join(lines))

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate API key
        api_key = config.get('api', {}).get('gemini_api_key', '')
        if not api_key or api_key == 'your-google-ai-studio-key-here':
            errors.append("GEMINI_API_KEY is required")
        
        # Validate models
        big_model = config.get('models', {}).get('big_model', '')
        small_model = config.get('models', {}).get('small_model', '')
        
        if big_model not in self.SUPPORTED_MODELS:
            errors.append(f"Unsupported big_model: {big_model}")
        
        if small_model not in self.SUPPORTED_MODELS:
            errors.append(f"Unsupported small_model: {small_model}")
        
        # Validate server settings
        port = config.get('server', {}).get('port', 8082)
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append("Invalid port number")
        
        log_level = config.get('server', {}).get('log_level', 'WARNING')
        if log_level not in self.LOG_LEVELS:
            errors.append(f"Invalid log_level: {log_level}")
        
        # Validate numeric settings
        numeric_settings = [
            ('server', 'max_tokens_limit', 1, 100000),
            ('server', 'request_timeout', 1, 600),
            ('reliability', 'max_retries', 0, 10),
            ('reliability', 'max_streaming_retries', 0, 50)
        ]
        
        for section, key, min_val, max_val in numeric_settings:
            value = config.get(section, {}).get(key, 0)
            if not isinstance(value, int) or value < min_val or value > max_val:
                errors.append(f"Invalid {key}: must be between {min_val} and {max_val}")
        
        return errors

    def get_env_dict(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Convert config to environment variables dictionary"""
        return {
            'GEMINI_API_KEY': config.get('api', {}).get('gemini_api_key', ''),
            'BIG_MODEL': config.get('models', {}).get('big_model', 'gemini-1.5-pro-latest'),
            'SMALL_MODEL': config.get('models', {}).get('small_model', 'gemini-1.5-flash-latest'),
            'HOST': config.get('server', {}).get('host', '0.0.0.0'),
            'PORT': str(config.get('server', {}).get('port', 8082)),
            'LOG_LEVEL': config.get('server', {}).get('log_level', 'WARNING'),
            'MAX_TOKENS_LIMIT': str(config.get('server', {}).get('max_tokens_limit', 8192)),
            'REQUEST_TIMEOUT': str(config.get('server', {}).get('request_timeout', 90)),
            'MAX_RETRIES': str(config.get('reliability', {}).get('max_retries', 2)),
            'MAX_STREAMING_RETRIES': str(config.get('reliability', {}).get('max_streaming_retries', 12)),
            'FORCE_DISABLE_STREAMING': str(config.get('reliability', {}).get('force_disable_streaming', False)).lower(),
            'EMERGENCY_DISABLE_STREAMING': str(config.get('reliability', {}).get('emergency_disable_streaming', False)).lower(),
        }

    def create_template_config(self, format: str = 'yaml'):
        """Create a template configuration file"""
        template_config = self.default_config.copy()
        template_config['api']['gemini_api_key'] = 'your-google-ai-studio-key-here'
        
        if format == 'yaml':
            with open(self.config_dir / 'claude-proxy.template.yml', 'w') as f:
                f.write("# Claude Code Multi-Provider Proxy Configuration Template\n")
                f.write("# Copy this to claude-proxy.yml and customize\n\n")
                yaml.dump(template_config, f, default_flow_style=False, indent=2)
        elif format == 'json':
            with open(self.config_dir / 'claude-proxy.template.json', 'w') as f:
                json.dump(template_config, f, indent=2)

if __name__ == '__main__':
    # CLI for config management
    import argparse
    
    parser = argparse.ArgumentParser(description='Claude Code Multi-Provider Proxy Configuration Manager')
    parser.add_argument('--init', action='store_true', help='Initialize configuration')
    parser.add_argument('--validate', action='store_true', help='Validate configuration')
    parser.add_argument('--format', choices=['json', 'yaml', 'env'], default='json', help='Configuration format')
    
    args = parser.parse_args()
    
    config_manager = ConfigManager()
    
    if args.init:
        config_manager.create_template_config(args.format)
        print(f"Template configuration created: claude-proxy.template.{args.format}")
    
    if args.validate:
        config = config_manager.load_config()
        errors = config_manager.validate_config(config)
        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("Configuration is valid!")