# Multi-Repository Strategy for Gravitee APIs

## Overview

This guide describes how to organize Gravitee API definitions across multiple Git repositories, giving each team full autonomy over their APIs.

## Repository Structure Options

### Option 1: Monorepo (Single Repository)

```
gravitee-apis/                    # Single repo for all teams
├── apis/teams/catalog-team/
├── apis/teams/commerce-team/
└── apis/teams/platform-team/
```

**Pros:**
- Simpler CI/CD setup
- Easier cross-team visibility
- Single source of truth

**Cons:**
- All teams share same release cycle
- Merge conflicts between teams
- Less team autonomy

---

### Option 2: Multi-Repo (Separate Repositories) ✅ Recommended

```
# Each team has their own repository

catalog-team-apis/               # Catalog Team's repo
├── apis/
│   ├── base/
│   │   └── products-api/
│   └── overlays/
│       ├── dev/
│       ├── uat/
│       └── prod/
├── .github/workflows/
└── CODEOWNERS

commerce-team-apis/              # Commerce Team's repo
├── apis/
│   ├── base/
│   │   └── orders-api/
│   └── overlays/
└── ...

platform-team-apis/              # Platform Team's repo
├── apis/
│   ├── base/
│   │   └── users-api/
│   └── overlays/
└── ...

gravitee-shared-config/          # Shared configurations (Platform team)
├── base/
│   ├── namespace.yaml
│   └── management-context.yaml
└── argocd/
```

**Pros:**
- Full team autonomy
- Independent release cycles
- Clear ownership boundaries
- Teams can have different branching strategies
- Smaller, focused repositories

**Cons:**
- More ArgoCD applications to manage
- Need to sync shared configurations
- Slightly more complex initial setup

---

## Multi-Repo Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Multi-Repo GitOps Architecture                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│   │  catalog-team-   │  │  commerce-team-  │  │  platform-team-  │         │
│   │      apis        │  │      apis        │  │      apis        │         │
│   │   (Products)     │  │    (Orders)      │  │    (Users)       │         │
│   └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘         │
│            │                     │                     │                    │
│            ▼                     ▼                     ▼                    │
│   ┌──────────────────────────────────────────────────────────────┐         │
│   │                         ArgoCD                                │         │
│   │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │         │
│   │  │ catalog-   │  │ commerce-  │  │ platform-  │              │         │
│   │  │ team-app   │  │ team-app   │  │ team-app   │              │         │
│   │  └────────────┘  └────────────┘  └────────────┘              │         │
│   └──────────────────────────────────────────────────────────────┘         │
│                                    │                                        │
│                                    ▼                                        │
│   ┌──────────────────────────────────────────────────────────────┐         │
│   │              Gravitee Kubernetes Operator (GKO)               │         │
│   └──────────────────────────────────────────────────────────────┘         │
│                                    │                                        │
│                                    ▼                                        │
│   ┌──────────────────────────────────────────────────────────────┐         │
│   │                      Gravitee APIM Gateway                    │         │
│   └──────────────────────────────────────────────────────────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Setting Up Multi-Repo

### Step 1: Create Team Repository

Each team creates their own repository with this structure:

```
<team>-apis/
├── apis/
│   ├── base/
│   │   ├── kustomization.yaml
│   │   └── <api-name>/
│   │       ├── api-definition.yaml
│   │       └── api-plan.yaml
│   └── overlays/
│       ├── dev/
│       │   └── kustomization.yaml
│       ├── uat/
│       │   └── kustomization.yaml
│       └── prod/
│           └── kustomization.yaml
├── .github/
│   └── workflows/
│       ├── ci.yaml
│       ├── promotion.yaml
│       └── rollback.yaml
├── scripts/
├── CODEOWNERS
└── README.md
```

### Step 2: Shared Configuration Repository

Platform team maintains shared configurations:

```
gravitee-shared-config/
├── base/
│   ├── namespace.yaml           # Shared namespace definitions
│   └── management-context.yaml  # ManagementContext CRD
├── argocd/
│   ├── projects/               # ArgoCD projects per team
│   └── application-sets/       # ApplicationSets for each team repo
└── policies/
    └── common-policies.yaml    # Shared policy configurations
```

### Step 3: Reference Shared Config via Kustomize Remote

Teams can reference shared configurations:

```yaml
# In team's apis/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  # Remote reference to shared config
  - https://github.com/your-org/gravitee-shared-config//base/namespace.yaml?ref=v1.0.0
  - https://github.com/your-org/gravitee-shared-config//base/management-context.yaml?ref=v1.0.0
  # Local API definitions
  - products-api/api-definition.yaml
  - products-api/api-plan.yaml
```

---

## ArgoCD Configuration for Multi-Repo

### ApplicationSet per Team Repository

```yaml
# In gravitee-shared-config/argocd/application-sets/catalog-team.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: catalog-team-apis
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - env: dev
          - env: uat
          - env: prod
  
  template:
    metadata:
      name: 'catalog-team-apis-{{env}}'
    spec:
      project: catalog-team
      source:
        # Points to team's own repository
        repoURL: 'https://github.com/your-org/catalog-team-apis.git'
        targetRevision: '{{env == "prod" ? "main" : "develop"}}'
        path: 'apis/overlays/{{env}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: 'gravitee-apis-{{env}}'
```

### Multiple Sources (ArgoCD 2.6+)

ArgoCD supports multiple sources, allowing teams to combine their repo with shared config:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: catalog-team-apis-prod
spec:
  sources:
    # Shared configuration
    - repoURL: 'https://github.com/your-org/gravitee-shared-config.git'
      targetRevision: main
      path: base
    
    # Team-specific APIs
    - repoURL: 'https://github.com/your-org/catalog-team-apis.git'
      targetRevision: main
      path: apis/overlays/prod
```

---

## CI/CD for Multi-Repo

Each team repository has its own CI/CD pipeline:

```yaml
# .github/workflows/ci.yaml in each team repo
name: API CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Validate CRDs
        run: |
          # Download shared validation scripts
          curl -O https://raw.githubusercontent.com/your-org/gravitee-shared-config/main/scripts/validate-gko-crds.py
          python3 validate-gko-crds.py apis/
      
      - name: Build Kustomize
        run: |
          for env in dev uat prod; do
            kustomize build apis/overlays/$env > /tmp/manifests-$env.yaml
          done
```

---

## Comparison Table

| Aspect | Monorepo | Multi-Repo |
|--------|----------|------------|
| **Team Autonomy** | Low | High |
| **Release Independence** | Shared releases | Independent releases |
| **CI/CD Complexity** | Simpler | Per-repo pipelines |
| **Cross-team Visibility** | Easy | Requires tooling |
| **Merge Conflicts** | More likely | Isolated |
| **Onboarding** | Single repo to learn | Team-specific repos |
| **ArgoCD Apps** | Fewer | More (one per team/env) |
| **Best For** | Small orgs, few teams | Large orgs, many teams |

---

## Recommendations

### Use Monorepo When:
- Small organization (< 5 teams)
- Teams work closely together
- Shared release cycles are acceptable
- Simpler tooling is preferred

### Use Multi-Repo When:
- Large organization (5+ teams)
- Teams need full autonomy
- Different compliance requirements per team
- Independent release cycles needed
- Teams have different tech stacks/tooling preferences

---

## Migration Path: Monorepo → Multi-Repo

1. **Create team repositories** with same structure
2. **Copy team's APIs** to their new repository
3. **Update ArgoCD** to point to new repositories
4. **Test in dev/uat** before production
5. **Remove old paths** from monorepo
6. **Update CODEOWNERS** in shared config repo

