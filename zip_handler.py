# zip_handler.py
import os
import zipfile
import shutil
from datetime import datetime, timedelta
import threading
import time
from werkzeug.utils import secure_filename

class ZipHandler:
    def __init__(self, upload_folder='uploads', temp_zip_folder='temp_zips'):
        self.UPLOAD_FOLDER = upload_folder
        self.TEMP_ZIP_FOLDER = temp_zip_folder
        
        # ディレクトリの作成
        os.makedirs(self.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(self.TEMP_ZIP_FOLDER, exist_ok=True)
        
        # クリーンアップスレッドの開始
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_files, daemon=True)
        self.cleanup_thread.start()

    def _cleanup_old_files(self):
        """1時間以上前の一時ファイルを削除"""
        while True:
            try:
                current_time = datetime.now()
                if os.path.exists(self.UPLOAD_FOLDER):
                    for item in os.listdir(self.UPLOAD_FOLDER):
                        item_path = os.path.join(self.UPLOAD_FOLDER, item)
                        if os.path.isdir(item_path):
                            folder_time = datetime.fromtimestamp(os.path.getctime(item_path))
                            if current_time - folder_time > timedelta(hours=1):
                                shutil.rmtree(item_path, ignore_errors=True)

                if os.path.exists(self.TEMP_ZIP_FOLDER):
                    for item in os.listdir(self.TEMP_ZIP_FOLDER):
                        item_path = os.path.join(self.TEMP_ZIP_FOLDER, item)
                        if os.path.isfile(item_path):
                            file_time = datetime.fromtimestamp(os.path.getctime(item_path))
                            if current_time - file_time > timedelta(hours=1):
                                try:
                                    os.remove(item_path)
                                except:
                                    pass
            except:
                pass
            time.sleep(3600)  # 1時間ごとに実行

    def process_files(self, files):
        """ファイルを処理してZIPファイルを作成"""
        if not files:
            raise ValueError('ファイルが選択されていません')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_dir = os.path.join(self.UPLOAD_FOLDER, timestamp)
        os.makedirs(temp_dir, exist_ok=True)

        try:
            if len(files) <= 10:
                print("Creating uncompressed zip")
                zip_path = os.path.join(self.TEMP_ZIP_FOLDER, f'files_{timestamp}.zip')
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for file in files:
                        print(f"Processing file: {file.filename}")
                        filename = secure_filename(file.filename)
                        zipf.writestr(filename, file.read())
            else:
                print("Creating compressed zip")
                zip_path = os.path.join(self.TEMP_ZIP_FOLDER, f'compressed_{timestamp}.zip')
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file in files:
                        print(f"Processing file: {file.filename}")
                        filename = secure_filename(file.filename)
                        temp_path = os.path.join(temp_dir, filename)
                        file.save(temp_path)
                        zipf.write(temp_path, filename)

            return zip_path

        finally:
            # 一時ディレクトリの削除
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)