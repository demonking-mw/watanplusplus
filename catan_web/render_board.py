"""Render the Phase 1 board graph as SVG (no extra dependencies).

Usage from the repository root:

    python -m catan_web.render_board
    python -m catan_web.render_board -o catan_web/data/board.svg

Open the output file in a browser to inspect hex IDs, node IDs, and edges.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from catan_web.engine.coords import BOARD


def _bounds() -> tuple[float, float, float, float]:
    xs = [n.pos[0] for n in BOARD.nodes]
    ys = [n.pos[1] for n in BOARD.nodes]
    pad = 0.6
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


def render_svg() -> str:
    xmin, ymin, xmax, ymax = _bounds()
    width = xmax - xmin
    height = ymax - ymin
    scale = 80.0
    svg_w = width * scale
    svg_h = height * scale

    def tx(x: float, y: float) -> tuple[float, float]:
        return (x - xmin) * scale, (y - ymin) * scale

    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{svg_w:.1f}" height="{svg_h:.1f}" '
        f'viewBox="0 0 {svg_w:.1f} {svg_h:.1f}">'
    )
    lines.append('<rect width="100%" height="100%" fill="#e8f4ea"/>')

    for e in BOARD.edges:
        a = BOARD.node(e.node_ids[0])
        b = BOARD.node(e.node_ids[1])
        x1, y1 = tx(*a.pos)
        x2, y2 = tx(*b.pos)
        color = "#888" if len(e.hex_ids) == 1 else "#bbb"
        lines.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="2"/>'
        )

    for h in BOARD.hexes:
        pts = []
        for node_id in h.node_ids:
            x, y = tx(*BOARD.node(node_id).pos)
            pts.append(f"{x:.2f},{y:.2f}")
        cx, cy = tx(*h.center)
        lines.append(
            f'<polygon points="{" ".join(pts)}" fill="#fff" stroke="#2d6a4f" '
            f'stroke-width="2"/>'
        )
        lines.append(
            f'<text x="{cx:.2f}" y="{cy:.2f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="14" fill="#1b4332" '
            f'font-family="system-ui,sans-serif">H{h.id}</text>'
        )

    for n in BOARD.nodes:
        x, y = tx(*n.pos)
        if len(n.hex_ids) == 1:
            fill = "#e63946"
        elif len(n.hex_ids) == 2:
            fill = "#f4a261"
        else:
            fill = "#457b9d"
        lines.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="{fill}"/>')
        lines.append(
            f'<text x="{x:.2f}" y="{y - 10:.2f}" text-anchor="middle" '
            f'font-size="9" fill="#333" font-family="system-ui,sans-serif">'
            f'N{n.id}</text>'
        )

    lines.append(
        '<text x="8" y="16" font-size="11" fill="#333" '
        'font-family="system-ui,sans-serif">'
        'Red=1 hex (deg 2), Orange=2 hex (deg 3), Blue=3 hex (deg 3)</text>'
    )
    lines.append("</svg>")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render board graph to SVG")
    parser.add_argument(
        "-o",
        "--output",
        default="catan_web/data/board.svg",
        help="Output SVG path (default: catan_web/data/board.svg)",
    )
    args = parser.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_svg(), encoding="utf-8")
    print(f"Wrote {out.resolve()}")


if __name__ == "__main__":
    main()
