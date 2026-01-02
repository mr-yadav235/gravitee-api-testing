# Team API Repository Template

This is a template repository for team-specific Gravitee API definitions.

## Quick Start

1. Create a new repository from this template
2. Update `CODEOWNERS` with your team members
3. Define your APIs in `apis/`
4. Configure environment overlays in `overlays/`
5. Push to trigger CI/CD pipeline

## Repository Structure

```
.
├── apis/                          # API definitions
│   └── my-api/
│       ├── api-definition.yaml    # GKO ApiV4Definition
│       ├── api-plan.yaml          # Additional plans (optional)
│       └── tests/                 # API-specific tests
│           ├── unit/              # Unit tests for policies
│           ├── contract/          # OpenAPI contract tests
│           └── integration/       # Integration tests
├── overlays/                      # Environment configurations
│   ├── dev/
│   │   └── kustomization.yaml
│   ├── uat/
│   │   └── kustomization.yaml
│   └── prod/
│       └── kustomization.yaml
├── .github/
│   └── workflows/
│       ├── validate.yaml          # PR validation
│       ├── test.yaml              # Run tests
│       └── deploy.yaml            # Deploy via ArgoCD
├── CODEOWNERS                     # Team ownership
└── README.md
```

## CI/CD Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   PR Open   │────▶│  Validate   │────▶│    Test     │────▶│   Review    │
│             │     │  - YAML     │     │  - Unit     │     │  - CODEOWNER│
│             │     │  - Schema   │     │  - Contract │     │  - Approval │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                    │
                                                                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    PROD     │◀────│    UAT      │◀────│    DEV      │◀────│   Merge     │
│  (Manual)   │     │  (Auto)     │     │  (Auto)     │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

## Testing Strategy

| Phase | Test Type | Tool | Gate |
|-------|-----------|------|------|
| PR | Schema Validation | kubeconform | Required |
| PR | Contract Tests | Spectral | Required |
| DEV | Integration Tests | Postman/Newman | Required |
| UAT | E2E Tests | Postman/Newman | Required |
| UAT | Performance Tests | k6 | Advisory |
| UAT | Security Scan | OWASP ZAP | Required |

## Commands

```bash
# Validate locally
kustomize build overlays/dev

# Run tests
npm test

# Deploy to dev (via ArgoCD)
argocd app sync my-team-apis-dev
```

