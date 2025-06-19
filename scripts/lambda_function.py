# /scripts/acquia_to_hubspot_lambda.py
import os
import json
import time
import logging
import requests
from urllib.parse import urlparse
from typing import List
from hubspot import Client
from hubspot.files import ImportFromUrlInput, ApiException

# Setup logger for AWS Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ENV VARS
ACQUIA_DAM_API_KEY = os.environ.get("ACQUIA_DAM_API_KEY")
HUBSPOT_TOKEN = os.environ.get("HUBSPOT_ACCESS_TOKEN")
ACQUIA_DAM_SEARCH_URL = "https://api.widencollective.com/v2/assets/search"
SYNC_INTERVAL_SECONDS = int(os.environ.get("SYNC_INTERVAL_SECONDS", "300"))
UPLOADED_STATE_FILE = "/tmp/uploaded_assets.json"
LOG_FILE = "/tmp/uploaded_files.log"
HUBSPOT_FOLDER_PATH = "/AI-Generated Media/Images"

# Validate required environment variables
if not ACQUIA_DAM_API_KEY or not HUBSPOT_TOKEN:
    raise EnvironmentError("Missing required environment variables: ACQUIA_DAM_API_KEY or HUBSPOT_ACCESS_TOKEN")

HEADERS_ACQUIA = {"Authorization": f"Bearer {ACQUIA_DAM_API_KEY}"}

client = Client.create(access_token=HUBSPOT_TOKEN)

def validate_dam_token():
    res = requests.get(ACQUIA_DAM_SEARCH_URL, headers=HEADERS_ACQUIA)
    if res.status_code == 401:
        raise Exception("Unauthorized: Check ACQUIA_DAM_API_KEY")
    elif res.status_code != 200:
        raise Exception(f"Failed to validate token: {res.status_code} {res.text}")

def fetch_dam_assets() -> List[dict]:
    all_assets = []
    offset = 0
    limit = 100
    retries = 3

    while True:
        params = {"limit": limit, "offset": offset, "sort": "filename"}
        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(ACQUIA_DAM_SEARCH_URL, headers=HEADERS_ACQUIA, params=params, timeout=10)
                if resp.status_code == 401:
                    raise Exception("Token expired or invalid. Re-authentication needed.")
                resp.raise_for_status()
                break
            except requests.RequestException as e:
                logger.warning(f"[Attempt {attempt}] Failed to fetch assets: {e}")
                if attempt == retries:
                    raise
                backoff = 2 ** attempt
                logger.info(f"Retrying in {backoff}s...")
                time.sleep(backoff)

        data = resp.json()
        items = data.get("items", [])
        if not items:
            break
        all_assets.extend(items)
        offset += limit
    return all_assets

def load_uploaded_state() -> set:
    if not os.path.exists(UPLOADED_STATE_FILE):
        return set()
    try:
        with open(UPLOADED_STATE_FILE, 'r') as f:
            content = f.read().strip()
            return set(json.loads(content)) if content else set()
    except Exception as e:
        logger.warning(f"Failed to parse uploaded state file: {e}")
        return set()

def save_uploaded_state(asset_ids: set):
    with open(UPLOADED_STATE_FILE, 'w') as f:
        json.dump(list(asset_ids), f)

def log_uploaded_asset(asset_id: str, filename: str, hubspot_url: str):
    with open(LOG_FILE, "a") as f:
        f.write(f"{asset_id},{filename},{hubspot_url}\n")

def upload_to_hubspot_from_url(asset: dict, max_retries=3) -> dict:
    download_url = asset.get("_links", {}).get("download")
    filename = asset.get("filename")

    if not download_url or not filename:
        raise ValueError("Missing download URL or filename")

    input_payload = ImportFromUrlInput(
        folder_path=HUBSPOT_FOLDER_PATH,
        access="PUBLIC_INDEXABLE",
        duplicate_validation_scope="ENTIRE_PORTAL",
        name=filename,
        duplicate_validation_strategy="NONE",
        url=download_url,
        overwrite=True
    )

    for attempt in range(1, max_retries + 1):
        try:
            return client.files.files_api.import_from_url(import_from_url_input=input_payload)
        except ApiException as e:
            logger.warning(f"[Attempt {attempt}] Upload failed for {filename}: {e}")
            if attempt == max_retries:
                raise RuntimeError(f"HubSpot upload failed after {max_retries} attempts: {e}")
            sleep_time = 2 ** attempt
            logger.info(f"Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)

def lambda_handler(event, context):
    try:
        validate_dam_token()
        logger.info("✅ DAM token validated.")

        all_assets = fetch_dam_assets()
        uploaded_ids = load_uploaded_state()

        new_assets = [a for a in all_assets if str(a.get("id")) not in uploaded_ids]
        logger.info(f"Found {len(new_assets)} new assets to upload.")

        for i in range(0, len(new_assets), 10):
            batch = new_assets[i:i + 10]
            for asset in batch:
                asset_id = str(asset.get("id"))
                try:
                    upload_resp = upload_to_hubspot_from_url(asset)
                    hubspot_url = upload_resp.get("url")
                    uploaded_ids.add(asset_id)
                    log_uploaded_asset(asset_id, asset.get("filename"), hubspot_url)
                    logger.info(f"Uploaded asset {asset_id}: {hubspot_url}")
                except Exception as e:
                    logger.error(f"Failed to upload asset {asset_id}: {e}")

            save_uploaded_state(uploaded_ids)
            logger.info(f"Batch of {len(batch)} assets processed.")

    except Exception as e:
        logger.exception(f"Lambda execution failed: {e}")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Sync complete."})
    }
