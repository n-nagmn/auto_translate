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
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from pypdf import PdfReader, PdfWriter
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from multiprocessing import freeze_support
import undetected_chromedriver as uc

def get_local_chrome_major_version():
    """
    インストールされているChromeのメジャーバージョン（例: 120, 121）を取得する
    """
    system_name = platform.system()
    version_str = ""

    try:
        if system_name == "Windows":
            try:
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

        if version_str:
            match = re.search(r"(\d+)\.\d+\.\d+\.\d+", version_str)
            if match:
                major_ver = int(match.group(1))
                return major_ver

    except Exception as e:
        pass # GUI側でログに出すためここでは黙殺
    
    return None

# --- PDF処理ロジック (GUI/CLI共通) ---

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
    
    major_version = get_local_chrome_major_version()
    
    if major_version:
        print(f"Chrome v{major_version} を検知しました。")
        driver = uc.Chrome(options=options, version_main=major_version)
    else:
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
    try:
        driver.get(url)
    except Exception as e:
        print(f"  ページロードエラー: {e}")
        return False

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
    print(f"全結合完了: {output_filename}")

# --- メイン処理ロジック (GUI用に分離) ---

def run_translation_process(input_pdf, chunk_size):
    input_pdf = os.path.abspath(input_pdf)
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
        split_files = split_pdf(input_pdf, chunk_size, split_dir)
        
        driver = init_driver(download_dir)
        
        for i, f in enumerate(split_files):
            current_page_download_dir = os.path.join(download_dir, f"{i:04d}")
            os.makedirs(current_page_download_dir, exist_ok=True)

            params = {'behavior': 'allow', 'downloadPath': current_page_download_dir}
            try:
                driver.execute_cdp_cmd('Page.setDownloadBehavior', params)
            except Exception as e:
                print(f"  CDPコマンド警告 (続行します): {e}")

            success = translate_on_web(driver, f, current_page_download_dir)
            if success:
                downloaded = glob.glob(os.path.join(current_page_download_dir, "*.pdf"))[0]
                new_name = os.path.join(download_dir, f"translated_{i:04d}.pdf")
                os.rename(downloaded, new_name)
            
            time.sleep(random.uniform(5, 8))

        merge_pdfs(download_dir, final_output_path)

    except Exception as e:
        print(f"\n予期せぬエラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("ブラウザを終了中...")
        if driver:
            try:
                driver.quit()
            except:
                pass
        if os.path.exists(base_work_dir):
            try:
                shutil.rmtree(base_work_dir)
            except:
                pass
        print("=== 全処理終了 ===")

# --- GUI 実装 ---

class TextRedirector(object):
    """標準出力をGUIのTextウィジェットにリダイレクトするためのクラス"""
    def __init__(self, queue):
        self.queue = queue

    def write(self, str):
        self.queue.put(str)

    def flush(self):
        pass

class TranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Auto Translator")
        self.root.geometry("600x500")
        self.root.resizable(True, True)

        # スタイル設定
        style = ttk.Style()
        style.theme_use('clam')

        # メインフレーム
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ファイル選択エリア
        file_frame = ttk.LabelFrame(main_frame, text="入力ファイル", padding="10")
        file_frame.pack(fill=tk.X, pady=5)

        self.file_path_var = tk.StringVar()
        self.entry_file = ttk.Entry(file_frame, textvariable=self.file_path_var)
        self.entry_file.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        btn_browse = ttk.Button(file_frame, text="参照...", command=self.browse_file)
        btn_browse.pack(side=tk.RIGHT)

        # 設定エリア
        setting_frame = ttk.Frame(main_frame)
        setting_frame.pack(fill=tk.X, pady=5)

        ttk.Label(setting_frame, text="分割単位(ページ):").pack(side=tk.LEFT)
        self.chunk_var = tk.IntVar(value=1)
        spin_chunk = ttk.Spinbox(setting_frame, from_=1, to=100, textvariable=self.chunk_var, width=5)
        spin_chunk.pack(side=tk.LEFT, padx=5)

        # 実行ボタン
        self.btn_run = ttk.Button(main_frame, text="翻訳開始", command=self.start_thread)
        self.btn_run.pack(pady=10, fill=tk.X)

        # ログ表示エリア
        log_frame = ttk.LabelFrame(main_frame, text="実行ログ", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.txt_log = scrolledtext.ScrolledText(log_frame, state='disabled', height=15)
        self.txt_log.pack(fill=tk.BOTH, expand=True)
        self.txt_log.tag_config('error', foreground='red')

        # ログ用キューと監視
        self.log_queue = queue.Queue()
        self.update_log()

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.file_path_var.set(file_path)

    def append_log(self, text):
        self.txt_log.configure(state='normal')
        self.txt_log.insert(tk.END, text)
        self.txt_log.see(tk.END)
        self.txt_log.configure(state='disabled')

    def update_log(self):
        """キューからログを取り出して表示"""
        while not self.log_queue.empty():
            try:
                text = self.log_queue.get_nowait()
                self.append_log(text)
            except queue.Empty:
                pass
        self.root.after(100, self.update_log)

    def start_thread(self):
        file_path = self.file_path_var.get()
        if not file_path:
            self.append_log("エラー: ファイルを選択してください。\n")
            return
        
        chunk_size = self.chunk_var.get()
        
        self.btn_run.config(state='disabled')
        self.entry_file.config(state='disabled')
        
        # スレッド開始
        thread = threading.Thread(target=self.run_process, args=(file_path, chunk_size))
        thread.daemon = True
        thread.start()

    def run_process(self, file_path, chunk_size):
        # 標準出力をジャックする
        original_stdout = sys.stdout
        sys.stdout = TextRedirector(self.log_queue)
        
        try:
            run_translation_process(file_path, chunk_size)
        except Exception as e:
            sys.stdout.write(f"重大なエラー: {e}\n")
        finally:
            # 元に戻す
            sys.stdout = original_stdout
            # UIを戻すためにメインスレッドへ通知（簡易的にログ経由でやるか、afterを使う）
            self.log_queue.put("\n--- 完了 ---\n")
            # ボタンの有効化はメインスレッドで行う必要があるため、今回は簡易的に何もしないか、
            # 完了通知を受けてユーザーが閉じる想定。再実行したい場合はリセット機能が必要だが、
            # ここではシンプルにするため終了を促す。
            # self.root.after(0, lambda: self.btn_run.config(state='normal')) を使うと安全に復帰可能
            # ただしTextRedirector外からの呼び出しなので注意
            pass
            
def main():
    freeze_support() # Windowsでのmultiprocessing用
    
    # コマンドライン引数がある場合はCLIとして動作
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser()
        parser.add_argument('input_file', help='翻訳するPDFファイル')
        parser.add_argument('--chunk-size', '-c', type=int, default=1)
        args = parser.parse_args()
        run_translation_process(args.input_file, args.chunk_size)
    else:
        # 引数がない場合はGUI起動
        root = tk.Tk()
        app = TranslatorApp(root)
        
        # 処理終了後にボタンを戻すためのトリッキーな実装（簡易版）
        def check_thread_alive():
            # アクティブなスレッド数を監視したり、フラグで管理するのが正攻法だが
            # ここではボタンの状態を監視して、ログに"--- 完了 ---"が来たら戻す処理などを入れるのが一般的
            # 今回はシンプルに「再実行したい場合はアプリを再起動」推奨、または以下でボタン復帰
            if "--- 完了 ---" in app.txt_log.get("1.0", tk.END):
                 app.btn_run.config(state='normal')
                 app.entry_file.config(state='normal')
            root.after(1000, check_thread_alive)
            
        # check_thread_alive() # 必要であれば有効化
        
        root.mainloop()

if __name__ == "__main__":
    main()