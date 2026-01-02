/**
 * Quick k6 Load Test for Deployed Petstore API
 * Run: k6 run quick-load-test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');

const GATEWAY_URL = __ENV.GATEWAY_URL || 'http://localhost:8082';

export const options = {
    // Quick test: 30 seconds
    stages: [
        { duration: '10s', target: 10 },  // Ramp up to 10 users
        { duration: '15s', target: 10 },  // Stay at 10 users
        { duration: '5s', target: 0 },    // Ramp down
    ],
    
    thresholds: {
        http_req_duration: ['p(95)<2000'],  // 95% requests under 2s
        errors: ['rate<0.1'],                // Error rate under 10%
    },
};

export default function () {
    // Test 1: Find pets by status
    const findPetsRes = http.get(`${GATEWAY_URL}/petstore-gitops/v3/pet/findByStatus?status=available`);
    
    check(findPetsRes, {
        'Find Pets: status 200': (r) => r.status === 200,
        'Find Pets: response time < 2s': (r) => r.timings.duration < 2000,
        'Find Pets: has data': (r) => r.body.length > 0,
    });
    
    errorRate.add(findPetsRes.status !== 200);
    apiLatency.add(findPetsRes.timings.duration);
    
    sleep(0.5);
    
    // Test 2: Get pet by ID
    const getPetRes = http.get(`${GATEWAY_URL}/petstore-gitops/v3/pet/1`);
    
    check(getPetRes, {
        'Get Pet: status 200 or 404': (r) => r.status === 200 || r.status === 404,
        'Get Pet: response time < 1s': (r) => r.timings.duration < 1000,
    });
    
    errorRate.add(getPetRes.status !== 200 && getPetRes.status !== 404);
    apiLatency.add(getPetRes.timings.duration);
    
    sleep(0.5);
    
    // Test 3: HTTPBin via test-gko
    const httpbinRes = http.get(`${GATEWAY_URL}/test-gko`);
    
    check(httpbinRes, {
        'HTTPBin: status 200': (r) => r.status === 200,
        'HTTPBin: response time < 2s': (r) => r.timings.duration < 2000,
    });
    
    errorRate.add(httpbinRes.status !== 200);
    apiLatency.add(httpbinRes.timings.duration);
    
    sleep(1);
}

export function handleSummary(data) {
    console.log('\n========== LOAD TEST SUMMARY ==========');
    console.log(`Total Requests: ${data.metrics.http_reqs.values.count}`);
    console.log(`Failed Requests: ${data.metrics.http_req_failed.values.passes}`);
    console.log(`Avg Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
    console.log(`P95 Response Time: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
    console.log(`Error Rate: ${(data.metrics.errors.values.rate * 100).toFixed(2)}%`);
    console.log('========================================\n');
    
    return {
        stdout: JSON.stringify(data, null, 2),
    };
}

