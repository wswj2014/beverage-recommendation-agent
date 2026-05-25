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
        # If input looks like JSON, try to extract name/keyword field
        if query.startswith("{"):
            try:
                import json as _json
                obj = _json.loads(query)
                query = obj.get("name") or obj.get("keyword") or query
            except Exception:
                pass
        # Split query into words and search each independently
        words = [w for w in query.strip().split() if len(w) > 0]
        if not words:
            words = [query.strip()]
        # Search each word as an OR condition across name/category/tags
        clauses = ["name LIKE ? OR category LIKE ? OR tags LIKE ?"] * len(words)
        params = []
        for w in words:
            params.extend([f"%{w}%", f"%{w}%", f"%{w}%"])
        rows = self.conn.execute(
            f"SELECT name, category, temperature, sweetness, price, tags, description "
            f"FROM beverages WHERE {' OR '.join(clauses)} LIMIT 10",
            params,
        ).fetchall()
        if not rows:
            return f"未找到与 '{query}' 相关的饮品。"
        seen = set()
        lines = []
        for r in rows:
            name, cat, temp, sweet, price, tags_str, desc = r
            if name in seen: continue
            seen.add(name)
            tags = json.loads(tags_str)
            lines.append(f"【{r[0]}】{cat} | {temp} | {sweet} | ¥{price} | {'，'.join(tags)} | {desc}")
        return "\n".join(lines)
