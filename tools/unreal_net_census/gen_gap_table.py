#!/usr/bin/env python3
"""Render the UE x sa_std gap classification into summary.json + HTML rows,
and inject them into the census page template (@@SUMMARY@@ / @@GAPROWS@@).
Usage: gen_gap_table.py <ue_gap_items.tsv> <page_template.html> <page_out.html> <summary.json>
"""
import csv, sys, json, html, collections

TSV, TPL, OUT, SUM = sys.argv[1:5]
rows = list(csv.DictReader(open(TSV, encoding="utf-8"), delimiter="\t"))
CLASSES = ["已有等价", "可直接对应", "需建模", "模型不合", "不可核"]
SUBSYS = [("sockets", "Sockets 子系统（低层传输）"), ("netdriver", "NetDriver 体系"),
          ("packet_handler", "PacketHandler"), ("replication", "复制（Replication）"),
          ("iris", "Iris"), ("serialization", "序列化"), ("online", "OnlineSubsystem")]

per = collections.defaultdict(collections.Counter)
for r in rows:
    per[r["subsystem"]][r["classification"]] += 1
    per[r["subsystem"]]["总计"] += 1
tot = collections.Counter()
for r in rows:
    tot[r["classification"]] += 1
    tot["总计"] += 1
summary = {"per_subsystem": {k: dict(v) for k, v in per.items()},
           "total": dict(tot),
           "denominator_excl_unverifiable": tot["总计"] - tot.get("不可核", 0)}
json.dump(summary, open(SUM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False))

def esc(s):
    return html.escape(s, quote=False)

sum_html = []
sum_html.append("<table>\n<tr><th>子系统</th><th>条目</th><th>已有等价</th><th>可直接对应</th><th>需建模</th><th>模型不合</th><th>不可核</th></tr>")
for key, label in SUBSYS:
    c = per[key]
    sum_html.append(f"<tr><td>{label}</td><td>{c['总计']}</td><td>{c['已有等价']}</td>"
                    f"<td>{c['可直接对应']}</td><td>{c['需建模']}</td><td>{c['模型不合']}</td><td>{c['不可核']}</td></tr>")
sum_html.append(f"<tr><td><b>合计</b></td><td><b>{tot['总计']}</b></td><td><b>{tot['已有等价']}</b></td>"
                f"<td><b>{tot['可直接对应']}</b></td><td><b>{tot['需建模']}</b></td><td><b>{tot['模型不合']}</b></td>"
                f"<td><b>{tot.get('不可核', 0)}</b></td></tr>\n</table>")

gap_html = []
for key, label in SUBSYS:
    gap_html.append(f"<h3>{label}</h3>")
    gap_html.append("<table>\n<tr><th>条目</th><th>UE 侧证据</th><th>sa_std 现状</th><th>分类</th></tr>")
    for r in rows:
        if r["subsystem"] != key:
            continue
        note = f"<br><span>注：{esc(r['note'])}</span>" if r["note"] else ""
        gap_html.append(f"<tr><td>{esc(r['item'])}</td><td>{esc(r['ue_evidence'])}</td>"
                        f"<td>{esc(r['sa_counterpart'])}{note}</td><td>{esc(r['classification'])}</td></tr>")
    gap_html.append("</table>")

page = open(TPL, encoding="utf-8").read()
page = page.replace("@@SUMMARY@@", "\n".join(sum_html))
page = page.replace("@@GAPROWS@@", "\n".join(gap_html))
assert "@@" not in page, "unreplaced placeholder"
open(OUT, "w", encoding="utf-8").write(page)
print("page written:", OUT)
