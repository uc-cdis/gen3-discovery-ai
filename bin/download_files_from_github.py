"""
Quick example script that gets all Markdown for the uc-cdis GitHub org
when the GH_TOKEN environment variable is set.

This dumps all the files into a `library` folder with the repo name
afterward and then the files themselves from each repo.
"""
import logging
import os
import time

import requests
from werkzeug.utils import secure_filename

URL = "https://api.github.com/search/code?q=org:uc-cdis+language:Markdown"
GITHUB_TOKEN = str(os.environ.get("GH_TOKEN"))
AUTH_HEADER = {"Authorization": f"Bearer {GITHUB_TOKEN}"}


def create_library():
    """
    Process items by retrieving them from a URL, downloading files, and waiting for a delay.

    Returns:
        None
    """
    per_page = 100
    page = 0
    results = 100

    while results == per_page:
        print(f"Processing page: {page}")
        search_resp = requests.get(
            URL, params={"page": page, "per_page": per_page}, headers=AUTH_HEADER
        )
        print(search_resp)
        assert search_resp.status_code == 200

        items = search_resp.json()["items"]
        results = len(items)
        print(f"Number of items on page {page}: {results}")

        _download_items(items)

        print("Waiting for 7 seconds...")
        time.sleep(7)  # API rate limit

        page += 1


def _download_items(items):
    """
    Download items from a list of JSON items.

    Args:
        items (list): A list of JSON items.

    Returns:
        None
    """
    for item in items:
        repo = item["repository"]["name"]
        file_name = item["name"]
        output_path = f"library/{repo}"
        url = item["url"]
        print(f"Processing URL: {url}")
        try:
            search_res_resp = requests.get(
                url, headers={"Authorization": f"Bearer {GITHUB_TOKEN}"}
            )
        except Exception:
            logging.error(f"ERROR. Unable to download: {file_name}. Skipping...")
            continue

        download_url = search_res_resp.json()["download_url"]
        print(f"Download URL: {download_url}")
        os.makedirs(output_path, exist_ok=True)

        try:
            download_resp = requests.get(download_url)
        except Exception:
            logging.error(f"ERROR. Unable to download: {file_name}. Skipping...")
            continue

        with open(secure_filename(f"{output_path}/{file_name}"), "wb") as output_file:
            output_file.write(download_resp.content)
        print(f"File downloaded to: {output_path}/{file_name}")
        print("------")  # Print a separator for better readability


if __name__ == "__main__":
    create_library()
