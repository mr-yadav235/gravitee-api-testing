# Gravitee APIM Local Setup

This folder contains all the resources needed to set up Gravitee APIM on Minikube for local development.

## 📁 Folder Structure

```
gravitee-setup/
├── README.md                    # This file
├── docs/
│   └── GRAVITEE_MINIKUBE_SETUP.md  # Detailed setup documentation
├── manifests/
│   ├── namespace.yaml           # Kubernetes namespace
│   ├── elasticsearch.yaml       # Elasticsearch deployment
│   └── nginx-proxy.yaml         # Nginx proxy for UI access
├── values/
│   └── gravitee-values.yaml     # Helm values for Gravitee APIM
└── scripts/
    └── setup.sh                 # Automated setup script
```

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Run the setup script
./scripts/setup.sh start
```

This will:
1. Start Minikube (if not running)
2. Add Helm repositories
3. Create namespace
4. Install MongoDB
5. Install Elasticsearch
6. Install Gravitee APIM
7. Setup Nginx Proxy
8. Start port forwarding

### Option 2: Manual Setup

Follow the detailed guide in [docs/GRAVITEE_MINIKUBE_SETUP.md](docs/GRAVITEE_MINIKUBE_SETUP.md)

## 📋 Script Commands

```bash
# Start everything
./scripts/setup.sh start

# Check status
./scripts/setup.sh status

# Stop port forwarding
./scripts/setup.sh stop

# Restart port forwarding only
./scripts/setup.sh port-forward

# Clean up everything
./scripts/setup.sh clean
```

## 🌐 Access URLs

After setup is complete:

| Component | URL | Credentials |
|-----------|-----|-------------|
| **Console** | http://localhost:8080 | admin / admin |
| **Gateway** | http://localhost:8082 | - |

## 📦 Components

| Component | Version | Description |
|-----------|---------|-------------|
| Gravitee APIM | 4.9.10 | API Management Platform |
| MongoDB | 8.2.3 | Database for Gravitee |
| Elasticsearch | 7.17.9 | Analytics and logging |
| Nginx | Alpine | Proxy for UI access |

## ⚙️ Configuration

### Modify Helm Values

Edit `values/gravitee-values.yaml` to customize:
- Resource limits
- Replica counts
- Feature toggles

### Modify Manifests

Edit files in `manifests/` to customize:
- Elasticsearch configuration
- Nginx proxy rules

## 🔧 Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n gravitee
```

### View Logs
```bash
# API logs
kubectl logs deployment/gravitee-apim-api -n gravitee

# Gateway logs
kubectl logs deployment/gravitee-apim-gateway -n gravitee

# Proxy logs
kubectl logs deployment/gravitee-proxy -n gravitee
```

### Restart Port Forwarding
```bash
./scripts/setup.sh port-forward
```

### Full Reset
```bash
./scripts/setup.sh clean
./scripts/setup.sh start
```

## 📚 Documentation

For detailed setup instructions, troubleshooting, and architecture details, see:
- [Gravitee Minikube Setup Guide](docs/GRAVITEE_MINIKUBE_SETUP.md)

