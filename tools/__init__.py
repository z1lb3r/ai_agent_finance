"""
Initialize the tools package and export main functions.
"""

# Импортируем регистратор инструментов
from tools.registry import register_tool, get_all_tools, discover_tools_from_module

# Экспортируем публичный API
__all__ = [
    'register_tool',
    'get_all_tools',
    'discover_tools_from_module'
]

# Важно: Модули с инструментами НЕ импортируются здесь,
# чтобы избежать циклических импортов и непреднамеренной инициализации.
# Импорт модулей производится в main.py