from core.search import search_tags


TAGS = [
    ("blue_archive", "blue archive", 3, 1000),
    ("blue_eyes", "blue eyes", 0, 900),
    ("dark_blue_hair", "dark blue hair", 0, 500),
    ("hakurei_reimu", "hakurei reimu", 4, 800),
    ("reimu", "reimu", 4, 700),
]


def test_search_prefix():
    result = search_tags(TAGS, "blue", 10)

    assert [x["raw"] for x in result] == [
        "blue_archive",
        "blue_eyes",
        "dark_blue_hair",
    ]


def test_search_format():
    result1 = search_tags(TAGS, "blue archive", 10)
    result2 = search_tags(TAGS, "blue_archive", 10)

    assert result1[0]["raw"] == "blue_archive"
    assert result1[0]["tag"] == "blue archive"
    assert result2[0]["raw"] == "blue_archive"
    assert result2[0]["tag"] == "blue archive"


def test_search_limit():
    result = search_tags(TAGS, "blue", 2)

    assert len(result) == 2
    assert [x["raw"] for x in result] == [
        "blue_archive",
        "blue_eyes",
    ]


def test_search_shape():
    result = search_tags(TAGS, "hakurei", 1)

    assert result == [
        {
            "tag": "hakurei reimu",
            "raw": "hakurei_reimu",
            "category": 4,
            "count": 800,
        }
    ]
