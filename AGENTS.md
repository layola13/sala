在 Windows PowerShell 环境中处理包含中文的文件时，必须显式使用 UTF-8 编码。

读取文本文件优先使用：Get-Content -Encoding UTF8
写入文本文件优先使用 apply_patch；如必须用 PowerShell 写文件，使用 Set-Content -Encoding UTF8 或 Add-Content -Encoding UTF8
不要用未指定编码的 Get-Content / Set-Content / Out-File 处理中文、Markdown、TOML、JSON 等文本文件
终端输出出现乱码时，先用 UTF-8 重新读取确认，不要直接认定文件内容损坏

分支说明：本仓库（文档集合，非代码）以 main 分支为主分支。
所有文档工作直接在 main 上进行，不要新建 0.17 / sa-c 这类代码仓分支；
如本地残留 0.17 分支，完成合并后即删除，保持远端只有 main。
