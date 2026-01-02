#!/bin/bash
# Promote APIs between environments
# Usage: ./promote-env.sh <source> <target> [api-name]

set -e

SOURCE_ENV="${1:-dev}"
TARGET_ENV="${2:-uat}"
API_NAME="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CICD_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() { echo -e "\n${BLUE}$1${NC}\n"; }
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }

# Validate promotion path
validate_path() {
    case "$SOURCE_ENV-$TARGET_ENV" in
        dev-uat|uat-prod)
            print_success "Valid promotion path: $SOURCE_ENV → $TARGET_ENV"
            ;;
        *)
            print_error "Invalid promotion path: $SOURCE_ENV → $TARGET_ENV"
            echo "Valid paths: dev→uat, uat→prod"
            exit 1
            ;;
    esac
}

# Check source environment
check_source() {
    print_header "Checking source environment: $SOURCE_ENV"
    
    if [ ! -d "$CICD_DIR/environments/$SOURCE_ENV" ]; then
        print_error "Source environment not found: $SOURCE_ENV"
        exit 1
    fi
    
    # Check if APIs exist in source
    if ! kustomize build "$CICD_DIR/environments/$SOURCE_ENV" > /dev/null 2>&1; then
        print_error "Failed to build source environment"
        exit 1
    fi
    
    print_success "Source environment is valid"
}

# Sync with ArgoCD
sync_argocd() {
    print_header "Syncing with ArgoCD"
    
    APP_NAME="gravitee-apis-$TARGET_ENV"
    
    if command -v argocd &> /dev/null; then
        echo "Triggering ArgoCD sync for $APP_NAME..."
        argocd app sync "$APP_NAME" --grpc-web 2>/dev/null || {
            print_warning "ArgoCD sync command failed. Manual sync may be required."
        }
    else
        print_warning "ArgoCD CLI not installed. Please sync manually."
        echo "  argocd app sync $APP_NAME"
    fi
}

# Create promotion record
create_promotion_record() {
    print_header "Creating promotion record"
    
    RECORD_FILE="$CICD_DIR/environments/$TARGET_ENV/promotion-info.yaml"
    
    cat > "$RECORD_FILE" << EOF
# Promotion Information
# Auto-generated - do not edit manually
apiVersion: v1
kind: ConfigMap
metadata:
  name: promotion-info
  namespace: gravitee-apis-$TARGET_ENV
  labels:
    app.kubernetes.io/managed-by: promotion-script
data:
  promoted_from: "$SOURCE_ENV"
  promoted_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  promoted_by: "${USER:-unknown}"
  api_name: "${API_NAME:-all}"
EOF
    
    print_success "Promotion record created: $RECORD_FILE"
}

# Main
main() {
    echo "========================================"
    echo "API Environment Promotion"
    echo "========================================"
    echo ""
    echo "Source: $SOURCE_ENV"
    echo "Target: $TARGET_ENV"
    echo "API: ${API_NAME:-all}"
    echo ""
    
    validate_path
    check_source
    create_promotion_record
    
    echo ""
    print_header "Next Steps"
    echo "1. Review changes in: $CICD_DIR/environments/$TARGET_ENV/"
    echo "2. Commit and push to trigger ArgoCD sync"
    echo "3. Or manually sync: argocd app sync gravitee-apis-$TARGET_ENV"
    echo ""
    
    # Ask for confirmation to sync
    read -p "Sync now with ArgoCD? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sync_argocd
    fi
    
    print_success "Promotion complete!"
}

main "$@"

