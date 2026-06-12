import abc
from typing import Optional, Dict, Any

class StorageAdapter(abc.ABC):
    """
    Abstract interface for file and artifact storage.
    Ensures that business logic relies on logical keys rather than physical paths.
    """

    @abc.abstractmethod
    def save_file(self, logical_path: str, content: bytes, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Saves content to the given logical path.

        :param logical_path: Deterministic logical key (e.g., 'artifacts/exam-1/file.pdf')
        :param content: Byte content to save
        :param metadata: Optional metadata to persist with the file
        :return: The logical path where it was saved
        """
        pass

    @abc.abstractmethod
    def load_file(self, logical_path: str) -> bytes:
        """
        Loads content from the given logical path.

        :param logical_path: Deterministic logical key
        :return: Byte content of the file
        """
        pass

    @abc.abstractmethod
    def delete_file(self, logical_path: str) -> bool:
        """
        Deletes the file at the given logical path.

        :param logical_path: Deterministic logical key
        :return: True if deleted successfully, False otherwise
        """
        pass

    @abc.abstractmethod
    def generate_storage_path(self, prefix: str, filename: str) -> str:
        """
        Generates a standardized, deterministic logical path.

        :param prefix: The category/prefix (e.g., 'submissions', 'screenshots', 'artifacts')
        :param filename: The desired filename (e.g., 'uuid-1234.png')
        :return: The generated logical path string
        """
        pass

    @abc.abstractmethod
    def file_exists(self, logical_path: str) -> bool:
        """
        Checks if a file exists at the given logical path.

        :param logical_path: Deterministic logical key
        :return: True if the file exists
        """
        pass

    @abc.abstractmethod
    def get_metadata(self, logical_path: str) -> Dict[str, Any]:
        """
        Retrieves metadata associated with the logical path.

        :param logical_path: Deterministic logical key
        :return: Dictionary of metadata
        """
        pass
