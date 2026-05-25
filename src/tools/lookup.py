import sqlite3
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import DB_PATH


class LookUpTool:
    name = "LookUp"
    desc = "查询饮品信息。支持模糊搜索名称、品类、标签。"

    def __init__(self):
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        return self._conn

    def run(self, query: str) -> str:
        keyword = query.strip()
        rows = self.conn.execute(
            "SELECT name, category, temperature, sweetness, price, tags, description "
            "FROM beverages WHERE name LIKE ? OR category LIKE ? OR tags LIKE ? LIMIT 10",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
        if not rows:
            return f"未找到与 '{keyword}' 相关的饮品。"
        lines = []
        for r in rows:
            name, cat, temp, sweet, price, tags_str, desc = r
            tags = json.loads(tags_str)
            lines.append(f"【{name}】{cat} | {temp} | {sweet} | ¥{price} | {'，'.join(tags)} | {desc}")
        return "\n".join(lines)
