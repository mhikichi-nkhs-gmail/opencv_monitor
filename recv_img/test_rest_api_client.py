#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REST API スタブサーバーテストクライアント
APIサーバーの機能をテストするためのクライアント
"""

import os
import json
import time
import requests
from datetime import datetime
from typing import Optional, Dict, List
import argparse

class RESTAPITestClient:
    """REST APIテストクライアント"""
    
    def __init__(self, base_url: str = "http://localhost:5000/api/v1"):
        """初期化"""
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
    
    def create_token(self, description: str = "Test Token") -> bool:
        """認証トークンを作成"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/token",
                json={"description": description, "expires_days": 30}
            )
            
            if response.status_code == 201:
                data = response.json()
                self.auth_token = data['token']
                print(f"認証トークンを作成しました: {self.auth_token[:20]}...")
                return True
            else:
                print(f"トークン作成失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"トークン作成エラー: {e}")
            return False
    
    def upload_image(self, image_path: str, source: str = "test_client") -> Optional[int]:
        """画像をアップロード"""
        if not os.path.exists(image_path):
            print(f"画像ファイルが見つかりません: {image_path}")
            return None
        
        try:
            # メタデータを準備
            metadata = {
                'filename': os.path.basename(image_path),
                'file_size': os.path.getsize(image_path),
                'upload_time': datetime.now().isoformat(),
                'source': source,
                'test_client': True
            }
            
            # ファイルとメタデータを送信
            with open(image_path, 'rb') as f:
                files = {'image': f}
                data = {
                    'source': source,
                    'metadata': json.dumps(metadata)
                }
                
                headers = {}
                if self.auth_token:
                    headers['Authorization'] = f'Bearer {self.auth_token}'
                
                response = self.session.post(
                    f"{self.base_url}/images",
                    files=files,
                    data=data,
                    headers=headers
                )
            
            if response.status_code == 201:
                data = response.json()
                print(f"画像アップロード成功: ID={data['image_id']}")
                return data['image_id']
            else:
                print(f"アップロード失敗: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"アップロードエラー: {e}")
            return None
    
    def get_image_info(self, image_id: int) -> Optional[Dict]:
        """画像情報を取得"""
        try:
            headers = {}
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            response = self.session.get(
                f"{self.base_url}/images/{image_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"画像情報取得失敗: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"画像情報取得エラー: {e}")
            return None
    
    def list_images(self, limit: int = 10, source: str = None) -> Optional[List[Dict]]:
        """画像一覧を取得"""
        try:
            params = {'limit': limit}
            if source:
                params['source'] = source
            
            headers = {}
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            response = self.session.get(
                f"{self.base_url}/images",
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['images']
            else:
                print(f"画像一覧取得失敗: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"画像一覧取得エラー: {e}")
            return None
    
    def get_statistics(self, days: int = 7) -> Optional[Dict]:
        """統計情報を取得"""
        try:
            params = {'days': days}
            headers = {}
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            response = self.session.get(
                f"{self.base_url}/statistics",
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"統計情報取得失敗: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"統計情報取得エラー: {e}")
            return None
    
    def health_check(self) -> bool:
        """ヘルスチェック"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"ヘルスチェック成功: {data['status']}")
                return True
            else:
                print(f"ヘルスチェック失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"ヘルスチェックエラー: {e}")
            return False
    
    def get_status(self) -> Optional[Dict]:
        """サーバー状態を取得"""
        try:
            response = self.session.get(f"{self.base_url}/status")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"状態取得失敗: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"状態取得エラー: {e}")
            return None
    
    def create_test_image(self, filename: str = "test_image.jpg", size: int = 1024) -> str:
        """テスト用画像を作成"""
        from PIL import Image, ImageDraw, ImageFont
        
        # テスト画像を作成
        img = Image.new('RGB', (200, 200), color='white')
        draw = ImageDraw.Draw(img)
        
        # テキストを描画
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        text = f"Test Image\n{datetime.now().strftime('%H:%M:%S')}"
        draw.text((10, 10), text, fill='black', font=font)
        
        # ファイルに保存
        img.save(filename)
        print(f"テスト画像を作成しました: {filename}")
        
        return filename

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='REST API スタブサーバーテストクライアント')
    parser.add_argument('--url', default='http://localhost:5000/api/v1', help='APIベースURL')
    parser.add_argument('--image', help='アップロードする画像ファイル')
    parser.add_argument('--create-token', action='store_true', help='認証トークンを作成')
    parser.add_argument('--upload', action='store_true', help='画像をアップロード')
    parser.add_argument('--list', action='store_true', help='画像一覧を取得')
    parser.add_argument('--stats', action='store_true', help='統計情報を取得')
    parser.add_argument('--health', action='store_true', help='ヘルスチェック')
    parser.add_argument('--status', action='store_true', help='サーバー状態を取得')
    parser.add_argument('--create-test-image', action='store_true', help='テスト画像を作成')
    parser.add_argument('--source', default='test_client', help='画像ソース')
    
    args = parser.parse_args()
    
    client = RESTAPITestClient(args.url)
    
    # ヘルスチェック
    if args.health or not any([args.create_token, args.upload, args.list, args.stats, args.status]):
        print("=== ヘルスチェック ===")
        if not client.health_check():
            print("サーバーに接続できません。サーバーが起動しているか確認してください。")
            return
    
    # 認証トークン作成
    if args.create_token:
        print("\n=== 認証トークン作成 ===")
        client.create_token()
    
    # テスト画像作成
    if args.create_test_image:
        print("\n=== テスト画像作成 ===")
        test_image = client.create_test_image()
        args.image = test_image
    
    # 画像アップロード
    if args.upload:
        print("\n=== 画像アップロード ===")
        if args.image:
            image_id = client.upload_image(args.image, args.source)
            if image_id:
                print(f"アップロードされた画像ID: {image_id}")
                
                # 画像情報を取得
                print("\n=== 画像情報 ===")
                image_info = client.get_image_info(image_id)
                if image_info:
                    print(json.dumps(image_info, indent=2, ensure_ascii=False))
        else:
            print("アップロードする画像ファイルを指定してください (--image)")
    
    # 画像一覧取得
    if args.list:
        print("\n=== 画像一覧 ===")
        images = client.list_images(limit=10, source=args.source)
        if images:
            for img in images:
                print(f"ID: {img['id']}, ファイル: {img['filename']}, サイズ: {img['file_size']}, 受信時刻: {img['received_at']}")
    
    # 統計情報取得
    if args.stats:
        print("\n=== 統計情報 ===")
        stats = client.get_statistics(7)
        if stats:
            print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # サーバー状態取得
    if args.status:
        print("\n=== サーバー状態 ===")
        status = client.get_status()
        if status:
            print(json.dumps(status, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
