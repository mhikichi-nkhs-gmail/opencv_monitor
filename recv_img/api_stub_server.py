#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APIスタブサーバー
ET ROBOT CONTEST APIの仕様に合わせたスタブサーバー
"""

from flask import Flask, request, jsonify
import logging
import os
from datetime import datetime
import json

app = Flask(__name__)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# チームごとの提出回数を管理
team_submissions = {}
MAX_SUBMISSIONS_PER_DAY = 2

@app.route('/version', methods=['GET'])
def get_version():
    """バージョン情報を返す"""
    return jsonify({
        'compesys': '1.0.0'
    })

@app.route('/snap', methods=['POST'])
def submit_image():
    """画像提出エンドポイント"""
    try:
        # チームIDを取得
        team_id = request.args.get('id')
        if not team_id:
            return jsonify({
                'status': 'Bad Request',
                'message': 'Team ID is required'
            }), 400
        
        team_id = int(team_id)
        
        # Content-Typeを確認
        content_type = request.headers.get('Content-Type', '')
        if 'image/jpeg' not in content_type:
            return jsonify({
                'status': 'Bad Request',
                'message': 'Content-Type must be image/jpeg'
            }), 400
        
        # 画像データを取得
        image_data = request.get_data()
        if not image_data:
            return jsonify({
                'status': 'Bad Request',
                'message': 'Image data is required'
            }), 400
        
        # チームの提出回数をチェック
        today = datetime.now().strftime('%Y-%m-%d')
        if team_id not in team_submissions:
            team_submissions[team_id] = {}
        
        if today not in team_submissions[team_id]:
            team_submissions[team_id][today] = 0
        
        current_count = team_submissions[team_id][today]
        
        if current_count >= MAX_SUBMISSIONS_PER_DAY:
            return jsonify({
                'status': 'Too Many Requests',
                'message': f'Up to {MAX_SUBMISSIONS_PER_DAY} images can be accepted.'
            }), 429
        
        # 提出回数を増加
        team_submissions[team_id][today] += 1
        
        # 画像を保存（オプション）
        save_image(image_data, team_id, current_count + 1)
        
        logger.info(f"画像提出成功 - チーム{team_id}, サイズ: {len(image_data)} bytes, 今日の提出回数: {current_count + 1}")
        
        return jsonify({
            'status': 'Created'
        }), 201
        
    except ValueError:
        return jsonify({
            'status': 'Bad Request',
            'message': 'Invalid team ID format'
        }), 400
    except Exception as e:
        logger.error(f"画像提出エラー: {e}")
        return jsonify({
            'status': 'Internal Server Error',
            'message': 'An error occurred while processing the image'
        }), 500

def save_image(image_data, team_id, submission_count):
    """画像を保存（デバッグ用）"""
    try:
        # 保存ディレクトリを作成
        save_dir = 'stub_images'
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # ファイル名を生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"team{team_id}_submission{submission_count}_{timestamp}.jpg"
        filepath = os.path.join(save_dir, filename)
        
        # 画像を保存
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        logger.info(f"画像を保存: {filepath}")
        
    except Exception as e:
        logger.error(f"画像保存エラー: {e}")

@app.route('/status', methods=['GET'])
def get_status():
    """サーバー状態を返す"""
    return jsonify({
        'status': 'running',
        'uptime': '2h 30m 15s',
        'teams': len(team_submissions),
        'max_submissions_per_day': MAX_SUBMISSIONS_PER_DAY
    })

@app.route('/reset', methods=['POST'])
def reset_submissions():
    """提出回数をリセット（テスト用）"""
    global team_submissions
    team_submissions = {}
    logger.info("提出回数をリセットしました")
    return jsonify({
        'status': 'OK',
        'message': 'Submissions reset successfully'
    })

if __name__ == '__main__':
    print("="*60)
    print("APIスタブサーバー")
    print("="*60)
    print(f"最大提出回数/日: {MAX_SUBMISSIONS_PER_DAY}")
    print("エンドポイント:")
    print("  GET  /version  - バージョン情報")
    print("  POST /snap     - 画像提出")
    print("  GET  /status   - サーバー状態")
    print("  POST /reset    - 提出回数リセット（テスト用）")
    print("="*60)
    
    app.run(host='0.0.0.0', port=3000, debug=True)
