# 政策島原型（Policy Island Prototype）

用 Three.js 做的 3D 政策島互動原型：14 座六角形島嶼，每座島代表一項政策主題，點選後相機會飛過去並顯示資訊卡。

- 單一 `index.html`，透過 import map 從 jsDelivr 載入 Three.js r160，無建置步驟
- 所有模型都是用 Three.js 基本幾何體以程式生成，不載入外部模型檔
- **內容皆為假資料**，不代表任何真實政見

## 本機執行

```bash
python3 -m http.server 8000
# 開啟 http://localhost:8000
```
