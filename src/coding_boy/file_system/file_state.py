from pathlib import Path
import json

class FileState:
    def __init__(self, state_file: str | None = None):
        if state_file is None:
            _base_dir = Path(__file__).resolve().parent.parent
            state_file = str(_base_dir / ".agent" / "state.json")
        self.state_path = Path(state_file)
        # 文件路径 -> mtime
        self.files: dict[str, float] = {}
        self.load()

    def load(self):
        """
        从本地恢复状态
        """
        if not self.state_path.exists():
            return
        try:
            self.files = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            self.files = {}

    def save(self):
        """
        保存状态
        """
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(self.files, indent=2),encoding="utf-8")
        
    def record(self, path: Path):
        """
        记录文件当前mtime
        """
        path = path.resolve()
        self.files[str(path)] = (path.stat().st_mtime)
        self.save()

    def has_record(self, path: Path) -> bool:
        path = path.resolve()
        return str(path) in self.files

    def changed(self, path: Path) -> bool:
        """
        判断文件是否被外部修改
        """
        path = path.resolve()
        old_mtime = self.files.get(
            str(path)
        )
        if old_mtime is None:
            return True
        current_mtime = (path.stat().st_mtime)
        return current_mtime != old_mtime

file_state = FileState()