#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ET ROBOT CONTEST API スタブサーバー
実際のAPI仕様に準拠した画像アップロードサーバー
"""

import os
import json
import time
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import Flask, request, jsonify, abort
import logging
import threading
import queue

app = Flask(__name__)

class ETRoboconDatabase:
    """ET ROBOT CONTEST データベース管理クラス"""
    
    def __init__(self, db_path: str = "et_robocon.db"):
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
                team_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                content_type TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'received'
            )
        ''')
        
        # チーム統計テーブルの作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                competition_date DATE NOT NULL,
                image_count INTEGER DEFAULT 0,
                total_size INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team_id, competition_date)
            )
        ''')
        
        # 競技状態テーブルの作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competition_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # 初期競技状態を設定
        self._init_competition_status()
    
    def _init_competition_status(self):
        """競技状態の初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 現在の競技状態を確認
        cursor.execute('SELECT COUNT(*) FROM competition_status')
        if cursor.fetchone()[0] == 0:
            # 初期状態: 競技開始前
            cursor.execute('''
                INSERT INTO competition_status (status, start_time, end_time)
                VALUES ('waiting', NULL, NULL)
            ''')
            conn.commit()
        
        conn.close()
    
    def save_image(self, team_id: int, filename: str, file_path: str, 
                   file_size: int, content_type: str) -> int:
        """画像情報をデータベースに保存"""
        # ファイルハッシュを計算
        file_hash = self._calculate_file_hash(file_path)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO images (team_id, filename, file_path, file_size, file_hash, content_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (team_id, filename, file_path, file_size, file_hash, content_type))
        
        image_id = cursor.lastrowid
        
        # チーム統計を更新
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            INSERT OR REPLACE INTO team_statistics (team_id, competition_date, image_count, total_size)
            VALUES (
                ?,
                ?,
                (SELECT COUNT(*) FROM images WHERE team_id = ? AND DATE(received_at) = ?),
                (SELECT SUM(file_size) FROM images WHERE team_id = ? AND DATE(received_at) = ?)
            )
        ''', (team_id, today, team_id, today, team_id, today))
        
        conn.commit()
        conn.close()
        
        return image_id
    
    def get_team_image_count_today(self, team_id: int) -> int:
        """今日のチームの画像数を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) FROM images 
            WHERE team_id = ? AND DATE(received_at) = ?
        ''', (team_id, today))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def get_competition_status(self) -> str:
        """競技状態を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT status FROM competition_status ORDER BY id DESC LIMIT 1')
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else 'waiting'
    
    def set_competition_status(self, status: str):
        """競技状態を設定"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        
        if status == 'started':
            cursor.execute('''
                INSERT INTO competition_status (status, start_time, end_time)
                VALUES (?, ?, NULL)
            ''', (status, now))
        elif status == 'ended':
            cursor.execute('''
                INSERT INTO competition_status (status, start_time, end_time)
                VALUES (?, NULL, ?)
            ''', (status, now))
        else:
            cursor.execute('''
                INSERT INTO competition_status (status, start_time, end_time)
                VALUES (?, NULL, NULL)
            ''', (status,))
        
        conn.commit()
        conn.close()
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """ファイルのハッシュを計算"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_team_statistics(self, team_id: int, days: int = 7) -> Dict:
        """チーム統計情報を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_images,
                SUM(file_size) as total_size,
                COUNT(DISTINCT DATE(received_at)) as competition_days
            FROM images 
            WHERE team_id = ? AND DATE(received_at) >= ?
        ''', (team_id, date_from))
        
        row = cursor.fetchone()
        
        # 今日の統計
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) as today_images, SUM(file_size) as today_size
            FROM images 
            WHERE team_id = ? AND DATE(received_at) = ?
        ''', (team_id, today))
        
        today_row = cursor.fetchone()
        
        conn.close()
        
        return {
            'team_id': team_id,
            'period_days': days,
            'total_images': row[0] or 0,
            'total_size': row[1] or 0,
            'competition_days': row[2] or 0,
            'today_images': today_row[0] or 0,
            'today_size': today_row[1] or 0
        }

class ETRoboconAPIStub:
    """ET ROBOT CONTEST APIスタブサーバー"""
    
    def __init__(self, upload_dir: str = "et_robocon_images", 
                 max_file_size: int = 10 * 1024 * 1024):  # 10MB
        """初期化"""
        self.upload_dir = upload_dir
        self.max_file_size = max_file_size
        self.db = ETRoboconDatabase()
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
        # 既存のログ設定をクリア
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # 新しいログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('et_robocon_api.log', encoding='utf-8'),
                logging.StreamHandler()
            ],
            force=True
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
            
            # 処理時間をシミュレート（0.1-1秒）
            import random
            time.sleep(random.uniform(0.1, 1.0))
            
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
api_stub = ETRoboconAPIStub()

@app.route('/snap', methods=['POST'])
def upload_image():
    """画像アップロードエンドポイント (ET ROBOT CONTEST API仕様)"""
    try:
        # 競技状態のチェック
        competition_status = api_stub.db.get_competition_status()
        if competition_status not in ['started', 'waiting']:
            return jsonify({'error': 'Request not currently allowed'}), 403
        
        # Content-Typeのチェック
        content_type = request.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            return jsonify({'error': 'Unexpected content type'}), 400
        
        # リクエストボディのチェック
        if not request.data:
            return jsonify({'error': 'No data in request body'}), 400
        
        # チームIDの取得と検証
        team_id = request.args.get('id')
        if not team_id:
            return jsonify({'error': 'Invalid id format or range'}), 400
        
        try:
            team_id = int(team_id)
            if team_id <= 0:
                return jsonify({'error': 'Invalid id format or range'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid id format or range'}), 400
        
        # 今日の画像数制限チェック（2枚まで）
        today_count = api_stub.db.get_team_image_count_today(team_id)
        if today_count >= 2:
            return jsonify({'error': 'Up to 2 images can be accepted'}), 429
        
        # ファイルサイズチェック
        if len(request.data) > api_stub.max_file_size:
            return jsonify({'error': 'File size too large'}), 400
        
        # ファイル名の生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"team{team_id}_{timestamp}.jpg"
        
        # ファイルの保存
        file_path = os.path.join(api_stub.upload_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(request.data)
        
        # データベースに保存
        image_id = api_stub.db.save_image(
            team_id=team_id,
            filename=filename,
            file_path=file_path,
            file_size=len(request.data),
            content_type=content_type
        )
        
        # 処理キューに追加
        api_stub.request_queue.put((image_id, file_path))
        
        api_stub.logger.info(f"画像アップロード成功: チーム{team_id}, ID={image_id}, ファイル={filename}")
        
        return jsonify({
            'success': True,
            'image_id': image_id,
            'team_id': team_id,
            'filename': filename,
            'file_size': len(request.data),
            'received_at': datetime.now().isoformat()
        }), 201
        
    except Exception as e:
        api_stub.logger.error(f"画像アップロードエラー: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """サーバー状態取得エンドポイント"""
    competition_status = api_stub.db.get_competition_status()
    queue_size = api_stub.request_queue.qsize()
    
    return jsonify({
        'server_status': 'running',
        'competition_status': competition_status,
        'queue_size': queue_size,
        'upload_directory': api_stub.upload_dir,
        'max_file_size': api_stub.max_file_size
    })

@app.route('/admin/competition/start', methods=['POST'])
def start_competition():
    """競技開始エンドポイント（管理者用）"""
    try:
        api_stub.db.set_competition_status('started')
        api_stub.logger.info("競技を開始しました")
        return jsonify({'status': 'started', 'message': 'Competition started'}), 200
    except Exception as e:
        api_stub.logger.error(f"競技開始エラー: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/competition/end', methods=['POST'])
def end_competition():
    """競技終了エンドポイント（管理者用）"""
    try:
        api_stub.db.set_competition_status('ended')
        api_stub.logger.info("競技を終了しました")
        return jsonify({'status': 'ended', 'message': 'Competition ended'}), 200
    except Exception as e:
        api_stub.logger.error(f"競技終了エラー: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/competition/reset', methods=['POST'])
def reset_competition():
    """競技リセットエンドポイント（管理者用）"""
    try:
        api_stub.db.set_competition_status('waiting')
        api_stub.logger.info("競技をリセットしました")
        return jsonify({'status': 'waiting', 'message': 'Competition reset'}), 200
    except Exception as e:
        api_stub.logger.error(f"競技リセットエラー: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/team/<int:team_id>/statistics', methods=['GET'])
def get_team_statistics(team_id):
    """チーム統計情報取得エンドポイント（管理者用）"""
    try:
        days = request.args.get('days', 7, type=int)
        stats = api_stub.db.get_team_statistics(team_id, days)
        return jsonify(stats), 200
    except Exception as e:
        api_stub.logger.error(f"統計情報取得エラー: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'database': 'connected',
        'competition_status': api_stub.db.get_competition_status()
    })

if __name__ == '__main__':
    import argparse
    import locale
    import sys
    
    # ロケール設定（日本語対応）
    try:
        if sys.platform.startswith('win'):
            locale.setlocale(locale.LC_ALL, 'Japanese_Japan.932')
        else:
            locale.setlocale(locale.LC_ALL, 'ja_JP.UTF-8')
    except:
        pass  # ロケール設定に失敗しても続行
    
    parser = argparse.ArgumentParser(description='ET ROBOT CONTEST API スタブサーバー')
    parser.add_argument('--host', default='localhost', help='ホストアドレス')
    parser.add_argument('--port', type=int, default=5000, help='ポート番号')
    parser.add_argument('--debug', action='store_true', help='デバッグモード')
    parser.add_argument('--upload-dir', default='et_robocon_images', help='アップロードディレクトリ')
    parser.add_argument('--max-file-size', type=int, default=10*1024*1024, help='最大ファイルサイズ（バイト）')
    
    args = parser.parse_args()
    
    # グローバルインスタンスを再初期化
    api_stub = ETRoboconAPIStub(args.upload_dir, args.max_file_size)
    
    print(f"ET ROBOT CONTEST API スタブサーバーを起動中...")
    print(f"ホスト: {args.host}:{args.port}")
    print(f"アップロードディレクトリ: {args.upload_dir}")
    print(f"最大ファイルサイズ: {args.max_file_size} バイト")
    print(f"API エンドポイント: http://{args.host}:{args.port}/snap")
    print("Ctrl+Cで停止")
    
    app.run(host=args.host, port=args.port, debug=args.debug)
