#!/opt/homebrew/bin/python3
"""
Name: cloning.py
Purpose: Clone GitHub repositories for competition backend
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import os
import shutil
from git import Repo
import json

MODELS_FILE = "models.json"


def main() -> None:
    # Load JSON data from the hardcoded file name 'models.json'
    if not os.path.exists(MODELS_FILE):
        print(f"Error: The file '{MODELS_FILE}' was not found.")
        return

    try:
        with open(MODELS_FILE, "r") as file:
            data = json.load(file)
    except Exception as e:
        print(f"Error reading '{MODELS_FILE}': {e}")
        return

    spreadsheet = data.get("values", [])[1:]  # Skip header row
    if not spreadsheet:
        print(f"Error: No data found in '{MODELS_FILE}'.")
        return

    valid_models = []

    for model in spreadsheet:
        model_name = model[0].replace("/", "_")
        github_link = model[1].replace("https://", "")
        username = model[2]
        pat = model[3]

        if not model_name or model_name.strip() in [".", "./"]:
            print(f"Warning: Invalid model name '{model_name}', skipping...")
            continue

        if os.path.exists(f"./{model_name}"):
            shutil.rmtree(f"./{model_name}")

        print(f"Cloning: {github_link} to ./{model_name}")
        try:
            repo = Repo.clone_from(
                f"https://{username}:{pat}@{github_link}", f"./{model_name}"
            )

            with open(f"{model_name}/details.txt", "w") as file:
                file.write(f"Model Name: {str(model_name)}\n\n")

            valid_models.append(model)

        except Exception as e:
            print(f"Failed to clone {github_link} for {model_name}: {e}")
            shutil.rmtree(f"./{model_name}", ignore_errors=True)
            continue

    with open("models.json", "w") as file:
        json.dump(valid_models, file)

    print("Cloning process completed!")


if __name__ == "__main__":
    main()
