# API Testing Strategy for Gravitee APIM

## Overview

This document outlines the comprehensive testing strategy for APIs published through Gravitee APIM Gateway. Testing occurs at multiple stages: post-deployment validation, continuous testing, and pre-release verification.

---

## Testing Pyramid

```
                    ┌─────────────────┐
                    │   E2E Tests     │  ← Business flows (few)
                   ┌┴─────────────────┴┐
                   │  Performance Tests │  ← Load, stress, soak
                  ┌┴───────────────────┴┐
                  │   Security Tests    │  ← OWASP, penetration
                 ┌┴─────────────────────┴┐
                 │   Contract Tests      │  ← API schema validation
                ┌┴───────────────────────┴┐
                │    Functional Tests     │  ← API behavior
               ┌┴─────────────────────────┴┐
               │      Smoke Tests          │  ← Quick health checks (many)
               └───────────────────────────┘
```

---

## Test Types & When They Run

| Test Type | Trigger | Environment | Duration | Blocking |
|-----------|---------|-------------|----------|----------|
| **Smoke Tests** | Post-deploy | All | < 1 min | Yes |
| **Functional Tests** | Post-deploy | All | 5-10 min | Yes |
| **Contract Tests** | Post-deploy | All | 2-5 min | Yes |
| **Security Tests** | Nightly / Pre-prod | UAT, Prod | 15-30 min | Yes (Prod) |
| **Performance Tests** | Weekly / Pre-prod | UAT | 30-60 min | Yes (Prod) |
| **E2E Tests** | Pre-release | UAT | 15-30 min | Yes |

---

## Testing Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Post-Deployment Testing Flow                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐          │
│   │  ArgoCD  │────▶│   GKO    │────▶│ Gravitee │────▶│  Tests   │          │
│   │   Sync   │     │  Syncs   │     │ Gateway  │     │  Start   │          │
│   └──────────┘     └──────────┘     └──────────┘     └────┬─────┘          │
│                                                           │                 │
│                         ┌─────────────────────────────────┼─────────────┐  │
│                         │                                 ▼             │  │
│                         │     ┌─────────────────────────────────┐      │  │
│                         │     │         Smoke Tests             │      │  │
│                         │     │    (Health, Auth, Basic Flow)   │      │  │
│                         │     └──────────────┬──────────────────┘      │  │
│                         │                    │ Pass?                    │  │
│                         │                    ▼                          │  │
│                         │     ┌─────────────────────────────────┐      │  │
│                         │     │       Functional Tests          │      │  │
│                         │     │   (CRUD, Policies, Transforms)  │      │  │
│                         │     └──────────────┬──────────────────┘      │  │
│                         │                    │ Pass?                    │  │
│                         │                    ▼                          │  │
│                         │     ┌─────────────────────────────────┐      │  │
│                         │     │        Contract Tests           │      │  │
│                         │     │    (OpenAPI, Schema, Pact)      │      │  │
│                         │     └──────────────┬──────────────────┘      │  │
│                         │                    │                          │  │
│                         │                    ▼                          │  │
│                         │            ┌──────────────┐                   │  │
│                         │            │   Results    │                   │  │
│                         │            │   Report     │                   │  │
│                         │            └──────────────┘                   │  │
│                         │                                               │  │
│                         └───────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Smoke Tests

Quick health checks to verify API is accessible and responding.

### What to Test
- API endpoint reachability
- Authentication mechanisms work
- Basic request/response flow
- Gateway policies are applied

### Tools
- Newman (Postman CLI)
- curl scripts
- k6 (quick checks)

### Example Checks
```yaml
smoke_tests:
  - name: Health Check
    endpoint: /api/v1/users/health
    expected_status: 200
    timeout: 5s
    
  - name: Auth Required
    endpoint: /api/v1/users
    headers: {}  # No auth
    expected_status: 401
    
  - name: Valid API Key
    endpoint: /api/v1/users
    headers:
      X-Gravitee-Api-Key: "{{API_KEY}}"
    expected_status: 200
```

---

## 2. Functional Tests

Verify API behavior matches specifications.

### What to Test
- All CRUD operations
- Query parameters and filtering
- Error handling and edge cases
- Rate limiting enforcement
- Request/response transformations
- Caching behavior

### Tools
- Newman (Postman CLI)
- pytest + requests
- REST Assured (Java)

---

## 3. Contract Tests

Ensure API responses match the defined schema.

### What to Test
- Response schema matches OpenAPI spec
- Required fields are present
- Data types are correct
- Consumer contracts (Pact)

### Tools
- Spectral (OpenAPI linting)
- Pact (consumer-driven contracts)
- Schemathesis (property-based testing)

---

## 4. Security Tests

Identify vulnerabilities and security misconfigurations.

### What to Test
- OWASP API Security Top 10
- Authentication bypass attempts
- Authorization checks (IDOR, privilege escalation)
- Injection attacks (SQL, NoSQL, command)
- Rate limiting bypass
- Security headers

### Tools
- OWASP ZAP
- Burp Suite
- Nuclei
- Custom Python scripts

---

## 5. Performance Tests

Verify API performance under various load conditions.

### Test Types
- **Load Test**: Normal expected load
- **Stress Test**: Beyond normal capacity
- **Soak Test**: Extended duration
- **Spike Test**: Sudden traffic bursts

### Metrics to Capture
- Response time (p50, p95, p99)
- Throughput (requests/second)
- Error rate
- Resource utilization

### Tools
- k6
- Gatling
- Apache JMeter

---

## 6. E2E Tests

Verify complete business flows across multiple APIs.

### What to Test
- User registration → Login → Profile update
- Product browse → Add to cart → Checkout
- Multi-API workflows

### Tools
- Playwright
- Cypress
- Custom test frameworks

---

## Test Configuration by Environment

| Environment | Smoke | Functional | Contract | Security | Performance | E2E |
|-------------|-------|------------|----------|----------|-------------|-----|
| **Dev** | ✅ | ✅ | ✅ | ⚠️ Weekly | ❌ | ❌ |
| **UAT** | ✅ | ✅ | ✅ | ✅ Nightly | ✅ Weekly | ✅ |
| **Prod** | ✅ | ✅ Limited | ✅ | ✅ Monthly | ❌ | ❌ |

---

## Success Criteria

### Smoke Tests
- 100% pass rate required
- Response time < 2 seconds
- All endpoints reachable

### Functional Tests
- 100% pass rate for critical paths
- 95% overall pass rate

### Contract Tests
- 100% schema compliance
- No breaking changes

### Security Tests
- Zero critical/high vulnerabilities
- All security headers present

### Performance Tests
- p95 response time < 500ms
- Error rate < 1%
- Throughput meets SLA

---

## Reporting & Notifications

### Test Reports
- HTML reports stored as artifacts
- JUnit XML for CI integration
- Allure reports for detailed analysis

### Notifications
- Slack: Test results summary
- Email: Detailed failure reports
- PagerDuty: Critical test failures in production

