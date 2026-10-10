# 辞書データのライセンスと帰属

調査日: 2026-10-10。プログラム自体はMITですが、以下の辞書にはそれぞれの条件が適用されます。
公開・再配布するときは、このファイルと `licenses/` を辞書に添付してください。

## SudachiDict Full由来の日本語辞書

- 対象: `gen_pass/dictionary/japanese_romaji.txt`
- 提供者: Works Applications Co., Ltd.
- Copyright (c) 2017-2023 Works Applications Co., Ltd.
- 元データ: [SudachiDict](https://github.com/WorksApplications/SudachiDict)、20260723版。
  Full相当の `small_lex.csv`, `core_lex.csv`, `notcore_lex.csv` をすべて使用。
- 参照リポジトリ: `v20260723.1`、コミット `3e49051e71011cac7d74df779e80ef1dab818e56`。
  ソースCSVは20260723版のV0配布ZIPを使用。バイナリ辞書は同梱していません。
- ライセンス: [Apache License 2.0全文](licenses/Apache-2.0.txt)。
- 収録元の追加条件・謝辞: [上流LEGAL全文](licenses/SudachiDict-LEGAL.txt)。
  [固定コミットの原文](https://github.com/WorksApplications/SudachiDict/blob/3e49051e71011cac7d74df779e80ef1dab818e56/LEGAL)。

改変内容: 名詞・読み・表記による選別、ASCIIヘボン式を基本とするローマ字変換、
長さ制限、ローマ字の重複除去、クラスごとの固定ハッシュ順位での抽出、並べ替え。
`scripts/build_dictionary.py` に処理を保存しています。本派生辞書の追加変更もApache 2.0で提供します。

Apache 2.0は改変・抽出物の再配布を許諾し、ライセンスの添付、変更の明示、
関係する著作権・帰属表示などの維持を要求します。本リポジトリでは上流LEGAL全体を維持します。
上流に独立したNOTICEファイルはなく、LEGALを帰属資料として添付しています。

### 収録元の条件

- **UniDic**: Copyright (c) 2011-2013, The UniDic Consortium, All rights reserved.
  SudachiDict LEGALには改変の有無を問わずソース・バイナリの再配布を許諾するBSD 3条項相当の条件が記載されています。
  著作権表示、条件、免責文の保持が必要です。提供者名による推薦・宣伝は許諾されません。
- **NEologd**: Copyright (C) 2015-2019 Toshinori Sato (@overlast)。
  SudachiDictは [mecab-unidic-neologd](https://github.com/neologd/mecab-unidic-neologd) の一部を含みます。
  Apache 2.0の許諾と収録元への謝辞・参照がLEGALにあります。
  はてなキーワード、日本郵便の郵便番号、スナフキん氏の全国駅名、工藤拓氏の人名、
  Web文書について、上流の日本語による説明とURLをLEGALにそのまま保持しています。
  元データの新規取得や個別ライセンスの付け替えは行っていません。

### 代替候補の調査

[mecab-ipadic-NEologdのCOPYING](https://github.com/neologd/mecab-ipadic-neologd/blob/master/COPYING)
にもApache 2.0と元データへの帰属があり、固有名詞の補完候補になります。
UniDic由来データの再配布条件は上記SudachiDict LEGALで確認しました。
今回はFull由来だけで必要語数と分類を確保できたため、これらを別途追加していません。
上流に含まれる各資源の個別バージョンはLEGALに記載されておらず、
本リポジトリではSudachiDictの固定配布版とSHA-256で由来を特定します。

## EFF Short Wordlist #1由来の英語辞書

- 対象: `gen_pass/dictionary/english.txt`
- 原作: Electronic Frontier Foundation (EFF)、リスト作成者 Joseph Bonneau。
- 版: Short Wordlist #1、2016-09-08配布URLの固定内容。
- [紹介・原作者表記](https://www.eff.org/dice)
- [元のリスト](https://www.eff.org/files/2016/09/08/eff_short_wordlist_1.txt)
- [EFF Copyright Policy](https://www.eff.org/copyright): 特記がないEFF独自コンテンツはCC BY 4.0。
- [CC BY 4.0全文](licenses/CC-BY-4.0.txt)、[ライセンスの説明](https://creativecommons.org/licenses/by/4.0/)。

変更内容: サイコロ番号を削除、`yo-yo`を`yoyo`に正規化、重複除去、
日本語辞書と同一表記の8語を除外、ASCII順に並べ替え。
本派生英語辞書もCC BY 4.0で提供します。
改変・商用利用を含む再配布が可能で、適切な帰属表示、ライセンスへの参照、変更の明示が必要です。
EFFや元データ提供者による本ツールの推薦を意味しません。

## 配布物と再現性

ダウンロード元URL、版、入力SHA-256は `gen_pass/dictionary/sources.json` に記録しています。
抽出数は `gen_pass/dictionary/build_stats.json` を参照してください。
上流の大きなZIPはビルド用キャッシュだけに保存し、公開用の同梱物には含めません。
