# Selenium Google Translate PDF Automator

Google翻訳（Web版）のドキュメント翻訳機能をSeleniumで自動化し、大容量のPDFファイルを一括翻訳するPythonツールです。

## 動作環境
* Python 3.10 以降
* Google Chrome（最新版）

## インストール

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

## コマンドライン引数

| 引数 | 説明 | デフォルト値 |
| :--- | :--- | :--- |
| `input_file` | 【必須】翻訳元PDFファイルのパス | - |
| `-c`, `--chunk-size` | 1回に翻訳するページ数 | `1` |
| `-o`, `--output-dir` | 翻訳済みファイルの保存先フォルダ | `./downloads` |

### 3\. Windows環境での実行

リリースページからexeをダウンロードします。

```bash
auto_translate_full.exe input.pdf -c 3 -o "C:\MyDocs"
```

## License

MIT License
