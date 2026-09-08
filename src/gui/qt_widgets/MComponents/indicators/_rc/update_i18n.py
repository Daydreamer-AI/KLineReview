# scripts/update_i18n.py
import glob
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"ROOT目录：ROOT")
TRANS_DIR = os.path.join(ROOT, "_rc", "i18n")
os.makedirs(TRANS_DIR, exist_ok=True)

py_files = glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True)
ui_files = glob.glob(os.path.join(ROOT, "**", "*.ui"), recursive=True)

# print(f"py_files: {len(py_files)}")
# print("\n\n============================================================================\n\n")
# print(f"ui_files: {ui_files}")

langs = ["en_US", "zh_CN", "zh_HK"]
for lang in langs:
    ts_path = os.path.join(TRANS_DIR, f"indicators_{lang}.ts")
    cmd = ["pylupdate5", *py_files, *ui_files, "-ts", ts_path]
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    # 顺手编译 qm
    subprocess.run(["lrelease", ts_path], check=True)