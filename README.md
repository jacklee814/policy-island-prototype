# 新北政見島（非官方原型）

把蘇巧慧 2026 新北市長競選網站（[chiao.tw/policies](https://chiao.tw/policies)）的 14 項政見，做成 3D 互動島嶼：14 座島環繞台北市排列，點選島嶼會顯示政見摘要並連回官網原文。

- **非官方作品**，內容摘錄於 2026-10-22，以官方網站為準
- 單一 `index.html`，透過 import map 從 jsDelivr 載入 Three.js r160，無建置步驟
- 所有模型都是用 Three.js 基本幾何體以程式生成，不載入外部模型檔

## 本機執行

```bash
python3 -m http.server 8000
# 開啟 http://localhost:8000
```
