# Team API Repository Template

Use this template to create a new team-specific API repository.

## Quick Start

1. **Create new repository** from this template
2. **Rename** `my-api` to your API name
3. **Update** configurations with your team details
4. **Register** with ArgoCD (platform team)

## Repository Structure

```
<team>-apis/
├── apis/
│   ├── base/
│   │   ├── kustomization.yaml
│   │   └── my-api/
│   │       ├── api-definition.yaml
│   │       └── api-plan.yaml
│   └── overlays/
│       ├── dev/
│       │   └── kustomization.yaml
│       ├── uat/
│       │   └── kustomization.yaml
│       └── prod/
│           └── kustomization.yaml
├── .github/workflows/
│   └── ci.yaml
├── scripts/
├── CODEOWNERS
└── README.md
```

## Configuration

### 1. Update Team Details

Edit `apis/base/kustomization.yaml`:
```yaml
commonLabels:
  team: your-team-name
  cost-center: CC-YOUR-TEAM
```

### 2. Configure Backend URLs

Each overlay patches the backend URL:
- Dev: `http://<service>.<team>-dev.svc.cluster.local:8080`
- UAT: `http://<service>.<team>-uat.svc.cluster.local:8080`
- Prod: `http://<service>.<team>-prod.svc.cluster.local:8080`

### 3. Update CODEOWNERS

```
* @your-team @your-team-leads
/apis/overlays/prod/ @sre-team
```

## Deployment

ArgoCD automatically syncs:
- **Dev/UAT**: On push to `develop` branch
- **Prod**: Manual sync after merge to `main`

