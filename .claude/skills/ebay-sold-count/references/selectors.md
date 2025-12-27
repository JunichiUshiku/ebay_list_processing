# eBay Product Research セレクター

## 🚀 URL直接ナビゲート（並列処理用）

### URL生成テンプレート

```javascript
// タイムスタンプ計算（ミリ秒）- 必ずDate.now()で現在時刻を取得すること
const endDate = Date.now();  // 例: 1766771545620 (2025年12月27日)
const startDate90 = endDate - (90 * 24 * 60 * 60 * 1000);   // 90日前
const startDate180 = endDate - (180 * 24 * 60 * 60 * 1000); // 180日前

// 90日間検索URL（startDate/endDate必須）
const url90 = `https://www.ebay.com/sh/research?marketplace=EBAY-US&keywords=${encodeURIComponent(keyword)}&dayRange=90&endDate=${endDate}&startDate=${startDate90}&categoryId=0&offset=0&limit=50&tabName=SOLD&tz=Asia%2FTokyo`;

// 6ヶ月間検索URL（startDate/endDate必須）
const url180 = `https://www.ebay.com/sh/research?marketplace=EBAY-US&keywords=${encodeURIComponent(keyword)}&dayRange=180&endDate=${endDate}&startDate=${startDate180}&categoryId=0&offset=0&limit=50&tabName=SOLD&tz=Asia%2FTokyo`;
```

**⚠️ 重要**:
- `endDate`は必ず`Date.now()`で現在時刻を動的に取得すること
- ハードコードされたタイムスタンプは使用禁止（過去のデータを参照してしまう）
- `startDate`と`endDate`パラメータがないと期間計算が不正確になる

**使用方法**:
- `keyword` を検索キーワードに置換
- `encodeURIComponent` でURLエンコード済み
- このURLに直接ナビゲートすることでUI操作を省略

---

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

---

## 🔄 ページロード完了検出

### 検索結果テーブル出現待機

```javascript
// 検索結果テーブルの出現を待機（最大10秒）
const waitForResults = async () => {
  for (let i = 0; i < 20; i++) {
    const table = document.querySelector('.research-table-row__totalSoldCount');
    if (table) return true;
    await new Promise(r => setTimeout(r, 500));
  }
  return false;
};
await waitForResults();
```

### 簡易ロード確認（1行版）

```
!!document.querySelector('.research-table-row__totalSoldCount') || !!document.querySelector('.research-table__no-results')
```
※ 戻り値: true（検索結果あり or 結果なし表示あり）= ロード完了

---

## 🚨 エラー検出

### CAPTCHA検出

```
!!document.querySelector('iframe[title*="reCAPTCHA"]') || !!document.querySelector('.g-recaptcha') || document.body.innerText.includes('確認が必要です')
```
※ 戻り値: true = CAPTCHA出現（処理中断が必要）

### ログイン切れ検出

```
window.location.href.includes('/signin') || document.body.innerText.includes('Sign in')
```
※ 戻り値: true = ログイン画面にリダイレクト（処理中断が必要）

### 検索結果なし検出

```
!!document.querySelector('.research-table__no-results')
```
※ 戻り値: true = 検索結果0件（Total Sold = 0として記録）
