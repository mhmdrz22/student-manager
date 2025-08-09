import uuid
import os
from fastapi import UploadFile

def secure_filename(filename: str) -> str:
    """
    Generates a secure, unique filename for an uploaded file.
    """
    # Get the file extension
    ext = os.path.splitext(filename)[1]
    # Generate a unique filename using UUID
    unique_filename = f"{uuid.uuid4()}{ext}"
    return unique_filename

def save_upload_file(upload_file: UploadFile, destination: str) -> str:
    """
    Saves an uploaded file to a destination with a secure filename.
    """
    try:
        # Ensure the destination directory exists
        os.makedirs(destination, exist_ok=True)

        # Generate a secure filename
        new_filename = secure_filename(upload_file.filename)
        file_path = os.path.join(destination, new_filename)

        # Save the file
        with open(file_path, "wb") as buffer:
            buffer.write(upload_file.file.read())

        return file_path
    finally:
        upload_file.file.close()
