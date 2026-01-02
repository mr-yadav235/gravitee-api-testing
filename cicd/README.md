# CI/CD for Gravitee API Management

This folder contains all configurations for GitOps-based API lifecycle management using ArgoCD and Gravitee Kubernetes Operator (GKO).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GitOps CI/CD Pipeline                              │
└─────────────────────────────────────────────────────────────────────────────┘

  Developer          GitHub            ArgoCD           GKO            Gravitee
     │                  │                 │               │                │
     │  Push API CRD    │                 │               │                │
     │─────────────────▶│                 │               │                │
     │                  │   Webhook       │               │                │
     │                  │────────────────▶│               │                │
     │                  │                 │  Sync CRDs    │                │
     │                  │                 │──────────────▶│                │
     │                  │                 │               │  Create/Update │
     │                  │                 │               │───────────────▶│
     │                  │                 │               │                │
     │                  │     Status      │               │                │
     │◀─────────────────│◀────────────────│◀──────────────│◀───────────────│
```

## Folder Structure

```
cicd/
├── README.md                    # This file
├── argocd/                      # ArgoCD configurations
│   ├── install.yaml             # ArgoCD installation manifest
│   ├── project.yaml             # ArgoCD Project for Gravitee APIs
│   ├── application-set.yaml     # ApplicationSet for multi-env deployment
│   └── notifications.yaml       # Slack/Teams notifications
├── gko/                         # Gravitee Kubernetes Operator
│   ├── install.yaml             # GKO Helm values
│   ├── management-context.yaml  # Connection to Gravitee APIM
│   └── crds/                    # Custom Resource examples
│       ├── api-definition.yaml
│       ├── api-plan.yaml
│       └── application.yaml
├── environments/                # Environment-specific configs
│   ├── dev/
│   ├── uat/
│   └── prod/
├── github-actions/              # GitHub Actions workflows
│   ├── validate-api.yaml
│   ├── deploy-api.yaml
│   └── promote-api.yaml
└── scripts/                     # Helper scripts
    ├── setup.sh
    ├── validate-crds.sh
    └── promote-env.sh
```

## Quick Start

### 1. Install ArgoCD & GKO

```bash
./scripts/setup.sh
```

### 2. Configure Management Context

```bash
kubectl apply -f gko/management-context.yaml
```

### 3. Deploy an API

```bash
kubectl apply -f gko/crds/api-definition.yaml
```

### 4. Check Status

```bash
kubectl get apidefinitions -A
kubectl get applications -n argocd
```

## Environment Promotion

```
DEV ──────▶ UAT ──────▶ PROD
 │           │           │
 │  PR/MR    │  PR/MR    │
 │  Review   │  Review   │
 └───────────┴───────────┘
```

APIs are promoted through environments via Pull Requests, ensuring proper review and approval gates.

