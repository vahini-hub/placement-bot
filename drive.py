import os
import json
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_drive_service():
    token_info = json.loads(os.environ["TOKEN_JSON"])
    creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    return build("drive", "v3", credentials=creds)
def upload_to_drive(local_path, filename, retries=3):
    folder_id = os.environ.get("DRIVE_FOLDER_ID")

    for attempt in range(1, retries + 1):
        try:
            service = get_drive_service()

            # 🔍 Look ONLY inside the target folder
            query = (
                f"name='{filename}' "
                f"and '{folder_id}' in parents "
                f"and trashed=false"
            )

            results = service.files().list(
                q=query,
                fields="files(id)",
                spaces="drive"
            ).execute()

            media = MediaFileUpload(
                local_path,
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

            if results["files"]:
                # ♻ Update existing file
                service.files().update(
                    fileId=results["files"][0]["id"],
                    media_body=media
                ).execute()
            else:
                # 🆕 Create file inside folder
                service.files().create(
                    body={
                        "name": filename,
                        "parents": [folder_id]
                    },
                    media_body=media,
                    fields="id"
                ).execute()

            print("✅ Drive sync successful")
            return True

        except HttpError as e:
            print(f"⚠️ Drive sync failed (attempt {attempt}/{retries})")
            print(e)
            time.sleep(2)

    print("❌ Drive sync failed after all retries")
    return False
