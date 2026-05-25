from src.llm import LLM


EXTRACT_PROFILE_PROMPT = """Extract user beverage preferences from this conversation into JSON.

Output format:
{{"history": ["drink_name_or_keyword", ...], "like": ["preferred_tag", ...], "unwanted": ["disliked_tag", ...]}}

Rules:
- history: beverage names or categories the user has ordered/discussed
- like: flavor tags, temperature, sweetness levels the user prefers (single words like "拿铁","冰","无糖")
- unwanted: things the user dislikes (single keywords like "太甜","奶茶","全糖")
- Use Chinese keywords matching the beverage domain (咖啡/奶茶/果茶/拿铁/美式/冰/热/无糖/微糖/半糖/全糖/低卡/提神 etc.)

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
