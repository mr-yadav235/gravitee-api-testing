/**
 * k6 Load Test for Gravitee APIM Gateway
 * Tests API performance under normal load conditions
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');
const requestsPerEndpoint = new Counter('requests_per_endpoint');

// Configuration from environment
const GATEWAY_URL = __ENV.K6_GATEWAY_URL || 'https://api.example.com';
const API_KEY = __ENV.K6_API_KEY || '';

// Test configuration
export const options = {
    // Stages define the load pattern
    stages: [
        { duration: '1m', target: 20 },   // Ramp up to 20 users
        { duration: '3m', target: 20 },   // Stay at 20 users
        { duration: '1m', target: 50 },   // Ramp up to 50 users
        { duration: '3m', target: 50 },   // Stay at 50 users
        { duration: '1m', target: 100 },  // Ramp up to 100 users
        { duration: '3m', target: 100 },  // Stay at 100 users
        { duration: '2m', target: 0 },    // Ramp down
    ],
    
    // Thresholds define pass/fail criteria
    thresholds: {
        http_req_duration: [
            'p(50)<200',   // 50% of requests should be below 200ms
            'p(95)<500',   // 95% of requests should be below 500ms
            'p(99)<1000',  // 99% of requests should be below 1000ms
        ],
        errors: ['rate<0.01'],           // Error rate should be below 1%
        http_req_failed: ['rate<0.01'],  // Failed requests should be below 1%
        api_latency: ['p(95)<400'],      // Custom latency metric
    },
    
    // Tags for result organization
    tags: {
        testType: 'load',
    },
};

// Default headers
const headers = {
    'Content-Type': 'application/json',
    'X-Gravitee-Api-Key': API_KEY,
};

// Test scenarios
export default function() {
    // Users API tests
    group('Users API', () => {
        // GET /users - List users
        let response = http.get(`${GATEWAY_URL}/api/v1/users?page=1&limit=10`, { headers });
        
        check(response, {
            'GET /users status is 200': (r) => r.status === 200,
            'GET /users response time < 500ms': (r) => r.timings.duration < 500,
            'GET /users returns array': (r) => {
                try {
                    return Array.isArray(JSON.parse(r.body));
                } catch {
                    return false;
                }
            },
        });
        
        errorRate.add(response.status !== 200);
        apiLatency.add(response.timings.duration);
        requestsPerEndpoint.add(1, { endpoint: 'GET /users' });
        
        sleep(1);
        
        // GET /users/:id - Get single user
        response = http.get(`${GATEWAY_URL}/api/v1/users/user-123`, { headers });
        
        check(response, {
            'GET /users/:id status is 200 or 404': (r) => [200, 404].includes(r.status),
            'GET /users/:id response time < 300ms': (r) => r.timings.duration < 300,
        });
        
        errorRate.add(![200, 404].includes(response.status));
        apiLatency.add(response.timings.duration);
        requestsPerEndpoint.add(1, { endpoint: 'GET /users/:id' });
    });
    
    // Orders API tests
    group('Orders API', () => {
        // GET /orders - List orders
        let response = http.get(`${GATEWAY_URL}/api/v1/orders`, { headers });
        
        check(response, {
            'GET /orders status is 200': (r) => r.status === 200,
            'GET /orders response time < 500ms': (r) => r.timings.duration < 500,
        });
        
        errorRate.add(response.status !== 200);
        apiLatency.add(response.timings.duration);
        requestsPerEndpoint.add(1, { endpoint: 'GET /orders' });
        
        sleep(0.5);
        
        // POST /orders - Create order (less frequent)
        if (Math.random() < 0.1) {  // Only 10% of iterations
            const orderPayload = JSON.stringify({
                customerId: 'customer-' + Math.floor(Math.random() * 1000),
                items: [
                    { productId: 'prod-1', quantity: Math.floor(Math.random() * 5) + 1 },
                    { productId: 'prod-2', quantity: Math.floor(Math.random() * 3) + 1 }
                ]
            });
            
            response = http.post(`${GATEWAY_URL}/api/v1/orders`, orderPayload, { headers });
            
            check(response, {
                'POST /orders status is 201': (r) => r.status === 201,
                'POST /orders response time < 1000ms': (r) => r.timings.duration < 1000,
                'POST /orders returns orderId': (r) => {
                    try {
                        return JSON.parse(r.body).orderId !== undefined;
                    } catch {
                        return false;
                    }
                },
            });
            
            errorRate.add(response.status !== 201);
            apiLatency.add(response.timings.duration);
            requestsPerEndpoint.add(1, { endpoint: 'POST /orders' });
        }
    });
    
    // Products API tests (public, higher traffic)
    group('Products API', () => {
        // GET /products - List products (no auth required)
        let response = http.get(`${GATEWAY_URL}/api/v1/products`);
        
        check(response, {
            'GET /products status is 200': (r) => r.status === 200,
            'GET /products response time < 300ms': (r) => r.timings.duration < 300,
            'GET /products has cache header': (r) => r.headers['Cache-Control'] !== undefined,
        });
        
        errorRate.add(response.status !== 200);
        apiLatency.add(response.timings.duration);
        requestsPerEndpoint.add(1, { endpoint: 'GET /products' });
        
        sleep(0.3);
        
        // GET /products/:id - Get single product
        const productId = `prod-${Math.floor(Math.random() * 100) + 1}`;
        response = http.get(`${GATEWAY_URL}/api/v1/products/${productId}`);
        
        check(response, {
            'GET /products/:id status is 200 or 404': (r) => [200, 404].includes(r.status),
            'GET /products/:id response time < 200ms': (r) => r.timings.duration < 200,
        });
        
        errorRate.add(![200, 404].includes(response.status));
        apiLatency.add(response.timings.duration);
        requestsPerEndpoint.add(1, { endpoint: 'GET /products/:id' });
    });
    
    // Random sleep between iterations (1-3 seconds)
    sleep(Math.random() * 2 + 1);
}

// Setup function - runs once before the test
export function setup() {
    console.log(`Starting load test against: ${GATEWAY_URL}`);
    
    // Verify API is accessible
    const response = http.get(`${GATEWAY_URL}/api/v1/products`, { headers });
    
    if (response.status !== 200) {
        console.error(`API not accessible: ${response.status}`);
    }
    
    return { startTime: new Date().toISOString() };
}

// Teardown function - runs once after the test
export function teardown(data) {
    console.log(`Load test completed. Started at: ${data.startTime}`);
}

// Handle summary for custom reporting
export function handleSummary(data) {
    return {
        'reports/k6-summary.json': JSON.stringify(data),
        stdout: textSummary(data, { indent: ' ', enableColors: true }),
    };
}

// Text summary helper
function textSummary(data, options) {
    const { metrics } = data;
    
    let summary = '\n=== Load Test Summary ===\n\n';
    
    // Request metrics
    summary += `Total Requests: ${metrics.http_reqs.values.count}\n`;
    summary += `Failed Requests: ${metrics.http_req_failed.values.passes}\n`;
    summary += `Error Rate: ${(metrics.errors.values.rate * 100).toFixed(2)}%\n\n`;
    
    // Latency metrics
    summary += `Response Time (p50): ${metrics.http_req_duration.values['p(50)'].toFixed(2)}ms\n`;
    summary += `Response Time (p95): ${metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
    summary += `Response Time (p99): ${metrics.http_req_duration.values['p(99)'].toFixed(2)}ms\n\n`;
    
    // Throughput
    const duration = (data.state.testRunDurationMs / 1000).toFixed(2);
    const rps = (metrics.http_reqs.values.count / duration).toFixed(2);
    summary += `Throughput: ${rps} req/s\n`;
    summary += `Test Duration: ${duration}s\n`;
    
    return summary;
}

