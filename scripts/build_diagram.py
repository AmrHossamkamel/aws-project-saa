"""Build the editable draw.io diagram and matching SVG preview from local icons."""

from __future__ import annotations

import base64
import html
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ICON_DIR = DOCS / "icons"
WIDTH, HEIGHT = 1720, 1180

ICONS = {
    key: base64.b64encode((ICON_DIR / f"{key}.svg").read_bytes()).decode("ascii")
    for key in (
        "route53", "waf", "alb", "autoscaling", "ec2", "rds", "cloudfront",
        "s3", "ssm", "cloudwatch", "sns", "nat",
    )
}

frames = [
    ("aws", "AWS Cloud · us-east-1 (example deployment Region)", 25, 240, 1670, 925, "#F8FAFC", "#91A7B8", 2),
    ("vpc", "VPC · 10.20.0.0/16", 250, 285, 1180, 825, "#F2F8FC", "#4C7290", 2),
    ("aza", "Availability Zone A", 280, 430, 520, 625, "#FFFFFF", "#9BB5C6", 1),
    ("azb", "Availability Zone B", 830, 430, 520, 625, "#FFFFFF", "#9BB5C6", 1),
    ("pub_a", "Public subnet · 10.20.1.0/24", 300, 475, 480, 135, "#FFF8EB", "#E3AE52", 1),
    ("pub_b", "Public subnet · 10.20.2.0/24", 850, 475, 480, 135, "#FFF8EB", "#E3AE52", 1),
    ("app_a", "Private application subnet · 10.20.11.0/24", 300, 625, 480, 165, "#F3FAFC", "#76B6C8", 1),
    ("app_b", "Private application subnet · 10.20.12.0/24", 850, 625, 480, 165, "#F3FAFC", "#76B6C8", 1),
    ("db_a", "Isolated database subnet · 10.20.21.0/24", 300, 805, 480, 185, "#F7F4FC", "#A68AC5", 1),
    ("db_b", "Isolated database subnet · 10.20.22.0/24", 850, 805, 480, 185, "#F7F4FC", "#A68AC5", 1),
]

icons = [
    ("client", "", 55, 100, 130, 90, "browser"),
    ("route53", "Amazon Route 53", 235, 94, 85, 110, "route53"),
    ("cloudfront", "Amazon CloudFront", 1230, 94, 85, 110, "cloudfront"),
    ("waf", "AWS WAF", 70, 330, 85, 110, "waf"),
    ("alb", "Application Load Balancer", 790, 312, 95, 112, "alb"),
    ("nat_a", "NAT Gateway A", 340, 512, 65, 78, "nat"),
    ("nat_b", "NAT Gateway B", 890, 512, 65, 78, "nat"),
    ("ec2_a", "EC2 web target · private", 520, 668, 76, 94, "ec2"),
    ("ec2_b", "EC2 web target · private", 1070, 668, 76, 94, "ec2"),
    ("rds_a", "RDS writer · AZ A", 520, 854, 76, 92, "rds"),
    ("rds_b", "Multi-AZ standby · AZ B", 1070, 854, 76, 92, "rds"),
    ("ssm", "Systems Manager\nSession Manager", 65, 675, 96, 120, "ssm"),
    ("s3", "Private S3 static assets", 1500, 330, 90, 112, "s3"),
    ("cloudwatch", "CloudWatch\nEC2 · ALB · RDS", 1500, 545, 90, 112, "cloudwatch"),
    ("sns", "Amazon SNS alerts", 1500, 735, 90, 112, "sns"),
    ("asg", "EC2 Auto Scaling\nmin 2 · desired 2 · max 6\nCPU target 50%\nrequest burst step-out", 1485, 920, 120, 155, "autoscaling"),
]

notes = [
    ("nacl", "Security groups: ALB → EC2 TCP/8080 · EC2 → RDS TCP/3306  |  Tier NACLs + ephemeral return ports  |  Same-AZ NAT egress  |  RDS Multi-AZ failover", 350, 1050, 990, 28, "#EAF0F5", "#A8B9C6"),
]

edge_specs = [
    ("dns", "client", "route53", "", "#596F80", False),
    ("request", "route53", "alb", "Route 53 alias", "#D18B21", False),
    ("waf_attach", "waf", "alb", "", "#8C5BB7", True),
    ("oac_flow", "cloudfront", "s3", "OAC signed reads", "#6E57A5", False),
    ("alb_to_a", "alb", "ec2_a", "HTTP 8080", "#D18B21", False),
    ("alb_to_b", "alb", "ec2_b", "HTTP 8080", "#D18B21", False),
    ("app_to_db", "ec2_a", "rds_a", "MySQL 3306", "#577D9B", False),
    ("db_replica", "rds_a", "rds_b", "Sync replication", "#8059A6", True),
    ("ssm_flow", "ssm", "ssm_gate", "", "#548A73", True),
    ("notify", "cloudwatch", "sns", "Alarm actions", "#D0655C", False),
    ("scale", "ec2_b", "asg", "", "#548A73", True),
]

# Coordinates for deliberate orthogonal routes in both output formats.
paths = {
    "dns": [(185, 144), (235, 144)],
    "request": [(277, 204), (277, 225), (838, 225), (838, 312)],
    "waf_attach": [(155, 383), (500, 383), (790, 383)],
    "oac_flow": [(1272, 204), (1272, 260), (1545, 260), (1545, 330)],
    "alb_to_a": [(810, 420), (700, 500), (558, 668)],
    "alb_to_b": [(860, 420), (970, 500), (1108, 668)],
    "app_to_db": [(558, 762), (558, 854)],
    "db_replica": [(596, 900), (1070, 900)],
    "ssm_flow": [(161, 735), (215, 735), (250, 735)],
    "notify": [(1545, 657), (1545, 735)],
    "scale": [(1330, 708), (1390, 708), (1390, 990), (1485, 990)],
}

label_points = {
    "request": (560, 222),
    "oac_flow": (1410, 256),
    "alb_to_a": (678, 526),
    "alb_to_b": (1015, 526),
    "app_to_db": (650, 802),
    "db_replica": (825, 925),
    "notify": (1590, 701),
}


def mxfile() -> str:
    root = ET.Element("mxfile", {
        "host": "app.diagrams.net", "modified": "2026-10-28T00:00:00.000Z",
        "agent": "Codex", "version": "28.1.0", "type": "device",
    })
    diagram = ET.SubElement(root, "diagram", {"id": "scalelab-architecture", "name": "Architecture"})
    model = ET.SubElement(diagram, "mxGraphModel", {
        "dx": "1720", "dy": "1180", "grid": "1", "gridSize": "10",
        "guides": "1", "tooltips": "1", "connect": "1", "arrows": "1",
        "fold": "1", "page": "1", "pageScale": "1", "pageWidth": str(WIDTH),
        "pageHeight": str(HEIGHT), "math": "0", "shadow": "0",
    })
    cells = ET.SubElement(model, "root")
    ET.SubElement(cells, "mxCell", {"id": "0"})
    ET.SubElement(cells, "mxCell", {"id": "1", "parent": "0"})

    def vertex(cid, label, x, y, w, h, style, parent="1"):
        cell = ET.SubElement(cells, "mxCell", {
            "id": cid, "value": label, "style": style, "vertex": "1", "parent": parent,
        })
        ET.SubElement(cell, "mxGeometry", {
            "x": str(x), "y": str(y), "width": str(w), "height": str(h), "as": "geometry",
        })

    for cid, label, x, y, w, h, fill, stroke, sw in frames:
        vertex(cid, label,
               x, y, w, h,
               f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth={sw};fontColor=#334E62;fontSize=14;fontStyle=1;spacing=10;align=left;verticalAlign=top;arcSize=10;")

    # Arrows are placed before icons so their lines remain behind the components.
    for eid, source, target, label, color, dashed in edge_specs:
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
            f"strokeColor={color};strokeWidth=2;endArrow=block;endFill=1;"
            "fontColor=#40576A;fontSize=10;labelBackgroundColor=#FFFFFF;"
            + ("dashed=1;dashPattern=6 4;" if dashed else "")
        )
        cell = ET.SubElement(cells, "mxCell", {
            "id": eid, "value": label, "style": style, "edge": "1",
            "parent": "1", "source": source, "target": target,
        })
        geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        points = ET.SubElement(geometry, "Array", {"as": "points"})
        for x, y in paths[eid][1:-1]:
            ET.SubElement(points, "mxPoint", {"x": str(x), "y": str(y)})

    for cid, label, x, y, w, h, key in icons:
        if key == "browser":
            vertex(cid, "Browser / user", x, y, w, h,
                   "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#6F8799;strokeWidth=1.5;fontColor=#30485A;fontSize=13;fontStyle=1;arcSize=12;shadow=1;")
            vertex("browser_bar", "", x + 12, y + 13, w - 24, 14,
                   "rounded=1;whiteSpace=wrap;html=1;fillColor=#E9F0F5;strokeColor=#D1DDE5;arcSize=5;")
            vertex("browser_dot", "●  ●  ●", x + 15, y + 12, 44, 15,
                   "text;html=1;strokeColor=none;fillColor=none;fontColor=#8193A2;fontSize=8;align=left;verticalAlign=middle;")
            vertex("browser_page", "GET / · /site.css", x + 10, y + 41, w - 20, 22,
                   "text;html=1;strokeColor=none;fillColor=none;fontColor=#516B7E;fontSize=10;align=center;verticalAlign=middle;")
            continue
        data = ICONS[key]
        style = (
            f"shape=image;image=data:image/svg+xml;base64,{data};"
            "verticalLabelPosition=bottom;verticalAlign=top;align=center;imageAspect=0;"
            "aspect=fixed;html=1;labelBackgroundColor=#F8FAFC;fontColor=#20394D;"
            "fontSize=11;fontStyle=1;spacingTop=5;"
        )
        vertex(cid, label.replace("\n", "<br>"), x, y, w, h, style)

    vertex("ssm_gate", "", 250, 734, 1, 1,
           "ellipse;fillColor=none;strokeColor=none;opacity=0;")

    for cid, label, x, y, w, h, fill, stroke in notes:
        vertex(cid, label, x, y, w, h,
               f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontColor=#40576A;fontSize=10;fontStyle=1;align=center;verticalAlign=middle;arcSize=12;spacing=4;")

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def svg_preview() -> str:
    chunks = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="context-stroke"/></marker><filter id="shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="5" stdDeviation="7" flood-color="#193B55" flood-opacity=".08"/></filter></defs>',
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        '<text x="50" y="52" font-family="Arial,sans-serif" font-size="28" font-weight="800" fill="#142F43">SCALELAB</text>',
        '<text x="50" y="80" font-family="Arial,sans-serif" font-size="15" font-weight="600" fill="#607A8C">Route 53 alias → ALB for the app · CloudFront → private S3 for static assets · two Availability Zones</text>',
        '<text x="1535" y="52" text-anchor="end" font-family="Arial,sans-serif" font-size="11" font-weight="700" letter-spacing="2" fill="#8193A2">SOLUTION ARCHITECTURE</text>',
    ]

    def text_lines(x, y, lines, size=12, color="#30485A", weight=600, anchor="middle", gap=16):
        chunks.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">')
        for i, line in enumerate(lines):
            chunks.append(f'<tspan x="{x}" dy="{0 if i == 0 else gap}">{html.escape(line)}</tspan>')
        chunks.append('</text>')

    for cid, label, x, y, w, h, fill, stroke, sw in frames:
        chunks.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        if cid in ("aws", "vpc", "aza", "azb"):
            text_lines(x + (18 if cid in ("aws", "vpc") else w / 2), y + 28, [label], 14 if cid != "aws" else 16, "#334E62", 750, "start" if cid in ("aws", "vpc") else "middle")
        else:
            text_lines(x + 16, y + 24, [label], 12, "#425D70", 700, "start")

    for eid, source, target, label, color, dashed in edge_specs:
        pts = paths[eid]
        d = "M" + " L".join(f"{x},{y}" for x, y in pts)
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        chunks.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.5"{dash} marker-end="url(#arrow)"/>')
        lx, ly = label_points.get(eid, pts[len(pts) // 2])
        if label:
            label_w = max(88, min(360, len(label) * 6.4 + 20))
            chunks.append(f'<rect x="{lx-label_w/2:.1f}" y="{ly-18:.1f}" width="{label_w:.1f}" height="22" rx="8" fill="#FFFFFF" fill-opacity=".94" stroke="#E3EAF0"/>')
            text_lines(lx, ly - 3, [label], 10, "#475F71", 650)

    for cid, label, x, y, w, h, key in icons:
        if key == "browser":
            chunks.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#FFFFFF" stroke="#6F8799" stroke-width="1.5" filter="url(#shadow)"/>')
            chunks.append(f'<rect x="{x+12}" y="{y+13}" width="{w-24}" height="14" rx="5" fill="#E9F0F5" stroke="#D1DDE5"/>')
            text_lines(x + w/2, y + 22, ["●  ●  ●"], 8, "#8193A2", 700)
            text_lines(x + w/2, y + 52, ["Browser / user", "GET / · /site.css"], 11, "#30485A", 700, gap=18)
        else:
            icon = ICON_DIR / f"{key}.svg"
            encoded = base64.b64encode(icon.read_bytes()).decode("ascii")
            ih = h - (37 if "\n" not in label else 50)
            iw = min(w - 12, ih)
            ix, iy = x + (w - iw) / 2, y + 2
            chunks.append(f'<image href="data:image/svg+xml;base64,{encoded}" x="{ix}" y="{iy}" width="{iw}" height="{iw}" preserveAspectRatio="xMidYMid meet"/>')
            lines = label.split("\n")
            text_lines(x + w/2, y + h - (len(lines) - 1) * 14 - 4, lines, 11, "#20394D", 700, gap=14)

    for cid, label, x, y, w, h, fill, stroke in notes:
        chunks.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{stroke}"/>')
        text_lines(x + w/2, y + h/2 + 4, [label], 10, "#40576A", 700)

    chunks.append('<text x="50" y="1146" font-family="Arial,sans-serif" font-size="10" fill="#8496A4">Design note: Route 53 points the app hostname directly to the ALB; CloudFront serves static assets from the private S3 origin.</text>')
    chunks.append('</svg>')
    return "\n".join(chunks)


DOCS.mkdir(parents=True, exist_ok=True)
(DOCS / "architecture.drawio").write_text(mxfile(), encoding="utf-8")
(DOCS / "architecture.svg").write_text(svg_preview(), encoding="utf-8")
print(f"Wrote {DOCS / 'architecture.drawio'} and architecture.svg")
