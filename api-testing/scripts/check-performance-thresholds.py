#!/usr/bin/env python3
"""
Check k6 performance test results against thresholds
"""

import json
import sys

# Thresholds
THRESHOLDS = {
    "p50_latency_ms": 200,
    "p95_latency_ms": 500,
    "p99_latency_ms": 1000,
    "error_rate_percent": 1.0,
    "min_rps": 100
}


def check_thresholds(summary_file: str) -> bool:
    with open(summary_file, 'r') as f:
        data = json.load(f)
    
    metrics = data.get('metrics', {})
    passed = True
    
    # Check latency
    duration = metrics.get('http_req_duration', {}).get('values', {})
    
    p50 = duration.get('p(50)', 0)
    if p50 > THRESHOLDS['p50_latency_ms']:
        print(f"❌ p50 latency {p50:.2f}ms exceeds {THRESHOLDS['p50_latency_ms']}ms")
        passed = False
    else:
        print(f"✅ p50 latency {p50:.2f}ms")
    
    p95 = duration.get('p(95)', 0)
    if p95 > THRESHOLDS['p95_latency_ms']:
        print(f"❌ p95 latency {p95:.2f}ms exceeds {THRESHOLDS['p95_latency_ms']}ms")
        passed = False
    else:
        print(f"✅ p95 latency {p95:.2f}ms")
    
    # Check error rate
    errors = metrics.get('errors', {}).get('values', {})
    error_rate = errors.get('rate', 0) * 100
    
    if error_rate > THRESHOLDS['error_rate_percent']:
        print(f"❌ Error rate {error_rate:.2f}% exceeds {THRESHOLDS['error_rate_percent']}%")
        passed = False
    else:
        print(f"✅ Error rate {error_rate:.2f}%")
    
    return passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: check-performance-thresholds.py <k6-summary.json>")
        sys.exit(1)
    
    if not check_thresholds(sys.argv[1]):
        print("\n❌ Performance thresholds not met")
        sys.exit(1)
    
    print("\n✅ All performance thresholds passed")

