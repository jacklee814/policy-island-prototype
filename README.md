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

## 由政見資料產生的靜態檔

修改 `index.html` 裡的 `POLICIES` 或 `SPOTS` 後，要重新產生：

```bash
python3 tools/build_static.py
```

會更新這些檔案：

- `policy/`、`spot/`、`about/`：給搜尋引擎與一般閱讀的文字頁。3D 網站把所有內容放在同一個網址的 `#` 後面，搜尋引擎只會當成一頁，所以每項政見與景點另有自己的頁面。共用樣式在 `pages.css`。
- `share/*.html`：每項政見與景點的分享預覽頁。社群平台抓預覽時看不到網址 `#` 後面的部分，所以每項都有自己的頁面帶標題與摘要，打開後跳回主頁面（保留 `utm_*` 參數供 GA4 判斷來源）。
- `index.html` 裡 `seo:jsonld` 與 `seo:noscript` 標記之間的內容：給搜尋引擎讀的結構化資料與文字版政見。
- `sitemap.xml`

`og.png` 是首頁與總覽頁共用的 1200×630 預覽圖（全景截圖）。每項政見與景點的預覽卡片在 `og/`，由網站自己畫（`index.html?og=policy-12`）再截圖，需要 agent-browser。內容或外觀改了之後：

```bash
python3 tools/build_og_images.py && python3 tools/build_static.py
```

## 流量統計

使用 Google Analytics 4（`G-5H13CQWF3X`）。除了頁面瀏覽，還記錄 `view_policy`、`view_spot`、`share`、`search`、`filter_category`、`open_index` 事件。
