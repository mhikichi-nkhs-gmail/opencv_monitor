# 画像中継サーバーシステム

ET ROBOT CONTEST用の画像中継サーバーシステムです。ソケット通信で画像を受信し、REST APIで外部サーバーに送信する信頼性の高いシステムです。

## 成果物構成

### 1. 画像中継サーバー (`image_relay_server.py`)
- ソケット通信で画像を受信
- 800x600 JPEG形式に変換
- REST APIで外部サーバーに送信
- 証拠保全機能（提出画像の保存）
- エラー時の再送処理

### 2. APIスタブサーバー (`api_stub_server.py`)
- ET ROBOT CONTEST API仕様に準拠
- 画像提出エンドポイント `/snap`
- 1日2回の提出制限機能
- バージョン情報エンドポイント `/version`

### 3. 起動バッチファイル
- `start_relay_server.bat` - 画像中継サーバー起動
- `start_stub_server.bat` - APIスタブサーバー起動

### 4. 設定ファイル (`config.ini`)
- ソケット設定
- API設定
- 画像変換設定
- 証拠保全設定

## セットアップ

### 1. 必要なライブラリのインストール
```bash
pip install opencv-python numpy requests flask
```

### 2. 設定ファイルの確認
`config.ini`を編集して、チームIDやAPI URLを設定してください。

## 使用方法

### 1. APIスタブサーバーの起動
```bash
start_stub_server.bat
```
または
```bash
python api_stub_server.py
```

### 2. 画像中継サーバーの起動
```bash
start_relay_server.bat
```
または
```bash
python image_relay_server.py
```

### 3. クライアントからの画像送信
```python
import socket
import json
import struct

# 画像データを準備
with open('test_image.jpg', 'rb') as f:
    image_data = f.read()

# ヘッダー情報
header = {
    'image_size': len(image_data),
    'metadata': {
        'team_id': 1
    }
}

# ソケット接続
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost', 8080))

# ヘッダー送信
header_bytes = json.dumps(header).encode('utf-8')
client.send(struct.pack('>I', len(header_bytes)))
client.send(header_bytes)

# 画像データ送信
client.send(image_data)
client.close()
```

## API仕様

### 画像提出エンドポイント
```
POST /snap?id=チームID
Content-Type: image/jpeg
```

#### 成功時 (HTTP 201)
```json
{
  "status": "Created"
}
```

#### 制限エラー時 (HTTP 429)
```json
{
  "status": "Too Many Requests",
  "message": "Up to 2 images can be accepted."
}
```

### バージョン情報エンドポイント
```
GET /version
```

#### レスポンス
```json
{
  "compesys": "1.0.0"
}
```

## 設定項目

### config.ini ファイルの詳細説明

`config.ini`ファイルは画像中継サーバーの動作を制御する設定ファイルです。以下のセクションで構成されています：

#### [socket] セクション - ソケット通信設定
```ini
[socket]
host = 0.0.0.0          # ソケットサーバーのホストアドレス
port = 8080             # ソケットサーバーのポート番号
buffer_size = 65536     # 受信バッファサイズ（バイト）
```

**設定項目の意味：**
- `host`: サーバーが待ち受けるIPアドレス
  - `0.0.0.0`: すべてのネットワークインターフェースで待ち受け
  - `127.0.0.1`: ローカルホストのみで待ち受け
  - `192.168.1.100`: 特定のIPアドレスで待ち受け
- `port`: クライアントが接続するポート番号（1024-65535）
- `buffer_size`: 一度に受信する最大データサイズ

#### [api] セクション - REST API設定
```ini
[api]
url = http://localhost:3000/snap  # APIサーバーのエンドポイントURL
team_id = 1                       # チームID（画像提出時に使用）
timeout = 30                      # APIリクエストのタイムアウト時間（秒）
max_retries = 3                   # 送信失敗時の最大リトライ回数
retry_delay = 1.0                 # リトライ間隔（秒）
```

**設定項目の意味：**
- `url`: 画像を送信するAPIサーバーのURL
  - 本番環境: `http://192.168.100.1/snap`
  - テスト環境: `http://localhost:3000/snap`
- `team_id`: ET ROBOT CONTESTのチームID
- `timeout`: APIサーバーからの応答を待つ最大時間
- `max_retries`: ネットワークエラー時の再送回数
- `retry_delay`: リトライ間隔（指数バックオフで増加）

#### [image] セクション - 画像変換設定
```ini
[image]
target_width = 800                # 変換後の画像幅（ピクセル）
target_height = 600               # 変換後の画像高さ（ピクセル）
jpeg_quality = 95                 # JPEG圧縮品質（1-100）
```

**設定項目の意味：**
- `target_width`: 提出用画像の幅（ET ROBOT CONTEST仕様）
- `target_height`: 提出用画像の高さ（ET ROBOT CONTEST仕様）
- `jpeg_quality`: JPEG圧縮品質
  - `95`: 高品質（ファイルサイズ大）
  - `80`: 標準品質
  - `60`: 低品質（ファイルサイズ小）

#### [server] セクション - サーバー設定
```ini
[server]
max_workers = 3                   # 並行処理するワーカースレッド数
log_level = INFO                  # ログ出力レベル
```

**設定項目の意味：**
- `max_workers`: 同時に処理できる画像数
  - `1`: シングルスレッド（安定性重視）
  - `3`: 標準設定（バランス重視）
  - `5`: 高並行（性能重視）
- `log_level`: ログの詳細度
  - `DEBUG`: 詳細なデバッグ情報
  - `INFO`: 一般的な情報
  - `WARNING`: 警告のみ
  - `ERROR`: エラーのみ

#### [evidence] セクション - 証拠保全設定
```ini
[evidence]
save_images = True                # 画像保存の有効/無効
save_dir = evidence_images        # 保存ディレクトリ名
save_metadata = True              # メタデータ保存の有効/無効
```

**設定項目の意味：**
- `save_images`: 提出画像の保存
  - `True`: 証拠保全用に画像を保存
  - `False`: 画像を保存しない（ディスク容量節約）
- `save_dir`: 画像保存先のディレクトリ名
- `save_metadata`: 画像の詳細情報保存
  - `True`: JSONファイルでメタデータも保存
  - `False`: 画像ファイルのみ保存

### 設定例

#### 本番環境用設定
```ini
[socket]
host = 0.0.0.0
port = 8080
buffer_size = 65536

[api]
url = http://192.168.100.1/snap
team_id = 5
timeout = 30
max_retries = 5
retry_delay = 2.0

[image]
target_width = 800
target_height = 600
jpeg_quality = 95

[server]
max_workers = 3
log_level = INFO

[evidence]
save_images = True
save_dir = evidence_images
save_metadata = True
```

#### テスト環境用設定
```ini
[socket]
host = 127.0.0.1
port = 8080
buffer_size = 32768

[api]
url = http://localhost:3000/snap
team_id = 1
timeout = 10
max_retries = 2
retry_delay = 1.0

[image]
target_width = 800
target_height = 600
jpeg_quality = 80

[server]
max_workers = 1
log_level = DEBUG

[evidence]
save_images = False
save_dir = test_evidence
save_metadata = False
```

## ログファイル

- `image_relay_server.log` - 画像中継サーバーのログ
- 証拠保全画像は `evidence_images/` ディレクトリに保存

## トラブルシューティング

### 1. ポートが使用中
- 別のポート番号に変更
- 既存のプロセスを終了

### 2. ライブラリが見つからない
- `pip install` で必要なライブラリをインストール
- Python環境を確認

### 3. APIサーバーに接続できない
- APIサーバーが起動しているか確認
- ネットワーク設定を確認
- ファイアウォール設定を確認

