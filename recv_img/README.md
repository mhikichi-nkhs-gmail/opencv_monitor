# 画像中継サーバー

ソケット通信で画像を受信し、REST APIで外部に送信する信頼性の高いPythonサーバーです。

## 機能

- **ソケット通信**: TCPソケットで画像を受信
- **REST API送信**: 受信した画像を外部APIに送信
- **証拠保全**: 受信した画像を自動保存（法的証拠として）
- **信頼性**: エラー処理とリトライ機能
- **マルチスレッド**: 複数のワーカースレッドで並行処理
- **キュー管理**: 画像のバッファリングと優先度管理
- **ログ機能**: 詳細なログ出力
- **設定管理**: 設定ファイルによる柔軟な設定

## ファイル構成

```
opencv_monitor/recv_img/
├── image_relay_server.py    # メインサーバー
├── test_client.py          # テスト用クライアント
├── test_api_server.py      # テスト用APIサーバー
├── evidence_manager.py     # 証拠保全管理ツール
├── folder_monitor_client.py # フォルダ監視クライアント
├── raspberrypi_camera_client.py # Raspberry Piカメラクライアント
├── rest_api_stub.py        # REST APIスタブサーバー
├── test_rest_api_client.py # REST APIテストクライアント
├── et_robocon_api_stub.py  # ET ROBOT CONTEST APIスタブサーバー
├── test_et_robocon_client.py # ET ROBOT CONTEST APIテストクライアント
├── config.ini              # 設定ファイル
├── requirements.txt        # 依存関係
└── README.md              # このファイル
```

## インストール

1. 依存関係をインストール:
```bash
pip install -r requirements.txt
```

## 使用方法

### 1. メインサーバーの起動

```bash
python image_relay_server.py
```

デフォルト設定:
- ソケットサーバー: `0.0.0.0:8080`
- API送信先: `http://localhost:3000/api/images`

### 2. 設定のカスタマイズ

`config.ini` ファイルを編集して設定を変更できます:

```ini
[socket]
host = 0.0.0.0
port = 8080
buffer_size = 65536

[api]
url = http://your-api-server.com/api/images
timeout = 30
max_retries = 3
retry_delay = 1.0

[server]
max_workers = 3
log_level = INFO

[evidence]
# 証拠保全設定
save_images = True
save_dir = evidence_images
save_metadata = True

### 3. テスト用APIサーバーの起動

```bash
python test_api_server.py
```

### 4. テストクライアントの実行

```bash
# デフォルトテスト
python test_client.py

# 特定の画像を送信
python test_client.py --image path/to/image.jpg

# ディレクトリ内の画像を連続送信
python test_client.py --dir path/to/images --count 10 --interval 0.5

### 5. フォルダ監視クライアントの使用

```bash
# デフォルト設定で監視開始
python folder_monitor_client.py

# 特定のディレクトリを監視
python folder_monitor_client.py --dir /path/to/monitor/directory

# サーバー設定を指定
python folder_monitor_client.py --host 192.168.1.100 --port 8080

# 設定ファイルを指定
python folder_monitor_client.py --config custom_monitor_config.ini
```

### 6. 証拠保全管理ツールの使用

```bash
# 証拠画像一覧を表示
python evidence_manager.py list

# 証拠画像を検索
python evidence_manager.py search "192.168.1.100"

# 統計情報を表示
python evidence_manager.py stats

# 証拠画像をエクスポート
python evidence_manager.py export backup_dir --start-date 2024-01-01

# 古い証拠画像を削除（ドライラン）
python evidence_manager.py cleanup 30

# 古い証拠画像を削除（実行）
python evidence_manager.py cleanup 30 --execute
```

## Raspberry Pi対応

### 初期セットアップ

```bash
# 管理者権限でセットアップスクリプトを実行
sudo chmod +x raspberrypi_setup.sh
sudo ./raspberrypi_setup.sh

# プロジェクトファイルをコピー
cp -r * /home/pi/image_relay_client/

# 権限を設定
sudo chown -R pi:pi /home/pi/image_relay_client
```

### フォルダ監視クライアント（Raspberry Pi）

```bash
# 基本的な使用方法
./start_monitor_raspberrypi.sh

# 設定ファイルを指定
python3 folder_monitor_client.py --config raspberrypi_config.ini

# 特定のディレクトリを監視
python3 folder_monitor_client.py --dir /home/pi/monitor_images --host 192.168.1.100
```

### カメラクライアント（Raspberry Pi）

```bash
# 単発撮影・送信
python3 raspberrypi_camera_client.py --single

# 連続撮影（5秒間隔）
python3 raspberrypi_camera_client.py --continuous --interval 5.0

# 最大100枚撮影
python3 raspberrypi_camera_client.py --continuous --max-photos 100

# ファイルにも保存
python3 raspberrypi_camera_client.py --single --save
```

### systemdサービス設定

```bash
# サービスを設定
sudo chmod +x raspberrypi_service.sh
sudo ./raspberrypi_service.sh

# サービスの管理
sudo systemctl start image-relay-monitor
sudo systemctl status image-relay-monitor
sudo systemctl enable image-relay-monitor
```

### Raspberry Pi設定ファイル

```ini
[server]
host = 192.168.1.100  # 中継サーバーのIPアドレス
port = 8080

[raspberrypi]
camera_enabled = true
camera_resolution = 1920x1080
camera_framerate = 30
auto_save = true
```

## REST APIスタブサーバー

### 概要
実際の外部システムを模擬するREST APIスタブサーバーです。画像中継サーバーからの画像を受信し、データベースに保存して処理をシミュレートします。

### 機能
- **画像アップロード**: マルチパートフォームデータで画像を受信
- **認証システム**: Bearer トークンによる認証
- **データベース管理**: SQLiteを使用した画像情報の永続化
- **統計情報**: 期間別の画像統計を提供
- **画像処理シミュレーション**: 非同期での画像処理を模擬
- **ヘルスチェック**: サーバー状態の監視
- **CORS対応**: クロスオリジンリクエストをサポート

### 起動方法

#### Windows
```bash
start_rest_api.bat
```

#### Linux/macOS
```bash
chmod +x start_rest_api.sh
./start_rest_api.sh
```

#### 手動起動
```bash
python rest_api_stub.py --host 0.0.0.0 --port 5000
```

### API エンドポイント

#### 画像アップロード
```bash
POST /api/v1/images
Content-Type: multipart/form-data

# パラメータ
- image: 画像ファイル
- source: 画像ソース（オプション）
- metadata: JSON形式のメタデータ（オプション）
```

#### 認証トークン作成
```bash
POST /api/v1/auth/token
Content-Type: application/json

{
  "description": "API Token",
  "expires_days": 30
}
```

#### 画像一覧取得
```bash
GET /api/v1/images?limit=100&offset=0&source=test
Authorization: Bearer <token>
```

#### 統計情報取得
```bash
GET /api/v1/statistics?days=7
Authorization: Bearer <token>
```

#### ヘルスチェック
```bash
GET /api/v1/health
```

#### サーバー状態
```bash
GET /api/v1/status
```

### テストクライアント

```bash
# ヘルスチェック
python test_rest_api_client.py --health

# 認証トークン作成
python test_rest_api_client.py --create-token

# テスト画像作成・アップロード
python test_rest_api_client.py --create-test-image --upload

# 画像一覧取得
python test_rest_api_client.py --list

# 統計情報取得
python test_rest_api_client.py --stats
```

### 設定ファイル

```ini
[server]
host = 0.0.0.0
port = 5000
max_file_size = 52428800

[security]
require_auth = true
token_expiry_days = 30
allowed_extensions = .jpg,.jpeg,.png,.bmp,.gif,.tiff

[processing]
enable_processing = true
processing_threads = 2
```

## ET ROBOT CONTEST API対応

### 概要
ET ROBOT CONTESTの実際のAPI仕様に準拠したスタブサーバーとクライアントです。

### API仕様
- **エンドポイント**: `POST http://localhost:5000/snap`
- **Content-Type**: `image/jpeg`
- **パラメータ**: `id` (チームID: 数値)
- **制限**: 競技中は1チームあたり最大2枚まで
- **レスポンス**: 201 Created (成功), 429 Too Many Requests (制限超過)

### 起動方法

#### ET ROBOT CONTEST APIスタブサーバー
```bash
# Windows
start_et_robocon_api.bat

# 手動起動
python et_robocon_api_stub.py --host localhost --port 5000
```

#### テストクライアント
```bash
# ヘルスチェック
python test_et_robocon_client.py --health

# 競技シミュレーション
python test_et_robocon_client.py --simulate --team-id 1

# 個別テスト
python test_et_robocon_client.py --start-competition
python test_et_robocon_client.py --upload --image test.jpg --team-id 1
python test_et_robocon_client.py --end-competition
```

### 競技管理機能

#### 競技状態管理
```bash
# 競技開始
curl -X POST http://localhost:5000/admin/competition/start

# 競技終了
curl -X POST http://localhost:5000/admin/competition/end

# 競技リセット
curl -X POST http://localhost:5000/admin/competition/reset
```

#### 統計情報
```bash
# チーム統計取得
curl "http://localhost:5000/admin/team/1/statistics?days=7"
```

### 画像中継サーバーとの連携

画像中継サーバーは自動的にET ROBOT CONTEST API仕様に合わせて画像を送信します：

- チームIDはメタデータから取得（デフォルト: 1）
- Content-Type: image/jpegで送信
- 429エラー（制限超過）は適切に処理
- 証拠保全機能は維持

### 設定例

```ini
[api]
# ET ROBOT CONTEST API設定
url = http://localhost:5000/snap
timeout = 30
max_retries = 3
retry_delay = 1.0
```

## フォルダ監視機能

### 自動監視
- 指定されたディレクトリをリアルタイムで監視
- 新しい画像ファイルの追加を自動検知
- ファイルの書き込み完了を待機してから送信
- 既存ファイルの処理も可能

### 監視設定
```ini
[monitor]
directory = ./monitor_images          # 監視ディレクトリ
image_extensions = .jpg,.jpeg,.png,.bmp  # 監視対象拡張子
delay = 1.0                           # 書き込み完了待機時間
```

### 対応イベント
- **ファイル作成**: 新しい画像ファイルの追加
- **ファイル移動**: 他の場所から移動された画像ファイル
- **既存ファイル**: 起動時に既存の画像ファイルを処理

### メタデータ
監視で検出された画像には以下のメタデータが追加されます：
- ファイルパス
- 作成時刻・更新時刻
- 検出時刻
- ソース情報（folder_monitor）

## プロトコル仕様

### クライアント → サーバー

1. **ヘッダーサイズ送信** (4バイト, big-endian)
2. **ヘッダーJSON送信** (UTF-8)
3. **画像データ送信** (バイナリ)

ヘッダーJSON例:
```json
{
    "image_size": 12345,
    "format": "jpeg",
    "metadata": {
        "filename": "test.jpg",
        "timestamp": 1234567890.123
    }
}
```

### サーバー → API

マルチパートフォームデータで送信:
- `image`: 画像ファイル
- `timestamp`: 受信タイムスタンプ
- `client_address`: クライアントアドレス
- `image_size`: 画像サイズ
- `metadata`: メタデータJSON

## 信頼性機能

### エラー処理
- ソケット接続エラー
- 画像受信エラー
- API送信エラー
- 設定ファイルエラー

### リトライ機能
- API送信失敗時の自動リトライ
- 指数バックオフ
- 最大リトライ回数設定

### キュー管理
- 画像のバッファリング
- キュー満杯時の古い画像破棄
- ワーカースレッドによる並行処理

### ログ機能
- ファイルとコンソールへのログ出力
- ログレベル設定
- 詳細なエラー情報

## ログファイル

- `image_relay_server.log`: メインサーバーのログ
- `evidence_images/`: 証拠保全用画像保存ディレクトリ

## トラブルシューティング

### よくある問題

1. **ポートが使用中**
   - 設定ファイルでポートを変更
   - 既存プロセスを終了

2. **API送信エラー**
   - APIサーバーが起動しているか確認
   - ネットワーク接続を確認
   - 設定ファイルのURLを確認

3. **メモリ不足**
   - バッファサイズを小さくする
   - ワーカースレッド数を減らす

### デバッグ

ログレベルを `DEBUG` に設定:
```ini
[server]
log_level = DEBUG
```

## 証拠保全機能

### 自動保存
- 受信した画像は自動的に `evidence_images/` ディレクトリに保存
- ファイル名には受信時刻とクライアントアドレスを含む
- メタデータ（JSON形式）も同時に保存

### ファイル命名規則
```
evidence_YYYYMMDD_HHMMSS_microseconds_clientip_port.jpg
```

### メタデータ内容
- ファイル情報（サイズ、パス）
- 受信時刻
- クライアントアドレス
- ヘッダー情報
- 受信順序番号

### 管理機能
- 画像一覧表示
- 検索機能（ファイル名、メタデータ）
- 統計情報表示
- エクスポート機能
- 古いファイルの自動削除

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
