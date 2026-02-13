# -*- coding: utf-8 -*-
import json
from pathlib import Path
from datetime import datetime
from conf import BASE_DIR

class UploadHistory:
    def __init__(self):
        self.history_file = BASE_DIR / 'videos' / 'history.json'
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
    
    def get_latest_records(self, limit=10):
        history = self._load_history()
        return history[:limit]
    
    def _load_history(self):
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _save_history(self, history):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def add_record(self, folder_name, upload_results, account):
        history = self._load_history()
        success_count = sum(1 for s in upload_results.values() if s == '成功')
        failed_count = sum(1 for s in upload_results.values() if s == '失败')
        result = 'fail' if failed_count > 0 else 'success'
        
        record = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'account': account,
            'video': folder_name,
            'platforms': success_count + failed_count,
            'result': result,
            'details': upload_results
        }
        
        history.insert(0, record)
        self._save_history(history[:100])

_upload_history = None

def get_upload_history():
    global _upload_history
    if _upload_history is None:
        _upload_history = UploadHistory()
    return _upload_history
