# 複数形態・複数キャラ画像のAIデータセット組み込み

**作成日**: 2026-06-19  
**ステータス**: フェーズ1・フェーズ2 完了（2026-06-19）

---

## 背景

`concept` 系画像や複数キャラが作画されたイラストは、現状のAIデータセット (`manifest.jsonl`) に個別キャラクターと紐付いた形で含まれていなかった。  
キャラクターごとの特徴をまとめた `AIHints` フィールドが充実してきたことを受け、複数形態・複数キャラ画像も活用できるよう段階的に対応する。

---

## フェーズ1: build-dataset.js 側の拡張（2026-06-19 完了）

### 変更内容

`_creations-ai/scripts/build-dataset.js` の `resolveCharacterImages()` を拡張し、各キャラクターレコードの `images` フィールドに以下のサブキーを追加した。

| サブキー | 元フィールド | 概要 |
|---|---|---|
| `concept` | `Images.concept_PNGName` | 両形態を描いた概念イラスト (1枚) |
| `concept_alt` | `Images.conceptAlt_PNGName[]` | 概念イラストのバリアント群 |
| `arts` | `Images.arts_PNGPath[]` | キャラクター個別アートワーク |
| `design_alt` | `Images.designAlt_PNGPath[]` | 衣装差分・デザインバリアント |

既存の `images.DB_Primary` (corefolder 等のフォルダスキャン結果) は引き続き維持。

拡張子は `.png` 優先で `.jpg/.jpeg/.gif/.webp/.svg` にも対応するヘルパー `resolveImagePath()` を追加。ファイルが実在しない場合はキー自体が省略される。

### パス規則

すべてのパスは creations-db サブモジュールルートからの相対パス。

```
concept / concept_alt → data/{Work}/Images/DB_Primary/concept/{name}.{ext}
arts / design_alt     → data/{Work}/Images/DB_Primary/arts/{rel}.{ext}
```

### ビルド確認結果（2026-06-19）

`node scripts/build-dataset.js --verbose` 実行結果:

- **`concept`**: 94キャラクターに反映 ✅
- **`arts`**: 対応キャラクターに反映 ✅ (例: char2 → `arts/corefolders/2023/art_img2-corefolderWinter.png`)
- **`concept_alt`**: 0件 → **画像ファイルが creations-db にまだ未コミット**
- **`design_alt`**: 0件 → **画像ファイルが creations-db にまだ未コミット**

`conceptAlt_PNGName` (14/28/35/41/60/61/66番) および `designAlt_PNGPath` (35/44/61/66/85番) に参照されているファイルは、JSONフィールドには登録済みだが `addon-ai-tag` ブランチの現時点では画像ファイルが存在しない。  
**実装は正しく機能している**（`resolveImagePath()` がファイル実在チェックを行うため、未コミット画像は自動的に除外される）。  
creations-db に画像が追加されサブモジュールが更新された次回ビルド時に自動で反映される。

また、`designAlt_PNGPath` に含まれる `eventArt/art_halloween2023A` / `art_halloween2023B` は char44・char66・char85 の3キャラが同一パスを参照していることが判明。**複数キャラが同じイラストに登場するケース**（フェーズ2 案C の対象）が確認された。

### 確認が必要な事項（継続）

- [ ] creations-db に `conceptAlt` / `designAlt` 画像が追加された後、次回ビルドで正しく反映されるかを確認
- [ ] `eventArt` 系画像（複数キャラ登場）の `arts_metadata` 対応を案Cとして上流に提案するタイミングを検討

---

## フェーズ2: creations-db 側の対応（2026-06-19 サブモジュール更新で完了）

`addon-ai-tag` ブランチへの変更が取り込まれ、`build-dataset.js` への反映も完了。

---

### 案B: `AIHints.concept_contains_forms` フィールド追加 ✅

#### 目的

`concept_PNGName` の画像が「どの形態を含むか」を明示する。  
現状、概念イラストには `corefolder` と `humanoid` の両形態が描かれているが、それが機械可読でない。

#### 提案フィールド

`data/Works_NumberTales/DataBases/db_Primary.json` の各キャラクターレコード内 `AIHints` に追加:

```json
"AIHints": {
  "concept_contains_forms": ["corefolder", "humanoid"],
  ...
}
```

許容値: `"corefolder"`, `"humanoid"`, 将来的に `"corefolder_dressed"` 等も追加可。

#### build-dataset.js 側の対応（案B実装後）

`build-dataset.js` で `ai_hints.concept_contains_forms` としてマニフェストに反映するだけ（AIHints をそのままトップレベルに露出する既存ロジックで自動対応）。  
ただし `has_*` フラグ群に `has_concept_forms_metadata: boolean` を追加すると消費側で検索しやすくなる。

---

### 案C: `arts` / `concept` 内の複数キャラ情報の明示 ✅

#### 目的

複数キャラが作画されているアートワークについて、どのキャラクターが登場するかを機械可読にする。  
現状、`image-index.json` の作品レベルには画像一覧があるが、「誰が写っているか」の情報がない。

#### 提案フィールド

**パターンA: `arts_PNGPath` をオブジェクト配列化**

```json
"arts_PNGPath": [
  {
    "path": "humanoids/2023/art_img1-humanoid",
    "characters": [1],
    "form": "humanoid"
  }
]
```

> ⚠️ 後方互換破壊になるため `build-dataset.js` の既存パース処理も要修正。  
> 文字列配列と混在させる場合は型判定が必要。

**パターンB: 別フィールド `arts_metadata` を新設（後方互換あり）**

```json
"arts_metadata": [
  {
    "path": "humanoids/2023/art_img1-humanoid",
    "characters": [1],
    "form": "humanoid"
  }
]
```

> `arts_PNGPath` を変えずに補完情報として追加できる。既存の `build-dataset.js` への影響が少ない。推奨。

**複数キャラ artwork の場合:**

```json
"arts_metadata": [
  {
    "path": "arts/art_numbertalesAniv4th",
    "characters": [1, 5, 12, 25, 57],
    "form": null,
    "note": "4th anniversary art"
  }
]
```

#### build-dataset.js 側の対応（案C実装後）

- `resolveCharacterImages()` で `charData.Images.arts_metadata` を参照し、`characters[]` が自キャラを含む画像のみを `arts` キーに追加する
- 複数キャラ artwork を参照している他キャラのレコードにも同じ画像パスが反映されるため、クロス参照学習が可能になる

---

### 案D: `designAlt_PNGPath` への形態・説明注記 ✅

#### 目的

衣装差分画像がどの形態・どのシーンのものかを示す。現状、`designAlt_PNGPath` はパス文字列のみでメタ情報がない。

#### 提案フィールド

```json
"designAlt_PNGPath": [
  {
    "path": "chattingArt/chart_img35-swimwear",
    "form": "humanoid",
    "note": "水着バリアント"
  }
]
```

または `designAlt_metadata` として別フィールド化（案C パターンBと同様の方針）。

---

## 完了サマリー

| 案 | 実装場所 | 完了日 | 追加内容 |
|---|---|---|---|
| フェーズ1 | `build-dataset.js` | 2026-06-19 | `images.concept/arts/design_alt` のパスをマニフェストに反映 |
| 案B | creations-db `db_Primary.json` | 2026-06-19 | `AIHints.concept_contains_forms: ["corefolder","humanoid"]` を全キャラに追加 |
| 案C | creations-db `db_Primary.json` | 2026-06-19 | `Images.arts_metadata[]{path,form,characters}` を追加 |
| 案D | creations-db `db_Primary.json` | 2026-06-19 | `Images.designAlt_metadata[]{path,form,characters}` を追加 |
| build-dataset.js 反映 | `build-dataset.js` | 2026-06-19 | arts/design_altをメタデータ形式に変更・designAltパス修正・`has_concept_forms_metadata` フラグ追加 |

**build-info.json の追加統計**: `ai_hints_stats.with_concept_forms_metadata`

---

## 関連ファイル

- `_creations-ai/scripts/build-dataset.js` — フェーズ1実装済み
- `_creations-ai/ai-dataset/policy.json` — `images_field` スキーマ説明を追加済み（ビルド後に反映）
- `_creations-ai/creations-db/data/Works_NumberTales/DataBases/db_Primary.json` — 案B〜D の対象ファイル（読み取り専用）
- `_creations-ai/creations-db/` — `addon-ai-tag` ブランチで管理

## 注意事項

- `creations-db` への変更は上流リポジトリ側での対応が必要（サブモジュール更新後に `build-dataset.js` を再ビルドして反映）
- フェーズ1は次回の `node scripts/build-dataset.js --verbose` 実行時に自動で `manifest.jsonl` に反映される
- `designAlt` は `conceptAlt` と異なり「キャラクター間の情報」ではなく「1キャラクターの衣装バリアント」なので、フェーズ2での優先度は低め
