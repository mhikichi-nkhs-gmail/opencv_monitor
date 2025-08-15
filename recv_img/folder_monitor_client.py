#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
フォルダ監視画像送信クライアント
指定されたフォルダを監視し、新しい画像ファイルを自動的に中継サーバーに送信
"""

import os
import time
import json
import socket
import threading
import argparse
import configparser
from datetime import datetime
from typing import Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

class ImageSender:
    """画像送信クラス"""
    
    def __init__(self, host: str, port: int, timeout: float = 30.0):
        """初期化"""
        self.host = host
        self.port = port
        self.timeout = timeout
    
    def send_image(self, image_path: str, metadata: Optional[dict] = None) -> bool:
        """画像をサーバーに送信"""
        try:
            # 画像ファイルを読み込み
            if not os.path.exists(image_path):
                print(f"エラー: 画像ファイルが見つかりません: {image_path}")
                return False
            
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # メタデータを準備
            if metadata is None:
                metadata = {
                    'filename': os.path.basename(image_path),
                    'file_size': len(image_data),
                    'timestamp': time.time(),
                    'source': 'folder_monitor'
                }
            
            # ヘッダー情報を作成
            header = {
                'image_size': len(image_data),
                'format': 'jpeg',
                'metadata': metadata
            }
            
            # ソケット接続
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(self.timeout)
            client_socket.connect((self.host, self.port))
            
            # ヘッダーサイズを送信
            header_json = json.dumps(header, ensure_ascii=False)
            header_data = header_json.encode('utf-8')
            header_size = len(header_data)
            
            client_socket.send(header_size.to_bytes(4, byteorder='big'))
            
            # ヘッダーデータを送信
            client_socket.send(header_data)
            
            # 画像データを送信
            client_socket.send(image_data)
            
            print(f"画像送信完了: {image_path} ({len(image_data)} bytes)")
            
            client_socket.close()
            return True
            
        except Exception as e:
            print(f"送信エラー {image_path}: {e}")
            return False

class FolderMonitorHandler(FileSystemEventHandler):
    """フォルダ監視ハンドラー"""
    
    def __init__(self, sender: ImageSender, image_extensions: Set[str], 
                 processed_files: Set[str], delay: float = 1.0):
        """初期化"""
        self.sender = sender
        self.image_extensions = image_extensions
        self.processed_files = processed_files
        self.delay = delay
        self.logger = logging.getLogger(__name__)
    
    def on_created(self, event):
        """ファイル作成イベント"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if self._is_image_file(file_path) and file_path not in self.processed_files:
            self.logger.info(f"新しい画像ファイルを検出: {file_path}")
            
            # ファイルの書き込み完了を待機
            time.sleep(self.delay)
            
            # ファイルが完全に書き込まれているかチェック
            if self._is_file_ready(file_path):
                self._process_image_file(file_path)
            else:
                self.logger.warning(f"ファイルがまだ書き込み中: {file_path}")
    
    def on_moved(self, event):
        """ファイル移動イベント"""
        if event.is_directory:
            return
        
        file_path = event.dest_path
        if self._is_image_file(file_path) and file_path not in self.processed_files:
            self.logger.info(f"移動された画像ファイルを検出: {file_path}")
            
            # ファイルの書き込み完了を待機
            time.sleep(self.delay)
            
            if self._is_file_ready(file_path):
                self._process_image_file(file_path)
    
    def _is_image_file(self, file_path: str) -> bool:
        """画像ファイルかどうかを判定"""
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.image_extensions
    
    def _is_file_ready(self, file_path: str) -> bool:
        """ファイルが書き込み完了しているかチェック"""
        try:
            # ファイルサイズが安定しているかチェック
            size1 = os.path.getsize(file_path)
            time.sleep(0.1)
            size2 = os.path.getsize(file_path)
            return size1 == size2 and size1 > 0
        except:
            return False
    
    def _process_image_file(self, file_path: str):
        """画像ファイルを処理"""
        try:
            # メタデータを準備
            metadata = {
                'filename': os.path.basename(file_path),
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'created_time': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                'modified_time': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                'source': 'folder_monitor',
                'detected_time': datetime.now().isoformat()
            }
            
            # 画像を送信
            success = self.sender.send_image(file_path, metadata)
            
            if success:
                self.processed_files.add(file_path)
                self.logger.info(f"画像送信成功: {file_path}")
            else:
                self.logger.error(f"画像送信失敗: {file_path}")
                
        except Exception as e:
            self.logger.error(f"画像処理エラー {file_path}: {e}")

class FolderMonitorClient:
    """フォルダ監視クライアント"""
    
    def __init__(self, config_file: str = "monitor_config.ini"):
        """初期化"""
        self.config = self._load_config(config_file)
        self.setup_logging()
        
        # サーバー設定
        self.server_host = self.config.get('server', 'host', fallback='localhost')
        self.server_port = self.config.getint('server', 'port', fallback=8080)
        self.timeout = self.config.getfloat('server', 'timeout', fallback=30.0)
        
        # 監視設定
        self.monitor_dir = self.config.get('monitor', 'directory')
        self.image_extensions = set(self.config.get('monitor', 'image_extensions', 
                                                   fallback='.jpg,.jpeg,.png,.bmp').split(','))
        self.delay = self.config.getfloat('monitor', 'delay', fallback=1.0)
        
        # 状態
        self.running = False
        self.observer = None
        self.sender = ImageSender(self.server_host, self.server_port, self.timeout)
        self.processed_files = set()
        
        self.logger.info("フォルダ監視クライアントを初期化しました")
    
    def _load_config(self, config_file: str) -> configparser.ConfigParser:
        """設定ファイルを読み込み"""
        config = configparser.ConfigParser()
        
        # デフォルト設定
        config['server'] = {
            'host': 'localhost',
            'port': '8080',
            'timeout': '30.0'
        }
        config['monitor'] = {
            'directory': './monitor_images',
            'image_extensions': '.jpg,.jpeg,.png,.bmp',
            'delay': '1.0'
        }
        config['logging'] = {
            'level': 'INFO',
            'file': 'folder_monitor.log'
        }
        
        # 設定ファイルが存在する場合は読み込み
        if os.path.exists(config_file):
            config.read(config_file, encoding='utf-8')
            print(f"設定ファイル {config_file} を読み込みました")
        else:
            # デフォルト設定をファイルに保存
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            print(f"デフォルト設定を {config_file} に保存しました")
        
        return config
    
    def setup_logging(self):
        """ログ設定"""
        log_level = self.config.get('logging', 'level', fallback='INFO')
        log_file = self.config.get('logging', 'file', fallback='folder_monitor.log')
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def start_monitoring(self):
        """監視を開始"""
        if not os.path.exists(self.monitor_dir):
            os.makedirs(self.monitor_dir)
            self.logger.info(f"監視ディレクトリを作成: {self.monitor_dir}")
        
        # 既存の画像ファイルを処理
        self._process_existing_files()
        
        # 監視を開始
        event_handler = FolderMonitorHandler(
            self.sender, 
            self.image_extensions, 
            self.processed_files, 
            self.delay
        )
        
        self.observer = Observer()
        self.observer.schedule(event_handler, self.monitor_dir, recursive=False)
        self.observer.start()
        
        self.running = True
        self.logger.info(f"フォルダ監視を開始: {self.monitor_dir}")
        self.logger.info(f"監視対象拡張子: {', '.join(self.image_extensions)}")
        self.logger.info(f"サーバー: {self.server_host}:{self.server_port}")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_monitoring()
    
    def _process_existing_files(self):
        """既存の画像ファイルを処理"""
        self.logger.info("既存の画像ファイルを処理中...")
        
        for filename in os.listdir(self.monitor_dir):
            file_path = os.path.join(self.monitor_dir, filename)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(filename.lower())
                if ext in self.image_extensions:
                    self.logger.info(f"既存ファイルを処理: {file_path}")
                    
                    metadata = {
                        'filename': filename,
                        'file_path': file_path,
                        'file_size': os.path.getsize(file_path),
                        'created_time': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                        'modified_time': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                        'source': 'folder_monitor_existing',
                        'detected_time': datetime.now().isoformat()
                    }
                    
                    success = self.sender.send_image(file_path, metadata)
                    if success:
                        self.processed_files.add(file_path)
                        self.logger.info(f"既存ファイル送信成功: {file_path}")
                    else:
                        self.logger.error(f"既存ファイル送信失敗: {file_path}")
    
    def stop_monitoring(self):
        """監視を停止"""
        self.logger.info("フォルダ監視を停止中...")
        self.running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.logger.info("フォルダ監視を停止しました")

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='フォルダ監視画像送信クライアント')
    parser.add_argument('--config', default='monitor_config.ini', help='設定ファイル')
    parser.add_argument('--dir', help='監視ディレクトリ')
    parser.add_argument('--host', help='サーバーホスト')
    parser.add_argument('--port', type=int, help='サーバーポート')
    
    args = parser.parse_args()
    
    client = FolderMonitorClient(args.config)
    
    # コマンドライン引数で設定を上書き
    if args.dir:
        client.monitor_dir = args.dir
    if args.host:
        client.server_host = args.host
    if args.port:
        client.server_port = args.port
    
    try:
        client.start_monitoring()
    except KeyboardInterrupt:
        print("\nCtrl+Cで停止しました")
        client.stop_monitoring()

if __name__ == "__main__":
    main()


