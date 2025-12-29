# API Testing Strategy

This folder contains the complete API testing suite for Gravitee APIM Gateway APIs.

## 📁 Folder Structure

```
api-testing/
├── docs/
│   └── API_TESTING_STRATEGY.md    # Comprehensive testing strategy documentation
├── scripts/
│   └── check-performance-thresholds.py  # Performance threshold validation
├── tests/
│   ├── contract/                  # Contract/Schema validation tests
│   │   ├── openapi/              # OpenAPI specs for validation
│   │   └── test_schema_validation.py
│   ├── e2e/                      # End-to-end tests
│   ├── functional/               # Functional API tests
│   │   └── users-api.json        # Postman collection for Users API
│   ├── performance/              # Performance & load tests
│   │   ├── load-test.js          # k6 load test script
│   │   └── stress-test.js        # k6 stress test script
│   ├── postman/                  # Postman collections & environments
│   │   ├── env-dev.json          # Dev environment variables
│   │   ├── env-uat.json          # UAT environment variables
│   │   ├── env-prod.json         # Prod environment variables
│   │   └── smoke-tests.json      # Smoke test collection
│   ├── security/                 # Security tests
│   │   ├── test_api_security.py  # Security test suite
│   │   └── zap-rules.tsv         # OWASP ZAP rules
│   └── smoke/                    # Smoke tests
└── workflows/
    └── post-deploy-tests.yaml    # GitHub Actions workflow
```

## 🧪 Test Types

| Test Type | Tool | Purpose |
|-----------|------|---------|
| **Smoke Tests** | Newman/Postman | Quick health checks post-deployment |
| **Functional Tests** | Newman/Postman | Full API functionality validation |
| **Contract Tests** | Pytest + OpenAPI | Schema validation against specs |
| **Security Tests** | Pytest + OWASP ZAP | Vulnerability scanning |
| **Performance Tests** | k6 | Load and stress testing |

## 🚀 Quick Start

### Prerequisites

```bash
# Install Node.js dependencies
npm install -g newman k6

# Install Python dependencies
pip install pytest requests jsonschema schemathesis
```

### Running Tests Locally

#### Smoke Tests
```bash
newman run tests/postman/smoke-tests.json \
  -e tests/postman/env-dev.json \
  --reporters cli,junit \
  --reporter-junit-export results/smoke-results.xml
```

#### Functional Tests
```bash
newman run tests/functional/users-api.json \
  -e tests/postman/env-dev.json \
  --reporters cli,junit
```

#### Contract Tests
```bash
pytest tests/contract/test_schema_validation.py -v \
  --junitxml=results/contract-results.xml
```

#### Security Tests
```bash
pytest tests/security/test_api_security.py -v \
  --junitxml=results/security-results.xml
```

#### Performance Tests
```bash
# Load test
k6 run tests/performance/load-test.js \
  -e GATEWAY_URL=http://localhost:8082 \
  -e ENVIRONMENT=dev

# Stress test
k6 run tests/performance/stress-test.js \
  -e GATEWAY_URL=http://localhost:8082 \
  -e ENVIRONMENT=dev
```

## 🔄 CI/CD Integration

The `workflows/post-deploy-tests.yaml` file contains a GitHub Actions workflow that:

1. **Triggers** after API deployment via ArgoCD
2. **Runs** tests in sequence: Smoke → Functional → Contract → Security → Performance
3. **Reports** results back to GitHub and Slack
4. **Fails** the pipeline if critical tests don't pass

### Using the Workflow

Copy the workflow to your `.github/workflows/` directory:

```bash
cp workflows/post-deploy-tests.yaml ../.github/workflows/
```

Or reference it from your main repository's workflow.

## 📊 Test Reports

Test results are generated in various formats:
- **JUnit XML**: For CI/CD integration
- **HTML**: For human-readable reports
- **JSON**: For programmatic processing

Results are stored in the `results/` directory (created at runtime).

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GATEWAY_URL` | Gravitee Gateway URL | `http://localhost:8082` |
| `ENVIRONMENT` | Target environment | `dev` |
| `API_KEY` | API key for authentication | - |
| `VUS` | Virtual users for load tests | `10` |
| `DURATION` | Test duration | `30s` |

### Thresholds

Performance thresholds are defined in:
- `tests/performance/load-test.js` - k6 threshold configuration
- `scripts/check-performance-thresholds.py` - Custom threshold validation

## 📚 Documentation

For detailed information about the testing strategy, see:
- [API Testing Strategy](docs/API_TESTING_STRATEGY.md)

## 🤝 Contributing

1. Add new test collections to the appropriate folder
2. Update environment files with new variables
3. Document new tests in this README
4. Ensure tests pass locally before committing

