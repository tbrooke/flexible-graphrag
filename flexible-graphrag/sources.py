from pathlib import Path
from typing import List, Union
import logging
import os

from cmislib import CmisClient
try:
    from python_alfresco_api import ClientFactory
    # Try to import the direct API functions - these may or may not exist
    try:
        from python_alfresco_api.api.nodes import sync as get_node_sync
        from python_alfresco_api.api.nodes import list_node_children_sync
    except ImportError:
        get_node_sync = None
        list_node_children_sync = None
        logging.info("Using hybrid approach: python-alfresco-api + CMIS for path-based operations")
except ImportError:
    ClientFactory = None
    get_node_sync = None
    list_node_children_sync = None
    logging.warning("python-alfresco-api not installed, Alfresco will use CMIS only")

logger = logging.getLogger(__name__)

def is_docling_supported(content_type: str, filename: str) -> bool:
    """Check if document type is supported by Docling"""
    content_type_lower = content_type.lower()
    filename_lower = filename.lower()
    
    # Supported MIME types (based on Docling supported formats)
    supported_types = [
        # PDF
        'application/pdf',
        # Microsoft Office modern formats (OpenXML)
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # DOCX
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # XLSX
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # PPTX
        # Text and markup formats
        'text/plain',  # TXT
        'text/markdown',  # MD
        'text/html',  # HTML
        'application/xhtml+xml',  # XHTML
        'text/csv',  # CSV
        'text/x-asciidoc',  # AsciiDoc
        # Image formats
        'image/png',  # PNG
        'image/jpeg',  # JPEG
        'image/tiff',  # TIFF
        'image/bmp',  # BMP
        'image/webp',  # WEBP
        # Schema-specific formats
        'application/xml',  # XML (USPTO, JATS)
        'application/json',  # JSON (Docling JSON)
    ]
    
    # Supported file extensions (based on Docling supported formats)
    supported_extensions = [
        # PDF
        '.pdf',
        # Microsoft Office modern formats (OpenXML)
        '.docx', '.xlsx', '.pptx',
        # Text and markup formats
        '.txt', '.md', '.markdown', '.html', '.htm', '.xhtml', '.csv',
        '.asciidoc', '.adoc',
        # Image formats
        '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.webp',
        # Schema-specific formats
        '.xml', '.json',
    ]
    
    # Check by exact MIME type match
    if content_type in supported_types:
        return True
        
    # Check by file extension
    if any(filename_lower.endswith(ext) for ext in supported_extensions):
        return True
        
    # Additional pattern matching for content types
    content_patterns = [
        'pdf', 'word', 'excel', 'powerpoint', 'officedocument',
        'text', 'markdown', 'html', 'csv', 'image', 'xml', 'json'
    ]
    
    return any(pattern in content_type_lower for pattern in content_patterns)

class FileSystemSource:
    """Data source for local filesystem files and directories"""
    
    def __init__(self, paths: List[str]):
        self.paths = paths
        logger.info(f"FileSystemSource initialized with {len(paths)} paths")
    
    def list_files(self) -> List[Path]:
        """List all files from the specified paths (files or directories)"""
        files = []
        
        for path_str in self.paths:
            logger.info(f"Processing path: {path_str}")
            path = Path(path_str)
            logger.info(f"Resolved path: {path.absolute()}")
            
            if not path.exists():
                logger.warning(f"Path does not exist: {path.absolute()}")
                continue
            
            if path.is_file():
                # Single file
                logger.info(f"Found single file: {path.absolute()}")
                # Check if file type is supported by Docling
                if is_docling_supported('', path.name):
                    files.append(path)
                    logger.info(f"Added supported file: {path}")
                else:
                    logger.warning(f"Unsupported file type: {path.suffix} for file: {path}")
            elif path.is_dir():
                # Directory - recursively find all files
                logger.info(f"Scanning directory: {path.absolute()}")
                for file_path in path.rglob("*"):
                    if file_path.is_file():
                        # Filter for supported file types using Docling support
                        if is_docling_supported('', file_path.name):
                            files.append(file_path)
                            logger.info(f"Added file from directory: {file_path}")
            else:
                logger.warning(f"Path is neither file nor directory: {path.absolute()}")
        
        logger.info(f"FileSystemSource found {len(files)} files")
        return files

class CmisSource:
    """Data source for CMIS repositories"""
    
    def __init__(self, url: str, username: str, password: str, folder_path: str = "/"):
        self.url = url
        self.username = username
        self.password = password
        self.folder_path = folder_path
        
        try:
            self.client = CmisClient(url, username, password)
            self.repo = self.client.getDefaultRepository()
            logger.info("Successfully connected to CMIS repository")
        except Exception as e:
            logger.error(f"Failed to connect to CMIS repository: {str(e)}")
            raise
    
    def is_document_supported(self, content_type: str, filename: str) -> bool:
        """Check if document type is supported by Docling"""
        return is_docling_supported(content_type, filename)
    
    def get_document_by_path(self, document_path: str) -> dict:
        """Get a specific document by its full path"""
        try:
            doc_object = self.repo.getObjectByPath(document_path)
            if not doc_object:
                raise ValueError(f"Document not found: {document_path}")
            
            if doc_object.properties['cmis:baseTypeId'] != 'cmis:document':
                raise ValueError(f"Path does not point to a document: {document_path}")
            
            content_type = doc_object.properties.get('cmis:contentStreamMimeType', '')
            filename = doc_object.getName()
            
            if not self.is_document_supported(content_type, filename):
                raise ValueError(f"Unsupported document type: {filename} ({content_type})")
            
            return {
                'id': doc_object.getObjectId(),
                'name': filename,
                'path': document_path,
                'content_type': content_type,
                'cmis_object': doc_object
            }
            
        except Exception as e:
            logger.error(f"Error getting CMIS document by path {document_path}: {str(e)}")
            raise
    
    def list_files(self) -> List[dict]:
        """List all documents from the CMIS folder or get specific file"""
        try:
            # Check if folder_path points to a specific document
            try:
                folder_or_doc = self.repo.getObjectByPath(self.folder_path)
                if folder_or_doc and folder_or_doc.properties['cmis:baseTypeId'] == 'cmis:document':
                    # It's a specific document
                    content_type = folder_or_doc.properties.get('cmis:contentStreamMimeType', '')
                    filename = folder_or_doc.getName()
                    
                    if self.is_document_supported(content_type, filename):
                        logger.info(f"CmisSource found specific document: {filename}")
                        return [{
                            'id': folder_or_doc.getObjectId(),
                            'name': filename,
                            'path': self.folder_path,
                            'content_type': content_type,
                            'cmis_object': folder_or_doc
                        }]
                    else:
                        logger.warning(f"Unsupported document type: {filename} ({content_type})")
                        return []
            except:
                # Not a document, proceed as folder
                pass
            
            # Treat as folder
            folder = self.repo.getObjectByPath(self.folder_path)
            if not folder:
                raise ValueError(f"Folder not found: {self.folder_path}")
            
            documents = []
            children = folder.getChildren()
            
            for child in children:
                if child.properties['cmis:baseTypeId'] == 'cmis:document':
                    content_type = child.properties.get('cmis:contentStreamMimeType', '')
                    filename = child.getName()
                    
                    if self.is_document_supported(content_type, filename):
                        documents.append({
                            'id': child.getObjectId(),
                            'name': filename,
                            'path': f"{self.folder_path.rstrip('/')}/{filename}",
                            'content_type': content_type,
                            'cmis_object': child
                        })
                elif child.properties['cmis:baseTypeId'] == 'cmis:folder':
                    # Recursively process subfolders
                    subfolder_path = f"{self.folder_path.rstrip('/')}/{child.getName()}"
                    try:
                        subfolder_source = CmisSource(self.url, self.username, self.password, subfolder_path)
                        documents.extend(subfolder_source.list_files())
                    except Exception as e:
                        logger.warning(f"Error processing subfolder {subfolder_path}: {str(e)}")
            
            logger.info(f"CmisSource found {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error listing CMIS files: {str(e)}")
            raise
    
    def download_document(self, document: dict, temp_dir: str) -> str:
        """Download a CMIS document to a temporary file and return the file path"""
        import tempfile
        import os
        
        try:
            cmis_object = document['cmis_object']
            filename = document['name']
            
            # Determine file extension from filename or content type
            file_ext = ''
            if '.' in filename:
                file_ext = '.' + filename.split('.')[-1]
            elif 'pdf' in document['content_type'].lower():
                file_ext = '.pdf'
            elif 'docx' in document['content_type'].lower():
                file_ext = '.docx'
            elif 'pptx' in document['content_type'].lower():
                file_ext = '.pptx'
            elif 'text' in document['content_type'].lower():
                file_ext = '.txt'
            elif 'markdown' in document['content_type'].lower():
                file_ext = '.md'
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                suffix=file_ext,
                prefix=f"cmis_{document['id']}_",
                dir=temp_dir,
                delete=False
            )
            
            # Download content
            content_stream = cmis_object.getContentStream()
            if content_stream:
                content = content_stream.read()
                temp_file.write(content)
                temp_file.flush()
                temp_file.close()
                
                logger.info(f"Downloaded CMIS document {filename} to {temp_file.name}")
                return temp_file.name
            else:
                temp_file.close()
                os.unlink(temp_file.name)
                raise ValueError(f"No content stream available for document: {filename}")
                
        except Exception as e:
            logger.error(f"Error downloading CMIS document {document.get('name', 'unknown')}: {str(e)}")
            raise

class AlfrescoSource:
    """Data source for Alfresco repositories using python-alfresco-api + CMIS for path operations"""
    
    def __init__(self, base_url: str, username: str, password: str, path: str = "/"):
        if ClientFactory is None:
            raise ImportError("python-alfresco-api package is required for Alfresco support")
        
        self.base_url = base_url
        self.username = username
        self.password = password
        self.path = path
        
        try:
            # Initialize python-alfresco-api for main operations
            factory = ClientFactory(
                base_url=base_url,
                username=username,
                password=password
            )
            self.core_client = factory.create_core_client()
            self.nodes_client = self.core_client.nodes if hasattr(self.core_client, 'nodes') else None
            self.raw_client = self.core_client.client if hasattr(self.core_client, 'client') else self.core_client
            
            # Initialize CMIS specifically for getObjectByPath operations
            # Use CMIS_URL environment variable if available, otherwise construct from base_url
            import os
            cmis_url = os.getenv("CMIS_URL", f"{base_url}/api/-default-/public/cmis/versions/1.1/atom")
            logger.info(f"AlfrescoSource using CMIS URL: {cmis_url}")
            self.cmis_client = CmisClient(cmis_url, username, password)
            self.repo = self.cmis_client.defaultRepository
            
            logger.info("Successfully connected to Alfresco repository (python-alfresco-api + CMIS for paths)")
        except Exception as e:
            logger.error(f"Failed to connect to Alfresco repository: {str(e)}")
            raise
    
    def is_document_supported(self, content_type: str, filename: str) -> bool:
        """Check if document type is supported by Docling"""
        return is_docling_supported(content_type, filename)
    
    def get_document_by_path(self, document_path: str) -> dict:
        """Get a specific document by its path"""
        try:
            # Use CMIS getObjectByPath for reliable path-based access
            doc_object = self.repo.getObjectByPath(document_path)
            if not doc_object:
                raise ValueError(f"Document not found: {document_path}")
            
            if doc_object.properties['cmis:baseTypeId'] != 'cmis:document':
                raise ValueError(f"Path does not point to a document: {document_path}")
            
            content_type = doc_object.properties.get('cmis:contentStreamMimeType', '')
            filename = doc_object.getName()
            
            if not self.is_document_supported(content_type, filename):
                raise ValueError(f"Unsupported document type: {filename} ({content_type})")
            
            return {
                'id': doc_object.getObjectId(),
                'name': filename,
                'path': document_path,
                'content_type': content_type,
                'cmis_object': doc_object,
                'alfresco_object': None  # Could enhance this later with python-alfresco-api if needed
            }
            
        except Exception as e:
            logger.error(f"Error getting Alfresco document by path {document_path}: {str(e)}")
            raise
    
    def list_files(self) -> List[dict]:
        """List all documents from the Alfresco path or get specific file"""
        try:
            # Use CMIS getObjectByPath for reliable path-based access
            # Check if path points to a specific document
            try:
                obj = self.repo.getObjectByPath(self.path)
                if obj and obj.properties['cmis:baseTypeId'] == 'cmis:document':
                    # It's a specific document
                    content_type = obj.properties.get('cmis:contentStreamMimeType', '')
                    filename = obj.getName()
                    
                    if self.is_document_supported(content_type, filename):
                        logger.info(f"AlfrescoSource found specific document: {filename}")
                        return [{
                            'id': obj.getObjectId(),
                            'name': filename,
                            'path': self.path,
                            'content_type': content_type,
                            'cmis_object': obj,
                            'alfresco_object': None  # Could enhance later with python-alfresco-api
                        }]
                    else:
                        logger.warning(f"Unsupported document type: {filename} ({content_type})")
                        return []
            except:
                # Not a document, proceed as folder
                pass
            
            # Treat as folder - use CMIS for folder operations
            try:
                folder = self.repo.getObjectByPath(self.path)
                if not folder:
                    raise ValueError(f"Folder not found: {self.path}")
                
                documents = []
                children = folder.getChildren()
                
                for child in children:
                    if child.properties['cmis:baseTypeId'] == 'cmis:document':
                        content_type = child.properties.get('cmis:contentStreamMimeType', '')
                        filename = child.getName()
                        
                        if self.is_document_supported(content_type, filename):
                            documents.append({
                                'id': child.getObjectId(),
                                'name': filename,
                                'path': f"{self.path.rstrip('/')}/{filename}",
                                'content_type': content_type,
                                'cmis_object': child,
                                'alfresco_object': None  # Could enhance later with python-alfresco-api
                            })
                    elif child.properties['cmis:baseTypeId'] == 'cmis:folder':
                        # Recursively process subfolders
                        subfolder_path = f"{self.path.rstrip('/')}/{child.getName()}"
                        try:
                            subfolder_source = AlfrescoSource(self.base_url, self.username, self.password, subfolder_path)
                            documents.extend(subfolder_source.list_files())
                        except Exception as e:
                            logger.warning(f"Error processing subfolder {subfolder_path}: {str(e)}")
                
                logger.info(f"AlfrescoSource found {len(documents)} documents")
                return documents
                
            except Exception as e:
                logger.error(f"Error accessing folder {self.path}: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"Error listing Alfresco files: {str(e)}")
            raise
    
    def download_document(self, document: dict, temp_dir: str) -> str:
        """Download an Alfresco document to a temporary file and return the file path"""
        import tempfile
        import os
        
        try:
            filename = document['name']
            node_id = document['id']
            
            # Determine file extension from filename or content type
            file_ext = ''
            if '.' in filename:
                file_ext = '.' + filename.split('.')[-1]
            elif 'pdf' in document['content_type'].lower():
                file_ext = '.pdf'
            elif 'docx' in document['content_type'].lower():
                file_ext = '.docx'
            elif 'pptx' in document['content_type'].lower():
                file_ext = '.pptx'
            elif 'text' in document['content_type'].lower():
                file_ext = '.txt'
            elif 'markdown' in document['content_type'].lower():
                file_ext = '.md'
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                suffix=file_ext,
                prefix=f"alfresco_{node_id}_",
                dir=temp_dir,
                delete=False
            )
            
            # Try python-alfresco-api first if available
            content_downloaded = False
            if self.nodes_client:
                try:
                    content_response = self.nodes_client.get_content(node_id=node_id)
                    if content_response and hasattr(content_response, 'content'):
                        temp_file.write(content_response.content)
                        content_downloaded = True
                        logger.info(f"Downloaded via python-alfresco-api: {filename}")
                except Exception as e:
                    logger.debug(f"python-alfresco-api download failed: {str(e)}, trying CMIS")
            
            # Fall back to CMIS if python-alfresco-api didn't work
            if not content_downloaded and 'cmis_object' in document:
                cmis_object = document['cmis_object']
                content_stream = cmis_object.getContentStream()
                if content_stream:
                    temp_file.write(content_stream.read())
                    content_stream.close()
                    content_downloaded = True
                    logger.info(f"Downloaded via CMIS: {filename}")
            
            if content_downloaded:
                temp_file.flush()
                temp_file.close()
                logger.info(f"Downloaded Alfresco document {filename} to {temp_file.name}")
                return temp_file.name
            else:
                temp_file.close()
                os.unlink(temp_file.name)
                raise ValueError(f"No content available for document: {filename}")
                
        except Exception as e:
            logger.error(f"Error downloading Alfresco document {document.get('name', 'unknown')}: {str(e)}")
            raise