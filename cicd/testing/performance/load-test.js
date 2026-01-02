/**
 * k6 Load Test for Gravitee APIs
 * Run with: k6 run load-test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');
const successfulRequests = new Counter('successful_requests');

// Test configuration
export const options = {
  // Load test stages
  stages: [
    { duration: '1m', target: 10 },   // Ramp up to 10 users
    { duration: '3m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Ramp up to 100 users
    { duration: '3m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down
  ],
  
  // Thresholds (quality gates)
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],  // 95% < 500ms, 99% < 1s
    http_req_failed: ['rate<0.01'],                   // Error rate < 1%
    errors: ['rate<0.05'],                            // Custom error rate < 5%
    api_latency: ['p(95)<400'],                       // API latency p95 < 400ms
  },
  
  // Tags for filtering results
  tags: {
    environment: __ENV.ENVIRONMENT || 'dev',
    api: 'petstore',
  },
};

// Environment configuration
const BASE_URL = __ENV.GATEWAY_URL || 'http://localhost:8082';
const API_PATH = __ENV.API_PATH || '/petstore/v3';
const KEYCLOAK_URL = __ENV.KEYCLOAK_URL || 'http://localhost:8180';
const CLIENT_ID = __ENV.CLIENT_ID || 'api-client';
const CLIENT_SECRET = __ENV.CLIENT_SECRET || 'api-client-secret';

let accessToken = '';

// Setup - get authentication token
export function setup() {
  const tokenResponse = http.post(
    `${KEYCLOAK_URL}/realms/gravitee/protocol/openid-connect/token`,
    {
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      grant_type: 'client_credentials',
    },
    {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }
  );
  
  if (tokenResponse.status === 200) {
    const body = JSON.parse(tokenResponse.body);
    return { token: body.access_token };
  }
  
  console.error('Failed to get token:', tokenResponse.status);
  return { token: '' };
}

// Main test function
export default function(data) {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${data.token}`,
  };
  
  group('GET Requests', function() {
    // Get single pet
    const getPetResponse = http.get(`${BASE_URL}${API_PATH}/pet/1`, { headers });
    
    const getPetSuccess = check(getPetResponse, {
      'GET pet status is 200': (r) => r.status === 200,
      'GET pet response time < 500ms': (r) => r.timings.duration < 500,
      'GET pet has id': (r) => JSON.parse(r.body).id !== undefined,
    });
    
    errorRate.add(!getPetSuccess);
    apiLatency.add(getPetResponse.timings.duration);
    if (getPetSuccess) successfulRequests.add(1);
    
    sleep(0.5);
    
    // Get pets by status
    const findPetsResponse = http.get(
      `${BASE_URL}${API_PATH}/pet/findByStatus?status=available`,
      { headers }
    );
    
    const findPetsSuccess = check(findPetsResponse, {
      'Find pets status is 200': (r) => r.status === 200,
      'Find pets response time < 1000ms': (r) => r.timings.duration < 1000,
      'Find pets returns array': (r) => Array.isArray(JSON.parse(r.body)),
    });
    
    errorRate.add(!findPetsSuccess);
    apiLatency.add(findPetsResponse.timings.duration);
    if (findPetsSuccess) successfulRequests.add(1);
  });
  
  group('POST Requests', function() {
    const newPet = {
      id: Math.floor(Math.random() * 1000000),
      name: `LoadTestPet_${Date.now()}`,
      category: { id: 1, name: 'Dogs' },
      photoUrls: ['string'],
      status: 'available',
    };
    
    const createPetResponse = http.post(
      `${BASE_URL}${API_PATH}/pet`,
      JSON.stringify(newPet),
      { headers }
    );
    
    const createPetSuccess = check(createPetResponse, {
      'POST pet status is 200': (r) => r.status === 200,
      'POST pet response time < 1000ms': (r) => r.timings.duration < 1000,
    });
    
    errorRate.add(!createPetSuccess);
    apiLatency.add(createPetResponse.timings.duration);
    if (createPetSuccess) successfulRequests.add(1);
  });
  
  group('Error Handling', function() {
    // Test 404
    const notFoundResponse = http.get(
      `${BASE_URL}${API_PATH}/pet/999999999`,
      { headers }
    );
    
    check(notFoundResponse, {
      '404 response handled': (r) => r.status === 404 || r.status === 200,
    });
  });
  
  sleep(1);
}

// Teardown
export function teardown(data) {
  console.log('Load test completed');
}

// Handle summary
export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'summary.json': JSON.stringify(data),
  };
}

function textSummary(data, options) {
  const lines = [];
  lines.push('\n========== Load Test Summary ==========\n');
  
  // Request metrics
  if (data.metrics.http_req_duration) {
    lines.push(`HTTP Request Duration:`);
    lines.push(`  avg: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
    lines.push(`  p95: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
    lines.push(`  p99: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms`);
  }
  
  // Error rate
  if (data.metrics.errors) {
    lines.push(`\nError Rate: ${(data.metrics.errors.values.rate * 100).toFixed(2)}%`);
  }
  
  // Throughput
  if (data.metrics.http_reqs) {
    lines.push(`\nTotal Requests: ${data.metrics.http_reqs.values.count}`);
    lines.push(`Requests/sec: ${data.metrics.http_reqs.values.rate.toFixed(2)}`);
  }
  
  // Thresholds
  lines.push('\n========== Threshold Results ==========');
  for (const [name, threshold] of Object.entries(data.thresholds || {})) {
    const status = threshold.ok ? '✓ PASS' : '✗ FAIL';
    lines.push(`${status}: ${name}`);
  }
  
  return lines.join('\n');
}

