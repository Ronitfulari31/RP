import base64
import json
from datetime import datetime
from bson import ObjectId


class CursorPagination:
    """
    Reusable cursor-based pagination helper.

    Supports compound cursors like:
    - created_at DESC
    - _id DESC (tie-breaker)

    Can be reused across any MongoDB collection.
    """

    def __init__(self, sort_fields=None, max_limit=50):
        """
        sort_fields example:
        [
            ("created_at", -1),
            ("_id", -1)
        ]
        """
        self.sort_fields = sort_fields or [
            ("created_at", -1),
            ("_id", -1)
        ]
        self.max_limit = max_limit

    # --------------------------------------------------
    # Cursor encode / decode
    # --------------------------------------------------

    def encode_cursor(self, document: dict) -> str:
        payload = {}

        for field, _ in self.sort_fields:
            value = document.get(field)

            if isinstance(value, ObjectId):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()

            payload[field] = value

        raw = json.dumps(payload).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8")

    def decode_cursor(self, cursor: str) -> dict:
        raw = base64.urlsafe_b64decode(cursor.encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))

        decoded = {}
        for field, _ in self.sort_fields:
            value = data.get(field)

            if field == "_id":
                value = ObjectId(value)
            elif isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value)
                except Exception:
                    pass

            decoded[field] = value

        return decoded

    # --------------------------------------------------
    # MongoDB cursor filter
    # --------------------------------------------------

    def build_cursor_filter(self, cursor: str):
        """
        Builds MongoDB filter to fetch documents AFTER the cursor.
        """
        if not cursor:
            return None

        decoded = self.decode_cursor(cursor)

        conditions = []
        for i, (field, order) in enumerate(self.sort_fields):
            clause = {}

            # Fields before must be equal
            for prev_field, _ in self.sort_fields[:i]:
                clause[prev_field] = decoded[prev_field]

            # This field must be less/greater
            operator = "$lt" if order == -1 else "$gt"
            clause[field] = {operator: decoded[field]}

            conditions.append(clause)

        return {"$or": conditions}

    # --------------------------------------------------
    # Utility
    # --------------------------------------------------

    def clamp_limit(self, requested: int | None):
        if not requested:
            return self.max_limit
        return min(int(requested), self.max_limit)
