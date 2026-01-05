# eBay Product Research セレクター

## 目次

1. [タイムスタンプ取得](#タイムスタンプ取得)
2. [URL構築テンプレート](#url構築テンプレート)
3. [結果取得](#結果取得)
4. [ページロード検出](#ページロード検出)
5. [エラー検出](#エラー検出)

---

## タイムスタンプ取得

**重要**: URL生成関数の戻り値はMCPセキュリティでブロックされるため、タイムスタンプのみ取得しClaude側でURLを構築すること。

### 90日間用タイムスタンプ

```javascript
(function() {
  const now = Date.now();
  const start = now - (90 * 24 * 60 * 60 * 1000);
  return JSON.stringify({now: now, start: start});
})()
```

### 6ヶ月間用タイムスタンプ

```javascript
(function() {
  const now = Date.now();
  const start = now - (180 * 24 * 60 * 60 * 1000);
  return JSON.stringify({now: now, start: start});
})()
```

**注意**:
- 新規タブは `chrome://newtab/` 状態でJS実行不可 → 先にeBayへナビゲートすること
- 戻り値は `{"now":1234567890123,"start":1234567890123}` 形式

---

## URL構築テンプレート

タイムスタンプ取得後、Claude側で以下のURLを構築:

### 90日間URL

```
https://www.ebay.com/sh/research?marketplace=EBAY-US&keywords={キーワード（URLエンコード）}&dayRange=90&startDate={start}&endDate={now}&categoryId=0&sellerCountry=SellerLocation%3A%3A%3AJP&offset=0&limit=50&tabName=SOLD&tz=Asia%2FTokyo
```

### 6ヶ月間URL

```
https://www.ebay.com/sh/research?marketplace=EBAY-US&keywords={キーワード（URLエンコード）}&dayRange=180&startDate={start}&endDate={now}&categoryId=0&sellerCountry=SellerLocation%3A%3A%3AJP&offset=0&limit=50&tabName=SOLD&tz=Asia%2FTokyo
```

**重要**: 構築したURLを保持（HYPERLINK作成用に再利用）

---

## 結果取得

### Total Sold合計取得

```javascript
const cells = document.querySelectorAll('.research-table-row__totalSoldCount');
Array.from(cells).reduce((sum, cell) => sum + (parseInt(cell.innerText) || 0), 0);
```

戻り値: Total Sold の合計数値

### HYPERLINK作成

```
=HYPERLINK("{保持したURL}", "{販売数}")
```

**注意**: `window.location.href` はMCPセキュリティでブロックされるため使用不可

---

## ページロード検出

### 簡易ロード確認

```javascript
!!document.querySelector('.research-table-row__totalSoldCount') ||
!!document.querySelector('.research-table__no-results')
```

戻り値: `true` = ロード完了

---

## エラー検出

### CAPTCHA検出

```javascript
!!document.querySelector('iframe[title*="reCAPTCHA"]') ||
!!document.querySelector('.g-recaptcha') ||
document.body.innerText.includes('確認が必要です')
```

戻り値: `true` = CAPTCHA出現（処理中断が必要）

### ログイン切れ検出

```javascript
document.body.innerText.includes('Sign in') ||
document.body.innerText.includes('Hello! Sign in')
```

戻り値: `true` = ログイン画面にリダイレクト（処理中断が必要）

### 検索結果なし検出

```javascript
!!document.querySelector('.research-table__no-results')
```

戻り値: `true` = 検索結果0件（Total Sold = 0として記録）

---

## エラー対応表

| エラー種別 | 対応 | 続行可否 |
|-----------|------|---------|
| CAPTCHA検出 | 処理中断、ユーザーに手動解除を依頼 | ❌ |
| ログイン切れ | 処理中断、ユーザーに再ログインを依頼 | ❌ |
| 検索結果なし | 0として記録（リンク付き） | ✅ |

詳細は [error-handling.md](error-handling.md) を参照
