# sahelp — SA / SLA 帮助文档（CHM 风格）

为 SA（Safe ASM）工具链与 SLA 语言编写的 CHM 风格帮助系统：既是可直接双击打开的 HTML
帮助查看器（左侧「目录 / 索引 / 搜索」三个页签，右侧内容窗格），也生成可被
HTML Help Workshop 编译成真正 `.chm` 的工程文件。

## 目录结构

```
sahelp/
├── build.py                  # 构建脚本（Python 3 标准库）
├── assets/help.css           # 查看器与主题页共用样式
├── _template/topic_template.html   # 新主题页模板
├── content/<章节>/            # 主题页 + 该章节的 _manifest.json
│   ├── _manifest.json
│   └── *.html
├── dist/                     # 构建产物：直接用浏览器打开 dist/default.html
└── build/chm/                # help.hhc / help.hhk / help.hhp（供 hhc.exe 编译 .chm）
```

## 章节

| 目录 | 章节 | 内容 |
|---|---|---|
| content/01_overview | 入门指南 | SA/SLA 是什么、安装构建、快速上手 |
| content/02_sla_lang | SLA 语言参考 | 词法、语法、类型、所有权、特性清单 |
| content/03_sa_asm | SA 汇编与 SAB | SA 指令集、SAB 字节码格式 |
| content/04_cli | 命令行参考 | `sa sla …` 等全部 CLI 子命令 |
| content/05_plugins | 插件参考 | sax/mui/react/vite/tui/vm/wgpu/db/deno/node/pkg/http_*/bc2sa 等 |
| content/06_stdlib | 标准库 | sa_std / sla_std 契约与模块 |
| content/07_ui | SAX / MUI 界面开发 | 用 sax+mui+react+vite 写界面（参考 codex_ui） |
| content/08_faq | FAQ 与故障排查 | 常见问题、已知问题、路线图状态 |

## 使用

```powershell
python build.py             # 构建 dist/ 与 build/chm/
python build.py --serve     # 构建并启动 http://127.0.0.1:8765/default.html 预览
```

编译为真正的 `.chm`（需安装 [HTML Help Workshop](https://learn.microsoft.com/zh-cn/previous-versions/windows/desktop/htmlhelp/microsoft-html-help-downloads)）：

```powershell
& "C:\Program Files (x86)\HTML Help Workshop\hhc.exe" build\chm\help.hhp
# 输出 D:\projects\sla\sahelp\SA_SLDA_Help.chm
```

## 编写新主题

1. 复制 `_template/topic_template.html` 到对应 `content/<章节>/` 下；
2. 必须保持 `<link rel="stylesheet" href="../../assets/help.css">`（所有主题固定两层深）；
3. 在同目录 `_manifest.json` 的 `topics` 中登记：

```json
{
  "id": "syntax",                 // 章节内唯一
  "title": "语法基础",
  "file": "syntax.html",          // 同目录文件名
  "keywords": ["语法", "lexer"],   // 出现在索引页签中
  "parent": null                  // 或另一个 topic 的 id，形成二级树
}
```

## 版权声明

Copyright © 2026 layola13. 保留所有权利。

本文档基于 SA / SLA 工具链的真实源码与仓库文档编写，内容中的第三方事实素材
（命令、契约签名、性能数据等）版权归各自上游项目所有。转载请注明出处。
