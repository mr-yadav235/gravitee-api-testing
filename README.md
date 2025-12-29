# Gravitee API GitOps CI/CD

GitOps-driven CI/CD solution for managing APIs in Gravitee APIM Gateway using the Gravitee Kubernetes Operator (GKO).

## 🎯 Features

- **GitOps-First**: Git as the single source of truth for all API definitions
- **GKO CRDs**: Native Kubernetes resources (ApiDefinition, ApiPlan, ManagementContext)
- **Multi-Environment**: Dev → UAT → Production promotion workflow
- **Automated Validation**: OpenAPI specs, CRD structure, security policies
- **ArgoCD Integration**: Automatic sync with approval gates for production
- **Rollback Support**: Easy rollback to any previous version
- **Security**: External secrets, network policies, RBAC

## 📁 Repository Structure

```
├── api-testing/                 # 🧪 Isolated API testing suite
│   ├── docs/                    # Testing strategy documentation
│   ├── scripts/                 # Test utility scripts
│   ├── tests/                   # All test files
│   │   ├── contract/            # Contract/schema validation
│   │   ├── functional/          # Functional API tests
│   │   ├── performance/         # k6 load & stress tests
│   │   ├── postman/             # Postman collections & envs
│   │   ├── security/            # Security tests
│   │   └── smoke/               # Smoke tests
│   └── workflows/               # Test-specific GitHub Actions
├── apis/
│   ├── base/                    # Base API definitions (source of truth)
│   │   ├── users-api/
│   │   ├── orders-api/
│   │   └── products-api/
│   ├── overlays/                # Environment-specific configurations
│   │   ├── dev/
│   │   ├── uat/
│   │   └── prod/
│   └── teams/                   # Team-based API ownership
│       ├── catalog-team/
│       └── commerce-team/
├── argocd/                      # ArgoCD ApplicationSets and RBAC
├── templates/                   # API definition templates
├── scripts/                     # Validation scripts
├── docs/                        # GitOps documentation
└── .github/workflows/           # CI/CD pipelines
```

## 🚀 Quick Start

### Prerequisites

- Kubernetes cluster with GKO installed
- ArgoCD deployed and configured
- GitHub repository access

### 1. Install Gravitee Kubernetes Operator

```bash
# Add Gravitee Helm repository
helm repo add gravitee https://helm.gravitee.io

# Install GKO
helm install gravitee-gko gravitee/gko \
  --namespace gravitee-system \
  --create-namespace
```

### 2. Configure ArgoCD

```bash
# Apply ArgoCD configurations
kubectl apply -f argocd/application-set.yaml
kubectl apply -f argocd/rbac.yaml
kubectl apply -f argocd/notifications.yaml
```

### 3. Create a New API

```bash
# Copy templates
cp templates/api-definition-template.yaml apis/base/my-api/api-definition.yaml
cp templates/api-plan-template.yaml apis/base/my-api/api-plan.yaml

# Edit and customize
# Replace all {{PLACEHOLDER}} values

# Commit and push
git add apis/base/my-api/
git commit -m "feat: add my-api definition"
git push origin develop
```

### 4. Deploy to Environment

ArgoCD will automatically sync changes:

- **Dev**: Auto-sync on push to `develop`
- **UAT**: Auto-sync on push to `develop`
- **Prod**: Manual sync after merge to `main`

## 📋 Workflows

### CI Pipeline (`api-gitops-ci.yaml`)

Triggered on every push/PR:

1. **YAML Lint** - Validate YAML syntax
2. **CRD Validation** - Validate Kubernetes and GKO CRDs
3. **OpenAPI Validation** - Lint embedded OpenAPI specs
4. **Security Scan** - Check for sensitive data and misconfigurations
5. **Policy Validation** - Verify rate limits and security policies
6. **GitOps Diff** - Show changes in PR comments

### Promotion Workflow (`api-promotion.yaml`)

Promote APIs between environments:

```bash
gh workflow run api-promotion.yaml \
  -f api_name=users-api \
  -f source_env=uat \
  -f target_env=prod \
  -f version=1.2.0 \
  -f change_description="Added user preferences endpoint"
```

### Rollback Workflow (`api-rollback.yaml`)

Rollback to previous version:

```bash
gh workflow run api-rollback.yaml \
  -f api_name=users-api \
  -f environment=prod \
  -f reason="Performance regression"
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GRAVITEE_MGMT_URL` | Management API URL | Yes |
| `GRAVITEE_MGMT_TOKEN` | Management API token | Yes |
| `ARGOCD_SERVER` | ArgoCD server URL | Yes |
| `ARGOCD_TOKEN` | ArgoCD API token | Yes |
| `SLACK_WEBHOOK_URL` | Slack notifications | No |

### Secrets

Configure these secrets in GitHub:

- `GRAVITEE_MGMT_TOKEN` - Gravitee Management API token
- `ARGOCD_TOKEN` - ArgoCD API token
- `SLACK_WEBHOOK_URL` - Slack webhook for notifications

## 🔒 Security

### Secrets Management

Production secrets are managed via External Secrets Operator:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: gravitee-admin-credentials
spec:
  secretStoreRef:
    kind: ClusterSecretStore
    name: vault-backend
  data:
    - secretKey: GRAVITEE_PASSWORD
      remoteRef:
        key: gravitee/production/admin
        property: password
```

### Network Policies

Production deployments include network policies restricting traffic:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: gravitee-apis-network-policy
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  # ... restricted access rules
```

## 📊 Monitoring

### ArgoCD Dashboard

Monitor sync status at: `https://<argocd-server>/applications`

### Key Metrics

- Sync success/failure rate
- Time to deploy
- Rollback frequency
- API error rates

## 📚 Documentation

- [GitOps Guide](docs/GITOPS_GUIDE.md) - Detailed GitOps workflow documentation
- [Multi-Repo Guide](docs/MULTI_REPO_GUIDE.md) - Team-based multi-repository setup
- [API Testing Strategy](api-testing/docs/API_TESTING_STRATEGY.md) - Comprehensive testing documentation
- [API Templates](templates/) - Templates for creating new APIs
- [ArgoCD Configuration](argocd/) - ArgoCD setup and RBAC

## 🤝 Contributing

1. Create a feature branch from `develop`
2. Make changes to API definitions
3. Run validation locally: `python scripts/validate-gko-crds.py apis/`
4. Create a Pull Request
5. Wait for CI checks and review
6. Merge to `develop` for Dev/UAT deployment
7. Use promotion workflow for production

## 🧪 API Testing Strategy

Comprehensive testing runs automatically after APIs are published. All testing resources are isolated in the `api-testing/` folder.

| Test Type | Trigger | Duration |
|-----------|---------|----------|
| **Smoke Tests** | Post-deploy | < 1 min |
| **Functional Tests** | Post-deploy | 5-10 min |
| **Contract Tests** | Post-deploy | 2-5 min |
| **Security Tests** | Nightly | 15-30 min |
| **Performance Tests** | Weekly | 30-60 min |

See [API Testing Strategy](api-testing/docs/API_TESTING_STRATEGY.md) for details, or check the [API Testing README](api-testing/README.md) for quick start.

## 📄 License

Apache 2.0

