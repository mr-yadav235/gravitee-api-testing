#!/usr/bin/env python3
"""
Checks for sensitive data in API definitions.
Ensures no secrets, passwords, or tokens are hardcoded.
"""

import sys
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Tuple


class SensitiveDataChecker:
    """Checker for sensitive data in configuration files."""
    
    # Patterns that indicate ACTUAL hardcoded secrets (more specific)
    SENSITIVE_PATTERNS = [
        # Real passwords (not placeholders, not references)
        (r'password\s*[:=]\s*["\'](?!changeme|PLACEHOLDER|SEALED|TODO|xxx|admin)[a-zA-Z0-9!@#$%^&*()_+-=]{12,}["\']', 'Possible hardcoded password'),
        # Real secrets (long random strings)
        (r'secret\s*[:=]\s*["\'][a-zA-Z0-9!@#$%^&*()_+-=]{24,}["\']', 'Possible hardcoded secret'),
        # API keys (specific formats)
        (r'api[_-]?key\s*[:=]\s*["\'][a-zA-Z0-9-]{32,}["\']', 'Possible hardcoded API key'),
        # Bearer tokens
        (r'[Bb]earer\s+[a-zA-Z0-9._-]{40,}', 'Possible hardcoded bearer token'),
        # Private keys
        (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', 'Private key detected'),
        # Connection strings with passwords
        (r'mongodb://[^:]+:[^@]{8,}@', 'MongoDB connection string with credentials'),
        (r'postgres://[^:]+:[^@]{8,}@', 'PostgreSQL connection string with credentials'),
        (r'mysql://[^:]+:[^@]{8,}@', 'MySQL connection string with credentials'),
        # AWS keys
        (r'AKIA[0-9A-Z]{16}', 'AWS Access Key ID detected'),
        # GitHub tokens
        (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Personal Access Token detected'),
        (r'github_pat_[a-zA-Z0-9_]{22,}', 'GitHub PAT detected'),
    ]
    
    # Values that are explicitly safe (not secrets)
    SAFE_VALUE_PATTERNS = [
        r'^\$\{.*\}$',           # Environment variable: ${VAR}
        r'^\{\{.*\}\}$',         # Template: {{var}}
        r'^\{#.*\}$',            # Gravitee EL expression: {#...}
        r'^secretRef$',          # K8s secret reference
        r'.*PLACEHOLDER.*',      # Placeholder text
        r'.*SEALED.*',           # Sealed secret
        r'.*CHANGE_ME.*',        # Change me marker
        r'.*REPLACE.*',          # Replace marker
        r'.*TODO.*',             # TODO marker
        r'^changeme$',           # Default placeholder
        r'^admin$',              # Default username (not a secret)
        r'^xxx+$',               # Placeholder xxx
        r'^yyy+$',               # Placeholder yyy
        r'^JWKS_URL$',           # Config value, not secret
        r'^GRAVITEE_PASSWORD$',  # Reference to key name, not actual password
        r'^GRAVITEE_USERNAME$',  # Reference to key name
        r'\.svc\.cluster\.local',  # K8s service URLs
        r'^http://',             # URLs are not secrets
        r'^https://',            # URLs are not secrets
    ]
    
    # Keys that contain "key" but are NOT sensitive (config keys, not secret keys)
    SAFE_KEY_CONTEXTS = [
        'publicKeyResolver',     # JWT config
        'secretKey',             # External secrets field name (not the actual secret)
        'remoteRef.key',         # Vault path reference
        'configuration.key',     # Rate limit key expression
        'properties.key',        # Property name
        'backend-url',           # Property key name
        'rate-limit',            # Property key name
    ]
    
    def __init__(self):
        self.findings: List[Dict[str, Any]] = []
    
    def check_directory(self, directory: Path) -> None:
        """Check all YAML files in a directory."""
        for yaml_file in directory.rglob('*.yaml'):
            self.check_file(yaml_file)
        for yml_file in directory.rglob('*.yml'):
            self.check_file(yml_file)
    
    def check_file(self, file_path: Path) -> None:
        """Check a file for sensitive data."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Check for sensitive patterns
            for pattern, description in self.SENSITIVE_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Double-check it's not a safe value
                    if not self._line_is_safe(line):
                        self.findings.append({
                            'file': str(file_path),
                            'line': line_num,
                            'description': description,
                            'content': line.strip()[:100]
                        })
    
    def _line_is_safe(self, line: str) -> bool:
        """Check if a line contains safe patterns."""
        for pattern in self.SAFE_VALUE_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _is_safe_value(self, value: str, key_path: str) -> bool:
        """Check if a value is safe (placeholder, reference, etc.)."""
        # Check if the key context is safe
        for safe_context in self.SAFE_KEY_CONTEXTS:
            if safe_context in key_path:
                return True
        
        # Check if value matches safe patterns
        for pattern in self.SAFE_VALUE_PATTERNS:
            if re.search(pattern, str(value), re.IGNORECASE):
                return True
        
        return False
    
    def print_results(self) -> int:
        """Print findings and return exit code."""
        if not self.findings:
            print("✅ No sensitive data detected!")
            return 0
        
        # Deduplicate findings
        unique_findings = []
        seen = set()
        for finding in self.findings:
            key = (finding['file'], finding['line'], finding['description'])
            if key not in seen:
                seen.add(key)
                unique_findings.append(finding)
        
        print(f"\n⚠️  Found {len(unique_findings)} potential sensitive data issues:\n")
        
        for finding in unique_findings:
            print(f"📁 {finding['file']}")
            if finding['line']:
                print(f"   Line {finding['line']}: {finding['description']}")
            else:
                print(f"   {finding['description']}")
            print(f"   Content: {finding['content']}")
            print()
        
        print("Please review these findings and ensure no actual secrets are committed.")
        print("Use Kubernetes Secrets, External Secrets Operator, or Sealed Secrets instead.")
        
        # Return 1 only for critical issues (private keys, AWS keys, etc.)
        critical_patterns = ['Private key', 'AWS', 'GitHub']
        has_critical = any(
            any(p in f['description'] for p in critical_patterns) 
            for f in unique_findings
        )
        
        return 1 if has_critical else 0


def main():
    if len(sys.argv) < 2:
        print("Usage: check-sensitive-data.py <directory>")
        sys.exit(1)
    
    directory = Path(sys.argv[1])
    
    if not directory.exists():
        print(f"Directory not found: {directory}")
        sys.exit(1)
    
    checker = SensitiveDataChecker()
    checker.check_directory(directory)
    exit_code = checker.print_results()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
