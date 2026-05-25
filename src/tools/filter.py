import sqlite3
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import DB_PATH
from src.buffer import CandidateBuffer


class FilterTool:
    name = "Filter"
    desc = (
        "按条件筛选饮品。可选条件: name(饮品名模糊), category(品类), temperature(温度), "
        "sweetness(甜度), price_min, price_max, tags(标签关键词)。输入为 JSON 对象。"
    )

    def __init__(self, buffer: CandidateBuffer):
        self.buffer = buffer
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        return self._conn

    def run(self, input_str: str) -> str:
        conditions = json.loads(input_str)
        where = []
        params = []

        if "name" in conditions:
            where.append("name LIKE ?")
            params.append(f"%{conditions['name']}%")
        if "category" in conditions:
            where.append("category LIKE ?")
            params.append(f"%{conditions['category']}%")
        if "temperature" in conditions:
            temp = conditions["temperature"]
            where.append("(temperature = ? OR temperature LIKE ?)")
            params.extend([temp, f"%{temp}%"])
        if "sweetness" in conditions:
            where.append("sweetness = ?")
            params.append(conditions["sweetness"])
        if "price_min" in conditions:
            where.append("price >= ?")
            params.append(conditions["price_min"])
        if "price_max" in conditions:
            where.append("price <= ?")
            params.append(conditions["price_max"])
        if "tags" in conditions:
            where.append("tags LIKE ?")
            params.append(f"%{conditions['tags']}%")

        current_ids = self.buffer.get()
        if not current_ids:
            return "Buffer 为空，无需筛选。"

        placeholders = ",".join("?" * len(current_ids))
        where.append(f"id IN ({placeholders})")
        params.extend(current_ids)

        sql = f"SELECT id FROM beverages WHERE {' AND '.join(where)}"
        rows = self.conn.execute(sql, params).fetchall()
        result = [r[0] for r in rows]
        self.buffer.update("Filter", result)
        return f"筛选后剩余 {len(result)} 杯饮品。"
