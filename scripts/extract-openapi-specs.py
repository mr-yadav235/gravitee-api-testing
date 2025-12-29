#!/usr/bin/env python3
"""
Extracts OpenAPI specifications embedded in Gravitee API definitions.
Used for validating OpenAPI specs during CI.
"""

import sys
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional


def extract_openapi_from_api_definition(doc: Dict[str, Any]) -> Optional[str]:
    """Extract OpenAPI spec from an ApiDefinition resource."""
    if doc.get('kind') != 'ApiDefinition':
        return None
    
    spec = doc.get('spec', {})
    resources = spec.get('resources', [])
    
    for resource in resources:
        if resource.get('type') == 'content':
            config = resource.get('configuration', {})
            content = config.get('content', '')
            
            # Check if it looks like an OpenAPI spec
            if 'openapi:' in content or 'swagger:' in content:
                return content
    
    return None


def extract_from_file(file_path: Path, output_dir: Path) -> int:
    """Extract OpenAPI specs from a YAML file."""
    extracted_count = 0
    
    try:
        with open(file_path, 'r') as f:
            documents = list(yaml.safe_load_all(f))
    except yaml.YAMLError as e:
        print(f"Error parsing {file_path}: {e}")
        return 0
    
    for doc in documents:
        if doc is None:
            continue
        
        openapi_content = extract_openapi_from_api_definition(doc)
        if openapi_content:
            api_name = doc.get('metadata', {}).get('name', 'unknown')
            output_file = output_dir / f"{api_name}-openapi.yaml"
            
            with open(output_file, 'w') as f:
                f.write(openapi_content)
            
            print(f"Extracted OpenAPI spec: {output_file}")
            extracted_count += 1
    
    return extracted_count


def main():
    if len(sys.argv) < 3:
        print("Usage: extract-openapi-specs.py <input_dir> <output_dir>")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    total_extracted = 0
    
    for yaml_file in input_dir.rglob('*.yaml'):
        total_extracted += extract_from_file(yaml_file, output_dir)
    
    for yml_file in input_dir.rglob('*.yml'):
        total_extracted += extract_from_file(yml_file, output_dir)
    
    print(f"\nTotal OpenAPI specs extracted: {total_extracted}")


if __name__ == '__main__':
    main()

