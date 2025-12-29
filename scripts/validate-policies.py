#!/usr/bin/env python3
"""
Validates Gravitee API policies against best practices.
Checks for security, performance, and configuration issues.
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, List, Any


class PolicyValidator:
    """Validator for Gravitee API policies."""
    
    # Policies that should typically be present
    RECOMMENDED_POLICIES = {
        'rate-limit': 'Rate limiting protects against abuse',
        'transform-headers': 'Header transformation for security headers',
    }
    
    # Security-related policies
    SECURITY_POLICIES = ['api-key', 'jwt', 'oauth2', 'mtls', 'basic-auth']
    
    # Performance-related policies
    PERFORMANCE_POLICIES = ['cache', 'circuit-breaker', 'retry']
    
    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
    
    def validate_directory(self, directory: Path) -> None:
        """Validate all API definitions in a directory."""
        for yaml_file in directory.rglob('*.yaml'):
            self.validate_file(yaml_file)
    
    def validate_file(self, file_path: Path) -> None:
        """Validate policies in a YAML file."""
        try:
            with open(file_path, 'r') as f:
                documents = list(yaml.safe_load_all(f))
        except yaml.YAMLError:
            return
        
        for doc in documents:
            if doc and doc.get('kind') == 'ApiDefinition':
                self._validate_api_definition(doc, file_path)
    
    def _validate_api_definition(self, doc: Dict[str, Any], file_path: Path) -> None:
        """Validate policies in an API definition."""
        api_name = doc.get('metadata', {}).get('name', 'unknown')
        spec = doc.get('spec', {})
        flows = spec.get('flows', [])
        
        all_policies = []
        
        for flow in flows:
            pre_policies = flow.get('pre', [])
            post_policies = flow.get('post', [])
            all_policies.extend(pre_policies)
            all_policies.extend(post_policies)
        
        policy_types = [p.get('policy') for p in all_policies]
        
        # Check for rate limiting
        if 'rate-limit' not in policy_types and 'quota' not in policy_types:
            self.issues.append({
                'api': api_name,
                'severity': 'warning',
                'message': 'No rate limiting policy found',
                'file': str(file_path)
            })
        
        # Check rate limit configuration
        for policy in all_policies:
            if policy.get('policy') == 'rate-limit':
                self._validate_rate_limit(policy, api_name, file_path)
        
        # Check for security headers
        has_security_headers = False
        for policy in all_policies:
            if policy.get('policy') == 'transform-headers':
                config = policy.get('configuration', {})
                add_headers = config.get('addHeaders', [])
                for header in add_headers:
                    if header.get('name') in ['X-Content-Type-Options', 'X-Frame-Options', 'Strict-Transport-Security']:
                        has_security_headers = True
                        break
        
        if not has_security_headers:
            self.issues.append({
                'api': api_name,
                'severity': 'info',
                'message': 'Consider adding security headers (X-Content-Type-Options, X-Frame-Options, etc.)',
                'file': str(file_path)
            })
        
        # Check for logging configuration
        analytics = spec.get('analytics', {})
        logging = analytics.get('logging', {})
        if logging.get('content') == 'PAYLOADS':
            condition = logging.get('condition', '')
            if not condition or condition == 'true':
                self.issues.append({
                    'api': api_name,
                    'severity': 'warning',
                    'message': 'Payload logging enabled without condition - may impact performance',
                    'file': str(file_path)
                })
        
        # Check for circuit breaker on external calls
        proxy = spec.get('proxy', {})
        groups = proxy.get('groups', [])
        for group in groups:
            endpoints = group.get('endpoints', [])
            for endpoint in endpoints:
                target = endpoint.get('target', '')
                if 'external' in target.lower() or not '.svc.cluster.local' in target:
                    if 'circuit-breaker' not in policy_types:
                        self.issues.append({
                            'api': api_name,
                            'severity': 'info',
                            'message': f'Consider adding circuit breaker for external endpoint: {target}',
                            'file': str(file_path)
                        })
    
    def _validate_rate_limit(self, policy: Dict[str, Any], api_name: str, file_path: Path) -> None:
        """Validate rate limit policy configuration."""
        config = policy.get('configuration', {})
        rate = config.get('rate', {})
        
        limit = rate.get('limit', 0)
        period_unit = rate.get('periodTimeUnit', 'SECONDS')
        
        # Check for very high rate limits
        if period_unit == 'SECONDS' and limit > 100:
            self.issues.append({
                'api': api_name,
                'severity': 'warning',
                'message': f'Very high rate limit: {limit}/second',
                'file': str(file_path)
            })
        
        # Check for very low rate limits
        if period_unit == 'MINUTES' and limit < 5:
            self.issues.append({
                'api': api_name,
                'severity': 'info',
                'message': f'Low rate limit: {limit}/minute - may affect usability',
                'file': str(file_path)
            })
    
    def print_results(self) -> None:
        """Print validation results."""
        if not self.issues:
            print("✅ No policy issues found!")
            return
        
        errors = [i for i in self.issues if i['severity'] == 'error']
        warnings = [i for i in self.issues if i['severity'] == 'warning']
        infos = [i for i in self.issues if i['severity'] == 'info']
        
        if errors:
            print("\n❌ ERRORS:")
            for issue in errors:
                print(f"  [{issue['api']}] {issue['message']}")
        
        if warnings:
            print("\n⚠️  WARNINGS:")
            for issue in warnings:
                print(f"  [{issue['api']}] {issue['message']}")
        
        if infos:
            print("\nℹ️  INFO:")
            for issue in infos:
                print(f"  [{issue['api']}] {issue['message']}")
        
        print(f"\nSummary: {len(errors)} errors, {len(warnings)} warnings, {len(infos)} info")


def main():
    if len(sys.argv) < 2:
        print("Usage: validate-policies.py <directory>")
        sys.exit(1)
    
    directory = Path(sys.argv[1])
    
    if not directory.exists():
        print(f"Directory not found: {directory}")
        sys.exit(1)
    
    validator = PolicyValidator()
    validator.validate_directory(directory)
    validator.print_results()
    
    # Exit with error if there are errors
    errors = [i for i in validator.issues if i['severity'] == 'error']
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()

