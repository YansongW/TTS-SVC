import os
import platform

def get_path_separator():
    """获取系统路径分隔符"""
    return '\\' if platform.system() == 'Windows' else '/'

def normalize_path(path):
    """标准化路径"""
    return os.path.normpath(path).replace('\\', '/')

def get_script_path(script_name):
    """获取脚本路径"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_dir = os.path.join(base_dir, 'scripts')
    return os.path.join(script_dir, script_name)

def ensure_directory(path):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)
    return path 