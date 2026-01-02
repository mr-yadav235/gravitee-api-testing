# Multi-Repository GitOps Strategy

This document describes the multi-repository architecture for managing Gravitee APIs across different teams.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        MULTI-REPO GITOPS ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────────┐
                              │   Platform Repo     │
                              │  (Central Config)   │
                              │  - ArgoCD Setup     │
                              │  - GKO Config       │
                              │  - Shared Policies  │
                              └──────────┬──────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
              ▼                          ▼                          ▼
   ┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
   │  Payments Team   │      │   Catalog Team   │      │   Orders Team    │
   │     Repo         │      │      Repo        │      │      Repo        │
   │                  │      │                  │      │                  │
   │ - payments-api   │      │ - products-api   │      │ - orders-api     │
   │ - refunds-api    │      │ - inventory-api  │      │ - shipping-api   │
   │ - billing-api    │      │ - search-api     │      │ - tracking-api   │
   └────────┬─────────┘      └────────┬─────────┘      └────────┬─────────┘
            │                         │                         │
            └─────────────────────────┼─────────────────────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │       ArgoCD         │
                           │  ApplicationSets     │
                           │  (SCM Generator)     │
                           └──────────┬───────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
              ┌──────────┐     ┌──────────┐     ┌──────────┐
              │   DEV    │     │   UAT    │     │   PROD   │
              │ Cluster  │     │ Cluster  │     │ Cluster  │
              └──────────┘     └──────────┘     └──────────┘
```

## Repository Structure

### Platform Repository (Central)
```
gravitee-platform/
├── argocd/
│   ├── applicationsets/
│   │   ├── team-repos-appset.yaml      # SCM-based ApplicationSet
│   │   └── platform-apps.yaml
│   ├── projects/
│   │   ├── payments-team.yaml
│   │   ├── catalog-team.yaml
│   │   └── orders-team.yaml
│   └── rbac/
├── gko/
│   ├── management-contexts/
│   │   ├── dev.yaml
│   │   ├── uat.yaml
│   │   └── prod.yaml
│   └── shared-policies/
│       ├── security-headers.yaml
│       ├── rate-limiting.yaml
│       └── logging.yaml
└── testing/
    └── shared-test-configs/
```

### Team Repository Template
```
team-apis/
├── apis/
│   ├── my-api/
│   │   ├── api-definition.yaml
│   │   ├── api-plan.yaml
│   │   └── tests/
│   │       ├── unit/
│   │       ├── contract/
│   │       └── integration/
│   └── another-api/
├── overlays/
│   ├── dev/
│   ├── uat/
│   └── prod/
├── .github/
│   └── workflows/
│       ├── validate.yaml
│       ├── test.yaml
│       └── deploy.yaml
└── CODEOWNERS
```

## Team Onboarding

1. Create team repository from template
2. Add team to ArgoCD project
3. Configure CODEOWNERS
4. Set up branch protection
5. Add to ApplicationSet SCM generator

