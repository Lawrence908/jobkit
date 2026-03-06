"""Google Drive upload."""
import logging
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.core.config import get_settings
from app.utils.files import ensure_safe_relative_path

logger = logging.getLogger(__name__)


def upload_file(creds: Credentials, local_path: Path, name: str, mime: str, folder_id: str | None) -> tuple[str, str]:
    """Upload a file to Drive. Returns (file_id, web_view_link)."""
    service = build("drive", "v3", credentials=creds)
    body = {"name": name}
    if folder_id:
        body["parents"] = [folder_id]
    media = MediaFileUpload(str(local_path), mimetype=mime, resumable=False)
    f = service.files().create(body=body, media_body=media, fields="id,webViewLink").execute()
    return f["id"], f.get("webViewLink", f"https://drive.google.com/file/d/{f['id']}/view")


def ensure_folder(creds: Credentials, parent_id: str | None, name: str) -> str:
    """Create folder if not exists; return folder id."""
    service = build("drive", "v3", credentials=creds)
    q = f"name = '{name}' and trashed = false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    r = service.files().list(q=q, spaces="drive", fields="files(id)").execute()
    files = r.get("files", [])
    if files:
        return files[0]["id"]
    body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        body["parents"] = [parent_id]
    f = service.files().create(body=body, fields="id").execute()
    return f["id"]
