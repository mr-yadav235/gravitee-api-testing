# GKO (Gravitee Kubernetes Operator) API Deployment Guide

This guide explains how APIs are deployed to Gravitee APIM using the Gravitee Kubernetes Operator (GKO) and ArgoCD GitOps workflow.

## 📁 File Structure

```
cicd/environments/dev/
├── kustomization.yaml    # Kustomize configuration (bundles all resources)
├── namespace.yaml        # Kubernetes namespace definition
└── petstore-api.yaml     # API definitions (GKO CRDs)
```

---

## 🔑 Required Components

### 1. ManagementContext (Cluster-wide)

**Location:** `cicd/gko/management-context.yaml`

The ManagementContext tells GKO how to connect to your Gravitee Management API:

```yaml
apiVersion: gravitee.io/v1alpha1
kind: ManagementContext
metadata:
  name: gravitee-apim
  namespace: gravitee-gko
spec:
  baseUrl: http://gravitee-apim-api.gravitee.svc.cluster.local:83
  environmentId: DEFAULT
  organizationId: DEFAULT
  auth:
    secretRef:
      name: gravitee-admin-credentials
```

| Field | Description |
|-------|-------------|
| `baseUrl` | Internal K8s URL to Gravitee Management API |
| `environmentId` | Target environment (DEFAULT, DEV, UAT) |
| `organizationId` | Organization ID (usually DEFAULT) |
| `auth.secretRef` | Reference to K8s Secret with credentials |

---

### 2. Namespace (`namespace.yaml`)

Creates the Kubernetes namespace for API resources:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: gravitee-apis-dev
  labels:
    environment: dev
    app.kubernetes.io/name: gravitee-apis
  annotations:
    argocd.argoproj.io/sync-wave: "-1"  # Deploy namespace first
```

| Field | Description |
|-------|-------------|
| `name` | Namespace name (e.g., gravitee-apis-dev) |
| `labels.environment` | Environment identifier |
| `sync-wave: "-1"` | Ensures namespace is created before APIs |

---

### 3. API Definition (`petstore-api.yaml`)

The main API configuration using GKO's `ApiDefinition` CRD:

```yaml
apiVersion: gravitee.io/v1alpha1
kind: ApiDefinition
metadata:
  name: petstore-api
  namespace: gravitee-apis-dev
  labels:
    app.kubernetes.io/name: petstore-api
    team: platform
spec:
  contextRef:
    name: gravitee-apim           # Reference to ManagementContext
    namespace: gravitee-gko
  
  name: "Petstore API (GitOps)"
  description: "API managed via ArgoCD and GKO"
  version: "1.0.0"
  
  # Proxy configuration
  proxy:
    virtual_hosts:
      - path: /petstore-gitops/v3   # Gateway entrypoint
    groups:
      - name: default
        endpoints:
          - name: petstore-backend
            target: https://petstore3.swagger.io/api/v3  # Backend URL
  
  # Request/Response policies
  flows:
    - name: "All Requests"
      path-operator:
        path: /
        operator: STARTS_WITH
      pre:
        - name: "Add Headers"
          policy: transform-headers
          configuration:
            addHeaders:
              - name: X-Source
                value: gravitee-gitops
      post:
        - name: "Response Headers"
          policy: transform-headers
          configuration:
            addHeaders:
              - name: X-Powered-By
                value: Gravitee-GKO
  
  # Security plans
  plans:
    - name: "Keyless Plan"
      description: "Open access - no authentication"
      security: KEY_LESS
      status: PUBLISHED
```

#### Key Sections:

| Section | Description |
|---------|-------------|
| `contextRef` | Links to ManagementContext for API deployment |
| `proxy.virtual_hosts` | Gateway path where API is exposed |
| `proxy.groups.endpoints` | Backend service URL(s) |
| `flows` | Request/Response policies (rate limiting, headers, etc.) |
| `plans` | Security plans (KEY_LESS, API_KEY, JWT, OAUTH2) |

---

### 4. Kustomization (`kustomization.yaml`)

Bundles all resources for deployment:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

metadata:
  name: gravitee-apis-dev

namespace: gravitee-apis-dev

labels:
  - pairs:
      environment: dev
      app.kubernetes.io/managed-by: argocd

resources:
  - namespace.yaml      # Deploy namespace first
  - petstore-api.yaml   # Then deploy APIs

configMapGenerator:
  - name: api-config
    literals:
      - ENVIRONMENT=dev
      - LOG_LEVEL=DEBUG
```

---

## 🔐 Security Plan Types

| Plan Type | Security | Use Case |
|-----------|----------|----------|
| `KEY_LESS` | None | Public APIs, testing |
| `API_KEY` | API Key header | Simple authentication |
| `JWT` | JWT token validation | OAuth2/OIDC integration |
| `OAUTH2` | OAuth2 token introspection | Full OAuth2 flow |

### JWT Plan Example:

```yaml
plans:
  - name: "JWT-Keycloak"
    security: JWT
    securityDefinition: |
      {
        "signature": "RSA_RS256",
        "publicKeyResolver": "JWKS_URL",
        "resolverParameter": "http://keycloak:8080/realms/gravitee/protocol/openid-connect/certs",
        "extractClaims": true,
        "propagateAuthHeader": true
      }
    status: PUBLISHED
```

---

## 🚀 Deployment Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Git Push   │────▶│   ArgoCD    │────▶│     GKO     │────▶│  Gravitee   │
│  (YAML)     │     │  (Sync)     │     │  (Operator) │     │   APIM      │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

1. **Developer** pushes API definition changes to Git
2. **ArgoCD** detects changes and syncs to Kubernetes
3. **GKO** watches for ApiDefinition CRDs
4. **GKO** calls Gravitee Management API to create/update the API
5. **API** becomes available on the Gateway

---

## 📋 Common Operations

### Deploy a new API:

```bash
# Add API definition to the resources list in kustomization.yaml
# Then commit and push to Git
git add cicd/environments/dev/my-new-api.yaml
git commit -m "feat: Add my-new-api"
git push origin main
# ArgoCD will automatically sync
```

### Update an existing API:

```bash
# Edit the API definition file
# Commit and push
git add cicd/environments/dev/petstore-api.yaml
git commit -m "feat: Update petstore-api rate limits"
git push origin main
```

### Check deployed APIs:

```bash
kubectl get apidefinitions -n gravitee-apis-dev
```

### View API details:

```bash
kubectl describe apidefinition petstore-api -n gravitee-apis-dev
```

---

## 🔧 Troubleshooting

### API not appearing in Gravitee:

1. Check GKO logs:
   ```bash
   kubectl logs -n gravitee-gko deployment/gko-controller-manager
   ```

2. Verify ManagementContext:
   ```bash
   kubectl get managementcontext -A
   ```

3. Check API status:
   ```bash
   kubectl get apidefinition -n gravitee-apis-dev -o yaml
   ```

### Common Issues:

| Issue | Cause | Solution |
|-------|-------|----------|
| `bad credentials` | Wrong secret keys | Use `username`/`password` keys in Secret |
| `404 Not Found` | Wrong baseUrl | Remove `/management` from baseUrl |
| `connection refused` | Wrong service URL | Check K8s service name and port |

---

## 🔄 Environment Promotion

### Promotion Flow

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│   DEV   │────▶│   UAT   │────▶│  PROD   │
└─────────┘     └─────────┘     └─────────┘
     │               │               │
  Testing        Validation      Production
  & Debug        & QA Sign-off    Release
```

**Valid Promotion Paths:**
- ✅ `dev → uat` (Development to UAT)
- ✅ `uat → prod` (UAT to Production)
- ❌ `dev → prod` (Not allowed - must go through UAT)

---

### Method 1: GitHub Actions (Recommended)

Trigger the **Promote API** workflow from GitHub:

1. Go to **Actions** → **Promote API**
2. Click **Run workflow**
3. Select:
   - **Source environment:** `dev` or `uat`
   - **Target environment:** `uat` or `prod`
   - **API name:** (optional, leave empty for all)
4. Click **Run workflow**

This creates a **Pull Request** with:
- Promotion metadata
- Required reviewers (for prod)
- Slack notification

```yaml
# Workflow location: .github/workflows/promote-api.yaml
on:
  workflow_dispatch:
    inputs:
      source_env:
        type: choice
        options: [dev, uat]
      target_env:
        type: choice
        options: [uat, prod]
```

---

### Method 2: CLI Script (Local)

```bash
# Promote from dev to uat
./cicd/scripts/promote-env.sh dev uat

# Promote specific API
./cicd/scripts/promote-env.sh dev uat petstore-api

# Promote from uat to prod
./cicd/scripts/promote-env.sh uat prod
```

The script:
1. Validates the promotion path
2. Creates promotion metadata
3. Optionally triggers ArgoCD sync

---

### How Kustomize Overlays Work

Each environment uses **Kustomize overlays** to customize base API definitions:

```
cicd/environments/
├── dev/
│   ├── kustomization.yaml    # Dev-specific configs
│   ├── namespace.yaml
│   └── petstore-api.yaml     # Full API definition
├── uat/
│   ├── kustomization.yaml    # UAT patches
│   └── namespace.yaml
└── prod/
    ├── kustomization.yaml    # Prod patches
    ├── namespace.yaml
    └── network-policy.yaml   # Extra security
```

#### DEV Environment:
```yaml
# Full API definitions, debug logging
configMapGenerator:
  - name: api-config
    literals:
      - ENVIRONMENT=dev
      - LOG_LEVEL=DEBUG
```

#### UAT Environment:
```yaml
# References base APIs + applies patches
resources:
  - ../../gko/crds/api-definition-v4.yaml

patches:
  - target:
      kind: ApiV4Definition
      name: petstore-api
    patch: |-
      - op: replace
        path: /spec/listeners/0/paths/0/path
        value: /uat/petstore/v3    # UAT-specific path
      - op: replace
        path: /spec/name
        value: "Petstore API (UAT)"
```

#### PROD Environment:
```yaml
# Only secured APIs, stricter settings
resources:
  - ../../gko/crds/api-jwt-secured.yaml  # Only secured APIs

patches:
  # Production paths
  - target:
      kind: ApiV4Definition
    patch: |-
      - op: replace
        path: /spec/listeners/0/paths/0/path
        value: /api/petstore/v3
      - op: replace
        path: /spec/visibility
        value: PRIVATE
  
  # Disable payload logging
  - target:
      kind: ApiV4Definition
    patch: |-
      - op: replace
        path: /spec/analytics/logging/content/payload
        value: false
```

---

### Environment Differences Summary

| Aspect | DEV | UAT | PROD |
|--------|-----|-----|------|
| **Path Prefix** | `/petstore-gitops/` | `/uat/petstore/` | `/api/petstore/` |
| **Log Level** | DEBUG | INFO | WARN |
| **Rate Limit** | 1000/min | 500/min | 100/min |
| **Payload Logging** | ✅ Enabled | ✅ Enabled | ❌ Disabled |
| **Network Policy** | None | None | Restricted |
| **APIs Allowed** | All | All | Secured only |
| **Sync Mode** | Auto | Auto | Manual approval |

---

### Promotion Checklist

Before promoting to **UAT**:
- [ ] All unit tests pass
- [ ] API contract validated
- [ ] No breaking changes
- [ ] OpenAPI spec updated

Before promoting to **PROD**:
- [ ] UAT testing complete
- [ ] Performance tests passed
- [ ] Security scan clean
- [ ] Stakeholder approval
- [ ] Rollback plan ready

---

### ArgoCD Sync After Promotion

```bash
# Check application status
argocd app list

# Sync specific environment
argocd app sync gravitee-apis-uat
argocd app sync gravitee-apis-prod

# View diff before sync
argocd app diff gravitee-apis-prod
```

---

## 📚 References

- [GKO Documentation](https://documentation.gravitee.io/gravitee-kubernetes-operator/)
- [API Definition CRD Reference](https://documentation.gravitee.io/gravitee-kubernetes-operator/api-reference/api-definition-crd)
- [Gravitee Policy Reference](https://documentation.gravitee.io/apim/policies/)

