#!/usr/bin/env python3
"""Создаёт три демо-изображения: фото, скриншот, график (только stdlib)."""

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo_images"


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def save_png(path: Path, width: int, height: int, rows: list[list[tuple[int, int, int]]]) -> None:
    raw = b""
    for row in rows:
        raw += b"\x00" + bytes(c for px in row for c in px)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", zlib.compress(raw, 9))
    png += _png_chunk(b"IEND", b"")
    path.write_bytes(png)


def _blank(w: int, h: int, color: tuple[int, int, int]) -> list[list[tuple[int, int, int]]]:
    return [[color] * w for _ in range(h)]


def _rect(
    rows: list[list[tuple[int, int, int]]],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int],
) -> None:
    for y in range(max(0, y0), min(y1, len(rows))):
        for x in range(max(0, x0), min(x1, len(rows[0]))):
            rows[y][x] = color


def make_photo(path: Path) -> None:
    w, h = 480, 320
    rows = _blank(w, h, (135, 206, 235))
    _rect(rows, 0, int(h * 0.62), w, h, (46, 139, 87))
    _rect(rows, 80, 140, 200, 220, (139, 90, 43))
    _rect(rows, 80, 90, 200, 140, (34, 100, 34))
    for y in range(40, 140):
        for x in range(320, 420):
            if (x - 370) ** 2 + (y - 90) ** 2 < 50**2:
                rows[y][x] = (255, 220, 80)
    save_png(path, w, h, rows)


def make_screenshot(path: Path) -> None:
    w, h = 520, 360
    rows = _blank(w, h, (240, 240, 240))
    _rect(rows, 0, 0, w, 36, (30, 100, 200))
    _rect(rows, 20, 56, 500, 300, (255, 255, 255))
    _rect(rows, 40, 150, 160, 190, (30, 100, 200))
    save_png(path, w, h, rows)


def make_chart(path: Path) -> None:
    w, h = 500, 340
    rows = _blank(w, h, (255, 255, 255))
    _rect(rows, 60, 50, 62, 280, (0, 0, 0))
    _rect(rows, 60, 278, 460, 282, (0, 0, 0))
    for x, top, color in [
        (120, 220, (70, 130, 180)),
        (200, 180, (60, 179, 113)),
        (280, 140, (255, 165, 0)),
        (360, 100, (205, 92, 92)),
    ]:
        _rect(rows, x, top, x + 50, 280, color)
    save_png(path, w, h, rows)


def main() -> None:
    DEMO.mkdir(exist_ok=True)
    make_photo(DEMO / "photo.png")
    make_screenshot(DEMO / "screenshot.png")
    make_chart(DEMO / "chart.png")
    print(f"Создано в {DEMO}:")
    for p in sorted(DEMO.iterdir()):
        print(f"  - {p.name} ({p.stat().st_size} байт)")


if __name__ == "__main__":
    main()
