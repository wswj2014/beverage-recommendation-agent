import sqlite3
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import DB_PATH
from src.buffer import CandidateBuffer


class RankTool:
    name = "Rank"
    desc = (
        "对当前候选饮品排序并截取 top K。可选 order_by: popularity(热度)/price(价格)。"
        "输入为 JSON，例如: {\"order_by\": \"popularity\", \"limit\": 5}"
    )

    def __init__(self, buffer: CandidateBuffer):
        self.buffer = buffer
        self._conn = None
        self._user_profile = {}

    @property
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(DB_PATH)
        return self._conn

    def set_profile(self, profile: dict):
        self._user_profile = profile

    def run(self, input_str: str) -> str:
        params = json.loads(input_str)
        order_by = params.get("order_by", "popularity")
        limit = params.get("limit", 5)
        order_col = "popularity" if order_by == "popularity" else "price"

        current_ids = self.buffer.get()
        if not current_ids:
            return "Buffer 为空，无法排序。"

        placeholders = ",".join("?" * len(current_ids))
        rows = self.conn.execute(
            f"SELECT id, name, price, popularity, tags, description FROM beverages "
            f"WHERE id IN ({placeholders}) ORDER BY {order_col} DESC LIMIT ?",
            [*current_ids, limit],
        ).fetchall()

        # 融入用户画像：喜欢的标签加权，不喜欢的降权
        liked = set(self._user_profile.get("like", []))
        unwanted = set(self._user_profile.get("unwanted", []))

        scored = []
        for r in rows:
            rid, name, price, pop, tags_str, desc = r
            tags = json.loads(tags_str)
            score = pop
            for tag in tags:
                if tag in liked:
                    score += 20
            for tag in tags:
                if tag in unwanted:
                    score -= 30
            scored.append((rid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        result = [s[0] for s in scored[:limit]]
        self.buffer.update("Rank", result)
        return f"排序完成，保留 TOP {len(result)}。"
