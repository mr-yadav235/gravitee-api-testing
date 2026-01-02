#!/bin/bash
# CI/CD Setup Script
# Installs ArgoCD and GKO on the current Kubernetes cluster

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CICD_DIR="$(dirname "$SCRIPT_DIR")"

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    command -v kubectl &> /dev/null || { print_error "kubectl not found"; exit 1; }
    print_success "kubectl installed"
    
    command -v helm &> /dev/null || { print_error "helm not found"; exit 1; }
    print_success "helm installed"
    
    kubectl cluster-info &> /dev/null || { print_error "Cannot connect to cluster"; exit 1; }
    print_success "Connected to Kubernetes cluster"
}

# Install ArgoCD
install_argocd() {
    print_header "Installing ArgoCD"
    
    kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
    
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.3/manifests/install.yaml
    
    echo "Waiting for ArgoCD to be ready..."
    kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s
    
    # Apply custom configurations
    kubectl apply -f "$CICD_DIR/argocd/install.yaml"
    
    print_success "ArgoCD installed"
    
    echo ""
    echo "ArgoCD Admin Password:"
    kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
    echo ""
}

# Install GKO
install_gko() {
    print_header "Installing Gravitee Kubernetes Operator"
    
    helm repo add graviteeio https://helm.gravitee.io
    helm repo update
    
    kubectl create namespace gravitee-gko --dry-run=client -o yaml | kubectl apply -f -
    
    helm upgrade --install gravitee-gko graviteeio/gko \
        --namespace gravitee-gko \
        --set manager.scope.cluster=true \
        --wait --timeout 5m
    
    print_success "GKO installed"
    
    echo ""
    echo "GKO CRDs:"
    kubectl get crds | grep gravitee
}

# Create namespaces
create_namespaces() {
    print_header "Creating API Namespaces"
    
    for env in dev uat prod; do
        kubectl apply -f "$CICD_DIR/environments/$env/namespace.yaml"
        print_success "Created gravitee-apis-$env"
    done
}

# Apply Management Context
apply_management_context() {
    print_header "Applying Management Context"
    
    kubectl apply -f "$CICD_DIR/gko/management-context.yaml"
    print_success "Management Context created"
}

# Apply ArgoCD Project and ApplicationSet
apply_argocd_apps() {
    print_header "Applying ArgoCD Applications"
    
    kubectl apply -f "$CICD_DIR/argocd/project.yaml"
    print_success "ArgoCD Project created"
    
    kubectl apply -f "$CICD_DIR/argocd/application-set.yaml"
    print_success "ArgoCD ApplicationSet created"
}

# Setup port forwards
setup_port_forwards() {
    print_header "Setting up Port Forwards"
    
    pkill -f "port-forward.*argocd" 2>/dev/null || true
    
    kubectl port-forward svc/argocd-server -n argocd 8443:443 &
    sleep 2
    
    print_success "ArgoCD UI: https://localhost:8443"
}

# Print summary
print_summary() {
    print_header "Setup Complete!"
    
    echo "Components Installed:"
    echo "  ✓ ArgoCD"
    echo "  ✓ Gravitee Kubernetes Operator"
    echo ""
    echo "Namespaces Created:"
    echo "  ✓ argocd"
    echo "  ✓ gravitee-gko"
    echo "  ✓ gravitee-apis-dev"
    echo "  ✓ gravitee-apis-uat"
    echo "  ✓ gravitee-apis-prod"
    echo ""
    echo "Access:"
    echo "  ArgoCD UI: https://localhost:8443"
    echo "  Username: admin"
    echo -n "  Password: "
    kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
    echo ""
    echo ""
    echo "Next Steps:"
    echo "  1. Deploy Gravitee APIM (if not already deployed)"
    echo "  2. Update management-context.yaml with correct APIM URL"
    echo "  3. Push API definitions to GitHub"
    echo "  4. ArgoCD will automatically sync"
}

# Main
main() {
    print_header "CI/CD Setup for Gravitee APIs"
    
    check_prerequisites
    install_argocd
    install_gko
    create_namespaces
    apply_management_context
    apply_argocd_apps
    setup_port_forwards
    print_summary
}

main "$@"

