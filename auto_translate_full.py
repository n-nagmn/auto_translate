import os
import time
import glob
import random
import sys
import shutil
import argparse
import datetime
from pypdf import PdfReader, PdfWriter
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

def split_pdf(file_path, chunk_size, split_dir):
    if not os.path.exists(file_path):
        print(f"エラー: ファイル '{file_path}' が見つかりません。")
        sys.exit(1)

    reader = PdfReader(file_path)
    parts = []
    
    if not os.path.exists(split_dir):
        os.makedirs(split_dir)

    print(f"[{os.path.basename(file_path)}] 全{len(reader.pages)}ページを分割中...")
    for i in range(0, len(reader.pages), chunk_size):
        writer = PdfWriter()
        end_page = min(i + chunk_size, len(reader.pages))
        for j in range(i, end_page):
            writer.add_page(reader.pages[j])
        
        # 連番ファイル名
        part_filename = os.path.join(split_dir, f"part_{i:04d}.pdf")
        with open(part_filename, "wb") as f:
            writer.write(f)
        parts.append(os.path.abspath(part_filename))
    return parts

def init_driver(download_dir):
    options = uc.ChromeOptions()
    
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_settings.popups": 0,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    # 複数起動時にプロファイルが競合しないよう、ドライバ側で自動生成される一時プロファイルを使用
    driver = uc.Chrome(options=options)
    return driver

def wait_for_download(download_dir, timeout=60):
    """
    指定されたフォルダ内にPDFが生成され、書き込みが完了するのを待つ
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        files = glob.glob(os.path.join(download_dir, "*"))
        
        # .crdownload がある場合はダウンロード中
        if any(f.endswith(".crdownload") for f in files):
            time.sleep(1)
            continue
        
        # PDFファイルが存在し、サイズが0以上なら完了とみなす
        pdf_files = [f for f in files if f.endswith(".pdf")]
        if pdf_files:
            target_file = pdf_files[0] # 専用フォルダなので1つしかないはず
            if os.path.getsize(target_file) > 0:
                return target_file
        
        time.sleep(1)
    return None

def translate_on_web(driver, file_path, download_dir):
    url = "https://translate.google.co.jp/?sl=en&tl=ja&op=docs"
    
    # 前のセッションの影響を受けないようクリーンな状態でアクセス
    driver.get(url)

    wait = WebDriverWait(driver, 40)

    print(f"  処理中: {os.path.basename(file_path)}")
    time.sleep(random.uniform(2, 4))
    
    try:
        file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]')))
        file_input.send_keys(file_path)
    except Exception as e:
        print(f"  アップロード要素が見つかりませんでした: {e}")
        return False

    try:
        time.sleep(random.uniform(1, 2))
        translate_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[descendant::span[contains(text(), '翻訳') or contains(text(), 'Translate')]]")))
        translate_btn.click()
    except Exception:
        pass # 自動開始される場合があるため無視

    try:
        download_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[descendant::span[contains(text(), 'ダウンロード') or contains(text(), 'Download')]]")))
        # 少し長めに待ってからクリック（Bot検知回避）
        time.sleep(random.uniform(2, 3))
        download_btn.click()
        
        downloaded_file = wait_for_download(download_dir)
        if downloaded_file:
            print(f"  ダウンロード完了: {os.path.basename(downloaded_file)}")
            return True
        else:
            print("  ダウンロードタイムアウト")
            return False

    except Exception as e:
        print(f"  エラー: {e}")
        return False

def merge_pdfs(input_dir, output_filename):
    writer = PdfWriter()
    files = sorted(glob.glob(os.path.join(input_dir, "translated_*.pdf")))
    
    if not files:
        print("結合するファイルがありません。")
        return

    print(f"結合中 ({len(files)}ファイル)...")
    for pdf in files:
        try:
            reader = PdfReader(pdf)
            for page in reader.pages:
                writer.add_page(page)
        except Exception:
            pass

    with open(output_filename, "wb") as f:
        writer.write(f)
    print(f"★ 全結合完了: {output_filename}")

def main():
    parser = argparse.ArgumentParser(description='PDF翻訳スクリプト (並列実行対応版)')
    parser.add_argument('input_file', help='翻訳するPDFファイル')
    parser.add_argument('--chunk-size', '-c', type=int, default=1, help='分割ページ数')
    
    args = parser.parse_args()
    input_pdf = os.path.abspath(args.input_file)
    chunk_pages = args.chunk_size

    # 1. 実行IDの生成 (時刻 + ランダム値でユニーク化)
    run_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + "_" + str(random.randint(1000, 9999))
    
    # 作業用の一時フォルダ (実行ごとに完全に分離)
    # 実行場所のカレントディレクトリに一時フォルダを作る
    base_work_dir = os.path.join(os.getcwd(), f"temp_work_{run_id}")
    split_dir = os.path.join(base_work_dir, "split")
    download_dir = os.path.join(base_work_dir, "downloads")
    
    # フォルダ作成
    os.makedirs(split_dir, exist_ok=True)
    os.makedirs(download_dir, exist_ok=True)

    # 2. 出力ファイル名の決定 (元のファイル名_translated.pdf)
    file_dir = os.path.dirname(input_pdf)
    file_name = os.path.basename(input_pdf)
    name_root, ext = os.path.splitext(file_name)
    final_output_path = os.path.join(file_dir, f"{name_root}_translated{ext}")

    print(f"=== 処理開始: {file_name} (ID: {run_id}) ===")

    driver = None
    try:
        # PDF分割
        split_files = split_pdf(input_pdf, chunk_pages, split_dir)
        
        # Chrome起動 (この実行ID専用のダウンロードフォルダを指定)
        driver = init_driver(download_dir)
        
        for i, f in enumerate(split_files):
            # 今回のファイル用のサブフォルダを作る（Google翻訳のファイル名重複回避のため）
            # downloads/0001/ のようにページごとにフォルダを分ける
            current_page_download_dir = os.path.join(download_dir, f"{i:04d}")
            os.makedirs(current_page_download_dir, exist_ok=True)

            # ダウンロード先を動的に変更 (Chrome DevTools Protocolを使用)
            # これにより、ドライバを再起動せずにダウンロード先を変えられる
            params = {'behavior': 'allow', 'downloadPath': current_page_download_dir}
            driver.execute_cdp_cmd('Page.setDownloadBehavior', params)

            success = translate_on_web(driver, f, current_page_download_dir)
            
            if success:
                # ダウンロードされたファイルを取得して、結合用にリネーム・移動
                downloaded = glob.glob(os.path.join(current_page_download_dir, "*.pdf"))[0]
                new_name = os.path.join(download_dir, f"translated_{i:04d}.pdf")
                os.rename(downloaded, new_name)
            else:
                print(f"警告: パート {i} の翻訳失敗")

            # 待機
            time.sleep(random.uniform(5, 8))

        # 結合
        merge_pdfs(download_dir, final_output_path)

    except Exception as e:
        print(f"\n予期せぬエラーが発生しました: {e}")
    
    finally:
        if driver:
            driver.quit()
        
        # 一時フォルダのお掃除
        # エラーが起きても、成功しても、この実行IDのフォルダだけを消す
        if os.path.exists(base_work_dir):
            try:
                shutil.rmtree(base_work_dir)
                print("一時ファイルを削除しました。")
            except Exception as e:
                print(f"一時フォルダの削除に失敗 (手動で削除してください): {base_work_dir}")

if __name__ == "__main__":
    main()