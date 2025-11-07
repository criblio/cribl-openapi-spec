#!/usr/bin/env python3
"""
Expand all $ref pointers in OpenAPI spec (JSON or YAML).
Handles circular references by tracking expansion depth.
"""
import json
import yaml
import sys
from copy import deepcopy


MAX_DEPTH = 10  # Prevent infinite recursion


def resolve_ref_pointer(ref_path, root_doc):
    """Resolve a JSON reference pointer like '#/components/schemas/Error'"""
    if not ref_path.startswith('#/'):
        raise ValueError(f"External references not supported: {ref_path}")
    
    parts = ref_path[2:].split('/')
    current = root_doc
    
    for part in parts:
        part = part.replace('~1', '/').replace('~0', '~')  # JSON pointer escaping
        if isinstance(current, dict):
            current = current[part]
        elif isinstance(current, list):
            current = current[int(part)]
        else:
            raise ValueError(f"Cannot resolve path {ref_path}")
    
    return current


def expand_refs(obj, root_doc, path="root", depth=0, visited_paths=None):
    """
    Recursively expand all $ref in the document.
    """
    if visited_paths is None:
        visited_paths = set()
    
    if depth > MAX_DEPTH:
        return {"type": "object", "description": f"Max expansion depth reached at {path}"}
    
    if isinstance(obj, dict):
        if '$ref' in obj:
            ref_path = obj['$ref']
            
            # Create a tracking key for this expansion
            tracking_key = f"{path}:{ref_path}"
            
            if tracking_key in visited_paths:
                # Circular reference detected, return a placeholder
                return {"type": "object", "description": f"Circular reference: {ref_path}"}
            
            visited_paths.add(tracking_key)
            
            try:
                # Resolve the reference
                resolved = resolve_ref_pointer(ref_path, root_doc)
                
                # Deep copy to avoid modifying the original
                resolved = deepcopy(resolved)
                
                # Merge other properties if they exist
                other_props = {k: v for k, v in obj.items() if k != '$ref'}
                if other_props:
                    if isinstance(resolved, dict):
                        resolved = {**resolved, **other_props}
                
                # Recursively expand the resolved object
                result = expand_refs(resolved, root_doc, f"{path}->{ref_path}", depth + 1, visited_paths.copy())
                
                return result
            except Exception as e:
                return {"type": "object", "description": f"Error resolving {ref_path}: {str(e)}"}
        else:
            # Recursively expand all values in the dict
            return {key: expand_refs(value, root_doc, f"{path}.{key}", depth, visited_paths.copy()) 
                    for key, value in obj.items()}
    
    elif isinstance(obj, list):
        # Recursively expand all items in the list
        return [expand_refs(item, root_doc, f"{path}[{i}]", depth, visited_paths.copy()) 
                for i, item in enumerate(obj)]
    
    else:
        # Base case: return primitive values as-is
        return obj


class NoAliasDumper(yaml.SafeDumper):
    """Custom YAML dumper that ignores anchors and aliases."""
    def ignore_aliases(self, data):
        return True
    
    def increase_indent(self, flow=False, indentless=False):
        return super(NoAliasDumper, self).increase_indent(flow, False)


def str_representer(dumper, data):
    """Use double quotes for strings that need quoting, matching OpenAPI style."""
    # Use double quotes for:
    # - Empty strings ("")
    # - HTTP status codes (3-digit numbers like "200", "404", "502")
    if not data:  # Empty string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
    if len(data) == 3 and data.isdigit():  # HTTP status codes like "200"
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
    # Let YAML decide for other strings (plain style when safe, quoted when needed)
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


# Register the custom string representer
NoAliasDumper.add_representer(str, str_representer)


def remove_unused_components(doc):
    """Remove the components section since all refs are expanded."""
    if 'components' in doc:
        print(f"  Removing unused components section...")
        del doc['components']
    return doc


def process_file(input_path, output_path):
    """Load spec, expand all refs, and save."""
    print(f"Loading {input_path}...")
    
    # Detect format from extension
    with open(input_path, 'r') as f:
        if input_path.endswith('.json'):
            doc = json.load(f)
        else:
            doc = yaml.safe_load(f)
    
    print(f"Expanding all $ref pointers (max depth: {MAX_DEPTH})...")
    expanded = expand_refs(doc, doc)
    
    print(f"Removing unused components...")
    expanded = remove_unused_components(expanded)
    
    print(f"Saving to {output_path}...")
    with open(output_path, 'w') as f:
        if output_path.endswith('.json'):
            json.dump(expanded, f, indent=2)
        else:
            yaml.dump(expanded, f, Dumper=NoAliasDumper, default_flow_style=False, sort_keys=False, width=120, indent=2)
    
    print(f"✓ Done!")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: expand-refs.py <input> <output>")
        sys.exit(1)
    
    process_file(sys.argv[1], sys.argv[2])

