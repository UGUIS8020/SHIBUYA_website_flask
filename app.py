# app.py
from flask import Flask, render_template, send_from_directory,request, send_file, redirect
import os

from zip_handler import ZipHandler

app = Flask(__name__, static_url_path='/static')

# ZIPハンドラーのインスタンス作成
zip_handler_instance = ZipHandler()  # インスタンスを作成

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shibuya/hotetu/gikoubutu.html')
def gikoubutu():
    return render_template('gikoubutu.html')

@app.route('/shibuya/recruitment.html')
def recruitment():
    return render_template('recruitment.html')

@app.route('/shibuya/rootreplica.html')
def rootreplica():
    return render_template('rootreplica.html')

@app.route('/shibuya/gakukotu.html')
def gakukotu():
    return render_template('gakukotu.html')

@app.route('/colors.html', methods=['GET', 'POST'])
def colors():
    return render_template('colors.html')

@app.route('/zip_handler.html')
def zip_handler():
    return render_template('zip_handler.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if 'files[]' not in request.files:
        return 'ファイルがありません', 400
    
    files = request.files.getlist('files[]')
    if not files or files[0].filename == '':
        return 'ファイルが選択されていません', 400

    try:
        # インスタンスのメソッドを呼び出す
        zip_path = zip_handler_instance.process_files(files)
        return send_file(
            zip_path,
            as_attachment=True,
            download_name='files.zip'
        )
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return str(e), 500
    
@app.route('/upload-images', methods=['GET', 'POST'])
def upload_images():
    if 'images[]' not in request.files:
        return 'ファイルがありません', 400
    
    files = request.files.getlist('images[]')
    if not files or files[0].filename == '':
        return 'ファイルが選択されていません', 400

    try:
        # 画像処理関連のコードをここに書く
        # 例：保存先ディレクトリを作成したり、画像のリサイズなど
        
        # 成功したら結果ページにリダイレクトするか、成功メッセージを返す
        return '画像がアップロードされました', 200
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return str(e), 500

@app.route('/zoom')
def zoom_redirect():
    return redirect('https://us06web.zoom.us/j/84262814694')

if __name__ == '__main__':
    app.run(debug=True)


# Directory structure:
# /
# ├── app.py
# ├── static/
# │   ├── css/
# │   │   └── stylettop.css
# │   ├── images/
# │   │   ├── logo02.jpg
# │   │   └── ...
# │   └── shibuya/
# │       └── ... (all shibuya directory contents)
# └── templates/
#     ├── index.html
#     ├── base.html
#     └── ... (other HTML templates)