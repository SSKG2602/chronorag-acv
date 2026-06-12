#!/usr/bin/env python3
"""Generate paper-support figures from documented ChronoRAG results.

This script is standalone by design: it imports no project internals and writes
only files under docs/paper_assets/.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape


OUT_DIR = Path(__file__).resolve().parent


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_framework_svg()
    write_finalization_svg()
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"matplotlib unavailable; using standard-library PNG fallback: {exc}")
        write_retrieval_comparison_fallback()
        write_ablation_study_fallback()
        write_answer_validation_fallback()
        write_temporal_heatmap_fallback()
        print(f"Generated paper assets in {OUT_DIR}")
        return

    write_retrieval_comparison(plt, np)
    write_ablation_study(plt, np)
    write_answer_validation(plt, np)
    write_temporal_heatmap(plt, np)
    print(f"Generated paper assets in {OUT_DIR}")


def write_framework_svg() -> None:
    blocks = [
        ("Query", 40, 60),
        ("Candidate Retrieval", 250, 60),
        ("Temporal Contextual Chunking", 460, 60),
        ("Valid-Time / Transaction-Time Separation", 670, 60),
        ("Temporal Precision Scoring", 250, 180),
        ("Temporal Fusion", 460, 180),
        ("Forbidden-Time Handling", 670, 180),
        ("Source / Metric / Slot-Aware Finalization", 250, 300),
        ("ChronoSanity", 460, 300),
        ("Attribution Cards", 670, 300),
        ("Answer Synthesis", 460, 420),
        ("Answer-Contract Validation", 670, 420),
    ]
    edges = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 8),
        (8, 9),
        (9, 10),
        (10, 11),
    ]
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="920" height="540" viewBox="0 0 920 540">',
        "<defs>",
        '<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">',
        '<path d="M0,0 L0,6 L9,3 z" fill="#2f3a45" />',
        "</marker>",
        "</defs>",
        '<rect x="0" y="0" width="920" height="540" fill="#ffffff" />',
        '<text x="460" y="30" text-anchor="middle" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#1f2933">ChronoRAG Framework</text>',
    ]
    for start, end in edges:
        x1, y1 = blocks[start][1] + 170, blocks[start][2] + 36
        x2, y2 = blocks[end][1], blocks[end][2] + 36
        if blocks[start][2] != blocks[end][2]:
            x1, y1 = blocks[start][1] + 85, blocks[start][2] + 72
            x2, y2 = blocks[end][1] + 85, blocks[end][2]
        svg.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#2f3a45" stroke-width="2" marker-end="url(#arrow)" />'
        )
    for label, x, y in blocks:
        svg.extend(draw_block(label, x, y, 170, 72))
    svg.append("</svg>")
    (OUT_DIR / "chronorag_framework.svg").write_text("\n".join(svg) + "\n", encoding="utf-8")


def write_finalization_svg() -> None:
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="980" height="520" viewBox="0 0 980 520">',
        "<defs>",
        '<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">',
        '<path d="M0,0 L0,6 L9,3 z" fill="#2f3a45" />',
        "</marker>",
        "</defs>",
        '<rect x="0" y="0" width="980" height="520" fill="#ffffff" />',
        '<text x="490" y="34" text-anchor="middle" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#1f2933">Evidence Finalization Schematic</text>',
    ]
    columns = [
        (
            "Generic candidate evidence list",
            40,
            [
                "high semantic score, wrong date",
                "correct entity, transaction-time mismatch",
                "correct source, forbidden date",
                "correct date, wrong metric",
                "required slot missing",
            ],
        ),
        (
            "Temporal finalization controls",
            360,
            [
                "valid-time fit",
                "transaction-role penalty",
                "forbidden-time exclusion",
                "source/metric anchors",
                "slot coverage",
            ],
        ),
        (
            "Final evidence set",
            680,
            [
                "valid date",
                "correct source family",
                "correct metric/claim",
                "required slots covered",
                "attribution metadata attached",
            ],
        ),
    ]
    for title, x, items in columns:
        svg.append(
            f'<text x="{x + 130}" y="84" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#1f2933">{escape(title)}</text>'
        )
        for idx, item in enumerate(items):
            y = 115 + idx * 70
            svg.extend(draw_block(item, x, y, 260, 46, radius=8, fill="#f8fafc"))
    svg.append('<line x1="315" y1="270" x2="350" y2="270" stroke="#2f3a45" stroke-width="2" marker-end="url(#arrow)" />')
    svg.append('<line x1="635" y1="270" x2="670" y2="270" stroke="#2f3a45" stroke-width="2" marker-end="url(#arrow)" />')
    svg.append("</svg>")
    (OUT_DIR / "evidence_finalization_schematic.svg").write_text("\n".join(svg) + "\n", encoding="utf-8")


def draw_block(label: str, x: int, y: int, width: int, height: int, radius: int = 10, fill: str = "#eef6ff") -> list[str]:
    lines = wrap_label(label, max_chars=max(14, width // 8))
    line_height = 14
    start_y = y + height / 2 - ((len(lines) - 1) * line_height) / 2 + 5
    out = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}" stroke="#45607a" stroke-width="1.4" />'
    ]
    for idx, line in enumerate(lines):
        out.append(
            f'<text x="{x + width / 2:.1f}" y="{start_y + idx * line_height:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12.5" fill="#1f2933">{escape(line)}</text>'
        )
    return out


def wrap_label(label: str, max_chars: int) -> list[str]:
    words = label.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if current and len(candidate) > max_chars:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def write_retrieval_comparison(plt, np) -> None:
    labels = ["Generic Hit@1", "Generic Hit@5", "Forbidden Absent@5", "Category Primary Pass"]
    chronorag = [0.82, 0.90, 0.99, 0.96]
    baseline = [0.69, 0.86, 0.69, 0.48]
    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.bar(x - width / 2, chronorag, width, label="ChronoRAG Full", color="#2563eb")
    ax.bar(x + width / 2, baseline, width, label="Metadata Temporal RAG", color="#10b981")
    finish_grouped_axis(ax, labels, "Cross-Domain Retrieval Benchmark", "Score")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "layer2a_retrieval_comparison.png", dpi=220)
    plt.close(fig)


def write_ablation_study(plt, np) -> None:
    labels = ["Generic Hit@1", "Generic Hit@5", "Forbidden Absent@5", "Category Primary Pass"]
    series = {
        "ChronoRAG Full": [0.8250, 0.8950, 0.9950, 0.9625],
        "No Temporal Precision": [0.7500, 0.8500, 0.9450, 0.7500],
        "No Slot Assembler": [0.8300, 0.8900, 0.8150, 0.7750],
        "Score Only": [0.8150, 0.9850, 0.6500, 0.5625],
        "Metadata Temporal RAG": [0.6900, 0.8600, 0.6950, 0.4813],
    }
    colors = ["#2563eb", "#f59e0b", "#8b5cf6", "#ef4444", "#10b981"]
    x = np.arange(len(labels))
    width = 0.15
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    offset_start = -width * (len(series) - 1) / 2
    for idx, ((name, values), color) in enumerate(zip(series.items(), colors)):
        ax.bar(x + offset_start + idx * width, values, width, label=name, color=color)
    finish_grouped_axis(ax, labels, "Layer 2A Ablation Study", "Score")
    ax.legend(ncol=2, fontsize=8, loc="lower left", bbox_to_anchor=(0.0, 1.01))
    fig.tight_layout()
    fig.savefig(OUT_DIR / "layer2a_ablation_study.png", dpi=220)
    plt.close(fig)


def write_answer_validation(plt, np) -> None:
    labels = [
        "Deterministic\nhard-contract",
        "LLM judge\nsemantic",
        "Strict\ncombined",
        "Manual-audited\nacceptable",
    ]
    values = [0.76, 0.76, 0.70, 0.82]
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    bars = ax.bar(np.arange(len(labels)), values, color=["#2563eb", "#10b981", "#ef4444", "#8b5cf6"], width=0.55)
    ax.set_title("Natural-Language Temporal QA Validation", fontsize=15, fontweight="700")
    ax.set_ylabel("Pass Rate")
    ax.set_ylim(0, 1.05)
    ax.set_xticks(np.arange(len(labels)), labels)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.025, f"{value:.2f}", ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "layer2b_answer_validation.png", dpi=220)
    plt.close(fig)


def write_temporal_heatmap(plt, np) -> None:
    values = np.array(
        [
            [0.10, 0.20, 0.30],
            [0.20, 0.50, 0.70],
            [0.30, 0.70, 0.95],
        ]
    )
    semantic = ["Low", "Medium", "High"]
    temporal = ["Low", "Medium", "High"]
    fig, ax = plt.subplots(figsize=(6.7, 5.8))
    image = ax.imshow(values, cmap="viridis", vmin=0, vmax=1)
    ax.set_title("Temporal Fusion Scoring Schematic", fontsize=14, fontweight="700")
    ax.set_xlabel("Semantic relevance")
    ax.set_ylabel("Temporal fit")
    ax.set_xticks(np.arange(len(semantic)), semantic)
    ax.set_yticks(np.arange(len(temporal)), temporal)
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            color = "white" if values[i, j] > 0.55 else "#111827"
            ax.text(j, i, f"{values[i, j]:.2f}", ha="center", va="center", color=color, fontsize=11)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="Schematic score")
    fig.text(0.5, 0.025, "Schematic visualization; not a new experimental result.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(OUT_DIR / "temporal_scoring_heatmap.png", dpi=220)
    plt.close(fig)


def finish_grouped_axis(ax, labels: list[str], title: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=15, fontweight="700")
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, 1.08)
    ax.set_xticks(range(len(labels)), labels, rotation=12, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.legend(fontsize=9)


FONT_5X7 = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10011", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "/": ("00001", "00001", "00010", "00100", "01000", "10000", "10000"),
    "@": ("01110", "10001", "10111", "10101", "10111", "10000", "01110"),
    "%": ("11001", "11010", "00100", "01000", "10000", "01011", "10011"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


class Canvas:
    def __init__(self, width: int, height: int, bg: tuple[int, int, int] = (255, 255, 255)) -> None:
        self.width = width
        self.height = height
        self.pixels = bytearray(bg * (width * height))

    def rect(self, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.width, x + w), min(self.height, y + h)
        for yy in range(y0, y1):
            row = yy * self.width * 3
            for xx in range(x0, x1):
                idx = row + xx * 3
                self.pixels[idx : idx + 3] = bytes(color)

    def line(self, x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int]) -> None:
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        x, y = x1, y1
        while True:
            self.rect(x, y, 1, 1, color)
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def text(self, x: int, y: int, text: str, color: tuple[int, int, int] = (17, 24, 39), scale: int = 2) -> None:
        cursor = x
        for ch in text.upper():
            glyph = FONT_5X7.get(ch, FONT_5X7[" "])
            for gy, row in enumerate(glyph):
                for gx, value in enumerate(row):
                    if value == "1":
                        self.rect(cursor + gx * scale, y + gy * scale, scale, scale, color)
            cursor += 6 * scale

    def centered_text(self, center_x: int, y: int, text: str, color: tuple[int, int, int] = (17, 24, 39), scale: int = 2) -> None:
        width = len(text) * 6 * scale
        self.text(center_x - width // 2, y, text, color=color, scale=scale)

    def save(self, path: Path) -> None:
        import struct
        import zlib

        raw = bytearray()
        stride = self.width * 3
        for y in range(self.height):
            raw.append(0)
            raw.extend(self.pixels[y * stride : (y + 1) * stride])

        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        png = bytearray(b"\x89PNG\r\n\x1a\n")
        png.extend(chunk(b"IHDR", struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)))
        png.extend(chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        png.extend(chunk(b"IEND", b""))
        path.write_bytes(png)


def draw_chart(
    path: str,
    title: str,
    labels: list[str],
    series: dict[str, list[float]],
    ylabel: str,
    colors: list[tuple[int, int, int]],
    width: int = 1100,
    height: int = 680,
) -> None:
    canvas = Canvas(width, height)
    left, top, right, bottom = 90, 95, 40, 165
    plot_w = width - left - right
    plot_h = height - top - bottom
    axis = (31, 41, 55)
    grid = (225, 231, 239)
    canvas.centered_text(width // 2, 28, title, scale=3)
    canvas.text(20, top + plot_h // 2 - 20, ylabel, scale=2)
    for tick in range(0, 6):
        value = tick / 5
        y = top + plot_h - int(value * plot_h)
        canvas.line(left, y, width - right, y, grid)
        canvas.text(42, y - 7, f"{value:.1f}", scale=1)
    canvas.line(left, top, left, top + plot_h, axis)
    canvas.line(left, top + plot_h, width - right, top + plot_h, axis)

    groups = len(labels)
    names = list(series)
    group_w = plot_w / groups
    bar_w = max(10, int(group_w * 0.7 / len(names)))
    for gi, label in enumerate(labels):
        center = left + int(group_w * gi + group_w / 2)
        start = center - (bar_w * len(names)) // 2
        for si, name in enumerate(names):
            value = series[name][gi]
            bar_h = int(value * plot_h)
            x = start + si * bar_w
            y = top + plot_h - bar_h
            canvas.rect(x, y, bar_w - 3, bar_h, colors[si % len(colors)])
            canvas.centered_text(x + (bar_w - 3) // 2, y - 15, f"{value:.2f}", scale=1)
        for li, line in enumerate(wrap_label(label, 16)):
            canvas.centered_text(center, top + plot_h + 16 + li * 15, line, scale=1)

    legend_x = left
    legend_y = height - 72
    for idx, name in enumerate(names):
        x = legend_x + (idx % 3) * 330
        y = legend_y + (idx // 3) * 26
        canvas.rect(x, y, 18, 12, colors[idx % len(colors)])
        canvas.text(x + 26, y - 1, name, scale=1)
    canvas.save(OUT_DIR / path)


def write_retrieval_comparison_fallback() -> None:
    draw_chart(
        "layer2a_retrieval_comparison.png",
        "Cross-Domain Retrieval Benchmark",
        ["Generic Hit@1", "Generic Hit@5", "Forbidden Absent@5", "Category Primary Pass"],
        {
            "ChronoRAG Full": [0.82, 0.90, 0.99, 0.96],
            "Metadata Temporal RAG": [0.69, 0.86, 0.69, 0.48],
        },
        "Score",
        [(37, 99, 235), (16, 185, 129)],
    )


def write_ablation_study_fallback() -> None:
    draw_chart(
        "layer2a_ablation_study.png",
        "Layer 2A Ablation Study",
        ["Generic Hit@1", "Generic Hit@5", "Forbidden Absent@5", "Category Primary Pass"],
        {
            "ChronoRAG Full": [0.8250, 0.8950, 0.9950, 0.9625],
            "No Temporal Precision": [0.7500, 0.8500, 0.9450, 0.7500],
            "No Slot Assembler": [0.8300, 0.8900, 0.8150, 0.7750],
            "Score Only": [0.8150, 0.9850, 0.6500, 0.5625],
            "Metadata Temporal RAG": [0.6900, 0.8600, 0.6950, 0.4813],
        },
        "Score",
        [(37, 99, 235), (245, 158, 11), (139, 92, 246), (239, 68, 68), (16, 185, 129)],
        width=1220,
    )


def write_answer_validation_fallback() -> None:
    draw_chart(
        "layer2b_answer_validation.png",
        "Natural-Language Temporal QA Validation",
        ["Deterministic hard-contract", "LLM judge semantic", "Strict combined", "Manual-audited acceptable"],
        {
            "Pass Rate": [0.76, 0.76, 0.70, 0.82],
        },
        "Pass Rate",
        [(37, 99, 235)],
        width=980,
    )


def write_temporal_heatmap_fallback() -> None:
    canvas = Canvas(760, 660)
    canvas.centered_text(380, 28, "Temporal Fusion Scoring Schematic", scale=3)
    left, top, cell = 190, 130, 130
    values = [[0.10, 0.20, 0.30], [0.20, 0.50, 0.70], [0.30, 0.70, 0.95]]
    colors = [
        [(68, 1, 84), (72, 35, 116), (64, 67, 135)],
        [(52, 94, 141), (33, 145, 140), (69, 177, 112)],
        [(122, 209, 81), (189, 223, 38), (253, 231, 37)],
    ]
    canvas.centered_text(left + cell * 3 // 2, top + cell * 3 + 38, "Semantic relevance", scale=2)
    canvas.text(18, top + cell, "Temporal fit", scale=2)
    labels = ["Low", "Medium", "High"]
    for i, label in enumerate(labels):
        canvas.centered_text(left + i * cell + cell // 2, top - 28, label, scale=2)
        canvas.text(left - 88, top + i * cell + cell // 2 - 8, label, scale=2)
    for y in range(3):
        for x in range(3):
            canvas.rect(left + x * cell, top + y * cell, cell - 2, cell - 2, colors[y][x])
            text_color = (255, 255, 255) if values[y][x] < 0.45 else (17, 24, 39)
            canvas.centered_text(left + x * cell + cell // 2, top + y * cell + cell // 2 - 10, f"{values[y][x]:.2f}", color=text_color, scale=2)
    canvas.centered_text(380, 610, "Schematic visualization; not a new experimental result.", scale=1)
    canvas.save(OUT_DIR / "temporal_scoring_heatmap.png")


if __name__ == "__main__":
    main()
