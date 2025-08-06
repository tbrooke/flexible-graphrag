from pathlib import Path
from typing import List, Union
import logging
import os

from cmislib import CmisClient
try:
    from alfresco.api import AlfrescoApi
except ImportError:
    AlfrescoApi = None
    logging.warning("python-alfresco-api not installed, Alfresco support disabled")

logger = logging.getLogger(__name__)

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
                # Check if file type is supported
                if path.suffix.lower() in ['.pdf', '.docx', '.pptx', '.txt', '.md']:
                    files.append(path)
                    logger.info(f"Added supported file: {path}")
                else:
                    logger.warning(f"Unsupported file type: {path.suffix} for file: {path}")
            elif path.is_dir():
                # Directory - recursively find all files
                logger.info(f"Scanning directory: {path.absolute()}")
                for file_path in path.rglob("*"):
                    if file_path.is_file():
                        # Filter for supported file types
                        if file_path.suffix.lower() in ['.pdf', '.docx', '.pptx', '.txt', '.md']:
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
    
    def list_files(self) -> List[dict]:
        """List all documents from the CMIS folder"""
        try:
            folder = self.repo.getObjectByPath(self.folder_path)
            if not folder:
                raise ValueError(f"Folder not found: {self.folder_path}")
            
            documents = []
            children = folder.getChildren()
            
            for child in children:
                if child.properties['cmis:baseTypeId'] == 'cmis:document':
                    # Check if it's a supported document type
                    content_type = child.properties.get('cmis:contentStreamMimeType', '').lower()
                    if any(doc_type in content_type for doc_type in ['pdf', 'docx', 'pptx', 'text']):
                        documents.append({
                            'id': child.getObjectId(),
                            'name': child.getName(),
                            'content_type': content_type,
                            'cmis_object': child
                        })
            
            logger.info(f"CmisSource found {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error listing CMIS files: {str(e)}")
            raise

class AlfrescoSource:
    """Data source for Alfresco repositories using python-alfresco-api"""
    
    def __init__(self, base_url: str, username: str, password: str, path: str = "/"):
        if AlfrescoApi is None:
            raise ImportError("python-alfresco-api package is required for Alfresco support")
        
        self.base_url = base_url
        self.username = username
        self.password = password
        self.path = path
        
        try:
            self.api = AlfrescoApi(base_url, username, password)
            logger.info("Successfully connected to Alfresco repository")
        except Exception as e:
            logger.error(f"Failed to connect to Alfresco repository: {str(e)}")
            raise
    
    def list_files(self) -> List[dict]:
        """List all documents from the Alfresco path"""
        try:
            children = self.api.get_children(self.path)
            documents = []
            
            for child in children:
                if child.get('isFile', False):
                    # Check if it's a supported document type
                    name = child.get('name', '')
                    if any(name.lower().endswith(ext) for ext in ['.pdf', '.docx', '.pptx', '.txt', '.md']):
                        documents.append({
                            'id': child.get('id'),
                            'name': name,
                            'content_type': child.get('content', {}).get('mimeType', ''),
                            'alfresco_object': child
                        })
            
            logger.info(f"AlfrescoSource found {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error listing Alfresco files: {str(e)}")
            raise