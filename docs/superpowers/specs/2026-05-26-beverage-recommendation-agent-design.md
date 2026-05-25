# 饮品推荐 Agent 设计规格

## 概述

基于微软 RecAI InteRecAgent 架构复刻的饮品推荐智能体。保留 Plan-First + Candidate Buffer 核心模式，砍掉饮品场景不需要的组件（Reflection、DemoSelector、SoftFilter），使用 DeepSeek 作为 LLM 后端。

## 架构

### Agent 主循环

```
用户输入 → 构建Prompt → LLM决策
                          ├→ Final Answer → 直接回复
                          └→ Action Plan → ToolBox执行 → LLM润色 → 回复
                                              ↕
                                       Candidate Buffer
```

### Plan-First 策略

LLM 一次性生成完整的工具执行计划（JSON 数组），ToolBox 批量执行全部工具，中间不再询问 LLM。相比 ReAct 模式减少 3-5 倍 API 调用。

### 组件

| 组件 | 文件 | 职责 |
|------|------|------|
| Agent | agent.py | 主循环：Prompt构建、LLM调用、ToolBox调度、Summarizer润色 |
| ToolBox | toolbox.py | 解析 LLM 生成的 JSON 计划，按序执行工具 |
| Buffer | buffer.py | 共享候选集状态，工具间传递饮品列表 |
| LLM | llm.py | DeepSeek API 封装（OpenAI 兼容协议） |
| Prompt | prompt.py | System prompt 模板构建 |
| Memory | memory.py | 对话记忆（cut策略）+ 用户画像记忆（LLM抽取） |

## 工具

### 饮品数据表 (SQLite)

beverages 表：id, name, category, temperature, sweetness, price, popularity, tags(JSON), description

### 四个工具

| 工具 | 输入 | 操作 | 输出 |
|------|------|------|------|
| LookUp | 饮品名/关键词 | SQL 模糊查询，不经过 Buffer | 饮品详情文本 |
| Filter | 品类/温度/甜度/价格/标签 | 对 Buffer 执行 SQL 过滤 | "筛选后剩余 N 杯" |
| Rank | 排序方式/limit | Buffer 排序截取 top K，融入用户画像 | Buffer 更新 |
| Format | top_k | Buffer ID→名称+描述映射 | 可读推荐文本 |

执行顺序：LookUp(可选) → Filter → Rank → Format(必须最后)

## 记忆系统

- **对话记忆**：保留最近 10 轮，超过则截断最早（cut 策略）
- **用户画像**：每 5 轮用 LLM 抽取 {history, like, unwanted}，传入 Rank 影响排序
- **生命周期**：用户画像更新后清空对话记忆，防止过长

## 项目结构

```
Product Recommendation Agent/
├── src/
│   ├── agent.py        # Plan-First Agent 主逻辑
│   ├── toolbox.py      # ToolBox 批量执行
│   ├── buffer.py       # Candidate Buffer
│   ├── memory.py       # 对话记忆 + 用户画像
│   ├── llm.py          # DeepSeek API 封装
│   ├── prompt.py       # System prompt 模板
│   └── tools/
│       ├── lookup.py   # 饮品查询
│       ├── filter.py   # SQL 过滤
│       ├── ranking.py  # 排序
│       └── format.py   # 格式化输出
├── data/
│   ├── init_db.py      # 建表 + 示例数据
│   └── beverages.db
├── main.py             # CLI 交互入口
├── requirements.txt    # openai
└── config.py           # API key, 模型配置
```

## 技术选型

- **语言**：Python 3.10+
- **LLM**：DeepSeek（OpenAI 兼容 API）
- **数据库**：SQLite（内置）
- **依赖**：openai SDK（唯一外部依赖）

## 初始数据

~20 款瑞幸风格饮品，覆盖品类（咖啡/奶茶/果茶/纯茶/冰沙）、温度（热/冰/常温）、甜度（无糖/微糖/半糖/全糖）。

## 部署

### API 层

FastAPI 包装 Agent，提供 REST 接口：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/chat` | POST | `{"user_id": "...", "message": "..."}` → `{"reply": "...", "items": [...]}` |
| `/chat/{user_id}/clear` | POST | 清空该用户对话记忆 |
| `/health` | GET | 健康检查 |

每次请求携带 `user_id`，服务端用内存字典区分不同用户的 Agent 实例和对话状态。

### 部署目标：Railway

- 支持 FastAPI + uvicorn 一键部署
- 自动挂载持久卷，SQLite 不丢数据
- 免费额度（$5/月）足够开发测试
- GitHub 仓库推送自动部署

### 项目结构（更新）

```
Product Recommendation Agent/
├── src/
│   ├── agent.py
│   ├── toolbox.py
│   ├── buffer.py
│   ├── memory.py
│   ├── llm.py
│   ├── prompt.py
│   └── tools/
│       ├── lookup.py
│       ├── filter.py
│       ├── ranking.py
│       └── format.py
├── data/
│   ├── init_db.py
│   └── beverages.db
├── app.py              # FastAPI 服务入口
├── main.py             # CLI 交互入口
├── requirements.txt    # openai, fastapi, uvicorn
├── config.py
├── Procfile            # Railway: web: uvicorn app:app --host 0.0.0.0 --port $PORT
└── runtime.txt         # python-3.10
```

## 非目标

- 不做 Reflection 自检（增加延迟，饮品场景收益低）
- 不做 DemoSelector（few-shot 对饮品无必要）
- 不做 SoftFilter 相似度工具（饮品间相似度意义不大）
- 不做 Gradio UI（CLI + API 即可）
- 不接 wj-coffee 真实数据（数据未就绪）
- 不做数据库持久化用户状态（内存字典即可，重启丢失可接受）
