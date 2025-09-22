#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画像中継サーバー
ソケット通信で画像を受信し、REST APIで外部に送信する信頼性の高いサーバー
"""

import socket
import json
import logging
import time
import threading
import queue
import requests
from typing import Optional, Dict, Any
import configparser
import os
from datetime import datetime
import traceback
import cv2
import numpy as np
from io import BytesIO

class ImageRelayServer:
    """画像中継サーバークラス"""
    
    def __init__(self, config_file: str = "config.ini"):
        """初期化"""
        # まずログ設定を初期化
        self.logger = logging.getLogger(__name__)
        
        # 設定ファイルを読み込み
        self.config = self._load_config(config_file)
        self.setup_logging()
        
        # ソケットサーバー設定
        self.host = self.config.get('socket', 'host', fallback='0.0.0.0')
        self.port = self.config.getint('socket', 'port', fallback=8080)
        self.buffer_size = self.config.getint('socket', 'buffer_size', fallback=65536)
        
        # REST API設定
        self.api_url = self.config.get('api', 'url')
        self.api_timeout = self.config.getint('api', 'timeout', fallback=30)
        self.max_retries = self.config.getint('api', 'max_retries', fallback=3)
        self.retry_delay = self.config.getfloat('api', 'retry_delay', fallback=1.0)
        self.team_id = self.config.getint('api', 'team_id', fallback=1)
        
        # 証拠保全設定
        self.save_images = self.config.getboolean('evidence', 'save_images', fallback=True)
        self.save_dir = self.config.get('evidence', 'save_dir', fallback='evidence_images')
        self.save_metadata = self.config.getboolean('evidence', 'save_metadata', fallback=True)
        self.ensure_save_dir()
        
        # 画像変換設定
        self.target_width = self.config.getint('image', 'target_width', fallback=800)
        self.target_height = self.config.getint('image', 'target_height', fallback=600)
        self.jpeg_quality = self.config.getint('image', 'jpeg_quality', fallback=95)
        
        # サーバー状態
        self.running = False
        self.server_socket = None
        self.image_queue = queue.Queue(maxsize=200)
        self.worker_threads = []
        self.max_workers = self.config.getint('server', 'max_workers', fallback=5)
        self.received_count = 0
        
        self.logger.info("画像中継サーバーを初期化しました")
        self._print_initialization_info()
        
        # REST API疎通確認
        self._check_api_connectivity()
    
    def _load_config(self, config_file: str) -> configparser.ConfigParser:
        """設定ファイルを読み込み"""
        config = configparser.ConfigParser()
        
        # デフォルト設定
        config['socket'] = {
            'host': '0.0.0.0',
            'port': '8080',
            'buffer_size': '65536'
        }
        config['api'] = {
            'url': 'http://192.168.100.1/snap',
            'timeout': '30',
            'max_retries': '3',
            'retry_delay': '1.0',
            'team_id': '1'
        }
        config['server'] = {
            'max_workers': '5',
            'log_level': 'INFO'
        }
        config['evidence'] = {
            'save_images': 'True',
            'save_dir': 'evidence_images',
            'save_metadata': 'True'
        }
        config['image'] = {
            'target_width': '800',
            'target_height': '600',
            'jpeg_quality': '95'
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
    
    def _print_initialization_info(self):
        """初期化情報を表示"""
        print("\n" + "="*60)
        print("画像中継サーバー 初期化情報")
        print("="*60)
        
        # ソケット設定
        print(f"【ソケット設定】")
        print(f"  ホスト: {self.host}")
        print(f"  ポート: {self.port}")
        print(f"  バッファサイズ: {self.buffer_size:,} bytes")
        
        # REST API設定
        print(f"\n【REST API設定】")
        print(f"  API URL: {self.api_url}")
        print(f"  タイムアウト: {self.api_timeout}秒")
        print(f"  最大リトライ回数: {self.max_retries}回")
        print(f"  リトライ遅延: {self.retry_delay}秒")
        print(f"  チームID: {self.team_id}")
        
        # 画像変換設定
        print(f"\n【画像変換設定】")
        print(f"  目標サイズ: {self.target_width}x{self.target_height}")
        print(f"  JPEG品質: {self.jpeg_quality}%")
        
        # サーバー設定
        print(f"\n【サーバー設定】")
        print(f"  最大ワーカー数: {self.max_workers}")
        print(f"  キューサイズ: 200件")
        print(f"  ログレベル: {self.config.get('server', 'log_level', fallback='INFO')}")
        
        # 証拠保全設定
        print(f"\n【証拠保全設定】")
        print(f"  画像保存: {'有効' if self.save_images else '無効'}")
        if self.save_images:
            print(f"  保存ディレクトリ: {self.save_dir}")
            print(f"  メタデータ保存: {'有効' if self.save_metadata else '無効'}")
        
        print("="*60)
        print("サーバーを開始中...\n")
    
    def _check_api_connectivity(self):
        """REST APIの疎通確認とversion情報取得"""
        print("【REST API疎通確認】")
        
        try:
            # APIのベースURLを取得（パス部分を除去）
            from urllib.parse import urlparse
            parsed_url = urlparse(self.api_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # version情報を取得
            version_url = f"{base_url}/version"
            
            print(f"  APIベースURL: {base_url}")
            print(f"  Version確認URL: {version_url}")
            
            response = requests.get(version_url, timeout=10)
            
            if response.status_code == 200:
                try:
                    version_info = response.json()
                    print(f"  ✓ API疎通確認成功")
                    
                    # compesysバージョン情報を表示
                    if 'compesys' in version_info:
                        print(f"  Compesys Version: {version_info['compesys']}")
                    else:
                        print(f"  Compesys Version: 不明")
                    
                    # レスポンス全体を表示（デバッグ用）
                    print(f"  レスポンス: {version_info}")
                        
                except json.JSONDecodeError:
                    print(f"  ✓ API疎通確認成功（レスポンス: {response.text[:100]}...）")
                    
            else:
                print(f"  ⚠ API疎通確認警告 - HTTP {response.status_code}")
                print(f"    レスポンス: {response.text[:100]}...")
                
        except requests.exceptions.ConnectionError:
            print(f"  ✗ API疎通確認失敗 - 接続エラー")
            print(f"    URL: {version_url}")
            print(f"    エラー: サーバーに接続できません")
            
        except requests.exceptions.Timeout:
            print(f"  ✗ API疎通確認失敗 - タイムアウト")
            print(f"    URL: {version_url}")
            print(f"    エラー: 10秒以内に応答がありませんでした")
            
        except Exception as e:
            print(f"  ✗ API疎通確認失敗 - 予期しないエラー")
            print(f"    URL: {version_url}")
            print(f"    エラー: {str(e)}")
        
        print()
    
    def setup_logging(self):
        """ログ設定"""
        log_level = self.config.get('server', 'log_level', fallback='INFO')
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[
                logging.FileHandler('image_relay_server.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def ensure_save_dir(self):
        """保存ディレクトリを作成"""
        if self.save_images and not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            print(f"証拠保全用ディレクトリを作成: {self.save_dir}")
    
    def save_evidence_image(self, image_data: bytes, header: Dict[str, Any], client_address: tuple, timestamp: str, is_submission: bool = False) -> Optional[str]:
        """証拠保全用に画像を保存"""
        if not self.save_images:
            return None
        
        try:
            # ファイル名を生成（タイムスタンプ + クライアントアドレス + 提出フラグ + 連番）
            timestamp_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            prefix = "submission" if is_submission else "evidence"
            base_filename = f"{prefix}_{timestamp_obj.strftime('%Y%m%d_%H%M%S_%f')}_{client_address[0]}_{client_address[1]}"
            
            # ファイル名の重複を防ぐため連番を追加
            counter = 1
            filename = f"{base_filename}_{counter:03d}.jpg"
            filepath = os.path.join(self.save_dir, filename)
            
            # ファイルが既に存在する場合は連番を増やして重複を回避
            while os.path.exists(filepath):
                counter += 1
                filename = f"{base_filename}_{counter:03d}.jpg"
                filepath = os.path.join(self.save_dir, filename)
            
            # 画像を保存
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            # メタデータを保存
            if self.save_metadata:
                metadata_file = filepath.replace('.jpg', '_metadata.json')
                metadata = {
                    'filename': filename,
                    'filepath': filepath,
                    'size': len(image_data),
                    'timestamp': timestamp,
                    'client_address': str(client_address),
                    'header': header,
                    'received_count': self.received_count,
                    'is_submission': is_submission,
                    'image_type': 'submission' if is_submission else 'original'
                }
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            self.received_count += 1
            image_type = "提出画像" if is_submission else "元画像"
            self.logger.info(f"証拠保全: {image_type}を保存しました - {filename} ({len(image_data)} bytes) [連番: {counter:03d}]")
            return filepath
            
        except Exception as e:
            self.logger.error(f"証拠保全保存エラー: {e}")
            return None
    
    def start(self):
        """サーバーを開始"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)  # タイムアウト設定
            
            self.running = True
            self.logger.info(f"サーバーを開始しました - {self.host}:{self.port}")
            
            # ワーカースレッドを開始
            for i in range(self.max_workers):
                worker = threading.Thread(target=self._worker_thread, args=(i,))
                worker.daemon = True
                worker.start()
                self.worker_threads.append(worker)
                self.logger.info(f"ワーカースレッド {i} を開始しました")
            
            # メインループ
            self._main_loop()
            
        except Exception as e:
            self.logger.error(f"サーバー開始エラー: {e}")
            self.logger.error(traceback.format_exc())
        finally:
            self.stop()
    
    def _main_loop(self):
        """メインループ - クライアント接続を待機"""
        connection_count = 0
        while self.running:
            try:
                self.logger.info("クライアント接続を待機中...")
                client_socket, address = self.server_socket.accept()
                connection_count += 1
                self.logger.info(f"クライアント接続 #{connection_count}: {address}")
                
                # クライアント処理スレッドを開始
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address, connection_count)
                )
                client_thread.daemon = True
                client_thread.start()
                self.logger.info(f"クライアント処理スレッド開始: {address} (接続#{connection_count})")
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"メインループエラー: {e}")
                    import traceback
                    self.logger.error(f"メインループエラー詳細: {traceback.format_exc()}")
    
    def _handle_client(self, client_socket: socket.socket, address: tuple, connection_id: int = 0):
        """クライアント接続を処理"""
        try:
            self.logger.info(f"クライアント処理開始: {address} (接続#{connection_id})")
            client_socket.settimeout(30.0)  # 30秒タイムアウト
            
            # ヘッダー情報を受信
            self.logger.info(f"ヘッダー受信開始: {address} (接続#{connection_id})")
            header_data = self._receive_header(client_socket)
            if not header_data:
                self.logger.warning(f"ヘッダー受信失敗: {address} (接続#{connection_id})")
                return
            
            self.logger.info(f"ヘッダー受信完了: {address} (接続#{connection_id}) - 画像サイズ: {header_data.get('image_size', 0)} bytes")
            
            # 画像データを受信
            self.logger.info(f"画像データ受信開始: {address} (接続#{connection_id}) - サイズ: {header_data.get('image_size', 0)} bytes")
            image_data = self._receive_image(client_socket, header_data)
            if not image_data:
                self.logger.warning(f"画像データ受信失敗: {address} (接続#{connection_id})")
                return
            
            self.logger.info(f"画像データ受信完了: {address} (接続#{connection_id}) - 受信サイズ: {len(image_data)} bytes")
            
            # 画像変換処理
            converted_image_data = self.convert_image(image_data)
            if not converted_image_data:
                self.logger.error(f"画像変換に失敗しました: {address}")
                return
            
            # 証拠保全用に提出画像を保存
            timestamp = datetime.now().isoformat()
            saved_path = self.save_evidence_image(converted_image_data, header_data, address, timestamp, is_submission=True)
            
            # キューに追加（ブロッキング方式で確実に追加）
            try:
                queue_item = {
                    'image_data': converted_image_data,
                    'header': header_data,
                    'timestamp': timestamp,
                    'client_address': address,
                    'saved_path': saved_path
                }
                
                # ブロッキング方式でキューに追加（最大5秒待機）
                self.image_queue.put(queue_item, timeout=5.0)
                self.logger.info(f"画像をキューに追加: {address} - サイズ: {len(converted_image_data)} bytes (キューサイズ: {self.image_queue.qsize()})")
                
            except queue.Full:
                self.logger.error(f"キューが満杯で画像を追加できませんでした: {address} - キューサイズ: {self.image_queue.qsize()}")
                # キューが満杯の場合は、古い画像を1つ削除して新しい画像を追加
                try:
                    old_item = self.image_queue.get_nowait()
                    self.logger.warning(f"古い画像を破棄して新しい画像を追加: {old_item.get('client_address', 'unknown')}")
                    self.image_queue.put_nowait(queue_item)
                    self.logger.info(f"画像をキューに追加（古い画像を破棄後）: {address} - サイズ: {len(converted_image_data)} bytes")
                except queue.Empty:
                    self.logger.error(f"キューが空で古い画像を削除できませんでした: {address}")
            except Exception as e:
                self.logger.error(f"キュー追加エラー: {address} - {e}")
            
        except Exception as e:
            self.logger.error(f"クライアント処理エラー {address}: {e}")
            import traceback
            self.logger.error(f"詳細エラー情報 {address}: {traceback.format_exc()}")
        finally:
            try:
                client_socket.close()
                self.logger.info(f"クライアント接続を閉じました: {address}")
            except Exception as e:
                self.logger.error(f"クライアント接続クローズエラー {address}: {e}")
    
    def _receive_header(self, client_socket: socket.socket) -> Optional[Dict[str, Any]]:
        """ヘッダー情報を受信"""
        try:
            self.logger.info("ヘッダーサイズ受信開始 (4バイト)")
            # ヘッダーサイズを受信 (4バイト)
            header_size_data = client_socket.recv(4)
            self.logger.info(f"ヘッダーサイズ受信完了: {len(header_size_data)} bytes")
            if len(header_size_data) != 4:
                self.logger.error(f"ヘッダーサイズ受信失敗: 期待値4バイト, 実際{len(header_size_data)}バイト")
                return None
            
            header_size = int.from_bytes(header_size_data, byteorder='big')
            self.logger.info(f"ヘッダーサイズ: {header_size} bytes")
            
            # ヘッダーデータを受信
            header_data = b''
            received_bytes = 0
            while len(header_data) < header_size:
                chunk_size = min(1024, header_size - len(header_data))
                self.logger.info(f"ヘッダーデータ受信中: {received_bytes}/{header_size} bytes")
                chunk = client_socket.recv(chunk_size)
                if not chunk:
                    self.logger.error(f"ヘッダーデータ受信中断: {received_bytes}/{header_size} bytes")
                    return None
                header_data += chunk
                received_bytes += len(chunk)
            
            self.logger.info(f"ヘッダーデータ受信完了: {len(header_data)} bytes")
            header = json.loads(header_data.decode('utf-8'))
            self.logger.info(f"ヘッダー解析完了: {header}")
            return header
            
        except Exception as e:
            self.logger.error(f"ヘッダー受信エラー: {e}")
            import traceback
            self.logger.error(f"ヘッダー受信エラー詳細: {traceback.format_exc()}")
            return None
    
    def _receive_image(self, client_socket: socket.socket, header: Dict[str, Any]) -> Optional[bytes]:
        """画像データを受信"""
        try:
            image_size = header.get('image_size', 0)
            self.logger.info(f"画像データ受信開始: 期待サイズ {image_size} bytes")
            if image_size <= 0:
                self.logger.error(f"無効な画像サイズ: {image_size}")
                return None
            
            image_data = b''
            received_bytes = 0
            chunk_count = 0
            consecutive_empty_chunks = 0
            max_empty_chunks = 10  # 連続で空のチャンクが来る最大回数
            
            while len(image_data) < image_size:
                chunk_size = min(self.buffer_size, image_size - len(image_data))
                chunk_count += 1
                if chunk_count % 50 == 0:  # 50チャンクごとにログ出力
                    self.logger.info(f"画像データ受信中: {received_bytes}/{image_size} bytes (チャンク#{chunk_count})")
                
                try:
                    chunk = client_socket.recv(chunk_size)
                    if not chunk:
                        consecutive_empty_chunks += 1
                        self.logger.warning(f"空のチャンク受信: {consecutive_empty_chunks}/{max_empty_chunks} (チャンク#{chunk_count})")
                        if consecutive_empty_chunks >= max_empty_chunks:
                            self.logger.error(f"画像データ受信中断: {received_bytes}/{image_size} bytes (連続空チャンク上限)")
                            return None
                        time.sleep(0.1)  # 少し待機してから再試行
                        continue
                    else:
                        consecutive_empty_chunks = 0  # 正常なチャンクを受信したらリセット
                    
                    image_data += chunk
                    received_bytes += len(chunk)
                    
                except socket.timeout:
                    self.logger.warning(f"ソケットタイムアウト: チャンク#{chunk_count}")
                    continue
                except Exception as e:
                    self.logger.error(f"チャンク受信エラー: {e}")
                    return None
            
            self.logger.info(f"画像データ受信完了: {len(image_data)} bytes (チャンク#{chunk_count})")
            return image_data
            
        except Exception as e:
            self.logger.error(f"画像受信エラー: {e}")
            import traceback
            self.logger.error(f"画像受信エラー詳細: {traceback.format_exc()}")
            return None
    
    def convert_image(self, image_data: bytes) -> Optional[bytes]:
        """画像を800x600のJPEG形式に変換"""
        try:
            # バイトデータをnumpy配列に変換
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                self.logger.error("画像のデコードに失敗しました")
                return None
            
            original_height, original_width = img.shape[:2]
            self.logger.info(f"元画像サイズ: {original_width}x{original_height}")
            
            # サイズが異なる場合はリサイズ
            if original_width != self.target_width or original_height != self.target_height:
                img = cv2.resize(img, (self.target_width, self.target_height), interpolation=cv2.INTER_LANCZOS4)
                self.logger.info(f"画像をリサイズしました: {self.target_width}x{self.target_height}")
            
            # JPEG形式でエンコード
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
            success, encoded_image = cv2.imencode('.jpg', img, encode_params)
            
            if not success:
                self.logger.error("JPEGエンコードに失敗しました")
                return None
            
            # バイトデータに変換
            converted_data = encoded_image.tobytes()
            self.logger.info(f"画像変換完了: {len(converted_data)} bytes (品質: {self.jpeg_quality})")
            
            return converted_data
            
        except Exception as e:
            self.logger.error(f"画像変換エラー: {e}")
            return None
    
    def _worker_thread(self, worker_id: int):
        """ワーカースレッド - キューから画像を取得してAPIに送信"""
        self.logger.info(f"ワーカースレッド {worker_id} が開始されました")
        processed_count = 0
        
        while self.running:
            try:
                # キューから画像を取得
                item = self.image_queue.get(timeout=1.0)
                processed_count += 1
                self.logger.info(f"ワーカー {worker_id}: 画像処理開始 ({processed_count}件目) - {item['client_address']} (キューサイズ: {self.image_queue.qsize()})")
                
                self._send_image_to_api(item, worker_id)
                self.image_queue.task_done()
                
                self.logger.info(f"ワーカー {worker_id}: 画像処理完了 ({processed_count}件目) - {item['client_address']}")
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"ワーカースレッド {worker_id} エラー: {e}")
                if 'item' in locals():
                    self.image_queue.task_done()
    
    def _send_image_to_api(self, item: Dict[str, Any], worker_id: int):
        """画像をAPIに送信（ET ROBOT CONTEST API仕様）"""
        image_data = item['image_data']
        header = item['header']
        timestamp = item['timestamp']
        client_address = item['client_address']
        saved_path = item.get('saved_path')
        
        for attempt in range(self.max_retries + 1):
            try:
                # ET ROBOT CONTEST API仕様に合わせて送信
                # Content-Type: image/jpeg
                # パラメータ: id (チームID)
                
                # チームIDを取得（設定ファイルから、またはメタデータから、またはデフォルト値）
                team_id = header.get('metadata', {}).get('team_id', self.team_id)
                
                # ヘッダーを設定
                headers = {
                    'Content-Type': 'image/jpeg'
                }
                
                # パラメータを設定（id=チームIDの形式）
                params = {
                    'id': team_id
                }
                
                response = requests.post(
                    self.api_url,
                    data=image_data,
                    headers=headers,
                    params=params,
                    timeout=self.api_timeout
                )
                
                if response.status_code == 201:
                    try:
                        response_data = response.json()
                        self.logger.info(f"ワーカー {worker_id}: 画像送信成功 - チーム{team_id}, レスポンス: {response_data}, {client_address}")
                    except json.JSONDecodeError:
                        self.logger.info(f"ワーカー {worker_id}: 画像送信成功 - チーム{team_id}, レスポンス: {response.text}, {client_address}")
                    return
                elif response.status_code == 429:
                    try:
                        response_data = response.json()
                        self.logger.warning(f"ワーカー {worker_id}: 画像送信制限 - チーム{team_id}, レスポンス: {response_data}")
                    except json.JSONDecodeError:
                        self.logger.warning(f"ワーカー {worker_id}: 画像送信制限 - チーム{team_id}, レスポンス: {response.text}")
                    return  # 429エラーは再試行しない
                else:
                    try:
                        response_data = response.json()
                        self.logger.warning(f"ワーカー {worker_id}: API応答エラー - {response.status_code}, レスポンス: {response_data}")
                    except json.JSONDecodeError:
                        self.logger.warning(f"ワーカー {worker_id}: API応答エラー - {response.status_code}, レスポンス: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"ワーカー {worker_id}: API送信エラー (試行 {attempt + 1}/{self.max_retries + 1}): {e}")
                
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))  # 指数バックオフ
                else:
                    self.logger.error(f"ワーカー {worker_id}: 最大リトライ回数に達しました - 画像を破棄")
    
    def stop(self):
        """サーバーを停止"""
        self.logger.info("サーバーを停止中...")
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        # ワーカースレッドの終了を待機
        for worker in self.worker_threads:
            worker.join(timeout=5.0)
        
        self.logger.info("サーバーを停止しました")

def main():
    """メイン関数"""
    import signal
    import sys
    
    server = ImageRelayServer()
    
    def signal_handler(signum, frame):
        """シグナルハンドラー"""
        print("\n停止シグナルを受信しました")
        server.stop()
        sys.exit(0)
    
    # シグナルハンドラーを設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nCtrl+Cで停止しました")
        server.stop()

if __name__ == "__main__":
    main()
