import os
import time
import glob
import random
import sys
import argparse
from pypdf import PdfReader, PdfWriter
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

def split_pdf(file_path, chunk_size):
    if not os.path.exists(file_path):
        print(f"エラー: ファイル '{file_path}' が見つかりません。")
        sys.exit(1)

    reader = PdfReader(file_path)
    parts = []
    temp_dir = "temp_split"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    print(f"[{file_path}] 全{len(reader.pages)}ページを分割します (1ファイル{chunk_size}ページ)...")
    for i in range(0, len(reader.pages), chunk_size):
        writer = PdfWriter()
        end_page = min(i + chunk_size, len(reader.pages))
        for j in range(i, end_page):
            writer.add_page(reader.pages[j])
        part_filename = os.path.join(temp_dir, f"part_{i:04d}.pdf")
        with open(part_filename, "wb") as f:
            writer.write(f)
        parts.append(os.path.abspath(part_filename))
    return parts

def init_driver(download_dir):
    options = uc.ChromeOptions()
    
    # ダウンロード設定
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_settings.popups": 0,
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = uc.Chrome(options=options)
    return driver

def translate_on_web(driver, file_path):
    url = "https://translate.google.co.jp/?sl=en&tl=ja&op=docs"
    driver.get(url)

    wait = WebDriverWait(driver, 30)

    # 1. ファイルアップロード
    time.sleep(random.uniform(2, 4))
    
    file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]')))
    file_input.send_keys(file_path)
    print(f"  アップロード中: {os.path.basename(file_path)}")

    # 2. 翻訳ボタンクリック
    try:
        time.sleep(random.uniform(1, 3))
        translate_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[descendant::span[contains(text(), '翻訳') or contains(text(), 'Translate')]]")))
        translate_btn.click()
    except Exception as e:
        print("  (翻訳ボタンが見つからない、または自動開始されました)")

    # 3. ダウンロードボタン待機
    print("  翻訳処理待ち...")
    try:
        download_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[descendant::span[contains(text(), 'ダウンロード') or contains(text(), 'Download')]]")))
        time.sleep(random.uniform(1.5, 3.5))
        download_btn.click()
        print("  ダウンロード開始")
    except Exception as e:
        print(f"  ダウンロードボタンの検出に失敗しました: {e}")
        return

    time.sleep(10) 

def merge_pdfs(input_dir, output_filename):
    writer = PdfWriter()
    files = sorted(glob.glob(os.path.join(input_dir, "*.pdf")))
    if not files:
        print("結合するファイルが見つかりません。")
        return

    print("ファイルを結合しています...")
    for pdf in files:
        try:
            reader = PdfReader(pdf)
            for page in reader.pages:
                writer.add_page(page)
        except Exception as e:
            print(f"  読み込みエラー: {pdf} -> {e}")

    with open(output_filename, "wb") as f:
        writer.write(f)
    print(f"完了！: {output_filename}")

def main():
    parser = argparse.ArgumentParser(description='Google翻訳自動化スクリプト')
    
    # 必須引数: 入力ファイル
    parser.add_argument('input_file', help='翻訳するPDFファイルのパス')
    
    # オプション引数: 分割ページ数 (デフォルト: 1)
    parser.add_argument('--chunk-size', '-c', type=int, default=1, 
                        help='1回に翻訳するページ数 (デフォルト: 1)')
    
    # オプション引数: 保存先フォルダ (デフォルト: ./downloads)
    parser.add_argument('--output-dir', '-o', type=str, default=os.path.join(os.getcwd(), "downloads"),
                        help='ダウンロード先のフォルダパス (デフォルト: ./downloads)')
    
    args = parser.parse_args()
    
    input_pdf = args.input_file
    chunk_pages = args.chunk_size
    download_dir = os.path.abspath(args.output_dir)

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    # 分割実行
    split_files = split_pdf(input_pdf, chunk_pages)
    
    driver = init_driver(download_dir)
    
    try:
        print(f"保存先: {download_dir}")
        
        for f in split_files:
            try:
                translate_on_web(driver, f)
            except Exception as e:
                print(f"  エラー発生 ({os.path.basename(f)}): {e}")
                continue
            
    finally:
        driver.quit()
        import shutil
        if os.path.exists("temp_split"):
            shutil.rmtree("temp_split")

    # 結合実行
    merge_pdfs(download_dir, "final_translated.pdf")

if __name__ == "__main__":
    main()