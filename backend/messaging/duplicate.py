class DuplicateDetector:
    def __init__(self):
        self.seen = set()

    def is_duplicate(self, message_id: str) -> bool:
        return message_id in self.seen

    def mark_seen(self, message_id: str):
        self.seen.add(message_id)

    def check_and_mark(self, message_id: str) -> bool:
        if self.is_duplicate(message_id):
            return True

        self.mark_seen(message_id)
        return False

    def clear(self):
        self.seen.clear()

    def count(self):
        return len(self.seen)