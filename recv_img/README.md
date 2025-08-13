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

### 5. 証拠保全管理ツールの使用

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
