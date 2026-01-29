import os
import time
import glob
import random
import sys
import shutil
import argparse
import datetime
import platform
import subprocess
import re
from pypdf import PdfReader, PdfWriter
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from multiprocessing import freeze_support
import undetected_chromedriver as uc

# Chromeバージョン自動取得ロジック
def get_local_chrome_major_version():
    """
    インストールされているChromeのメジャーバージョン（例: 120, 121）を取得する
    """
    system_name = platform.system()
    version_str = ""

    try:
        if system_name == "Windows":
            # Windows: レジストリまたはPowerShellから取得を試みる
            try:
                # 一般的なインストールパスを確認
                process = subprocess.Popen(
                    ['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                )
                stdout, _ = process.communicate()
                output = stdout.decode(errors='ignore')
                match = re.search(r"version\s+REG_SZ\s+([\d.]+)", output)
                if match:
                    version_str = match.group(1)
            except:
                pass
            
            # レジストリで見つからない場合の予備（wmic）
            if not version_str:
                process = subprocess.Popen(
                    ['wmic', 'datafile', 'where', 'name="C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe"', 'get', 'Version', '/value'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                )
                stdout, _ = process.communicate()
                version_str = stdout.decode(errors='ignore')

        elif system_name == "Darwin": # Mac
            process = subprocess.Popen(
                ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, _ = process.communicate()
            version_str = stdout.decode('utf-8')

        elif system_name == "Linux":
            process = subprocess.Popen(
                ['google-chrome', '--version'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, _ = process.communicate()
            version_str = stdout.decode('utf-8')

        # バージョン番号の抽出 (例: "Google Chrome 120.0.6099.109" -> 120)
        if version_str:
            match = re.search(r"(\d+)\.\d+\.\d+\.\d+", version_str)
            if match:
                major_ver = int(match.group(1))
                print(f"検知されたChromeバージョン: {major_ver}")
                return major_ver

    except Exception as e:
        print(f"Chromeバージョンの自動検知に失敗しました: {e}")
    
    return None
# --- ここまで追加 ---

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
    
    # バージョンを自動検知して指定する
    major_version = get_local_chrome_major_version()
    
    if major_version:
        # バージョンを指定して起動（これがエラー回避の肝です）
        driver = uc.Chrome(options=options, version_main=major_version)
    else:
        # 検知できなかった場合は運任せ（デフォルト動作）
        print("Chromeバージョンが特定できなかったため、自動ダウンロードを試みます...")
        driver = uc.Chrome(options=options)
        
    return driver

def wait_for_download(download_dir, timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        files = glob.glob(os.path.join(download_dir, "*"))
        if any(f.endswith(".crdownload") for f in files):
            time.sleep(1)
            continue
        pdf_files = [f for f in files if f.endswith(".pdf")]
        if pdf_files:
            target_file = pdf_files[0]
            if os.path.getsize(target_file) > 0:
                return target_file
        time.sleep(1)
    return None

def translate_on_web(driver, file_path, download_dir):
    url = "https://translate.google.co.jp/?sl=en&tl=ja&op=docs"
    driver.get(url)

    wait = WebDriverWait(driver, 40)
    print(f"  処理中: {os.path.basename(file_path)}")
    time.sleep(random.uniform(2, 4))
    
    try:
        file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]')))
        file_input.send_keys(file_path)
    except Exception:
        return False

    try:
        time.sleep(random.uniform(1, 2))
        translate_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[descendant::span[contains(text(), '翻訳') or contains(text(), 'Translate')]]")))
        translate_btn.click()
    except Exception:
        pass

    try:
        download_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[descendant::span[contains(text(), 'ダウンロード') or contains(text(), 'Download')]]")))
        time.sleep(random.uniform(2, 3))
        download_btn.click()
        
        downloaded_file = wait_for_download(download_dir)
        if downloaded_file:
            print(f"  ダウンロード完了: {os.path.basename(downloaded_file)}")
            return True
        else:
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
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='翻訳するPDFファイル')
    parser.add_argument('--chunk-size', '-c', type=int, default=1)
    args = parser.parse_args()
    
    input_pdf = os.path.abspath(args.input_file)
    run_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + "_" + str(random.randint(1000, 9999))
    base_work_dir = os.path.join(os.getcwd(), f"temp_work_{run_id}")
    split_dir = os.path.join(base_work_dir, "split")
    download_dir = os.path.join(base_work_dir, "downloads")
    
    os.makedirs(split_dir, exist_ok=True)
    os.makedirs(download_dir, exist_ok=True)

    file_dir = os.path.dirname(input_pdf)
    file_name = os.path.basename(input_pdf)
    name_root, ext = os.path.splitext(file_name)
    final_output_path = os.path.join(file_dir, f"{name_root}_translated{ext}")

    print(f"=== 処理開始: {file_name} (ID: {run_id}) ===")
    driver = None
    try:
        split_files = split_pdf(input_pdf, args.chunk_size, split_dir)
        
        # ドライバ起動 (ここでバージョン自動検知が動きます)
        driver = init_driver(download_dir)
        
        for i, f in enumerate(split_files):
            current_page_download_dir = os.path.join(download_dir, f"{i:04d}")
            os.makedirs(current_page_download_dir, exist_ok=True)

            params = {'behavior': 'allow', 'downloadPath': current_page_download_dir}
            driver.execute_cdp_cmd('Page.setDownloadBehavior', params)

            success = translate_on_web(driver, f, current_page_download_dir)
            if success:
                downloaded = glob.glob(os.path.join(current_page_download_dir, "*.pdf"))[0]
                new_name = os.path.join(download_dir, f"translated_{i:04d}.pdf")
                os.rename(downloaded, new_name)
            
            time.sleep(random.uniform(5, 8))

        merge_pdfs(download_dir, final_output_path)

    except Exception as e:
        print(f"\n予期せぬエラー: {e}")
    finally:
        if driver:
            driver.quit()
        if os.path.exists(base_work_dir):
            try:
                shutil.rmtree(base_work_dir)
            except:
                pass

if __name__ == "__main__":
    freeze_support()
    main()