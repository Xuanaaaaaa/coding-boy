from pathlib import Path
from .registry import tool
from typing import Annotated,Optional
from ..core import _find_actual_string
from ..file_system.file_state import file_state

@tool
def read_file(path: Annotated[str,"将要读取的文本文件路径"],
    start: Annotated[Optional[int], "起始行位置"] = None,
    end: Annotated[Optional[int], "结束行位置"] = None
) -> str:
    """
    读取指定路径的文件内容，可以选择读取的起始和结束区间，不选默认全部完整读取
    """
    try:
        file_path = Path(path).resolve()
        if not file_path.exists():
            return "Error: file not found"
        content = file_path.read_text(encoding="utf-8")
        file_state.record(file_path)
        lines = content.split("\n")
        if start is not None and end is not None:
            read_lines = lines[start:end+1]
        else:
            read_lines = lines
        numberd = "\n".join(f"{i+1:4d} | {line}" for i,line in enumerate(read_lines))
        return numberd
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def write_file(path: Annotated[str,"将要写入的文件的路径"], content: Annotated[str, "将要写入的内容"]) -> str:
    """
    给指定路径的文件中写入文本内容，尽量在写入新文件的时候使用
    """
    try:
        file_path = Path(path).resolve()
        if file_path.exists():
            if not file_state.has_record(file_path):
                return "Error: You must read this file before writing"
            if file_state.changed(file_path):
                return (
                    "Warning: "
                    "file was modified externally. "
                    "Please read_file again."
                )
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        file_state.record(file_path)
        lines = content.split("\n")
        line_count = len(lines)
        preview = "\n".join(f"{i+1:4d} | {l} " for i, l in enumerate(lines[0:10]) )
        trunc = f"\n  ... ({line_count} lines total)" if line_count > 10 else ""
        print(f"Successfully wrote to {file_path} ({line_count} lines)\n\n{preview}{trunc}")
        return f"Successfully wrote to {file_path} ({line_count} lines)\n\n{preview}{trunc}"
    except Exception as e:
        return f"Error writing file: {e}"

@tool
def edit_file(path: Annotated[str, "将要编辑的文件的路径"],
    old_string: Annotated[str, "编辑前的内容"],
    new_string: Annotated[str, "编辑后的内容"]
) -> str:
    """
    对文件进行编辑，如果文件已经存在，优先使用这个工具
    """
    try:
        file_path = Path(path).resolve()
        if file_path.exists():
            if not file_state.has_record(file_path):
                return "Error: You must read this file before editing"
            if file_state.changed(file_path):
                return (
                    "Warning: "
                    "file was modified externally. "
                    "Please read_file again."
                )
        content = file_path.read_text(encoding="utf-8")
        actual_old_string = _find_actual_string(content, old_string)
        if not actual_old_string :
            return f"Error old_string not found in {path}"
        count = content.count(actual_old_string)
        if count > 1:
            return f"Error old_string found {count} times in {path}, must be unique"
        updated = content.replace(actual_old_string,new_string)
        file_path.write_text(updated, encoding="utf-8")
        file_state.record(file_path)
        return f"Sucessfully edited {path}"
    except Exception as e:
        return f"Error editing file: {e}"
