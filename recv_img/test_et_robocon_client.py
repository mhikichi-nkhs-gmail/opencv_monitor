#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ET ROBOT CONTEST API テストクライアント
実際のAPI仕様に準拠したテストクライアント
"""

import os
import json
import time
import requests
from datetime import datetime
from typing import Optional, Dict
import argparse

class ETRoboconTestClient:
    """ET ROBOT CONTEST APIテストクライアント"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """初期化"""
        self.base_url = base_url
        self.session = requests.Session()
    
    def upload_image(self, image_path: str, team_id: int) -> Optional[Dict]:
        """画像をアップロード（ET ROBOT CONTEST API仕様）"""
        if not os.path.exists(image_path):
            print(f"画像ファイルが見つかりません: {image_path}")
            return None
        
        try:
            # 画像ファイルを読み込み
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Content-Typeを設定
            headers = {
                'Content-Type': 'image/jpeg'
            }
            
            # パラメータを設定
            params = {
                'id': team_id
            }
            
            # APIに送信
            response = self.session.post(
                f"{self.base_url}/snap",
                data=image_data,
                headers=headers,
                params=params
            )
            
            if response.status_code == 201:
                data = response.json()
                print(f"画像アップロード成功: チーム{team_id}, ID={data['image_id']}")
                return data
            else:
                print(f"アップロード失敗: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"アップロードエラー: {e}")
            return None
    
    def health_check(self) -> bool:
        """ヘルスチェック"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"ヘルスチェック成功: {data['status']}")
                print(f"競技状態: {data['competition_status']}")
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
    
    def start_competition(self) -> bool:
        """競技開始（管理者用）"""
        try:
            response = self.session.post(f"{self.base_url}/admin/competition/start")
            
            if response.status_code == 200:
                data = response.json()
                print(f"競技開始成功: {data['status']}")
                return True
            else:
                print(f"競技開始失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"競技開始エラー: {e}")
            return False
    
    def end_competition(self) -> bool:
        """競技終了（管理者用）"""
        try:
            response = self.session.post(f"{self.base_url}/admin/competition/end")
            
            if response.status_code == 200:
                data = response.json()
                print(f"競技終了成功: {data['status']}")
                return True
            else:
                print(f"競技終了失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"競技終了エラー: {e}")
            return False
    
    def reset_competition(self) -> bool:
        """競技リセット（管理者用）"""
        try:
            response = self.session.post(f"{self.base_url}/admin/competition/reset")
            
            if response.status_code == 200:
                data = response.json()
                print(f"競技リセット成功: {data['status']}")
                return True
            else:
                print(f"競技リセット失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"競技リセットエラー: {e}")
            return False
    
    def get_team_statistics(self, team_id: int, days: int = 7) -> Optional[Dict]:
        """チーム統計情報を取得（管理者用）"""
        try:
            params = {'days': days}
            response = self.session.get(
                f"{self.base_url}/admin/team/{team_id}/statistics",
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"統計情報取得失敗: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"統計情報取得エラー: {e}")
            return None
    
    def create_test_image(self, filename: str = "test_image.jpg") -> str:
        """テスト用画像を作成"""
        from PIL import Image, ImageDraw, ImageFont
        
        # テスト画像を作成
        img = Image.new('RGB', (640, 480), color='white')
        draw = ImageDraw.Draw(img)
        
        # テキストを描画
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        text = f"ET ROBOT CONTEST\nTest Image\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        draw.text((10, 10), text, fill='black', font=font)
        
        # ファイルに保存
        img.save(filename, 'JPEG', quality=85)
        print(f"テスト画像を作成しました: {filename}")
        
        return filename
    
    def simulate_competition(self, team_id: int, image_count: int = 2):
        """競技シミュレーション"""
        print(f"=== チーム{team_id}の競技シミュレーション開始 ===")
        
        # 競技開始
        print("1. 競技開始")
        if not self.start_competition():
            print("競技開始に失敗しました")
            return
        
        time.sleep(1)
        
        # 画像アップロード
        print(f"2. 画像アップロード（最大{image_count}枚）")
        for i in range(image_count):
            print(f"   {i+1}枚目の画像をアップロード中...")
            
            # テスト画像を作成
            test_image = self.create_test_image(f"test_team{team_id}_{i+1}.jpg")
            
            # アップロード
            result = self.upload_image(test_image, team_id)
            if result:
                print(f"   ✓ 成功: ID={result['image_id']}")
            else:
                print(f"   ✗ 失敗")
            
            time.sleep(0.5)
        
        # 3枚目を試行（429エラーを確認）
        print("3. 3枚目の画像を試行（制限確認）")
        test_image = self.create_test_image(f"test_team{team_id}_3rd.jpg")
        result = self.upload_image(test_image, team_id)
        if not result:
            print("   ✓ 期待通り429エラー（制限確認）")
        else:
            print("   ✗ 予期しない成功")
        
        # 統計情報取得
        print("4. 統計情報取得")
        stats = self.get_team_statistics(team_id)
        if stats:
            print(f"   今日の画像数: {stats['today_images']}")
            print(f"   今日のサイズ: {stats['today_size']} bytes")
        
        # 競技終了
        print("5. 競技終了")
        self.end_competition()
        
        print("=== シミュレーション完了 ===")

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='ET ROBOT CONTEST API テストクライアント')
    parser.add_argument('--url', default='http://localhost:5000', help='APIベースURL')
    parser.add_argument('--image', help='アップロードする画像ファイル')
    parser.add_argument('--team-id', type=int, default=1, help='チームID')
    parser.add_argument('--upload', action='store_true', help='画像をアップロード')
    parser.add_argument('--health', action='store_true', help='ヘルスチェック')
    parser.add_argument('--status', action='store_true', help='サーバー状態を取得')
    parser.add_argument('--start-competition', action='store_true', help='競技開始')
    parser.add_argument('--end-competition', action='store_true', help='競技終了')
    parser.add_argument('--reset-competition', action='store_true', help='競技リセット')
    parser.add_argument('--stats', action='store_true', help='統計情報を取得')
    parser.add_argument('--simulate', action='store_true', help='競技シミュレーション')
    parser.add_argument('--create-test-image', action='store_true', help='テスト画像を作成')
    
    args = parser.parse_args()
    
    client = ETRoboconTestClient(args.url)
    
    # ヘルスチェック
    if args.health or not any([args.upload, args.status, args.start_competition, 
                              args.end_competition, args.reset_competition, args.stats, args.simulate]):
        print("=== ヘルスチェック ===")
        if not client.health_check():
            print("サーバーに接続できません。サーバーが起動しているか確認してください。")
            return
    
    # テスト画像作成
    if args.create_test_image:
        print("\n=== テスト画像作成 ===")
        test_image = client.create_test_image()
        args.image = test_image
    
    # 画像アップロード
    if args.upload:
        print("\n=== 画像アップロード ===")
        if args.image:
            result = client.upload_image(args.image, args.team_id)
            if result:
                print(f"アップロード成功: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print("アップロードする画像ファイルを指定してください (--image)")
    
    # サーバー状態取得
    if args.status:
        print("\n=== サーバー状態 ===")
        status = client.get_status()
        if status:
            print(json.dumps(status, indent=2, ensure_ascii=False))
    
    # 競技開始
    if args.start_competition:
        print("\n=== 競技開始 ===")
        client.start_competition()
    
    # 競技終了
    if args.end_competition:
        print("\n=== 競技終了 ===")
        client.end_competition()
    
    # 競技リセット
    if args.reset_competition:
        print("\n=== 競技リセット ===")
        client.reset_competition()
    
    # 統計情報取得
    if args.stats:
        print("\n=== 統計情報 ===")
        stats = client.get_team_statistics(args.team_id)
        if stats:
            print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 競技シミュレーション
    if args.simulate:
        print("\n=== 競技シミュレーション ===")
        client.simulate_competition(args.team_id)

if __name__ == "__main__":
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
    
    main()
