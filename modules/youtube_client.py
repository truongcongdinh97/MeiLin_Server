"""
YouTube Client - Hiện tại để mô phỏng, sẽ tích hợp sau
"""

import pickle
import os
from googleapiclient.discovery import build

class YouTubeClient:
    def __init__(self, video_id=None):
        self.video_id = video_id or "r7MYQQhjngw" # livestream video id
        self.youtube = self.get_authenticated_service()
        self.live_chat_id = None
        if self.video_id:
            self.live_chat_id = self.get_live_chat_id(self.video_id)

    def get_authenticated_service(self):
        TOKEN_FILE = 'youtube_token.pickle'
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
            return build('youtube', 'v3', credentials=creds)
        else:
            raise Exception("Chưa xác thực OAuth. Hãy chạy youtube_auth.py trước!")

    def get_live_chat_id(self, video_id):
        response = self.youtube.videos().list(
            part='liveStreamingDetails',
            id=video_id
        ).execute()
        items = response.get('items', [])
        if not items or 'liveStreamingDetails' not in items[0] or 'activeLiveChatId' not in items[0]['liveStreamingDetails']:
            print(f"[ERROR] Không tìm thấy live chat cho video_id: {video_id}. Đáp trả API: {response}")
            raise Exception(f"Không tìm thấy live chat cho video_id: {video_id}")
        return items[0]['liveStreamingDetails']['activeLiveChatId']

    def get_live_chat_messages(self):
        if not self.live_chat_id:
            return []
        response = self.youtube.liveChatMessages().list(
            liveChatId=self.live_chat_id,
            part='snippet,authorDetails',
            maxResults=20
        ).execute()
        messages = []
        for item in response['items']:
            messages.append({
                'user_id': item['authorDetails']['channelId'],
                'username': item['authorDetails']['displayName'],
                'message': item['snippet']['displayMessage']
            })
        return messages

    async def get_new_messages(self):
        # Trả về tin nhắn thật từ livestream nếu có video_id, ngược lại trả về mô phỏng
        if self.live_chat_id:
            # Lọc trùng tin nhắn dựa trên message_id
            if not hasattr(self, '_last_message_ids'):
                self._last_message_ids = set()
            response = self.youtube.liveChatMessages().list(
                liveChatId=self.live_chat_id,
                part='id,snippet,authorDetails',
                maxResults=20
            ).execute()
            print("[DEBUG] YouTube API response:", response)  # Log toàn bộ response
            new_messages = []
            for item in response.get('items', []):
                msg_id = item.get('id')
                if msg_id not in self._last_message_ids:
                    new_messages.append({
                        'user_id': item.get('authorDetails', {}).get('channelId'),
                        'username': item.get('authorDetails', {}).get('displayName'),
                        'message': item.get('snippet', {}).get('displayMessage'),
                        'timestamp': item.get('snippet', {}).get('publishedAt'),
                        'id': msg_id
                    })
                    self._last_message_ids.add(msg_id)
            return new_messages
        # Nếu chưa có video_id, trả về tin nhắn mô phỏng như cũ
        simulated_messages = [
            "Chào MeiLin!",
            "Bạn là ai thế?",
            "Hôm nay bạn khỏe không?",
            "Kể cho mình nghe về AI đi",
            "Bạn có thích chơi game không?",
            "Tôi mới biết đến kênh của bạn",
            "Airi dễ thương quá!",
            "Bạn có thể hát không?",
            "Công nghệ AI đang phát triển thế nào?",
            "Tạm biệt Airi!"
        ]
        if not hasattr(self, 'message_index'):
            self.message_index = 0
        if self.message_index < len(simulated_messages):
            msg = simulated_messages[self.message_index]
            self.message_index += 1
            return [{"author": "Người xem", "message": msg}]
        return []