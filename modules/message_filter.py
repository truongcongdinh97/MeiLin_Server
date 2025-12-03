import time

class MessageFilter:
    def __init__(self):
        self.start_timestamp = None
        self.seen_message_ids = set()

    def set_start_timestamp(self):
        self.start_timestamp = time.time()

    def filter_new_messages(self, messages, timestamp_key='publishedAt', id_key='id'):
        # Chỉ giữ lại tin nhắn sau khi khởi động
        if not self.start_timestamp:
            self.set_start_timestamp()
        filtered = []
        for msg in messages:
            msg_time = self._parse_timestamp(msg.get(timestamp_key))
            msg_id = msg.get(id_key)
            if msg_time and msg_time >= self.start_timestamp and msg_id not in self.seen_message_ids:
                filtered.append(msg)
                self.seen_message_ids.add(msg_id)
        return filtered

    def _parse_timestamp(self, ts):
        # Chuyển đổi ISO8601 sang epoch
        if not ts:
            return None
        try:
            import dateutil.parser
            dt = dateutil.parser.parse(ts)
            return dt.timestamp()
        except Exception:
            return None

    def is_short_message(self, msg, min_length=4):
        return len(msg.get('message', '')) <= min_length

    def save_sample_message(self, msg, db):
        # Lưu tin nhắn mẫu vào database (db là ChatHistoryDB)
        db.add_chat_history(
            user_id=msg.get('user_id', 'unknown'),
            username=msg.get('username', 'unknown'),
            preferences=[],
            message=msg.get('message', ''),
            response='',
        )
