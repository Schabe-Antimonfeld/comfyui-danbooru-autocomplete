from typing import Dict, List, Sequence

from .loader import TagTuple


def search_tags(tags: Sequence[TagTuple], query: str, limit: int) -> List[Dict[str, int | str]]:
    '''在标签列表中搜索匹配的标签
    @param tags: 标签列表
    @param query: 搜索查询
    @param limit: 返回结果的最大数量
    @return: 匹配的标签列表
    '''
    query_with_us = query.replace(" ", "_")
    query_with_sp = query.replace("_", " ")

    prefix_hits: List[Dict[str, int | str]] = []
    contain_hits: List[Dict[str, int | str]] = []

    for raw, display, count, category in tags:
        raw_l = raw.lower()
        disp_l = display.lower()

        is_prefix = (
            raw_l.startswith(query_with_us)
            or raw_l.startswith(query)
            or disp_l.startswith(query_with_sp)
            or disp_l.startswith(query)
        )

        is_contain = (
            query_with_us in raw_l
            or query in raw_l
            or query_with_sp in disp_l
            or query in disp_l
        )

        item = {"tag": display, "raw": raw, "count": count, "category": category}
        if is_prefix:
            prefix_hits.append(item)
        elif is_contain:
            contain_hits.append(item)

        if len(prefix_hits) >= limit and len(contain_hits) >= limit:
            break

    return (prefix_hits + contain_hits)[:limit]
