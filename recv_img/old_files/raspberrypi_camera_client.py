#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Raspberry Piカメラ画像送信クライアント
カメラモジュールで画像を撮影し、中継サーバーに送信
"""

import os
import time
import json
import socket
import argparse
import configparser
from datetime import datetime
from typing import Optional
import logging

try:
    from picamera import PiCamera
    from picamera.exc import PiCameraError
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False
    print("警告: picameraライブラリがインストールされていません")

class ImageSender:
    """画像送信クラス"""
    
    def __init__(self, host: str, port: int, timeout: float = 30.0):
        """初期化"""
        self.host = host
        self.port = port
        self.timeout = timeout
    
    def send_image_data(self, image_data: bytes, metadata: Optional[dict] = None) -> bool:
        """画像データをサーバーに送信"""
        try:
            # メタデータを準備
            if metadata is None:
                metadata = {
                    'timestamp': time.time(),
                    'source': 'raspberrypi_camera'
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
            
            print(f"画像送信完了: {len(image_data)} bytes")
            
            client_socket.close()
            return True
            
        except Exception as e:
            print(f"送信エラー: {e}")
            return False

class RaspberryPiCameraClient:
    """Raspberry Piカメラクライアント"""
    
    def __init__(self, config_file: str = "raspberrypi_config.ini"):
        """初期化"""
        self.config = self._load_config(config_file)
        self.setup_logging()
        
        # サーバー設定
        self.server_host = self.config.get('server', 'host', fallback='localhost')
        self.server_port = self.config.getint('server', 'port', fallback=8080)
        self.timeout = self.config.getfloat('server', 'timeout', fallback=30.0)
        
        # カメラ設定
        self.camera_enabled = self.config.getboolean('raspberrypi', 'camera_enabled', fallback=False)
        self.camera_resolution = self.config.get('raspberrypi', 'camera_resolution', fallback='1920x1080')
        self.camera_framerate = self.config.getint('raspberrypi', 'camera_framerate', fallback=30)
        
        # 撮影設定
        self.save_dir = self.config.get('raspberrypi', 'save_dir', fallback='./camera_images')
        self.auto_save = self.config.getboolean('raspberrypi', 'auto_save', fallback=True)
        
        # 状態
        self.camera = None
        self.sender = ImageSender(self.server_host, self.server_port, self.timeout)
        self.photo_count = 0
        
        self.logger.info("Raspberry Piカメラクライアントを初期化しました")
        
        if self.camera_enabled and CAMERA_AVAILABLE:
            self._setup_camera()
    
    def _load_config(self, config_file: str) -> configparser.ConfigParser:
        """設定ファイルを読み込み"""
        config = configparser.ConfigParser()
        
        # デフォルト設定
        config['server'] = {
            'host': 'localhost',
            'port': '8080',
            'timeout': '30.0'
        }
        config['raspberrypi'] = {
            'camera_enabled': 'False',
            'camera_resolution': '1920x1080',
            'camera_framerate': '30',
            'save_dir': './camera_images',
            'auto_save': 'True'
        }
        config['logging'] = {
            'level': 'INFO',
            'file': 'raspberrypi_camera.log'
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
        log_file = self.config.get('logging', 'file', fallback='raspberrypi_camera.log')
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _setup_camera(self):
        """カメラの初期化"""
        try:
            self.camera = PiCamera()
            
            # 解像度の設定
            width, height = map(int, self.camera_resolution.split('x'))
            self.camera.resolution = (width, height)
            
            # フレームレートの設定
            self.camera.framerate = self.camera_framerate
            
            # カメラのウォームアップ
            self.camera.start_preview()
            time.sleep(2)
            self.camera.stop_preview()
            
            self.logger.info(f"カメラを初期化しました: {self.camera_resolution}, {self.camera_framerate}fps")
            
        except PiCameraError as e:
            self.logger.error(f"カメラ初期化エラー: {e}")
            self.camera = None
        except Exception as e:
            self.logger.error(f"予期しないエラー: {e}")
            self.camera = None
    
    def take_photo(self, save_to_file: bool = None) -> Optional[bytes]:
        """写真を撮影"""
        if not self.camera_enabled or not CAMERA_AVAILABLE:
            self.logger.error("カメラが有効になっていないか、picameraライブラリが利用できません")
            return None
        
        if self.camera is None:
            self.logger.error("カメラが初期化されていません")
            return None
        
        try:
            # 保存ディレクトリの作成
            if save_to_file is None:
                save_to_file = self.auto_save
            
            if save_to_file and not os.path.exists(self.save_dir):
                os.makedirs(self.save_dir)
            
            # 画像データをメモリに保存
            from io import BytesIO
            image_stream = BytesIO()
            
            # 写真を撮影
            self.camera.capture(image_stream, format='jpeg', quality=85)
            image_data = image_stream.getvalue()
            
            self.photo_count += 1
            self.logger.info(f"写真を撮影しました: {len(image_data)} bytes")
            
            # ファイルに保存（オプション）
            if save_to_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"photo_{timestamp}_{self.photo_count:04d}.jpg"
                filepath = os.path.join(self.save_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(image_data)
                
                self.logger.info(f"画像を保存しました: {filepath}")
            
            return image_data
            
        except Exception as e:
            self.logger.error(f"写真撮影エラー: {e}")
            return None
    
    def take_and_send_photo(self, save_to_file: bool = None) -> bool:
        """写真を撮影して送信"""
        image_data = self.take_photo(save_to_file)
        
        if image_data is None:
            return False
        
        # メタデータを準備
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'source': 'raspberrypi_camera',
            'photo_count': self.photo_count,
            'resolution': self.camera_resolution,
            'framerate': self.camera_framerate,
            'camera_model': 'Raspberry Pi Camera Module'
        }
        
        # 画像を送信
        success = self.sender.send_image_data(image_data, metadata)
        
        if success:
            self.logger.info(f"画像送信成功: 写真 #{self.photo_count}")
        else:
            self.logger.error(f"画像送信失敗: 写真 #{self.photo_count}")
        
        return success
    
    def continuous_capture(self, interval: float = 5.0, max_photos: int = None):
        """連続撮影"""
        self.logger.info(f"連続撮影を開始: 間隔 {interval}秒")
        
        photo_count = 0
        
        try:
            while True:
                if max_photos and photo_count >= max_photos:
                    self.logger.info(f"最大撮影数に達しました: {max_photos}")
                    break
                
                success = self.take_and_send_photo()
                if success:
                    photo_count += 1
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("連続撮影を停止しました")
    
    def cleanup(self):
        """クリーンアップ"""
        if self.camera:
            self.camera.close()
            self.logger.info("カメラを閉じました")

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='Raspberry Piカメラ画像送信クライアント')
    parser.add_argument('--config', default='raspberrypi_config.ini', help='設定ファイル')
    parser.add_argument('--host', help='サーバーホスト')
    parser.add_argument('--port', type=int, help='サーバーポート')
    parser.add_argument('--single', action='store_true', help='単発撮影')
    parser.add_argument('--continuous', action='store_true', help='連続撮影')
    parser.add_argument('--interval', type=float, default=5.0, help='撮影間隔（秒）')
    parser.add_argument('--max-photos', type=int, help='最大撮影数')
    parser.add_argument('--save', action='store_true', help='ファイルに保存')
    
    args = parser.parse_args()
    
    client = RaspberryPiCameraClient(args.config)
    
    # コマンドライン引数で設定を上書き
    if args.host:
        client.server_host = args.host
    if args.port:
        client.server_port = args.port
    
    try:
        if args.continuous:
            client.continuous_capture(args.interval, args.max_photos)
        else:
            # 単発撮影
            success = client.take_and_send_photo(args.save)
            if success:
                print("写真撮影・送信成功")
            else:
                print("写真撮影・送信失敗")
    
    except KeyboardInterrupt:
        print("\nCtrl+Cで停止しました")
    finally:
        client.cleanup()

if __name__ == "__main__":
    main()


