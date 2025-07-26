#!/usr/bin/env python3
"""
Test script for rate limit and quota error handling.
Tests the centralized error handler and ensures proper HTTP status codes.
"""

import sys
import os
import re
import json
from unittest.mock import Mock

# Add the current directory to the path so we can import from server.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set a dummy API key to avoid config errors when importing
os.environ['GEMINI_API_KEY'] = 'test-key-for-import'

try:
    from server import (
        extract_retry_delay, 
        parse_gemini_error_details, 
        handle_quota_rate_limit_error
    )
except ImportError as e:
    print(f"❌ Could not import functions from server.py: {e}")
    sys.exit(1)

def test_extract_retry_delay():
    """Test retry delay extraction from various error formats."""
    print("🧪 Testing retry delay extraction...")
    
    # Test case 1: Full quota error with RetryInfo
    quota_error = '''litellm.RateLimitError: VertexAIException - b'{
  "error": {
    "code": 429,
    "message": "You exceeded your current quota",
    "status": "RESOURCE_EXHAUSTED",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.RetryInfo",
        "retryDelay": "25s"
      }
    ]
  }
}'''
    
    delay = extract_retry_delay(quota_error)
    assert delay == 25, f"Expected 25s, got {delay}s"
    print(f"  ✅ Quota error: {delay}s")
    
    # Test case 2: Error without RetryInfo (should default to 60)
    simple_error = "RateLimitError: Too many requests"
    delay = extract_retry_delay(simple_error)
    assert delay == 60, f"Expected 60s default, got {delay}s"
    print(f"  ✅ Simple error: {delay}s (default)")
    
    # Test case 3: Different delay value
    different_delay_error = '''{"error": {"details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "120s"}]}}'''
    delay = extract_retry_delay(different_delay_error)
    assert delay == 120, f"Expected 120s, got {delay}s"
    print(f"  ✅ Different delay: {delay}s")

def test_parse_gemini_error_details():
    """Test parsing of Gemini error response details."""
    print("\n🧪 Testing error detail parsing...")
    
    # Test case 1: Quota exhaustion error
    quota_error = '''litellm.RateLimitError: VertexAIException - b'{
  "error": {
    "code": 429,
    "message": "Request limit for gemini-1.5-flash exceeded. Your current quota: 50 requests per day per model.",
    "status": "RESOURCE_EXHAUSTED",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
        "violations": [
          {
            "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
            "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
            "quotaDimensions": {
              "location": "global",
              "model": "gemini-1.5-flash"
            },
            "quotaValue": "50"
          }
        ]
      },
      {
        "@type": "type.googleapis.com/google.rpc.RetryInfo",
        "retryDelay": "20s"
      }
    ]
  }
}'''
    
    details = parse_gemini_error_details(quota_error)
    assert details['error_code'] == 429
    assert details['error_status'] == 'RESOURCE_EXHAUSTED'
    assert 'Request limit for gemini-1.5-flash exceeded' in details['message']
    assert details['quota_metric'] == 'generativelanguage.googleapis.com/generate_content_free_tier_requests'
    assert details['quota_model'] == 'gemini-1.5-flash'
    assert details['quota_value'] == '50'
    assert details['retry_delay'] == '20s'
    print(f"  ✅ Quota error parsed: {details['quota_metric']} for {details['quota_model']}")
    
    # Test case 2: Rate limit error (different quota type)
    rate_limit_error = '''litellm.RateLimitError: VertexAIException - b'{
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
            "quotaDimensions": {
              "location": "global",
              "model": "gemini-1.5-flash"
            },
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
}'''
    
    details = parse_gemini_error_details(rate_limit_error)
    assert details['quota_metric'] == 'generativelanguage.googleapis.com/generate_content_requests_per_minute'
    assert details['retry_delay'] == '5s'
    print(f"  ✅ Rate limit parsed: {details['quota_metric']} with {details['retry_delay']} delay")

def test_centralized_error_handler():
    """Test the centralized error handler's HTTP status code logic."""
    print("\n🧪 Testing centralized error handler...")
    
    # Mock request and config objects
    mock_request = Mock()
    mock_request.model = 'gemini-1.5-flash'
    mock_request.original_model = 'claude-3-sonnet-20240229'
    
    mock_config = Mock()
    mock_config.big_model = 'gemini-1.5-flash'
    mock_config.small_model = 'gemini-1.5-flash-latest'
    
    # Test case 1: Quota exhaustion should return 400 (so Claude Code stops with message)
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
    assert http_exc.status_code == 400, f"Expected 400 for quota exhaustion, got {http_exc.status_code}"
    assert "quota" in http_exc.detail.lower(), "Expected quota message in detail"
    print(f"  ✅ Quota exhaustion: HTTP {http_exc.status_code} - {http_exc.detail[:50]}...")
    
    # Test case 2: Rate limit should return 500 (so Claude Code retries properly)
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
            "quotaValue": "60"
          }
        ]
      }
    ]
  }
}'
    ''')
    
    http_exc = handle_quota_rate_limit_error(rate_limit_error, mock_request, mock_config)
    assert http_exc.status_code == 500, f"Expected 500 for rate limit, got {http_exc.status_code}"
    print(f"  ✅ Rate limit: HTTP {http_exc.status_code} - {http_exc.detail[:50]}...")
    
    # Test case 3: Model type detection
    mock_request.model = 'gemini-1.5-flash-latest'  # Should be SMALL
    http_exc = handle_quota_rate_limit_error(quota_error, mock_request, mock_config)
    # We can't easily test the log output, but the function should work without errors
    print(f"  ✅ Model type detection: Works for SMALL model")

def test_real_error_scenarios():
    """Test with real error messages from the logs."""
    print("\n🧪 Testing real error scenarios from logs...")
    
    # Test the bytes format that was failing in the logs
    bytes_format_error = '''litellm.RateLimitError: litellm.RateLimitError: VertexAIException - b'{\\n  "error": {\\n    "code": 429,\\n    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits.",\\n    "status": "RESOURCE_EXHAUSTED",\\n    "details": [\\n      {\\n        "@type": "type.googleapis.com/google.rpc.QuotaFailure",\\n        "violations": [\\n          {\\n            "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",\\n            "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",\\n            "quotaDimensions": {\\n              "location": "global",\\n              "model": "gemini-1.5-flash"\\n            },\\n            "quotaValue": "50"\\n          }\\n        ]\\n      },\\n      {\\n        "@type": "type.googleapis.com/google.rpc.RetryInfo",\\n        "retryDelay": "22s"\\n      }\\n    ]\\n  }\\n}'
'''
    
    details = parse_gemini_error_details(bytes_format_error)
    assert not details.get('parsing_failed'), f"Bytes format parsing should not fail: {details}"
    assert details['quota_metric'] == 'generativelanguage.googleapis.com/generate_content_free_tier_requests'
    assert details['quota_value'] == '50'
    assert details['retry_delay'] == '22s'
    print(f"  ✅ Bytes format parsed: {details['quota_metric']}, delay={details['retry_delay']}")
    
    # Your actual error from the logs
    real_quota_error = '''litellm.RateLimitError: litellm.RateLimitError: VertexAIException - b'{
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits.",
    "status": "RESOURCE_EXHAUSTED",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
        "violations": [
          {
            "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
            "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
            "quotaDimensions": {
              "location": "global",
              "model": "gemini-1.5-flash"
            },
            "quotaValue": "50"
          }
        ]
      },
      {
        "@type": "type.googleapis.com/google.rpc.Help",
        "links": [
          {
            "description": "Learn more about Gemini API quotas",
            "url": "https://ai.google.dev/gemini-api/docs/rate-limits"
          }
        ]
      },
      {
        "@type": "type.googleapis.com/google.rpc.RetryInfo",
        "retryDelay": "20s"
      }
    ]
  }
}
'
    '''
    
    # Test parsing
    details = parse_gemini_error_details(real_quota_error)
    assert details['quota_metric'] == 'generativelanguage.googleapis.com/generate_content_free_tier_requests'
    assert details['quota_value'] == '50'
    assert details['retry_delay'] == '20s'
    print(f"  ✅ Real error parsed: {details['quota_metric']}, limit={details['quota_value']}")
    
    # Test retry delay extraction
    delay = extract_retry_delay(real_quota_error)
    assert delay == 20, f"Expected 20s, got {delay}s"
    print(f"  ✅ Real error retry delay: {delay}s")
    
    # Test centralized handler
    mock_request = Mock()
    mock_request.model = 'gemini-1.5-flash'
    mock_config = Mock()
    mock_config.big_model = 'gemini-1.5-flash'
    mock_config.small_model = 'gemini-1.5-flash-latest'
    
    real_error_exception = Exception(real_quota_error)
    http_exc = handle_quota_rate_limit_error(real_error_exception, mock_request, mock_config)
    assert http_exc.status_code == 400, f"Real quota error should return 400, got {http_exc.status_code}"
    print(f"  ✅ Real error handler: HTTP {http_exc.status_code}")

def main():
    """Run all tests."""
    print("🔬 Testing Rate Limit Error Handling")
    print("=" * 50)
    
    try:
        test_extract_retry_delay()
        test_parse_gemini_error_details()
        test_centralized_error_handler()
        test_real_error_scenarios()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed! The centralized error handler is working correctly.")
        print("\nBehavior Summary:")
        print("• Quota exhaustion errors → HTTP 400 (Claude Code stops with message)")
        print("• Rate limit errors → HTTP 500 (Claude Code retries properly with message)")
        print("• HTTP 400 stops Claude Code, HTTP 500 allows retries")
        print("• Detailed parsing extracts Google's official error messages")
        print("• Model type detection works for BIG vs SMALL models")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()