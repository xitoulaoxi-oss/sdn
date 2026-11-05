#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把飞书导出的 Markdown 转成便于提交/答辩的 .docx。

用法：
    python scripts/build_docx.py                     # 默认读 docs/export/leftrace.md
    python scripts/build_docx.py --md a.md --out b.docx

设计取舍（答辩可讲）：
- Markdown 是唯一事实源，docx 是派生产物，随时可重建，避免二进制进 git 冲突；
- 只实现课程文档用得到的子集：标题 / 段落 / 加粗 / 行内代码 / 代码块 / 表格 / 列表 / 引用；
- 不追求 100% 还原飞书样式，追求「打印出来能交、内容不丢」。
"""

import argparse
import datetime as dt
import io
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

BODY_CN = "微软雅黑"
BODY_EN = "Calibri"
CODE_FONT = "Consolas"


def set_run_font(run, name=BODY_EN, size=None, bold=None, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), BODY_CN)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor(*color)


def shade(paragraph_or_cell, hex_fill):
    el = paragraph_or_cell._p if hasattr(paragraph_or_cell, "_p") else paragraph_or_cell._tc
    pr = el.get_or_add_pPr() if hasattr(el, "get_or_add_pPr") else el.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    pr.append(shd)


INLINE_RE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


def add_inline(paragraph, text, size=10.5, base_bold=False):
    """把 **粗体**、`代码`、[文字](链接) 拆成 run 写进去。"""
    text = (
        text.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            r = paragraph.add_run(part[2:-2])
            set_run_font(r, size=size, bold=True)
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            r = paragraph.add_run(part[1:-1])
            set_run_font(r, name=CODE_FONT, size=size - 0.5)
            r.font.color.rgb = RGBColor(0xC7, 0x25, 0x4E)
        elif part.startswith("[") and "](" in part:
            label, url = part[1:-1].split("](", 1)
            r = paragraph.add_run(label)
            set_run_font(r, size=size, bold=base_bold)
            r.font.color.rgb = RGBColor(0x1A, 0x5F, 0xB4)
            if url and url != label:
                r2 = paragraph.add_run(f"（{url}）")
                set_run_font(r2, size=size - 1)
                r2.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
        else:
            r = paragraph.add_run(part)
            set_run_font(r, size=size, bold=base_bold)


def add_code_block(doc, lines):
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Pt(6)
        shade(p, "F4F6F8")
        r = p.add_run(line if line else " ")
        set_run_font(r, name=CODE_FONT, size=9)


def add_table(doc, rows):
    if not rows:
        return
    header, body = rows[0], rows[1:]
    cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j in range(cols):
            cell = table.cell(i, j)
            cell.text = ""
            p = cell.paragraphs[0]
            txt = row[j] if j < len(row) else ""
            add_inline(p, txt, size=9)
            if i == 0:
                for r in p.runs:
                    r.bold = True
                shade(cell, "DDE7F5")
    doc.add_paragraph()
    # 跨页时重复表头，长表格翻页不迷路
    tr = table.rows[0]._tr
    trPr = tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trPr.append(th)
    # 单行不跨页拆断（否则会出现半行 + 半个字）
    for row in table.rows:
        rp = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        rp.append(cs)


def looks_like_separator(row):
    cells = [c.strip() for c in row if c.strip()]
    return bool(cells) and all(re.fullmatch(r":?-+:?", c) for c in cells)


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def convert(md_path, out_path, source_url=""):
    raw = io.open(md_path, encoding="utf-8").read()
    lines = raw.splitlines()

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = BODY_EN
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_CN)

    title = None
    m = re.search(r"<title>(.*?)</title>", raw)
    if m:
        title = m.group(1).strip()

    if title:
        h = doc.add_heading(title, level=0)
        for r in h.runs:
            set_run_font(r, size=22, bold=True)
        meta = doc.add_paragraph()
        meta.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = meta.add_run(
            f"导出时间：{dt.datetime.now():%Y-%m-%d %H:%M}"
            + (f"　｜　来源：{source_url}" if source_url else "")
        )
        set_run_font(r, size=9)
        r.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

    in_code = False
    code_lang = ""
    code_buf = []
    table_buf = []
    skip_title_line = title is not None

    def flush_table():
        nonlocal table_buf
        rows = [split_row(l) for l in table_buf if not looks_like_separator(split_row(l))]
        if rows:
            add_table(doc, rows)
        table_buf = []

    for idx, line in enumerate(lines):
        if skip_title_line and idx == 0 and line.strip().startswith("<title>"):
            continue
        if line.strip().startswith("```"):
            if in_code:
                if code_lang == "mermaid":
                    cap = doc.add_paragraph()
                    r = cap.add_run("〔Mermaid 图源｜飞书版为可交互画板，此处保留源码〕")
                    set_run_font(r, size=8.5)
                    r.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
                add_code_block(doc, code_buf)
                code_buf = []
                in_code = False
            else:
                if table_buf:
                    flush_table()
                in_code = True
                code_lang = line.strip()[3:].strip().lower()
            continue
        if in_code:
            code_buf.append(line)
            continue

        if line.strip().startswith("|"):
            table_buf.append(line)
            continue
        elif table_buf:
            flush_table()

        s = line.rstrip()
        if not s.strip():
            continue
        if re.fullmatch(r"-{3,}", s.strip()):
            continue

        hm = re.match(r"^(#{1,6})\s+(.*)$", s)
        if hm:
            # 本文档只有两层语义：一级章节与二级小节；## 与 ### 都归为二级
            depth = len(hm.group(1))
            level = 1 if depth == 1 else 2
            h = doc.add_heading("", level=level)
            add_inline(h, hm.group(2), size={1: 16, 2: 14, 3: 12, 4: 11}[level], base_bold=True)
            for r in h.runs:
                r.bold = True
            continue

        if s.startswith(">"):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(18)
            add_inline(p, s.lstrip("> ").strip(), size=9.5)
            for r in p.runs:
                r.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
            continue

        lm = re.match(r"^\s*[-*+]\s+(.*)$", s)
        if lm:
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(3)
            add_inline(p, lm.group(1))
            continue
        nm = re.match(r"^\s*(\d+)[.)]\s+(.*)$", s)
        if nm:
            # 不用 Word 自动编号（会跨列表连续计数），直接写死序号
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.left_indent = Pt(21)
            p.paragraph_format.first_line_indent = Pt(-15)
            num = p.add_run(f"{nm.group(1)}. ")
            set_run_font(num, size=10.5, bold=True)
            add_inline(p, nm.group(2))
            continue

        p = doc.add_paragraph()
        add_inline(p, s.strip())

    if in_code and code_buf:
        add_code_block(doc, code_buf)
    if table_buf:
        flush_table()

    doc.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="docs/export/leftrace.md")
    ap.add_argument("--out", default="docs/export/软件定义网络-课程项目留痕.docx")
    ap.add_argument("--source-url", default="")
    args = ap.parse_args()
    path = convert(args.md, args.out, args.source_url)
    print(f"OK: {path}")


if __name__ == "__main__":
    main()
