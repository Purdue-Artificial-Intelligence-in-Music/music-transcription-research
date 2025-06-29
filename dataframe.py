#!/opt/homebrew/bin/python3
"""
Name: dataframe.py
Purpose: Download and process results from music model evaluations and create a DataFrame
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


# Google Drive functions


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


def download_details_files(folder_id, local_directory):
    """Download all .txt files containing 'details' from a Google Drive folder and subfolders."""
    drive = authenticate_service_account()

    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    downloaded_count = 0
    downloaded_files = []
    folders_to_search = [folder_id]

    while folders_to_search:
        current_folder_id = folders_to_search.pop(0)
        query = f"'{current_folder_id}' in parents and trashed=false"
        file_list = drive.ListFile({"q": query}).GetList()

        for file in file_list:
            file_name = file["title"]
            mime_type = file["mimeType"]

            # Add subfolders to search queue
            if mime_type == "application/vnd.google-apps.folder":
                folders_to_search.append(file["id"])

            # Download .txt files containing 'details'
            elif file_name.lower().endswith(".txt") and "details" in file_name.lower():
                try:
                    drive_file = drive.CreateFile({"id": file["id"]})
                    safe_filename = file_name.replace("/", "_").replace("\\", "_")
                    local_file_path = os.path.join(local_directory, safe_filename)
                    drive_file.GetContentFile(local_file_path)
                    downloaded_count += 1
                    downloaded_files.append(safe_filename)
                    print(f"Downloaded: {safe_filename}")
                except Exception as e:
                    print(f"Error downloading {file_name}: {str(e)}")

    return downloaded_count

if __name__ == "__main__":
    print("Downloading details files from cloud...")
    print("=" * 60)

    folder_id = "11zBLIit-Cg7Tu5KHJXZBvaUauFr5Dtbc"
    local_directory = "./visuals"
    count = download_details_files(folder_id, local_directory)
    print(f"Downloaded {count} files")

