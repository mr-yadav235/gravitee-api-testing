# GitOps Guide for Gravitee API Management

## Overview

This guide describes the GitOps-driven CI/CD approach for managing APIs in Gravitee APIM using the Gravitee Kubernetes Operator (GKO).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GitOps Flow                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────────────┐  │
│   │   Git    │────▶│    CI    │────▶│  ArgoCD  │────▶│       GKO        │  │
│   │  (APIs)  │     │ Pipeline │     │          │     │ (K8s Operator)   │  │
│   └──────────┘     └──────────┘     └──────────┘     └────────┬─────────┘  │
│        │                                                       │            │
│        │                                                       ▼            │
│        │           ┌──────────────────────────────────────────────────┐    │
│        │           │              Gravitee APIM                        │    │
│        │           │  ┌─────────────┐    ┌─────────────────────────┐  │    │
│        │           │  │   Gateway   │◀───│   Management API        │  │    │
│        │           │  │  (Traffic)  │    │   (Configuration)       │  │    │
│        │           │  └─────────────┘    └─────────────────────────┘  │    │
│        │           └──────────────────────────────────────────────────┘    │
│        │                                                                    │
│        └─────────────────────  Source of Truth  ────────────────────────▶  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Repository Structure

```
gravitee-api-testing-strategy/
├── apis/
│   ├── base/                          # Base API definitions
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   ├── management-context.yaml
│   │   ├── users-api/
│   │   │   ├── api-definition.yaml    # GKO ApiDefinition CRD
│   │   │   └── api-plan.yaml          # GKO ApiPlan CRDs
│   │   ├── orders-api/
│   │   └── products-api/
│   └── overlays/                      # Environment-specific overrides
│       ├── dev/
│       │   └── kustomization.yaml
│       ├── uat/
│       │   └── kustomization.yaml
│       └── prod/
│           ├── kustomization.yaml
│           ├── external-secrets.yaml
│           └── network-policies.yaml
├── argocd/                            # ArgoCD configurations
│   ├── application-set.yaml
│   ├── notifications.yaml
│   └── rbac.yaml
├── templates/                         # API templates
│   ├── api-definition-template.yaml
│   └── api-plan-template.yaml
├── scripts/                           # Validation scripts
│   ├── validate-gko-crds.py
│   ├── validate-policies.py
│   └── check-sensitive-data.py
└── .github/workflows/                 # CI/CD pipelines
    ├── api-gitops-ci.yaml
    ├── api-promotion.yaml
    └── api-rollback.yaml
```

## GKO Custom Resource Definitions (CRDs)

### ApiDefinition

The `ApiDefinition` CRD represents a complete API configuration:

```yaml
apiVersion: gravitee.io/v1alpha1
kind: ApiDefinition
metadata:
  name: users-api
  namespace: gravitee-apis
spec:
  contextRef:
    name: gravitee-apim-context
  name: "Users API"
  version: "1.0.0"
  proxy:
    virtualHosts:
      - path: /api/v1/users
    groups:
      - endpoints:
          - target: http://users-service:8080
  flows:
    - name: "Rate Limiting"
      pre:
        - policy: rate-limit
          configuration:
            rate:
              limit: 100
              periodTimeUnit: MINUTES
```

### ApiPlan

The `ApiPlan` CRD defines subscription plans:

```yaml
apiVersion: gravitee.io/v1alpha1
kind: ApiPlan
metadata:
  name: users-api-standard-plan
spec:
  apiRef:
    name: users-api
  name: "Standard Plan"
  security: API_KEY
  status: PUBLISHED
  validation: AUTO
```

### ManagementContext

The `ManagementContext` CRD connects GKO to Gravitee Management API:

```yaml
apiVersion: gravitee.io/v1alpha1
kind: ManagementContext
metadata:
  name: gravitee-apim-context
spec:
  baseUrl: http://gravitee-management-api:8083
  environmentId: DEFAULT
  auth:
    secretRef:
      name: gravitee-admin-credentials
```

## Environment Promotion Flow

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│   DEV   │────▶│   UAT   │────▶│  PROD   │
└─────────┘     └─────────┘     └─────────┘
     │               │               │
     │  Auto-sync    │  Auto-sync    │  Manual sync
     │  Auto-heal    │  Auto-heal    │  Approval required
     │  Prune: Yes   │  Prune: Yes   │  Prune: No
     │               │               │
     ▼               ▼               ▼
  develop         develop          main
  branch          branch          branch
```

### Promotion Process

1. **Dev → UAT Promotion**
   - Trigger: Workflow dispatch or PR merge to develop
   - Validation: CRD validation, policy checks
   - Approval: Not required
   - Deployment: Automatic via ArgoCD

2. **UAT → Prod Promotion**
   - Trigger: Workflow dispatch only
   - Validation: Full test suite, security scan
   - Approval: Required (GitHub Environment protection)
   - Deployment: Manual sync in ArgoCD

### Using the Promotion Workflow

```bash
# Via GitHub CLI
gh workflow run api-promotion.yaml \
  -f api_name=users-api \
  -f source_env=uat \
  -f target_env=prod \
  -f version=1.2.0 \
  -f change_description="Added new endpoint for user preferences"
```

## Rollback Procedures

### Automatic Rollback (via ArgoCD)

ArgoCD maintains revision history. To rollback:

```bash
# Via ArgoCD CLI
argocd app rollback gravitee-apis-prod <revision>

# Or via UI
# Navigate to Application → History → Select revision → Rollback
```

### Manual Rollback (via Workflow)

```bash
# Via GitHub CLI
gh workflow run api-rollback.yaml \
  -f api_name=users-api \
  -f environment=prod \
  -f reason="Performance degradation after v1.2.0 release"
```

## CI/CD Pipeline Stages

### 1. Validation Stage

```yaml
jobs:
  validate-crds:
    - YAML linting
    - Kubeconform validation
    - GKO CRD structure validation
    - OpenAPI spec validation
```

### 2. Security Stage

```yaml
jobs:
  security-scan:
    - Trivy config scan
    - Sensitive data detection
    - Policy best practices
```

### 3. Diff Stage (PRs only)

```yaml
jobs:
  gitops-diff:
    - Generate manifests for each environment
    - Compare with base branch
    - Post diff as PR comment
```

### 4. Deploy Stage

```yaml
jobs:
  notify-argocd:
    - ArgoCD auto-syncs on Git changes
    - Manual sync for production
```

## Best Practices

### 1. API Definition Best Practices

- **Versioning**: Use semantic versioning (e.g., 1.0.0)
- **Naming**: Use kebab-case for API names
- **Documentation**: Include descriptions for all APIs and plans
- **Rate Limiting**: Always configure rate limits
- **Logging**: Use conditional logging in production

### 2. Security Best Practices

- **Secrets**: Never commit secrets; use External Secrets Operator
- **Authentication**: Prefer JWT over API keys for enterprise
- **Network Policies**: Apply network policies in production
- **RBAC**: Use ArgoCD RBAC for access control

### 3. GitOps Best Practices

- **Single Source of Truth**: Git is the only source of truth
- **Declarative**: All configurations are declarative YAML
- **Immutable**: Changes go through Git, not direct edits
- **Auditable**: Git history provides full audit trail

### 4. Kustomize Best Practices

- **Base/Overlay Pattern**: Common configs in base, env-specific in overlays
- **Strategic Patches**: Use JSON patches for targeted changes
- **Labels**: Apply consistent labels for filtering

## Troubleshooting

### Common Issues

1. **API not syncing to Gravitee**
   ```bash
   # Check GKO operator logs
   kubectl logs -n gravitee-system -l app=gravitee-kubernetes-operator
   
   # Check ApiDefinition status
   kubectl get apidefinition -n gravitee-apis -o yaml
   ```

2. **ArgoCD sync failed**
   ```bash
   # Check ArgoCD app status
   argocd app get gravitee-apis-prod
   
   # View sync details
   argocd app sync gravitee-apis-prod --dry-run
   ```

3. **ManagementContext authentication failed**
   ```bash
   # Verify secret exists
   kubectl get secret gravitee-admin-credentials -n gravitee-apis
   
   # Check Management API connectivity
   kubectl exec -it <gko-pod> -- curl http://gravitee-management-api:8083/management/organizations
   ```

### Debugging Commands

```bash
# View all Gravitee CRDs
kubectl get apidefinition,apiplan,managementcontext -A

# Describe specific API
kubectl describe apidefinition users-api -n gravitee-apis

# View ArgoCD application
argocd app get gravitee-apis-prod --show-params

# Check Kustomize build
kustomize build apis/overlays/prod
```

## Monitoring

### Key Metrics to Monitor

1. **ArgoCD Sync Status**
   - Sync success/failure rate
   - Time to sync
   - Out-of-sync duration

2. **GKO Operator Health**
   - Reconciliation errors
   - API sync latency
   - CRD processing time

3. **Gravitee Gateway**
   - Request latency (p50, p95, p99)
   - Error rate
   - Rate limit violations

### Alerting Rules

```yaml
# Example Prometheus alerts
- alert: ArgoCD_SyncFailed
  expr: argocd_app_info{sync_status="OutOfSync"} == 1
  for: 15m
  
- alert: GKO_ReconciliationError
  expr: gko_reconciliation_errors_total > 0
  for: 5m
```

## References

- [Gravitee Kubernetes Operator Documentation](https://docs.gravitee.io/apim/kubernetes/)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Kustomize Documentation](https://kustomize.io/)
- [External Secrets Operator](https://external-secrets.io/)

