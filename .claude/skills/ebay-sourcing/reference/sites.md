# 国内検索サイト一覧（11サイト）

`##SEARCH##` をキーワードに置換して使用。

## 検索URL

| サイト | 検索URL |
|--------|---------|
| Amazon | `https://www.amazon.co.jp/s?k=##SEARCH##` |
| メルカリ | `https://www.mercari.com/jp/search/?keyword=##SEARCH##` |
| フリル | `https://fril.jp/search/##SEARCH##` |
| PayPayフリマ | `https://paypayfleamarket.yahoo.co.jp/search/##SEARCH##?page=1` |
| ヤフオク | `https://auctions.yahoo.co.jp/search/search?va=##SEARCH##` |
| 駿河屋 | `https://www.suruga-ya.jp/search?category=&search_word=##SEARCH##` |
| ハードオフ | `https://netmall.hardoff.co.jp/search/?q=##SEARCH##` |
| ツールオフ | `https://tooloff-ec.com/search/?keyword=##SEARCH##` |
| モノタロウ | `https://www.monotaro.com/s/?c=&q=##SEARCH##` |
| じゃんぱら | `https://www.janpara.co.jp/sale/search/result/?KEYWORDS=##SEARCH##` |
| ジモティー | `https://jmty.jp/all/sale?button=&keyword=##SEARCH##` |

---

## javascript_tool 情報抽出ガイド

`read_page`の代わりに`javascript_tool`で必要情報のみ抽出。

### 0件判定（共通）

```javascript
// 0件の場合true
document.body.innerText.includes('0件') ||
document.body.innerText.includes('見つかりません') ||
document.body.innerText.includes('該当する商品がありません')
```

### 件数取得（汎用）

```javascript
document.body.innerText.match(/(\d+)件/)?.[1] || '0'
```

---

## サイト別セレクター

### Amazon

```javascript
JSON.stringify({
  count: document.querySelector('[data-component-type="s-result-info-bar"]')?.textContent?.match(/\d+/g)?.[0] || '0',
  items: [...document.querySelectorAll('[data-component-type="s-search-result"]')].slice(0,10).map(el => ({
    title: el.querySelector('h2')?.textContent?.trim(),
    price: el.querySelector('.a-price-whole')?.textContent?.trim()
  }))
})
```

### メルカリ

```javascript
JSON.stringify({
  count: document.querySelectorAll('[data-testid="item-cell"]').length,
  items: [...document.querySelectorAll('[data-testid="item-cell"]')].slice(0,10).map(el => ({
    title: el.querySelector('[data-testid="thumbnail-item-name"]')?.textContent?.trim(),
    price: el.querySelector('[data-testid="thumbnail-item-price"]')?.textContent?.trim()
  }))
})
```

### ヤフオク

```javascript
JSON.stringify({
  count: document.querySelector('.Result__count')?.textContent?.match(/\d+/)?.[0] || '0',
  items: [...document.querySelectorAll('.Product')].slice(0,10).map(el => ({
    title: el.querySelector('.Product__title')?.textContent?.trim(),
    price: el.querySelector('.Product__priceValue')?.textContent?.trim()
  }))
})
```

### その他サイト

基本的な抽出パターン:
```javascript
// タイトルと価格を含む商品カードを探す
JSON.stringify({
  count: document.querySelectorAll('.product-card, .item, .search-result').length,
  items: [...document.querySelectorAll('.product-card, .item, .search-result')].slice(0,10).map(el => ({
    title: el.querySelector('h2, h3, .title, .name')?.textContent?.trim(),
    price: el.querySelector('.price, .cost')?.textContent?.trim()
  }))
})
```
