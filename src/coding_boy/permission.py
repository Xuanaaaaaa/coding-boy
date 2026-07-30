import re
import json
from pathlib import Path
from typing import Optional, Any


class PermissionManager:
    """权限管理器：负责加载和检查权限规则"""

    # 危险命令模式
    DANGEROUS_PATTERNS = [
        re.compile(r"\brm\s"),
        re.compile(r"\bgit\s+(push|reset|clean|checkout\s+\.)"),
        re.compile(r"\bsudo\b"),
        re.compile(r"\bmkfs\b"),
        re.compile(r"\bdd\s"),
        re.compile(r">\s*/dev/"),
        re.compile(r"\bkill\b"),
        re.compile(r"\bpkill\b"),
        re.compile(r"\breboot\b"),
        re.compile(r"\bshutdown\b"),
        re.compile(r"\bdel\s", re.IGNORECASE),
        re.compile(r"\brmdir\s", re.IGNORECASE),
        re.compile(r"\bformat\s", re.IGNORECASE),
        re.compile(r"\btaskkill\s", re.IGNORECASE),
        re.compile(r"\bRemove-Item\s", re.IGNORECASE),
        re.compile(r"\bStop-Process\s", re.IGNORECASE),
    ]

    # 缓存的权限规则
    _cached_rules: Optional[dict] = None

    # 只读工具
    READ_TOOLS = ["read_file", "grep_search", "tool_search", "web_search"]
    EDIT_TOOLS = ["write_file", "edit_file"]
    
    @classmethod
    def is_dangerous(cls, command: str) -> bool:
        """检查命令是否危险"""
        return any(p.search(command) for p in cls.DANGEROUS_PATTERNS)

    @classmethod
    def _parse_rule(cls, rule: str) -> dict:
        """解析规则字符串为结构化字典"""
        m = re.match(r"^([a-z_]+)\((.+)\)$", rule)
        if m:
            return {"tool": m.group(1), "pattern": m.group(2)}
        return {"tool": rule, "pattern": None}

    @classmethod
    def _load_settings(cls, path: Path) -> dict:
        """加载配置文件"""
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    @classmethod
    def load_rules(cls) -> dict:
        """从配置文件加载权限规则，并缓存结果"""
        if cls._cached_rules is not None:
            return cls._cached_rules

        allow: list[dict] = []
        deny: list[dict] = []

        # 加载用户级和项目级配置
        user_settings = cls._load_settings(Path.home() / ".coding-boy" / "settings.json")
        project_settings = cls._load_settings(Path.cwd() / ".coding-boy" / "settings.json")

        for settings in [user_settings, project_settings]:
            if not settings or "permissions" not in settings:
                continue
            perms = settings["permissions"]
            for r in perms.get("allow", []):
                allow.append(cls._parse_rule(r))
            for r in perms.get("deny", []):
                deny.append(cls._parse_rule(r))

        cls._cached_rules = {"allow": allow, "deny": deny}
        return cls._cached_rules

    @classmethod
    def check_permission_rules(cls, tool: str, inp: dict[str, Any]) -> bool | None:
        """
        检查工具调用是否有权限

        Args:
            tool: 工具名称
            inp: 工具调用的参数字典

        Returns:
            True 表示允许，False 表示拒绝
        """
        rules = cls.load_rules()

        # 检查 deny 规则
        for rule in rules["deny"]:
            if cls._match_rule(rule, tool, inp):
                return False

        # 检查 allow 规则
        for rule in rules["allow"]:
            if cls._match_rule(rule, tool, inp):
                return True

        # 默认行为：没有匹配任何规则时的处理
        # 可以根据需求修改，比如默认拒绝或默认允许
        return None

    @classmethod
    def _match_rule(cls, rule: dict, tool: str, inp: dict[str, Any]) -> bool:
        """
        检查工具调用是否匹配规则

        Args:
            rule: 解析后的规则 {"tool": "bash", "pattern": "rm *"}
            tool: 工具名称
            inp: 工具调用的参数字典

        Returns:
            是否匹配
        """
        if rule["tool"] != tool:
            return False

        if rule["pattern"] is None:
            return True  # 没有参数模式，匹配整个工具

        # 根据工具类型获取匹配值
        value = ""
        if tool == "run_shell":
            value = inp.get("command", "")
        elif "path" in inp:
            value = inp["path"]
        else:
            return True  # 无法匹配的参数，默认通过

        # 支持通配符匹配
        pattern = rule["pattern"]
        if pattern.endswith("*"):
            return value.startswith(pattern[:-1])
        return value == pattern

    @classmethod
    def clear_cache(cls):
        """清除缓存（用于测试或重新加载配置）"""
        cls._cached_rules = None

    @classmethod
    def check_permission(
        cls,
        tool_name: str,
        inp: dict,
        mode: str = "default",
        plan_file_path: str | None = None,
    ) -> dict:
        """Returns {"action": "allow"|"deny"|"confirm", "message": ...}"""
        if mode == "bypassPermissions":
            return {"action": "allow"}
    
        # Layer 1: 配置文件规则（deny 优先）
        rule_result = cls.check_permission_rules(tool_name, inp)
        if rule_result is False:
            return {"action": "deny", "message": f"Denied by permission rule for {tool_name}"}
        elif rule_result:
            return {"action": "allow"}
    
        # 读工具永远安全
        if tool_name in cls.READ_TOOLS:
            return {"action": "allow"}
    
        # 权限模式检查
        if mode == "plan":
            if tool_name in cls.EDIT_TOOLS:
                file_path = inp.get("path")
                if plan_file_path and file_path == plan_file_path:
                    return {"action": "allow"}
                return {"action": "deny", "message": f"Blocked in plan mode: {tool_name}"}
            if tool_name == "run_shell":
                return {"action": "deny", "message": "Shell commands blocked in plan mode"}
    
        if mode == "acceptEdits" and tool_name in cls.EDIT_TOOLS:
            return {"action": "allow"}
    
        # Layer 2: 内置危险模式检查
        needs_confirm = False
        confirm_message = ""
    
        if tool_name == "run_shell" and cls.is_dangerous(inp.get("command", "")):
            needs_confirm = True
            confirm_message = inp.get("command", "")
        elif tool_name == "write_file" and not Path(inp.get("path", "")).exists():
            needs_confirm = True
            confirm_message = f"write new file: {inp.get('path', '')}"
        elif tool_name == "edit_file" and not Path(inp.get("path", "")).exists():
            needs_confirm = True
            confirm_message = f"edit non-existent file: {inp.get('path', '')}"
    
        if needs_confirm:
            if mode == "dontAsk":
                return {"action": "deny", "message": f"Auto-denied (dontAsk mode): {confirm_message}"}
            return {"action": "confirm", "message": confirm_message}
    
        return {"action": "allow"}
