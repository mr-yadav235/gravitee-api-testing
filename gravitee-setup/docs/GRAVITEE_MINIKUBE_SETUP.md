# Gravitee APIM Setup on Minikube

This document provides a complete guide to setting up Gravitee API Management (APIM) on Minikube with all dependencies.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Start Minikube](#step-1-start-minikube)
3. [Add Helm Repositories](#step-2-add-helm-repositories)
4. [Create Namespace](#step-3-create-namespace)
5. [Install MongoDB](#step-4-install-mongodb)
6. [Install Elasticsearch](#step-5-install-elasticsearch)
7. [Install Gravitee APIM](#step-6-install-gravitee-apim)
8. [Setup Nginx Proxy](#step-7-setup-nginx-proxy)
9. [Access Gravitee Console](#step-8-access-gravitee-console)
10. [Configure Primary Owner Group](#step-9-configure-primary-owner-group-required-for-api-import)
11. [Setup Keycloak Authorization Server](#step-10-setup-keycloak-authorization-server-optional)
12. [Troubleshooting](#troubleshooting)
13. [Cleanup](#cleanup)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Minikube                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      gravitee namespace                            │  │
│  │                                                                    │  │
│  │  ┌──────────────┐  ┌────────────────────┐  ┌───────────────────┐  │  │
│  │  │   MongoDB    │  │  Elasticsearch 7.x │  │     Keycloak      │  │  │
│  │  │  (Bitnami)   │  │ (Simple Deployment)│  │  (Auth Server)    │  │  │
│  │  │  Port: 27017 │  │    Port: 9200      │  │   Port: 8180      │  │  │
│  │  └──────┬───────┘  └─────────┬──────────┘  └────────┬──────────┘  │  │
│  │         │                    │                      │             │  │
│  │         └────────────┬───────┴──────────────────────┘             │  │
│  │                      │                                            │  │
│  │  ┌───────────────────▼──────────────────────────────────────────┐ │  │
│  │  │                    Gravitee APIM                              │ │  │
│  │  │  ┌───────────┐ ┌───────────┐ ┌──────────┐ ┌───────────────┐  │ │  │
│  │  │  │  Gateway  │ │    API    │ │    UI    │ │    Portal     │  │ │  │
│  │  │  │  :8082    │ │   :8083   │ │  :8002   │ │    :8003      │  │ │  │
│  │  │  └───────────┘ └───────────┘ └──────────┘ └───────────────┘  │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  │                       │                                           │  │
│  │  ┌────────────────────▼─────────────────────────────────────────┐ │  │
│  │  │              Nginx Proxy (gravitee-proxy)                     │ │  │
│  │  │  - Proxies UI and Management API on single port               │ │  │
│  │  │  - Handles base path rewriting                                │ │  │
│  │  │  - Port: 8080                                                 │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  Port Forward: localhost:8080 → gravitee-proxy:8080                     │
│  Port Forward: localhost:8082 → gravitee-gateway:82                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Install Required Tools

```bash
# Install Minikube
brew install minikube

# Install Helm
brew install helm

# Install kubectl
brew install kubectl
```

### System Requirements

- **CPU**: 4 cores minimum
- **Memory**: 8GB minimum
- **Disk**: 20GB free space
- **Docker**: Running and accessible

---

## Step 1: Start Minikube

```bash
# Start Minikube with sufficient resources
minikube start --cpus=4 --memory=8192 --driver=docker

# Enable ingress addon (optional, for ingress-based access)
minikube addons enable ingress

# Verify Minikube is running
minikube status
```

---

## Step 2: Add Helm Repositories

```bash
# Add Gravitee Helm repository
helm repo add graviteeio https://helm.gravitee.io

# Add Bitnami repository (for MongoDB)
helm repo add bitnami https://charts.bitnami.com/bitnami

# Add Elastic repository (for Elasticsearch)
helm repo add elastic https://helm.elastic.co

# Update repositories
helm repo update
```

---

## Step 3: Create Namespace

```bash
kubectl create namespace gravitee
```

---

## Step 4: Install MongoDB

```bash
helm install mongodb bitnami/mongodb \
  --namespace gravitee \
  --set auth.enabled=true \
  --set auth.rootUser=root \
  --set auth.rootPassword=rootpassword \
  --set auth.username=gravitee \
  --set auth.password=gravitee123 \
  --set auth.database=gravitee \
  --set persistence.size=8Gi
```

### Wait for MongoDB to be ready

```bash
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=mongodb \
  -n gravitee --timeout=300s
```

### Verify MongoDB

```bash
kubectl get pods -n gravitee -l app.kubernetes.io/name=mongodb
```

---

## Step 5: Install Elasticsearch

We use a simple Elasticsearch 7.x deployment (without security) for compatibility with Gravitee:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elasticsearch
  namespace: gravitee
spec:
  replicas: 1
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
    spec:
      containers:
      - name: elasticsearch
        image: docker.elastic.co/elasticsearch/elasticsearch:7.17.9
        ports:
        - containerPort: 9200
        - containerPort: 9300
        env:
        - name: discovery.type
          value: single-node
        - name: xpack.security.enabled
          value: "false"
        - name: ES_JAVA_OPTS
          value: "-Xms512m -Xmx512m"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: elasticsearch-master
  namespace: gravitee
spec:
  selector:
    app: elasticsearch
  ports:
  - port: 9200
    targetPort: 9200
    name: http
  - port: 9300
    targetPort: 9300
    name: transport
EOF
```

### Wait for Elasticsearch to be ready

```bash
kubectl wait --for=condition=ready pod -l app=elasticsearch \
  -n gravitee --timeout=300s
```

### Verify Elasticsearch

```bash
kubectl exec -it deployment/elasticsearch -n gravitee -- \
  curl -s 'http://localhost:9200/_cluster/health?pretty'
```

Expected output should show `"status" : "green"`.

---

## Step 6: Install Gravitee APIM

### Create values file

```bash
cat <<EOF > /tmp/gravitee-values.yaml
mongo:
  enabled: false
  uri: "mongodb://gravitee:gravitee123@mongodb.gravitee.svc.cluster.local:27017/gravitee?authSource=gravitee"

es:
  enabled: false
  endpoints:
    - http://elasticsearch-master.gravitee.svc.cluster.local:9200
  security:
    enabled: false
  ssl:
    enabled: false

installation:
  type: standalone
  api:
    url: http://localhost:8080/management
  standalone:
    console:
      url: http://localhost:8080
    portal:
      url: http://localhost:8080

gateway:
  replicaCount: 1
  ingress:
    enabled: false

api:
  replicaCount: 1
  ingress:
    enabled: false

ui:
  replicaCount: 1
  ingress:
    enabled: false
  baseURL: http://localhost:8080/management

portal:
  replicaCount: 1
  ingress:
    enabled: false
EOF
```

### Install Gravitee APIM

```bash
helm install gravitee-apim graviteeio/apim \
  --namespace gravitee \
  -f /tmp/gravitee-values.yaml
```

### Wait for all pods to be ready

```bash
kubectl get pods -n gravitee -w
```

Wait until all pods show `READY 1/1` and `STATUS Running`.

---

## Step 7: Setup Nginx Proxy

The Gravitee UI requires specific configuration to work with port forwarding. We deploy an Nginx proxy to handle path rewriting:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-proxy-config
  namespace: gravitee
data:
  nginx.conf: |
    server {
        listen 8080;
        
        location / {
            proxy_pass http://gravitee-apim-ui:8002/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            sub_filter '<base href="/console/">' '<base href="/">';
            sub_filter '"baseURL": "http://localhost:8083/management"' '"baseURL": "/management"';
            sub_filter_once off;
            sub_filter_types text/html application/json;
        }
        
        location /management/ {
            proxy_pass http://gravitee-apim-api:83/management/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header Origin http://localhost:8080;
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gravitee-proxy
  namespace: gravitee
spec:
  replicas: 1
  selector:
    matchLabels:
      app: gravitee-proxy
  template:
    metadata:
      labels:
        app: gravitee-proxy
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: config
          mountPath: /etc/nginx/conf.d/default.conf
          subPath: nginx.conf
      volumes:
      - name: config
        configMap:
          name: nginx-proxy-config
---
apiVersion: v1
kind: Service
metadata:
  name: gravitee-proxy
  namespace: gravitee
spec:
  selector:
    app: gravitee-proxy
  ports:
  - port: 8080
    targetPort: 8080
EOF
```

### Wait for proxy to be ready

```bash
kubectl wait --for=condition=ready pod -l app=gravitee-proxy \
  -n gravitee --timeout=120s
```

---

## Step 8: Access Gravitee Console

### Start Port Forwarding

```bash
# Forward the proxy (Console + API)
kubectl port-forward svc/gravitee-proxy 8080:8080 -n gravitee &

# Forward the Gateway
kubectl port-forward svc/gravitee-apim-gateway 8082:82 -n gravitee &
```

### Access URLs

| Component | URL | Credentials |
|-----------|-----|-------------|
| **Management Console** | http://localhost:8080 | `admin` / `admin` |
| **Gateway** | http://localhost:8082 | - |

### Login

1. Open browser: http://localhost:8080
2. Login with:
   - **Username**: `admin`
   - **Password**: `admin`

---

## Step 9: Configure Primary Owner Group (Required for API Import)

When importing OpenAPI specifications, you may encounter this error:

```
User must belongs to at least one group with a primary owner member.
```

This happens because Gravitee requires users to belong to a group with PRIMARY_OWNER role before they can create/import APIs.

### Create API Owners Group

```bash
# Create a new group called "API Owners"
curl -s -X POST -u admin:admin \
  -H "Content-Type: application/json" \
  http://localhost:8080/management/organizations/DEFAULT/environments/DEFAULT/configuration/groups \
  -d '{
    "name": "API Owners",
    "event_rules": [],
    "lock_api_role": false,
    "lock_application_role": false,
    "system_invitation": false,
    "email_invitation": false,
    "disable_membership_notifications": false
  }'
```

### Get the Group ID

```bash
# List all groups and find the API Owners group ID
curl -s -u admin:admin \
  http://localhost:8080/management/organizations/DEFAULT/environments/DEFAULT/configuration/groups | python3 -m json.tool
```

Note the `id` field for "API Owners" group (e.g., `d4dca82a-32ec-429d-9ca8-2a32ecc29d87`).

### Get the Admin User ID

```bash
# Get the current user (admin) ID
curl -s -u admin:admin \
  http://localhost:8080/management/organizations/DEFAULT/user | python3 -m json.tool | grep '"id"'
```

Note the `id` field (e.g., `29c5dd2b-e3ca-47aa-85dd-2be3caa7aa6b`).

### Add Admin User to Group with PRIMARY_OWNER Role

```bash
# Replace GROUP_ID and USER_ID with your actual values
GROUP_ID="<your-group-id>"
USER_ID="<your-user-id>"

curl -s -X POST -u admin:admin \
  -H "Content-Type: application/json" \
  "http://localhost:8080/management/organizations/DEFAULT/environments/DEFAULT/configuration/groups/${GROUP_ID}/members" \
  -d "[{
    \"id\": \"${USER_ID}\",
    \"roles\": [{
      \"scope\": \"API\",
      \"name\": \"PRIMARY_OWNER\"
    }]
  }]"
```

### Verify Group Membership

```bash
# Verify the user was added with PRIMARY_OWNER role
curl -s -u admin:admin \
  "http://localhost:8080/management/organizations/DEFAULT/environments/DEFAULT/configuration/groups/${GROUP_ID}/members" | python3 -m json.tool
```

Expected output:
```json
[
    {
        "id": "29c5dd2b-e3ca-47aa-85dd-2be3caa7aa6b",
        "displayName": "admin",
        "roles": {
            "API": "PRIMARY_OWNER"
        }
    }
]
```

### Alternative: Using the Console UI

1. Go to **Settings** (gear icon) → **Organization** → **Groups**
2. Click **+ Add Group**
3. Name it "API Owners"
4. Save the group
5. Click on the group to edit it
6. Go to **Members** tab
7. Click **+ Add Member**
8. Search for "admin" and add with **PRIMARY_OWNER** role
9. Save

### After Configuration

1. **Log out** from the console
2. **Log back in** with `admin` / `admin`
3. Try importing your OpenAPI YAML again - it should work now!

---

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n gravitee
```

### Check Pod Logs

```bash
# API logs
kubectl logs deployment/gravitee-apim-api -n gravitee --tail=50

# Gateway logs
kubectl logs deployment/gravitee-apim-gateway -n gravitee --tail=50

# UI logs
kubectl logs deployment/gravitee-apim-ui -n gravitee --tail=50

# Proxy logs
kubectl logs deployment/gravitee-proxy -n gravitee --tail=50
```

### Check Elasticsearch Health

```bash
kubectl exec -it deployment/elasticsearch -n gravitee -- \
  curl -s 'http://localhost:9200/_cluster/health?pretty'
```

### Check MongoDB Connection

```bash
kubectl exec -it deployment/mongodb -n gravitee -- \
  mongosh -u gravitee -p gravitee123 --authenticationDatabase gravitee
```

### Test Management API

```bash
curl -s http://localhost:8080/management/organizations/DEFAULT/console | head -10
```

### Port Forward Issues

If port forwarding stops working:

```bash
# Kill existing port forwards
pkill -f "kubectl port-forward"

# Restart port forwards
kubectl port-forward svc/gravitee-proxy 8080:8080 -n gravitee &
kubectl port-forward svc/gravitee-apim-gateway 8082:82 -n gravitee &
```

### Console Loading Issues

If the console is stuck on loading:

1. **Clear browser cache** or use **incognito mode**
2. Check proxy logs: `kubectl logs deployment/gravitee-proxy -n gravitee`
3. Verify API is responding: `curl http://localhost:8080/management/v2/ui/bootstrap`

### Elasticsearch Connection Issues

If Gravitee can't connect to Elasticsearch:

```bash
# Check Elasticsearch service
kubectl get svc elasticsearch-master -n gravitee

# Check endpoints
kubectl get endpoints elasticsearch-master -n gravitee

# Test connectivity from API pod
kubectl exec -it deployment/gravitee-apim-api -n gravitee -- \
  curl -s http://elasticsearch-master:9200/_cluster/health
```

### API Import Error: "User must belongs to at least one group with a primary owner member"

This error occurs when trying to import an OpenAPI specification. The admin user needs to be part of a group with PRIMARY_OWNER role.

**Solution:**

See [Step 9: Configure Primary Owner Group](#step-9-configure-primary-owner-group-required-for-api-import) for detailed instructions.

**Quick Fix via API:**

```bash
# 1. Create group
curl -s -X POST -u admin:admin \
  -H "Content-Type: application/json" \
  http://localhost:8080/management/organizations/DEFAULT/environments/DEFAULT/configuration/groups \
  -d '{"name": "API Owners"}'

# 2. Get group ID
GROUP_ID=$(curl -s -u admin:admin \
  http://localhost:8080/management/organizations/DEFAULT/environments/DEFAULT/configuration/groups | \
  python3 -c "import sys,json; groups=json.load(sys.stdin); print([g['id'] for g in groups if g['name']=='API Owners'][0])")

# 3. Get user ID
USER_ID=$(curl -s -u admin:admin \
  http://localhost:8080/management/organizations/DEFAULT/user | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 4. Add user to group with PRIMARY_OWNER role
curl -s -X POST -u admin:admin \
  -H "Content-Type: application/json" \
  "http://localhost:8080/management/organizations/DEFAULT/environments/DEFAULT/configuration/groups/${GROUP_ID}/members" \
  -d "[{\"id\": \"${USER_ID}\", \"roles\": [{\"scope\": \"API\", \"name\": \"PRIMARY_OWNER\"}]}]"

echo "Done! Log out and log back in, then try importing again."
```

---

## Cleanup

### Uninstall Gravitee APIM

```bash
helm uninstall gravitee-apim -n gravitee
```

### Delete Proxy

```bash
kubectl delete deployment gravitee-proxy -n gravitee
kubectl delete svc gravitee-proxy -n gravitee
kubectl delete configmap nginx-proxy-config -n gravitee
```

### Delete Elasticsearch

```bash
kubectl delete deployment elasticsearch -n gravitee
kubectl delete svc elasticsearch-master -n gravitee
```

### Uninstall MongoDB

```bash
helm uninstall mongodb -n gravitee
```

### Delete Namespace

```bash
kubectl delete namespace gravitee
```

### Stop Minikube

```bash
minikube stop

# Or delete completely
minikube delete
```

---

## Quick Reference

### Helm Releases

```bash
helm list -n gravitee
```

### All Resources

```bash
kubectl get all -n gravitee
```

### Services

```bash
kubectl get svc -n gravitee
```

### Persistent Volume Claims

```bash
kubectl get pvc -n gravitee
```

---

## Component Versions

| Component | Version |
|-----------|---------|
| Gravitee APIM | 4.9.10 |
| MongoDB | 8.2.3 (Bitnami Chart 18.1.20) |
| Elasticsearch | 7.17.9 |
| Nginx | Alpine (latest) |

---

## Step 10: Setup Keycloak Authorization Server (Optional)

To secure your APIs with OAuth2/OpenID Connect, deploy Keycloak as the Authorization Server.

### Deploy Keycloak

```bash
# Apply Keycloak manifests
kubectl apply -f gravitee-setup/manifests/keycloak/keycloak.yaml

# Wait for Keycloak to be ready (~2 minutes)
kubectl wait --for=condition=ready pod -l app=keycloak -n gravitee --timeout=300s

# Start port forwarding
kubectl port-forward svc/keycloak 8180:8080 -n gravitee &
```

### Access Keycloak

| URL | Purpose | Credentials |
|-----|---------|-------------|
| http://localhost:8180/admin | Admin Console | admin / admin123 |
| http://localhost:8180/realms/gravitee | Gravitee Realm | - |

### Pre-configured Clients

| Client ID | Purpose | Secret |
|-----------|---------|--------|
| `gravitee-gateway` | Token validation | `gravitee-gateway-secret` |
| `api-client` | API consumer app | `api-client-secret` |

### Pre-configured Users

| Username | Password | Roles |
|----------|----------|-------|
| `apiuser` | `apiuser123` | user |
| `apiadmin` | `apiadmin123` | admin |

### Get an Access Token

```bash
curl -s -X POST "http://localhost:8180/realms/gravitee/protocol/openid-connect/token" \
  -d "client_id=api-client" \
  -d "client_secret=api-client-secret" \
  -d "username=apiuser" \
  -d "password=apiuser123" \
  -d "grant_type=password" | jq .
```

For detailed Keycloak integration guide, see [KEYCLOAK_INTEGRATION_GUIDE.md](KEYCLOAK_INTEGRATION_GUIDE.md).

---

## Next Steps

After successful setup:

1. **Create your first API** in the Management Console
2. **Configure API Plans** for access control (API Key or OAuth2)
3. **Deploy APIs** to the Gateway
4. **Secure APIs with OAuth2** using Keycloak (see [Keycloak Integration Guide](KEYCLOAK_INTEGRATION_GUIDE.md))
5. **Set up GKO** (Gravitee Kubernetes Operator) for GitOps workflows

See [GitOps Guide](GITOPS_GUIDE.md) for managing APIs using Kubernetes CRDs.

