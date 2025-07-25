# Troubleshooting Guide

Common issues and solutions for the Claude Code Multi-Provider Proxy.

## 🚨 Common Issues

### Server Won't Start

**Problem**: `claude-proxy start` fails or server exits immediately.

**Solutions**:

1. **Check API Key**:
   ```bash
   claude-proxy config
   # Verify your API key is set correctly
   ```

2. **Check Dependencies**:
   ```bash
   claude-proxy install
   # Reinstall dependencies if needed
   ```

3. **Check Port Availability**:
   ```bash
   lsof -i :8082
   # Kill any process using port 8082
   sudo kill -9 <PID>
   ```

4. **Check Permissions**:
   ```bash
   ls -la ~/.local/claude-proxy/
   # Ensure files are readable/executable
   chmod +x ~/.local/claude-proxy/claude-proxy
   ```

### API Connection Errors

**Problem**: "Failed to connect to Gemini API" or similar errors.

**Solutions**:

1. **Test API Key**:
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://generativelanguage.googleapis.com/v1beta/models"
   ```

2. **Check Network Connectivity**:
   ```bash
   ping generativelanguage.googleapis.com
   # Check if you can reach Google's servers
   ```

3. **Verify Firewall/Proxy Settings**:
   ```bash
   export https_proxy=your-proxy-server:port
   export http_proxy=your-proxy-server:port
   ```

4. **Check API Quotas**:
   - Visit [Google AI Studio](https://aistudio.google.com)
   - Check your usage limits and quotas

### Claude Code Integration Issues

**Problem**: Claude Code doesn't connect to the proxy.

**Solutions**:

1. **Check Base URL**:
   ```bash
   echo $ANTHROPIC_BASE_URL
   # Should be http://localhost:8082
   export ANTHROPIC_BASE_URL=http://localhost:8082
   ```

2. **Verify Server is Running**:
   ```bash
   claude-proxy status
   curl http://localhost:8082/health
   ```

3. **Check Claude Code Version**:
   ```bash
   claude --version
   # Update if needed: npm update -g @anthropic-ai/claude-code
   ```

### Streaming Issues

**Problem**: Responses are cut off or malformed.

**Solutions**:

1. **Disable Streaming Temporarily**:
   ```bash
   export FORCE_DISABLE_STREAMING=true
   claude-proxy restart
   ```

2. **Increase Retry Limits**:
   ```bash
   export MAX_STREAMING_RETRIES=20
   claude-proxy restart
   ```

3. **Check Network Stability**:
   ```bash
   ping -c 10 generativelanguage.googleapis.com
   # Look for packet loss
   ```

### Performance Issues

**Problem**: Slow responses or high resource usage.

**Solutions**:

1. **Check System Resources**:
   ```bash
   top -p $(pgrep -f "server.py")
   # Monitor CPU/memory usage
   ```

2. **Reduce Model Size**:
   ```bash
   # Use smaller model for faster responses
   export SMALL_MODEL=gemini-1.5-flash-latest
   claude-proxy config
   ```

3. **Adjust Timeouts**:
   ```bash
   export REQUEST_TIMEOUT=120
   claude-proxy restart
   ```

## 🔍 Debugging Steps

### 1. Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
claude-proxy restart
claude-proxy logs -f
```

### 2. Check Health Status

```bash
# Basic health check
curl http://localhost:8082/health

# Detailed status
claude-proxy status

# Test API connectivity
curl http://localhost:8082/test-connection
```

### 3. Validate Configuration

```bash
# Check configuration
python config_manager.py --validate

# View current config
python -c "
from config_manager import ConfigManager
import json
cm = ConfigManager()
config = cm.load_config()
print(json.dumps(config, indent=2))
"
```

### 4. Test Manual Request

```bash
curl -X POST http://localhost:8082/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 10
  }'
```

## 🛠️ System-Specific Issues

### Linux Issues

**systemd Service Problems**:
```bash
# Check service status
systemctl --user status claude-proxy

# View service logs
journalctl --user -u claude-proxy -f

# Reload service configuration
systemctl --user daemon-reload
systemctl --user restart claude-proxy
```

**Permission Issues**:
```bash
# Fix file permissions
chmod +x ~/.local/bin/claude-proxy
chmod -R 755 ~/.local/claude-proxy/

# Check SELinux (if applicable)
getenforce
# If enforcing, you may need to adjust SELinux policies
```

### macOS Issues

**launchd Service Problems**:
```bash
# Check if service is loaded
launchctl list | grep claude-proxy

# View service logs
tail -f ~/.local/claude-proxy/logs/stdout.log
tail -f ~/.local/claude-proxy/logs/stderr.log

# Reload service
launchctl unload ~/Library/LaunchAgents/com.claude-proxy.proxy.plist
launchctl load ~/Library/LaunchAgents/com.claude-proxy.proxy.plist
```

**Python Environment Issues**:
```bash
# Check Python version
python3 --version

# Recreate virtual environment
rm -rf ~/.local/claude-proxy/venv
./install.sh
```


## 📋 Diagnostic Information

When reporting issues, include this information:

### System Information
```bash
# System details
uname -a
python3 --version
pip3 --version

# Proxy status  
claude-proxy status

# Service status
claude-proxy status
```

### Log Files
```bash
# Server logs
claude-proxy logs --lines 100

# Health monitor logs
cat ~/.local/claude-proxy/logs/health-monitor.log

# System service logs (Linux)
journalctl --user -u claude-proxy --lines 50

# System service logs (macOS)
cat ~/.local/claude-proxy/logs/stdout.log
cat ~/.local/claude-proxy/logs/stderr.log
```

### Configuration
```bash
# Sanitized configuration (remove API key)
python -c "
from config_manager import ConfigManager
import json
cm = ConfigManager()
config = cm.load_config()
config['api']['gemini_api_key'] = 'REDACTED'
print(json.dumps(config, indent=2))
"
```

## 🆘 Getting Help

### Before Asking for Help

1. Check this troubleshooting guide
2. Search existing issues on GitHub
3. Try the diagnostic steps above
4. Gather system information and logs

### Where to Get Help

- **GitHub Issues**: [Create an issue](https://github.com/your-repo/claude-proxy/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/claude-proxy/discussions)
- **Documentation**: Check all documentation files

### Creating a Good Issue Report

Include:
- **Problem description**: Clear, specific description
- **Steps to reproduce**: Exact commands and actions
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **System information**: OS, Python version, etc.
- **Logs**: Relevant log excerpts (sanitize API keys!)
- **Configuration**: Your config (remove secrets)

Example issue template:
```markdown
## Problem Description
Brief description of the issue

## Environment
- OS: macOS 13.5
- Python: 3.11.2
- Installation method: ./install.sh

## Steps to Reproduce
1. Run `claude-proxy start`
2. Execute `claude`
3. Error occurs

## Expected Behavior
Server should start and accept connections

## Actual Behavior
Server exits with error "API key invalid"

## Logs
```
[paste relevant logs here]
```

## Configuration
```json
{
  "api": {
    "gemini_api_key": "REDACTED"
  },
  ...
}
```
```

## 🔧 Quick Fixes

### Reset Everything
```bash
# Nuclear option - reset everything
claude-proxy stop
rm -rf ~/.local/claude-proxy
./install.sh
claude-proxy config
```

### Temporary Workarounds
```bash
# Disable streaming if having issues
export EMERGENCY_DISABLE_STREAMING=true

# Use smaller model for testing
export SMALL_MODEL=gemini-1.5-flash-latest
export BIG_MODEL=gemini-1.5-flash-latest

# Increase all timeouts
export REQUEST_TIMEOUT=300
export MAX_RETRIES=5
```