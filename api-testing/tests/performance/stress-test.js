/**
 * k6 Stress Test for Gravitee APIM Gateway
 * Tests API behavior under extreme load conditions
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');

// Configuration
const GATEWAY_URL = __ENV.K6_GATEWAY_URL || 'https://api.example.com';
const API_KEY = __ENV.K6_API_KEY || '';

// Stress test configuration
export const options = {
    stages: [
        { duration: '2m', target: 100 },   // Ramp up to 100 users
        { duration: '5m', target: 100 },   // Stay at 100 users
        { duration: '2m', target: 200 },   // Ramp up to 200 users
        { duration: '5m', target: 200 },   // Stay at 200 users
        { duration: '2m', target: 300 },   // Ramp up to 300 users
        { duration: '5m', target: 300 },   // Stay at 300 users
        { duration: '2m', target: 400 },   // Ramp up to 400 users (stress point)
        { duration: '5m', target: 400 },   // Stay at 400 users
        { duration: '5m', target: 0 },     // Ramp down
    ],
    
    thresholds: {
        // More lenient thresholds for stress testing
        http_req_duration: ['p(95)<2000'],  // 95% below 2 seconds
        errors: ['rate<0.1'],               // Allow up to 10% errors under stress
        http_req_failed: ['rate<0.1'],      // Allow up to 10% failures
    },
    
    tags: {
        testType: 'stress',
    },
};

const headers = {
    'Content-Type': 'application/json',
    'X-Gravitee-Api-Key': API_KEY,
};

export default function() {
    // Focus on high-traffic endpoints
    const endpoints = [
        { method: 'GET', url: '/api/v1/users', weight: 30 },
        { method: 'GET', url: '/api/v1/products', weight: 40 },
        { method: 'GET', url: '/api/v1/orders', weight: 20 },
        { method: 'POST', url: '/api/v1/orders', weight: 10 },
    ];
    
    // Weighted random selection
    const totalWeight = endpoints.reduce((sum, e) => sum + e.weight, 0);
    let random = Math.random() * totalWeight;
    let selectedEndpoint = endpoints[0];
    
    for (const endpoint of endpoints) {
        random -= endpoint.weight;
        if (random <= 0) {
            selectedEndpoint = endpoint;
            break;
        }
    }
    
    let response;
    
    if (selectedEndpoint.method === 'GET') {
        response = http.get(`${GATEWAY_URL}${selectedEndpoint.url}`, { headers });
    } else {
        const payload = JSON.stringify({
            customerId: 'stress-test-customer',
            items: [{ productId: 'prod-1', quantity: 1 }]
        });
        response = http.post(`${GATEWAY_URL}${selectedEndpoint.url}`, payload, { headers });
    }
    
    // Check response
    const success = check(response, {
        'status is success': (r) => r.status >= 200 && r.status < 400,
        'response time < 2s': (r) => r.timings.duration < 2000,
    });
    
    errorRate.add(!success);
    apiLatency.add(response.timings.duration);
    
    // Minimal sleep to maximize load
    sleep(0.1);
}

export function handleSummary(data) {
    return {
        'reports/k6-stress-summary.json': JSON.stringify(data),
        stdout: generateStressSummary(data),
    };
}

function generateStressSummary(data) {
    const { metrics } = data;
    
    let summary = '\n=== Stress Test Summary ===\n\n';
    
    summary += `Peak VUs: ${data.metrics.vus_max.values.value}\n`;
    summary += `Total Requests: ${metrics.http_reqs.values.count}\n`;
    summary += `Error Rate: ${(metrics.errors.values.rate * 100).toFixed(2)}%\n\n`;
    
    summary += `Response Time (p50): ${metrics.http_req_duration.values['p(50)'].toFixed(2)}ms\n`;
    summary += `Response Time (p95): ${metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
    summary += `Response Time (p99): ${metrics.http_req_duration.values['p(99)'].toFixed(2)}ms\n`;
    summary += `Response Time (max): ${metrics.http_req_duration.values.max.toFixed(2)}ms\n\n`;
    
    // Breaking point analysis
    if (metrics.errors.values.rate > 0.05) {
        summary += '⚠️  WARNING: Error rate exceeded 5% - system may be at capacity\n';
    }
    
    if (metrics.http_req_duration.values['p(95)'] > 1000) {
        summary += '⚠️  WARNING: p95 latency exceeded 1 second - performance degradation detected\n';
    }
    
    return summary;
}

