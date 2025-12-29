#!/usr/bin/env python3
"""
Validates Gravitee Kubernetes Operator (GKO) CRDs structure and content.
Ensures API definitions follow best practices and required fields are present.
"""

import sys
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


class GKOValidator:
    """Validator for Gravitee Kubernetes Operator CRDs."""
    
    REQUIRED_API_DEFINITION_FIELDS = [
        'spec.name',
        'spec.version',
        'spec.contextRef',
        'spec.proxy.virtualHosts',
        'spec.proxy.groups',
    ]
    
    REQUIRED_API_PLAN_FIELDS = [
        'spec.name',
        'spec.apiRef',
        'spec.contextRef',
        'spec.security',
        'spec.status',
    ]
    
    VALID_SECURITY_TYPES = ['API_KEY', 'JWT', 'OAUTH2', 'KEY_LESS', 'MTLS']
    VALID_LIFECYCLE_STATES = ['CREATED', 'PUBLISHED', 'UNPUBLISHED', 'DEPRECATED']
    VALID_PLAN_STATUSES = ['STAGING', 'PUBLISHED', 'DEPRECATED', 'CLOSED']
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_file(self, file_path: str) -> bool:
        """Validate a YAML file containing GKO CRDs."""
        try:
            with open(file_path, 'r') as f:
                documents = list(yaml.safe_load_all(f))
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error in {file_path}: {e}")
            return False
        
        for doc in documents:
            if doc is None:
                continue
            self._validate_document(doc, file_path)
        
        return len(self.errors) == 0
    
    def _validate_document(self, doc: Dict[str, Any], file_path: str) -> None:
        """Validate a single Kubernetes resource document."""
        if not isinstance(doc, dict):
            return
        
        api_version = doc.get('apiVersion', '')
        kind = doc.get('kind', '')
        
        if not api_version.startswith('gravitee.io/'):
            return  # Not a GKO CRD
        
        metadata = doc.get('metadata', {})
        name = metadata.get('name', 'unknown')
        
        if kind == 'ApiDefinition':
            self._validate_api_definition(doc, name, file_path)
        elif kind == 'ApiPlan':
            self._validate_api_plan(doc, name, file_path)
        elif kind == 'ManagementContext':
            self._validate_management_context(doc, name, file_path)
    
    def _validate_api_definition(self, doc: Dict[str, Any], name: str, file_path: str) -> None:
        """Validate ApiDefinition CRD."""
        spec = doc.get('spec', {})
        
        # Check required fields
        for field_path in self.REQUIRED_API_DEFINITION_FIELDS:
            if not self._get_nested_value(doc, field_path):
                self.errors.append(f"[{name}] Missing required field: {field_path}")
        
        # Validate version format
        version = spec.get('version', '')
        if version and not re.match(r'^\d+\.\d+\.\d+$', version):
            self.warnings.append(f"[{name}] Version '{version}' doesn't follow semver format")
        
        # Validate lifecycle state
        lifecycle_state = spec.get('lifecycleState')
        if lifecycle_state and lifecycle_state not in self.VALID_LIFECYCLE_STATES:
            self.errors.append(f"[{name}] Invalid lifecycleState: {lifecycle_state}")
        
        # Validate proxy configuration
        proxy = spec.get('proxy', {})
        virtual_hosts = proxy.get('virtualHosts', [])
        
        for vh in virtual_hosts:
            path = vh.get('path', '')
            if not path.startswith('/'):
                self.errors.append(f"[{name}] Virtual host path must start with '/': {path}")
        
        # Validate endpoint groups
        groups = proxy.get('groups', [])
        for group in groups:
            endpoints = group.get('endpoints', [])
            if not endpoints:
                self.warnings.append(f"[{name}] Endpoint group '{group.get('name', 'unknown')}' has no endpoints")
            
            for endpoint in endpoints:
                target = endpoint.get('target', '')
                if not target:
                    self.errors.append(f"[{name}] Endpoint missing target URL")
                elif not target.startswith(('http://', 'https://')):
                    self.warnings.append(f"[{name}] Endpoint target should be absolute URL: {target}")
        
        # Validate flows
        flows = spec.get('flows', [])
        for flow in flows:
            self._validate_flow(flow, name)
        
        # Validate analytics configuration
        analytics = spec.get('analytics', {})
        if analytics.get('enabled', False):
            logging = analytics.get('logging', {})
            if logging.get('content') == 'PAYLOADS':
                self.warnings.append(f"[{name}] Payload logging enabled - consider performance impact")
    
    def _validate_api_plan(self, doc: Dict[str, Any], name: str, file_path: str) -> None:
        """Validate ApiPlan CRD."""
        spec = doc.get('spec', {})
        
        # Check required fields
        for field_path in self.REQUIRED_API_PLAN_FIELDS:
            if not self._get_nested_value(doc, field_path):
                self.errors.append(f"[{name}] Missing required field: {field_path}")
        
        # Validate security type
        security = spec.get('security')
        if security and security not in self.VALID_SECURITY_TYPES:
            self.errors.append(f"[{name}] Invalid security type: {security}")
        
        # Validate plan status
        status = spec.get('status')
        if status and status not in self.VALID_PLAN_STATUSES:
            self.errors.append(f"[{name}] Invalid plan status: {status}")
        
        # Check for rate limiting in plans
        flows = spec.get('flows', [])
        has_rate_limit = False
        for flow in flows:
            for policy in flow.get('pre', []):
                if policy.get('policy') in ['rate-limit', 'quota']:
                    has_rate_limit = True
                    break
        
        if not has_rate_limit and security != 'KEY_LESS':
            self.warnings.append(f"[{name}] Plan has no rate limiting or quota policy")
    
    def _validate_management_context(self, doc: Dict[str, Any], name: str, file_path: str) -> None:
        """Validate ManagementContext CRD."""
        spec = doc.get('spec', {})
        
        # Check required fields
        if not spec.get('baseUrl'):
            self.errors.append(f"[{name}] Missing required field: spec.baseUrl")
        
        # Validate auth configuration
        auth = spec.get('auth', {})
        if not auth.get('secretRef'):
            self.errors.append(f"[{name}] Missing auth.secretRef configuration")
    
    def _validate_flow(self, flow: Dict[str, Any], api_name: str) -> None:
        """Validate a flow configuration."""
        flow_name = flow.get('name', 'unnamed')
        
        # Validate path operator
        path_operator = flow.get('pathOperator', {})
        path = path_operator.get('path', '')
        operator = path_operator.get('operator', '')
        
        if not path:
            self.warnings.append(f"[{api_name}] Flow '{flow_name}' has no path defined")
        
        # Validate policies
        for policy in flow.get('pre', []) + flow.get('post', []):
            self._validate_policy(policy, api_name, flow_name)
    
    def _validate_policy(self, policy: Dict[str, Any], api_name: str, flow_name: str) -> None:
        """Validate a policy configuration."""
        policy_name = policy.get('name', 'unnamed')
        policy_type = policy.get('policy', '')
        
        if not policy_type:
            self.errors.append(f"[{api_name}] Policy '{policy_name}' in flow '{flow_name}' missing policy type")
        
        # Check configuration exists
        if not policy.get('configuration'):
            self.warnings.append(f"[{api_name}] Policy '{policy_name}' has no configuration")
    
    def _get_nested_value(self, d: Dict[str, Any], path: str) -> Any:
        """Get a nested value from a dictionary using dot notation."""
        keys = path.split('.')
        value = d
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def print_results(self) -> None:
        """Print validation results."""
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All validations passed!")
        
        print(f"\nSummary: {len(self.errors)} errors, {len(self.warnings)} warnings")


def main():
    if len(sys.argv) < 2:
        print("Usage: validate-gko-crds.py <file_or_directory>")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    validator = GKOValidator()
    
    if path.is_file():
        validator.validate_file(str(path))
    elif path.is_dir():
        for yaml_file in path.rglob('*.yaml'):
            validator.validate_file(str(yaml_file))
        for yml_file in path.rglob('*.yml'):
            validator.validate_file(str(yml_file))
    else:
        print(f"Path not found: {path}")
        sys.exit(1)
    
    validator.print_results()
    
    if validator.errors:
        sys.exit(1)


if __name__ == '__main__':
    main()

