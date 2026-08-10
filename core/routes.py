import os
from importlib import import_module

import server  # type: ignore
from aiohttp import ClientError, ClientSession, ClientTimeout, web

from .loader import load_tags, to_display
from .search import search_tags

_PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_PATH = os.path.join(_PLUGIN_DIR, "data")
_ONLINE_API = "https://danbooru.donmai.us/tags.json"


def _resolve_proxy_settings(config) -> dict[str, str]:
    """Resolve proxy mode and URL from request settings."""
    proxy_type = str(config.get("proxy_type", "none") or "").strip().lower()
    proxy_host = str(config.get("proxy_host", "127.0.0.1") or "").strip()
    proxy_port = str(config.get("proxy_port", "") or "").strip()

    if not proxy_port:
        return {"mode": "direct", "proxy": ""}

    if proxy_type not in {"http", "socks5", "socks5h"}:
        return {"mode": "direct", "proxy": ""}

    try:
        port_value = int(proxy_port)
    except ValueError:
        return {"mode": "direct", "proxy": ""}

    if not (1 <= port_value <= 65535):
        return {"mode": "direct", "proxy": ""}

    if proxy_type == "http":
        return {
            "mode": "http-proxy",
            "proxy": f"http://{proxy_host}:{port_value}",
        }

    return {
        "mode": "socks5-proxy",
        "proxy": f"{proxy_type}://{proxy_host}:{port_value}",
    }


def _proxy_debug(settings: dict[str, str]) -> dict[str, str]:
    """Build lightweight debug info for online request failures."""
    return {
        "proxy_mode": settings.get("mode", "direct"),
        "proxy": settings.get("proxy", ""),
    }


def _build_socks_connector(proxy_url: str):
    """Build socks connector from aiohttp-socks when available."""
    try:
        module = import_module("aiohttp_socks")
    except ImportError:
        return None
    return module.ProxyConnector.from_url(proxy_url)


def _normalize_online_tags(items: list[dict]) -> list[dict[str, int | str]]:
    normalized: list[dict[str, int | str]] = []
    for item in items:
        raw = str(item.get("name", "") or "")
        if not raw:
            continue
        normalized.append(
            {
                "tag": to_display(raw),
                "raw": raw,
                "count": int(item.get("post_count", 0) or 0),
                "category": int(item.get("category", 0) or 0),
            }
        )
    return normalized


@server.PromptServer.instance.routes.get("/danbooru-autocomplete/tags")
async def get_tags(request: web.Request) -> web.Response:
    """处理标签搜索请求
    @param request: HTTP请求对象，包含查询参数:
        - q: 搜索查询字符串
        - limit: 返回结果的最大数量（可选，默认为20，最大为50）
    @return: JSON响应，包含匹配的标签列表
    """
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


@server.PromptServer.instance.routes.get("/danbooru-autocomplete/online-tags")
async def get_online_tags(request: web.Request) -> web.Response:
    """Fetch online Danbooru tags via backend proxy settings."""
    query = request.rel_url.query.get("q", "").strip().lower()
    try:
        limit = max(1, min(50, int(request.rel_url.query.get("limit", 20))))
    except ValueError:
        limit = 20

    if len(query) < 2:
        return web.json_response([])

    params = {
        "search[name_matches]": f"{query}*",
        "search[order]": "count",
        "limit": str(limit),
        "only": "name,post_count,category",
    }

    proxy_settings = _resolve_proxy_settings(request.rel_url.query)
    proxy_mode = proxy_settings.get("mode", "direct")
    proxy_url = proxy_settings.get("proxy", "")
    proxy_debug = _proxy_debug(proxy_settings)
    timeout = ClientTimeout(total=8)

    try:
        if proxy_mode == "socks5-proxy":
            connector = _build_socks_connector(proxy_url)
            if connector is None:
                return web.json_response(
                    {
                        "error": "socks5 proxy requires aiohttp-socks",
                        **proxy_debug,
                    },
                    status=500,
                )
            async with ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(_ONLINE_API, params=params) as response:
                    if response.status != 200:
                        return web.json_response(
                            {
                                "error": "Danbooru upstream error",
                                "status": response.status,
                                **proxy_debug,
                            },
                            status=502,
                        )
                    data = await response.json()
        else:
            async with ClientSession(timeout=timeout) as session:
                async with session.get(
                    _ONLINE_API,
                    params=params,
                    proxy=proxy_url or None,
                ) as response:
                    if response.status != 200:
                        return web.json_response(
                            {
                                "error": "Danbooru upstream error",
                                "status": response.status,
                                **proxy_debug,
                            },
                            status=502,
                        )
                    data = await response.json()
    except ClientError as error:
        return web.json_response(
            {
                "error": "Failed to fetch online tags",
                "detail": str(error),
                **proxy_debug,
            },
            status=502,
        )
    except TimeoutError:
        return web.json_response(
            {
                "error": "Online tags request timed out",
                **proxy_debug,
            },
            status=504,
        )

    if not isinstance(data, list):
        return web.json_response([])

    return web.json_response(_normalize_online_tags(data))


@server.PromptServer.instance.routes.get("/danbooru-autocomplete/status")
async def get_status(request: web.Request) -> web.Response:
    """提供插件状态信息接口
    @param request: HTTP请求对象
    @return: JSON响应，包含插件状态信息，如标签数量、数据文件列表等
    """
    tags = load_tags(_DATA_PATH)
    files = (
        [
            file
            for file in os.listdir(_DATA_PATH)
            if file.endswith(".txt") or file.endswith(".csv")
        ]
        if os.path.isdir(_DATA_PATH)
        else []
    )

    return web.json_response(
        {
            "ok": len(tags) > 0,
            "tag_count": len(tags),
            "files": files,
            "file_exists": len(files) > 0,
            "sample": [{"raw": t[0], "display": t[1]} for t in tags[:5]],
        }
    )
