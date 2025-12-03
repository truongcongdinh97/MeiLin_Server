from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pickle
import os

SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
]

# Đường dẫn file credentials và token cho YouTube
CLIENT_SECRET_FILE = 'youtube_credentials.json'
TOKEN_FILE = 'youtube_token.pickle'


def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=63799)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return build('youtube', 'v3', credentials=creds)

if __name__ == '__main__':
    service = get_authenticated_service()
    print('✅ Đã xác thực OAuth thành công! Token đã lưu vào youtube_token.pickle')
