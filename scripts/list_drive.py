#!/usr/bin/env python3
"""
Name: list_drive.py
Purpose: List what has been uploaded to the results Google Drive folder and
         cross-check it against datasets.json expected file counts, so you can
         see at a glance which model x dataset results are present and complete.

Usage:
  python scripts/list_drive.py            # list every uploaded model/dataset folder
  python scripts/list_drive.py --check    # also flag partial/short uploads vs datasets.json

Requires service_account.json (gitignored) in the repo root, same as upload.py.
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import os
import json
import argparse
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

MAIN_FOLDER_ID = "1aP9Nc49RfXheSiV5vmp-AFr5WBuUxDlE"
SERVICE_EMAIL = "ai-music-service-account@aimusicfinal.iam.gserviceaccount.com"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def drive_client():
    gauth = GoogleAuth()
    gauth.settings = {
        "client_config_backend": "service",
        "service_config": {
            "client_json_file_path": os.path.join(REPO_ROOT, "service_account.json"),
            "client_user_email": SERVICE_EMAIL,
        },
        "oauth_scope": ["https://www.googleapis.com/auth/drive"],
    }
    gauth.ServiceAuth()
    return GoogleDrive(gauth)


def list_children(drive, folder_id):
    return drive.ListFile(
        {"q": f"'{folder_id}' in parents and trashed=false"}
    ).GetList()


def expected_counts():
    """Map dataset name -> expected file count from datasets.json (values + disabled)."""
    counts = {}
    try:
        data = json.load(open(os.path.join(REPO_ROOT, "datasets.json")))
    except Exception:
        return counts
    for key in ("values", "disabled"):
        rows = data.get(key, [])
        start = 1 if key == "values" else 0
        for row in rows[start:]:
            if len(row) >= 5 and row[0] != "Dataset Name":
                try:
                    counts[row[0]] = int(row[4])
                except (ValueError, TypeError):
                    pass
    return counts


def main():
    parser = argparse.ArgumentParser(description="List results uploaded to Google Drive.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Flag folders whose Model Output count is short of datasets.json",
    )
    args = parser.parse_args()

    drive = drive_client()
    exp = expected_counts()

    folders = drive.ListFile(
        {
            "q": f"'{MAIN_FOLDER_ID}' in parents and trashed=false "
            "and mimeType='application/vnd.google-apps.folder'"
        }
    ).GetList()

    print(f"{len(folders)} result folder(s) in Drive:\n")
    print(f"{'Model - Dataset':48s} {'MIDIs':>7s}  {'Expected':>8s}  Status")
    print("-" * 78)
    for f in sorted(folders, key=lambda x: x["title"]):
        children = list_children(drive, f["id"])
        mo = next((c for c in children if c["title"] == "Model Output"), None)
        n = len(list_children(drive, mo["id"])) if mo else 0

        # dataset name is the part after " - "; datasets.json uses spaces, Drive
        # folders may use underscores (run.sh sanitizes), so normalize both.
        ds = f["title"].split(" - ", 1)[-1]
        want = exp.get(ds) or exp.get(ds.replace("_", " "))
        status = ""
        if want is not None:
            status = "OK" if n >= want else f"SHORT by {want - n}"
        want_s = str(want) if want is not None else "?"
        line = f"{f['title']:48s} {n:>7d}  {want_s:>8s}  {status}"
        if args.check and status.startswith("SHORT"):
            line = "!! " + line
        print(line)


if __name__ == "__main__":
    main()
