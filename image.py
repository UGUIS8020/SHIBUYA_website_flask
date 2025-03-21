import os
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from flask import Flask, request, render_template, send_file, url_for
import io
import base64

app = Flask(__name__)

# アップロードされたファイルの一時保存先
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_main_color_list_img(img_path, n_clusters=5, img_size=64, margin=15):
    """
    対象の画像のメインカラーを算出し、色を横並びにしたPILの画像を取得する。
    
    Parameters
    ----------
    img_path : str
        対象の画像のパス。
    n_clusters : int, optional
        抽出する色の数。デフォルトは5。
    img_size : int, optional
        出力画像の各色のサイズ。デフォルトは64。
    margin : int, optional
        出力画像の余白。デフォルトは15。
    
    Returns
    -------
    tiled_color_img : Image
        色を横並びにしたPILの画像。
    
    Raises
    ------
    FileNotFoundError
        画像ファイルが見つからない場合
    ValueError
        画像の読み込みに失敗した場合
    """
    try:
        cv2_img = cv2.imread(img_path)
        if cv2_img is None:
            raise ValueError(f"画像の読み込みに失敗しました: {img_path}")
            
        cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
        
        # メモリ使用量を削減するため、画像をリサイズ
        max_dimension = 1000
        height, width = cv2_img.shape[:2]
        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            cv2_img = cv2.resize(cv2_img, (new_width, new_height))
        
        cv2_img = cv2_img.reshape((cv2_img.shape[0] * cv2_img.shape[1], 3))
        
        cluster = KMeans(n_clusters=n_clusters, random_state=42)
        cluster.fit(X=cv2_img)
        cluster_centers_arr = cluster.cluster_centers_.astype(int, copy=False)
        
        width = img_size * n_clusters + margin * 2
        height = img_size + margin * 2
        
        tiled_color_img = Image.new(
            mode='RGB', size=(width, height), color='#333333')
        
        for i, rgb_arr in enumerate(cluster_centers_arr):
            color_hex_str = '#%02x%02x%02x' % tuple(rgb_arr)
            color_img = Image.new(
                mode='RGB', size=(img_size, img_size),
                color=color_hex_str)
            tiled_color_img.paste(
                im=color_img,
                box=(margin + img_size * i, margin))
        return tiled_color_img
        
    except FileNotFoundError:
        raise FileNotFoundError(f"画像ファイルが見つかりません: {img_path}")
    except Exception as e:
        raise ValueError(f"画像処理中にエラーが発生しました: {str(e)}")

def get_original_small_img(img_path, max_width=500):
    """
    元画像の小さくリサイズしたPILの画像を取得する。
    
    Parameters
    ----------
    img_path : str
        対象の画像のパス。
    max_width : int, optional
        最大幅。デフォルトは500px。
    
    Returns
    -------
    img : Image
        リサイズ後の画像。
        
    Raises
    ------
    FileNotFoundError
        画像ファイルが見つからない場合
    ValueError
        画像の読み込みに失敗した場合
    """
    try:
        img = Image.open(fp=img_path)
        
        # アスペクト比を保持しながらリサイズ
        if img.width > max_width:
            scale = max_width / img.width
            new_width = max_width
            new_height = int(img.height * scale)
            img = img.resize((new_width, new_height), Image.LANCZOS)
        
        return img
    except FileNotFoundError:
        raise FileNotFoundError(f"画像ファイルが見つかりません: {img_path}")
    except Exception as e:
        raise ValueError(f"画像処理中にエラーが発生しました: {str(e)}")

def process_image(img_path):
    """
    画像を処理して結果画像を生成する。
    
    Parameters
    ----------
    img_path : str
        対象の画像のパス。
    
    Returns
    -------
    result_img : Image
        処理結果の画像。
    """
    # 色の抽出
    color_img = get_main_color_list_img(img_path)
    
    # 元画像の縮小版
    small_img = get_original_small_img(img_path)
    
    # 結果画像の作成（元画像の下にカラーチャート）
    result_width = max(small_img.width, color_img.width)
    result_height = small_img.height + color_img.height + 20
    
    result_img = Image.new('RGB', (result_width, result_height), '#333333')
    
    # 元画像を中央に配置
    x_offset = (result_width - small_img.width) // 2
    result_img.paste(small_img, (x_offset, 0))
    
    # カラーチャートを下に配置
    x_offset = (result_width - color_img.width) // 2
    result_img.paste(color_img, (x_offset, small_img.height + 20))
    
    return result_img

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'ファイルがありません', 400
    
    file = request.files['file']
    if file.filename == '':
        return 'ファイルが選択されていません', 400
    
    if file:
        # ファイルを一時保存
        filename = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filename)
        
        try:
            # 画像を処理
            result_img = process_image(filename)
            
            # 結果画像をBase64エンコード
            buffered = io.BytesIO()
            result_img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # 一時ファイルを削除
            os.remove(filename)
            
            return render_template('result.html', image_data=img_str)
            
        except Exception as e:
            # エラーが発生した場合も一時ファイルを削除
            if os.path.exists(filename):
                os.remove(filename)
            return f'エラーが発生しました: {str(e)}', 500

@app.route('/colors.html', methods=['GET', 'POST'])
def colors():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'ファイルがありません', 400
        
        file = request.files['file']
        if file.filename == '':
            return 'ファイルが選択されていません', 400
        
        if file:
            # ファイルを一時保存
            filename = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filename)
            
            try:
                # 画像を処理
                result_img = process_image(filename)
                
                # 結果画像をBase64エンコード
                buffered = io.BytesIO()
                result_img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                # 一時ファイルを削除
                os.remove(filename)
                
                return render_template('colors.html', image_data=img_str)
                
            except Exception as e:
                # エラーが発生した場合も一時ファイルを削除
                if os.path.exists(filename):
                    os.remove(filename)
                return f'エラーが発生しました: {str(e)}', 500
    
    return render_template('colors.html')

if __name__ == '__main__':
    app.run(debug=True)