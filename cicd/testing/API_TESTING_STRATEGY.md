# API Testing Strategy - DEV to UAT

This document defines the comprehensive API testing strategy for the CI/CD pipeline, covering all testing phases from development through UAT.

## Testing Pyramid

```
                    ┌─────────────┐
                    │   E2E/UAT   │  ← Fewer, slower, comprehensive
                    │    Tests    │
                    └──────┬──────┘
                           │
                ┌──────────┴──────────┐
                │   Integration       │  ← API-level testing
                │      Tests          │
                └──────────┬──────────┘
                           │
          ┌────────────────┴────────────────┐
          │        Contract Tests           │  ← Schema compliance
          │    (OpenAPI Validation)         │
          └────────────────┬────────────────┘
                           │
    ┌──────────────────────┴──────────────────────┐
    │              Unit Tests                      │  ← Policy logic
    │         (Policy Validation)                  │
    └──────────────────────────────────────────────┘
                    Most, fastest
```

## Test Phases by Environment

| Phase | Environment | Tests | Gate Type | Tools |
|-------|-------------|-------|-----------|-------|
| **PR Validation** | None | Schema, Lint, Security | Required | kubeconform, yamllint, checkov |
| **DEV Deploy** | DEV | Unit, Contract | Required | Jest, Spectral |
| **DEV Smoke** | DEV | Smoke Tests | Required | Newman/Postman |
| **DEV Integration** | DEV | Integration | Required | Newman/Postman |
| **UAT Deploy** | UAT | Contract, Integration | Required | Newman/Postman |
| **UAT E2E** | UAT | End-to-End | Required | Newman/Postman |
| **UAT Performance** | UAT | Load, Stress | Advisory | k6 |
| **UAT Security** | UAT | OWASP Scan | Required | ZAP |

## Test Categories

### 1. Schema Validation (PR Phase)
- Validates YAML syntax
- Validates against GKO CRD schemas
- Checks for required fields
- Validates Kustomize builds

### 2. Contract Tests (DEV Phase)
- OpenAPI specification compliance
- Request/Response schema validation
- Breaking change detection
- API versioning compliance

### 3. Integration Tests (DEV/UAT Phase)
- API endpoint availability
- Authentication flows
- Authorization checks
- Error handling
- Rate limiting behavior

### 4. E2E Tests (UAT Phase)
- Complete user journeys
- Cross-API workflows
- Data consistency
- Session management

### 5. Performance Tests (UAT Phase)
- Response time benchmarks
- Throughput testing
- Concurrent user simulation
- Resource utilization

### 6. Security Tests (UAT Phase)
- OWASP Top 10 checks
- Authentication bypass attempts
- Injection testing
- Security header validation

## Quality Gates

### PR Gate (Required for Merge)
```yaml
checks:
  - yaml_lint: pass
  - schema_validation: pass
  - security_scan: no_high_severity
  - code_review: approved
```

### DEV Gate (Required for UAT Promotion)
```yaml
checks:
  - smoke_tests: 100% pass
  - contract_tests: 100% pass
  - integration_tests: 95% pass
  - api_available: true
```

### UAT Gate (Required for PROD Promotion)
```yaml
checks:
  - e2e_tests: 100% pass
  - performance_tests:
      p95_latency: < 500ms
      error_rate: < 1%
  - security_scan: no_critical
  - manual_approval: required
```

