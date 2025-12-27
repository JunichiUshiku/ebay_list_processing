# eBay Product Research セレクター

## URL生成関数（変更禁止）

**⚠️ この関数を正確に実行すること。手動でURLを構築しないこと。**

### 90日間URL生成

javascript_toolで以下を実行（`KEYWORD`を置換）:

```
(function(keyword) { const now = Date.now(); const start = now - (90 * 24 * 60 * 60 * 1000); return 'https://www.ebay.com/sh/research?marketplace=EBAY-US&keywords=' + encodeURIComponent(keyword) + '&dayRange=90&startDate=' + start + '&endDate=' + now + '&categoryId=0&offset=0&limit=50&tabName=SOLD&tz=Asia%2FTokyo'; })('KEYWORD')
```

### 6ヶ月間URL生成

javascript_toolで以下を実行（`KEYWORD`を置換）:

```
(function(keyword) { const now = Date.now(); const start = now - (180 * 24 * 60 * 60 * 1000); return 'https://www.ebay.com/sh/research?marketplace=EBAY-US&keywords=' + encodeURIComponent(keyword) + '&dayRange=180&startDate=' + start + '&endDate=' + now + '&categoryId=0&offset=0&limit=50&tabName=SOLD&tz=Asia%2FTokyo'; })('KEYWORD')
```

**🔴 絶対禁止事項**:
- 上記関数の戻り値を使用せずに手動でURLを構築すること
- タイムスタンプをハードコードすること
- 関数を「参考情報」として独自実装すること

---

## URL検証関数（必須）

**ナビゲート前に必ず実行すること**

javascript_toolで以下を実行（`URL`を生成されたURLに置換）:

```
(function(url) { try { const params = new URLSearchParams(new URL(url).search); const endDate = parseInt(params.get('endDate')); const now = Date.now(); const diff = Math.abs(now - endDate); if (!endDate) return 'ERROR: endDateパラメータなし'; if (diff > 3600000) return 'ERROR: タイムスタンプが' + Math.round(diff/1000) + '秒古い'; return 'OK: 検証成功 endDate=' + endDate; } catch(e) { return 'ERROR: ' + e.message; } })('URL')
```

**検証結果の対応**:
- `OK:` → ナビゲート実行可
- `ERROR:` → URL生成からやり直すこと（検証失敗のままナビゲート禁止）

---

## 結果取得

### Total Sold合計取得

```
const cells = document.querySelectorAll('.research-table-row__totalSoldCount'); Array.from(cells).reduce((sum, cell) => sum + (parseInt(cell.innerText) || 0), 0);
```
※ 戻り値: Total Sold の合計数値

### HYPERLINK用URL

**⚠️ MCPセキュリティ制限により `window.location.href` は使用不可**

URL生成関数で取得したURLを保持し、HYPERLINK作成時に再利用すること:

```
処理フロー:
1. URL生成関数実行 → 戻り値を generatedUrl として保持
2. ナビゲート実行
3. Total Sold取得（数値のみ）
4. HYPERLINK作成: =HYPERLINK("${generatedUrl}", ${totalSold})
```

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
document.body.innerText.includes('Sign in') || document.body.innerText.includes('Hello! Sign in')
```
※ 戻り値: true = ログイン画面にリダイレクト（処理中断が必要）
※ MCPセキュリティ制限により `window.location.href` は使用不可

### 検索結果なし検出

```
!!document.querySelector('.research-table__no-results')
```
※ 戻り値: true = 検索結果0件（Total Sold = 0として記録）

---

## 🔴 エラー発生時の対応（必須手順）

**この表に従って対応すること。独自判断での続行禁止。**

| エラー種別 | 検出方法 | 対応 | 続行可否 |
|-----------|---------|------|---------|
| CAPTCHA検出 | `iframe[title*="reCAPTCHA"]` | 処理中断、ユーザーに手動解除を依頼 | ❌ 不可 |
| ログイン切れ | `innerText.includes('Sign in')` | 処理中断、ユーザーに再ログインを依頼 | ❌ 不可 |
| URL検証失敗 | 検証関数が`ERROR:`を返す | URL生成からやり直し | ❌ 不可（再生成後は可） |
| DOM未検出 | querySelector失敗 | 3秒待機後リトライ（最大3回） | △ 条件付き |
| タイムアウト | 10秒経過 | 5秒待機後リトライ（最大2回） | △ 条件付き |
| 検索結果なし | `.research-table__no-results` | 正常終了、0として記録 | ✅ 可 |

### リトライ間隔

| 回数 | 間隔 |
|------|------|
| 1回目 | 2秒 |
| 2回目 | 5秒 |
| 3回目 | 10秒 |
| 失敗 | 「取得エラー」記録、次へ |
