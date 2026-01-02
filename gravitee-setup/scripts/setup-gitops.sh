#!/bin/bash
# GitOps Setup Script - ArgoCD + Gravitee Kubernetes Operator (GKO)
# This script sets up a complete GitOps pipeline for Gravitee API management

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ARGOCD_VERSION="v2.13.3"
GKO_VERSION="4.9.10"
GITHUB_REPO="${GITHUB_REPO:-}"  # Set via environment variable

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

wait_for_pods() {
    local namespace=$1
    local label=$2
    local timeout=${3:-300}
    
    echo "Waiting for pods in $namespace with label $label..."
    kubectl wait --for=condition=ready pod -l "$label" -n "$namespace" --timeout="${timeout}s" 2>/dev/null || {
        print_warning "Timeout waiting for pods, checking status..."
        kubectl get pods -n "$namespace" -l "$label"
    }
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed"
        exit 1
    fi
    print_success "kubectl installed"
    
    # Check helm
    if ! command -v helm &> /dev/null; then
        print_error "helm is not installed"
        exit 1
    fi
    print_success "helm installed"
    
    # Check minikube
    if ! command -v minikube &> /dev/null; then
        print_error "minikube is not installed"
        exit 1
    fi
    print_success "minikube installed"
    
    # Check minikube status
    if ! minikube status &> /dev/null; then
        print_error "minikube is not running. Start it with: minikube start --memory=8192 --cpus=6"
        exit 1
    fi
    print_success "minikube is running"
    
    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    print_success "Connected to Kubernetes cluster"
}

# Install ArgoCD
install_argocd() {
    print_header "Installing ArgoCD"
    
    # Create namespace
    kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
    print_success "Created argocd namespace"
    
    # Install ArgoCD
    echo "Installing ArgoCD ${ARGOCD_VERSION}..."
    kubectl apply -n argocd -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"
    print_success "ArgoCD manifests applied"
    
    # Wait for ArgoCD to be ready
    echo "Waiting for ArgoCD pods to be ready (this may take a few minutes)..."
    sleep 10
    wait_for_pods "argocd" "app.kubernetes.io/name=argocd-server" 300
    
    # Get initial admin password
    echo ""
    echo "ArgoCD initial admin password:"
    kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>/dev/null | base64 -d || echo "Password not yet available"
    echo ""
    
    print_success "ArgoCD installed successfully"
}

# Install ArgoCD CLI (optional)
install_argocd_cli() {
    print_header "Installing ArgoCD CLI"
    
    if command -v argocd &> /dev/null; then
        print_success "ArgoCD CLI already installed"
        return
    fi
    
    # Detect OS
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        ARCH="arm64"
    else
        ARCH="amd64"
    fi
    
    echo "Downloading ArgoCD CLI for ${OS}/${ARCH}..."
    curl -sSL -o /tmp/argocd "https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_VERSION}/argocd-${OS}-${ARCH}"
    
    if [ -w /usr/local/bin ]; then
        sudo install -m 555 /tmp/argocd /usr/local/bin/argocd
    else
        print_warning "Cannot write to /usr/local/bin. Installing to ~/.local/bin"
        mkdir -p ~/.local/bin
        install -m 555 /tmp/argocd ~/.local/bin/argocd
        echo "Add ~/.local/bin to your PATH if not already done"
    fi
    
    rm /tmp/argocd
    print_success "ArgoCD CLI installed"
}

# Install Gravitee Kubernetes Operator
install_gko() {
    print_header "Installing Gravitee Kubernetes Operator (GKO)"
    
    # Add Gravitee Helm repo
    echo "Adding Gravitee Helm repository..."
    helm repo add graviteeio https://helm.gravitee.io
    helm repo update
    print_success "Gravitee Helm repo added"
    
    # Create namespace for GKO
    kubectl create namespace gravitee-gko --dry-run=client -o yaml | kubectl apply -f -
    print_success "Created gravitee-gko namespace"
    
    # Install GKO
    echo "Installing GKO ${GKO_VERSION}..."
    helm upgrade --install gravitee-gko graviteeio/gko \
        --namespace gravitee-gko \
        --version "${GKO_VERSION}" \
        --set manager.scope.cluster=true \
        --wait --timeout 5m
    
    print_success "GKO installed successfully"
    
    # Verify CRDs are installed
    echo ""
    echo "Installed GKO CRDs:"
    kubectl get crds | grep gravitee || echo "No Gravitee CRDs found yet"
}

# Create namespaces for API environments
create_api_namespaces() {
    print_header "Creating API Namespaces"
    
    for env in dev uat prod; do
        kubectl create namespace "gravitee-apis-${env}" --dry-run=client -o yaml | kubectl apply -f -
        print_success "Created gravitee-apis-${env} namespace"
    done
}

# Setup GitHub repository connection (if provided)
setup_github_repo() {
    print_header "Setting up GitHub Repository"
    
    if [ -z "$GITHUB_REPO" ]; then
        print_warning "GITHUB_REPO not set. Skipping GitHub setup."
        echo "To connect to a GitHub repo later, run:"
        echo "  export GITHUB_REPO=https://github.com/your-org/your-repo.git"
        echo "  argocd repo add \$GITHUB_REPO --username <user> --password <token>"
        return
    fi
    
    echo "Repository: $GITHUB_REPO"
    
    # Create repository secret
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: github-repo-creds
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: ${GITHUB_REPO}
  # Add your credentials here or use SSH key
  # username: your-username
  # password: your-token
EOF
    
    print_success "GitHub repository configured"
}

# Create Management Context for GKO
create_management_context() {
    print_header "Creating GKO Management Context"
    
    # Create secret for Gravitee admin credentials
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: gravitee-admin-credentials
  namespace: gravitee-gko
type: Opaque
stringData:
  GRAVITEE_USERNAME: admin
  GRAVITEE_PASSWORD: admin
EOF
    print_success "Created Gravitee admin credentials secret"
    
    # Create Management Context
    cat <<EOF | kubectl apply -f -
apiVersion: gravitee.io/v1alpha1
kind: ManagementContext
metadata:
  name: local-gravitee
  namespace: gravitee-gko
spec:
  baseUrl: http://gravitee-apim-api.gravitee.svc.cluster.local:83/management
  environmentId: DEFAULT
  organizationId: DEFAULT
  auth:
    secretRef:
      name: gravitee-admin-credentials
      namespace: gravitee-gko
    credentials:
      username: GRAVITEE_USERNAME
      password: GRAVITEE_PASSWORD
EOF
    print_success "Created Management Context"
}

# Create sample ArgoCD Application
create_sample_application() {
    print_header "Creating Sample ArgoCD Application"
    
    cat <<EOF | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: gravitee-apis-dev
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: ${GITHUB_REPO:-https://github.com/your-org/gravitee-api-testing-strategy.git}
    targetRevision: HEAD
    path: apis/overlays/dev
  destination:
    server: https://kubernetes.default.svc
    namespace: gravitee-apis-dev
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
EOF
    print_success "Created sample ArgoCD Application"
}

# Port forward for access
setup_port_forwards() {
    print_header "Setting up Port Forwards"
    
    # Kill existing port forwards
    pkill -f "port-forward.*argocd" 2>/dev/null || true
    
    echo "Starting ArgoCD port forward..."
    kubectl port-forward svc/argocd-server -n argocd 8443:443 &
    sleep 2
    
    print_success "ArgoCD available at: https://localhost:8443"
    echo ""
    echo "Login credentials:"
    echo "  Username: admin"
    echo -n "  Password: "
    kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>/dev/null | base64 -d
    echo ""
}

# Print summary
print_summary() {
    print_header "Setup Complete!"
    
    echo "Components installed:"
    echo "  ✓ ArgoCD ${ARGOCD_VERSION}"
    echo "  ✓ Gravitee Kubernetes Operator ${GKO_VERSION}"
    echo ""
    echo "Access Points:"
    echo "  ArgoCD UI: https://localhost:8443"
    echo ""
    echo "ArgoCD Login:"
    echo "  Username: admin"
    echo -n "  Password: "
    kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>/dev/null | base64 -d
    echo ""
    echo ""
    echo "Next Steps:"
    echo "  1. Access ArgoCD UI at https://localhost:8443"
    echo "  2. Connect your GitHub repository"
    echo "  3. Create API definitions as Kubernetes CRDs"
    echo "  4. ArgoCD will automatically sync them to Gravitee"
    echo ""
    echo "Useful commands:"
    echo "  kubectl get applications -n argocd"
    echo "  kubectl get apidefinitions -A"
    echo "  kubectl get managementcontexts -A"
    echo ""
    echo "GKO CRDs available:"
    kubectl get crds | grep gravitee || echo "  (None yet - GKO may still be starting)"
}

# Main execution
main() {
    print_header "GitOps Setup for Gravitee API Management"
    echo "This script will install:"
    echo "  - ArgoCD (GitOps continuous delivery)"
    echo "  - Gravitee Kubernetes Operator (GKO)"
    echo ""
    
    check_prerequisites
    install_argocd
    install_argocd_cli
    install_gko
    create_api_namespaces
    setup_github_repo
    create_management_context
    # create_sample_application  # Uncomment when GitHub repo is configured
    setup_port_forwards
    print_summary
}

# Run main function
main "$@"

