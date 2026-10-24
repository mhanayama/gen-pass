# gen-pass — 日本語ローマ字パスワードジェネレーター

macOS・Linux・Windows向けのCLIです。日本語由来のローマ字を中心とする
パスフレーズを表示し、同じパスワードだけをクリップボードへコピーします。
`--hr`を指定すると、手入力しやすい小文字の英単語3語＋数字4桁を生成します。
辞書を含めてインストールでき、任意のディレクトリから`gen-pass`で実行できます。
通常実行は完全オフラインです。Releaseの実行ファイルはPythonの事前インストール不要で、
ソースから使う場合はPython **3.11以降**が必要です。

## インストール

### 1コマンドでインストール（Python不要）

公開済みの[GitHub Releases](https://github.com/mhanayama/gen-pass/releases/latest)から、
OS・CPUに合う実行ファイルを取得し、SHA-256を検証してインストールします。
最初のReleaseを公開するまでは、このURL・コマンドは利用できません。

macOS / Linux:

```bash
curl -fsSL https://github.com/mhanayama/gen-pass/releases/latest/download/install.sh | sh
```

Apple Silicon・Intel Macと、Linuxのarm64・x86_64に対応しています。
管理者権限は不要で、実行ファイルは`~/.local/bin/gen-pass`、
ライセンスは`~/.local/share/gen-pass/`へ配置します。
既に`gen-pass`がPATH上にあれば、その導入先を自動検出し、同じコマンドで最新版に置き換えます。
以前の版をアンインストールする必要はありません。初回に配置先を変更した場合も、PATHに入っていれば引き継ぎます。
`~/.local/bin`がPATHに含まれていない場合は、`~/.local/bin/gen-pass`で直接実行するか、
シェルの設定ファイル（zshなら`~/.zshrc`、bashなら`~/.bashrc`など）へ次を追加してください。

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Windows x64（PowerShell）:

```powershell
irm https://github.com/mhanayama/gen-pass/releases/latest/download/install.ps1 | iex
```

実行ファイルとライセンスを`%LOCALAPPDATA%\Programs\gen-pass\`へ配置し、
ユーザーのPATHと実行中のPowerShellのPATHへ追加します。他のターミナルは開き直してください。
既に`gen-pass.exe`がPATH上にある場合はその場所を自動検出し、旧版を最新版に置き換えます。
管理者権限とPythonは不要です。Windows arm64用のビルドは提供していません。

導入後の確認:

```text
gen-pass --help
gen-pass --hr
```

インストーラーはダウンロードした実行ファイルを`--help`で確認し、クリップボードは変更しません。
Linuxのクリップボード利用には`wl-clipboard`、`xclip`または`xsel`が別途必要です。
クリップボードがない環境では`gen-pass --no-clipboard`を使ってください。

バージョンや配置先を指定する場合は、ダウンロードしたスクリプトに環境変数を渡せます。
`GEN_PASS_VERSION=v0.1.0`で特定のRelease、`GEN_PASS_INSTALL_DIR`で絶対パスの配置先を指定します。
macOS / Linuxのライセンス配置先は`GEN_PASS_DATA_DIR`で変更できます。
`GEN_PASS_INSTALL_DIR`の明示指定は、既存導入先の自動検出より優先します。
更新先への書き込み権限がない場合はエラーになります。
自動更新はインストーラー実行時に行い、通常のパスワード生成時はオフラインのままです。
pipxで導入したコマンドも実行ファイルへ置き換えられますが、旧venvは残ります。
移行後の更新・削除はこのインストーラーと下記の手順を使ってください。

### ダウンロードして使う（Python不要）

Releaseの対応ファイルをダウンロードして展開すると、`gen-pass/`の中に実行ファイルと
ライセンスが入っています。macOS / Linuxでは`./gen-pass`、Windowsでは`.\gen-pass.exe`で実行できます。

| 環境 | 配布ファイル |
|---|---|
| macOS / Apple Silicon | `gen-pass-macos-arm64.tar.gz` |
| macOS / Intel | `gen-pass-macos-x86_64.tar.gz` |
| Linux / x86_64 | `gen-pass-linux-x86_64.tar.gz` |
| Linux / arm64 | `gen-pass-linux-arm64.tar.gz` |
| Windows / x64 | `gen-pass-windows-x86_64.zip` |

Linux版はglibc 2.35以降（Ubuntu 22.04以降など）を対象とし、Alpine Linuxのmusl環境には非対応です。
macOS版はmacOS 15以降をビルド・動作確認の対象にしています。
実行ファイルは配布者証明書でのコード署名・公証を行っていないため、ダウンロード方法やOS設定によって
macOSのGatekeeperやWindowsのSmartScreenに確認・ブロックされる場合があります。
各アーカイブの`.sha256`も同じReleaseに添付します。

### ソースからインストール（pipx）

Python 3.11以降と[pipx](https://pipx.pypa.io/)を用意します。
pipxはアプリ専用の仮想環境を作り、シェルからコマンドを呼び出せるようにするツールです。

#### macOS

Homebrewを利用している場合:

```bash
brew install pipx
pipx ensurepath
```

#### Linux

Ubuntu / Debianの例:

```bash
sudo apt install pipx python3-venv
pipx ensurepath
```

クリップボードを使う場合は、Waylandなら`wl-clipboard`、X11なら`xclip`または`xsel`も用意します。
Ubuntu / Debianの例は`sudo apt install wl-clipboard`または`sudo apt install xclip`です。
SSH・サーバーなどデスクトップのクリップボードがない環境では`--no-clipboard`を指定します。
ディストリビューションのPythonが3.11未満なら、3.11以降を別途用意し、
`pipx install --python /path/to/python3.11 .`のように指定してください。

#### Windows

Python 3.11以降をインストールした後、PowerShellまたはコマンドプロンプトで:

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
```

#### gen-passのインストール（3 OS共通）

`ensurepath`後にターミナルを開き直し、このリポジトリのディレクトリで実行します。
Windowsで`pipx`が見つからない場合は`py -m pipx`で置き換えられます。

```text
pipx install .
gen-pass --help
gen-pass
gen-pass -n 32
```

辞書とライセンスもインストールされるため、実行時に元のリポジトリは不要です。
パッケージ名は`gen-pass-romaji`、呼び出すコマンド名は`gen-pass`です。
インストール時はビルドツール取得のためネットワークを使う場合があります。
PyPIへの公開を前提にせず、ローカルディレクトリからインストールできます。

ソースを変更した後の更新とアンインストール:

```text
pipx install --force .
pipx uninstall gen-pass-romaji
```

pipxを使わない場合は、専用venvに`python -m pip install .`でインストールし、
そのvenvを有効にしたシェルから`gen-pass`を実行できます。
配布用wheelは`python -m pip install build`と`python -m build`で作成できます。
作成されたwheelも`pipx install /path/to/gen_pass_romaji-0.1.0-py3-none-any.whl`でインストールできます。
wheelに実行時Python依存パッケージはなく、Python自体は別途必要です。

### アンインストール

1コマンドのインストーラーで導入した場合は、macOS / Linuxでは
`~/.local/bin/gen-pass`と`~/.local/share/gen-pass/`を削除します。
Windowsでは`%LOCALAPPDATA%\Programs\gen-pass\`を削除し、ユーザーのPATHから同じ項目を取り除きます。
既存導入先を引き継いだ場合や配置先を変更した場合は、その場所のファイルを削除してください。
pipxで導入した場合は`pipx uninstall gen-pass-romaji`を使います。

## Releaseの作成（メンテナー向け）

`pyproject.toml`のバージョンに一致する`v`付きタグをpushすると、
GitHub Actionsが5環境の実行ファイル、SHA-256、wheel、ソースアーカイブ、
`install.sh`、`install.ps1`をビルドし、下書きReleaseへアップロードします。
すべての環境でテストと実行ファイルの動作確認が成功した後にアップロードします。

変更をコミット・pushした後、バージョン0.1.0の場合:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Actionsの`Build release`が成功したら、Releasesで下書きの添付ファイルを確認し、
`Publish release`で公開してください。通常の安定版Releaseを最新にすると、1コマンド導入の対象になります。
同じタグのワークフローを再実行すると、下書きの添付ファイルを更新します。
公開済みReleaseのファイルは上書きせず、エラーで停止します。
Actionsからの手動実行（`workflow_dispatch`）はビルドとArtifactsへの保存だけを行います。

手元のOS・CPU向けの配布物を作る場合（Python 3.11以降）:

```bash
python3 -m venv .build/release-tools
.build/release-tools/bin/python -m pip install -r scripts/release-requirements.txt
.build/release-tools/bin/python scripts/build_release.py
```

WindowsではvenvのPythonを`.build\release-tools\Scripts\python.exe`に置き換えます。
生成物は`dist/release/`に保存されます。別のOS・CPU用は、それぞれの環境でビルドが必要です。
Pythonランタイムと辞書を実行ファイルに含め、各配布アーカイブにもライセンスを同梱します。

## 使い方

インストール後は任意のディレクトリで実行できます。

```bash
gen-pass
gen-pass -n 8
gen-pass -n 12
gen-pass -n 16
gen-pass -n 17
gen-pass -n 32
gen-pass -n 32 --ed
gen-pass -n 32 --eu
gen-pass -n 16 --ed --eu
gen-pass --hr
gen-pass --hr -n 20
gen-pass --hr --ed
gen-pass --hr --ed --eu
gen-pass --no-clipboard
gen-pass --help
```

インストールせずにリポジトリ内で`python3 gen-pass.py`、macOS・Linuxでは`./gen-pass.py`でも実行できます。
Windowsでは`py gen-pass.py`を使用できます。インストール済み環境では`python -m gen_pass`にも対応します。
辞書の場所はパッケージを基準に解決します。

| オプション | 動作 |
|---|---|
| 未指定 | 日本語5語＋5桁の数字 |
| `-n N`, `--max-length N` | 通常は3〜16でN文字ちょうどのランダム文字列、17以上でN文字以内のパスフレーズ。`--hr`では3語＋4桁を維持してN文字以内 |
| `--ed` | `-`を禁止 |
| `--eu` | `_`を禁止 |
| `--hr` | Human Readableモード。小文字の英単語3語＋数字4桁、区切りは`-` |
| `--no-clipboard` | コピーせずコンソールに表示する（SSH・サーバー向け） |

Nが3未満または整数でなければ、生成もコピーもせず終了コード2で終了します。
`--hr`で指定した最大長に3語＋4桁が収まらなければ、生成もコピーもせず終了コード1で終了します。
旧オプション`--exclude-dash`と`--exclude-under`は廃止しました。
既存のスクリプトでは、それぞれ`--ed`と`--eu`に置き換えてください。
旧オプションや`--h`などの省略形は受け付けず、終了コード2で終了します。
記号は必須ではなく、両方を除外すると英数字だけになります。
エントロピーが80 bit未満でも生成します。

出力形式（2行目は説明用のプレースホルダー）:

```text
Generated 43 character password. Entropy: ~91.3 bits
<生成したパスワード>
```

実際の文字数を表示します。推定を行わないモードでは`Entropy: N/A`になります。
クリップボードにはパスワードだけを、改行なしで渡します。
生成は1回だけで、表示とコピーには同じ値を使います。
macOSでは`/usr/bin/pbcopy`、Windowsでは`clip.exe`、Linuxではセッションとインストール状況から
`wl-copy`、`xclip`、`xsel`を選びます。X11ではPRIMARYではなくCLIPBOARD選択へコピーします。
いずれもシェルを介さず呼び出し、パスワードはコマンド引数に含めず標準入力に渡します。
コピー失敗・タイムアウト時は標準エラーに通知して終了コード1で終了します。
この場合も表示済みのパスワードは利用できますが、クリップボード更新は保証されません。
対応ツールやデスクトップセッションがない場合は、導入方法または`--no-clipboard`を案内して失敗を通知します。

## 生成方式

### Human Readable（`--hr`）

テレビやゲーム機などへの手入力向けに、8文字以内の小文字の英単語3語と、末尾の数字4桁を使います。
形式例は`river-apple-tiger-5831`です（同梱辞書の語を使った説明用の例です）。
既存の英語辞書1,287語はすべて3〜5文字なので、そのまま利用できます。
語数・数字桁数は固定で、追加の設定オプションはありません。

| `--hr`と併用するオプション | 区切り | 同梱辞書での文字数 |
|---|---|---|
| なし、または`--eu` | `-` | 16〜22文字 |
| `--ed` | `_` | 16〜22文字 |
| `--ed --eu` | なし | 13〜19文字 |

単語の重複と数字の先頭0を許可します。
単語・数字はCSPRNGで一様に選び、大文字化や数字位置のシャッフルは行いません。

`-n N`の併用時は、数字と区切りも含めてN文字以内に収まる語列を一様に選びます。
語列の組合せ数を長さごとに数えて重み付き抽選するため、短い語列だけに偏ることはありません。
現在の辞書では区切りありで最低16文字、区切りなしで最低13文字必要です。
収まらなくても語数・数字桁数を減らしたり、ランダム文字列へ切り替えたりはしません。

### デフォルト

31,184語の日本語辞書から5語を独立・一様に選びます。重複選択を許可し、
順序をCSPRNGでシャッフルします。5桁の数字は各桁独立で、先頭0も許可します。
数字列の挿入位置は6か所から一様に選択します。
各境界に、禁止されていない`-`または`_`を一様に選びます。

各語の先頭だけをランダムに大文字化します。全小文字を除く31通りのパターンから
一様に選び、少なくとも1語が大文字で始まります。

### 最大長17文字以上（`--hr`なし）

読みやすさと語彙数を保つため、まず6文字以上の日本語を優先します。
目標語数は`min(5, max(2, (N - 1) // 6))`です。
同じ語数では日本語の数が多い構成を優先し、収まらなければ短い英語を混合し、
必要なら英語だけにします。数字桁数は5〜1で調整します。
構成を選ぶ優先順位は「目標語数 → 日本語語数 → 数字桁数 → 合計文字数」です。
その構成の中で、可能な限り上限に近い長さを選びます。
例として同梱辞書の`-n 17`は日本語2語、`-n 32`は日本語3語と英語2語になります。
記号除外によって構成は変わります。

動的計画法で、各語の長さ別候補数と残りの組合せ数を事前に計算し、
完成可能な候補だけを重み付きで選びます。選んだ構成・合計語長の中では語列を一様に選びます。
単純な切り詰めや、試行回数切れによるフォールバックは行いません。
優先構成が成立しなければ語数を減らし、短い日本語を含む辞書全体も探索します。
2語以上のパスフレーズが成立しない場合だけ、上限と同じ長さのランダム文字列へ切り替えます。
語数は読みやすさのため最大5語なので、十分大きなNでは上限を使い切らないことがあります。

### 最大長16文字以下（`--hr`なし）

候補文字は`abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_`から
禁止記号を除いた集合です。N文字全体を独立・一様に抽選し、
大文字・小文字・数字のいずれかが欠けていれば全体を再抽選します。
これにより必須文字種を満たす全候補から一様に生成します。
「各文字種を1文字ずつ入れてから埋める」方式の分布の偏りを避けています。

すべての乱数選択にはPythonの`secrets.choice` / `secrets.randbelow`を使います。
固定シード、`random`、手作業での剰余選択は使用しません。

## 参考エントロピー

数値は参考値で、パスワードの実用上の安全性や80 bitを保証する表示ではありません。

- **デフォルト・区切りあり**: `5 × log2(31184) + 5 × log2(10) ≈ 91.3 bit`。
  大文字化、区切り選択、数字位置、シャッフルの寄与は加算しません。
  辞書と語数が公開されても、独立した語と数字の選択がランダム性を提供します。
- **Human Readable・区切りあり**: `3 × log2(1287) + 4 × log2(10) ≈ 44.3 bit`。
  長さ制限付きでは、収まる順序付き語列の数をCとして`log2(C) + 4 × log2(10)`を表示します。
  区切りなしでは語境界が曖昧になるため`N/A`です。
- **長さ制限付き単語モード**: `N/A`。
  構成や長さで語彙を条件付けするため、単純な辞書語数の式を当てはめません。
- **区切りなし単語モード**: `N/A`。
  異なる語列を同じ文字列に連結できる可能性があります。大文字化は全境界を表示しません。
- **ランダム文字列**: 必須3文字種を含む有効文字列数Mに対する`log2(M)`。
  文字集合の大きさをSとすると、包除原理で
  `M = S^n - 2(S-26)^n - (S-10)^n + (S-52)^n + 2(S-36)^n - (S-62)^n`。
  例えば3文字は約15.3 bit、記号除外なしの8文字は約47.5 bitです。

構成の切替や語境界の曖昧さがある出力に、上記の単純式による値を付けません。
短いサイト制約でも拒否せずに生成します。

## 辞書と再構築

固定データを`gen_pass/dictionary/`に同梱しています。通常実行時のダウンロード処理はありません。

| 辞書 | 語数 | 由来 |
|---|---:|---|
| 日本語ローマ字 | 31,184 | SudachiDict Full相当、20260723版 |
| 英語 | 1,287 | EFF Short Wordlist #1、2016-09-08 |

日本語は一般・サ変可能名詞、地名、人名、その他の固有名詞を対象にします。
日本語表記2〜12文字、ローマ字4〜12文字に限定し、数字・記号を含む表記や、
接頭辞・接尾辞・非名詞・未対応の読みを除外します。
一般名詞16,384、地名6,144、人名6,144、その他4,096を上限として
SHA-256の固定順位で抽出し、例示された6語を保持してから全体を重複除去します。
クラス間で同じローマ字になるため、最終語数は枠の合計より小さくなります。
これはビルド時の決定的な選別で、パスワード生成のシードとして使うものではありません。

ローマ字化はヘボン式の`shi`, `chi`, `tsu`, `fu`, 拗音・促音を基本とします。
ASCII制約に合わせ長音符`ー`は省略し、仮名で書かれた母音列は保持します
（例: `スーパー → supa`, `トウキョウ → toukyou`）。
東京・東芝・レッツノートは慣用表記に固定します。撥音のアポストロフィーは使いません。
完全な表記統一や全語の手動精査は行っておらず、珍しい固有名詞や上流由来の読み違いが含まれる可能性があります。
英語は3〜5文字で、記号を正規化し、日本語と同じローマ字の8語を除外しています。
実行時にも不正文字・空行・重複・日本語辞書の語数不足を拒否します。

再構築も標準ライブラリのみで可能です。ネットワークを使うのは明示的な取得コマンドだけです。

```bash
# 初回のビルド用原本取得（約67 MB、ネットワーク接続が必要）
python3 scripts/download_sources.py

# SHA-256を検証してオフラインで再生成
python3 scripts/build_dictionary.py

# 別ディレクトリに再生成して一致を確認する場合
python3 scripts/build_dictionary.py --output-dir .build/rebuilt
diff gen_pass/dictionary/japanese_romaji.txt .build/rebuilt/japanese_romaji.txt
diff gen_pass/dictionary/english.txt .build/rebuilt/english.txt
```

URL・バージョン・原本SHA-256は[sources.json](gen_pass/dictionary/sources.json)、
抽出件数は[build_stats.json](gen_pass/dictionary/build_stats.json)に記録しています。
原本ZIPのハッシュが一致しなければ再構築を拒否します。
原本は`.build/`に保存し、Gitの管理対象から除外しています。

## テスト

```bash
python3 -m unittest discover -s tests -v
```

標準の`unittest`でCLI、長さと禁止文字の組合せ、辞書検証、混合生成、
`--hr`の形式・長さ制限・区切り・エントロピー・長さ不足時の失敗、旧オプションの拒否、
全大文字化パターン、組合せ数と小規模な全列挙の一致、再抽選、
クリップボードへの入力・失敗・タイムアウトを確認します。
テスト中のコピーはモック化し、クリップボードを変更しません。
統計テストでCSPRNGの安全性を証明したと主張するものではありません。
配布アーカイブのライセンス・チェックサム、macOS / Linux用インストーラーの更新と失敗時の保護も検証します。
Windows用インストーラーは、Releaseビルド時に実際の配布ファイルを使って導入・更新・チェックサム不一致を確認します。

ビルド済みwheelを一時venvへインストールし、リポジトリ外からの実行・
辞書とライセンスの同梱・実行時依存がないことも検証できます。

```bash
python3 scripts/verify_install.py dist/gen_pass_romaji-0.1.0-py3-none-any.whl
```

各OSのクリップボード選択はモックで確認しています。
macOS以外の実際のクリップボード連携は、それぞれのOSのデスクトップ環境で確認してください。

実際のmacOS連携を確認する場合はCLIを実行して`pbpaste`で比較できます。
この操作は現在のクリップボードを上書きします。

## 残存リスク

パスワードはコンソールのスクロールバックとクリップボードに残ります。
ターミナルの出力記録・セッション履歴・クリップボード履歴アプリ・
端末間クリップボード同期などの設定によっては保存・同期される可能性があります。
本ツール自身は生成結果をファイルに保存せず、外部サービスに送信せず、
ネットワーク通信もしません。自動消去機能はありません。
端末や辞書が改ざんされている場合の安全性は保証できません。
生成値はサービスごとに独立して使用してください。

## ライセンス

ソースコードと独自ドキュメントは[MIT](LICENSE)。
辞書は別ライセンスです。[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)と
`licenses/`にSudachiDict / UniDic / NEologd / EFFの条件と帰属表示を同梱しています。
公開・再配布時にはこれらを維持してください。
