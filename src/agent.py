import re
import sqlite3
import sys
import os
from typing import Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


SUMMARIZE_PROMPT = """You are a polite and cute beverage recommendation assistant — warm, gentle, like a smiling barista.
Generate a light, encouraging Chinese response based STRICTLY on the tool execution results below.
ONLY recommend drinks that appear in the Tool Results — never invent or guess drinks.
Use "您" to address the user. Use emojis sparingly (1-3 at most, keep them light ☺️✨🍃).
Be warm and supportive, but not overly excited. Keep replies brief — 2-3 sentences max, recommend no more than 3 drinks.

Chat History:
{history}

User Request: {user_input}

Tool Execution Track:
{track_info}

Tool Results:
{tool_result}

Do NOT mention tool names. ONLY use drinks from the Tool Results. Sound like a cute, polite barista!"""


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

        # 构建 system prompt 模板（工具名和描述不变，一次性填充）
        self._tools_desc = "\n".join([f"{t.name}: {t.desc}" for t in self.tools.values()])
        self._tool_names_str = "[" + ", ".join(self.tools.keys()) + "]"
        self._tool_name_map = {
            "LookUpTool": "LookUp",
            "FilterTool": "Filter",
            "RankTool": "Rank",
            "FormatTool": "Format",
        }
        self.sys_prompt_template = build_system_prompt("", "")

    def _init_buffer(self):
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        rows = conn.execute("SELECT id FROM beverages").fetchall()
        all_ids = [r[0] for r in rows]
        conn.close()
        self.buffer.init_all(all_ids)

    def _get_table_info(self) -> str:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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

        # If output contains planning keywords but regex didn't match,
        # it's a malformed plan — treat as error, not final answer
        if "Question:" in output and ("Action:" in output or "Action Input:" in output):
            return True, "抱歉，我有点迷糊了，能再说一遍吗？☺️"

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
            tools_desc=self._tools_desc,
            tool_names=self._tool_names_str,
            **self._tool_name_map,
        )

        # LLM 第 1 次调用：决策（规划工具 or 直接回复）
        llm_output = self.llm.call(user_prompt=prompt, max_tokens=512)
        is_final, content = self._parse_llm_output(llm_output)

        if is_final:
            final_answer = content
        else:
            # LLM 规划了工具，执行
            tool_result = self.toolbox.run(content)
            if tool_result.startswith("工具") or tool_result.startswith("执行"):
                final_answer = tool_result
            else:
                # LLM 第 2 次调用：润色工具结果
                summary_prompt = SUMMARIZE_PROMPT.format(
                    history=history if history else "(new conversation)",
                    user_input=user_input,
                    track_info=self.buffer.track_info(),
                    tool_result=tool_result,
                )
                final_answer = self.llm.call(
                    user_prompt=summary_prompt,
                    sys_prompt="You are a polite and cute barista. Use warm, gentle Chinese. Address user as '您'. Light emojis only. Keep response under 150 chars.",
                    temperature=0.5,
                    max_tokens=512,
                )

        if not final_answer or not final_answer.strip():
            final_answer = "抱歉呀，刚刚走神了～能再说一遍吗？☺️"

        self.dialogue.append("User", user_input)
        self.dialogue.append("Agent", final_answer)
        return final_answer

    def clear(self):
        self.dialogue.clear()
        self.profile.clear()
        self._turn_count = 0
        self.rank_tool.set_profile({})
