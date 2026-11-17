import os
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def get_drive_service(client_id, client_secret, refresh_token):
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=credentials)

def upload_or_update_file(service, folder_id, file_path, target_name, overwrite=False):
    """
    Jika overwrite=True:
      Mencari file yang bernama target_name di folder_id.
      Jika ditemukan, lakukan update file content (ID tetap sama).
      Jika tidak ditemukan, buat file baru.
    Jika overwrite=False:
      Selalu buat file baru di folder_id.
    """
    media = MediaFileUpload(file_path, mimetype='application/pdf', resumable=True)

    if overwrite:
        query = f"'{folder_id}' in parents and name = '{target_name}' and trashed = false"
        response = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        files = response.get('files', [])

        if files:
            file_id = files[0]['id']
            print(f"Updating existing file: {target_name} (ID: {file_id})")
            updated_file = service.files().update(
                fileId=file_id,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            print(f"Successfully updated {target_name}. Link: {updated_file.get('webViewLink')}")
            return updated_file

    file_metadata = {
        'name': target_name,
        'parents': [folder_id]
    }
    print(f"Uploading new file: {target_name} to folder {folder_id}")
    new_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink'
    ).execute()
    print(f"Successfully uploaded {target_name}. Link: {new_file.get('webViewLink')}")
    return new_file

def main():
    client_id = os.environ.get('GDRIVE_CLIENT_ID')
    client_secret = os.environ.get('GDRIVE_CLIENT_SECRET')
    refresh_token = os.environ.get('GDRIVE_REFRESH_TOKEN')
    folder_id = os.environ.get('GDRIVE_FOLDER_ID')
    archive_folder_id = os.environ.get('GDRIVE_ARCHIVE_FOLDER_ID')
    pdf_path = os.environ.get('PDF_PATH', 'build/main_buku.pdf')
    version_tag = os.environ.get('VERSION_TAG', 'v0.4.0')
    build_number = os.environ.get('BUILD_NUMBER', '0')
    git_sha = os.environ.get('GIT_SHA', 'latest')

    if not client_id or not client_secret or not refresh_token or not folder_id:
        print("Error: GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN, or GDRIVE_FOLDER_ID missing!")
        sys.exit(1)

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}!")
        sys.exit(1)

    service = get_drive_service(client_id, client_secret, refresh_token)

    # 1. Update/Upload 'Buku-KP-Latest.pdf' di folder utama (selalu overwrite)
    print("\n--- [1/2] Processing Latest Build ---")
    upload_or_update_file(
        service=service,
        folder_id=folder_id,
        file_path=pdf_path,
        target_name='Buku-KP-Latest.pdf',
        overwrite=True
    )

    # 2. Upload arsip berversi ke archive_folder_id jika dikonfigurasi, atau ke folder_id
    target_archive_folder = archive_folder_id if archive_folder_id else folder_id
    archive_name = f"Buku-KP-{version_tag}-b{build_number}-{git_sha}.pdf"
    print(f"\n--- [2/2] Processing Archive Build: {archive_name} ---")
    upload_or_update_file(
        service=service,
        folder_id=target_archive_folder,
        file_path=pdf_path,
        target_name=archive_name,
        overwrite=False
    )

    print("\nAll uploads completed successfully!")

if __name__ == '__main__':
    main()
