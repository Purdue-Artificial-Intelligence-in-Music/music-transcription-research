#!/opt/homebrew/bin/python3
"""
Name: cloning.py
Purpose: Clone GitHub repositories for paper backend
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import time
import os
import shutil
import json
from git import Repo
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess

KEYS_FILE = "keys.json"
MODELS_FILE = "models.json"


def load_json(path):
    if not os.path.exists(path):
        print(f"Error: File '{path}' not found.")
        return None

    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading '{path}': {e}")
        return None


def clone_repo(entry):
    model_name, github_url, username, token = entry
    safe_name = model_name.replace("/", "_")
    github_link = github_url.replace("https://", "")

    if not safe_name or safe_name.strip() in [".", "./"]:
        return (model_name, False, f"Invalid model name '{safe_name}'")

    repo_path = f"./{safe_name}"
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)

    try:
        print(f"Cloning: {github_link} to {repo_path}")
        Repo.clone_from(f"https://{username}:{token}@{github_link}", repo_path)

        subprocess.run(
            ["git", "lfs", "install"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        subprocess.run(["git", "lfs", "pull"], cwd=repo_path, check=True)

        return (model_name, True, None)
    except Exception as e:
        shutil.rmtree(repo_path, ignore_errors=True)
        return (model_name, False, str(e))


def main():
    start_time = time.time()

    keys_data = load_json(KEYS_FILE)
    models_data = load_json(MODELS_FILE)

    if not keys_data or not models_data:
        return

    keys_header, *key_rows = keys_data.get("values", [])
    models_header, *model_rows = models_data.get("values", [])

    # Build model lookups
    desired_models = [row[0] for row in model_rows if row]  # names from models.json
    name_to_model_row = {row[0]: row for row in model_rows if row}
    name_to_key_row = {row[0]: row for row in key_rows if row and len(row) >= 4}

    # Only clone entries that appear in models.json (order taken from models.json)
    entries_to_clone = [
        name_to_key_row[name] for name in desired_models if name in name_to_key_row
    ]

    successful_models = []
    successful_names = set()

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(clone_repo, row) for row in entries_to_clone]
        for future in as_completed(futures):
            model_name, success, error = future.result()
            if success:
                successful_names.add(model_name)
            else:
                print(f"Failed to clone for {model_name}: {error}")

    # Save only the successful models back into models.json (preserve original order)
    for name in desired_models:
        if name in successful_names:
            successful_models.append(name_to_model_row[name])

    with open(MODELS_FILE, "w") as f:
        json.dump({"values": [models_header] + successful_models}, f, indent=2)

    print("Cloning process completed!")
    print(f"Total time taken: {time.time() - start_time:.2f} seconds")


if __name__ == "__main__":
    main()
