import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_FILE = os.environ.get("TOKEN_JSON_PATH", "/app/token.json")
FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")        # optional
DRIVE_FILE_ID = os.getenv("DRIVE_FILE_ID")      # REQUIRED after first upload


def get_drive_service():
    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError(
            "token.json not found. Generate it locally and upload to Railway."
        )

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def upload_to_drive(local_file, filename):
    try:
        service = get_drive_service()
        media = MediaFileUpload(local_file, resumable=True)

        # 🔁 UPDATE EXISTING FILE (NORMAL MODE)
        if DRIVE_FILE_ID:
            service.files().update(
                fileId=DRIVE_FILE_ID,
                media_body=media,
            ).execute()
            print("☁️ Drive file updated")
            return True

        # ⬆️ FIRST UPLOAD ONLY (RUNS ONCE)
        metadata = {"name": filename}
        if FOLDER_ID:
            metadata["parents"] = [FOLDER_ID]

        file = service.files().create(
            body=metadata,
            media_body=media,
            fields="id",
        ).execute()

        print("☁️ Drive file created")
        print("🟡 SET THIS ENV VAR:")
        print(f"DRIVE_FILE_ID={file['id']}")

        return True

    except HttpError as e:
        print(f"❌ DRIVE ERROR: {e}")
        return False

    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False
