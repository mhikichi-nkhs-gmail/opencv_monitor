#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画像中継サーバーのテストクライアント
画像をサーバーに送信するテスト用スクリプト
"""

import socket
import json
import time
import argparse
import os
from typing import Optional

class ImageClient:
    """画像送信クライアント"""
    
    def __init__(self, host: str, port: int):
        """初期化"""
        self.host = host
        self.port = port
    
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
                    'timestamp': time.time()
                }
            
            # ヘッダー情報を作成
            header = {
                'image_size': len(image_data),
                'format': 'jpeg',
                'metadata': metadata
            }
            
            # ソケット接続
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(30.0)
            client_socket.connect((self.host, self.port))
            
            print(f"サーバーに接続: {self.host}:{self.port}")
            
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
            
            # 応答を待機（オプション）
            try:
                response = client_socket.recv(1024)
                if response:
                    print(f"サーバー応答: {response.decode('utf-8')}")
            except socket.timeout:
                print("サーバーからの応答なし（タイムアウト）")
            
            client_socket.close()
            return True
            
        except Exception as e:
            print(f"送信エラー: {e}")
            return False
    
    def send_test_images(self, image_dir: str, count: int = 5, interval: float = 1.0):
        """テスト画像を連続送信"""
        if not os.path.exists(image_dir):
            print(f"エラー: ディレクトリが見つかりません: {image_dir}")
            return
        
        # 画像ファイルを検索
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        image_files = []
        
        for file in os.listdir(image_dir):
            if any(file.lower().endswith(ext) for ext in image_extensions):
                image_files.append(os.path.join(image_dir, file))
        
        if not image_files:
            print(f"エラー: 画像ファイルが見つかりません: {image_dir}")
            return
        
        print(f"見つかった画像ファイル: {len(image_files)}個")
        
        for i in range(count):
            if i >= len(image_files):
                break
            
            image_path = image_files[i % len(image_files)]
            print(f"\n--- テスト {i + 1}/{count} ---")
            
            metadata = {
                'test_id': i + 1,
                'filename': os.path.basename(image_path),
                'timestamp': time.time()
            }
            
            success = self.send_image(image_path, metadata)
            if success:
                print(f"テスト {i + 1} 成功")
            else:
                print(f"テスト {i + 1} 失敗")
            
            if i < count - 1:  # 最後のテスト以外は待機
                time.sleep(interval)

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='画像中継サーバーのテストクライアント')
    parser.add_argument('--host', default='localhost', help='サーバーホスト')
    parser.add_argument('--port', type=int, default=8080, help='サーバーポート')
    parser.add_argument('--image', help='送信する画像ファイルのパス')
    parser.add_argument('--dir', help='テスト用画像ディレクトリ')
    parser.add_argument('--count', type=int, default=5, help='テスト回数')
    parser.add_argument('--interval', type=float, default=1.0, help='送信間隔（秒）')
    
    args = parser.parse_args()
    
    client = ImageClient(args.host, args.port)
    
    if args.image:
        # 単一画像送信
        success = client.send_image(args.image)
        if success:
            print("画像送信成功")
        else:
            print("画像送信失敗")
    
    elif args.dir:
        # テスト画像連続送信
        client.send_test_images(args.dir, args.count, args.interval)
    
    else:
        # デフォルトテスト
        print("デフォルトテストを実行します")
        test_image = "test_image.jpg"
        
        # テスト用の小さな画像を作成
        try:
            from PIL import Image, ImageDraw
            
            # 100x100のテスト画像を作成
            img = Image.new('RGB', (100, 100), color='red')
            draw = ImageDraw.Draw(img)
            draw.text((10, 40), "Test", fill='white')
            img.save(test_image, 'JPEG')
            
            success = client.send_image(test_image)
            if success:
                print("テスト画像送信成功")
            else:
                print("テスト画像送信失敗")
            
            # テスト画像を削除
            os.remove(test_image)
            
        except ImportError:
            print("PILがインストールされていません。--imageオプションで画像ファイルを指定してください。")
        except Exception as e:
            print(f"テスト画像作成エラー: {e}")

if __name__ == "__main__":
    main()


