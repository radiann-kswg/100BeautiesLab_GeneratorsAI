# サブモジュール同期ログ 2026-11-21

| サブモジュール | 追跡先 | 旧 | 新 | 判定 |
|---|---|---|---|---|
| `_creations-ai` | origin/master | c5031d1 | 68a873a | UPDATED |


## 取り込み範囲

### `_creations-ai` c5031d1..68a873a

```
68a873a chore: sync ai-dataset (creations-db@09b475e4) — ai_training allowed: 187 [skip ci]
5893ef5 chore: sync ai-dataset (creations-db@9abd3425) — ai_training allowed: 187 [skip ci]
9e73e88 chore: sync ai-dataset (creations-db@1e432890) — ai_training allowed: 187 [skip ci]
```

```
 ai-dataset/build-info.json                         |  6 ++--
 ai-dataset/image-index.json                        | 24 +++++++++++++--
 ai-dataset/index.json                              |  6 ++--
 ai-dataset/manifest-training.jsonl                 |  6 ++--
 ai-dataset/manifest.jsonl                          | 14 ++++-----
 ai-dataset/policy.json                             |  2 +-
 ai-dataset/works/Works_CommonReferences.json       |  2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json      |  2 +-
 ai-dataset/works/Works_FLInvestigator78.json       |  2 +-
 ai-dataset/works/Works_NumberTales.json            | 34 +++++++++++++++++-----
 ai-dataset/works/Works_PastDivers.json             |  2 +-
 ai-dataset/works/Works_ShauErRiders.json           |  2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json  |  2 +-
 ai-dataset/works/Works_StardustVsKaleidoscope.json |  2 +-
 ai-dataset/works/Works_UnauthedLogica.json         |  2 +-
 ai-dataset/works/Works_UnibyteLive.json            |  2 +-
 ai-dataset/works/Works_VirtuesUs.json              |  2 +-
 creations-db                                       |  2 +-
 18 files changed, 77 insertions(+), 37 deletions(-)
```

### `_creations-ai/creations-db` 02cfe1e..09b475e（ネスト）

```
09b475e4 Merge branch 'develop' into addon-ai-tag
467e54f9 DB進捗更新(ナンバーテールズ)
9abd3425 Merge pull request #66 from radiann-kswg/auto/aihints-structural-resync
e9f30083 AIHints: 構造的再同期（自動生成）
1e432890 Merge branch 'develop' into addon-ai-tag
1e4ed94f DB情報追加・推敲(ナンバーテールズ)＆進捗ログ追記
```

```
 .../2026-11-20_github-issue-28-review.md           |  49 +++++++++++++++++++++
 .../DataBases/db_SelfSecondary.json                |  12 ++---
 .../DataBases/db_SemiPrimary.json                  |  28 ++++++------
 .../Works_NumberTales/Dictionaries/dict_Class.json |   2 +-
 .../concept/rm/cnsp_imgNTS-314RM.png               | Bin 0 -> 37784 bytes
 .../attr/tailsUnit/attr_tailsUnitNTS-333.png       | Bin 0 -> 15235 bytes
 .../attr/tailsUnit/attr_tailsUnitNTS-888.png       | Bin 0 -> 14695 bytes
 .../concept/DVinesForDevelop/cnsp_imgNTS-314.png   | Bin 0 -> 37383 bytes
 data/Works_NumberTales/lot.md                      |   2 +-
 9 files changed, 72 insertions(+), 21 deletions(-)
```

## 最適化メモ

- 差分把握: データの再生成のみ（スクリプトの変更なし）。ナンバーテールズの DB 進捗更新で、
  - SelfSecondary の `314-am`（量産型 314 番機 AM シリーズ）が `314-rm`（RM シリーズ）に改名。`ai_training.allowed` は改名前後とも false。
  - 266・314 の表示名を修正。314 の不許可理由が `nowCreating` から `stillTentative` に変わった（不許可のまま）。
  - 333・888 に `TailsUnit_PNGName` が入り、`images.tails_unit` と `image-index.json` に 2 件追加（573→575 件）。
  - 許可件数は 187 件のまま。スキーマ・フィールド名・`manifest-training.jsonl` の前提に変化なし。
- 影響判定: 最適化不要。`314-am` / `314-rm` を名指しするコード・テスト・ドキュメントは無く（grep で確認）、`tails_unit` は既存の処理が扱う。
- `collect_reference_images()` で確認: 333・888 の尻尾ユニット図（`attr_tailsUnitNTS-333.png`・`-888.png`）は `humanoid`・`tailsunit` 形態で参照に入る。`corefolder` 形態では従来どおり `_is_path_compatible_with_form` が除外する（設計どおり）。
- テスト結果: tests/ の 144 件成功・2 件スキップ（API キーは空、`OUTPUT_SINK=local`、Linux のクラウド環境）。
- Cowork の GeneratorsAI プロジェクトで見つかった改善点の反映を依頼されたが、その内容はリポジトリ内の記録（`_ideas/`・`_tasks/`・`docs/`）に見当たらず、このセッションから Cowork プロジェクトの会話や知識は読めない。今回の同期では未反映。内容の共有を待って別途対応する。
