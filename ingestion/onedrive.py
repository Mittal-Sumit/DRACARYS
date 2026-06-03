"""
OneDrive / SharePoint document downloader via Microsoft Graph API.

Authentication: MSAL device-code flow.
  - First run: prints a URL + one-time code → user opens browser, logs in once.
  - Subsequent runs: token is refreshed silently from .msal_cache.json.

Required .env vars:
    ONEDRIVE_TENANT_ID     Azure AD Directory (tenant) ID
    ONEDRIVE_CLIENT_ID     App registration client ID
    ONEDRIVE_SHARING_URL   Full OneDrive/SharePoint sharing link (folder)

Azure app setup (one-time, ~3 minutes):
    1. portal.azure.com → Azure Active Directory → App registrations → New registration
    2. Name: Dracarys | Accounts: this org only | No redirect URI
    3. Authentication tab → enable "Allow public client flows" → Save
    4. API permissions → Add → Microsoft Graph → Delegated → Files.Read → Add
    5. Copy Application (client) ID and Directory (tenant) ID into .env
"""

import base64
import os
import tempfile
from pathlib import Path

import requests
from dotenv import load_dotenv
from msal import PublicClientApplication, SerializableTokenCache

load_dotenv(Path(__file__).parent.parent / ".env")

_TENANT_ID = os.getenv("ONEDRIVE_TENANT_ID", "")
_CLIENT_ID = os.getenv("ONEDRIVE_CLIENT_ID", "")
_SHARING_URL = os.getenv("ONEDRIVE_SHARING_URL", "")
_SCOPES = ["https://graph.microsoft.com/Files.Read"]
_CACHE_FILE = Path(__file__).parent.parent / ".msal_cache.json"
_GRAPH = "https://graph.microsoft.com/v1.0"
_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc"}


# ── Auth ──────────────────────────────────────────────────────────────────────

def _load_cache() -> SerializableTokenCache:
    cache = SerializableTokenCache()
    if _CACHE_FILE.exists():
        cache.deserialize(_CACHE_FILE.read_text(encoding="utf-8"))
    return cache


def _save_cache(cache: SerializableTokenCache) -> None:
    if cache.has_state_changed:
        _CACHE_FILE.write_text(cache.serialize(), encoding="utf-8")


def _get_token() -> str:
    """Return a valid Graph API access token. Prompts once via device code if needed."""
    if not _TENANT_ID or not _CLIENT_ID:
        raise ValueError(
            "ONEDRIVE_TENANT_ID and ONEDRIVE_CLIENT_ID must be set in .env.\n"
            "See ingestion/onedrive.py header for setup instructions."
        )

    cache = _load_cache()
    app = PublicClientApplication(
        client_id=_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{_TENANT_ID}",
        token_cache=cache,
    )

    # Try silent refresh first (cached token)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(_SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _save_cache(cache)
            return result["access_token"]

    # First run — device code flow
    flow = app.initiate_device_flow(scopes=_SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Device flow initiation failed: {flow.get('error_description', flow)}")

    print("\n" + "=" * 60)
    print("OneDrive authentication required (one-time).")
    print(flow["message"])
    print("=" * 60 + "\n")

    result = app.acquire_token_by_device_flow(flow)  # blocks until user logs in
    if "access_token" not in result:
        raise RuntimeError(f"Authentication failed: {result.get('error_description', result)}")

    _save_cache(cache)
    return result["access_token"]


# ── Graph API helpers ─────────────────────────────────────────────────────────

def _encode_sharing_url(url: str) -> str:
    """Encode a sharing URL for the Graph /shares/{id} endpoint."""
    b64 = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    return f"u!{b64}"


def _get(url: str, headers: dict, **kwargs) -> dict:
    resp = requests.get(url, headers=headers, timeout=30, **kwargs)
    resp.raise_for_status()
    return resp.json()


def _list_folder_files(token: str, sharing_url: str) -> list[dict]:
    """Return all supported files in the shared folder, handling pagination."""
    headers = {"Authorization": f"Bearer {token}"}
    encoded = _encode_sharing_url(sharing_url)

    # Resolve the sharing link → folder driveItem
    folder = _get(f"{_GRAPH}/shares/{encoded}/driveItem", headers)

    drive_id = folder["parentReference"]["driveId"]
    folder_id = folder["id"]

    files = []
    url = f"{_GRAPH}/drives/{drive_id}/items/{folder_id}/children"
    while url:
        page = _get(url, headers)
        for item in page.get("value", []):
            if "folder" not in item and Path(item["name"]).suffix.lower() in _SUPPORTED_EXTENSIONS:
                files.append(item)
        url = page.get("@odata.nextLink")  # handle pagination

    return files


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_docs_to_tempdir() -> tuple[str, list[str]]:
    """
    Authenticate, list files in the shared OneDrive folder, download all
    PDF/DOCX files to a temporary directory.

    Returns:
        (tmp_dir_path, [list_of_downloaded_file_paths])

    The caller must delete tmp_dir after use (use try/finally).
    """
    if not _SHARING_URL:
        raise ValueError("ONEDRIVE_SHARING_URL is not set in .env")

    token = _get_token()
    files = _list_folder_files(token, _SHARING_URL)

    if not files:
        raise RuntimeError("No PDF/DOCX files found in the OneDrive folder.")

    print(f"Found {len(files)} document(s) in OneDrive: {[f['name'] for f in files]}")

    tmp_dir = tempfile.mkdtemp(prefix="dracarys_onedrive_")
    headers = {"Authorization": f"Bearer {token}"}
    downloaded = []

    for item in files:
        name = item["name"]
        # downloadUrl is pre-authenticated and works without the Bearer header
        download_url = item.get("@microsoft.graph.downloadUrl")
        if not download_url:
            # Fetch fresh item to get the download URL
            drive_id = item["parentReference"]["driveId"]
            fresh = _get(f"{_GRAPH}/drives/{drive_id}/items/{item['id']}", headers)
            download_url = fresh.get("@microsoft.graph.downloadUrl")

        if not download_url:
            print(f"  Skipping {name} — could not get download URL")
            continue

        dest = Path(tmp_dir) / name
        print(f"  Downloading {name}...")
        resp = requests.get(download_url, timeout=120)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        downloaded.append(str(dest))

    print(f"Downloaded {len(downloaded)} file(s) to temp directory.")
    return tmp_dir, downloaded
