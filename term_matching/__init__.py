"""
术语匹配算法包

默认使用轻量字符串匹配器 StringTermMatcher（无模型、无 FAISS）。

历史的语义匹配组件（TermMatcher / FAISSManager 等，依赖 torch + faiss）
改为「惰性导入」：只有真正访问到它们时才加载对应重型依赖，
避免仅使用字符串匹配时也把 torch/faiss 拉进内存。
"""

import importlib

__version__ = "2.0.0"

# 名称 -> 所在子模块
_LAZY = {
    "StringTermMatcher": ".string_matcher",
    "TermMatcher": ".term_matcher",
    "TextPreprocessor": ".text_preprocessor",
    "FAISSManager": ".faiss_manager",
    "OverlapHandler": ".overlap_handler",
}

__all__ = list(_LAZY.keys())


def __getattr__(name):
    """PEP 562：按需从子模块加载，避免启动即导入 torch/faiss。"""
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target, __name__)
    return getattr(module, name)
