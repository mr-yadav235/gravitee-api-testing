# Complete API Testing Guide

This comprehensive guide documents all testing phases, tools, commands, and workflows for testing Gravitee APIs from development through UAT.

---

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Testing Pipeline Flow](#testing-pipeline-flow)
3. [Pre-Deployment Validation](#pre-deployment-validation)
4. [Post-Deployment Testing](#post-deployment-testing)
5. [Test Types & Commands](#test-types--commands)
6. [Quality Gates](#quality-gates)
7. [CI/CD Integration](#cicd-integration)
8. [Troubleshooting](#troubleshooting)

---

## Testing Overview

### Testing Pyramid

```
                         ┌─────────────────┐
                         │   E2E / UAT     │  ← Fewer, slower, comprehensive
                         │     Tests       │
                         └────────┬────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │     Integration Tests     │  ← API-level testing
                    │    (Newman/Postman)       │
                    └─────────────┬─────────────┘
                                  │
              ┌───────────────────┴───────────────────┐
              │          Contract Tests               │  ← Schema compliance
              │     (OpenAPI/Spectral/Schemathesis)   │
              └───────────────────┬───────────────────┘
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │                   Unit Tests                       │  ← Policy logic
        │              (Jest/Policy Validation)              │
        └────────────────────────────────────────────────────┘
                           Most, fastest
```

### Test Phases by Environment

| Phase | Environment | Tests | Gate Type | Tools |
|-------|-------------|-------|-----------|-------|
| **PR Validation** | None | YAML Lint, Schema, Security | Required | yamllint, kubeconform, Trivy |
| **DEV Deploy** | DEV | Unit, Contract | Required | Jest, Spectral |
| **DEV Smoke** | DEV | Smoke Tests | Required | Newman/Postman |
| **DEV Integration** | DEV | Integration | Required | Newman/Postman |
| **UAT Deploy** | UAT | Contract, Integration | Required | Newman/Postman |
| **UAT E2E** | UAT | End-to-End | Required | Newman/Postman |
| **UAT Performance** | UAT | Load, Stress | Advisory | k6 |
| **UAT Security** | UAT | OWASP Scan | Required | ZAP |

---

## Testing Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COMPLETE TESTING FLOW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    PHASE 1: PR VALIDATION                            │    │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │    │
│  │  │ YAML     │→ │ CRD Schema   │→ │ OpenAPI      │→ │ Security    │  │    │
│  │  │ Lint     │  │ Validation   │  │ Validation   │  │ Scan        │  │    │
│  │  └──────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    PHASE 2: DEV DEPLOYMENT                           │    │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │    │
│  │  │ ArgoCD   │→ │ GKO Sync     │→ │ Smoke Tests  │→ │ Integration │  │    │
│  │  │ Sync     │  │ API Create   │  │ (Health)     │  │ Tests       │  │    │
│  │  └──────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    PHASE 3: UAT PROMOTION                            │    │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │    │
│  │  │ Promote  │→ │ E2E Tests    │→ │ Performance  │→ │ Security    │  │    │
│  │  │ to UAT   │  │ (Full Flow)  │  │ Tests (k6)   │  │ Scan (ZAP)  │  │    │
│  │  └──────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    PHASE 4: PROD PROMOTION                           │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐ │    │
│  │  │ Manual Approval  │→ │ Promote to Prod  │→ │ Smoke Tests Only   │ │    │
│  │  │ (Required)       │  │ (GitOps)         │  │ (Minimal Impact)   │ │    │
│  │  └──────────────────┘  └──────────────────┘  └────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Pre-Deployment Validation

### 1. YAML Lint

**Purpose:** Validate YAML syntax and formatting

**Workflow Location:** `.github/workflows/api-gitops-ci.yaml` (Lines 51-64)

**Command:**
```bash
# Install
pip install yamllint

# Run locally
yamllint -c .yamllint.yaml apis/ templates/

# Check specific file
yamllint apis/base/petstore-api/api-definition.yaml
```

**Configuration:** `.yamllint.yaml`
```yaml
extends: default
rules:
  line-length:
    max: 200
  document-start: disable
  truthy:
    check-keys: false
  comments-indentation: disable
```

---

### 2. CRD Schema Validation

**Purpose:** Validate Kubernetes CRDs against schemas

**Workflow Location:** `.github/workflows/api-gitops-ci.yaml` (Lines 69-125)

**Commands:**
```bash
# Install kubeconform
curl -L https://github.com/yannh/kubeconform/releases/download/v0.6.4/kubeconform-linux-amd64.tar.gz | tar xz
sudo mv kubeconform /usr/local/bin/

# Install kustomize
curl -L https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2Fv5.3.0/kustomize_v5.3.0_linux_amd64.tar.gz | tar xz
sudo mv kustomize /usr/local/bin/

# Build and validate for each environment
for ENV in dev uat prod; do
  echo "Validating $ENV environment..."
  kustomize build apis/overlays/$ENV > /tmp/manifests-$ENV.yaml
  
  kubeconform \
    -summary \
    -output json \
    -schema-location default \
    -skip ApiDefinition,ApiV4Definition,ApiPlan,ManagementContext,Application,Subscription \
    /tmp/manifests-$ENV.yaml
done
```

**Custom GKO CRD Validation:**
```bash
python3 scripts/validate-gko-crds.py /tmp/manifests-dev.yaml
```

---

### 3. OpenAPI Validation

**Purpose:** Validate OpenAPI specifications

**Workflow Location:** `.github/workflows/api-gitops-ci.yaml` (Lines 130-171)

**Commands:**
```bash
# Install validators
npm install -g @apidevtools/swagger-cli
npm install -g @stoplight/spectral-cli

# Validate OpenAPI spec
swagger-cli validate openapi.yaml

# Lint with Spectral
spectral lint openapi.yaml --ruleset .spectral.yaml
```

**Spectral Configuration:** `.spectral.yaml`
```yaml
extends: spectral:oas
rules:
  operation-operationId: error
  operation-tags: warn
  info-contact: warn
```

---

### 4. Security Scan

**Purpose:** Detect misconfigurations and secrets

**Workflow Location:** `.github/workflows/api-gitops-ci.yaml` (Lines 175-239)

**Commands:**
```bash
# Trivy scan for misconfigurations
trivy config apis/ --severity CRITICAL,HIGH,MEDIUM

# Check for hardcoded secrets
grep -rE "(password|secret|key):\s*['\"]?[a-zA-Z0-9]+" apis/ --include="*.yaml"

# Custom sensitive data checker
python3 scripts/check-sensitive-data.py apis/
```

---

### 5. Policy Validation

**Purpose:** Validate API policies (rate limits, auth)

**Workflow Location:** `.github/workflows/api-gitops-ci.yaml` (Lines 244-292)

**Commands:**
```bash
# Install yq
curl -L https://github.com/mikefarah/yq/releases/download/v4.40.5/yq_linux_amd64 -o /usr/local/bin/yq
chmod +x /usr/local/bin/yq

# Check rate limiting configurations
for file in apis/base/*/api-definition.yaml; do
  api_name=$(yq '.metadata.name' "$file")
  rate_limit=$(yq '.spec.flows[].pre[] | select(.policy == "rate-limit") | .configuration.rate.limit' "$file" 2>/dev/null)
  echo "API: $api_name - Rate Limit: $rate_limit"
done

# Validate authentication policies
for file in apis/base/*/api-plan.yaml; do
  yq eval-all '.metadata.name as $name | .spec.security as $security | "\($name): \($security)"' "$file"
done

# Custom policy validation
python3 scripts/validate-policies.py apis/
```

---

## Post-Deployment Testing

### Prerequisites

```bash
# Install Node.js dependencies
npm install -g newman newman-reporter-htmlextra k6

# Install Python dependencies
pip install pytest requests jsonschema schemathesis pyjwt pyyaml
```

---

### 1. Smoke Tests

**Purpose:** Quick health checks after deployment

**Workflow Location:** `workflows/post-deploy-tests.yaml` (Lines 144-190)

**Commands:**
```bash
# Run smoke tests with Newman
newman run api-testing/tests/postman/smoke-tests.json \
  --environment api-testing/tests/postman/env-dev.json \
  --env-var "GATEWAY_URL=http://localhost:8082" \
  --reporters cli,htmlextra,junit \
  --reporter-htmlextra-export reports/smoke-tests.html \
  --reporter-junit-export reports/smoke-tests.xml \
  --timeout-request 10000
```

**Sample Smoke Test (Postman Collection):**
```json
{
  "name": "API Gateway Health",
  "request": {
    "method": "GET",
    "url": "{{gateway_url}}/_node/health"
  },
  "event": [{
    "listen": "test",
    "script": {
      "exec": [
        "pm.test('Gateway is healthy', function () {",
        "    pm.response.to.have.status(200);",
        "});",
        "pm.test('Response time is acceptable', function () {",
        "    pm.expect(pm.response.responseTime).to.be.below(1000);",
        "});"
      ]
    }
  }]
}
```

---

### 2. Functional/Integration Tests

**Purpose:** Full API functionality validation

**Workflow Location:** `workflows/post-deploy-tests.yaml` (Lines 194-244)

**Commands:**
```bash
# Run functional tests
newman run api-testing/tests/functional/users-api.json \
  --environment api-testing/tests/postman/env-dev.json \
  --env-var "GATEWAY_URL=http://localhost:8082" \
  --reporters cli,htmlextra,junit \
  --reporter-htmlextra-export reports/functional-tests.html \
  --reporter-junit-export reports/functional-tests.xml \
  --iteration-count 1
```

**Test Categories in Integration Collection:**

| Category | Tests Included |
|----------|----------------|
| **Health & Smoke** | Gateway health, API endpoint availability |
| **Authentication** | Token validation, expired token, no token |
| **Rate Limiting** | Headers present, enforcement |
| **Error Handling** | 404, 400, error response format |
| **Response Headers** | Security headers, Gravitee headers |
| **CRUD Operations** | GET, POST, PUT, DELETE |

---

### 3. Contract Tests

**Purpose:** Schema validation against OpenAPI specs

**Workflow Location:** `workflows/post-deploy-tests.yaml` (Lines 249-301)

**Commands:**
```bash
# Run pytest contract tests
python -m pytest api-testing/tests/contract/ \
  -v \
  --html=reports/contract-tests.html \
  --self-contained-html \
  --junitxml=reports/contract-tests.xml

# Run Schemathesis (property-based testing)
schemathesis run openapi.yaml \
  --base-url "http://localhost:8082" \
  --header "X-Gravitee-Api-Key: your-api-key" \
  --checks all \
  --max-examples 50 \
  --report reports/schemathesis-report.html
```

---

### 4. Security Tests

**Purpose:** OWASP vulnerability scanning

**Workflow Location:** `workflows/post-deploy-tests.yaml` (Lines 306-356)

**Commands:**
```bash
# Run Python security tests
python -m pytest api-testing/tests/security/ \
  -v \
  --html=reports/security-tests.html \
  --junitxml=reports/security-tests.xml

# Run OWASP ZAP scan
docker run -v $(pwd):/zap/wrk:rw \
  -t owasp/zap2docker-stable zap-api-scan.py \
  -t http://localhost:8082/api/v1/openapi.json \
  -f openapi \
  -c cicd/testing/security/zap-config.yaml \
  -r zap-report.html \
  -J zap-report.json
```

**ZAP Configuration Highlights:**

| Scan Type | Purpose | Duration |
|-----------|---------|----------|
| **Passive Scan** | Analyze responses for issues | Continuous |
| **Spider** | Discover endpoints | 5 min max |
| **Active Scan** | Attack endpoints | 30 min max |

**Security Rules Checked:**
- SQL Injection (40018)
- Cross-Site Scripting (40012)
- Path Traversal (6)
- Remote File Inclusion (7)
- CRLF Injection (40003)
- External Redirect (20019)

---

### 5. Performance Tests

**Purpose:** Load and stress testing

**Workflow Location:** `workflows/post-deploy-tests.yaml` (Lines 361-405)

**Commands:**
```bash
# Run load test
k6 run cicd/testing/performance/load-test.js \
  -e GATEWAY_URL=http://localhost:8082 \
  -e API_PATH=/petstore/v3 \
  -e ENVIRONMENT=dev \
  --out json=reports/k6-results.json \
  --summary-export=reports/k6-summary.json

# Run stress test
k6 run api-testing/tests/performance/stress-test.js \
  -e GATEWAY_URL=http://localhost:8082 \
  --out json=reports/k6-stress-results.json

# Check thresholds
python3 api-testing/scripts/check-performance-thresholds.py reports/k6-summary.json
```

**Load Test Stages:**

| Stage | Duration | Virtual Users | Purpose |
|-------|----------|---------------|---------|
| Ramp Up | 1 min | 0 → 10 | Warm up |
| Ramp Up | 3 min | 10 → 50 | Increase load |
| Steady | 5 min | 50 | Normal load |
| Ramp Up | 2 min | 50 → 100 | Peak load |
| Steady | 3 min | 100 | Peak load |
| Ramp Down | 2 min | 100 → 0 | Cool down |

**Performance Thresholds:**

```javascript
thresholds: {
  http_req_duration: ['p(95)<500', 'p(99)<1000'],  // 95% < 500ms
  http_req_failed: ['rate<0.01'],                   // Error rate < 1%
  errors: ['rate<0.05'],                            // Custom errors < 5%
  api_latency: ['p(95)<400'],                       // API latency p95 < 400ms
}
```

---

## Quality Gates

### PR Gate (Required for Merge)

```yaml
checks:
  yaml_lint: pass
  schema_validation: pass
  security_scan: no_high_severity
  code_review: approved
```

**Enforced in:** `.github/workflows/api-gitops-ci.yaml`

---

### DEV Gate (Required for UAT Promotion)

```yaml
checks:
  smoke_tests: 100% pass
  contract_tests: 100% pass
  integration_tests: 95% pass
  api_available: true
```

**Enforced in:** `workflows/post-deploy-tests.yaml`

---

### UAT Gate (Required for PROD Promotion)

```yaml
checks:
  e2e_tests: 100% pass
  performance_tests:
    p95_latency: < 500ms
    error_rate: < 1%
  security_scan: no_critical
  manual_approval: required
```

**Enforced in:** `cicd/github-actions/promote-api.yaml`

---

## CI/CD Integration

### Workflow Files

| File | Purpose | Trigger |
|------|---------|---------|
| `.github/workflows/api-gitops-ci.yaml` | Pre-deployment validation | Push, PR |
| `cicd/github-actions/validate-api.yaml` | PR validation | PR only |
| `cicd/github-actions/deploy-api.yaml` | Deployment to environments | Push to main |
| `cicd/github-actions/promote-api.yaml` | Environment promotion | Manual |
| `workflows/post-deploy-tests.yaml` | Post-deployment testing | ArgoCD webhook, Manual |

### Scheduled Tests

```yaml
schedule:
  # Nightly security scans at 2 AM UTC
  - cron: '0 2 * * *'
  # Weekly performance tests on Saturday 3 AM UTC
  - cron: '0 3 * * 6'
```

### Manual Trigger

```bash
# Via GitHub CLI
gh workflow run "Post-Deployment API Tests" \
  -f environment=dev \
  -f test_types=all

# Via API
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/actions/workflows/post-deploy-tests.yaml/dispatches \
  -d '{"ref":"main","inputs":{"environment":"dev","test_types":"all"}}'
```

---

## Quick Reference Commands

### Run All Tests Locally

```bash
#!/bin/bash
# Complete local test suite

GATEWAY_URL="http://localhost:8082"
ENV="dev"

echo "=== 1. YAML Lint ==="
yamllint -c .yamllint.yaml apis/

echo "=== 2. CRD Validation ==="
kustomize build apis/overlays/$ENV > /tmp/manifests.yaml
kubeconform -summary /tmp/manifests.yaml

echo "=== 3. Smoke Tests ==="
newman run api-testing/tests/postman/smoke-tests.json \
  -e api-testing/tests/postman/env-$ENV.json \
  --env-var "GATEWAY_URL=$GATEWAY_URL"

echo "=== 4. Functional Tests ==="
newman run cicd/testing/integration/postman-collection.json \
  --env-var "gateway_url=$GATEWAY_URL"

echo "=== 5. Contract Tests ==="
python -m pytest api-testing/tests/contract/ -v

echo "=== 6. Security Tests ==="
python -m pytest api-testing/tests/security/ -v

echo "=== 7. Performance Tests ==="
k6 run cicd/testing/performance/load-test.js \
  -e GATEWAY_URL=$GATEWAY_URL \
  --duration 1m \
  --vus 10

echo "=== All Tests Complete ==="
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GATEWAY_URL` | Gravitee Gateway URL | `http://localhost:8082` |
| `ENVIRONMENT` | Target environment | `dev` |
| `API_KEY` | API key for authentication | - |
| `KEYCLOAK_URL` | Keycloak server URL | `http://localhost:8180` |
| `CLIENT_ID` | OAuth2 client ID | `api-client` |
| `CLIENT_SECRET` | OAuth2 client secret | - |
| `VUS` | Virtual users for load tests | `10` |
| `DURATION` | Test duration | `30s` |

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `YAML Lint failed` | Trailing spaces, missing `---` | Run `sed -i 's/[[:space:]]*$//' file.yaml` |
| `kubeconform schema not found` | GKO CRDs not in default schemas | Add `-skip ApiDefinition,ApiV4Definition` |
| `Newman timeout` | Slow API response | Increase `--timeout-request` |
| `k6 threshold failed` | Performance below threshold | Check API/backend performance |
| `ZAP scan timeout` | Too many endpoints | Reduce `maxScanDurationInMins` |
| `401 Unauthorized` | Token expired/invalid | Refresh OAuth token |

### Debug Commands

```bash
# Check API is reachable
curl -v http://localhost:8082/petstore/v3/pet/1

# Get OAuth token
curl -X POST http://localhost:8180/realms/gravitee/protocol/openid-connect/token \
  -d "client_id=api-client" \
  -d "client_secret=secret" \
  -d "grant_type=client_credentials"

# Test with token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8082/petstore-secure/v3/pet/1

# Check Gateway logs
kubectl logs -n gravitee deployment/gravitee-apim-gateway -f

# Check GKO operator logs
kubectl logs -n gravitee-gko deployment/gko-controller-manager -f
```

---

## Test Reports

### Report Locations

| Test Type | Format | Location |
|-----------|--------|----------|
| Smoke Tests | HTML, JUnit | `reports/smoke-tests.html`, `reports/smoke-tests.xml` |
| Functional Tests | HTML, JUnit | `reports/functional-*.html` |
| Contract Tests | HTML, JUnit | `reports/contract-tests.html` |
| Security Tests | HTML, SARIF | `reports/security-tests.html`, `zap-report.sarif` |
| Performance Tests | JSON | `reports/k6-summary.json` |

### GitHub Actions Artifacts

Test results are uploaded as artifacts and retained for:
- **Standard tests:** 14 days
- **Security/Performance:** 30 days

---

## Summary Checklist

### Before PR Merge
- [ ] YAML lint passes
- [ ] CRD schema validation passes
- [ ] No security vulnerabilities (CRITICAL/HIGH)
- [ ] Policy validation passes
- [ ] Code review approved

### Before UAT Promotion
- [ ] All smoke tests pass
- [ ] All contract tests pass
- [ ] Integration tests ≥ 95% pass
- [ ] API endpoints accessible

### Before PROD Promotion
- [ ] All E2E tests pass
- [ ] Performance: p95 < 500ms
- [ ] Performance: error rate < 1%
- [ ] Security scan: no CRITICAL
- [ ] Manual approval obtained
- [ ] Rollback plan documented

---

## References

- [Gravitee APIM Documentation](https://documentation.gravitee.io/)
- [GKO Documentation](https://documentation.gravitee.io/gravitee-kubernetes-operator/)
- [Newman CLI](https://learning.postman.com/docs/collections/using-newman-cli/command-line-integration-with-newman/)
- [k6 Documentation](https://k6.io/docs/)
- [OWASP ZAP](https://www.zaproxy.org/docs/)
- [Spectral](https://stoplight.io/open-source/spectral)
- [Schemathesis](https://schemathesis.readthedocs.io/)

