import os
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
from flask import Flask, request, redirect, url_for, render_template_string, flash

app = Flask(__name__)
app.secret_key = "your_secret_key"  # セッションのための秘密鍵

# Dropboxの設定
APP_KEY = "YOUR_APP_KEY"
APP_SECRET = "YOUR_APP_SECRET"
REDIRECT_URI = "http://localhost:5000/auth"
TOKEN_FILE = "token.txt"

# 認証フローのための状態
oauth_flow = None

@app.route('/')
def index():
    """
    メインページを表示。トークンが保存されていればファイルアップロードフォームを、
    なければDropbox認証リンクを表示
    """
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            token = f.read().strip()
        if token:
            return render_template_string('''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Dropboxファイルアップロード</title>
                    <style>
                        body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
                        .form-group { margin-bottom: 15px; }
                        label { display: block; margin-bottom: 5px; }
                        button { padding: 8px 15px; background: #0061ff; color: white; border: none; cursor: pointer; }
                        .success { color: green; }
                        .error { color: red; }
                    </style>
                </head>
                <body>
                    <h1>Dropboxファイルアップロード</h1>
                    {% if message %}
                        <p class="{{ message_class }}">{{ message }}</p>
                    {% endif %}
                    <form action="/upload" method="post" enctype="multipart/form-data">
                        <div class="form-group">
                            <label for="file">アップロードするファイル:</label>
                            <input type="file" id="file" name="file" required>
                        </div>
                        <div class="form-group">
                            <label for="path">Dropbox内の保存先パス (例: /uploads/myfile.txt):</label>
                            <input type="text" id="path" name="path" value="/uploads/" required>
                        </div>
                        <button type="submit">アップロード</button>
                    </form>
                </body>
                </html>
            ''', message=request.args.get('message'), message_class=request.args.get('message_class', ''))
    
    # トークンがない場合は認証リンクを表示
    auth_url = get_auth_url()
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dropbox認証</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
                .auth-button { padding: 10px 20px; background: #0061ff; color: white; text-decoration: none; display: inline-block; }
            </style>
        </head>
        <body>
            <h1>Dropbox APIとの連携</h1>
            <p>ファイルをアップロードするには、まずDropboxアカウントとの連携が必要です。</p>
            <a href="{{ auth_url }}" class="auth-button">Dropboxと連携する</a>
        </body>
        </html>
    ''', auth_url=auth_url)

@app.route('/auth')
def auth_callback():
    """Dropbox OAuth認証コールバック"""
    global oauth_flow
    auth_code = request.args.get('code')
    if not auth_code:
        return "認証コードがありません。"
    
    try:
        oauth_result = get_dropbox_auth_flow().finish(request.args)
        with open(TOKEN_FILE, 'w') as f:
            f.write(oauth_result.access_token)
        return redirect(url_for('index', message="認証に成功しました！", message_class="success"))
    except Exception as e:
        return f"認証エラー: {str(e)}"

@app.route('/upload', methods=['POST'])
def upload_file():
    """ファイルをDropboxにアップロード"""
    if 'file' not in request.files:
        return redirect(url_for('index', message="ファイルが選択されていません", message_class="error"))
    
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index', message="ファイルが選択されていません", message_class="error"))
    
    path = request.form.get('path', '/uploads/')
    if not path.startswith('/'):
        path = '/' + path
        
    # パスにファイル名を追加（パスがディレクトリで終わる場合）
    if path.endswith('/'):
        path = path + file.filename
    
    try:
        # トークンを読み込み
        with open(TOKEN_FILE, 'r') as f:
            access_token = f.read().strip()
        
        # Dropboxクライアントを初期化
        dbx = dropbox.Dropbox(access_token)
        
        # ユーザー情報を取得してアクセスをテスト
        dbx.users_get_current_account()
        
        # ファイルをアップロード
        file_content = file.read()
        result = dbx.files_upload(
            file_content,
            path,
            mode=WriteMode.overwrite
        )
        
        shared_link = dbx.sharing_create_shared_link_with_settings(path)
        return redirect(url_for('index', 
                               message=f"ファイル '{file.filename}' を '{path}' にアップロードしました！", 
                               message_class="success"))
        
    except AuthError:
        # 認証エラーの場合はトークンファイルを削除して再認証を促す
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        return redirect(url_for('index', message="認証の有効期限が切れています。再度認証してください。", message_class="error"))
    
    except ApiError as e:
        return redirect(url_for('index', message=f"APIエラー: {str(e)}", message_class="error"))
    
    except Exception as e:
        return redirect(url_for('index', message=f"エラー: {str(e)}", message_class="error"))

def get_auth_url():
    """Dropbox認証URLを取得"""
    return get_dropbox_auth_flow().start()

def get_dropbox_auth_flow():
    """Dropbox OAuth2認証フローを取得"""
    return dropbox.oauth.DropboxOAuth2Flow(
        APP_KEY,
        APP_SECRET,
        REDIRECT_URI,
        {},
        "dropbox-auth-csrf-token"
    )

if __name__ == '__main__':
    app.run(debug=True)