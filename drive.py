import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]
def upload_to_drive(local_file, drive_filename):
    try:
        creds_json = json.loads(os.getenv("GDRIVE_JSON"))
        folder_id = os.getenv("GDRIVE_FOLDER_ID")

        creds = Credentials.from_service_account_info(
            creds_json, scopes=SCOPES
        )
        service = build("drive", "v3", credentials=creds)

        results = service.files().list(
            q=f"name='{drive_filename}' and '{folder_id}' in parents and trashed=false",
            fields="files(id)"
        ).execute()

        media = MediaFileUpload(
            local_file,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        files = results.get("files", [])
        if files:
            service.files().update(
                fileId=files[0]["id"],
                media_body=media
            ).execute()
            print("☁️ Drive UPDATED")
        else:
            service.files().create(
                body={"name": drive_filename, "parents": [folder_id]},
                media_body=media
            ).execute()
            print("☁️ Drive CREATED")

        return True   # ✅ SUCCESS

    except Exception as e:
        print("❌ DRIVE SYNC FAILED:", e)
        return False  # ❌ FAILURE
