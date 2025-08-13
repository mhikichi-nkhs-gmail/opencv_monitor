#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画像中継サーバーのテスト用REST APIサーバー
画像を受信して保存・表示するテスト用API
"""

from flask import Flask, request, jsonify
import os
import json
from datetime import datetime
import argparse

app = Flask(__name__)

# 受信した画像の保存ディレクトリ
SAVE_DIR = "received_images"

class ImageReceiver:
    """画像受信処理クラス"""
    
    def __init__(self, save_dir: str = SAVE_DIR):
        """初期化"""
        self.save_dir = save_dir
        self.received_count = 0
        self.ensure_save_dir()
    
    def ensure_save_dir(self):
        """保存ディレクトリを作成"""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            print(f"保存ディレクトリを作成: {self.save_dir}")
    
    def save_image(self, image_file, metadata: dict) -> dict:
        """画像を保存"""
        try:
            # ファイル名を生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"image_{timestamp}.jpg"
            filepath = os.path.join(self.save_dir, filename)
            
            # 画像を保存
            image_file.save(filepath)
            
            # メタデータを保存
            metadata_file = filepath.replace('.jpg', '_metadata.json')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            self.received_count += 1
            
            result = {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'size': os.path.getsize(filepath),
                'received_count': self.received_count,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"画像保存成功: {filename} ({result['size']} bytes)")
            return result
            
        except Exception as e:
            print(f"画像保存エラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# グローバルインスタンス
receiver = ImageReceiver()

@app.route('/api/images', methods=['POST'])
def receive_image():
    """画像受信エンドポイント"""
    try:
        # 画像ファイルをチェック
        if 'image' not in request.files:
            return jsonify({'error': '画像ファイルが見つかりません'}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'error': '画像ファイルが選択されていません'}), 400
        
        # メタデータを取得
        metadata = {
            'timestamp': request.form.get('timestamp', ''),
            'client_address': request.form.get('client_address', ''),
            'image_size': request.form.get('image_size', ''),
            'metadata': request.form.get('metadata', '{}')
        }
        
        # 画像を保存
        result = receiver.save_image(image_file, metadata)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"API エラー: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """サーバー状態取得エンドポイント"""
    return jsonify({
        'status': 'running',
        'received_count': receiver.received_count,
        'save_dir': receiver.save_dir,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/images', methods=['GET'])
def list_images():
    """受信した画像一覧取得エンドポイント"""
    try:
        images = []
        if os.path.exists(receiver.save_dir):
            for filename in os.listdir(receiver.save_dir):
                if filename.endswith('.jpg'):
                    filepath = os.path.join(receiver.save_dir, filename)
                    metadata_file = filepath.replace('.jpg', '_metadata.json')
                    
                    image_info = {
                        'filename': filename,
                        'size': os.path.getsize(filepath),
                        'created': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                    }
                    
                    # メタデータファイルがあれば読み込み
                    if os.path.exists(metadata_file):
                        try:
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                image_info['metadata'] = json.load(f)
                        except:
                            pass
                    
                    images.append(image_info)
        
        return jsonify({
            'images': images,
            'count': len(images)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({'status': 'healthy'})

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='画像受信テスト用REST APIサーバー')
    parser.add_argument('--host', default='localhost', help='サーバーホスト')
    parser.add_argument('--port', type=int, default=3000, help='サーバーポート')
    parser.add_argument('--save-dir', default=SAVE_DIR, help='画像保存ディレクトリ')
    parser.add_argument('--debug', action='store_true', help='デバッグモード')
    
    args = parser.parse_args()
    
    # 保存ディレクトリを設定
    global receiver
    receiver = ImageReceiver(args.save_dir)
    
    print(f"画像受信APIサーバーを開始: {args.host}:{args.port}")
    print(f"画像保存先: {args.save_dir}")
    print("利用可能なエンドポイント:")
    print("  POST /api/images - 画像受信")
    print("  GET  /api/status - サーバー状態")
    print("  GET  /api/images - 画像一覧")
    print("  GET  /health - ヘルスチェック")
    
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        threaded=True
    )

if __name__ == "__main__":
    main()


