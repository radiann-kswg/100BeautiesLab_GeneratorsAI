# サブモジュール同期ログ — 2026-10-01 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 8a47bfe | c78afcb | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | c265fdd | c265fdd | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 8a47bfe..c78afcb

```
c78afcb chore: sync ai-dataset (creations-db@c265fdd8) 窶・ai_training allowed: 164 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |  6 +--
 ai-dataset/image-index.json                       |  2 +-
 ai-dataset/index.json                             |  4 +-
 ai-dataset/manifest-training.jsonl                | 12 ++---
 ai-dataset/manifest.jsonl                         | 58 +++++++++++------------
 ai-dataset/policy.json                            |  2 +-
 ai-dataset/works/Works_CommonReferences.json      |  2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |  2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |  2 +-
 ai-dataset/works/Works_NumberTales.json           |  4 +-
 ai-dataset/works/Works_PastDivers.json            |  2 +-
 ai-dataset/works/Works_ShauErRiders.json          |  2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |  2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |  2 +-
 ai-dataset/works/Works_UnibyteLive.json           |  2 +-
 ai-dataset/works/Works_VirtuesUs.json             |  2 +-
 creations-db                                      |  2 +-
 17 files changed, 55 insertions(+), 53 deletions(-)
```

## 最適化メモ

### 15:06 再取得・生成参照監査

- `daily-submodule-sync.ps1 -DryRun` で GitHub から再取得。CreationsAI `c78afcb`、CreationsDB `c265fdd` は追跡ブランチの最新と一致し、追加取り込みなし。
- 上流の `AppearanceDetail.img_PNGName` は存在するが、画像索引では番号等の attr 123枚が `category: null`。従来の全体図フィルタと観察カテゴリ制限で脱落していた。
- `src/` 側で宣言実名・適用形態から部位図を解決し、原点画像直後へ採用。原典の字形を禁止する指示も修正。
- 利用許可済み115レコードの監査で、部位画像を持つ172形態ケース・延べ228枚を全件解決・採用。既存の権利ゲート・本人照合は維持。
- 調査と検証の詳細: [`_ideas/20261001_official-reference-audit.md`](../_ideas/20261001_official-reference-audit.md)。


> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。


- 追加試行: 93・666を各ラフ1枚/完成1枚生成。666のNumberMark 1行=1か所という誤解釈を修正。公式部位図が届いても666のブローチ内部は未一致。詳細は ../_ideas/20261001_reference-generation-review.md。全87テスト成功。

### 10:15 Cowork 朝レビュー (daily-submodule-sync-optimize / 57イズナ)

- 実機スクリプト実行確認: `20261001_submodule-sync.md` 生成済み。`_creations-ai` が `8a47bfe..c78afcb` (chore: sync ai-dataset) で UPDATED、ネスト `creations-db` はログ上 NO-CHANGE。
- 差分の性質: データセット再生成のみ。`manifest-training.jsonl`(192件) / `manifest.jsonl`(757件) の最上位キー集合は新旧で完全一致、`Works_NumberTales.json` の再帰キーパスも一致。`build-info.json`/`index.json`/`policy.json` の差分は `generated_at`・`submodule_commit`(2274eb1→c265fdd)・`with_roleplay_prompt`(60→62) のみ。スキーマ/フィールド名/API/参照パスの変更なし。
- 追従判定: **src/ ・ docs/ の最適化は不要**。値・メタデータの更新のみで `src/` のプロンプト生成ロジックや `docs/*.md` の記述前提に影響しないため、過剰改変を避け編集なし。
- リモート照合 (GitHubコネクタ, 読み取りのみ): CreationsAI `master`=c78afcb / CreationsDB `addon-ai-tag`=c265fdd。いずれもローカルHEADと一致、次回同期待ちの未取り込み更新なし。
- 注記: 本サンドボックスからは全ファイルが CRLF↔LF 差分として見えるため `git add`/`commit`/`fetch` は未実行。コミットは実機 `scripts/daily-submodule-sync.ps1` が担当。
