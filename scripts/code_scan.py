"""
code_scan.py - Find unused imports, functions, and files in your codebase
Run this script to help clean up your project
"""

import os
import re
import ast
import argparse
from collections import defaultdict

def scan_python_file(file_path):
    """
    Scan a Python file for imports, function definitions, and function calls.
    
    Returns:
        tuple: (imports, defined_functions, called_functions)
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            content = file.read()
            tree = ast.parse(content)
            
            # Track imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for name in node.names:
                        imports.append(f"{module}.{name.name}" if module else name.name)
            
            # Track defined functions
            defined_functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    defined_functions.append(node.name)
            
            # Track function calls
            called_functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        called_functions.append(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        # Handle method calls like obj.method()
                        if isinstance(node.func.value, ast.Name):
                            called_functions.append(f"{node.func.value.id}.{node.func.attr}")
            
            return imports, defined_functions, called_functions
            
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return [], [], []
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
            return [], [], []

def scan_js_file(file_path):
    """
    Basic scanning for JavaScript/JSX files (simplified)
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        
        # Very basic regex to find imports
        imports = re.findall(r'import\s+\{?([^{}]*)\}?\s+from\s+[\'"]([^\'"]+)[\'"]', content)
        imports = [imp.strip() for group in imports for imp in group[0].split(',')]
        
        # Find function definitions
        func_defs = re.findall(r'function\s+(\w+)', content)
        
        # Find arrow functions
        arrow_funcs = re.findall(r'const\s+(\w+)\s+=', content)
        defined_functions = func_defs + arrow_funcs
        
        # Find function calls (very basic)
        called_functions = re.findall(r'(\w+)\(', content)
        
        return imports, defined_functions, called_functions

def scan_directory(directory, extensions=None):
    """
    Scan a directory for code files.
    
    Args:
        directory: Root directory to scan
        extensions: List of file extensions to scan (default: ['.py', '.js', '.jsx'])
        
    Returns:
        dict: Results of the scan
    """
    if extensions is None:
        extensions = ['.py', '.js', '.jsx']
    
    results = {
        'files': [],
        'all_imports': defaultdict(list),
        'all_defined_functions': defaultdict(list),
        'all_called_functions': defaultdict(list),
        'imports_by_file': {},
        'functions_by_file': {},
    }
    
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            _, ext = os.path.splitext(file)
            
            if ext not in extensions:
                continue
            
            results['files'].append(file_path)
            
            # Scan file based on extension
            imports, defined_functions, called_functions = [], [], []
            if ext == '.py':
                imports, defined_functions, called_functions = scan_python_file(file_path)
            elif ext in ['.js', '.jsx']:
                imports, defined_functions, called_functions = scan_js_file(file_path)
            
            # Store results
            rel_path = os.path.relpath(file_path, directory)
            results['imports_by_file'][rel_path] = imports
            results['functions_by_file'][rel_path] = defined_functions
            
            for imp in imports:
                results['all_imports'][imp].append(rel_path)
            for func in defined_functions:
                results['all_defined_functions'][func].append(rel_path)
            for func in called_functions:
                results['all_called_functions'][func].append(rel_path)
    
    return results

def analyze_scan_results(scan_results):
    """
    Analyze scan results to find unused imports and functions.
    """
    defined_functions = scan_results['all_defined_functions']
    called_functions = scan_results['all_called_functions']
    
    # Find potentially unused functions
    unused_functions = {}
    for func, files in defined_functions.items():
        # Skip functions starting with _ (typically private)
        if func.startswith('_'):
            continue
        
        # Check if the function is called anywhere
        if func not in called_functions and not any(f.startswith(func + '.') for f in called_functions):
            unused_functions[func] = files
    
    # Find unused imports (basic)
    unused_imports = {}
    for imp, files in scan_results['all_imports'].items():
        base_imp = imp.split('.')[-1]
        # Check if the import is used
        if (base_imp not in called_functions and 
            not any(f.startswith(base_imp + '.') for f in called_functions) and
            base_imp not in defined_functions):
            unused_imports[imp] = files
    
    return {
        'unused_functions': unused_functions,
        'unused_imports': unused_imports,
    }

def main():
    parser = argparse.ArgumentParser(description='Scan codebase for unused imports and functions.')
    parser.add_argument('--directory', '-d', default='.', help='Directory to scan')
    parser.add_argument('--output', '-o', default='code_scan_results.txt', help='Output file')
    args = parser.parse_args()
    
    print(f"Scanning directory: {args.directory}")
    scan_results = scan_directory(args.directory)
    analysis = analyze_scan_results(scan_results)
    
    # Output results
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write("=== Code Scan Results ===\n\n")
        
        f.write(f"Total files scanned: {len(scan_results['files'])}\n")
        f.write("\n=== Potentially Unused Functions ===\n")
        for func, files in analysis['unused_functions'].items():
            f.write(f"Function: {func}\n")
            for file in files:
                f.write(f"  - Defined in: {file}\n")
        
        f.write("\n=== Potentially Unused Imports ===\n")
        for imp, files in analysis['unused_imports'].items():
            f.write(f"Import: {imp}\n")
            for file in files:
                f.write(f"  - Imported in: {file}\n")
    
    print(f"Scan complete. Results written to {args.output}")
    print(f"Found {len(analysis['unused_functions'])} potentially unused functions and {len(analysis['unused_imports'])} potentially unused imports.")

if __name__ == "__main__":
    main()