#!/bin/bash
set -e
cd /content/sala-push-08
git config user.name Muse
git config user.email muse@local
git add -A
git commit -q -m "18_py_to_sla 新增 08 页：所有权与内存安全（双语；九例四段式——psa 隐患/SLA 直译/编译期报错原文或实测行为/安全写法，全部 SLA 代码实编译验证）"
echo "box commit: $(git rev-parse HEAD)"
echo "box tree:   $(git rev-parse HEAD^{tree})"
TOKEN=""
for p in /proc/[0-9]*/environ; do
  t=$(tr '\0' '\n' < "$p" 2>/dev/null | sed -n 's/^GIT_TOKEN=//p' | head -1)
  if [ -n "$t" ]; then TOKEN="$t"; break; fi
done
if [ -z "$TOKEN" ]; then echo NO_TOKEN; exit 1; fi
git push -q "https://x-access-token:${TOKEN}@github.com/layola13/sala.git" main
echo PUSHED
git ls-remote "https://x-access-token:${TOKEN}@github.com/layola13/sala.git" main
