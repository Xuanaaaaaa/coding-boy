import json
import uuid
from pathlib import Path
from datetime import datetime
SESSION_DIR = Path.home() / ".coding-boy" / "sessions"

def generate_session_id() -> str:
    """生成会话 ID：时间戳 + 短 UUID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"{timestamp}_{short_uuid}"
    
def save_session(session_id: str, messages: list[dict]) -> None:
    """保存会话历史消息"""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSION_DIR / f"{session_id}.json"
    if path.exists():
        existing_data = json.loads(path.read_text())
        start_time = existing_data.get("startTime", datetime.now().isoformat())
    else:
        start_time = datetime.now().isoformat()
    session_data = {
        "id": session_id,
        "messages": messages,
        "startTime": start_time,
    }
    path.write_text(json.dumps(session_data, indent=2))

def load_session(session_id: str) -> list[dict] | None:
    """加载会话历史消息"""
    path = SESSION_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return data.get("messages", [])
    
def get_latest_session_id() -> str | None:
    sessions = list_sessions()
    if not sessions: 
        return None
    sessions.sort(key=lambda s: s.get("startTime", ""), reverse=True)
    return sessions[0].get("id")

def list_sessions() -> list[dict]:
    """列出所有会话"""
    if not SESSION_DIR.exists():
        return []
    sessions = []
    for file in SESSION_DIR.glob("*.json"):
        try:
            data = json.loads(file.read_text())
            sessions.append({
                "id": file.stem,  # 文件名（不含扩展名）作为 id
                "startTime": data.get("startTime", ""),
                "message_count": len(data.get("messages", []))
            })
        except Exception:
            continue
    return sessions
