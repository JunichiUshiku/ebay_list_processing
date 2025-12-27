# エラーハンドリング詳細

## 目次

1. [エラー種別と対応](#エラー種別と対応)
2. [検出コード](#検出コード)
3. [リトライ戦略](#リトライ戦略)

---

## エラー種別と対応

| エラー種別 | 検出方法 | 対応 | 記録値 |
|------------|----------|------|--------|
| URL形式不正 | `_nkw=`なし | 次へスキップ | 「URLエラー」 |
| ログイン切れ | innerText検出 | 処理中断 | ユーザー通知 |
| CAPTCHA出現 | iframe検出 | 処理中断 | ユーザー通知 |
| 検索結果なし | DOM検出 | 正常終了 | 0（リンク付き） |
| ページタイムアウト | 10秒経過 | リトライ3回 | 「タイムアウト」 |
| DOM要素未検出 | querySelector失敗 | リトライ3回 | 「取得エラー」 |
| 書き込み失敗 | MCP例外 | リトライ2回 | ログ出力 |

---

## 検出コード

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

戻り値: `true` = ログイン画面にリダイレクト

**注意**: MCPセキュリティ制限により `window.location.href` は使用不可

### 検索結果なし検出

```javascript
!!document.querySelector('.research-table__no-results')
```

戻り値: `true` = 検索結果0件（Total Sold = 0として記録）

### ロード完了検出

```javascript
!!document.querySelector('.research-table-row__totalSoldCount') ||
!!document.querySelector('.research-table__no-results')
```

戻り値: `true` = ロード完了

---

## リトライ戦略

### リトライ間隔

| 回数 | 間隔 |
|------|------|
| 1回目 | 2秒 |
| 2回目 | 5秒 |
| 3回目 | 10秒 |
| 失敗 | エラー記録、次の行へ |

### リトライ対象

- ページタイムアウト: 最大3回
- DOM要素未検出: 最大3回
- 書き込み失敗: 最大2回

### リトライ非対象（即時中断）

- ログイン切れ
- CAPTCHA出現
- URL形式不正

---

## エラー発生時の対応フロー

### ログイン切れ/CAPTCHA検出時

1. 処理を即時中断
2. ユーザーに通知:
   - ログイン切れ: 「eBayへの再ログインが必要です」
   - CAPTCHA: 「CAPTCHAの手動解除が必要です」
3. 処理済み件数をサマリー報告
4. LINE通知送信（エラー内容を含む）

### タイムアウト/DOM未検出時

1. リトライ間隔で待機
2. 再度ナビゲート/取得を試行
3. 3回失敗 → エラー記録、次の行へ
4. 全件処理後にエラー行をサマリー報告

---

## エラー記録形式

### スプレッドシートへの記録

| エラー種別 | X列記録値 |
|------------|-----------|
| URLエラー | `URLエラー` |
| タイムアウト | `タイムアウト` |
| 取得エラー | `取得エラー` |
| 検索結果なし | `=HYPERLINK("URL", "0")` |

### サマリー報告形式

```
## 結果

| 項目 | 結果 |
|------|------|
| 処理件数 | 50件 |
| 成功 | 47件 |
| エラー | 3件 |

### エラー詳細
- 行15: タイムアウト
- 行28: URLエラー
- 行42: 取得エラー
```
