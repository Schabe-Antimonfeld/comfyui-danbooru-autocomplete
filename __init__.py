import os
import server   # type: ignore
from aiohttp import web

_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
_TAGS_FILE  = os.path.join(_PLUGIN_DIR, "data", "danbooru_tags.txt")


def _to_display(name):
    """将 danbooru raw tag 转换为 ComfyUI prompt 格式：
    - 下划线 → 空格
    - 括号转义，避免被 ComfyUI 解析为权重语法 (tag:1.2)
    """
    name = name.replace("_", " ")
    name = name.replace("(", r"\(").replace(")", r"\)")
    return name


_cache = None


def _load_tags():
    global _cache
    if _cache is not None:
        return _cache

    if not os.path.exists(_TAGS_FILE):
        _cache = []
        return _cache

    tags = []
    with open(_TAGS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            raw = parts[0]
            try:
                count = int(parts[1]) if len(parts) > 1 else 0
            except ValueError:
                count = 0
            try:
                category = int(parts[2]) if len(parts) > 2 else 0
            except ValueError:
                category = 0
            display = _to_display(raw)
            tags.append((raw, display, count, category))

    tags.sort(key=lambda x: -x[2])
    _cache = tags
    print(f"[DanbooruAutocomplete] 已加载 {len(_cache):,} 个 tag")
    return _cache


@server.PromptServer.instance.routes.get("/danbooru-autocomplete/tags")
async def get_tags(request):
    query = request.rel_url.query.get("q", "").strip().lower()
    try:
        limit = max(1, min(50, int(request.rel_url.query.get("limit", 20))))
    except ValueError:
        limit = 20

    if len(query) < 2:
        return web.json_response([])

    tags = _load_tags()
    if not tags:
        return web.Response(
            status=404,
            content_type="application/json",
            text='{"error":"Tags file not found."}'
        )

    query_with_us = query.replace(" ", "_")
    query_with_sp = query.replace("_", " ")

    prefix_hits = []
    contain_hits = []

    for raw, display, count, category in tags:
        raw_l = raw.lower()
        disp_l = display.lower()

        is_prefix = (raw_l.startswith(query_with_us) or
                     raw_l.startswith(query) or
                     disp_l.startswith(query_with_sp) or
                     disp_l.startswith(query))

        is_contain = (query_with_us in raw_l or
                      query in raw_l or
                      query_with_sp in disp_l or
                      query in disp_l)

        if is_prefix:
            prefix_hits.append({"tag": display, "raw": raw, "count": count, "category": category})
        elif is_contain:
            contain_hits.append({"tag": display, "raw": raw, "count": count, "category": category})

        if len(prefix_hits) >= limit and len(contain_hits) >= limit:
            break

    merged = (prefix_hits + contain_hits)[:limit]
    return web.json_response(merged)


@server.PromptServer.instance.routes.get("/danbooru-autocomplete/status")
async def get_status(request):
    """调试接口：访问 http://127.0.0.1:8000/danbooru-autocomplete/status"""
    tags = _load_tags()
    return web.json_response({
        "ok": len(tags) > 0,
        "tag_count": len(tags),
        "file": _TAGS_FILE,
        "file_exists": os.path.exists(_TAGS_FILE),
        "sample": [{"raw": t[0], "display": t[1]} for t in tags[:5]],
    })


WEB_DIRECTORY = "web"
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
