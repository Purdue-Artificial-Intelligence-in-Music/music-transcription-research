#!/opt/homebrew/bin/python3
"""
Name: upload.py
Purpose: Upload files to Google Drive using an IAM service account
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os
import argparse


def authenticate_service_account():
    """Authenticate with Google Drive using a service account."""
    gauth = GoogleAuth()
    gauth.settings = {
        "client_config_backend": "service",
        "service_config": {
            "client_json_file_path": "service_account.json",
            "client_user_email": "ai-music-service-account@aimusicfinal.iam.gserviceaccount.com",
        },
        "oauth_scope": [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.appdata",
        ],
    }
    gauth.ServiceAuth()
    return GoogleDrive(gauth)


def check_folder_exists(drive, folder_name, parent_folder_id):
    """Check if a folder with a given name already exists in Google Drive and return its ID and link."""
    query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and title='{folder_name}'"
    file_list = drive.ListFile({"q": query}).GetList()

    if file_list:
        folder_id = file_list[0]["id"]
        folder_link = f"https://drive.google.com/drive/folders/{folder_id}"
        print(f"Folder '{folder_name}' already exists with ID: {folder_id}")
        print(f"Folder link: {folder_link}")
        return folder_id, folder_link  # Return folder ID and link

    return None, None  # Folder does not exist


def create_folder(drive, model_name, dataset_name, parent_folder_id=None):
    """Create a folder in Google Drive (or return existing folder details) and return its ID and link."""
    folder_name = f"{model_name} - {dataset_name}"
    folder_id, folder_link = check_folder_exists(drive, folder_name, parent_folder_id)
    if folder_id:
        return folder_id, folder_link  # Return existing folder details

    print(f"Folder '{folder_name}' does not exist.")

    # Create a new folder if it does not exist
    folder_metadata = {
        "title": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_folder_id:
        folder_metadata["parents"] = [{"id": parent_folder_id}]

    folder = drive.CreateFile(folder_metadata)
    folder.Upload()

    # Make folder public (anyone can view)
    folder.InsertPermission(
        {
            "type": "anyone",
            "role": "reader",
        }
    )

    folder_id = folder["id"]
    folder_link = f"https://drive.google.com/drive/folders/{folder_id}"

    print(f"Created new folder '{folder_name}' with ID: {folder_id}")
    print(f"Folder link: {folder_link}")

    return folder_id, folder_link


def upload_files_to_folder(drive, local_directory, folder_id, output_folder_id=None):
    """Upload all files from a local directory to the specified Google Drive folder.
    MP3 files will be uploaded to a separate MP3 Input folder if provided.
    """
    for filename in os.listdir(local_directory):
        file_path = os.path.join(local_directory, filename)
        if os.path.isfile(file_path):
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext == ".mid" or file_ext == ".midi" or file_ext == ".pdf":
                target_folder_id = output_folder_id
            else:
                target_folder_id = folder_id

            file = drive.CreateFile(
                {"title": filename, "parents": [{"id": target_folder_id}]}
            )
            file.SetContentFile(file_path)
            file.Upload()
            print(f"Uploaded {filename} to folder ID: {target_folder_id}")


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(
        description="Upload files to a Google Drive folder using a service account."
    )
    parser.add_argument(
        "--main-folder",
        required=True,
        help="ID of the main parent folder in Google Drive",
    )
    parser.add_argument(
        "--model-name",
        required=True,
        help="Name of the model",
    )
    parser.add_argument(
        "--dataset-name",
        required=True,
        help="Name of the dataset",
    )
    parser.add_argument(
        "--local-directory",
        required=True,
        help="Local directory containing files to upload",
    )
    args = parser.parse_args()

    print("Arguments Received:")
    print(f"\tMain Folder ID: {args.main_folder}")
    print(f"\tModel Name: {args.model_name}")
    print(f"\tDataset Name: {args.dataset_name}")
    print(f"\tLocal Directory: {args.local_directory}")

    drive = authenticate_service_account()

    # Get or create the model folder
    model_folder_id, model_folder_link = create_folder(
        drive, args.model_name, args.dataset_name, args.main_folder
    )
    print(f"Using folder for {args.model_name} with ID: {model_folder_id}")
    print(f"\tModel folder link: {model_folder_link}")

    # Create Output subfolder inside the submission folder
    output_folder_name = "Model Output"
    output_folder_id, output_folder_link = create_folder(
        drive, output_folder_name, subfolder_id
    )
    print(f"\tModel Output subfolder link: {output_folder_link}")

    # Upload files, routing .mp3s into the MP3 Input folder
    upload_files_to_folder(drive, args.local_directory, subfolder_id, output_folder_id)


if __name__ == "__main__":
    main()
