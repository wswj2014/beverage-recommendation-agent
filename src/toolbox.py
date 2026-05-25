import json
import re
from ast import literal_eval
from typing import Dict

from src.buffer import CandidateBuffer


class ToolBox:
    def __init__(self, tools: Dict, buffer: CandidateBuffer):
        self.tools = tools
        self.buffer = buffer
        self.name = "ToolExecutor"
        self.desc = (
            "Execute a plan of tool calls. Input is a JSON array: "
            '[{"tool_name": "Filter", "input": {"category": "咖啡"}}, {"tool_name": "Format", "input": {"top_k": 5}}]. '
            "Only LookUp and Format return visible output."
        )

    def _try_parse(self, text: str):
        # Try direct JSON parse
        try:
            return True, json.loads(text)
        except Exception:
            pass

        # Try to extract JSON array from text
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            try:
                return True, json.loads(match.group())
            except Exception:
                pass

        # Try Python literal eval
        try:
            return True, literal_eval(text)
        except Exception:
            pass

        return False, f"无法解析工具计划: {text[:200]}"

    def run(self, plan_json: str) -> str:
        ok, plans = self._try_parse(plan_json)
        if not ok:
            return str(plans)

        if isinstance(plans, dict):
            plans = [plans]

        plans = {p["tool_name"]: p["input"] for p in plans}

        for name in plans:
            if name not in self.tools:
                return f"工具 '{name}' 不存在。可用工具: {list(self.tools.keys())}"

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
