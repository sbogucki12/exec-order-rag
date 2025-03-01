"""
Script to inspect the DocumentProcessor class and its methods.
"""
import os
import sys
import inspect

# Add the parent directory to sys.path to enable imports from src
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from src.document_processor import DocumentProcessor

def main():
    """Main function to inspect DocumentProcessor."""
    print("\n" + "="*50)
    print("DocumentProcessor Inspection")
    print("="*50)
    
    # Create an instance
    processor = DocumentProcessor()
    
    # Get class details
    print(f"\nClass: {processor.__class__.__name__}")
    print(f"Module: {processor.__class__.__module__}")
    
    # Get methods
    methods = [method for method in dir(processor) if not method.startswith('_')]
    print(f"\nAvailable methods: {methods}")
    
    # Inspect each method
    print("\nMethod details:")
    for method_name in methods:
        method = getattr(processor, method_name)
        if callable(method):
            try:
                signature = inspect.signature(method)
                print(f"\n- {method_name}{signature}")
                doc = inspect.getdoc(method)
                if doc:
                    print(f"  Docstring: {doc.split(chr(10))[0]}")
            except (ValueError, TypeError):
                print(f"\n- {method_name} (signature unavailable)")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    main()