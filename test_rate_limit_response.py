#!/usr/bin/env python3
"""
Test to verify that rate limit errors (vs quota exhaustion) return HTTP 500.
"""

import sys
import os
from unittest.mock import Mock

# Add the current directory to the path so we can import from server.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set a dummy API key to avoid config errors when importing
os.environ['GEMINI_API_KEY'] = 'test-key-for-import'

try:
    from server import handle_quota_rate_limit_error
except ImportError as e:
    print(f"❌ Could not import functions from server.py: {e}")
    sys.exit(1)

def test_rate_limit_vs_quota_exhaustion():
    """Test that rate limits return 500 and quota exhaustion returns 400."""
    
    # Mock request and config objects
    mock_request = Mock()
    mock_request.model = 'gemini-1.5-flash'
    mock_request.original_model = 'claude-3-sonnet-20240229'
    
    mock_config = Mock()
    mock_config.big_model = 'gemini-1.5-flash'
    mock_config.small_model = 'gemini-1.5-flash-latest'
    
    print("🧪 Testing Rate Limit vs Quota Exhaustion HTTP Status Codes")
    print("=" * 60)
    
    # Test 1: Quota exhaustion (should return 400)
    print("\n1️⃣ Testing quota exhaustion (daily limit)...")
    quota_error = Exception('''litellm.RateLimitError: VertexAIException - b'{
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details.",
    "status": "RESOURCE_EXHAUSTED",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
        "violations": [
          {
            "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
            "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
            "quotaValue": "50"
          }
        ]
      }
    ]
  }
}'
    ''')
    
    http_exc = handle_quota_rate_limit_error(quota_error, mock_request, mock_config)
    print(f"   Status Code: {http_exc.status_code}")
    print(f"   Detail: {http_exc.detail[:80]}...")
    assert http_exc.status_code == 400, f"Expected 400 for quota exhaustion, got {http_exc.status_code}"
    print("   ✅ Correctly returns HTTP 400 (Claude Code will stop with message)")
    
    # Test 2: Rate limit (should return 500)
    print("\n2️⃣ Testing rate limit (per-minute limit)...")
    rate_limit_error = Exception('''litellm.RateLimitError: VertexAIException - b'{
  "error": {
    "code": 429,
    "message": "Rate limit exceeded. Please slow down your requests.",
    "status": "RESOURCE_EXHAUSTED", 
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
        "violations": [
          {
            "quotaMetric": "generativelanguage.googleapis.com/generate_content_requests_per_minute",
            "quotaId": "RequestsPerMinute",
            "quotaValue": "60"
          }
        ]
      },
      {
        "@type": "type.googleapis.com/google.rpc.RetryInfo",
        "retryDelay": "5s"
      }
    ]
  }
}'
    ''')
    
    http_exc = handle_quota_rate_limit_error(rate_limit_error, mock_request, mock_config)
    print(f"   Status Code: {http_exc.status_code}")
    print(f"   Detail: {http_exc.detail[:80]}...")
    assert http_exc.status_code == 500, f"Expected 500 for rate limit, got {http_exc.status_code}"
    print("   ✅ Correctly returns HTTP 500 (Claude Code will retry)")
    
    # Test 3: Another rate limit metric (tokens per minute)
    print("\n3️⃣ Testing token rate limit (per-minute token limit)...")
    token_rate_limit_error = Exception('''litellm.RateLimitError: VertexAIException - b'{
  "error": {
    "code": 429,
    "message": "Token rate limit exceeded.",
    "status": "RESOURCE_EXHAUSTED",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.QuotaFailure", 
        "violations": [
          {
            "quotaMetric": "generativelanguage.googleapis.com/generate_tokens_per_minute",
            "quotaId": "TokensPerMinute",
            "quotaValue": "100000"
          }
        ]
      }
    ]
  }
}'
    ''')
    
    http_exc = handle_quota_rate_limit_error(token_rate_limit_error, mock_request, mock_config)
    print(f"   Status Code: {http_exc.status_code}")
    print(f"   Detail: {http_exc.detail[:80]}...")
    assert http_exc.status_code == 500, f"Expected 500 for token rate limit, got {http_exc.status_code}"
    print("   ✅ Correctly returns HTTP 500 (Claude Code will retry)")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("\n📋 Summary:")
    print("   • Quota exhaustion (daily/free-tier limits) → HTTP 400 → Claude stops")
    print("   • Rate limits (per-minute limits) → HTTP 500 → Claude retries")
    print("   • Our logic correctly distinguishes between the two types")

if __name__ == "__main__":
    test_rate_limit_vs_quota_exhaustion()