#!/bin/bash
# Validate GKO CRDs
# Checks YAML syntax and schema compliance

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CICD_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }

ERRORS=0

# Validate YAML syntax
validate_yaml() {
    echo "Validating YAML syntax..."
    
    find "$CICD_DIR" -name "*.yaml" -o -name "*.yml" | while read -r file; do
        if ! python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            print_error "Invalid YAML: $file"
            ((ERRORS++))
        fi
    done
    
    if [ $ERRORS -eq 0 ]; then
        print_success "All YAML files are valid"
    fi
}

# Validate Kustomize
validate_kustomize() {
    echo ""
    echo "Validating Kustomize builds..."
    
    for env in dev uat prod; do
        if [ -d "$CICD_DIR/environments/$env" ]; then
            if kustomize build "$CICD_DIR/environments/$env" > /dev/null 2>&1; then
                print_success "Kustomize build: $env"
            else
                print_error "Kustomize build failed: $env"
                ((ERRORS++))
            fi
        fi
    done
}

# Check for required fields in API definitions
validate_api_definitions() {
    echo ""
    echo "Validating API definitions..."
    
    find "$CICD_DIR/gko/crds" -name "*.yaml" | while read -r file; do
        # Check for required fields
        if grep -q "kind: ApiV4Definition" "$file"; then
            # Check contextRef
            if ! grep -q "contextRef:" "$file"; then
                print_warning "Missing contextRef in $file"
            fi
            
            # Check name
            if ! grep -q "name:" "$file"; then
                print_error "Missing name in $file"
                ((ERRORS++))
            fi
            
            # Check listeners
            if ! grep -q "listeners:" "$file"; then
                print_warning "Missing listeners in $file"
            fi
            
            print_success "Validated: $(basename $file)"
        fi
    done
}

# Check for sensitive data
check_sensitive_data() {
    echo ""
    echo "Checking for sensitive data..."
    
    SENSITIVE_PATTERNS=(
        "password:"
        "secret:"
        "apikey:"
        "token:"
        "credential:"
    )
    
    for pattern in "${SENSITIVE_PATTERNS[@]}"; do
        matches=$(grep -r -i "$pattern" "$CICD_DIR" --include="*.yaml" 2>/dev/null | grep -v "secretRef" | grep -v "#" || true)
        if [ -n "$matches" ]; then
            print_warning "Potential sensitive data found for pattern '$pattern':"
            echo "$matches" | head -5
        fi
    done
}

# Main
main() {
    echo "========================================"
    echo "GKO CRD Validation"
    echo "========================================"
    echo ""
    
    validate_yaml
    validate_kustomize
    validate_api_definitions
    check_sensitive_data
    
    echo ""
    echo "========================================"
    if [ $ERRORS -eq 0 ]; then
        print_success "All validations passed!"
        exit 0
    else
        print_error "Validation failed with $ERRORS errors"
        exit 1
    fi
}

main "$@"

