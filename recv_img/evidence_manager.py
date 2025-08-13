#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
証拠保全画像管理ツール
保存された画像の検索、表示、管理を行うツール
"""

import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any
import shutil

class EvidenceManager:
    """証拠保全画像管理クラス"""
    
    def __init__(self, evidence_dir: str = "evidence_images"):
        """初期化"""
        self.evidence_dir = evidence_dir
        self.ensure_dir()
    
    def ensure_dir(self):
        """ディレクトリの存在確認"""
        if not os.path.exists(self.evidence_dir):
            print(f"証拠保全ディレクトリが存在しません: {self.evidence_dir}")
            return False
        return True
    
    def list_evidence(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """証拠画像一覧を取得"""
        if not self.ensure_dir():
            return []
        
        evidence_list = []
        files = os.listdir(self.evidence_dir)
        
        # 画像ファイルのみをフィルタ
        image_files = [f for f in files if f.endswith('.jpg')]
        image_files.sort(reverse=True)  # 新しい順
        
        # ページネーション
        paginated_files = image_files[offset:offset + limit]
        
        for filename in paginated_files:
            filepath = os.path.join(self.evidence_dir, filename)
            metadata_file = filepath.replace('.jpg', '_metadata.json')
            
            evidence_info = {
                'filename': filename,
                'filepath': filepath,
                'size': os.path.getsize(filepath),
                'created': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat(),
                'metadata': None
            }
            
            # メタデータがあれば読み込み
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        evidence_info['metadata'] = json.load(f)
                except:
                    pass
            
            evidence_list.append(evidence_info)
        
        return evidence_list
    
    def search_evidence(self, query: str) -> List[Dict[str, Any]]:
        """証拠画像を検索"""
        if not self.ensure_dir():
            return []
        
        evidence_list = []
        files = os.listdir(self.evidence_dir)
        
        # 画像ファイルのみをフィルタ
        image_files = [f for f in files if f.endswith('.jpg')]
        
        for filename in image_files:
            filepath = os.path.join(self.evidence_dir, filename)
            metadata_file = filepath.replace('.jpg', '_metadata.json')
            
            # ファイル名で検索
            if query.lower() in filename.lower():
                evidence_info = self._get_evidence_info(filename, filepath, metadata_file)
                evidence_list.append(evidence_info)
                continue
            
            # メタデータで検索
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # メタデータ内で検索
                    metadata_str = json.dumps(metadata, ensure_ascii=False).lower()
                    if query.lower() in metadata_str:
                        evidence_info = self._get_evidence_info(filename, filepath, metadata_file)
                        evidence_list.append(evidence_info)
                except:
                    pass
        
        return evidence_list
    
    def _get_evidence_info(self, filename: str, filepath: str, metadata_file: str) -> Dict[str, Any]:
        """証拠情報を取得"""
        evidence_info = {
            'filename': filename,
            'filepath': filepath,
            'size': os.path.getsize(filepath),
            'created': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat(),
            'metadata': None
        }
        
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    evidence_info['metadata'] = json.load(f)
            except:
                pass
        
        return evidence_info
    
    def get_evidence_stats(self) -> Dict[str, Any]:
        """証拠統計情報を取得"""
        if not self.ensure_dir():
            return {}
        
        files = os.listdir(self.evidence_dir)
        image_files = [f for f in files if f.endswith('.jpg')]
        metadata_files = [f for f in files if f.endswith('_metadata.json')]
        
        total_size = 0
        for filename in image_files:
            filepath = os.path.join(self.evidence_dir, filename)
            total_size += os.path.getsize(filepath)
        
        # 最新と最古のファイル
        if image_files:
            image_files.sort()
            oldest_file = image_files[0]
            newest_file = image_files[-1]
            
            oldest_path = os.path.join(self.evidence_dir, oldest_file)
            newest_path = os.path.join(self.evidence_dir, newest_file)
            
            oldest_time = datetime.fromtimestamp(os.path.getctime(oldest_path))
            newest_time = datetime.fromtimestamp(os.path.getctime(newest_path))
        else:
            oldest_time = newest_time = None
        
        return {
            'total_images': len(image_files),
            'total_metadata': len(metadata_files),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'oldest_image': oldest_time.isoformat() if oldest_time else None,
            'newest_image': newest_time.isoformat() if newest_time else None,
            'date_range_days': (newest_time - oldest_time).days if oldest_time and newest_time else 0
        }
    
    def export_evidence(self, output_dir: str, start_date: str = None, end_date: str = None):
        """証拠画像をエクスポート"""
        if not self.ensure_dir():
            return False
        
        # 出力ディレクトリを作成
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        files = os.listdir(self.evidence_dir)
        image_files = [f for f in files if f.endswith('.jpg')]
        
        exported_count = 0
        
        for filename in image_files:
            filepath = os.path.join(self.evidence_dir, filename)
            file_time = datetime.fromtimestamp(os.path.getctime(filepath))
            
            # 日付フィルタ
            if start_date:
                start_dt = datetime.fromisoformat(start_date)
                if file_time < start_dt:
                    continue
            
            if end_date:
                end_dt = datetime.fromisoformat(end_date)
                if file_time > end_dt:
                    continue
            
            # ファイルをコピー
            dest_path = os.path.join(output_dir, filename)
            shutil.copy2(filepath, dest_path)
            
            # メタデータもコピー
            metadata_file = filepath.replace('.jpg', '_metadata.json')
            if os.path.exists(metadata_file):
                dest_metadata = dest_path.replace('.jpg', '_metadata.json')
                shutil.copy2(metadata_file, dest_metadata)
            
            exported_count += 1
        
        print(f"エクスポート完了: {exported_count}個のファイルを {output_dir} にコピーしました")
        return True
    
    def cleanup_old_evidence(self, days: int, dry_run: bool = True):
        """古い証拠画像を削除"""
        if not self.ensure_dir():
            return False
        
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        files = os.listdir(self.evidence_dir)
        image_files = [f for f in files if f.endswith('.jpg')]
        
        to_delete = []
        
        for filename in image_files:
            filepath = os.path.join(self.evidence_dir, filename)
            file_time = os.path.getctime(filepath)
            
            if file_time < cutoff_date:
                to_delete.append((filename, filepath))
        
        if dry_run:
            print(f"削除対象: {len(to_delete)}個のファイル（{days}日以上古い）")
            for filename, filepath in to_delete[:10]:  # 最初の10個を表示
                print(f"  - {filename}")
            if len(to_delete) > 10:
                print(f"  ... 他 {len(to_delete) - 10}個")
        else:
            deleted_count = 0
            for filename, filepath in to_delete:
                try:
                    os.remove(filepath)
                    
                    # メタデータも削除
                    metadata_file = filepath.replace('.jpg', '_metadata.json')
                    if os.path.exists(metadata_file):
                        os.remove(metadata_file)
                    
                    deleted_count += 1
                except Exception as e:
                    print(f"削除エラー {filename}: {e}")
            
            print(f"削除完了: {deleted_count}個のファイルを削除しました")
        
        return True

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='証拠保全画像管理ツール')
    parser.add_argument('--dir', default='evidence_images', help='証拠画像ディレクトリ')
    
    subparsers = parser.add_subparsers(dest='command', help='利用可能なコマンド')
    
    # 一覧表示コマンド
    list_parser = subparsers.add_parser('list', help='証拠画像一覧を表示')
    list_parser.add_argument('--limit', type=int, default=20, help='表示件数')
    list_parser.add_argument('--offset', type=int, default=0, help='オフセット')
    
    # 検索コマンド
    search_parser = subparsers.add_parser('search', help='証拠画像を検索')
    search_parser.add_argument('query', help='検索クエリ')
    
    # 統計コマンド
    stats_parser = subparsers.add_parser('stats', help='統計情報を表示')
    
    # エクスポートコマンド
    export_parser = subparsers.add_parser('export', help='証拠画像をエクスポート')
    export_parser.add_argument('output_dir', help='出力ディレクトリ')
    export_parser.add_argument('--start-date', help='開始日 (YYYY-MM-DD)')
    export_parser.add_argument('--end-date', help='終了日 (YYYY-MM-DD)')
    
    # クリーンアップコマンド
    cleanup_parser = subparsers.add_parser('cleanup', help='古い証拠画像を削除')
    cleanup_parser.add_argument('days', type=int, help='削除する日数')
    cleanup_parser.add_argument('--execute', action='store_true', help='実際に削除を実行')
    
    args = parser.parse_args()
    
    manager = EvidenceManager(args.dir)
    
    if args.command == 'list':
        evidence_list = manager.list_evidence(args.limit, args.offset)
        print(f"証拠画像一覧 ({len(evidence_list)}件):")
        for evidence in evidence_list:
            print(f"  {evidence['filename']} ({evidence['size']} bytes) - {evidence['created']}")
            if evidence['metadata']:
                client_addr = evidence['metadata'].get('client_address', 'Unknown')
                print(f"    クライアント: {client_addr}")
    
    elif args.command == 'search':
        evidence_list = manager.search_evidence(args.query)
        print(f"検索結果 ({len(evidence_list)}件):")
        for evidence in evidence_list:
            print(f"  {evidence['filename']} ({evidence['size']} bytes)")
    
    elif args.command == 'stats':
        stats = manager.get_evidence_stats()
        print("証拠統計情報:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    elif args.command == 'export':
        manager.export_evidence(args.output_dir, args.start_date, args.end_date)
    
    elif args.command == 'cleanup':
        manager.cleanup_old_evidence(args.days, not args.execute)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
