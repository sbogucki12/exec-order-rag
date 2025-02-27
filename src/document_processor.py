"""
Document processor for RAG application.
Handles document loading, chunking, and processing for executive orders.
"""

import os
import re
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# For document loading
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredHTMLLoader,
)
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Processes documents for RAG applications."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        metadata_extractor = None
    ):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Size of document chunks
            chunk_overlap: Overlap between chunks
            metadata_extractor: Optional function to extract metadata from documents
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.metadata_extractor = metadata_extractor
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def load_document(self, file_path: str) -> List[Document]:
        """
        Load a document from a file path.
        
        Args:
            file_path: Path to the document
            
        Returns:
            List of LangChain Document objects
        """
        logger.info(f"Loading document from {file_path}")
        
        file_extension = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_extension == ".pdf":
                loader = PyPDFLoader(file_path)
            elif file_extension in [".docx", ".doc"]:
                loader = Docx2txtLoader(file_path)
            elif file_extension == ".html":
                loader = UnstructuredHTMLLoader(file_path)
            elif file_extension == ".txt":
                loader = TextLoader(file_path)
            else:
                raise ValueError(f"Unsupported file extension: {file_extension}")
            
            documents = loader.load()
            logger.info(f"Successfully loaded {len(documents)} document parts")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading document: {str(e)}")
            raise
    
    def process_documents(
        self,
        documents: List[Document],
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Process documents by splitting into chunks and extracting metadata.
        
        Args:
            documents: List of LangChain Document objects
            include_metadata: Whether to include document metadata
            
        Returns:
            List of processed document chunks with metadata
        """
        logger.info(f"Processing {len(documents)} documents")
        
        try:
            # Split documents into chunks
            document_chunks = self.text_splitter.split_documents(documents)
            logger.info(f"Split documents into {len(document_chunks)} chunks")
            
            processed_chunks = []
            
            for i, chunk in enumerate(document_chunks):
                # Generate a unique ID for each chunk
                chunk_id = str(uuid.uuid4())
                
                # Extract metadata if available and requested
                metadata = {}
                if include_metadata:
                    # Include existing metadata from the document
                    if hasattr(chunk, 'metadata') and chunk.metadata:
                        metadata.update(chunk.metadata)
                    
                    # Use custom metadata extractor if provided
                    if self.metadata_extractor:
                        extracted_metadata = self.metadata_extractor(chunk.page_content)
                        if extracted_metadata:
                            metadata.update(extracted_metadata)
                
                # Add processing metadata
                metadata.update({
                    "chunk_id": chunk_id,
                    "chunk_index": i,
                    "processed_at": datetime.now().isoformat(),
                })
                
                # Create processed chunk
                processed_chunk = {
                    "id": chunk_id,
                    "content": chunk.page_content,
                    "metadata": metadata
                }
                
                processed_chunks.append(processed_chunk)
            
            logger.info(f"Successfully processed {len(processed_chunks)} document chunks")
            return processed_chunks
            
        except Exception as e:
            logger.error(f"Error processing documents: {str(e)}")
            raise

    @staticmethod
    def extract_executive_order_metadata(text: str) -> Dict[str, Any]:
        """
        Extract metadata specific to executive orders.
        
        Args:
            text: Document text
            
        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}
        
        # Try to extract executive order number
        eo_number_match = re.search(r'Executive Order (\d+)', text)
        if eo_number_match:
            metadata["eo_number"] = eo_number_match.group(1)
        
        # Try to extract date
        date_match = re.search(r'(\w+ \d{1,2}, \d{4})', text)
        if date_match:
            metadata["date"] = date_match.group(1)
        
        # Try to extract title
        title_match = re.search(r'Executive Order.*?\n(.+)', text)
        if title_match:
            metadata["title"] = title_match.group(1).strip()
        
        return metadata

    def process_from_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """
        Process all supported documents from a directory.
        
        Args:
            directory_path: Path to directory containing documents
            
        Returns:
            List of processed document chunks
        """
        logger.info(f"Processing documents from directory: {directory_path}")
        
        supported_extensions = [".pdf", ".docx", ".doc", ".txt", ".html"]
        all_chunks = []
        
        try:
            for filename in os.listdir(directory_path):
                file_path = os.path.join(directory_path, filename)
                
                if os.path.isfile(file_path):
                    file_extension = os.path.splitext(filename)[1].lower()
                    
                    if file_extension in supported_extensions:
                        # Load and process the document
                        documents = self.load_document(file_path)
                        
                        # Add filename to metadata
                        for doc in documents:
                            if not hasattr(doc, 'metadata'):
                                doc.metadata = {}
                            doc.metadata["source_filename"] = filename
                        
                        # Process the document
                        chunks = self.process_documents(documents)
                        all_chunks.extend(chunks)
            
            logger.info(f"Successfully processed {len(all_chunks)} total chunks from directory")
            return all_chunks
            
        except Exception as e:
            logger.error(f"Error processing directory: {str(e)}")
            raise

# Example usage function
def process_executive_orders(directory_path: str, output_path: Optional[str] = None):
    """
    Process executive orders from a directory.
    
    Args:
        directory_path: Path to directory containing executive orders
        output_path: Optional path to save processed chunks as JSON
    """
    processor = DocumentProcessor(
        chunk_size=1000,
        chunk_overlap=200,
        metadata_extractor=DocumentProcessor.extract_executive_order_metadata
    )
    
    chunks = processor.process_from_directory(directory_path)
    
    if output_path:
        import json
        with open(output_path, 'w') as f:
            json.dump(chunks, f, indent=2)
        logger.info(f"Saved {len(chunks)} processed chunks to {output_path}")
    
    return chunks