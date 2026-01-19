# eBay商品ページ セレクター

eBay商品詳細ページ（`https://www.ebay.com/itm/{itemNumber}`）の情報抽出用セレクター。

## ページ状態判定

```javascript
// mcp__claude-in-chrome__javascript_tool で実行
JSON.stringify({
  title: document.querySelector('h1.x-item-title__mainTitle')?.textContent?.trim() || null,
  image: document.querySelector('.ux-image-carousel-item img')?.src || null,
  isEnded: document.body.innerText.includes('This listing has ended'),
  isError: document.title.includes('Error Page') || !document.querySelector('h1.x-item-title__mainTitle')
})
```

## セレクター一覧

| 要素 | セレクター |
|------|-----------|
| タイトル | `h1.x-item-title__mainTitle` |
| 画像 | `.ux-image-carousel-item img` |

## 判定結果による分岐

| 状態 | 判定条件 | 対応 |
|------|----------|------|
| **正常** | `title` あり、`isError: false` | 検索ステップへ進む |
| **ENDED** | `isEnded: true` | 仕入れ先は探す（検索ステップへ） |
| **エラー/404** | `isError: true` or `title: null` | W列に「ページなし」記載してスキップ |

---

## 商品画像の保存

仕入れ先との同一商品照合用に画像を保存する。

### 保存先

`images/Target-Product/{itemNumber}.jpg`

### 画像URL取得

```javascript
// mcp__claude-in-chrome__javascript_tool で実行
document.querySelector('.ux-image-carousel-item img')?.src
```

### ダウンロード方法

```bash
curl -o "images/Target-Product/{itemNumber}.jpg" "{画像URL}"
```

### 処理完了後の削除

```bash
rm -f images/Target-Product/*.jpg
```
