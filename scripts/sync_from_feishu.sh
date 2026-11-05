#!/usr/bin/env bash
# 从飞书抓取文档 Markdown，并重建 docx。
# 用法：bash scripts/sync_from_feishu.sh [文档URL]
set -euo pipefail

DOC_URL="${1:-https://synxlab.feishu.cn/docx/P3QVdWYcOo14KZxEjSdcMhRfndf}"
cd "$(dirname "$0")/.."
TMP_JSON=".leftrace.json"
trap 'rm -f "$TMP_JSON"' EXIT

echo "[1/3] 从飞书抓取 Markdown ..."
lark-cli docs +fetch --doc "$DOC_URL" --scope full --doc-format markdown --json > "$TMP_JSON"

echo "[2/3] 写入 docs/source.md ..."
python - "$TMP_JSON" <<'PY'
import io, json, sys
d = json.load(io.open(sys.argv[1], encoding="utf-8"))
md = d["data"]["document"]["content"]
io.open("docs/source.md", "w", encoding="utf-8").write(md)
print(f"    {len(md)} 字符")
PY

echo "[3/3] 生成 docx ..."
python scripts/build_docx.py \
  --md docs/source.md \
  --out "docs/软件定义网络-课程项目留痕.docx" \
  --source-url "$DOC_URL"

echo "完成。记得 git add -A && git commit -m \"docs: 同步 $(date +%F)\""
