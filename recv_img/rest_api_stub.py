#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REST API スタブサーバー
画像中継サーバーからの画像を受信し、外部システムを模擬するAPIサーバー
"""

import os
import json
import time
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
import logging
from werkzeug.utils import secure_filename
import threading
import queue

app = Flask(__name__)
CORS(app)  # CORSを有効化

class ImageDatabase:
    """画像データベース管理クラス"""
    
    def __init__(self, db_path: str = "images.db"):
        """初期化"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """データベースの初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 画像テーブルの作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                content_type TEXT,
                source TEXT,
                client_ip TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                status TEXT DEFAULT 'received'
            )
        ''')
        
        # 統計テーブルの作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                total_images INTEGER DEFAULT 0,
                total_size INTEGER DEFAULT 0,
                unique_sources INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 認証トークンテーブルの作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_image(self, filename: str, file_path: str, file_size: int, 
                   content_type: str, source: str, client_ip: str, metadata: dict) -> int:
        """画像情報をデータベースに保存"""
        # ファイルハッシュを計算
        file_hash = self._calculate_file_hash(file_path)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO images (filename, file_path, file_size, file_hash, 
                               content_type, source, client_ip, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (filename, file_path, file_size, file_hash, content_type, 
              source, client_ip, json.dumps(metadata)))
        
        image_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return image_id
    
    def get_image(self, image_id: int) -> Optional[Dict]:
        """画像情報を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, file_path, file_size, file_hash, content_type,
                   source, client_ip, received_at, metadata, status
            FROM images WHERE id = ?
        ''', (image_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'filename': row[1],
                'file_path': row[2],
                'file_size': row[3],
                'file_hash': row[4],
                'content_type': row[5],
                'source': row[6],
                'client_ip': row[7],
                'received_at': row[8],
                'metadata': json.loads(row[9]) if row[9] else {},
                'status': row[10]
            }
        return None
    
    def list_images(self, limit: int = 100, offset: int = 0, 
                   source: str = None, date_from: str = None, date_to: str = None) -> List[Dict]:
        """画像一覧を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT id, filename, file_size, content_type, source, 
                   client_ip, received_at, status
            FROM images WHERE 1=1
        '''
        params = []
        
        if source:
            query += ' AND source = ?'
            params.append(source)
        
        if date_from:
            query += ' AND DATE(received_at) >= ?'
            params.append(date_from)
        
        if date_to:
            query += ' AND DATE(received_at) <= ?'
            params.append(date_to)
        
        query += ' ORDER BY received_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': row[0],
            'filename': row[1],
            'file_size': row[2],
            'content_type': row[3],
            'source': row[4],
            'client_ip': row[5],
            'received_at': row[6],
            'status': row[7]
        } for row in rows]
    
    def get_statistics(self, days: int = 7) -> Dict:
        """統計情報を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 期間内の統計
        date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT COUNT(*) as total_images,
                   SUM(file_size) as total_size,
                   COUNT(DISTINCT source) as unique_sources
            FROM images 
            WHERE DATE(received_at) >= ?
        ''', (date_from,))
        
        row = cursor.fetchone()
        
        # 今日の統計
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) as today_images,
                   SUM(file_size) as today_size
            FROM images 
            WHERE DATE(received_at) = ?
        ''', (today,))
        
        today_row = cursor.fetchone()
        
        conn.close()
        
        return {
            'period_days': days,
            'total_images': row[0] or 0,
            'total_size': row[1] or 0,
            'unique_sources': row[2] or 0,
            'today_images': today_row[0] or 0,
            'today_size': today_row[1] or 0
        }
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """ファイルのハッシュを計算"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def validate_token(self, token: str) -> bool:
        """認証トークンを検証"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM auth_tokens 
            WHERE token = ? AND is_active = 1 
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        ''', (token,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def create_token(self, description: str = None, expires_days: int = 30) -> str:
        """新しい認証トークンを作成"""
        token = hashlib.sha256(f"{time.time()}{os.urandom(16)}".encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        expires_at = None
        if expires_days > 0:
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        cursor.execute('''
            INSERT INTO auth_tokens (token, description, expires_at)
            VALUES (?, ?, ?)
        ''', (token, description, expires_at))
        
        conn.commit()
        conn.close()
        
        return token

class RESTAPIStub:
    """REST APIスタブサーバー"""
    
    def __init__(self, upload_dir: str = "received_images", 
                 max_file_size: int = 50 * 1024 * 1024):  # 50MB
        """初期化"""
        self.upload_dir = upload_dir
        self.max_file_size = max_file_size
        self.db = ImageDatabase()
        self.request_queue = queue.Queue()
        self.processing_thread = None
        
        # アップロードディレクトリの作成
        os.makedirs(upload_dir, exist_ok=True)
        
        # 処理スレッドの開始
        self.start_processing_thread()
        
        # ログ設定
        self.setup_logging()
    
    def setup_logging(self):
        """ログ設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('rest_api_stub.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def start_processing_thread(self):
        """画像処理スレッドを開始"""
        self.processing_thread = threading.Thread(target=self._process_images, daemon=True)
        self.processing_thread.start()
    
    def _process_images(self):
        """画像処理スレッド"""
        while True:
            try:
                # キューから画像処理タスクを取得
                task = self.request_queue.get(timeout=1)
                if task is None:  # 終了シグナル
                    break
                
                image_id, file_path = task
                self._process_single_image(image_id, file_path)
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"画像処理エラー: {e}")
    
    def _process_single_image(self, image_id: int, file_path: str):
        """単一画像の処理"""
        try:
            # ここで実際の画像処理をシミュレート
            # 例: 画像分析、OCR、異常検知など
            
            self.logger.info(f"画像処理中: ID={image_id}, ファイル={file_path}")
            
            # 処理時間をシミュレート（0.1-2秒）
            import random
            time.sleep(random.uniform(0.1, 2.0))
            
            # 処理完了をデータベースに記録
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE images SET status = 'processed' WHERE id = ?
            ''', (image_id,))
            conn.commit()
            conn.close()
            
            self.logger.info(f"画像処理完了: ID={image_id}")
            
        except Exception as e:
            self.logger.error(f"画像処理失敗: ID={image_id}, エラー={e}")
            
            # エラー状態を記録
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE images SET status = 'error' WHERE id = ?
            ''', (image_id,))
            conn.commit()
            conn.close()

# グローバルインスタンス
api_stub = RESTAPIStub()

def require_auth(f):
    """認証デコレータ"""
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            abort(401, description='認証が必要です')
        
        token = auth_header.split(' ')[1]
        if not api_stub.db.validate_token(token):
            abort(401, description='無効なトークンです')
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/v1/images', methods=['POST'])
def upload_image():
    """画像アップロードエンドポイント"""
    try:
        # ファイルの存在確認
        if 'image' not in request.files:
            return jsonify({'error': '画像ファイルが見つかりません'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        # ファイルサイズチェック
        file.seek(0, 2)  # ファイルの末尾に移動
        file_size = file.tell()
        file.seek(0)  # ファイルの先頭に戻る
        
        if file_size > api_stub.max_file_size:
            return jsonify({'error': f'ファイルサイズが大きすぎます（最大{api_stub.max_file_size}バイト）'}), 400
        
        # ファイル名の安全化
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        
        # ファイルの保存
        file_path = os.path.join(api_stub.upload_dir, filename)
        file.save(file_path)
        
        # メタデータの取得
        metadata = {}
        if 'metadata' in request.form:
            try:
                metadata = json.loads(request.form['metadata'])
            except json.JSONDecodeError:
                metadata = {'raw_metadata': request.form['metadata']}
        
        # 証拠保全パスの取得
        evidence_path = request.form.get('evidence_path', '')
        if evidence_path:
            metadata['evidence_path'] = evidence_path
        
        # データベースに保存
        image_id = api_stub.db.save_image(
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            content_type=file.content_type or 'application/octet-stream',
            source=request.form.get('source', 'unknown'),
            client_ip=request.remote_addr,
            metadata=metadata
        )
        
        # 処理キューに追加
        api_stub.request_queue.put((image_id, file_path))
        
        api_stub.logger.info(f"画像アップロード成功: ID={image_id}, ファイル={filename}")
        
        return jsonify({
            'success': True,
            'image_id': image_id,
            'filename': filename,
            'file_size': file_size,
            'received_at': datetime.now().isoformat()
        }), 201
        
    except Exception as e:
        api_stub.logger.error(f"画像アップロードエラー: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/images/<int:image_id>', methods=['GET'])
@require_auth
def get_image(image_id):
    """画像情報取得エンドポイント"""
    image = api_stub.db.get_image(image_id)
    if not image:
        return jsonify({'error': '画像が見つかりません'}), 404
    
    return jsonify(image)

@app.route('/api/v1/images/<int:image_id>/file', methods=['GET'])
@require_auth
def download_image(image_id):
    """画像ファイルダウンロードエンドポイント"""
    image = api_stub.db.get_image(image_id)
    if not image:
        return jsonify({'error': '画像が見つかりません'}), 404
    
    if not os.path.exists(image['file_path']):
        return jsonify({'error': 'ファイルが見つかりません'}), 404
    
    return send_file(image['file_path'], as_attachment=True, download_name=image['filename'])

@app.route('/api/v1/images', methods=['GET'])
@require_auth
def list_images():
    """画像一覧取得エンドポイント"""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    source = request.args.get('source')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    images = api_stub.db.list_images(limit, offset, source, date_from, date_to)
    
    return jsonify({
        'images': images,
        'total': len(images),
        'limit': limit,
        'offset': offset
    })

@app.route('/api/v1/statistics', methods=['GET'])
@require_auth
def get_statistics():
    """統計情報取得エンドポイント"""
    days = request.args.get('days', 7, type=int)
    stats = api_stub.db.get_statistics(days)
    
    return jsonify(stats)

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'database': 'connected',
        'upload_directory': api_stub.upload_dir
    })

@app.route('/api/v1/auth/token', methods=['POST'])
def create_token():
    """認証トークン作成エンドポイント"""
    data = request.get_json() or {}
    description = data.get('description', 'API Token')
    expires_days = data.get('expires_days', 30)
    
    token = api_stub.db.create_token(description, expires_days)
    
    return jsonify({
        'token': token,
        'description': description,
        'expires_days': expires_days,
        'created_at': datetime.now().isoformat()
    }), 201

@app.route('/api/v1/status', methods=['GET'])
def get_status():
    """サーバー状態取得エンドポイント"""
    # キューの状態を取得
    queue_size = api_stub.request_queue.qsize()
    
    # データベースの統計
    stats = api_stub.db.get_statistics(1)  # 今日の統計
    
    return jsonify({
        'server_status': 'running',
        'queue_size': queue_size,
        'processing_thread': api_stub.processing_thread.is_alive() if api_stub.processing_thread else False,
        'today_images': stats['today_images'],
        'today_size': stats['today_size'],
        'upload_directory': api_stub.upload_dir,
        'max_file_size': api_stub.max_file_size
    })

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='REST API スタブサーバー')
    parser.add_argument('--host', default='0.0.0.0', help='ホストアドレス')
    parser.add_argument('--port', type=int, default=5000, help='ポート番号')
    parser.add_argument('--debug', action='store_true', help='デバッグモード')
    parser.add_argument('--upload-dir', default='received_images', help='アップロードディレクトリ')
    parser.add_argument('--max-file-size', type=int, default=50*1024*1024, help='最大ファイルサイズ（バイト）')
    
    args = parser.parse_args()
    
    # グローバルインスタンスを再初期化
    api_stub = RESTAPIStub(args.upload_dir, args.max_file_size)
    
    print(f"REST API スタブサーバーを起動中...")
    print(f"ホスト: {args.host}:{args.port}")
    print(f"アップロードディレクトリ: {args.upload_dir}")
    print(f"最大ファイルサイズ: {args.max_file_size} バイト")
    print(f"API エンドポイント: http://{args.host}:{args.port}/api/v1/")
    print("Ctrl+Cで停止")
    
    app.run(host=args.host, port=args.port, debug=args.debug)
