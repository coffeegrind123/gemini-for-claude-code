# Advanced Usage Guide

This guide covers advanced features and configurations for the Claude Code Multi-Provider Proxy.

## 🔧 Configuration Management

### Configuration Files

The proxy supports multiple configuration formats with the following precedence (highest to lowest):

1. Environment variables
2. `.env` file
3. `claude-proxy.json` 
4. `claude-proxy.yml`
5. Default values

### JSON Configuration

Create a `claude-proxy.json` file:

```json
{
  "api": {
    "gemini_api_key": "your-api-key",
    "base_url": "https://generativelanguage.googleapis.com"
  },
  "models": {
    "big_model": "gemini-1.5-pro-latest",
    "small_model": "gemini-1.5-flash-latest",
    "model_mappings": {
      "haiku": "gemini-1.5-flash-latest",
      "sonnet": "gemini-1.5-pro-latest",
      "opus": "gemini-1.5-pro-latest"
    }
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8082,
    "log_level": "WARNING"
  },
  "reliability": {
    "auto_restart": true,
    "health_check_interval": 30,
    "max_consecutive_failures": 3
  }
}
```

### YAML Configuration

Create a `claude-proxy.yml` file:

```yaml
api:
  gemini_api_key: your-api-key
  base_url: https://generativelanguage.googleapis.com

models:
  big_model: gemini-1.5-pro-latest
  small_model: gemini-1.5-flash-latest
  model_mappings:
    haiku: gemini-1.5-flash-latest
    sonnet: gemini-1.5-pro-latest
    opus: gemini-1.5-pro-latest

server:
  host: 0.0.0.0
  port: 8082
  log_level: WARNING

reliability:
  auto_restart: true
  health_check_interval: 30
  max_consecutive_failures: 3
```

## 🔄 Service Management

### Systemd (Linux)

```bash
# Install as system service
sudo systemctl enable claude-proxy
sudo systemctl start claude-proxy

# User service (recommended)
systemctl --user enable claude-proxy
systemctl --user start claude-proxy

# Check status
systemctl --user status claude-proxy

# View logs
journalctl --user -u claude-proxy -f
```

### Launchd (macOS)

```bash
# Load service
launchctl load ~/Library/LaunchAgents/com.claude-proxy.plist

# Unload service
launchctl unload ~/Library/LaunchAgents/com.claude-proxy.plist

# Check if running
launchctl list | grep claude-proxy
```

## 📊 Health Monitoring

### Built-in Health Monitor

The proxy includes a comprehensive health monitoring system:

```bash
# Start health monitor
python health_monitor.py --daemon

# Check health status
curl http://localhost:8082/health

# View health metrics
cat logs/health-report.json
```

### Health Check Endpoints

- `/health` - Basic health status
- `/test-connection` - Test Gemini API connectivity
- `/metrics` - Detailed performance metrics

### Custom Health Checks

Create custom health check scripts:

```python
import requests
import time

def check_proxy_health():
    try:
        response = requests.get('http://localhost:8082/health', timeout=5)
        return response.status_code == 200
    except:
        return False

def check_latency():
    start = time.time()
    response = requests.post('http://localhost:8082/v1/messages', 
                           json={'messages': [{'role': 'user', 'content': 'test'}]})
    return time.time() - start
```


## 🔐 Security Considerations

### API Key Management

```bash
# Use environment variables
export GEMINI_API_KEY="your-secret-key"

# Or use a secrets management system  
# Store in secure environment variables

# For Kubernetes
kubectl create secret generic gemini-api-key --from-literal=key=your-secret-key
```

### Network Security

```bash
# Bind to localhost only (production)
export HOST=127.0.0.1

# Use reverse proxy for HTTPS
# nginx.conf
upstream claude-proxy {
    server localhost:8082;
}

server {
    listen 443 ssl;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://claude-proxy;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📈 Performance Tuning

### Resource Limits

```bash
# Set memory limits
export MAX_MEMORY=1GB

# Configure worker processes
export WORKER_COUNT=4

# Tune connection pool
export MAX_CONNECTIONS=100
```

### Caching

Enable response caching:

```python
# Add to server.py
from cachetools import TTLCache

response_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minute cache

@app.middleware("http")
async def cache_middleware(request: Request, call_next):
    if request.method == "POST" and "/v1/messages" in str(request.url):
        # Implement caching logic
        pass
    return await call_next(request)
```

## 🧪 Testing and Development

### Development Mode

```bash
# Start with auto-reload
make dev

# Or manually
uvicorn server:app --reload --host 0.0.0.0 --port 8082
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
make test

# Or manually
python -m pytest tests/ -v
```

### Load Testing

```bash
# Using Apache Bench
ab -n 1000 -c 10 -p test_request.json -T application/json http://localhost:8082/v1/messages

# Using curl for single test
curl -X POST http://localhost:8082/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}],"model":"claude-3-sonnet-20240229","max_tokens":100}'
```

## 🔍 Debugging

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
claude-proxy start
```

### Request/Response Logging

Add to your configuration:

```json
{
  "advanced": {
    "logging": {
      "log_requests": true,
      "log_responses": true,
      "max_log_size": "10MB"
    }
  }
}
```

### Performance Profiling

```python
# Add profiling middleware
import cProfile
import pstats
from fastapi import Request

@app.middleware("http")
async def profile_middleware(request: Request, call_next):
    profiler = cProfile.Profile()
    profiler.enable()
    
    response = await call_next(request)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative').print_stats(10)
    
    return response
```

## 🚀 Production Deployment

### Recommended Setup

1. **Reverse Proxy**: Use nginx or Apache
2. **Process Manager**: Use systemd or supervisor
3. **Monitoring**: Set up health checks and alerts
4. **Logging**: Centralized logging with ELK stack
5. **Backups**: Regular configuration backups

### Environment Variables for Production

```bash
# Production configuration
export LOG_LEVEL=WARNING
export HOST=127.0.0.1
export MAX_RETRIES=3
export REQUEST_TIMEOUT=60
export FORCE_DISABLE_STREAMING=false

# Security
export GEMINI_API_KEY="$(cat /etc/secrets/gemini-api-key)"

# Performance
export MAX_TOKENS_LIMIT=8192
export MAX_STREAMING_RETRIES=5
```

### Monitoring Setup

```bash
# Install monitoring tools
pip install prometheus-client grafana-api

# Start monitoring
python -c "
from prometheus_client import start_http_server, Counter, Histogram
start_http_server(8000)
"
```