import csv
import os
from typing import List, Tuple

TagTuple = Tuple[str, str, int, int]


def to_display(name: str) -> str:
    """将 danbooru raw tag 转换为 ComfyUI prompt 格式：
    - 下划线 → 空格
    - 括号转义，避免被 ComfyUI 解析为权重语法 (tag:1.2)
    @param name: danbooru raw tag
    @return: 转换后的 display tag
    """
    name = name.replace("_", " ")
    name = name.replace("(", r"\(").replace(")", r"\)")
    return name


def load_txt(file_path: str) -> List[TagTuple]:
    """加载txt格式的tag, 每行格式为：raw,count,category
    @param file: txt文件路径
    @return: 加载的tag列表，每个元素为(raw, display, count, category)的元组
    """
    tags: List[TagTuple] = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            parts = line.split(",")
            raw = parts[0]

            try:
                category = int(parts[1]) if len(parts) > 2 else 0
            except ValueError:
                category = 0

            try:
                count = int(parts[2]) if len(parts) > 1 else 0
            except ValueError:
                count = 0

            tags.append((raw, to_display(raw), count, category))
    return tags


def load_csv(file_path: str) -> List[TagTuple]:
    """加载csv格式的tag, 该csv应包含: raw,count,category
    @param file: csv文件路径
    @return: 加载的tag列表，每个元素为(raw, display, count, category)的元组
    """
    tags: List[TagTuple] = []
    with open(file_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            raw = row.get("raw", "").strip()
            if not raw:
                continue

            try:
                count = int(row.get("count", 0))
            except ValueError:
                count = 0

            try:
                category = int(row.get("category", 0))
            except ValueError:
                category = 0

            tags.append((raw, to_display(raw), count, category))
    return tags


def load_tags(data_path: str) -> List[TagTuple]:
    '''
    加载数据目录中的所有tag
    @param data_path: 数据目录路径
    @return: 加载的tag列表，每个元素为(raw, display, count, category)的元组
    '''
    normalized_path = os.path.normpath(data_path)
    if not os.path.isdir(normalized_path):
        return []

    tags: List[TagTuple] = []
    for file_name in os.listdir(normalized_path):
        file_path = os.path.join(normalized_path, file_name)
        if file_name.endswith(".txt"):
            tags.extend(load_txt(file_path))
        elif file_name.endswith(".csv"):
            tags.extend(load_csv(file_path))

    tags.sort(key=lambda item: item[2], reverse=True)

    seen = set()
    unique_tags: List[TagTuple] = []
    for raw, display, count, category in tags:
        if display in seen:
            continue
        seen.add(display)
        unique_tags.append((raw, display, count, category))

    return unique_tags
