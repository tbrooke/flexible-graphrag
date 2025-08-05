import cmislib
from cmislib import CmisClient, Repository
import logging
import tempfile
import os
from typing import Callable, Awaitable, List, Any

logger = logging.getLogger(__name__)

class CMISHandler:
    def __init__(self, url: str, username: str, password: str):
        """Initialize CMIS client and repository connection"""
        try:
            self.client = CmisClient(url, username, password)
            self.repo = self.client.getDefaultRepository()
            logger.info("Successfully connected to CMIS repository")
        except Exception as e:
            logger.error(f"Failed to connect to CMIS repository: {str(e)}")
            raise

    async def process_folder(
        self, 
        folder_path: str, 
        process_doc_callback: Callable[[str, str, str], Awaitable[None]]
    ) -> None:
        """Process all documents in a folder one at a time"""
        logger.info(f"Accessing folder: {folder_path}")
        try:
            folder = self.repo.getObjectByPath(folder_path)
            if not folder:
                logger.error(f"Folder not found: {folder_path}")
                raise ValueError(f"Folder not found: {folder_path}")

            # Get all children of the folder
            logger.info("Retrieving folder contents...")
            children: List[Any] = folder.getChildren()
            
            # Process each document
            for child in children:
                try:
                    if child.properties['cmis:baseTypeId'] == 'cmis:document':
                        doc_name = child.getName()
                        doc_id = child.getObjectId()
                        
                        # Check if it's a PDF document
                        content_type = child.properties.get('cmis:contentStreamMimeType', '').lower()
                        if not content_type.endswith('pdf'):
                            logger.info(f"Skipping non-PDF document: {doc_name} (type: {content_type})")
                            continue
                            
                        logger.info(f"Processing PDF document: {doc_name}")
                        
                        # Save PDF content to temporary file
                        content = child.getContentStream().read()
                        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                            temp_file.write(content)
                            temp_file_path = temp_file.name
                        
                        await process_doc_callback(doc_id, doc_name, temp_file_path)
                        logger.info(f"Successfully processed document: {doc_name}")
                        
                        # Clean up temporary file
                        os.unlink(temp_file_path)
                except Exception as e:
                    logger.error(f"Error processing child: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error accessing folder {folder_path}: {str(e)}")
            raise 