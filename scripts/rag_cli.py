"""
Command-line interface for RAG application.
Allows interactive testing of the RAG system.
"""
import os
import argparse
import logging
import sys
from typing import Optional

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# Now import our modules
from src.rag import LocalRAG
from src.simple_azure_rag import SimpleAzureRAG
from config import AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX_NAME

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_results(documents, show_scores=True):
    """Format retrieval results for display."""
    if not documents:
        return "No relevant documents found."
    
    result_text = []
    for i, doc in enumerate(documents):
        score_text = f" [Score: {doc['similarity_score']:.4f}]" if show_scores else ""
        result_text.append(f"Result {i+1}{score_text}")
        
        # Add metadata if available
        if 'metadata' in doc and doc['metadata']:
            metadata = doc['metadata']
            if 'source_filename' in metadata:
                result_text.append(f"Source: {metadata['source_filename']}")
            if 'title' in metadata:
                result_text.append(f"Title: {metadata['title']}")
            if 'eo_number' in metadata:
                result_text.append(f"Executive Order: {metadata['eo_number']}")
        
        # Add snippet of content
        content = doc.get('content', '')
        snippet = content[:300] + "..." if len(content) > 300 else content
        result_text.append(f"\n{snippet}\n")
        
        # Add separator between results
        result_text.append("-" * 80)
    
    return "\n".join(result_text)

def interactive_mode(rag_system, history_file: Optional[str] = None):
    """Run the RAG system in interactive mode."""
    # Load query history if available
    history = []
    if history_file and os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history = [line.strip() for line in f.readlines()]
        except Exception as e:
            logger.warning(f"Could not load history: {e}")
    system_type = "Azure AI Search" if isinstance(rag_system, AzureRAG) else "Local Vector Store"

    print("\n" + "=" * 80)
    print(f"Executive Orders and Government Guidance RAG System ({system_type})")
    print("=" * 80)
    print("\n" + "=" * 80)
    print("Executive Orders and Government Guidance RAG System")
    print("=" * 80)
    print("Type your question and press Enter. Type 'exit' or 'quit' to end.")
    print("Commands: '!clear' to clear screen, '!history' to view history")
    print("=" * 80 + "\n")
    
    while True:
        try:
            query = input("\nQuestion: ").strip()
            
            # Check for exit command
            if query.lower() in ['exit', 'quit']:
                break
            
            # Check for special commands
            if query == '!clear':
                clear_screen()
                continue
            elif query == '!history':
                print("\nQuery History:")
                for i, hist_query in enumerate(history[-10:], 1):
                    print(f"{i}. {hist_query}")
                continue
            
            # Skip empty queries
            if not query:
                continue
            
            # Add to history
            history.append(query)
            
            # Process the query
            print("\nSearching for relevant information...")
            documents = rag_system.retrieve(query)
            
            # Display results
            print("\nRelevant Information:")
            print(format_results(documents))
            
            # Generate answer (placeholder for now)
            print("\nWith LLM integration, the system would generate an answer based on:")
            print("- Your query: " + query)
            print("- The retrieved information shown above")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            print(f"\nError: {str(e)}")
    
    # Save history
    if history_file:
        try:
            with open(history_file, 'w') as f:
                for query in history:
                    f.write(query + '\n')
        except Exception as e:
            logger.warning(f"Could not save history: {e}")
    
    print("\nThank you for using the Executive Orders RAG System!")

def main():
    """Main function to run the RAG CLI."""
    parser = argparse.ArgumentParser(description='RAG CLI for Executive Orders')
    """parser.add_argument('--index', '-i', required=True, help='Vector store index file path')
    parser.add_argument('--query', '-q', help='Single query mode (non-interactive)')
    parser.add_argument('--top', '-k', type=int, default=3, help='Number of results to return')
    parser.add_argument('--threshold', '-t', type=float, default=0.4, help='Similarity score threshold')
    parser.add_argument('--history', help='Path to save query history')"""
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--index', '-i', help='Local vector store index file path')
    source_group.add_argument('--azure', '-a', action='store_true', help='Use Azure AI Search instead of local vector store')
    parser.add_argument('--query', '-q', help='Single query mode (non-interactive)')
    parser.add_argument('--top', '-k', type=int, default=3, help='Number of results to return')
    parser.add_argument('--threshold', '-t', type=float, default=0.4, help='Similarity score threshold (local only)')
    parser.add_argument('--history', help='Path to save query history')
    
    args = parser.parse_args()
    
    try:
        if args.azure:
            # Check Azure credentials
            if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_API_KEY or not AZURE_SEARCH_INDEX_NAME:
                logger.error("Azure Search credentials not found in environment variables")
                logger.error("Please set AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, and AZURE_SEARCH_INDEX_NAME")
                sys.exit(1)
                
            logger.info(f"Initializing Azure RAG system with index: {AZURE_SEARCH_INDEX_NAME}")
            rag_system = AzureRAG(
                search_endpoint=AZURE_SEARCH_ENDPOINT,
                search_key=AZURE_SEARCH_API_KEY,
                index_name=AZURE_SEARCH_INDEX_NAME,
                top_k=args.top
            )
        else:
            # Use local vector store
            logger.info(f"Initializing local RAG system with index: {args.index}")
            rag_system = LocalRAG(
                vector_store_path=args.index,
                top_k=args.top,
                similarity_threshold=args.threshold
            )
                    
    except Exception as e:
        logger.error(f"Error in RAG CLI: {e}")
        sys.exit(1)
      
    """ # Initialize RAG system
    rag_system = LocalRAG(
        vector_store_path=args.index,
        top_k=args.top,
        similarity_threshold=args.threshold
    )
    
    # Check for single query mode
    if args.query:
        # Process a single query
        documents = rag_system.retrieve(args.query)
        print(format_results(documents))
    else:
        # Run in interactive mode
        interactive_mode(rag_system, args.history)"""
   


if __name__ == "__main__":
    main()