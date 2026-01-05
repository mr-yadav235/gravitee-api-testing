# GitLab CI/CD Implementation

This folder contains the GitLab CI/CD equivalent of all GitHub Actions workflows for the Gravitee API Testing Strategy project.

## 📁 Folder Structure

```
gitlab-ci/
├── README.md                           # This file
├── .gitlab-ci.yml                      # Main pipeline configuration
├── pipelines/
│   ├── api-gitops-ci.yml              # Pre-deployment validation pipeline
│   ├── deploy-api.yml                  # Deployment pipeline
│   ├── promote-api.yml                 # Environment promotion pipeline
│   ├── validate-api.yml                # PR/MR validation pipeline
│   └── post-deploy-tests.yml           # Post-deployment testing pipeline
├── templates/
│   ├── .base-jobs.yml                  # Reusable job templates
│   └── .variables.yml                  # Shared variables
└── scripts/
    └── notify-slack.sh                 # Slack notification helper
```

## 🔄 GitHub Actions to GitLab CI Mapping

| GitHub Actions | GitLab CI | Description |
|----------------|-----------|-------------|
| `workflow_dispatch` | `when: manual` | Manual trigger |
| `on: push` | `rules: - if: $CI_PIPELINE_SOURCE == "push"` | Push trigger |
| `on: pull_request` | `rules: - if: $CI_MERGE_REQUEST_IID` | MR trigger |
| `on: schedule` | `schedules` (in UI or API) | Scheduled runs |
| `jobs.<job>.needs` | `needs:` | Job dependencies |
| `jobs.<job>.strategy.matrix` | `parallel: matrix:` | Matrix builds |
| `secrets.XXX` | `$XXX` (CI/CD Variables) | Secrets |
| `actions/upload-artifact` | `artifacts:` | Artifact upload |
| `actions/cache` | `cache:` | Caching |
| `environment` | `environment:` | Environment protection |

## 🚀 Quick Setup

### 1. Copy Main Pipeline File

Copy `.gitlab-ci.yml` to your repository root:

```bash
cp gitlab-ci/.gitlab-ci.yml .gitlab-ci.yml
```

### 2. Configure CI/CD Variables

In GitLab, go to **Settings → CI/CD → Variables** and add:

| Variable | Type | Protected | Description |
|----------|------|-----------|-------------|
| `ARGOCD_SERVER` | Variable | Yes | ArgoCD server URL |
| `ARGOCD_AUTH_TOKEN` | Variable | Yes | ArgoCD API token |
| `SLACK_WEBHOOK_URL` | Variable | Yes | Slack webhook URL |
| `TEST_API_KEY` | Variable | Yes | API key for testing |
| `KUBECONFIG` | File | Yes | Kubernetes config |

### 3. Enable Pipeline Schedules (Optional)

For scheduled tests, go to **CI/CD → Schedules** and create:

- **Nightly Security Scan**: `0 2 * * *` (2 AM UTC daily)
- **Weekly Performance Test**: `0 3 * * 6` (3 AM UTC Saturday)

## 📋 Pipeline Stages

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   validate  │→ │    build    │→ │   security  │→ │   deploy    │→ │    test     │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

## 🔒 Protected Environments

Configure environment protection in **Settings → CI/CD → Environments**:

- **dev**: Auto-deploy
- **uat**: Require approval from `api-team`
- **prod**: Require approval from `api-admins`

## 📚 Documentation

- [GitLab CI/CD Documentation](https://docs.gitlab.com/ee/ci/)
- [GitLab CI/CD Variables](https://docs.gitlab.com/ee/ci/variables/)
- [GitLab Environments](https://docs.gitlab.com/ee/ci/environments/)

