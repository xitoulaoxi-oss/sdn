# 软件定义网络 · 课程项目（三层 SDN 管理系统）

本仓库是《软件定义网络》课程项目的交付载体：**源码 + 过程文档快照**。
文档的事实源永远在飞书，这里只存可提交、可复现的派生版本。

## 目录

| 路径 | 说明 |
|---|---|
| `docs/source.md` | 飞书文档导出的 Markdown 快照（唯一事实源的镜像） |
| `docs/软件定义网络-课程项目留痕.docx` | 由 `source.md` 生成，用于提交 / 答辩 / 打印 |
| `scripts/build_docx.py` | Markdown → docx 转换器（标题 / 表格 / 代码块 / 列表 / 引用） |
| `scripts/sync_from_feishu.sh` | 从飞书重新抓取 Markdown 并重建 docx |

## 约定

1. **只在飞书改文档**，不要手改 `docs/source.md` 和 `.docx`——下次同步会被覆盖。
2. 每次同步 = 一次 commit，提交信息写清日期与阶段，例如 `docs: 同步 2026-11-06 L1 流表实验`。
3. `.docx` 是二进制，冲突无法合并；所以**只允许脚本生成**，不允许两人各改一版再合并。

## 重建

前置条件：

- `lark-cli` 已登录且具备 `docx:document`、`docx:document:create`、`docx:document:readonly` 权限；
- Python 3.9+，安装 `python-docx`。

```bash
pip install python-docx

# 从飞书抓取 + 重建 docx（推荐）
bash scripts/sync_from_feishu.sh

# 只重建本地 docx，不联网
python scripts/build_docx.py \
  --md docs/source.md \
  --out "docs/软件定义网络-课程项目留痕.docx"
```

## 当前进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| P0 | 环境基座（WSL2 + Mininet + OVS） | ✅ 可用 |
| P1 | 数据平面手操（流表 / 端口 / 抓包） | 🟡 进行中 |
| P2 | ONOS 接入与拓扑发现 | ⬜ 未开始 |
| P3 | 应用平面（Sanic + Vue 骨架） | ⬜ 未开始 |
| P4 | L1 单对单最优路径闭环 | ⬜ 未开始 |
| P5–P7 | 多流 / 组播 / 态势感知 | ⬜ 未开始 |

详细大纲见文档「二、教学大纲」，任务拆解见「三、任务拆解」。
