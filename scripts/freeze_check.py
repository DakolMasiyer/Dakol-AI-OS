#!/usr/bin/env python3
import os
import ast
import sys

def scan_directory(directory):
    # Allowed files that can import from memory.learning
    allowed_files = {
        "core/invariants.py",
        "scripts/semantic_router.py",
        "agents/orchestrator.py",
        "memory/learning.py",
    }
    
    violations = []
    
    for root, _, files in os.walk(directory):
        if "_archive" in root or "venv" in root or ".git" in root or "tests" in root:
            continue
        for file in files:
            if not file.endswith(".py"):
                continue
                
            path = os.path.join(root, file)
            rel_path = os.path.relpath(path, directory)
            
            if rel_path in allowed_files:
                continue
                
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                tree = ast.parse(content, filename=path)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.startswith("memory.learning"):
                                violations.append(f"{rel_path}: import {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.module.startswith("memory.learning"):
                            violations.append(f"{rel_path}: from {node.module} import ...")
            except Exception as e:
                print(f"Error parsing {rel_path}: {e}")
                
    if violations:
        print("ARCHITECTURE DRIFT DETECTED: Illegal memory.learning imports found!")
        for v in violations:
            print("  - " + v)
        return 1
    
    print("Architecture freeze check passed. No illegal imports detected.")
    return 0

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.exit(scan_directory(base_dir))
