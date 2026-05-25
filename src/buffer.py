from typing import List


class CandidateBuffer:
    def __init__(self):
        self._items: List[int] = []
        self._all_ids: List[int] = []
        self._tracks: List[dict] = []

    def init_all(self, all_ids: List[int]):
        """用全部饮品ID初始化buffer（Agent启动时调用一次）"""
        self._all_ids = all_ids
        self._items = all_ids.copy()

    def update(self, tool_name: str, candidates: List[int]):
        """工具执行后更新候选集"""
        self._items = list(candidates)
        self._tracks.append({"tool": tool_name, "count": len(candidates)})

    def get(self) -> List[int]:
        """获取当前候选ID列表"""
        return self._items

    def track_info(self) -> str:
        """获取工具执行轨迹文本"""
        lines = []
        for i, t in enumerate(self._tracks):
            lines.append(f"{i+1}. {t['tool']}: {t['count']} candidates")
        return "\n".join(lines)

    def clear(self):
        """重置buffer到初始全量状态（每轮对话开始时调用）"""
        self._items = self._all_ids.copy()
        self._tracks = []

    def __len__(self):
        return len(self._items)
