import os
from datetime import datetime, timedelta

from fastapi import Depends
from requests import Session

from app.data.repositories import QARepository
from app.database import get_db

LOG_DIR = "logs"
FEEDBACK_LOG = os.path.join(LOG_DIR, "feedback.log")
USAGE_LOG = os.path.join(LOG_DIR, "usage.log")

def log_usage(query: str, sources: list):
    """记录问题日志"""
    timestamp = datetime.now().isoformat()
    source_list = ",".join({s['source'] for s in sources})
    
    log_entry = f"{timestamp}|{query}|{source_list}\n"
    
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(USAGE_LOG, "a", encoding="utf-8") as f:  # 确保存在编码参数
        f.write(log_entry)

def log_feedback(feedback_data: dict):
    """记录反馈日志"""
    timestamp = datetime.now().isoformat()
    log_entry = f"{feedback_data.get('timestamp')}{timestamp}|{feedback_data.get('feedback')}|{feedback_data.get('question')}\n"
    
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry)

def calculate_stats(db: Session = Depends(get_db)):
    """计算统计信息"""
    today = datetime.now().date()
    
    # 从数据库获取总问题数和今日问题数
    repo = QARepository(db)
    total_count = repo.get_total_interactions_count()
    today_count = repo.get_today_interactions_count(today)
    
    return {
        "total_count": total_count,
        "today_count": today_count,
    }