import os
import shutil

class FileAgent:
    def __init__(self, project_id, bot_username):
        self.project_id = str(project_id)
        self.bot_username = bot_username
        self.base_path = os.path.abspath(os.path.join("projects", self.project_id, self.bot_username))

        # Ensure the base directory exists
        os.makedirs(self.base_path, exist_ok=True)

    def get_project_structure(self):
        """
        Returns a flat list of file paths (including subfolders) from the base path.
        Example: ['bot/handlers/image_handler.py', 'main.py']
        """
        structure = []
        for root, _, files in os.walk(self.base_path):
            for file in files:
                rel_dir = os.path.relpath(root, self.base_path)
                rel_file = os.path.join(rel_dir, file) if rel_dir != "." else file
                structure.append(rel_file.replace(os.sep, "/"))  # Ensure Unix-style path
        return structure


    def read_file(self, relative_path):
        """
        Reads the contents of a file relative to the project root.
        """
        full_path = os.path.join(self.base_path, relative_path)
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File '{relative_path}' not found.")
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def write_to_file(self, relative_path, content):
        """
        Writes content to a file. Creates any missing directories along the path.
        """
        full_path = os.path.join(self.base_path, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def delete_file(self, relative_path):
        """
        Deletes a file if it exists.
        """
        full_path = os.path.join(self.base_path, relative_path)
        if os.path.isfile(full_path):
            os.remove(full_path)
        else:
            raise FileNotFoundError(f"File '{relative_path}' not found.")

    def file_exists(self, relative_path):
        """
        Returns True if the file exists.
        """
        full_path = os.path.join(self.base_path, relative_path)
        return os.path.isfile(full_path)

    def create_file(self, relative_path):
        """
        Creates an empty file if it doesn't exist.
        """
        full_path = os.path.join(self.base_path, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        if not os.path.isfile(full_path):
            with open(full_path, "w", encoding="utf-8") as f:
                f.write("")

    def create_folder(self, relative_path):
        """
        Creates a folder (and any missing parent folders).
        """
        full_path = os.path.join(self.base_path, relative_path)
        os.makedirs(full_path, exist_ok=True)

    def delete_folder(self, relative_path):
        """
        Deletes a folder and all its contents.
        """
        full_path = os.path.join(self.base_path, relative_path)
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            raise FileNotFoundError(f"Folder '{relative_path}' not found.")
    
