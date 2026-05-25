# 饮品推荐 Agent 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 基于 RecAI InteRecAgent 架构，用 Python + DeepSeek 构建饮品推荐智能体，提供 CLI 和 FastAPI 两种入口。

**架构：** Plan-First Agent 主循环 → ToolBox 批量执行 4 个工具（LookUp/Filter/Rank/Format）→ Candidate Buffer 传递候选集 → LLM 润色输出。对话记忆 + 用户画像跨轮次积累偏好。

**技术栈：** Python 3.10+, DeepSeek API (OpenAI 兼容), SQLite, FastAPI + uvicorn, Railway 部署

---

## 文件结构

| 文件 | 职责 | 依赖 |
|------|------|------|
| `config.py` | API key、模型名、路径等全局配置 | 无 |
| `data/init_db.py` | 建表 + 写入 ~20 条瑞幸风格饮品示例数据 | config |
| `src/llm.py` | DeepSeek API 封装，call() 方法 | config |
| `src/buffer.py` | Candidate Buffer，工具间共享候选集 | 无 |
| `src/tools/lookup.py` | 饮品信息查询，SQL 模糊搜索 | llm, buffer (不依赖) |
| `src/tools/filter.py` | SQL 硬过滤，按品类/温度/甜度/价格/标签筛选 | buffer |
| `src/tools/ranking.py` | 排序截断 top K，融入用户画像偏好 | buffer |
| `src/tools/format.py` | Buffer ID → 名称+描述+价格文本 | buffer |
| `src/memory.py` | 对话记忆 (cut策略) + 用户画像 (LLM抽取) | llm |
| `src/prompt.py` | System prompt 模板，拼装工具描述和数据表信息 | 无 |
| `src/toolbox.py` | 解析 LLM 生成的 JSON 计划，批量执行工具 | buffer, tools |
| `src/agent.py` | Plan-First 主循环：Prompt构建/LLM规划/ToolBox执行/LLM润色 | 全部 |
| `main.py` | CLI 交互入口，read-while 循环 | agent |
| `app.py` | FastAPI 服务入口，多用户隔离 | agent |
| `requirements.txt` | 依赖清单：openai, fastapi, uvicorn | 无 |
| `Procfile` | Railway 启动命令 | app |

---

### 任务 1：项目骨架 + 配置

**文件：**
- 创建：`Product Recommendation Agent/config.py`
- 创建：`Product Recommendation Agent/requirements.txt`
- 创建：`Product Recommendation Agent/src/__init__.py`
- 创建：`Product Recommendation Agent/src/tools/__init__.py`
- 创建：`Product Recommendation Agent/data/__init__.py`

- [ ] **步骤 1：创建 requirements.txt**

```
openai>=1.0.0
fastapi>=0.100.0
uvicorn>=0.23.0
```

- [ ] **步骤 2：创建 config.py**

```python
import os

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "beverages.db")

MAX_DIALOGUE_TURNS = 10
USER_PROFILE_UPDATE_INTERVAL = 5
```

- [ ] **步骤 3：创建空白 `__init__.py` 文件**

```bash
echo "" > "src/__init__.py"
echo "" > "src/tools/__init__.py"
echo "" > "data/__init__.py"
```

- [ ] **步骤 4：验证目录结构**

运行：`ls -R "D:\develop\vscode project\projects\AI agent\Product Recommendation Agent"`
预期：看到 src/, src/tools/, data/, config.py, requirements.txt

- [ ] **步骤 5：Commit**

```bash
git add "projects/AI agent/Product Recommendation Agent/"
git commit -m "feat: project skeleton — config, requirements, directory structure"
```

---

### 任务 2：饮品数据库

**文件：**
- 创建：`Product Recommendation Agent/data/init_db.py`

- [ ] **步骤 1：编写 init_db.py——建表 + 示例数据**

```python
import sqlite3
import os

from config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS beverages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    temperature TEXT NOT NULL,
    sweetness   TEXT NOT NULL,
    price       REAL NOT NULL,
    popularity  INTEGER DEFAULT 50,
    tags        TEXT DEFAULT '[]',
    description TEXT DEFAULT ''
);
"""

SEED_DATA = [
    ("美式", "咖啡", "热/冰", "无糖", 15.0, 90, '["提神","经典","低卡"]', "经典美式咖啡，醇苦提神，适合纯咖啡爱好者"),
    ("拿铁", "咖啡", "热/冰", "半糖", 18.0, 95, '["经典","奶香","柔和"]', "浓缩咖啡与牛奶的经典融合，口感柔和顺滑"),
    ("生椰拿铁", "咖啡", "冰", "半糖", 20.0, 92, '["椰香","清爽","热门"]', "瑞幸同款，椰乳搭配浓缩咖啡，东南亚风情"),
    ("厚乳拿铁", "咖啡", "热/冰", "微糖", 22.0, 88, '["浓郁","奶香","冬天"]', "加倍厚牛乳，口感浓郁醇厚"),
    ("澳白", "咖啡", "热", "无糖", 18.0, 75, '["精致","浓郁","短萃"]', "短萃取浓缩配丝滑奶泡，咖啡味更浓郁"),
    ("摩卡", "咖啡", "热/冰", "全糖", 20.0, 80, '["巧克力","甜蜜","甜点"]', "浓缩咖啡+巧克力酱+牛奶，甜蜜与咖啡的碰撞"),
    ("卡布奇诺", "咖啡", "热", "半糖", 18.0, 70, '["经典","奶泡","绵密"]', "浓厚奶泡配浓缩咖啡，口感绵密"),
    ("冷萃咖啡", "咖啡", "冰", "无糖", 18.0, 85, '["顺滑","低酸","提神"]', "12小时冷泡萃取，顺滑不酸涩"),
    ("陨石厚乳拿铁", "咖啡", "冰", "半糖", 23.0, 90, '["黑糖","挂壁","热门","新品"]', "黑糖挂壁+厚牛乳+浓缩咖啡，视觉与味觉双享受"),
    ("冰摇浓缩", "咖啡", "冰", "无糖", 16.0, 65, '["清爽","纯粹","小众"]', "浓缩咖啡加冰摇匀，简单纯粹"),
    ("茉莉绿茶", "纯茶", "热/冰", "无糖", 12.0, 75, '["花香","清新","低卡"]', "茉莉花香萦绕，清新淡雅"),
    ("乌龙茶", "纯茶", "热/冰", "无糖", 12.0, 70, '["焙火","回甘","传统"]', "炭焙乌龙，回甘悠长"),
    ("柠檬茶", "果茶", "冰", "半糖", 14.0, 82, '["清爽","维C","夏天"]', "现切柠檬配红茶底，清爽解暑"),
    ("满杯百香果", "果茶", "冰", "半糖", 16.0, 88, '["百香果","酸甜","夏天","热门"]', "百香果原浆+绿茶底，酸甜解腻"),
    ("桃桃乌龙", "果茶", "冰", "微糖", 17.0, 80, '["桃子","乌龙","清爽"]', "蜜桃果肉配乌龙茶底，清爽甘甜"),
    ("葡萄冰沙", "冰沙", "冰", "半糖", 18.0, 78, '["葡萄","冰沙","夏天"]', "葡萄果肉搅打冰沙，清凉解暑"),
    ("芒芒冰沙", "冰沙", "冰", "半糖", 18.0, 76, '["芒果","冰沙","夏天"]', "新鲜芒果冰沙，甜蜜浓郁"),
    ("珍珠奶茶", "奶茶", "热/冰", "全糖", 15.0, 90, '["经典","珍珠","甜蜜"]', "经典台式珍珠奶茶，Q弹嚼劲"),
    ("黑糖波波牛乳", "奶茶", "冰", "全糖", 19.0, 85, '["黑糖","珍珠","浓郁","热门"]', "黑糖挂壁+Q弹波波+牛乳，视觉系奶茶"),
    ("芋泥波波奶茶", "奶茶", "热/冰", "半糖", 20.0, 83, '["芋泥","波波","暖冬"]', "芋泥绵密配Q弹波波，冬天必点"),
    ("抹茶拿铁", "咖啡", "热/冰", "半糖", 19.0, 78, '["抹茶","清新","颜值"]', "日式抹茶配绵密奶泡，绿色观赏级"),
    ("椰青美式", "咖啡", "冰", "无糖", 19.0, 73, '["椰子","清爽","小众","低卡"]', "青椰水配浓缩咖啡，低卡清爽新选择"),
]


def init_db(db_path: str = None):
    if db_path is None:
        db_path = DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    conn.execute("DELETE FROM beverages")
    conn.executemany(
        "INSERT INTO beverages (name, category, temperature, sweetness, price, popularity, tags, description) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        SEED_DATA,
    )
    conn.commit()
    conn.close()
    print(f"Database initialized at {db_path} with {len(SEED_DATA)} beverages.")


if __name__ == "__main__":
    init_db()
```

- [ ] **步骤 2：运行初始化**

运行：`python "D:\develop\vscode project\projects\AI agent\Product Recommendation Agent\data\init_db.py"`
预期：`Database initialized at ... with 22 beverages.`

- [ ] **步骤 3：验证数据**

运行：`sqlite3 "D:\develop\vscode project\projects\AI agent\Product Recommendation Agent\data\beverages.db" "SELECT COUNT(*) FROM beverages;"`
预期：`22`

- [ ] **步骤 4：Commit**

```bash
git add "projects/AI agent/Product Recommendation Agent/data/"
git commit -m "feat: beverage database with 22 seed drinks"
```

---

### 任务 3：LLM 封装

**文件：**
- 创建：`Product Recommendation Agent/src/llm.py`

- [ ] **步骤 1：编写 LLM 封装**

```python
from openai import OpenAI

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


class LLM:
    def __init__(self):
        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
        self.model = DEEPSEEK_MODEL

    def call(
        self,
        user_prompt: str,
        sys_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.0,
        max_tokens: int = 1024,
        stop: list = None,
    ) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
        )
        return resp.choices[0].message.content
```

- [ ] **步骤 2：Commit**

```bash
git add "projects/AI agent/Product Recommendation Agent/src/llm.py"
git commit -m "feat: DeepSeek LLM wrapper using OpenAI-compatible API"
```

---

### 任务 4：Candidate Buffer

**文件：**
- 创建：`Product Recommendation Agent/src/buffer.py`

- [ ] **步骤 1：编写 Buffer**

```python
from typing import List


class CandidateBuffer:
    def __init__(self):
        self._items: List[int] = []
        self._all_ids: List[int] = []
        self._tracks: List[dict] = []

    def init_all(self, all_ids: List[int]):
        self._all_ids = all_ids
        self._items = all_ids.copy()

    def update(self, tool_name: str, candidates: List[int]):
        self._items = list(candidates)
        self._tracks.append({"tool": tool_name, "count": len(candidates)})

    def get(self) -> List[int]:
        return self._items

    def track_info(self) -> str:
        lines = []
        for i, t in enumerate(self._tracks):
            lines.append(f"{i+1}. {t['tool']}: {t['count']} candidates")
        return "\n".join(lines)

    def clear(self):
        self._items = self._all_ids.copy()
        self._tracks = []

    def __len__(self):
        return len(self._items)
```

- [ ] **步骤 2：Commit**

```bash
git add "projects/AI agent/Product Recommendation Agent/src/buffer.py"
git commit -m "feat: candidate buffer for tool-to-tool state transfer"
```

---

### 任务 5：工具实现

**文件：**
- 创建：`Product Recommendation Agent/src/tools/lookup.py`
- 创建：`Product Recommendation Agent/src/tools/filter.py`
- 创建：`Product Recommendation Agent/src/tools/ranking.py`
- 创建：`Product Recommendation Agent/src/tools/format.py`

- [ ] **步骤 1：编写 LookUp 工具**

```python
import sqlite3
import json
from config import DB_PATH


class LookUpTool:
    name = "LookUp"
    desc = "查询饮品信息。支持模糊搜索名称、品类、标签。每行一个条件，例如: 拿铁"

    def __init__(self):
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(DB_PATH)
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
```

- [ ] **步骤 2：编写 Filter 工具**

```python
import sqlite3
import json
from config import DB_PATH
from src.buffer import CandidateBuffer


class FilterTool:
    name = "Filter"
    desc = (
        "按条件筛选饮品。可选条件: category(品类), temperature(温度), sweetness(甜度), "
        "price_min, price_max, tags(标签关键词)。输入为 JSON 对象，例如: "
        '{"category": "咖啡", "temperature": "冰", "sweetness": "无糖"}'
    )

    def __init__(self, buffer: CandidateBuffer):
        self.buffer = buffer
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(DB_PATH)
        return self._conn

    def run(self, input_str: str) -> str:
        conditions = json.loads(input_str)
        where = []
        params = []

        if "category" in conditions:
            where.append("category = ?")
            params.append(conditions["category"])
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
```

- [ ] **步骤 3：编写 Rank 工具**

```python
import sqlite3
import json
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

        # 融入用户画像：喜欢的加权，不喜欢的降权
        liked = set(self._user_profile.get("like", []))
        unwanted = set(self._user_profile.get("unwanted", []))
        
        scored = []
        for r in rows:
            rid, name, price, pop, tags_str, desc = r
            tags = json.loads(tags_str)
            score = pop
            # 标签匹配喜欢项加分
            for tag in tags:
                if tag in liked:
                    score += 20
            # 标签匹配不喜欢项减分
            for tag in tags:
                if tag in unwanted:
                    score -= 30
            scored.append((rid, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        result = [s[0] for s in scored[:limit]]
        self.buffer.update("Rank", result)
        return f"排序完成，保留 TOP {len(result)}。"
```

- [ ] **步骤 4：编写 Format 工具**

```python
import sqlite3
import json
from src.buffer import CandidateBuffer
from config import DB_PATH


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
            f"SELECT name, category, temperature, sweetness, price, tags, description "
            f"FROM beverages WHERE id IN ({placeholders})",
            ids,
        ).fetchall()

        # 保持 buffer 中的顺序
        id_to_row = {r[0]: r for r in rows}
        ordered = [id_to_row[i] for i in ids if i in id_to_row]

        lines = []
        for i, r in enumerate(ordered, 1):
            name, cat, temp, sweet, price, tags_str, desc = r
            tags = json.loads(tags_str)
            lines.append(
                f"{i}. 【{name}】{cat} | {temp} | {sweet} | ¥{price} | {'，'.join(tags[:3])} | {desc}"
            )
        return "\n".join(lines)
```

- [ ] **步骤 5：Commit**

```bash
git add "projects/AI agent/Product Recommendation Agent/src/tools/"
git commit -m "feat: implement 4 tools — LookUp, Filter, Rank, Format"
```

---

### 任务 6：记忆系统

**文件：**
- 创建：`Product Recommendation Agent/src/memory.py`

- [ ] **步骤 1：编写记忆系统**

```python
from src.llm import LLM


EXTRACT_PROFILE_PROMPT = """Extract user beverage preferences from this conversation into JSON.

Output format:
{"history": ["drink_name_or_keyword", ...], "like": ["preferred_tag", ...], "unwanted": ["disliked_tag", ...]}

Rules:
- history: beverage names or categories the user has ordered/discussed
- like: flavor tags, temperature, sweetness levels the user prefers (single words like "拿铁","第","无糖")
- unwanted: things the user dislikes (single keywords like "太甜","奶茶","全糖")
- Use Chinese keywords matching the beverage domain (咖啡/奶茶/果茶/拿铁/美式/第/热/无糖/微糖/半糖/全糖/低卡/提神 etc.)

Conversation:
{conversation}

JSON:"""


class DialogueMemory:
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self._memory: list = []

    def append(self, role: str, message: str):
        self._memory.append({"role": role, "content": message})
        self._enforce_limit()

    def get(self) -> str:
        lines = [f"{m['role']}: {m['content']}" for m in self._memory]
        return "\n".join(lines)

    def _enforce_limit(self):
        max_messages = self.max_turns * 2
        if len(self._memory) > max_messages:
            self._memory = self._memory[-max_messages:]

    def clear(self):
        self._memory = []


class UserProfileMemory:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.profile = {"history": [], "like": [], "unwanted": []}

    def update(self, conversation: str):
        prompt = EXTRACT_PROFILE_PROMPT.format(conversation=conversation)
        try:
            import json
            resp = self.llm.call(user_prompt=prompt, temperature=0.0)
            extracted = json.loads(resp)
        except Exception:
            return

        like_set = set(self.profile["like"])
        unwanted_set = set(self.profile["unwanted"])
        history_set = set(self.profile["history"])

        like_set.update(extracted.get("like", []))
        like_set -= set(extracted.get("unwanted", []))
        unwanted_set.update(extracted.get("unwanted", []))
        unwanted_set -= set(extracted.get("like", []))
        history_set.update(extracted.get("history", []))

        self.profile["like"] = list(like_set)
        self.profile["unwanted"] = list(unwanted_set)
        self.profile["history"] = list(history_set)

    def get(self) -> dict:
        return self.profile

    def clear(self):
        self.profile = {"history": [], "like": [], "unwanted": []}
```

- [ ] **步骤 2：Commit**

```bash
git add "projects/AI agent/Product Recommendation Agent/src/memory.py"
git commit -m "feat: dialogue memory + user profile memory with LLM extraction"
```

---

### 任务 7：System Prompt

**文件：**
- 创建：`Product Recommendation Agent/src/prompt.py`

- [ ] **步骤 1：编写 System Prompt 模板**

```python
SYSTEM_PROMPT = """
You are a beverage recommendation assistant for a Luckin Coffee style drink shop. Help users find drinks they'll enjoy.

Human requests fall into: chit-chat, drink info lookup, or drink recommendations.
- Chit-chat: respond with your knowledge about beverages.
- Drink info: use {LookUpTool} to query specific drinks.
- Recommendations: use tools to filter and rank drinks.

User intentions have hard conditions (category, temperature, sweetness, price) and soft conditions (preference, mood).
Separate hard and soft conditions when planning tool usage.

You have these tools:

{tools_desc}

All tools operate on a SQLite beverage table:
{{table_info}}

For recommendations, use tools with a shared candidate buffer:
1. Buffer starts with ALL drinks
2. Use {FilterTool} to filter by hard conditions (category, temperature, sweetness, price, tags)
3. Use {RankTool} to sort and limit results
4. Use {FormatTool} to get readable drink details for the final response
5. {LookUpTool} is for querying specific drink info, NOT for recommendations

MUST use {RankTool} and {FormatTool} before giving recommendations.
{FilterTool} is optional but should be used when user specifies conditions.

## Response Format

If NO tools needed, output:
###
Question: Do I need to use tools?
Thought: No, I know the answer.
Final Answer: [your response]
###

If tools ARE needed, make a plan and use ToolExecutor:
###
Question: Do I need to use tools?
Thought: Yes, I need to make a plan first.
Action: ToolExecutor
Action Input: [{{"tool_name": "{FilterTool}", "input": {{...}}}}, {{"tool_name": "{RankTool}", "input": {{...}}}}, {{"tool_name": "{FormatTool}", "input": {{...}}}}]
###

Tool names: {tool_names}

## Previous Conversation
{{history}}

## Rules
- Extract user preferences from conversation history
- Ask questions if the user's request is too vague
- NEVER mention tool names or technical details to the user
- Reply in Chinese
- Either "Final Answer" or "Action" must appear in your response

{{reflection}}
{{examples}}

Human: {{input}}
""".strip()


def build_system_prompt(tools_desc: str, tool_names: str, domain: str = "饮品") -> str:
    tool_name_map = {
        "LookUpTool": "LookUp",
        "FilterTool": "Filter",
        "RankTool": "Rank",
        "FormatTool": "Format",
    }
    return SYSTEM_PROMPT.format(
        tools_desc=tools_desc,
        tool_names=tool_names,
        domain=domain,
        **tool_name_map,
    )
```

- [ ] **步骤 2：Commit**

```bash
git add "projects/AI agent/Product Recommendation Agent/src/prompt.py"
git commit -m "feat: plan-first system prompt template"
```

---

### 任务 8：ToolBox 执行引擎

**文件：**
- 创建：`Product Recommendation Agent/src/toolbox.py`

- [ ] **步骤 1：编写 ToolBox**

```python
import json
from ast import literal_eval
from typing import Dict

from src.buffer import CandidateBuffer


class ToolBox:
    def __init__(self, tools: Dict, buffer: CandidateBuffer):
        self.tools = tools
        self.buffer = buffer
        self.name = "ToolExecutor"
        self.desc = (
            "Execute a plan of tool calls. Input is a JSON array of tool calls: "
            '[{"tool_name": "ToolName", "input": {...}}, ...]. '
            "Only LookUp and Format return visible output."
        )

    def run(self, plan_json: str) -> str:
        try:
            plans = json.loads(plan_json)
        except Exception:
            try:
                plans = literal_eval(plan_json)
            except Exception:
                return "工具计划解析失败。请使用正确的 JSON 格式。"

        if isinstance(plans, dict):
            plans = [plans]

        plans = {p["tool_name"]: p["input"] for p in plans}

        # 检查工具名是否存在
        for name in plans:
            if name not in self.tools:
                return f"工具 '{name}' 不存在。可用工具: {list(self.tools.keys())}"

        # 确保 Format 在最后
        if "Format" in plans:
            format_input = plans.pop("Format")
            plans["Format"] = format_input

        results = []
        for tool_name, tool_input in plans.items():
            try:
                if isinstance(tool_input, dict):
                    tool_input = json.dumps(tool_input, ensure_ascii=False)
                output = self.tools[tool_name].run(tool_input)
                if tool_name in ("LookUp", "Format"):
                    results.append(output)
            except Exception as e:
                return f"执行工具 '{tool_name}' 时出错: {e}"

        return "\n".join(results) if results else "工具执行完成。"
```

- [ ] **步骤 2：Commit**

```bash
git add "projects/AI agent/Product Recommendation Agent/src/toolbox.py"
git commit -m "feat: ToolBox plan executor with JSON parsing"
```

---

### 任务 9：Agent 主循环

**文件：**
- 创建：`Product Recommendation Agent/src/agent.py`

- [ ] **步骤 1：编写 Agent**

```python
import re
import sqlite3
from typing import Tuple

from config import DB_PATH, MAX_DIALOGUE_TURNS, USER_PROFILE_UPDATE_INTERVAL
from src.llm import LLM
from src.buffer import CandidateBuffer
from src.memory import DialogueMemory, UserProfileMemory
from src.prompt import build_system_prompt
from src.toolbox import ToolBox
from src.tools.lookup import LookUpTool
from src.tools.filter import FilterTool
from src.tools.ranking import RankTool
from src.tools.format import FormatTool


SUMMARIZE_PROMPT = """You are a friendly beverage recommendation assistant for a Luckin Coffee style shop.
Generate a warm, natural response in Chinese based on the tool execution results.
If no results match, politely suggest alternatives or ask the user to adjust their criteria.

Chat History:
{history}

User Request: {user_input}

Tool Execution Track:
{track_info}

Tool Results:
{tool_result}

Do NOT mention tool names. Keep it natural, like a barista talking to a customer."""


class BeverageRecommendAgent:
    def __init__(self):
        self.llm = LLM()
        self.buffer = CandidateBuffer()
        self.dialogue = DialogueMemory(max_turns=MAX_DIALOGUE_TURNS)
        self.profile = UserProfileMemory(self.llm)
        self._turn_count = 0

        # 初始化 buffer 的完整 ID 列表
        self._init_buffer()

        # 初始化工具
        self.lookup_tool = LookUpTool()
        self.filter_tool = FilterTool(self.buffer)
        self.rank_tool = RankTool(self.buffer)
        self.format_tool = FormatTool(self.buffer)

        self.tools = {
            "LookUp": self.lookup_tool,
            "Filter": self.filter_tool,
            "Rank": self.rank_tool,
            "Format": self.format_tool,
        }

        self.toolbox = ToolBox(self.tools, self.buffer)

        # 构建 system prompt
        tools_desc = "\n".join([f"{t.name}: {t.desc}" for t in self.tools.values()])
        tool_names = "[" + ", ".join(self.tools.keys()) + "]"
        self.sys_prompt_template = build_system_prompt(tools_desc, tool_names)

    def _init_buffer(self):
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT id FROM beverages").fetchall()
        all_ids = [r[0] for r in rows]
        conn.close()
        self.buffer.init_all(all_ids)

    def _get_table_info(self) -> str:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("PRAGMA table_info(beverages)")
        cols = [f"{r[1]} ({r[2]})" for r in cursor.fetchall()]
        conn.close()
        return "beverages(" + ", ".join(cols) + ")"

    def _parse_llm_output(self, output: str) -> Tuple[bool, str]:
        """Returns (is_final_answer, content)"""
        output = output.strip()
        if "Final Answer:" in output:
            return True, output.split("Final Answer:")[-1].strip()

        # try Action/Action Input pattern
        match = re.search(
            r"Action\s*\d*\s*:\s*(.*?)\nAction\s*\d*\s*Input\s*\d*\s*:\s*[\s]*(.*)",
            output, re.DOTALL,
        )
        if match:
            return False, match.group(2).strip()

        # fallback: treat entire output as final answer
        return True, output

    def run(self, user_input: str) -> str:
        self.buffer.clear()
        self._turn_count += 1

        # 每 N 轮更新用户画像
        if self._turn_count > 0 and self._turn_count % USER_PROFILE_UPDATE_INTERVAL == 0:
            self.profile.update(self.dialogue.get())
            self.dialogue.clear()
            self.rank_tool.set_profile(self.profile.get())

        # 构建 prompt
        table_info = self._get_table_info()
        history = self.dialogue.get()
        prompt = self.sys_prompt_template.format(
            table_info=table_info,
            history=history if history else "(new conversation)",
            input=user_input,
            reflection="",
            examples="",
            tool_names="[" + ", ".join(self.tools.keys()) + "]",
        )

        # LLM 第 1 次调用：决策
        llm_output = self.llm.call(user_prompt=prompt)
        is_final, content = self._parse_llm_output(llm_output)

        if is_final:
            self.dialogue.append("User", user_input)
            self.dialogue.append("Agent", content)
            return content

        # LLM 规划了工具，执行
        tool_result = self.toolbox.run(content)

        if tool_result.startswith("工具") or tool_result.startswith("执行"):
            # Tool execution error message
            self.dialogue.append("User", user_input)
            self.dialogue.append("Agent", tool_result)
            return tool_result

        # LLM 第 2 次调用：润色
        summary_prompt = SUMMARIZE_PROMPT.format(
            history=history if history else "(new conversation)",
            user_input=user_input,
            track_info=self.buffer.track_info(),
            tool_result=tool_result,
        )
        final_response = self.llm.call(
            user_prompt=summary_prompt,
            sys_prompt="You are a friendly barista at a Luckin Coffee style shop. Reply in Chinese.",
            temperature=1.0,
        )

        self.dialogue.append("User", user_input)
        self.dialogue.append("Agent", final_response)
        return final_response

    def clear(self):
        self.dialogue.clear()
        self.profile.clear()
        self._turn_count = 0
        self.rank_tool.set_profile({})
```

- [ ] **步骤 2：Commit**

```bash
git add "projects/AI agent/Product Recommendation Agent/src/agent.py"
git commit -m "feat: plan-first agent main loop — plan, execute, summarize"
```

---

### 任务 10：CLI 入口

**文件：**
- 创建：`Product Recommendation Agent/main.py`

- [ ] **步骤 1：编写 CLI**

```python
from src.agent import BeverageRecommendAgent


def main():
    print("=" * 50)
    print("LUCKIN COFFEE 饮品推荐助手")
    print("输入 'clear' 清空记忆，输入 'quit' 退出")
    print("=" * 50)

    agent = BeverageRecommendAgent()

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("再见！")
            break
        if user_input.lower() == "clear":
            agent.clear()
            print("记忆已清空。")
            continue

        response = agent.run(user_input)
        print(f"\n助手: {response}")


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：Commit**

```bash
git add "projects/AI agent/Product Recommendation Agent/main.py"
git commit -m "feat: CLI entry point for interactive beverage recommendations"
```

---

### 任务 11：FastAPI 服务

**文件：**
- 创建：`Product Recommendation Agent/app.py`

- [ ] **步骤 1：编写 API 服务**

```python
from fastapi import FastAPI
from pydantic import BaseModel
from src.agent import BeverageRecommendAgent


app = FastAPI(title="Beverage Recommendation Agent")
agents: dict = {}


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    agent = agents.get(req.user_id)
    if agent is None:
        agent = BeverageRecommendAgent()
        agents[req.user_id] = agent
    reply = agent.run(req.message)
    return ChatResponse(reply=reply)


@app.post("/chat/{user_id}/clear")
def clear_chat(user_id: str):
    agent = agents.get(user_id)
    if agent:
        agent.clear()
    return {"status": "cleared"}
```

- [ ] **步骤 2：Commit**

```bash
git add "projects/AI agent/Product Recommendation Agent/app.py"
git commit -m "feat: FastAPI server with multi-user agent isolation"
```

---

### 任务 12：部署配置

**文件：**
- 创建：`Product Recommendation Agent/Procfile`
- 创建：`Product Recommendation Agent/runtime.txt`

- [ ] **步骤 1：创建部署文件**

```bash
echo "web: uvicorn app:app --host 0.0.0.0 --port $PORT" > "Procfile"
echo "python-3.10" > "runtime.txt"
```

- [ ] **步骤 2：验证所有文件到位**

运行：`ls -R "D:\develop\vscode project\projects\AI agent\Product Recommendation Agent"`
预期：config.py, main.py, app.py, Procfile, runtime.txt, requirements.txt, data/, src/ (含所有模块)

- [ ] **步骤 3：Commit**

```bash
git add "projects/AI agent/Product Recommendation Agent/Procfile" "projects/AI agent/Product Recommendation Agent/runtime.txt"
git commit -m "feat: Railway deployment config (Procfile + runtime.txt)"
```

---

### 任务 13：端到端验证

- [ ] **步骤 1：安装依赖**

运行：`pip install openai fastapi uvicorn`
预期：成功安装

- [ ] **步骤 2：初始化数据库**

运行：`python "D:\develop\vscode project\projects\AI agent\Product Recommendation Agent\data\init_db.py"`
预期：`Database initialized at ... with 22 beverages.`

- [ ] **步骤 3：CLI 冒烟测试**

运行：`python "D:\develop\vscode project\projects\AI agent\Product Recommendation Agent\main.py"`
交互输入："推荐一杯冰的咖啡"
预期：返回包含冰咖啡推荐的回复

- [ ] **步骤 4：API 冒烟测试**

先启动服务（后台）：
`cd "D:\develop\vscode project\projects\AI agent\Product Recommendation Agent" && python app.py &`

测试 `/health`：
`curl http://localhost:8000/health`
预期：`{"status":"ok"}`

测试 `/chat`：
`curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"user_id":"test","message":"推荐一杯提神的"}'`
预期：返回饮品推荐 JSON

- [ ] **步骤 5：Commit（如有修改）**

```bash
git status
git add ... # 如有修复
git commit -m "fix: end-to-end testing fixes"
```
