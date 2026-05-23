from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "demo"


TERMINAL_BG = "#0b1020"
TITLE_BG = "#141b2d"
TEXT = "#d7e1f0"
PROMPT = "#7dd3fc"
MUTED = "#94a3b8"
SUCCESS = "#86efac"
WARN = "#fbbf24"


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def render_terminal(name: str, title: str, body: str, width: int = 1440) -> None:
    mono = font(26)
    title_font = font(24)
    lines = dedent(body).strip("\n").splitlines()
    line_height = 36
    pad_x = 42
    pad_y = 34
    title_h = 58
    height = title_h + pad_y * 2 + max(1, len(lines)) * line_height

    img = Image.new("RGB", (width, height), TERMINAL_BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width, title_h), fill=TITLE_BG)
    draw.ellipse((24, 21, 40, 37), fill="#ef4444")
    draw.ellipse((52, 21, 68, 37), fill="#f59e0b")
    draw.ellipse((80, 21, 96, 37), fill="#22c55e")
    draw.text((124, 15), title, fill=MUTED, font=title_font)

    y = title_h + pad_y
    for raw in lines:
        color = TEXT
        if raw.startswith("$"):
            color = PROMPT
        elif raw.startswith("ok") or raw.startswith("{") or "status" in raw:
            color = SUCCESS
        elif "fallback" in raw.lower() or "evidence" in raw.lower():
            color = WARN
        draw.text((pad_x, y), raw, fill=color, font=mono)
        y += line_height

    img.save(OUT / name)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    render_terminal(
        "api-health.png",
        "ChronoRAG API health check",
        """
        $ CHRONORAG_LIGHT=1 .venv/bin/python -m app.uvicorn_runner
        INFO:     Started server process
        INFO:     Uvicorn running on http://127.0.0.1:8000

        $ curl http://127.0.0.1:8000/healthz
        {"status":"ok"}
        """,
    )

    render_terminal(
        "cli-ingest.png",
        "ChronoRAG sample ingest",
        """
        $ CHRONORAG_LIGHT=1 .venv/bin/python -m cli.chronorag_cli ingest \\
            data/sample/docs/aihistory1.txt \\
            data/sample/docs/aihistory2.txt \\
            data/sample/docs/aihistory3.txt
        {
          "ingested_chunks": 24052,
          "source_files": [
            "data/sample/docs/aihistory1.txt",
            "data/sample/docs/aihistory2.txt",
            "data/sample/docs/aihistory3.txt"
          ],
          "chunk_ids": ["1367bd...", "d7b9d8...", "..."]
        }
        """,
    )

    render_terminal(
        "cli-answer.png",
        "ChronoRAG temporal answer",
        """
        $ CHRONORAG_LIGHT=1 .venv/bin/python -m cli.chronorag_cli answer \\
            --query "Europe GDP per capita in 1870 (1990 intl$)" \\
            --mode INTELLIGENT --axis valid
        Answer:
        ChronoGuard fallback mode - unable to reach the language model, supplying evidence digest.
        Query: Europe GDP per capita in 1870 (1990 intl$)
        Key evidence:
        1. Per capita GDP in
           Window: 1000-01-01 -> 2006-12-31
           Source: file:///mnt/data/world_economy.pdf
        2. From 1870 to 1913, world capita GDP rose 1.3 per cent a year...
        """,
    )

    render_terminal(
        "attribution-card.png",
        "ChronoRAG attribution card",
        """
        Attribution Card:
          Mode: INTELLIGENT
          Axis: valid
          Window: 1870-01-01T00:00:00+00:00 -> 1991-01-01T00:00:00+00:00
          Sources:
            1. file:///mnt/data/world_economy.pdf (score 0.21)
               Quote: Per capita GDP in
               Interval: 1000-01-01 -> 2006-12-31
            2. file:///mnt/data/world_economy.pdf (score 0.30)
               Quote: From 1870 to 1913, world capita GDP rose 1.3 per cent a year...
               Interval: 1870-01-01 -> 1913-12-31
        """,
    )

    render_terminal(
        "controller-stats.png",
        "ChronoRAG controller stats",
        """
        Controller Stats:
          hops_used: 1
          coverage: 1.0
          authority: 0.2
          latency_ms: 164
          rerank_method: ce

        Audit Trail:
          - chronosanity_block
              file:///mnt/data/world_economy.pdf <-> file:///mnt/data/world_economy.pdf
              overlap 1.000
        """,
    )


if __name__ == "__main__":
    main()
