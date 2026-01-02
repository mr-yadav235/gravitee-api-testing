#!/bin/bash
# Gravitee APIM Setup Script for Minikube
# Usage: ./setup.sh [start|stop|status|clean]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFESTS_DIR="$SCRIPT_DIR/../manifests"
VALUES_DIR="$SCRIPT_DIR/../values"
NAMESPACE="gravitee"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v minikube &> /dev/null; then
        log_error "minikube is not installed. Please install it first."
        exit 1
    fi
    
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed. Please install it first."
        exit 1
    fi
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install it first."
        exit 1
    fi
    
    log_info "All prerequisites are installed."
}

start_minikube() {
    log_info "Starting Minikube..."
    
    if minikube status | grep -q "Running"; then
        log_info "Minikube is already running."
    else
        minikube start --cpus=4 --memory=8192 --driver=docker
        minikube addons enable ingress
    fi
}

add_helm_repos() {
    log_info "Adding Helm repositories..."
    
    helm repo add graviteeio https://helm.gravitee.io 2>/dev/null || true
    helm repo add bitnami https://charts.bitnami.com/bitnami 2>/dev/null || true
    helm repo update
}

create_namespace() {
    log_info "Creating namespace..."
    
    kubectl apply -f "$MANIFESTS_DIR/namespace.yaml"
}

install_mongodb() {
    log_info "Installing MongoDB..."
    
    if helm status mongodb -n $NAMESPACE &> /dev/null; then
        log_info "MongoDB is already installed."
    else
        helm install mongodb bitnami/mongodb \
            --namespace $NAMESPACE \
            --set auth.enabled=true \
            --set auth.rootUser=root \
            --set auth.rootPassword=rootpassword \
            --set auth.username=gravitee \
            --set auth.password=gravitee123 \
            --set auth.database=gravitee \
            --set persistence.size=8Gi
    fi
    
    log_info "Waiting for MongoDB to be ready..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=mongodb \
        -n $NAMESPACE --timeout=300s
}

install_elasticsearch() {
    log_info "Installing Elasticsearch..."
    
    kubectl apply -f "$MANIFESTS_DIR/elasticsearch.yaml"
    
    log_info "Waiting for Elasticsearch to be ready..."
    kubectl wait --for=condition=ready pod -l app=elasticsearch \
        -n $NAMESPACE --timeout=300s
}

install_gravitee() {
    log_info "Installing Gravitee APIM..."
    
    if helm status gravitee-apim -n $NAMESPACE &> /dev/null; then
        log_info "Gravitee APIM is already installed. Upgrading..."
        helm upgrade gravitee-apim graviteeio/apim \
            --namespace $NAMESPACE \
            -f "$VALUES_DIR/gravitee-values.yaml"
    else
        helm install gravitee-apim graviteeio/apim \
            --namespace $NAMESPACE \
            -f "$VALUES_DIR/gravitee-values.yaml"
    fi
    
    log_info "Waiting for Gravitee pods to be ready..."
    sleep 30
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=gravitee-apim \
        -n $NAMESPACE --timeout=300s || true
}

install_proxy() {
    log_info "Installing Nginx Proxy..."
    
    kubectl apply -f "$MANIFESTS_DIR/nginx-proxy.yaml"
    
    log_info "Waiting for Proxy to be ready..."
    kubectl wait --for=condition=ready pod -l app=gravitee-proxy \
        -n $NAMESPACE --timeout=120s
}

start_port_forward() {
    log_info "Starting port forwarding..."
    
    # Kill existing port forwards
    pkill -f "kubectl port-forward.*gravitee" 2>/dev/null || true
    sleep 2
    
    # Start port forwards
    kubectl port-forward svc/gravitee-proxy 8080:8080 -n $NAMESPACE > /dev/null 2>&1 &
    kubectl port-forward svc/gravitee-apim-gateway 8082:82 -n $NAMESPACE > /dev/null 2>&1 &
    
    sleep 3
    
    log_info "Port forwarding started!"
    echo ""
    echo "=============================================="
    echo "  Gravitee APIM is ready!"
    echo "=============================================="
    echo ""
    echo "  Console: http://localhost:8080"
    echo "  Gateway: http://localhost:8082"
    echo ""
    echo "  Login: admin / admin"
    echo ""
    echo "=============================================="
}

show_status() {
    log_info "Checking status..."
    echo ""
    
    echo "=== Minikube Status ==="
    minikube status || true
    echo ""
    
    echo "=== Pods ==="
    kubectl get pods -n $NAMESPACE
    echo ""
    
    echo "=== Services ==="
    kubectl get svc -n $NAMESPACE
    echo ""
    
    echo "=== Port Forwards ==="
    ps aux | grep "kubectl port-forward" | grep -v grep || echo "No port forwards running"
}

stop_services() {
    log_info "Stopping port forwards..."
    pkill -f "kubectl port-forward.*gravitee" 2>/dev/null || true
    log_info "Port forwards stopped."
}

cleanup() {
    log_warn "This will delete all Gravitee resources!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleaning up..."
        
        # Stop port forwards
        pkill -f "kubectl port-forward.*gravitee" 2>/dev/null || true
        
        # Delete proxy
        kubectl delete -f "$MANIFESTS_DIR/nginx-proxy.yaml" 2>/dev/null || true
        
        # Uninstall Gravitee
        helm uninstall gravitee-apim -n $NAMESPACE 2>/dev/null || true
        
        # Delete Elasticsearch
        kubectl delete -f "$MANIFESTS_DIR/elasticsearch.yaml" 2>/dev/null || true
        
        # Uninstall MongoDB
        helm uninstall mongodb -n $NAMESPACE 2>/dev/null || true
        
        # Delete namespace
        kubectl delete namespace $NAMESPACE 2>/dev/null || true
        
        log_info "Cleanup complete!"
    else
        log_info "Cleanup cancelled."
    fi
}

# Main
case "${1:-start}" in
    start)
        check_prerequisites
        start_minikube
        add_helm_repos
        create_namespace
        install_mongodb
        install_elasticsearch
        install_gravitee
        install_proxy
        start_port_forward
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    clean)
        cleanup
        ;;
    port-forward)
        start_port_forward
        ;;
    *)
        echo "Usage: $0 {start|stop|status|clean|port-forward}"
        exit 1
        ;;
esac

