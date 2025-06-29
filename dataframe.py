#!/opt/homebrew/bin/python3
"""
Name: dataframe.py
Purpose: Download and process results from music model evaluations and create a DataFrame
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import os
import re
import pandas as pd
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


# Dataframe processing functions


def parse_results_file(file_path: str) -> list:
    """
    Parse a single results file and extract data for each MIDI file.

    Args:
        file_path: Path to the text file to parse

    Returns:
        List of dictionaries, each representing one MIDI file's results
    """
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    # Extract model and dataset info
    model_match = re.search(r"Model Name:\s*(.+)", content)
    dataset_match = re.search(r"Dataset Name:\s*(.+)", content)

    model_name = model_match.group(1).strip() if model_match else "Unknown"
    dataset_name = dataset_match.group(1).strip() if dataset_match else "Unknown"

    # Extract average f-measure and runtime (optional - file-level statistic)
    avg_f_measure_match = re.search(r"Average F-measure per file:\s*([\d.]+)", content)
    file_avg_f_measure = (
        float(avg_f_measure_match.group(1)) if avg_f_measure_match else None
    )

    avg_runtime_match = re.search(
        r"Average runtime per file:\s*([\d.]+)\s*seconds", content
    )
    file_avg_runtime = float(avg_runtime_match.group(1)) if avg_runtime_match else None

    # Find all MIDI file sections using regex
    midi_sections = re.findall(
        r"(MIDI-[^\n]+\.wav)\n"
        r"Duration:\s*([\d.]+)\s*seconds\n"
        r"Precision:\s*([\d.]+)\n"
        r"Recall:\s*([\d.]+)\n"
        r"F-measure:\s*([\d.]+)\n"
        r"Average_Overlap_Ratio:\s*([\d.]+)\n"
        r"Precision_no_offset:\s*([\d.]+)\n"
        r"Recall_no_offset:\s*([\d.]+)\n"
        r"F-measure_no_offset:\s*([\d.]+)\n"
        r"Average_Overlap_Ratio_no_offset:\s*([\d.]+)\n"
        r"Onset_Precision:\s*([\d.]+)\n"
        r"Onset_Recall:\s*([\d.]+)\n"
        r"Onset_F-measure:\s*([\d.]+)\n"
        r"Offset_Precision:\s*([\d.]+)\n"
        r"Offset_Recall:\s*([\d.]+)\n"
        r"Offset_F-measure:\s*([\d.]+)\n"
        r"Runtime:\s*([\d.]+)\s*seconds",
        content,
    )

    # Convert each MIDI section to a dictionary
    midi_data_list = []
    for _, section in enumerate(midi_sections):
        midi_data = {
            "model_name": model_name,
            "dataset_name": dataset_name,
            "midi_filename": section[0],
            "duration_seconds": float(section[1]),
            "precision": float(section[2]),
            "recall": float(section[3]),
            "f_measure": float(section[4]),
            "average_overlap_ratio": float(section[5]),
            "precision_no_offset": float(section[6]),
            "recall_no_offset": float(section[7]),
            "f_measure_no_offset": float(section[8]),
            "average_overlap_ratio_no_offset": float(section[9]),
            "onset_precision": float(section[10]),
            "onset_recall": float(section[11]),
            "onset_f_measure": float(section[12]),
            "offset_precision": float(section[13]),
            "offset_recall": float(section[14]),
            "offset_f_measure": float(section[15]),
            "runtime": float(section[16]),
        }
        midi_data_list.append(midi_data)

    return midi_data_list


def process_folder(folder_path: str) -> pd.DataFrame:
    """
    Process all text files in the local folder and create a pandas DataFrame.

    Args:
        folder_path: Path to the folder containing text files

    Returns:
        pandas DataFrame with all MIDI file results
    """
    all_midi_data = []

    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.")
        return pd.DataFrame()

    # Get all .txt files in the folder
    txt_files = [f for f in os.listdir(folder_path) if f.endswith(".txt")]

    if not txt_files:
        print(f"No .txt files found in '{folder_path}' folder.")
        return pd.DataFrame()

    print(f"Found {len(txt_files)} text files to process...")

    for filename in txt_files:
        file_path = os.path.join(folder_path, filename)
        try:
            midi_results = parse_results_file(file_path)
            all_midi_data.extend(midi_results)
            print(f"Processed: {filename} ({len(midi_results)} MIDI files)")
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")

    if not all_midi_data:
        print("No data was extracted from the files.")
        return pd.DataFrame()

    # Create DataFrame
    df = pd.DataFrame(all_midi_data)

    print(
        f"\nSuccessfully created DataFrame with {len(df)} rows and {len(df.columns)} columns"
    )
    return df

if __name__ == "__main__":
    print("Downloading details files from cloud...")
    print("=" * 60)

    folder_id = "11zBLIit-Cg7Tu5KHJXZBvaUauFr5Dtbc"
    local_directory = "./visuals"
    count = download_details_files(folder_id, local_directory)
    print(f"Downloaded {count} files")

    print("=" * 60)
    print("Processing music model results...")
    print("=" * 60)

    # Process all files and create DataFrame
    df = process_folder(local_directory)

    if not df.empty:
        # Save DataFrame to CSV and pickle
        df.to_csv(f"{local_directory}/dataframe.csv", index=False)
        df.to_pickle(f"{local_directory}/dataframe.pkl")

    else:
        print(
            f"No data processed. Please check your '{local_directory}' folder and file formats."
        )
