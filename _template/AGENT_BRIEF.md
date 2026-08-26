# sahelp 内容编写规范（供参与编写帮助文档的 agent 阅读）

你正在为 `D:\projects\sla\sahelp` 编写 CHM 风格的帮助文档主题页。素材来自本机仓库，
**必须以真实代码 / 真实 README 为依据，不要凭空编造命令或语法**；素材里没有的内容宁可
不写，也不要猜测。

## 产出物

1. 若干主题页 HTML，写到分配给你的 `content/<章节目录>/` 下；
2. 同目录的 `_manifest.json`（覆盖写，格式见下）。

## 主题页 HTML 规则（必须遵守）

- 每页骨架：复制 `_template/topic_template.html` 的结构。
- `<meta charset="utf-8">`；文件以 UTF-8 无 BOM 保存。全文用简体中文，代码/标识符保留原文。
- 样式表路径固定为 `<link rel="stylesheet" href="../../assets/help.css">`（所有主题固定两层深，勿改）。
- `<body class="topic">`，页首放面包屑：
  `<div class="topic-header">章节标题 &gt; 主题标题</div>`，随后 `<h1>主题标题</h1>`。
- **只允许在本章节目录内互链**（相对路径如 `syntax.html`、`types.html#struct`）。
  跨章节链接一律不写，避免死链。外部 URL 可以直接用绝对 https 链接。
- 可用的排版元素（样式已定义）：`h1-h3`、`p`、`ul/ol`、`table`、
  `<pre><code>…</code></pre>`（代码块）、行内 `<code>`、
  `<div class="note"><span class="label">注意</span>…</div>`、
  `<div class="warning"><span class="label">警告</span>…</div>`、`<blockquote>`。
- 不要引入图片、JS、其他 CSS。表格用于参数 / 命令 / 类型清单。
- 命令行示例统一放在 `<pre><code>` 中，并注明运行目录或前置条件。

## _manifest.json 格式

```json
{
  "topics": [
    {
      "id": "syntax",              // 本章节内唯一，小写连字符
      "title": "词法与基础语法",
      "file": "syntax.html",       // 同目录文件名
      "keywords": ["词法", "token", "关键字"],   // 3-8 个，进入索引页签
      "parent": null               // 或同清单内另一 topic 的 id，形成二级树
    }
  ]
}
```

- 文件名建议按阅读顺序编号前缀：`01_xxx.html`、`02_yyy.html`。
- `parent` 用于把细节页挂在概览页之下，一般不超过两层。

## 质量要求

- 单页正文 300~1500 字为宜；大主题拆多页，不要塞成一篇长文。
- 每页开头用 2~3 句话概括"这一页讲什么、读完能做什么"。
- 引用具体命令、类型名、函数签名时用行内 `<code>`。
- 写完后自查：HTML 标签配对、manifest 中 file 与实际文件一致、无跨章节链接。
