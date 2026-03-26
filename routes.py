import os

import server  # type: ignore
from aiohttp import web

from .core.loader import load_tags
from .core.search import search_tags

_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_PATH = os.path.join(_PLUGIN_DIR, "data")


@server.PromptServer.instance.routes.get("/danbooru-autocomplete/tags")
async def get_tags(request: web.Request)->web.Response:
    '''处理标签搜索请求
    @param request: HTTP请求对象，包含查询参数:
        - q: 搜索查询字符串
        - limit: 返回结果的最大数量（可选，默认为20，最大为50）
    @return: JSON响应，包含匹配的标签列表，每个标签包含raw、display、count和category字段
    '''
    query = request.rel_url.query.get("q", "").strip().lower()
    try:
        limit = max(1, min(50, int(request.rel_url.query.get("limit", 20))))
    except ValueError:
        limit = 20

    if len(query) < 2:
        return web.json_response([])

    tags = load_tags(_DATA_PATH)
    if not tags:
        return web.Response(
            status=404,
            content_type="application/json",
            text='{"error":"Tags file not found."}',
        )

    return web.json_response(search_tags(tags, query, limit))


@server.PromptServer.instance.routes.get("/danbooru-autocomplete/status")
async def get_status(request: web.Request)->web.Response:
    '''提供插件状态信息接口
    @param request: HTTP请求对象
    @return: JSON响应，包含插件状态信息，如标签数量、数据文件列表等
    '''
    tags = load_tags(_DATA_PATH)
    files = [
        file
        for file in os.listdir(_DATA_PATH)
        if file.endswith(".txt") or file.endswith(".csv")
    ] if os.path.isdir(_DATA_PATH) else []

    return web.json_response(
        {
            "ok": len(tags) > 0,
            "tag_count": len(tags),
            "files": files,
            "file_exists": len(files) > 0,
            "sample": [{"raw": t[0], "display": t[1]} for t in tags[:5]],
        }
    )
