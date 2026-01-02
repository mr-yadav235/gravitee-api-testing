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

## 📚 References

- [GKO Documentation](https://documentation.gravitee.io/gravitee-kubernetes-operator/)
- [API Definition CRD Reference](https://documentation.gravitee.io/gravitee-kubernetes-operator/api-reference/api-definition-crd)
- [Gravitee Policy Reference](https://documentation.gravitee.io/apim/policies/)

