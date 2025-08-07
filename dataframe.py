#!/opt/homebrew/bin/python3
"""
Name: dataframe.py
Purpose: Download and process results from music model evaluations and create a DataFrame
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import os
import json
import re
import pandas as pd
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from concurrent.futures import ThreadPoolExecutor, as_completed
from googleapiclient.http import build_http
from time import time


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
    gauth.http = build_http()
    return GoogleDrive(gauth)


def download_details_files(folder_id, local_directory):
    """Download all .txt files containing 'details' from a Google Drive folder and subfolders using concurrency."""
    drive = authenticate_service_account()

    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    downloaded_files = []
    folders_to_search = [(folder_id, None)]  # (folder_id, folder_name)
    download_tasks = []

    while folders_to_search:
        current_folder_id, parent_folder_name = folders_to_search.pop(0)
        query = f"'{current_folder_id}' in parents and trashed=false"
        file_list = drive.ListFile({"q": query}).GetList()

        for file in file_list:
            file_name = file["title"]
            mime_type = file["mimeType"]

            # Add subfolders to search queue
            if mime_type == "application/vnd.google-apps.folder":
                folders_to_search.append((file["id"], file_name))

            # Download .txt files containing 'details'
            elif file_name.lower().endswith(".txt") and "details" in file_name.lower():
                download_tasks.append((file, parent_folder_name))

    print(f"Found {len(download_tasks)} files to download...")

    def download_file(file_info):
        file, parent_folder_name = file_info
        try:
            drive_file = drive.CreateFile({"id": file["id"]})
            if parent_folder_name:
                clean_folder_name = (
                    parent_folder_name.replace(" - ", "_")
                    .replace(" ", "_")
                    .replace("-", "_")
                )
                new_filename = f"{clean_folder_name}.txt"
            else:
                new_filename = file["title"].replace("/", "_").replace("\\", "_")

            local_file_path = os.path.join(local_directory, new_filename)
            drive_file.GetContentFile(local_file_path)
            print(f"Downloaded: {new_filename}")
            return new_filename
        except Exception as e:
            print(f"Error downloading {file['title']}: {str(e)}")
            return None

    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(download_file, task): task for task in download_tasks
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                downloaded_files.append(result)

    return len(downloaded_files)


# Dataframe processing functions


def load_expected_counts(json_path: str) -> dict:
    """
    Load dataset expected counts from datasets.json file.

    Args:
        json_path: Path to the JSON file

    Returns:
        Dictionary mapping dataset names to expected counts
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    header = data["values"][0]
    name_idx = header.index("Dataset Name")
    count_idx = header.index("Count")

    expected_counts = {}
    for row in data["values"][1:]:
        dataset_name = row[name_idx]
        count = int(row[count_idx])
        expected_counts[dataset_name] = count

    return expected_counts


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
    avg_f_measure_match = re.search(r"Average F-measure:\s*(-?[\d.]+)", content)
    file_avg_f_measure = (
        float(avg_f_measure_match.group(1)) if avg_f_measure_match else None
    )

    avg_runtime_match = re.search(
        r"Average Runtime (seconds):\s*(-?[\d.]+)\s*seconds", content
    )
    file_avg_runtime = float(avg_runtime_match.group(1)) if avg_runtime_match else None

    # Find all MIDI file sections using regex
    midi_sections = re.findall(
        r"([^\n]+\.wav)\n"
        r"Duration:\s*(-?[\d.]+)\s*seconds\n"
        r"Reference MIDI Instruments:\s*(-?[\d.]+)\n"
        r"Transcription MIDI Instruments:\s*(-?[\d.]+)\n"
        r"Precision:\s*(-?[\d.]+)\n"
        r"Recall:\s*(-?[\d.]+)\n"
        r"F-measure:\s*(-?[\d.]+)\n"
        r"Average_Overlap_Ratio:\s*(-?[\d.]+)\n"
        r"Precision_no_offset:\s*(-?[\d.]+)\n"
        r"Recall_no_offset:\s*(-?[\d.]+)\n"
        r"F-measure_no_offset:\s*(-?[\d.]+)\n"
        r"Average_Overlap_Ratio_no_offset:\s*(-?[\d.]+)\n"
        r"Onset_Precision:\s*(-?[\d.]+)\n"
        r"Onset_Recall:\s*(-?[\d.]+)\n"
        r"Onset_F-measure:\s*(-?[\d.]+)\n"
        r"Offset_Precision:\s*(-?[\d.]+)\n"
        r"Offset_Recall:\s*(-?[\d.]+)\n"
        r"Offset_F-measure:\s*(-?[\d.]+)\n"
        r"Runtime:\s*(-?[\d.]+)\s*seconds",
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
            "reference_midi_instruments": int(section[2]),
            "transcription_midi_instruments": int(section[3]),
            "precision": float(section[4]),
            "recall": float(section[5]),
            "f_measure": float(section[6]),
            "average_overlap_ratio": float(section[7]),
            "precision_no_offset": float(section[8]),
            "recall_no_offset": float(section[9]),
            "f_measure_no_offset": float(section[10]),
            "average_overlap_ratio_no_offset": float(section[11]),
            "onset_precision": float(section[12]),
            "onset_recall": float(section[13]),
            "onset_f_measure": float(section[14]),
            "offset_precision": float(section[15]),
            "offset_recall": float(section[16]),
            "offset_f_measure": float(section[17]),
            "runtime": float(section[18]),
        }
        midi_data_list.append(midi_data)

    return midi_data_list


from concurrent.futures import ThreadPoolExecutor, as_completed


def process_folder(folder_path: str) -> pd.DataFrame:
    """
    Process all text files in the local folder and create a pandas DataFrame.
    Uses concurrency to process files in parallel.

    Args:
        folder_path: Path to the folder containing text files

    Returns:
        pandas DataFrame with all MIDI file results
    """
    all_midi_data = []
    file_parsed_counts = {}

    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.")
        return pd.DataFrame()

    # Get all .txt files in the folder
    txt_files = [f for f in os.listdir(folder_path) if f.endswith(".txt")]

    if not txt_files:
        print(f"No .txt files found in '{folder_path}' folder.")
        return pd.DataFrame()

    print(f"Found {len(txt_files)} text files to process...")

    def parse_file_concurrently(filename):
        file_path = os.path.join(folder_path, filename)
        try:
            midi_results = parse_results_file(file_path)
            return (filename, midi_results)
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            return (filename, [])

    with ThreadPoolExecutor() as executor:
        future_to_file = {
            executor.submit(parse_file_concurrently, filename): filename
            for filename in txt_files
        }

        for future in as_completed(future_to_file):
            filename, midi_results = future.result()
            all_midi_data.extend(midi_results)
            file_parsed_counts[filename] = len(midi_results)
            print(f"Processed: {filename} ({len(midi_results)} MIDI files)")

    expected_counts_path = "datasets.json"
    EXPECTED_COUNTS = load_expected_counts(expected_counts_path)

    for filename in txt_files:
        dataset_name = next(
            (ds for ds in EXPECTED_COUNTS if ds.lower() in filename.lower()), None
        )
        expected_count = EXPECTED_COUNTS.get(dataset_name, None)
        parsed_count = file_parsed_counts.get(filename, 0)

        if expected_count is not None and parsed_count != expected_count:
            print(
                f"\nERROR: {filename:<40} | Dataset: {dataset_name:<10} | Expected {expected_count}, Found {parsed_count}"
            )

    if not all_midi_data:
        print("No data was extracted from the files.")
        return pd.DataFrame()

    # Create DataFrame
    df = pd.DataFrame(all_midi_data)

    print(
        f"\nSuccessfully created DataFrame with {len(df)} rows and {len(df.columns)} columns"
    )
    return df


def print_dataframe_info(df: pd.DataFrame):
    """
    Print basic information about the DataFrame.

    Args:
        df: DataFrame to analyze
    """
    if df.empty:
        print("DataFrame is empty.")
        return

    print("\n" + "=" * 60)
    print("DATAFRAME INFORMATION")
    print("=" * 60)

    print(f"Shape: {df.shape}")
    print(f"\nColumns: {list(df.columns)}")

    print(f"\nUnique models: {df['model_name'].nunique()}")
    print(f"Models: {df['model_name'].unique().tolist()}")

    print(f"\nUnique datasets: {df['dataset_name'].nunique()}")
    print(f"Datasets: {df['dataset_name'].unique().tolist()}")

    # Basic statistics for key metrics
    print(f"\nKey Metrics Summary:")
    print("-" * 30)
    key_metrics = ["precision", "recall", "f_measure", "runtime"]
    for metric in key_metrics:
        if metric in df.columns:
            print(
                f"{metric.capitalize()}: "
                f"mean={df[metric].mean():.4f}, "
                f"std={df[metric].std():.4f}, "
                f"min={df[metric].min():.4f}, "
                f"max={df[metric].max():.4f}"
            )


if __name__ == "__main__":
    start_time = time()
    print("Downloading details files from cloud...")
    print("=" * 60)

    folder_id = "11zBLIit-Cg7Tu5KHJXZBvaUauFr5Dtbc"
    local_directory = "./data"
    count = download_details_files(folder_id, local_directory)
    print(f"Downloaded {count} files")

    print("=" * 60)
    print("Processing music model results...")
    print("=" * 60)

    # Process all files and create DataFrame
    df = process_folder(local_directory)

    if not df.empty:
        print_dataframe_info(df)

        # Save DataFrame to CSV and pickle
        df.to_csv(f"{local_directory}/dataframe.csv", index=False)
        df.to_pickle(f"{local_directory}/dataframe.pkl")

    else:
        print(
            f"No data processed. Please check your '{local_directory}' folder and file formats."
        )

    # Delete all .txt files in the local directory
    for file in os.listdir(local_directory):
        if file.endswith(".txt"):
            os.remove(os.path.join(local_directory, file))

    end_time = time()
    print(f"\nTotal processing time: {end_time - start_time:.2f}")
