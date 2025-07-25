#!/usr/bin/env python3
"""
Simple test suite for the Claude Code Multi-Provider Proxy.
Tests basic functionality of all endpoints.
"""

import asyncio
import json
import os
import sys
import time
from typing import Dict, Any, Optional
from pathlib import Path
import aiohttp
import argparse


class ProxyTester:
    def __init__(self, base_url: Optional[str] = None):
        if base_url is None:
            base_url = self._get_config_url()
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_results = []
    
    def _get_config_url(self) -> str:
        """Read configuration to determine the proxy URL"""
        # Use same config location logic as claude-proxy CLI
        if os.name == 'nt':  # Windows
            config_dir = Path.home() / 'AppData' / 'Local' / 'gemini-code'
        else:  # Unix-like (Linux, macOS)
            xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
            if xdg_config_home:
                config_dir = Path(xdg_config_home) / 'gemini-code'
            else:
                config_dir = Path.home() / '.config' / 'gemini-code'
        
        config_file = config_dir / 'config.env'
        
        # Default values
        host = "localhost"
        port = "8082"
        
        # Try to read config
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"\'')
                            
                            if key == 'HOST':
                                host = value
                            elif key == 'PORT':
                                port = value
            except Exception as e:
                print(f"Warning: Could not read config file {config_file}: {e}")
        
        # Convert 0.0.0.0 to localhost for client connections
        if host == "0.0.0.0":
            host = "localhost"
        
        return f"http://{host}:{port}"
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_test(self, test_name: str, status: str, details: str = "", duration: float = 0):
        """Log test results"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "duration": f"{duration:.2f}s"
        }
        self.test_results.append(result)
        
        # Colored output
        if status == "PASS":
            status_color = "\033[92m"  # green
        elif status == "SKIP":
            status_color = "\033[93m"  # yellow
        else:
            status_color = "\033[91m"  # red
        reset_color = "\033[0m"
        
        print(f"{status_color}[{status}]{reset_color} {test_name} ({duration:.2f}s)")
        if details:
            print(f"    {details}")
    
    async def test_health_endpoint(self) -> bool:
        """Test /health endpoint"""
        start_time = time.time()
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                duration = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    details = f"Status: {data.get('status')}, API configured: {data.get('gemini_api_configured')}"
                    self.log_test("Health Check", "PASS", details, duration)
                    return True
                else:
                    self.log_test("Health Check", "FAIL", f"HTTP {response.status}", duration)
                    return False
                    
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Health Check", "FAIL", str(e), duration)
            return False
    
    async def test_root_endpoint(self) -> bool:
        """Test / (root) endpoint"""
        start_time = time.time()
        try:
            async with self.session.get(f"{self.base_url}/") as response:
                duration = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    details = f"Version: {data.get('message', 'Unknown')}"
                    self.log_test("Root Endpoint", "PASS", details, duration)
                    return True
                else:
                    self.log_test("Root Endpoint", "FAIL", f"HTTP {response.status}", duration)
                    return False
                    
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Root Endpoint", "FAIL", str(e), duration)
            return False
    
    async def test_connection_endpoint(self) -> bool:
        """Test /test-connection endpoint"""
        start_time = time.time()
        try:
            async with self.session.get(f"{self.base_url}/test-connection") as response:
                duration = time.time() - start_time
                data = await response.json()
                
                if response.status == 200:
                    details = f"API test successful: {data.get('message', 'Unknown')}"
                    self.log_test("Connection Test", "PASS", details, duration)
                    return True
                else:
                    details = f"HTTP {response.status}: {data.get('message', 'Unknown error')}"
                    self.log_test("Connection Test", "FAIL", details, duration)
                    return False
                    
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Connection Test", "FAIL", str(e), duration)
            return False
    
    async def test_token_count_endpoint(self) -> bool:
        """Test /v1/messages/count_tokens endpoint"""
        start_time = time.time()
        payload = {
            "model": "claude-3-5-haiku-20241022",
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ]
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/messages/count_tokens",
                json=payload
            ) as response:
                duration = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    token_count = data.get('input_tokens', 0)
                    details = f"Token count: {token_count}"
                    self.log_test("Token Count", "PASS", details, duration)
                    return True
                else:
                    error_text = await response.text()
                    self.log_test("Token Count", "FAIL", f"HTTP {response.status}: {error_text[:100]}", duration)
                    return False
                    
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Token Count", "FAIL", str(e), duration)
            return False
    
    async def test_simple_message(self) -> bool:
        """Test simple message completion"""
        start_time = time.time()
        payload = {
            "model": "claude-3-5-haiku-20241022",
            "max_tokens": 50,
            "messages": [
                {"role": "user", "content": "Say hello in exactly 3 words."}
            ]
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/messages",
                json=payload
            ) as response:
                duration = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    content = data.get('content', [])
                    if content and content[0].get('type') == 'text':
                        text_response = content[0].get('text', '')
                        details = f"Response: '{text_response[:50]}{'...' if len(text_response) > 50 else ''}'"
                        self.log_test("Simple Message", "PASS", details, duration)
                        return True
                    else:
                        self.log_test("Simple Message", "FAIL", "No text content in response", duration)
                        return False
                else:
                    error_text = await response.text()
                    self.log_test("Simple Message", "FAIL", f"HTTP {response.status}: {error_text[:100]}", duration)
                    return False
                    
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Simple Message", "FAIL", str(e), duration)
            return False
    
    async def test_streaming_message(self) -> bool:
        """Test streaming message completion"""
        start_time = time.time()
        payload = {
            "model": "claude-3-5-haiku-20241022",
            "max_tokens": 30,
            "stream": True,
            "messages": [
                {"role": "user", "content": "Count from 1 to 5."}
            ]
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/messages",
                json=payload
            ) as response:
                duration = time.time() - start_time
                
                if response.status == 200:
                    # Read streaming response
                    chunks_received = 0
                    content_chunks = []
                    
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            chunks_received += 1
                            try:
                                data = json.loads(line_str[6:])  # Remove "data: " prefix
                                if data.get('type') == 'content_block_delta':
                                    delta = data.get('delta', {})
                                    if delta.get('type') == 'text_delta':
                                        content_chunks.append(delta.get('text', ''))
                            except json.JSONDecodeError:
                                pass  # Skip malformed chunks
                    
                    if chunks_received > 0:
                        full_content = ''.join(content_chunks)
                        details = f"Received {chunks_received} chunks, content: '{full_content[:50]}{'...' if len(full_content) > 50 else ''}'"
                        self.log_test("Streaming Message", "PASS", details, duration)
                        return True
                    else:
                        self.log_test("Streaming Message", "FAIL", "No chunks received", duration)
                        return False
                else:
                    error_text = await response.text()
                    self.log_test("Streaming Message", "FAIL", f"HTTP {response.status}: {error_text[:100]}", duration)
                    return False
                    
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Streaming Message", "FAIL", str(e), duration)
            return False
    
    async def test_model_mapping(self) -> bool:
        """Test model name mapping (Anthropic -> Gemini)"""
        start_time = time.time()
        payload = {
            "model": "claude-3-5-sonnet-20241022",  # Should map to big model
            "max_tokens": 20,
            "messages": [
                {"role": "user", "content": "Hi"}
            ]
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/messages",
                json=payload
            ) as response:
                duration = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    mapped_model = data.get('model', '')
                    details = f"Model mapping: claude-3-5-sonnet -> {mapped_model}"
                    self.log_test("Model Mapping", "PASS", details, duration)
                    return True
                elif response.status == 500:
                    error_text = await response.text()
                    if "rate limit" in error_text.lower() or "quota" in error_text.lower():
                        # Rate limit - let's see if this is the issue
                        self.log_test("Model Mapping", "SKIP", f"Rate limited: {error_text[:100]}", duration)
                        return True  # Return True to not fail the overall test
                    else:
                        self.log_test("Model Mapping", "FAIL", f"HTTP {response.status}: {error_text[:200]}", duration)
                        return False
                else:
                    error_text = await response.text()
                    self.log_test("Model Mapping", "FAIL", f"HTTP {response.status}: {error_text[:200]}", duration)
                    return False
                    
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Model Mapping", "FAIL", str(e), duration)
            return False
    
    async def debug_model_limits(self):
        """Test different model combinations to understand rate limits"""
        test_models = [
            ("claude-3-5-haiku-20241022", "Small model (Haiku → Flash 1.5)"),
            ("claude-3-5-sonnet-20241022", "Big model (Sonnet → 2.0 Flash Exp)"),
            ("gemini-1.5-flash-latest", "Direct Gemini 1.5 Flash"),
            ("gemini-1.5-pro-latest", "Direct Gemini 1.5 Pro"),
            ("gemini-2.0-flash-exp", "Direct Gemini 2.0 Flash Experimental"),
            ("gemini-2.5-flash-preview-04-17", "Direct Gemini 2.5 Flash Preview"),
            ("gemini-2.5-pro-preview-05-06", "Direct Gemini 2.5 Pro Preview"),
            ("gemini-exp-1206", "Direct Gemini Experimental 1206")
        ]
        
        print("🔍 Model Rate Limit Debug")
        print("=" * 40)
        
        for model, description in test_models:
            print(f"\n🧪 Testing {description} ({model})...")
            await asyncio.sleep(2.0)  # Generous delay between tests
            
            payload = {
                "model": model,
                "max_tokens": 10,  # Minimal tokens to reduce quota usage
                "messages": [{"role": "user", "content": "hi"}]
            }
            
            start_time = time.time()
            try:
                async with self.session.post(
                    f"{self.base_url}/v1/messages",
                    json=payload
                ) as response:
                    duration = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        actual_model = data.get('model', 'unknown')
                        content = data.get('content', [])
                        text = content[0].get('text', '') if content else ''
                        print(f"  ✅ SUCCESS: {model} → {actual_model}")
                        print(f"     Response: '{text[:30]}{'...' if len(text) > 30 else ''}'")
                    else:
                        error_text = await response.text()
                        status_emoji = "🚫" if response.status == 500 else "❌"
                        print(f"  {status_emoji} FAILED ({response.status}): {error_text[:100]}...")
                        
            except Exception as e:
                duration = time.time() - start_time
                print(f"  💥 ERROR: {str(e)[:100]}")
    
    def print_summary(self):
        """Print test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["status"] == "PASS")
        skipped_tests = sum(1 for result in self.test_results if result["status"] == "SKIP")
        failed_tests = sum(1 for result in self.test_results if result["status"] == "FAIL")
        
        print(f"\n{'='*50}")
        print(f"TEST SUMMARY")
        print(f"{'='*50}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: \033[92m{passed_tests}\033[0m")
        if skipped_tests > 0:
            print(f"Skipped: \033[93m{skipped_tests}\033[0m")
        print(f"Failed: \033[91m{failed_tests}\033[0m")
        
        # Calculate success rate treating skipped as success
        success_rate = ((passed_tests + skipped_tests) / total_tests) * 100 if total_tests > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\nFailed Tests:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['details']}")
        
        if skipped_tests > 0:
            print(f"\nSkipped Tests:")
            for result in self.test_results:
                if result["status"] == "SKIP":
                    print(f"  - {result['test']}: {result['details']}")
        
        return failed_tests == 0


async def main():
    parser = argparse.ArgumentParser(description="Test the Claude Code Multi-Provider Proxy")
    parser.add_argument("--url", help="Base URL of the proxy server (defaults to config)")
    parser.add_argument("--quick", action="store_true", help="Run only basic health checks")
    parser.add_argument("--minimal-api", action="store_true", help="Run minimal API tests to avoid rate limits")
    parser.add_argument("--model-mapping-only", action="store_true", help="Test only model mapping in isolation")
    parser.add_argument("--debug-models", action="store_true", help="Test different model combinations to debug rate limits")
    args = parser.parse_args()
    
    async with ProxyTester(args.url) as tester:
        print("🧪 Testing Gemini-to-Claude API Proxy")
        print(f"🔗 Target: {tester.base_url}")
        print("=" * 50)
        # Always run basic tests
        await tester.test_health_endpoint()
        await tester.test_root_endpoint()
        
        if args.quick:
            print("⚡ Quick mode - skipping API tests")
        elif args.minimal_api:
            print("🔥 Minimal API mode - testing connectivity only")
            await asyncio.sleep(1.0)
            await tester.test_connection_endpoint()
        elif args.model_mapping_only:
            print("🎯 Testing model mapping in isolation...")
            await asyncio.sleep(2.0)  # Wait longer to ensure no rate limits
            await tester.test_model_mapping()
        elif args.debug_models:
            await tester.debug_model_limits()
            return  # Don't run the normal summary for debug mode
        else:
            # Run comprehensive tests with delays to avoid rate limits
            print("⏳ Running API tests with rate limit protection...")
            
            await tester.test_connection_endpoint()
            await asyncio.sleep(1.0)  # Longer delay between API calls
            
            await tester.test_token_count_endpoint()
            await asyncio.sleep(1.0)
            
            # Choose between simple message OR streaming (not both) to reduce API calls
            print("🔀 Testing message completion (simple)...")
            await tester.test_simple_message()
            await asyncio.sleep(1.0)
            
            # Skip model mapping if we've already hit rate limits
            print("🔀 Testing model mapping...")
            await tester.test_model_mapping()
        
        # Print summary
        success = tester.print_summary()
        
        if success:
            print(f"\n✅ All tests passed!")
            sys.exit(0)
        else:
            print(f"\n❌ Some tests failed!")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())