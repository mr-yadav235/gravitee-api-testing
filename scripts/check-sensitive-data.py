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
    
    # Patterns that might indicate sensitive data
    SENSITIVE_PATTERNS = [
        (r'password\s*[:=]\s*["\']?(?!.*PLACEHOLDER|.*SEALED|.*\{\{)[a-zA-Z0-9!@#$%^&*()_+-=]{8,}', 'Possible hardcoded password'),
        (r'secret\s*[:=]\s*["\']?(?!.*PLACEHOLDER|.*SEALED|.*\{\{)[a-zA-Z0-9!@#$%^&*()_+-=]{16,}', 'Possible hardcoded secret'),
        (r'api[_-]?key\s*[:=]\s*["\']?(?!.*PLACEHOLDER|.*SEALED|.*\{\{)[a-zA-Z0-9-]{20,}', 'Possible hardcoded API key'),
        (r'token\s*[:=]\s*["\']?(?!.*PLACEHOLDER|.*SEALED|.*\{\{)[a-zA-Z0-9._-]{20,}', 'Possible hardcoded token'),
        (r'bearer\s+[a-zA-Z0-9._-]{20,}', 'Possible hardcoded bearer token'),
        (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', 'Private key detected'),
        (r'-----BEGIN\s+CERTIFICATE-----', 'Certificate detected (may be intentional)'),
        (r'mongodb://[^:]+:[^@]+@', 'MongoDB connection string with credentials'),
        (r'postgres://[^:]+:[^@]+@', 'PostgreSQL connection string with credentials'),
        (r'mysql://[^:]+:[^@]+@', 'MySQL connection string with credentials'),
    ]
    
    # Allowed patterns (false positives)
    ALLOWED_PATTERNS = [
        r'\$\{.*\}',  # Environment variable references
        r'\{\{.*\}\}',  # Template variables
        r'secretRef',  # Kubernetes secret references
        r'PLACEHOLDER',
        r'SEALED_SECRET',
        r'CHANGE_ME',
        r'REPLACE_WITH',
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
            # Skip if line matches allowed patterns
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in self.ALLOWED_PATTERNS):
                continue
            
            # Check for sensitive patterns
            for pattern, description in self.SENSITIVE_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    self.findings.append({
                        'file': str(file_path),
                        'line': line_num,
                        'description': description,
                        'content': line.strip()[:100]  # Truncate for safety
                    })
        
        # Also check YAML structure for suspicious keys
        try:
            documents = list(yaml.safe_load_all(content))
            for doc in documents:
                if doc:
                    self._check_yaml_structure(doc, file_path, [])
        except yaml.YAMLError:
            pass
    
    def _check_yaml_structure(self, obj: Any, file_path: Path, path: List[str]) -> None:
        """Recursively check YAML structure for suspicious values."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = path + [key]
                
                # Check if key suggests sensitive data
                key_lower = key.lower()
                if any(s in key_lower for s in ['password', 'secret', 'token', 'key', 'credential']):
                    if isinstance(value, str) and value and not self._is_safe_value(value):
                        self.findings.append({
                            'file': str(file_path),
                            'line': 0,
                            'description': f'Suspicious value for key: {".".join(current_path)}',
                            'content': f'{key}: {value[:50]}...' if len(str(value)) > 50 else f'{key}: {value}'
                        })
                
                self._check_yaml_structure(value, file_path, current_path)
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._check_yaml_structure(item, file_path, path + [f'[{i}]'])
    
    def _is_safe_value(self, value: str) -> bool:
        """Check if a value is safe (placeholder, reference, etc.)."""
        safe_indicators = [
            '${', '{{', 'secretRef', 'PLACEHOLDER', 'SEALED', 
            'CHANGE_ME', 'REPLACE', 'TODO', 'xxx', 'yyy'
        ]
        return any(indicator in value for indicator in safe_indicators)
    
    def print_results(self) -> int:
        """Print findings and return exit code."""
        if not self.findings:
            print("✅ No sensitive data detected!")
            return 0
        
        print(f"\n⚠️  Found {len(self.findings)} potential sensitive data issues:\n")
        
        for finding in self.findings:
            print(f"📁 {finding['file']}")
            if finding['line']:
                print(f"   Line {finding['line']}: {finding['description']}")
            else:
                print(f"   {finding['description']}")
            print(f"   Content: {finding['content']}")
            print()
        
        print("Please review these findings and ensure no actual secrets are committed.")
        print("Use Kubernetes Secrets, External Secrets Operator, or Sealed Secrets instead.")
        
        return 1


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

