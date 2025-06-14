#!/opt/homebrew/bin/python3
"""
Name: cloning.py
Purpose: Clone GitHub repositories for paper backend
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import os
import shutil
import json
from git import Repo
from concurrent.futures import ThreadPoolExecutor, as_completed

MODELS_FILE = "models.json"


def clone_repo(model):
    model_name = model[0].replace("/", "_")
    github_link = model[1].replace("https://", "")
    username = model[2]
    pat = model[3]

    if not model_name or model_name.strip() in [".", "./"]:
        return (model, False, f"Invalid model name '{model_name}'")

    repo_path = f"./{model_name}"
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)

    try:
        print(f"Cloning: {github_link} to {repo_path}")
        Repo.clone_from(f"https://{username}:{pat}@{github_link}", repo_path)
        with open(f"{repo_path}/details.txt", "w") as f:
            f.write(f"Model Name: {model_name}\n\n")
        return (model, True, None)
    except Exception as e:
        shutil.rmtree(repo_path, ignore_errors=True)
        return (model, False, str(e))


def main():
    if not os.path.exists(MODELS_FILE):
        print(f"Error: The file '{MODELS_FILE}' was not found.")
        return

    try:
        with open(MODELS_FILE, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading '{MODELS_FILE}': {e}")
        return

    all_rows = data.get("values", [])
    if len(all_rows) < 2:
        print(f"Error: Not enough data in '{MODELS_FILE}'.")
        return

    header, spreadsheet = all_rows[0], all_rows[1:]
    valid_models = []

    with ThreadPoolExecutor(max_workers=None) as executor:
        futures = [executor.submit(clone_repo, model) for model in spreadsheet]
        for future in as_completed(futures):
            model, success, error = future.result()
            if success:
                valid_models.append(model)
            else:
                print(f"Failed to clone for {model[0]}: {error}")

    with open(MODELS_FILE, "w") as f:
        json.dump({"values": [header] + valid_models}, f, indent=2)

    print("Cloning process completed!")


if __name__ == "__main__":
    main()
