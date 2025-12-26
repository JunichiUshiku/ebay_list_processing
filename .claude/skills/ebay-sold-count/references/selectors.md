# eBay Product Research セレクター

## 固定セレクター一覧

| 要素 | セレクター |
|------|-----------|
| キーワード入力 | `input.textbox__control` |
| 期間プルダウン | `button.menu-button__button` |
| Researchボタン | `button.search-input-panel__research-button` |
| メニューアイテム | `.menu-button__item` |
| Total Soldセル | `.research-table-row__totalSoldCount` |

---

## JavaScript コードスニペット

**重要**: javascript_toolで実行する際は、1行に結合するか、セミコロンで区切ること。

### キーワード入力

```
const input = document.querySelector('input.textbox__control'); input.value = 'KEYWORD'; input.dispatchEvent(new Event('input', { bubbles: true }));
```
※ `KEYWORD` を実際のキーワードに置換

### 期間プルダウン展開

```
const buttons = document.querySelectorAll('button.menu-button__button'); const periodBtn = Array.from(buttons).find(btn => btn.textContent.includes('days') || btn.textContent.includes('months') || btn.textContent.includes('year')); if (periodBtn) periodBtn.click();
```
※ 複数ボタンがあるためテキストでフィルタリング必須

### 期間選択（90日間）

```
const items = document.querySelectorAll('.menu-button__item'); const target = Array.from(items).find(el => el.textContent.trim() === 'Last 90 days'); if (target) target.click();
```

### 期間選択（6ヶ月間）

```
const items = document.querySelectorAll('.menu-button__item'); const target = Array.from(items).find(el => el.textContent.trim() === 'Last 6 months'); if (target) target.click();
```

### Researchボタンクリック

```
document.querySelector('button.search-input-panel__research-button').click();
```

### Total Sold合計取得

```
const cells = document.querySelectorAll('.research-table-row__totalSoldCount'); Array.from(cells).reduce((sum, cell) => sum + (parseInt(cell.innerText) || 0), 0);
```
※ 戻り値: Total Sold の合計数値

### 現在の検索結果URL取得

```
window.location.href
```
※ 戻り値: 検索結果ページのURL（スプレッドシートへのリンク挿入に使用）
