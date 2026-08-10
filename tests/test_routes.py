import asyncio
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest
from aiohttp import ClientError


class FakeRoutes:
    def get(self, _path):
        def decorator(func):
            return func

        return decorator


class FakePromptServer:
    instance = types.SimpleNamespace(routes=FakeRoutes())


def import_routes_module():
    """
    routes.py 使用了：
        import server
        from .core.loader import ...
        from .core.search import ...

    所以测试时不能直接 import routes。
    这里创建一个假的包名 dac_test_package，让相对导入能正常工作。
    """
    package_name = "dac_test_package"

    for name in list(sys.modules):
        if name == package_name or name.startswith(f"{package_name}."):
            del sys.modules[name]

    sys.modules["server"] = types.SimpleNamespace(PromptServer=FakePromptServer)

    root = Path(__file__).resolve().parents[1]

    package = types.ModuleType(package_name)
    package.__path__ = [str(root)]
    package.__file__ = str(root / "__init__.py")
    sys.modules[package_name] = package

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.core.routes",
        root / "core/routes.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{package_name}.routes"] = module
    spec.loader.exec_module(module)

    return module


@pytest.fixture()
def routes():
    return import_routes_module()


def make_request(query: dict[str, str]):
    return types.SimpleNamespace(
        rel_url=types.SimpleNamespace(query=query),
    )


def response_json(response):
    return json.loads(response.text)


@pytest.mark.parametrize(
    "config, expected",
    [
        (
            {"proxy_type": "http", "proxy_host": "127.0.0.1", "proxy_port": ""},
            {"mode": "direct", "proxy": ""},
        ),
        (
            {"proxy_type": "http", "proxy_host": "127.0.0.1", "proxy_port": "7890"},
            {"mode": "http-proxy", "proxy": "http://127.0.0.1:7890"},
        ),
        (
            {"proxy_type": "socks5", "proxy_host": "127.0.0.1", "proxy_port": "1080"},
            {"mode": "socks5-proxy", "proxy": "socks5://127.0.0.1:1080"},
        ),
        (
            {"proxy_type": "socks5h", "proxy_host": "127.0.0.1", "proxy_port": "1080"},
            {"mode": "socks5-proxy", "proxy": "socks5h://127.0.0.1:1080"},
        ),
        (
            {"proxy_type": "ftp", "proxy_host": "127.0.0.1", "proxy_port": "7890"},
            {"mode": "direct", "proxy": ""},
        ),
        (
            {"proxy_type": "http", "proxy_host": "127.0.0.1", "proxy_port": "abc"},
            {"mode": "direct", "proxy": ""},
        ),
        (
            {"proxy_type": "http", "proxy_host": "127.0.0.1", "proxy_port": "99999"},
            {"mode": "direct", "proxy": ""},
        ),
    ],
)
def test_resolve_proxy_settings(routes, monkeypatch, config, expected):
    assert routes._resolve_proxy_settings(config) == expected


def test_proxy_debug(routes):
    assert routes._proxy_debug(
        {
            "mode": "http-proxy",
            "proxy": "http://127.0.0.1:7890",
        }
    ) == {
        "proxy_mode": "http-proxy",
        "proxy": "http://127.0.0.1:7890",
    }


def test_build_socks_connector_missing(routes, monkeypatch):
    def fake_import_module(_name):
        raise ImportError

    monkeypatch.setattr(routes, "import_module", fake_import_module)

    assert routes._build_socks_connector("socks5://127.0.0.1:1080") is None


def test_build_socks_connector_available(routes, monkeypatch):
    class FakeProxyConnector:
        @staticmethod
        def from_url(url):
            return {"connector_url": url}

    fake_module = types.SimpleNamespace(ProxyConnector=FakeProxyConnector)

    monkeypatch.setattr(routes, "import_module", lambda _name: fake_module)

    assert routes._build_socks_connector("socks5://127.0.0.1:1080") == {
        "connector_url": "socks5://127.0.0.1:1080",
    }


def test_normalize_online_tags(routes):
    result = routes._normalize_online_tags(
        [
            {"name": "blue_archive", "post_count": "123", "category": "3"},
            {"name": "fate_(series)", "post_count": 456, "category": 4},
            {"name": "", "post_count": 999, "category": 0},
        ]
    )

    assert result == [
        {
            "tag": "blue archive",
            "raw": "blue_archive",
            "count": 123,
            "category": 3,
        },
        {
            "tag": r"fate \(series\)",
            "raw": "fate_(series)",
            "count": 456,
            "category": 4,
        },
    ]


def test_get_tags_short(routes):
    response = asyncio.run(routes.get_tags(make_request({"q": "a"})))

    assert response.status == 200
    assert response_json(response) == []


def test_get_tags_missing(routes, monkeypatch):
    monkeypatch.setattr(routes, "load_tags", lambda _path: [])

    response = asyncio.run(routes.get_tags(make_request({"q": "blue"})))

    assert response.status == 404
    assert response_json(response) == {
        "error": "Tags file not found.",
    }


def test_get_tags_search(routes, monkeypatch):
    tags = [
        ("blue_archive", "blue archive", 3, 1000),
        ("blue_eyes", "blue eyes", 0, 900),
    ]

    called = {}

    def fake_search_tags(given_tags, query, limit):
        called["tags"] = given_tags
        called["query"] = query
        called["limit"] = limit
        return [
            {
                "tag": "blue archive",
                "raw": "blue_archive",
                "count": 1000,
                "category": 3,
            }
        ]

    monkeypatch.setattr(routes, "load_tags", lambda _path: tags)
    monkeypatch.setattr(routes, "search_tags", fake_search_tags)

    response = asyncio.run(
        routes.get_tags(make_request({"q": " BLue ", "limit": "999"}))
    )

    assert response.status == 200
    assert called == {
        "tags": tags,
        "query": "blue",
        "limit": 50,
    }
    assert response_json(response) == [
        {
            "tag": "blue archive",
            "raw": "blue_archive",
            "count": 1000,
            "category": 3,
        }
    ]


def test_get_tags_bad_limit(routes, monkeypatch):
    called = {}

    monkeypatch.setattr(
        routes,
        "load_tags",
        lambda _path: [("blue_archive", "blue archive", 3, 1000)],
    )

    def fake_search_tags(_tags, _query, limit):
        called["limit"] = limit
        return []

    monkeypatch.setattr(routes, "search_tags", fake_search_tags)

    response = asyncio.run(routes.get_tags(make_request({"q": "blue", "limit": "bad"})))

    assert response.status == 200
    assert called["limit"] == 20


def test_get_online_tags_short(routes):
    response = asyncio.run(routes.get_online_tags(make_request({"q": "a"})))

    assert response.status == 200
    assert response_json(response) == []


def test_get_online_tags_no_socks(routes, monkeypatch):
    monkeypatch.setattr(
        routes,
        "_resolve_proxy_settings",
        lambda _config: {
            "mode": "socks5-proxy",
            "proxy": "socks5://127.0.0.1:1080",
        },
    )
    monkeypatch.setattr(routes, "_build_socks_connector", lambda _proxy_url: None)

    response = asyncio.run(routes.get_online_tags(make_request({"q": "blue"})))
    body = response_json(response)

    assert response.status == 500
    assert body["error"] == "socks5 proxy requires aiohttp-socks"
    assert body["proxy_mode"] == "socks5-proxy"
    assert body["proxy"] == "socks5://127.0.0.1:1080"


class FakeResponse:
    def __init__(self, status=200, data=None):
        self.status = status
        self._data = data if data is not None else []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._data


class FakeClientSession:
    calls = []
    init_kwargs = []
    response_status = 200
    response_data = []

    def __init__(self, *args, **kwargs):
        self.__class__.init_kwargs.append(kwargs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, **kwargs):
        self.__class__.calls.append({"url": url, **kwargs})
        return FakeResponse(
            status=self.__class__.response_status,
            data=self.__class__.response_data,
        )


def reset_fake_client_session():
    FakeClientSession.calls = []
    FakeClientSession.init_kwargs = []
    FakeClientSession.response_status = 200
    FakeClientSession.response_data = []


def test_get_online_tags_direct(routes, monkeypatch):
    reset_fake_client_session()

    FakeClientSession.response_data = [
        {"name": "blue_archive", "post_count": 123, "category": 3},
    ]

    monkeypatch.setattr(
        routes,
        "_resolve_proxy_settings",
        lambda _config: {
            "mode": "direct",
            "proxy": "",
        },
    )
    monkeypatch.setattr(routes, "ClientSession", FakeClientSession)

    response = asyncio.run(
        routes.get_online_tags(make_request({"q": " BLue ", "limit": "999"}))
    )

    assert response.status == 200
    assert response_json(response) == [
        {
            "tag": "blue archive",
            "raw": "blue_archive",
            "count": 123,
            "category": 3,
        }
    ]

    assert FakeClientSession.calls[0]["url"] == routes._ONLINE_API
    assert FakeClientSession.calls[0]["proxy"] is None
    assert FakeClientSession.calls[0]["params"] == {
        "search[name_matches]": "blue*",
        "search[order]": "count",
        "limit": "50",
        "only": "name,post_count,category",
    }


def test_get_online_tags_bad_limit(routes, monkeypatch):
    reset_fake_client_session()

    monkeypatch.setattr(
        routes,
        "_resolve_proxy_settings",
        lambda _config: {
            "mode": "direct",
            "proxy": "",
        },
    )
    monkeypatch.setattr(routes, "ClientSession", FakeClientSession)

    response = asyncio.run(
        routes.get_online_tags(make_request({"q": "blue", "limit": "bad"}))
    )

    assert response.status == 200
    assert FakeClientSession.calls[0]["params"]["limit"] == "20"


def test_get_online_tags_http_proxy(routes, monkeypatch):
    reset_fake_client_session()

    monkeypatch.setattr(routes, "ClientSession", FakeClientSession)

    response = asyncio.run(
        routes.get_online_tags(
            make_request(
                {
                    "q": "blue",
                    "proxy_type": "http",
                    "proxy_host": "127.0.0.1",
                    "proxy_port": "7890",
                }
            )
        )
    )

    assert response.status == 200
    assert FakeClientSession.calls[0]["proxy"] == "http://127.0.0.1:7890"


def test_get_online_tags_socks_proxy(routes, monkeypatch):
    reset_fake_client_session()

    connector = object()

    monkeypatch.setattr(
        routes,
        "_resolve_proxy_settings",
        lambda _config: {
            "mode": "socks5-proxy",
            "proxy": "socks5://127.0.0.1:1080",
        },
    )
    monkeypatch.setattr(routes, "_build_socks_connector", lambda _proxy_url: connector)
    monkeypatch.setattr(routes, "ClientSession", FakeClientSession)

    response = asyncio.run(routes.get_online_tags(make_request({"q": "blue"})))

    assert response.status == 200
    assert FakeClientSession.init_kwargs[0]["connector"] is connector
    assert "proxy" not in FakeClientSession.calls[0]


def test_get_online_tags_socks_status(routes, monkeypatch):
    reset_fake_client_session()

    FakeClientSession.response_status = 503
    connector = object()

    monkeypatch.setattr(
        routes,
        "_resolve_proxy_settings",
        lambda _config: {
            "mode": "socks5-proxy",
            "proxy": "socks5://127.0.0.1:1080",
        },
    )
    monkeypatch.setattr(routes, "_build_socks_connector", lambda _proxy_url: connector)
    monkeypatch.setattr(routes, "ClientSession", FakeClientSession)

    response = asyncio.run(routes.get_online_tags(make_request({"q": "blue"})))
    body = response_json(response)

    assert response.status == 502
    assert body["error"] == "Danbooru upstream error"
    assert body["status"] == 503
    assert body["proxy_mode"] == "socks5-proxy"


def test_get_online_tags_upstream_status(routes, monkeypatch):
    reset_fake_client_session()

    FakeClientSession.response_status = 503

    monkeypatch.setattr(
        routes,
        "_resolve_proxy_settings",
        lambda _config: {
            "mode": "direct",
            "proxy": "",
        },
    )
    monkeypatch.setattr(routes, "ClientSession", FakeClientSession)

    response = asyncio.run(routes.get_online_tags(make_request({"q": "blue"})))
    body = response_json(response)

    assert response.status == 502
    assert body["error"] == "Danbooru upstream error"
    assert body["status"] == 503
    assert body["proxy_mode"] == "direct"


def test_get_online_tags_bad_data(routes, monkeypatch):
    reset_fake_client_session()

    FakeClientSession.response_data = {"unexpected": "object"}

    monkeypatch.setattr(
        routes,
        "_resolve_proxy_settings",
        lambda _config: {
            "mode": "direct",
            "proxy": "",
        },
    )
    monkeypatch.setattr(routes, "ClientSession", FakeClientSession)

    response = asyncio.run(routes.get_online_tags(make_request({"q": "blue"})))

    assert response.status == 200
    assert response_json(response) == []


class ClientErrorSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, *_args, **_kwargs):
        raise ClientError("network failed")


def test_get_online_tags_client_error(routes, monkeypatch):
    monkeypatch.setattr(
        routes,
        "_resolve_proxy_settings",
        lambda _config: {
            "mode": "direct",
            "proxy": "",
        },
    )
    monkeypatch.setattr(
        routes, "ClientSession", lambda *args, **kwargs: ClientErrorSession()
    )

    response = asyncio.run(routes.get_online_tags(make_request({"q": "blue"})))
    body = response_json(response)

    assert response.status == 502
    assert body["error"] == "Failed to fetch online tags"
    assert "network failed" in body["detail"]


class TimeoutSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, *_args, **_kwargs):
        raise TimeoutError


def test_get_online_tags_timeout(routes, monkeypatch):
    monkeypatch.setattr(
        routes,
        "_resolve_proxy_settings",
        lambda _config: {
            "mode": "direct",
            "proxy": "",
        },
    )
    monkeypatch.setattr(
        routes, "ClientSession", lambda *args, **kwargs: TimeoutSession()
    )

    response = asyncio.run(routes.get_online_tags(make_request({"q": "blue"})))
    body = response_json(response)

    assert response.status == 504
    assert body["error"] == "Online tags request timed out"


def test_get_status(routes, monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "tags.txt").write_text("blue_archive,1000,3", encoding="utf-8")
    (data_dir / "tags.csv").write_text(
        "raw,count,category\n1girl,999,0", encoding="utf-8"
    )
    (data_dir / "ignore.md").write_text("ignored", encoding="utf-8")

    tags = [
        ("blue_archive", "blue archive", 3, 1000),
        ("1girl", "1girl", 0, 999),
    ]

    monkeypatch.setattr(routes, "_DATA_PATH", str(data_dir))
    monkeypatch.setattr(routes, "load_tags", lambda _path: tags)

    response = asyncio.run(routes.get_status(make_request({})))
    body = response_json(response)

    assert response.status == 200
    assert body["ok"] is True
    assert body["tag_count"] == 2
    assert sorted(body["files"]) == ["tags.csv", "tags.txt"]
    assert body["file_exists"] is True
    assert body["sample"] == [
        {"raw": "blue_archive", "display": "blue archive"},
        {"raw": "1girl", "display": "1girl"},
    ]
