import sqlite3
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import DB_PATH
from src.buffer import CandidateBuffer


class FormatTool:
    name = "Format"
    desc = "将当前候选饮品格式化为可读推荐文本。输入为 JSON，例如: {\"top_k\": 5}"

    def __init__(self, buffer: CandidateBuffer):
        self.buffer = buffer
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(DB_PATH)
        return self._conn

    def run(self, input_str: str) -> str:
        params = json.loads(input_str)
        top_k = params.get("top_k", 5)
        ids = self.buffer.get()[:top_k]

        if not ids:
            return "暂无符合条件的饮品。"

        placeholders = ",".join("?" * len(ids))
        rows = self.conn.execute(
            f"SELECT id, name, category, temperature, sweetness, price, tags, description "
            f"FROM beverages WHERE id IN ({placeholders})",
            ids,
        ).fetchall()

        # 保持 buffer 中的顺序
        id_to_row = {}
        for r in rows:
            id_to_row[r[0]] = r

        ordered = []
        for i in ids:
            if i in id_to_row:
                ordered.append(id_to_row[i])

        lines = []
        for num, r in enumerate(ordered, 1):
            rid, name, cat, temp, sweet, price, tags_str, desc = r
            tags = json.loads(tags_str)
            lines.append(
                f"{num}. 【{name}】{cat} | {temp} | {sweet} | ¥{price} | {'，'.join(tags[:3])} | {desc}"
            )
        return "\n".join(lines)
