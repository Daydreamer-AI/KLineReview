"""根据 src/resources/app.svg 生成 Windows .ico 与 macOS .icns。

在 PyInstaller 前运行：
    python packaging/make_icons.py

产物输出到 packaging/build/。
"""

import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QGuiApplication, QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "src" / "resources" / "app.svg"
BUILD_DIR = ROOT / "packaging" / "build"


def render_png(size: int, target: Path):
    app = QGuiApplication.instance() or QGuiApplication([])
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(0)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    QSvgRenderer(str(SVG)).render(painter, QRectF(0, 0, size, size))
    painter.end()
    image.save(str(target))


def make_ico(png_1024: Path, target: Path):
    base = Image.open(png_1024).convert("RGBA")
    base.thumbnail((256, 256), Image.LANCZOS)
    base.save(
        target,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


def make_iconset(png_1024: Path, iconset_dir: Path):
    iconset_dir.mkdir(parents=True, exist_ok=True)
    entries = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]
    base = Image.open(png_1024).convert("RGBA")
    for name, size in entries:
        resized = base.resize((size, size), Image.LANCZOS)
        resized.save(iconset_dir / name)


def main():
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    png_1024 = BUILD_DIR / "icon_1024.png"
    ico = BUILD_DIR / "KLineReview.ico"
    icns = BUILD_DIR / "KLineReview.icns"

    render_png(1024, png_1024)
    make_ico(png_1024, ico)
    print(f"generated: {ico}")

    if sys.platform == "darwin":
        iconset = BUILD_DIR / "KLineReview.iconset"
        make_iconset(png_1024, iconset)
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(icns)],
            check=True,
        )
        print(f"generated: {icns}")


if __name__ == "__main__":
    main()
