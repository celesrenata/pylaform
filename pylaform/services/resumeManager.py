import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pylaform.database.connect import db
from pylaform.database.templateWorker import Worker

logger = logging.getLogger(__name__)


class ResumeManager:
    """
    Class to manage multiple resumes for a user.
    Handles creating, copying, renaming, and deleting resumes.
    """

    def __init__(self, user_id=None):
        """
        Initialize the ResumeManager with a user ID.

        :param str user_id: The user ID to manage resumes for
        """
        self.user_id = user_id
        self.table = db()

    def get_all_resumes(self) -> List[Dict[str, Any]]:
        """
        Get all resumes for the current user.

        :return: List of resume objects
        """
        try:
            if not self.user_id:
                logger.warning("No user_id available, cannot get resumes")
                return []

            # Query for all resumes belonging to this user
            response = self.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                ExpressionAttributeValues={
                    ":pk": f"USER#{self.user_id}",
                    ":sk_prefix": "RESUME#"
                }
            )

            resumes = response.get('Items', [])

            # If no resumes exist, create a default one
            if not resumes:
                default_resume_id = self.create_resume("Default Resume")
                if default_resume_id:
                    # Set as active resume
                    self.set_active_resume(default_resume_id)
                    # Fetch the newly created resume
                    return self.get_all_resumes()

            return resumes

        except Exception as e:
            logger.error(f"Error getting resumes: {str(e)}")
            return []

    def get_active_resume_id(self) -> Optional[str]:
        """
        Get the ID of the active resume for the current user.

        :return: The active resume ID or None if not found
        """
        try:
            if not self.user_id:
                logger.warning("No user_id available, cannot get active resume")
                return None

            # Get user metadata which contains active_resume_id
            response = self.table.get_item(
                Key={
                    "PK": f"USER#{self.user_id}",
                    "SK": "METADATA"
                }
            )

            user_metadata = response.get('Item', {})
            active_resume_id = user_metadata.get('active_resume_id')

            # If no active resume is set, get the first resume or create a default one
            if not active_resume_id:
                resumes = self.get_all_resumes()
                if resumes:
                    # Use the first resume as active
                    active_resume_id = resumes[0]['id']
                    self.set_active_resume(active_resume_id)
                else:
                    # Create a default resume
                    active_resume_id = self.create_resume("Default Resume")
                    if active_resume_id:
                        self.set_active_resume(active_resume_id)

            return active_resume_id

        except Exception as e:
            logger.error(f"Error getting active resume ID: {str(e)}")
            return None

    def set_active_resume(self, resume_id: str) -> bool:
        """
        Set the active resume for the current user.

        :param str resume_id: The ID of the resume to set as active
        :return: True if successful, False otherwise
        """
        try:
            if not self.user_id or not resume_id:
                logger.warning("No user_id or resume_id available, cannot set active resume")
                return False

            # Update user metadata with active_resume_id
            response = self.table.update_item(
                Key={
                    "PK": f"USER#{self.user_id}",
                    "SK": "METADATA"
                },
                UpdateExpression="SET active_resume_id = :resume_id, updated_at = :updated_at",
                ExpressionAttributeValues={
                    ":resume_id": resume_id,
                    ":updated_at": datetime.now().isoformat()
                },
                ReturnValues="UPDATED_NEW"
            )

            logger.info(f"Set active resume to {resume_id} for user {self.user_id}")
            return True

        except Exception as e:
            logger.error(f"Error setting active resume: {str(e)}")
            return False

    def create_resume(self, name: str) -> Optional[str]:
        """
        Create a new resume for the current user.

        :param str name: The name of the new resume
        :return: The ID of the newly created resume or None if failed
        """
        try:
            if not self.user_id:
                logger.warning("No user_id available, cannot create resume")
                return None

            # Generate a unique ID for the resume
            resume_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            # Create the resume item
            response = self.table.put_item(
                Item={
                    "PK": f"USER#{self.user_id}",
                    "SK": f"RESUME#{resume_id}",
                    "id": resume_id,
                    "name": name,
                    "created_at": now,
                    "updated_at": now,
                    "type": "resume"
                }
            )

            logger.info(f"Created new resume '{name}' with ID {resume_id} for user {self.user_id}")

            # Always create fresh default identification entries for this new resume
            from pylaform.database.templateWorker import Worker
            worker = Worker(self.user_id)
            # Delete any existing identification for this resume (shouldn't exist, but for safety)
            # Optionally, you could add a method to Worker to clear identification for a resume
            worker.create_default_identification(resume_id=resume_id)

            return resume_id

        except Exception as e:
            logger.error(f"Error creating resume: {str(e)}")
            return None

    def rename_resume(self, resume_id: str, new_name: str) -> bool:
        """
        Rename an existing resume.

        :param str resume_id: The ID of the resume to rename
        :param str new_name: The new name for the resume
        :return: True if successful, False otherwise
        """
        try:
            if not self.user_id or not resume_id:
                logger.warning("No user_id or resume_id available, cannot rename resume")
                return False

            # Update the resume name
            response = self.table.update_item(
                Key={
                    "PK": f"USER#{self.user_id}",
                    "SK": f"RESUME#{resume_id}"
                },
                UpdateExpression="SET #name = :name, updated_at = :updated_at",
                ExpressionAttributeNames={
                    "#name": "name"  # 'name' is a reserved word in DynamoDB
                },
                ExpressionAttributeValues={
                    ":name": new_name,
                    ":updated_at": datetime.now().isoformat()
                },
                ReturnValues="UPDATED_NEW"
            )

            logger.info(f"Renamed resume {resume_id} to '{new_name}' for user {self.user_id}")
            return True

        except Exception as e:
            logger.error(f"Error renaming resume: {str(e)}")
            return False

    def delete_resume(self, resume_id: str) -> bool:
        """
        Delete a resume and all its associated data.

        :param str resume_id: The ID of the resume to delete
        :return: True if successful, False otherwise
        """
        try:
            if not self.user_id or not resume_id:
                logger.warning("No user_id or resume_id available, cannot delete resume")
                return False

            # First check if this is the active resume
            active_resume_id = self.get_active_resume_id()

            # Get all resumes to ensure we don't delete the last one
            all_resumes = self.get_all_resumes()
            if len(all_resumes) <= 1:
                logger.warning("Cannot delete the only resume")
                return False

            # Delete the resume entry
            response = self.table.delete_item(
                Key={
                    "PK": f"USER#{self.user_id}",
                    "SK": f"RESUME#{resume_id}"
                }
            )

            # If we deleted the active resume, set another one as active
            if active_resume_id == resume_id:
                # Find another resume to set as active
                for resume in all_resumes:
                    if resume.get("id") != resume_id:
                        self.set_active_resume(resume.get("id"))
                        break

            logger.info(f"Deleted resume {resume_id} for user {self.user_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting resume: {str(e)}")
            return False

    def get_resume(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific resume by ID.

        :param str resume_id: The ID of the resume to retrieve
        :return: The resume data or None if not found
        """
        try:
            if not self.user_id or not resume_id:
                logger.warning("No user_id or resume_id available, cannot get resume")
                return None

            response = self.table.get_item(
                Key={
                    "PK": f"USER#{self.user_id}",
                    "SK": f"RESUME#{resume_id}"
                }
            )

            return response.get('Item')
        except Exception as e:
            logger.error(f"Error getting resume: {str(e)}")
            return None

    def copy_resume(self, resume_id: str, new_name: str, make_active: bool = False) -> bool:
        """
        Copy an existing resume with a new name

        :param str resume_id: ID of the resume to copy
        :param str new_name: Name for the new resume
        :param bool make_active: Whether to set the new resume as active
        :return: True if successful, False otherwise
        """
        try:
            logger.info(f"Starting copy of resume {resume_id} to '{new_name}' for user {self.user_id}")

            if not self.user_id or not resume_id:
                logger.warning("No user_id or resume_id available, cannot copy resume")
                return False

            # Get the source resume
            source_resume = self.get_resume(resume_id)
            logger.info(f"Source resume data: {source_resume}")

            if not source_resume:
                logger.warning(f"Source resume {resume_id} not found for user {self.user_id}")
                return False

            # Create a new resume with the same data
            new_resume_id = self.create_resume(new_name)
            logger.info(f"Created new resume with ID: {new_resume_id}")

            if not new_resume_id:
                logger.warning(f"Failed to create new resume for user {self.user_id}")
                return False

            # Copy all sections from source to new resume
            source_sections = self._get_resume_sections(resume_id)
            logger.info(f"Found {len(source_sections)} sections to copy")

            for section in source_sections:
                logger.info(f"Copying section: {section.get('name', 'Unnamed')} (ID: {section.get('id')})")
                # Copy section
                new_section_id = self._copy_section(section, new_resume_id)
                logger.info(f"Created new section with ID: {new_section_id}")

                if new_section_id:
                    # Copy items in this section
                    source_items = self._get_section_items(section['id'])
                    logger.info(f"Found {len(source_items)} items to copy in section {section.get('id')}")

                    for item in source_items:
                        item_id = self._copy_item(item, new_section_id)
                        logger.info(f"Copied item with new ID: {item_id}")

            # Set as active if requested
            if make_active:
                logger.info(f"Setting new resume {new_resume_id} as active")
                self.set_active_resume(new_resume_id)

            logger.info(f"Successfully copied resume {resume_id} to new resume {new_resume_id} for user {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Error copying resume: {str(e)}")
            return False

    def _get_resume_sections(self, resume_id: str) -> List[Dict[str, Any]]:
        """
        Get all sections for a resume.

        :param str resume_id: The ID of the resume to get sections for
        :return: List of section objects
        """
        try:
            if not self.user_id or not resume_id:
                logger.warning("Missing user_id or resume_id in _get_resume_sections")
                return []

            # Query for all sections belonging to this resume
            logger.info(f"Querying for sections with PK=RESUME#{resume_id}")
            response = self.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                ExpressionAttributeValues={
                    ":pk": f"RESUME#{resume_id}",
                    ":sk_prefix": "SECTION#"
                }
            )

            sections = response.get('Items', [])
            logger.info(f"Found {len(sections)} sections for resume {resume_id}")
            return sections
        except Exception as e:
            logger.error(f"Error getting resume sections: {str(e)}")
            return []

    def _get_section_items(self, section_id: str) -> List[Dict[str, Any]]:
        """
        Get all items for a section.

        :param str section_id: The ID of the section to get items for
        :return: List of item objects
        """
        try:
            if not section_id:
                return []

            # Query for all items belonging to this section
            response = self.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                ExpressionAttributeValues={
                    ":pk": f"SECTION#{section_id}",
                    ":sk_prefix": "ITEM#"
                }
            )

            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Error getting section items: {str(e)}")
            return []

    def _copy_section(self, source_section: Dict[str, Any], new_resume_id: str) -> Optional[str]:
        """
        Copy a section to a new resume.

        :param Dict[str, Any] source_section: The source section data
        :param str new_resume_id: The ID of the new resume
        :return: The ID of the new section or None if failed
        """
        try:
            # Generate a new section ID
            new_section_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            # Create a new section with the same data but for the new resume
            section_data = {
                "PK": f"RESUME#{new_resume_id}",
                "SK": f"SECTION#{new_section_id}",
                "id": new_section_id,
                "name": source_section.get('name', 'Untitled Section'),
                "type": source_section.get('type', 'default'),
                "order": source_section.get('order', 0),
                "created_at": now,
                "updated_at": now
            }

            # Copy any additional attributes from the source section
            for key, value in source_section.items():
                if key not in ["PK", "SK", "id", "created_at", "updated_at"]:
                    section_data[key] = value

            # Create the new section
            self.table.put_item(Item=section_data)

            return new_section_id
        except Exception as e:
            logger.error(f"Error copying section: {str(e)}")
            return None

    def _copy_item(self, source_item: Dict[str, Any], new_section_id: str) -> Optional[str]:
        """
        Copy an item to a new section.

        :param Dict[str, Any] source_item: The source item data
        :param str new_section_id: The ID of the new section
        :return: The ID of the new item or None if failed
        """
        try:
            # Generate a new item ID
            new_item_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            # Create a new item with the same data but for the new section
            item_data = {
                "PK": f"SECTION#{new_section_id}",
                "SK": f"ITEM#{new_item_id}",
                "id": new_item_id,
                "order": source_item.get('order', 0),
                "created_at": now,
                "updated_at": now
            }

            # Copy any additional attributes from the source item
            for key, value in source_item.items():
                if key not in ["PK", "SK", "id", "created_at", "updated_at"]:
                    item_data[key] = value

            # Create the new item
            self.table.put_item(Item=item_data)

            return new_item_id
        except Exception as e:
            logger.error(f"Error copying item: {str(e)}")
            return None