"""Render docs/images/architecture.svg (and optionally a PNG) with official Azure icons.

    python scripts/render_architecture.py            # SVG only
    python scripts/render_architecture.py --png      # also needs `pip install playwright`

The layout mirrors the Miro board linked from the README. Icons are the Microsoft Azure
architecture icons stored in docs/images/icons.
"""

from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / "docs" / "images" / "icons"
OUT = ROOT / "docs" / "images" / "architecture.svg"

W, H = 1800, 900
FONT = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
INK, MUTED, BLUE = "#1b1f24", "#5b6470", "#0078d4"

_icon_cache: dict[str, str] = {}


def icon(name: str, x: float, y: float, size: float = 28) -> str:
    """Inline an Azure icon as a nested <svg> so gradients keep working."""
    if name not in _icon_cache:
        raw = (ICONS / f"{name}.svg").read_text(encoding="utf-8")
        body = re.sub(r"^<svg[^>]*>", "", raw.strip())
        body = re.sub(r"</svg>\s*$", "", body)
        body = re.sub(r"<title>.*?</title>", "", body)
        _icon_cache[name] = body
    return (
        f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="0 0 18 18">'
        f"{_icon_cache[name]}</svg>"
    )


def text(x, y, s, size=12, weight=400, fill=INK, anchor="start") -> str:
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{escape(s)}</text>'
    )


def card(
    x,
    y,
    w,
    h,
    title,
    lines,
    ico=None,
    fill="#ffffff",
    stroke="#9db8e0",
    title_size=12.5,
    step=15,
    size=11,
):
    out = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="1.3" filter="url(#sh)"/>'
    ]
    tx = x + 12
    if ico:
        out.append(icon(ico, x + 10, y + 9, 28))
        tx = x + 44
    out.append(text(tx, y + 28, title, title_size, 700))
    for i, line in enumerate(lines):
        out.append(text(x + 12, y + 56 + i * step, line, size, 400, MUTED))
    return "".join(out)


def panel(x, y, w, h, num, title, sub, fill="#eef4fd"):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}"/>'
        + text(x + 20, y + 34, f"{num}  {title}", 18, 700)
        + text(x + 20, y + 54, sub, 11.5, 400, MUTED)
    )


def arrow(d: str, dashed=False, color="#2b3440") -> str:
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    return (
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.8"{dash} '
        f'marker-end="url(#ah)"/>'
    )


def build() -> str:
    p = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="{FONT}">'
        "<defs>"
        '<marker id="ah" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="8" markerHeight="8" '
        'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#2b3440"/></marker>'
        '<filter id="sh" x="-5%" y="-5%" width="110%" height="115%">'
        '<feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#0b2545" flood-opacity="0.12"/>'
        "</filter></defs>"
        f'<rect width="{W}" height="{H}" fill="#ffffff"/>'
    )
    p.append(text(40, 58, "Retail 360 Lakehouse on Azure", 34, 800))
    p.append(
        text(
            40,
            86,
            "Batch and streaming ingestion with Data Factory and Event Hubs, a medallion lakehouse on "
            "ADLS Gen2 processed by Azure Databricks, and governed serving to BI, ML and applications.",
            13.5,
            400,
            MUTED,
        )
    )

    top, ph = 112, 510
    row = lambda i: top + 75 + i * 84  # noqa: E731  (card rows in the outer columns)

    # ---- 1 Sources ----
    p.append(panel(40, top, 260, ph, "1", "Sources", "Batch, API, file and stream"))
    src = [
        ("On-prem databases", ["SQL Server and Oracle (CDC-ready)"], "sqlserver"),
        ("SAP S/4HANA", ["SAP CDC connector and OData"], "sap"),
        ("SaaS and REST APIs", ["Salesforce, Dynamics 365, Shopify"], "api"),
        ("Files and partner feeds", ["SFTP, CSV, Parquet, EDI"], "files"),
        ("Real-time streams", ["POS, IoT and web clickstream"], "iot"),
    ]
    for i, (t, ls, ic) in enumerate(src):
        p.append(card(60, row(i), 220, 70, t, ls, ic))

    # ---- 2 Ingestion ----
    p.append(panel(350, top, 270, ph, "2", "Ingestion", "Orchestrated ELT and events"))
    adf_lines = [
        "Metadata-driven pipelines",
        "Dated CSV files into landing",
        "Self-hosted IR for on-prem and SAP",
        "Managed VNet IR + private endpoints",
        "Tumbling-window daily trigger",
        "Retries and failure alerts",
        "Triggers the Databricks job",
    ]
    p.append(
        card(
            370,
            row(0),
            230,
            322,
            "Azure Data Factory",
            adf_lines,
            "adf",
            "#d6e6ff",
            "#6fa3ec",
            step=34,
            size=12,
        )
    )
    p.append(
        card(370, row(4), 230, 70, "Azure Event Hubs", ["Kafka endpoint, Capture to ADLS"], "eh")
    )

    # ---- 3 Lakehouse ----
    p.append(
        panel(
            670,
            top,
            780,
            ph,
            "3",
            "Lakehouse: ADLS Gen2 + Azure Databricks",
            "Delta Lake medallion layers on ADLS Gen2, processed by Azure Databricks",
        )
    )
    cw, gap, x0 = 168, 25, 688
    xs = [x0 + i * (cw + gap) for i in range(4)]
    r1, r2 = top + 75, top + 215
    layers = [
        ("Landing", ["Immutable source files,", "by source and date"], "#ffffff", "#9aa5b1"),
        ("Bronze", ["Raw, append-only Delta", "with lineage columns"], "#fbe0c3", "#e08a2e"),
        ("Silver", ["Typed, de-duplicated,", "PII-minimised, SCD2"], "#ececec", "#9a9a9a"),
        ("Gold", ["Star schema, aggregates", "and KPIs for BI and ML"], "#fff3b0", "#d9b300"),
    ]
    for x, (t, ls, fl, st) in zip(xs, layers, strict=True):
        p.append(card(x, r1, cw, 100, t, ls, "storage", fl, st))
    engines = [
        ("Archive tier", ["Cool and archive lifecycle,", "quarantine, legal hold"], "storage"),
        ("Auto Loader", ["Incremental file ingest and", "Kafka streaming reads"], "dbx"),
        ("Delta Live Tables", ["Expectations, apply_changes,", "quarantine tables"], "dbx"),
        ("Spark + MERGE", ["Dimensions, facts and", "aggregates"], "dbx"),
    ]
    for x, (t, ls, ic) in zip(xs, engines, strict=True):
        p.append(card(x, r2, cw, 100, t, ls, ic, "#d6e6ff", "#6fa3ec", title_size=12))
    # flow arrows between layers
    cy = r1 + 50
    for i in range(3):
        p.append(arrow(f"M{xs[i] + cw},{cy} H{xs[i + 1] - 1}"))
    p.append(arrow(f"M{xs[0] + cw / 2},{r1 + 100} V{r2 - 1}"))
    for i in (1, 2, 3):
        p.append(arrow(f"M{xs[i] + cw / 2},{r2} V{r1 + 101}"))
    # Unity Catalog bar with capability chips
    uy = top + 355
    p.append(
        f'<rect x="688" y="{uy}" width="744" height="127" rx="9" fill="#fff" stroke="#9db8e0" '
        f'stroke-width="1.3" filter="url(#sh)"/>'
    )
    p.append(icon("dbx", 698, uy + 9, 28))
    p.append(text(732, uy + 28, "Unity Catalog", 12.5, 700))
    p.append(
        text(
            700,
            uy + 54,
            "One metastore across Bronze, Silver and Gold, with Entra ID groups for access.",
            11,
            400,
            MUTED,
        )
    )
    chips = [
        "Lineage",
        "Column masks",
        "Row filters",
        "Delta Sharing",
        "Audit logs",
        "External locations",
    ]
    cx = 700
    for c in chips:
        cwid = 14 + len(c) * 6.6
        p.append(
            f'<rect x="{cx}" y="{uy + 72}" width="{cwid}" height="26" rx="13" fill="#eef4fd" '
            f'stroke="#9db8e0"/>' + text(cx + cwid / 2, uy + 89, c, 11, 600, "#0b4a8f", "middle")
        )
        cx += cwid + 10

    # ---- 4 Serving ----
    p.append(panel(1500, top, 260, ph, "4", "Serving", "BI, ML, apps and APIs"))
    srv = [
        ("Databricks SQL", ["Photon serverless BI endpoint"], "dbx"),
        ("Power BI Premium", ["Certified semantic model, RLS"], "pbi"),
        ("Azure ML + MLflow", ["Feature tables, model serving"], "ml"),
        ("Azure Cosmos DB", ["Low-latency serving via reverse ETL"], "cosmos"),
        ("API Management", ["Data product APIs"], "apim"),
    ]
    for i, (t, ls, ic) in enumerate(srv):
        p.append(card(1520, row(i), 220, 70, t, ls, ic))

    # ---- flows between columns ----
    for i in range(4):
        p.append(arrow(f"M280,{row(i) + 35} H369"))
    p.append(arrow(f"M280,{row(4) + 35} H369"))
    # ADF -> Landing (batch)
    p.append(arrow(f"M600,{row(0) + 161} H640 V{r1 + 50} H687"))
    # Event Hubs -> Auto Loader / Structured Streaming (dashed = streaming)
    gy = top + 343
    p.append(arrow(f"M600,{row(4) + 35} H640 V{gy} H{xs[1] + cw / 2} V{r2 + 101}", dashed=True))
    # Gold -> Serving bus
    bx = 1475
    p.append(
        f'<path d="M{xs[3] + cw},{r1 + 50} H{bx}" stroke="#2b3440" stroke-width="1.8" fill="none"/>'
    )
    p.append(
        f'<path d="M{bx},{row(0) + 35} V{row(4) + 35}" stroke="#2b3440" stroke-width="1.8" fill="none"/>'
    )
    for i in range(5):
        p.append(arrow(f"M{bx},{row(i) + 35} H1519"))

    # ---- 5 Cross-cutting ----
    by = top + ph + 30
    p.append(
        panel(
            40,
            by,
            1720,
            230,
            "5",
            "Security, governance and operations",
            "Cross-cutting controls applied to every layer",
            "#f5f6f7",
        )
    )
    cross = [
        (
            "Identity and network",
            "kv",
            [
                "Entra ID, RBAC, managed identities",
                "Key Vault (RBAC), private endpoints",
                "VNet injection, no public IPs",
                "Shared keys disabled on ADLS",
            ],
        ),
        (
            "Governance and catalog",
            "purview",
            [
                "Microsoft Purview scans, lineage",
                "Unity Catalog ACLs and masking",
                "Data quality rules shared by",
                "DLT, jobs and tests",
            ],
        ),
        (
            "Monitoring and FinOps",
            "monitor",
            [
                "Azure Monitor and Log Analytics",
                "Diagnostics from ADF, ADLS, KV, EH",
                "Alert on PipelineFailedRuns",
                "Spot workers, cost tags, budgets",
            ],
        ),
        (
            "DevOps and IaC",
            "devops",
            [
                "Terraform (azurerm 4.x, OIDC)",
                "GitHub Actions: CI, plan, deploy",
                "Databricks Asset Bundles",
                "dev and prod environments",
            ],
        ),
        (
            "Resilience and DR",
            "backup",
            [
                "ZRS (dev) and GZRS (prod) storage",
                "Soft delete and Delta time travel",
                "Event Hubs Capture for replay",
                "Documented recovery runbook",
            ],
        ),
    ]
    cwd = (1720 - 40 - 4 * 18) // 5
    for i, (t, ic, ls) in enumerate(cross):
        x = 60 + i * (cwd + 18)
        p.append(card(x, by + 75, cwd, 130, t, ls, ic, stroke="#c4c9d0", step=16, size=11.5))
    p.append("</svg>")
    return "".join(p)


def main() -> None:
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    if "--png" in sys.argv:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
            page.goto(OUT.as_uri())
            page.screenshot(path=str(OUT.with_suffix(".png")))
            browser.close()
        print(f"wrote {OUT.with_suffix('.png').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
