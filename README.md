# ComfyUI Danbooru Autocomplete

在 **CLIP 文本编码节点**（CLIPTextEncode）中实现基于 Danbooru 词库的自动补全功能。

## 功能特性

- 🔍 **实时搜索**：输入 2 个字符后自动触发补全
- 🎨 **分类高亮**：不同颜色区分 general / artist / copyright / character / meta 标签
- 📊 **使用频次**：显示每个 tag 的使用次数（K/M 简写）
- ⌨️ **键盘操作**：方向键选择，Enter/Tab 确认，Esc 关闭
- 🖱️ **鼠标点击**：直接点击插入 tag
- ✍️ **智能插入**：自动处理逗号分隔，不破坏已有内容
- 🚀 **轻量快速**：服务端过滤，前端零依赖

## 安装步骤

### 1. 复制插件

将整个 `comfyui-danbooru-autocomplete` 文件夹复制到 ComfyUI 的自定义节点目录：

```
ComfyUI/
└── custom_nodes/
    └── comfyui-danbooru-autocomplete/
        ├── __init__.py
        ├── web/
        │   ├── js/
        │   │   └── danbooru_autocomplete.js
        │   └── css/
        │       └── danbooru_autocomplete.css
        └── data/
            └── danbooru_tags.txt
```
### 2. 重启 ComfyUI

重启后打开任意包含 `CLIPTextEncode` 节点的工作流，在文本框中输入即可看到补全。

## 使用方式

1. 在 CLIP 文本编码节点的文本框中输入 tag（至少 2 个字符）
2. 下拉菜单自动出现，显示匹配的 Danbooru tag
3. 使用 **↑↓** 方向键或鼠标选择
4. 按 **Enter** 或 **Tab** 插入选中 tag
5. 按 **Esc** 关闭下拉菜单

## 支持的节点

- `CLIPTextEncode`（标准 CLIP 文本编码）
- `CLIPTextEncodeSDXL`（SDXL 版本）
- `CLIPTextEncodeSDXLRefiner`（SDXL Refiner）
- 所有包含多行文本框的节点（通用监听）

## Tag 分类颜色说明

| 颜色 | 分类 |
|------|------|
| 🔵 蓝色 | General（通用） |
| 🟠 橙色 | Artist（画师） |
| 🟣 紫色 | Copyright（版权） |
| 🟢 绿色 | Character（角色） |
| 🔴 红色 | Meta（元数据） |

## 目录结构

```
comfyui-danbooru-autocomplete/
├── __init__.py          # 插件入口，注册 API 路由
├── setup.py             # 数据库初始化脚本
├── README.md            # 说明文档
├── web/
│   └── js/
│       └── danbooru_autocomplete.js  # 前端自动补全逻辑
└── data/
    └── danbooru_tags.txt             # Tag 数据库（自动生成）
```

## 工作原理

1. `__init__.py` 在 ComfyUI 服务端注册 `/danbooru-autocomplete/tags?q=<query>` API
2. 前端 JS 监听文本框 `input` 事件，防抖 150ms 后发送请求
3. 服务端读取 `danbooru_tags.txt`，过滤匹配并按前缀优先 + 频次排序返回
4. 前端渲染下拉菜单，处理键盘/鼠标交互

## 常见问题

**Q: 下拉菜单没有出现？**
- 确认 `data/danbooru_tags.txt` 文件存在
- 打开浏览器控制台查看是否有报错
- 确认输入了至少 2 个字符

**Q: 如何添加自定义 tag？**  
直接编辑 `data/danbooru_tags.txt`，每行格式：`tag_name,count,category`

**Q: 是否支持中文搜索？**  
Danbooru 标签均为英文，暂时不支持中文搜索。
以后有计划添加部分翻译与中文搜索功能。
