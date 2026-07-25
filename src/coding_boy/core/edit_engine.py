import re

def _normalize_quotes(s: str) -> str:
    """
    将文本中的智能引号转换为 ASCII 普通引号。
    
    例如:
    ‘hello’ -> 'hello'
    “hello” -> "hello"
    """
    s = re.sub(r"[\u2018\u2019\u2032]", "'", s)
    s = re.sub(r"[\u201c\u201d\u2033]", '"', s)
    return s

def _find_actual_string(file_content: str, search_string: str) -> str | None:
    """
    忽略引号的不同，找到真实匹配的字符串
    """
    if search_string in file_content:
        return search_string
    norm_search = _normalize_quotes(search_string)
    norm_file = _normalize_quotes(file_content)
    idx = norm_file.find(norm_search)
    if idx != -1:
        return file_content[idx:idx + len(search_string)]
    return None