# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述（Project Overview）

**專案名稱：notetrans**

HackMD to Obsidian Markdown 批量匯出工具。透過 HackMD API 抓取筆記，轉換 HackMD 特有語法為 Obsidian 相容格式，並產生含 YAML frontmatter 的 .md 檔案。支援 PARA + Zettelkasten 自動分類與 LLM 知識提取。

---

## 技術架構（Tech Stack）

- **語言**: Python 3.11+
- **套件管理**: uv
- **CLI 框架**: Click
- **HTTP**: requests
- **YAML**: PyYAML
- **環境變數**: python-dotenv
- **測試**: pytest + responses (mock HTTP)

---

## 目錄結構（Directory Structure）

```
.
├── pyproject.toml
├── notetrans/
│   ├── __init__.py
│   ├── __main__.py          # python -m notetrans
│   ├── cli.py               # Click CLI (export, list, organize, extract)
│   ├── client.py            # HackMD API v1 client
│   ├── converter.py         # HackMD -> Obsidian 語法轉換
│   ├── exporter.py          # 整合：抓取 + 轉換 + 寫檔
│   ├── organizer.py         # PARA 自動分類引擎
│   ├── extractor.py         # LLM Zettel 知識提取
│   └── models.py            # dataclass (Note, Team)
└── tests/
    ├── test_converter.py
    ├── test_client.py
    ├── test_exporter.py
    ├── test_organizer.py
    └── test_extractor.py
```

## 常用指令

- `uv run notetrans list --token $HACKMD_TOKEN` - 列出所有筆記
- `uv run notetrans export --token $HACKMD_TOKEN -o ./vault` - 匯出筆記
- `uv run notetrans organize --vault-dir ./vault [--dry-run]` - PARA 自動分類
- `uv run notetrans extract --vault-dir ./vault [--dry-run]` - LLM Zettel 提取
- `uv run pytest -v` - 執行測試

---

## 標準開發流程（Standard Development Workflow）

1. 先閱讀 `CLAUDE.md` 和 `README.md`
2. 根據任務需求探索相關程式碼
3. 大範圍修改前先說明計劃
4. 執行測試驗證修改 (`uv run pytest`)
5. 撰寫 commit message 並提交

**注意事項：**
- 不要使用 emoji
- 建立新檔案前先詢問使用者

---

最後更新：2026-03-09
