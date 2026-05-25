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
