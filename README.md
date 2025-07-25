# FOR OFFICIAL GOOGLE AI CLI TOOL SEE https://github.com/google-gemini/gemini-cli

# Claude Code Proxy: Multi-Provider Support for Claude Code

This server acts as a bridge, enabling you to use **Claude Code** with multiple AI providers including **Google Gemini models**. It translates API requests and responses between the Anthropic format (used by Claude Code) and various provider formats (via LiteLLM), allowing seamless integration.

**Currently supported providers:**
- ✅ **Google Gemini** (all models including 2.5 Pro/Flash)
- 🚧 **OpenAI** (coming soon)
- 🚧 **Other providers** (planned)

![Claude Code with Gemini Proxy](image.png)

## Features

- **Claude Code Compatibility with Gemini**: Directly use the Claude Code CLI with Google Gemini models.
- **Seamless Model Mapping**: Intelligently maps Claude Code model requests (e.g., `haiku`, `sonnet`, `opus` aliases) to your chosen Gemini models.
- **LiteLLM Integration**: Leverages LiteLLM for robust and flexible interaction with the Gemini API.
- **Enhanced Streaming Support**: Handles streaming responses from Gemini with robust error recovery for malformed chunks and API errors.
- **Complete Tool Use for Claude Code**: Translates Claude Code's tool usage (function calling) to and from Gemini's format, with robust handling of tool results.
- **Advanced Error Handling**: Provides specific and actionable error messages for common Gemini API issues with automatic fallback strategies.
- **Resilient Architecture**: Gracefully handles Gemini API instability with smart retry logic and fallback to non-streaming modes.
- **Diagnostic Endpoints**: Includes `/health` and `/test-connection` for easier troubleshooting of your setup.
- **Token Counting**: Offers a `/v1/messages/count_tokens` endpoint compatible with Claude Code.

## Recent Improvements

### 🚀 **Transformed into User-Friendly Tool**
- **One-Command Installation**: `./install.sh` handles everything automatically
- **Secure Configuration**: API keys stored safely outside repository in `~/.config/`
- **System Integration**: Native systemd/launchd service support with auto-restart
- **CLI Interface**: Simple commands like `claude-proxy start`, `stop`, `status`, `config`

### 🔧 **Enhanced Functionality** 
- **Dynamic Model Discovery**: Auto-detects available Gemini models via API
- **Smart Model Selection**: Fast mode testing for optimal model recommendations
- **Updated Defaults**: Uses latest Gemini 2.0/2.5 models by default
- **Comprehensive Testing**: Multi-tier test suite with rate limit protection

### 🛡️ **Improved Reliability**
- **Malformed Chunk Recovery**: Automatically handles broken JSON from Gemini streaming
- **Smart Retry Logic**: Exponential backoff with configurable retry limits
- **Graceful Fallback**: Seamlessly switches to non-streaming when needed
- **Enhanced Error Handling**: Specific guidance for different Gemini API issues

## Prerequisites

- A Google Gemini API key.
- Python 3.8+.
- Claude Code CLI installed (e.g., `npm install -g @anthropic-ai/claude-code`).

## Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/coffeegrind123/gemini-code.git # Or your fork
    cd gemini-code
    ```

2.  **Install system-wide** (Recommended):
    ```bash
    ./install.sh
    ```
    This automatically handles:
    - Virtual environment creation
    - Dependency installation  
    - System integration
    - Secure configuration setup

3.  **Configure and start**:
    ```bash
    claude-proxy config  # Interactive setup
    claude-proxy start   # Start the proxy
    ```

## Quick Start

### Method 1: Installed System-Wide (Recommended)

First install the proxy system-wide:
```bash
./install.sh
```

Then use the installed CLI from anywhere:
```bash
# Configure the proxy (interactive setup)
claude-proxy config

# Start the proxy server
claude-proxy start

# Check status and get connection info
claude-proxy status

# Validate and optimize model selection
claude-proxy models --update-config

# Stop the server
claude-proxy stop
```

### Method 2: Run from Repository (Development)

For development or testing without installation:
```bash
# Configure the proxy (interactive setup)
./claude-proxy config

# Start the proxy server
./claude-proxy start

# Check status and get connection info
./claude-proxy status

# Stop the server
./claude-proxy stop
```

### Usage with Claude Code

1.  **Start the Proxy Server**: Ensure the proxy server is running:
    ```bash
    # If installed system-wide:
    claude-proxy start
    
    # Or if running from repository:
    ./claude-proxy start
    ```

2.  **Configure Claude Code to Use the Proxy**:
    Set the `ANTHROPIC_BASE_URL` environment variable when running Claude Code:
    ```bash
    ANTHROPIC_BASE_URL=http://localhost:8082 claude
    ```
    Replace `localhost:8082` if your proxy is running on a different host or port.

3.  **Utilize `CLAUDE.md` for Optimal Gemini Performance (Crucial)**:
    - This repository includes a `CLAUDE.md` file. This file contains specific instructions and best practices tailored to help **Gemini** effectively understand and respond to **Claude Code's** unique command structure, tool usage patterns, and desired output formats.
    - **Copy `CLAUDE.md` into your project directory**:
      ```bash
      cp /path/to/gemini-code/CLAUDE.md /your/project/directory/
      ```
    - When starting a new conversation with Claude Code in that directory, begin with:
      ```
      First read and process CLAUDE.md with intent. After understanding and agreeing to use the policies and practices outlined in the document, respond with YES
      ```
    - This ensures Gemini receives important context and instructions for better assistance.
  
    - If Gemini still fucks up, ask it to read CLAUDE.md again. This might or might not help!

## How It Works: Powering Claude Code with Gemini

1.  **Claude Code Request**: You issue a command or prompt in the Claude Code CLI.
2.  **Anthropic Format**: Claude Code sends an API request (in Anthropic's Messages API format) to the proxy server's address (`http://localhost:8082`).
3.  **Proxy Translation (Anthropic to Gemini)**: The proxy server:
    *   Receives the Anthropic-formatted request.
    *   Validates it and maps any Claude model aliases (like `claude-3-sonnet...`) to the corresponding Gemini model specified in your configuration (e.g., `gemini-2.0-flash-exp`).
    *   Translates the message structure, content blocks, and tool definitions into a format LiteLLM can use with the Gemini API.
4.  **LiteLLM to Gemini**: LiteLLM sends the prepared request to the target Gemini model using your `GEMINI_API_KEY`.
5.  **Gemini Response**: Gemini processes the request and sends its response back through LiteLLM.
6.  **Proxy Translation (Gemini to Anthropic)**: The proxy server:
    *   Receives the Gemini response from LiteLLM (this can be a stream of events or a complete JSON object).
    *   Handles streaming errors and malformed chunks with intelligent recovery.
    *   Converts Gemini's output (text, tool calls, stop reasons) back into the Anthropic Messages API format that Claude Code expects.
7.  **Response to Claude Code**: The proxy sends the Anthropic-formatted response back to your Claude Code client, which then displays the result or performs the requested action.

## Model Mapping for Claude Code

To ensure Claude Code's model requests are handled correctly by Gemini:

- Requests from Claude Code for model names containing **"haiku"** (e.g., `claude-3-haiku-20240307`) are mapped to the Gemini model specified by your `SMALL_MODEL` configuration (default: `gemini-1.5-flash-latest`).
- Requests from Claude Code for model names containing **"sonnet"** or **"opus"** (e.g., `claude-3-sonnet-20240229`, `claude-3-opus-20240229`) are mapped to the Gemini model specified by your `BIG_MODEL` configuration (default: `gemini-2.0-flash-exp`).
- If Claude Code requests a full Gemini model name (e.g., `gemini/gemini-1.5-pro-latest`), the proxy will use that directly.

The server maintains a list of known Gemini models. If a recognized Gemini model is requested by the client without the `gemini/` prefix, the proxy will add it.

## Endpoints

- `POST /v1/messages`: The primary endpoint for Claude Code to send messages to Gemini. It's fully compatible with the Anthropic Messages API specification that Claude Code uses.
- `POST /v1/messages/count_tokens`: Allows Claude Code to estimate the token count for a set of messages, using Gemini's tokenization.
- `GET /health`: Returns the health status of the proxy, including API key configuration, streaming settings, and basic API key validation.
- `GET /test-connection`: Performs a quick API call to Gemini to verify connectivity and that your `GEMINI_API_KEY` is working.
- `GET /`: Root endpoint providing a welcome message, current configuration summary (models, limits), and available endpoints.

## Error Handling & Troubleshooting

### Common Issues and Solutions

**Streaming Errors (malformed chunks):**
- The proxy automatically handles malformed JSON chunks from Gemini
- If streaming becomes unstable, set `FORCE_DISABLE_STREAMING=true` as a temporary fix
- Increase `MAX_STREAMING_RETRIES` for more resilient streaming

**Gemini 500 Internal Server Errors:**
- The proxy automatically retries with exponential backoff
- These are temporary Gemini API issues that resolve automatically
- Check `/health` endpoint to monitor API status

**Connection Timeouts:**
- Increase `REQUEST_TIMEOUT` if experiencing frequent timeouts
- Check your internet connection and firewall settings
- Use `/test-connection` endpoint to verify API connectivity

**Rate Limiting:**
- Monitor your Google AI Studio quota in the Google Cloud Console
- The proxy will provide specific rate limit guidance in error messages

### Emergency Mode

If you experience persistent issues:
```bash
# Disable streaming temporarily
export EMERGENCY_DISABLE_STREAMING=true

# Or force disable all streaming
export FORCE_DISABLE_STREAMING=true
```

## Logging

The server provides detailed logs, which are especially useful for understanding how Claude Code requests are translated for Gemini and for monitoring error recovery. Logs are colorized in TTY environments for easier reading. Adjust verbosity in your configuration or with the `LOG_LEVEL` environment variable:

- `DEBUG`: Detailed request/response logging and error recovery steps
- `INFO`: General operation logging
- `WARNING`: Error recovery and fallback notifications (recommended)
- `ERROR`: Only errors and failures
- `CRITICAL`: Only critical failures

## The `CLAUDE.MD` File: Guiding Gemini for Claude Code

The `CLAUDE.MD` file included in this repository is critical for achieving the best experience when using this proxy with Claude Code and Gemini.

**Purpose:**

- **Tailors Gemini to Claude Code's Needs**: Claude Code has specific ways it expects an LLM to behave, especially regarding tool use, file operations, and output formatting. `CLAUDE.MD` provides Gemini with explicit instructions on these expectations.
- **Improves Tool Reliability**: By outlining how tools should be called and results interpreted, it helps Gemini make more effective use of Claude Code's capabilities.
- **Enhances Code Generation & Understanding**: Gives Gemini context about the development environment and coding standards, leading to better code suggestions within Claude Code.
- **Reduces Misinterpretations**: Helps bridge any gaps between how Anthropic models might interpret Claude Code directives versus how Gemini might.

**How Claude Code Uses It:**

When you run `claude` in a project directory, the Claude Code CLI automatically looks for a `CLAUDE.MD` file in that directory. If found, its contents are prepended to the system prompt for every request sent to the LLM (in this case, your Gemini proxy).

**Recommendation:** Always copy the `CLAUDE.MD` from this proxy's repository into the root of any project where you intend to use Claude Code with this Gemini proxy. This ensures Gemini receives these vital instructions for every session.

## Testing

The proxy includes a comprehensive test suite to verify functionality:

```bash
# Install test dependencies (if not already installed)
pip install aiohttp

# Run all tests (includes API calls - may hit rate limits with frequent use)
make test

# Run quick tests (no API calls, just health checks)
make test-quick

# Run minimal API tests (single connectivity test to avoid rate limits)
make test-minimal

# Debug model availability and rate limits
python3 test_proxy.py --debug-models
```

**Test Modes:**
- **Quick**: Basic connectivity (no API usage)
- **Minimal**: Single API call to verify connection
- **Full**: Comprehensive testing (may trigger rate limits)
- **Debug**: Test all available Gemini models to identify working ones

The tests automatically read your configuration and test the appropriate endpoints.

## Performance Tips

- **Model Selection**: Use `gemini-1.5-flash-latest` for faster responses, `gemini-2.0-flash-exp` for more complex tasks with the latest capabilities
- **Model Availability**: Different Gemini models have different rate limits and availability - use the debug test to identify which models work with your API key
- **Streaming**: Keep streaming enabled for better interactivity; the proxy handles errors automatically
- **Timeouts**: Increase `REQUEST_TIMEOUT` for complex requests that need more processing time
- **Retries**: Adjust `MAX_STREAMING_RETRIES` based on your network stability

## Contributing

Contributions, issues, and feature requests are welcome! Please submit them on the GitHub repository.

Areas where contributions are especially valuable:
- Additional Gemini model support
- Performance optimizations
- Enhanced error recovery strategies
- Documentation improvements

## Thanks

This project was heavily inspired by and builds upon the foundational work of the [claude-code-proxy by @1rgs](https://github.com/1rgs/claude-code-proxy). Their original proxy was instrumental in demonstrating the viability of such a bridge.

Special thanks to the community for testing and feedback on error handling improvements.
