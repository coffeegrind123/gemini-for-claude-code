# Claude Code Multi-Provider Proxy - Quick Start Guide

Get up and running with the Claude Code Multi-Provider Proxy in under 5 minutes!

## 🚀 One-Command Installation

```bash
# Clone and install
git clone https://github.com/your-repo/gemini-code.git
cd gemini-code
./install.sh
```

## 📋 Prerequisites

- Python 3.8+
- Google AI Studio API key ([Get yours here](https://aistudio.google.com/app/apikey))
- Claude Code CLI installed

## ⚡ Quick Setup

### 1. Configure API Key
```bash
claude-proxy config
# Follow the interactive prompts to set your API key
# Config is stored securely in ~/.config/gemini-code/
```

### 2. Start the Proxy
```bash
claude-proxy start
```

### 3. Use with Claude Code
```bash
export ANTHROPIC_BASE_URL=http://localhost:8082
claude
```

That's it! 🎉


## 🔧 CLI Commands

```bash
claude-proxy start        # Start the proxy server
claude-proxy stop         # Stop the server
claude-proxy status       # Check server status
claude-proxy config       # Configure settings
claude-proxy logs         # View logs
```

## 🆘 Need Help?

- **Server won't start?** Check `claude-proxy logs`
- **API errors?** Verify your API key with `claude-proxy config`
- **Connection issues?** Check `claude-proxy status`

## 📚 More Information

- [Full Documentation](./ADVANCED_USAGE.md)
- [Configuration Guide](./CONFIGURATION.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
