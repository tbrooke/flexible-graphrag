import asyncio
from pathlib import Path
from typing import List, Union
import logging

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions
from llama_index.core import Document

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Handles document conversion using Docling before LlamaIndex processing"""
    
    def __init__(self):
        # Configure Docling for optimal PDF processing
        pdf_options = PdfPipelineOptions(
            do_table_structure=True,
            do_picture_classification=True,
            do_formula_enrichment=True,
            table_structure_options=TableStructureOptions(
                do_cell_matching=True
            )
        )
        
        # Configure all supported Docling formats
        self.converter = DocumentConverter(
            allowed_formats=[
                InputFormat.PDF,
                InputFormat.DOCX, 
                InputFormat.PPTX,
                InputFormat.HTML,
                InputFormat.IMAGE,
                InputFormat.XLSX,
                InputFormat.MD,
                InputFormat.ASCIIDOC,
                InputFormat.CSV
            ],
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
            }
        )
        logger.info("DocumentProcessor initialized with Docling converter")
    
    async def process_documents(self, file_paths: List[Union[str, Path]]) -> List[Document]:
        """Convert documents to markdown using Docling, then create LlamaIndex Documents"""
        documents = []
        
        for file_path in file_paths:
            try:
                path_obj = Path(file_path)
                
                # Check if file exists
                if not path_obj.exists():
                    logger.warning(f"File does not exist: {file_path}")
                    continue
                
                # Check if it's a supported file type by Docling
                docling_extensions = [
                    '.pdf', '.docx', '.xlsx', '.pptx',
                    '.html', '.htm', '.md', '.markdown', '.asciidoc', '.adoc',
                    '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.webp',
                    '.csv', '.xml', '.json'
                ]
                if path_obj.suffix.lower() in docling_extensions:
                    logger.info(f"Converting document with Docling: {file_path}")
                    # Convert using Docling
                    result = self.converter.convert(str(file_path))
                    
                    # Extract both markdown and plain text
                    markdown_content = result.document.export_to_markdown()
                    plain_text = result.document.export_to_text()
                    
                    # Smart format selection: use markdown if tables detected, otherwise plain text
                    has_tables = "|" in markdown_content and "---" in markdown_content  # Simple table detection
                    
                    if has_tables:
                        content_to_use = markdown_content
                        format_used = "markdown (tables detected)"
                    else:
                        content_to_use = plain_text
                        format_used = "plain text (better for entities)"
                    
                    logger.info(f"Using {format_used} for {file_path}")
                    
                    # Log content length for debugging
                    logger.info(f"Docling extracted {len(content_to_use)} characters from {file_path}")
                    logger.debug(f"First 200 chars: {content_to_use[:200]}...")
                    
                    # Create LlamaIndex Document
                    doc = Document(
                        text=content_to_use,
                        metadata={
                            "source": str(file_path),
                            "conversion_method": "docling",
                            "file_type": path_obj.suffix,
                            "file_name": path_obj.name
                        }
                    )
                    documents.append(doc)
                    logger.info(f"Successfully converted: {file_path}")
                    
                elif path_obj.suffix.lower() in ['.txt', '.md']:
                    # Handle plain text files directly
                    logger.info(f"Reading text file directly: {file_path}")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Log content length for debugging
                    logger.info(f"Direct read extracted {len(content)} characters from {file_path}")
                    logger.debug(f"First 200 chars: {content[:200]}...")
                    
                    doc = Document(
                        text=content,
                        metadata={
                            "source": str(file_path),
                            "conversion_method": "direct",
                            "file_type": path_obj.suffix,
                            "file_name": path_obj.name
                        }
                    )
                    documents.append(doc)
                    logger.info(f"Successfully read text file: {file_path}")
                
                else:
                    logger.warning(f"Unsupported file type: {file_path}")
                    continue
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue
        
        logger.info(f"Successfully processed {len(documents)} documents")
        return documents
    
    def process_text_content(self, content: str, source_name: str = "text_input") -> Document:
        """Create a LlamaIndex Document from text content"""
        return Document(
            text=content,
            metadata={
                "source": source_name,
                "conversion_method": "direct_text",
                "file_type": ".txt",
                "file_name": source_name
            }
        )