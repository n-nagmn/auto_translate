# Selenium Google Translate PDF Automator

Google翻訳（Web版）のドキュメント翻訳機能をSeleniumで自動化し、大容量のPDFファイルを一括翻訳するPythonツールです。

通常、Web版のGoogle翻訳には「10MB以内」「100ページ以内」といった制限がありますが、このツールはPDFを自動で分割・翻訳・結合することで、その制限を回避します。Bot検知回避（`undetected-chromedriver`）に対応しています。

## 特徴
* **大容量PDF完全対応**: ページ単位で分割して処理するため、ファイルサイズやページ数の制限を回避可能。
* **Bot検知回避**: `undetected-chromedriver` を使用し、GoogleのBot判定を回避しやすい構成。
* **自動結合**: 翻訳された分割ファイルを最終的に1つのPDFに結合。
* **CLI対応**: コマンドライン引数で分割単位や保存先を指定可能。

## 動作環境
* Python 3.10 以降
* Google Chrome（最新版）

## インストール

必要なライブラリをインストールします。
※ Python 3.12以降を使用している場合は、`setuptools` のインストールも必須です。

```bash
pip install selenium pypdf webdriver_manager undetected-chromedriver setuptools
````

## 使いかた

### 1\. 基本的な実行

翻訳したいPDFファイルのパスを指定して実行します。

```bash
python auto_translate_full.py input.pdf
```

  * デフォルトでは **1ページずつ** 分割・翻訳されます。
  * 完了すると `./downloads` フォルダに `final_translated.pdf` が生成されます。

### 2\. オプションを指定して実行

ページ分割数や保存先を変更する場合の例です。

**例：3ページごとに分割し、`C:\MyDocs` に保存する場合**

```bash
python auto_translate_full.py input.pdf -c 3 -o "C:\MyDocs"
```

### 3\. 実行中の操作（重要）

スクリプトを起動するとブラウザが立ち上がり、コンソールに以下のメッセージが表示されます。

```text
Enter キーを押して開始...
```

この状態で処理が一時停止します。翻訳の成功率を高めるため、**Enterキーを押す前にブラウザ上でGoogleアカウントにログインすること**を推奨します。ログイン後、コンソールでEnterキーを押すと自動処理が始まります。

## コマンドライン引数

| 引数 | 説明 | デフォルト値 |
| :--- | :--- | :--- |
| `input_file` | 【必須】翻訳元PDFファイルのパス | - |
| `-c`, `--chunk-size` | 1回に翻訳するページ数 | `1` |
| `-o`, `--output-dir` | 翻訳済みファイルの保存先フォルダ | `./downloads` |

## トラブルシューティング

  * **ModuleNotFoundError: No module named 'distutils'**
      * Python 3.12以降で発生します。`pip install setuptools` を実行してください。
  * **翻訳がスキップされる / 原文のまま保存される**
      * GoogleのBot検知に引っかかっている可能性があります。
      * 対策: `undetected-chromedriver` が機能するよう、ブラウザ起動後の**手動ログイン**を必ず行ってください。また、頻繁に実行しすぎないようにしてください。

## 免責事項 (Disclaimer)

  * 本ツールはGoogle翻訳のWebインターフェースを自動操作するものです。Googleの利用規約に抵触する可能性があります。
  * 過度なアクセス（短時間での大量翻訳）を行うと、IPアドレスが一時的にブロックされる場合があります。使用は自己責任で行ってください。
  * **教育・研究目的**での使用を想定しています。

## License

MIT License