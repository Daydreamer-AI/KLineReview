import glob
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"ROOT目录：{ROOT}")
TRANS_DIR = os.path.join(ROOT, "resources", "i18n")
os.makedirs(TRANS_DIR, exist_ok=True)

# 需要排除的目录（库3自带翻译）
EXCLUDE_DIRS = [
    "qfluentwidgets",           # qfluentwidgets控件库，自带翻译
    "build",                # 构建产物
    "dist",                 # 发布产物
    ".venv",                # 虚拟环境
    "venv",                 # 虚拟环境
    "__pycache__",          # Python 缓存
    "node_modules",         # 前端依赖（如果有）
]

def is_excluded(path):
    """检查路径是否在排除列表中"""
    path_norm = path.replace("\\", "/")  # Windows 兼容
    for exclude in EXCLUDE_DIRS:
        if f"/{exclude}/" in f"/{path_norm}/":
            return True
    return False

# 收集所有 .py 文件，排除指定目录
py_files = [
    f for f in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True)
    if not is_excluded(f)
]

# 收集所有 .ui 文件，排除指定目录
ui_files = [
    f for f in glob.glob(os.path.join(ROOT, "**", "*.ui"), recursive=True)
    if not is_excluded(f)
]

# print(f"py_files: {len(py_files)}")
# print(f"ui_files: {len(ui_files)}")
# print(f"排除后 py_files: {py_files}")
# print(f"排除后 ui_files: {ui_files}")

langs = ["en_US", "zh_CN", "zh_HK"]
for lang in langs:
    ts_path = os.path.join(TRANS_DIR, f"klinereview_{lang}.ts")
    # 添加 -noobsolete 参数
    cmd = ["pylupdate5", "-noobsolete", *py_files, *ui_files, "-ts", ts_path]
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    subprocess.run(["lrelease", ts_path], check=True)