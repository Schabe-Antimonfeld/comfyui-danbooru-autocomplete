# ComfyUI Danbooru Autocomplete

在 **CLIP 文本编码节点**（CLIPTextEncode）中实现基于 Danbooru 词库的自动补全功能。

## 功能特性

- 🔍 **实时搜索**：输入 2 个字符后自动触发补全
- 🌐 **在线优先 + 本地降级**：优先使用 Danbooru 在线接口，失败后自动回退本地词库
- 🧭 **代理支持**：支持 HTTP / SOCKS5 代理访问在线 Danbooru
- 🎨 **分类高亮**：不同颜色区分 general / artist / copyright / character / meta 标签
- 📊 **使用频次**：显示每个 tag 的使用次数（K/M 简写）
- ⌨️ **键盘操作**：方向键选择，Enter/Tab 确认，Esc 关闭
- 🖱️ **鼠标点击**：直接点击插入 tag
- ✍️ **智能插入**：自动处理逗号分隔，不破坏已有内容
- 🚀 **轻量快速**：服务端过滤，前端零依赖

## 安装步骤

### 1. 复制插件

将仓库克隆到本地
```
git clone https://github.com/Schabe-Antimonfeld/comfyui-danbooru-autocomplete.git
```

将整个 `comfyui-danbooru-autocomplete` 文件夹复制到 ComfyUI 的自定义节点目录：

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

## 代理配置

在线查询 Danbooru 使用后端接口 `/danbooru-autocomplete/online-tags`，代理由以下文件控制：

- `configs/proxy_config.json`

默认配置示例：

```json
{
	"proxy_type": "http",
	"proxy_host": "127.0.0.1",
	"proxy_port": ""
}
```

字段说明：

- `proxy_type`：支持 `http`、`socks5`、`socks5h`
- `proxy_host`：代理主机地址，例如 `127.0.0.1`
- `proxy_port`：代理端口；留空表示不使用代理（直连）

行为规则：

- `proxy_port` 为空、端口非法、或 `proxy_type` 非法时，自动切换为直连模式
- `socks5/socks5h` 需要 `aiohttp-socks`（已在 `requirements.txt` 中声明）
- 在线请求超时（8 秒）或失败时，前端会自动回退到本地词库查询

推荐场景：

- 无法直接访问 Danbooru：配置 HTTP/SOCKS5 代理
- 仅需本地词库：将 `proxy_port` 留空，插件会按直连失败后回退本地，稍作等待即可
- 网络不稳定：保持默认在线优先，插件会自动处理降级

## 常见问题

**Q: 下拉菜单没有出现？**
- 确认 `data/` 内有合法的`.txt` 或 `.csv` 文件存在(正常情况已经内置，各一份)
- 打开浏览器控制台查看是否有报错
- 确认输入了至少 2 个字符

**Q: 如何添加自定义 tag？**  
在 `data/` 内创建一个新的 `.txt` 或 `.csv` 文件
txt每行格式：`tag_name,category,count`
csv需包含`raw`, `category`, `count`三列, 其余随意
具体格式可参考 `data/` 下的两个文件 [danbooru.txt](./data/danbooru.txt) 与 [danbooru.csv](./data/danbooru.csv)

**Q: 是否支持中文搜索？**  
Danbooru 标签均为英文，暂时不支持中文搜索。
以后有计划添加部分翻译与中文搜索功能。

**Q: 配了代理但在线搜索仍失败？**
- 检查 `configs/proxy_config.json` 是否为合法 JSON
- 检查 `proxy_type` 是否为 `http` / `socks5`
- 检查 `proxy_port` 是否为 1~65535 的整数
- 若使用 SOCKS5，确认环境已安装 `aiohttp-socks`

**Q: 如何确认当前是在在线模式还是本地模式？**
- 补全下拉标题会显示 `Danbooru Live`（在线）或 `Local`（本地）
