# メルカリ売り切れ判定仕様書

**バージョン**: 1.0.0
**作成日**: 2026-01-16
**関連**: mercari-collector-spec.md

---

## 1. 概要

メルカリ検索結果ページにおける商品の販売状態（販売中/売り切れ）を判定するための技術仕様。

---

## 2. 判定方法

### 2.1 推奨: `data-testid="thumbnail-sticker"` による判定

| 商品状態 | `thumbnail-sticker` 要素 | 判定コード |
|----------|-------------------------|-----------|
| **販売中** | 存在しない | `element === null` |
| **売り切れ** | 存在する | `element !== null` |

### 2.2 JavaScript判定コード

```javascript
// 単一要素の判定
const isSoldOut = (linkElement) => {
  return linkElement.querySelector('[data-testid="thumbnail-sticker"]') !== null;
};

// 販売中商品のみ抽出
const getAvailableItems = (maxItems = 10) => {
  return Array.from(document.querySelectorAll('a[href*="/item/"], a[href*="/shops/product/"]'))
    .filter(a => !a.querySelector('[data-testid="thumbnail-sticker"]'))
    .map(a => ({
      href: a.href,
      id: a.getAttribute('href').split('/').pop(),
      title: a.querySelector('[data-testid="thumbnail-item-name"]')?.textContent?.trim() || '',
      price: a.textContent.match(/¥[\d,]+/)?.[0] || ''
    }))
    .slice(0, maxItems);
};
```

---

## 3. DOM構造

### 3.1 販売中商品

```html
<a href="/item/m60508459861" class="sc-bcd1c877-1 lpjZwE">
  <div class="merItemThumbnail" role="img" aria-label="商品名の画像 8,500円">
    <figure class="itemThumbnail">
      <!-- thumbnail-sticker なし -->
      <div data-testid="thumbnail-item-name">商品名</div>
    </figure>
  </div>
</a>
```

**特徴**:
- `data-testid` に `thumbnail-item-name` のみ存在
- `thumbnail-sticker` 要素なし

### 3.2 売り切れ商品

```html
<a href="/item/m80539415607" class="sc-bcd1c877-1 lpjZwE">
  <div class="merItemThumbnail" role="img" aria-label="商品名の画像 売り切れ 30,000円">
    <figure class="itemThumbnail">
      <div data-testid="thumbnail-sticker">売り切れ</div>  <!-- ← これが存在 -->
      <div data-testid="thumbnail-item-name">商品名</div>
    </figure>
  </div>
</a>
```

**特徴**:
- `data-testid="thumbnail-sticker"` が存在
- `aria-label` にも「売り切れ」テキストあり

---

## 4. 非推奨: テキストベース判定

### 4.1 なぜ非推奨か

```javascript
// ❌ 非推奨
a.textContent.includes('売り切れ')
```

| 問題 | 例 |
|------|-----|
| 誤判定（偽陽性） | 商品名に「売り切れ間近」「売り切れ必至」等を含む場合 |
| 言語依存 | 多言語対応時に「SOLD」「已售出」等の対応が必要 |
| DOM変更に弱い | テキスト位置の変更で判定ロジック破綻 |

### 4.2 data-testidの利点

| メリット | 説明 |
|----------|------|
| 構造ベース | 要素の有無で判定、テキスト内容に依存しない |
| 安定性 | テスト用属性のため変更されにくい |
| 誤判定なし | 商品名の内容に影響されない |

---

## 5. 関連セレクター一覧

| 用途 | セレクター |
|------|-----------|
| 商品リンク（通常） | `a[href*="/item/"]` |
| 商品リンク（Shops） | `a[href*="/shops/product/"]` |
| 売り切れバッジ | `[data-testid="thumbnail-sticker"]` |
| 商品名 | `[data-testid="thumbnail-item-name"]` |
| サムネイル画像 | `.imageContainer__f8ddf3a2 img` |

---

## 6. agent-browserでの使用例

```bash
# 検索結果ページで販売中商品を抽出
agent-browser --session mercari eval "
  JSON.stringify(
    Array.from(document.querySelectorAll('a[href*=\"/item/\"]'))
      .filter(a => !a.querySelector('[data-testid=\"thumbnail-sticker\"]'))
      .slice(0, 10)
      .map(a => ({
        id: a.href.split('/').pop(),
        title: a.querySelector('[data-testid=\"thumbnail-item-name\"]')?.textContent?.trim()
      }))
  )
"
```

---

## 7. 検証情報

| 項目 | 値 |
|------|-----|
| 調査日 | 2026-01-16 |
| 対象サイト | https://jp.mercari.com/ |
| 検証キーワード | Alpine PXA-H510 |
| 確認商品数 | 7件（販売中1件、売り切れ6件） |

---

## 8. 注意事項

1. **DOM構造は変更される可能性あり**: メルカリのUI更新により`data-testid`が変更される場合がある
2. **定期的な検証推奨**: 月1回程度の動作確認を推奨
3. **フォールバック**: `data-testid`が見つからない場合は`aria-label`のテキスト判定を代替として使用可能

---

## 9. 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|----------|
| 1.0.0 | 2026-01-16 | 初版作成 |
