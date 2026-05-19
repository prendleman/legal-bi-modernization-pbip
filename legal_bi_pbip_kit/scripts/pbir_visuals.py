"""Programmatic PBIR visuals for Sidley_BI_Modernization_Demo.

Writes `definition/pages/<Page>/visuals/<id>/visual.json` per Microsoft Fabric
PBIR layout. Visual types and query roles follow standard built-in visuals;
if a future Desktop build rejects a type, open once in Desktop, re-save, and
diff the emitted JSON.

Schema reference:
https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# Layout: 1280×720 canvas; rail + body top tuned for KPI gap, slicer headers, and right chrome.
PAGE_W = 1280
PAGE_CANVAS_H = 720
RIGHT_MARGIN = 12
RAIL_W = 268
CONTENT_X = 16 + RAIL_W + 12  # 296
CHART_H = 378
# Executive first row: line + column share this height; industry bar + client bar use bands below.
EXEC_CHART_ROW_H = 268
EXEC_INDUSTRY_BAR_H = 108
BOTTOM_MARGIN = 4
CONTENT_W = PAGE_W - CONTENT_X - RIGHT_MARGIN  # 972
EXEC_LINE_W = 508
EXEC_COL_GAP = 12
EXEC_COL_W = CONTENT_W - EXEC_LINE_W - EXEC_COL_GAP
AS_OF_W = 288
AS_OF_X = PAGE_W - RIGHT_MARGIN - AS_OF_W
SUBTITLE_MAX_W = AS_OF_X - 24  # keep subtitle clear of freshness stack
# Page chrome: textbox heights must clear 20pt/11pt text or Desktop clips and shows scrollbars.
CHROME_TITLE_Y = 8
CHROME_TITLE_H = 44
CHROME_SUB_Y = CHROME_TITLE_Y + CHROME_TITLE_H + 4
CHROME_SUB_H = 40
CHROME_AS_OF_CAPTION_Y = 8
CHROME_AS_OF_CAPTION_H = 26  # 9pt caption + padding (avoids top/bottom clip in textbox)
CHROME_AS_OF_CARD_Y = CHROME_AS_OF_CAPTION_Y + CHROME_AS_OF_CAPTION_H + 4
# Card shows callout only (category label hidden in PBIR) so measure name does not steal height.
CHROME_AS_OF_CARD_H = 64
CHROME_BOTTOM = max(CHROME_SUB_Y + CHROME_SUB_H, CHROME_AS_OF_CARD_Y + CHROME_AS_OF_CARD_H)
KPI_TOP = CHROME_BOTTOM + 8
KPI_CARD_H = 88
KPI_BODY_GAP = 8
BODY_TOP = KPI_TOP + KPI_CARD_H + KPI_BODY_GAP
# Slicer gaps: keep SL_Y4 + client slicer height ≤ ~718 for 720 canvas.
_SL_GAP = 5
SL_Y0 = BODY_TOP
SL_Y1 = SL_Y0 + 118 + _SL_GAP
SL_Y2 = SL_Y1 + 90 + _SL_GAP
SL_Y3 = SL_Y2 + 100 + _SL_GAP
SL_Y4 = SL_Y3 + 100 + _SL_GAP
# Tables / full-width line: fill remaining canvas under 720p after chrome + KPI + BODY_TOP.
MAIN_BODY_H = PAGE_CANVAS_H - BODY_TOP - BOTTOM_MARGIN


def _rail_slicer_y(heights: List[int]) -> List[float]:
    """Top Y coordinate for each rail slicer given vertical sizes (gap ``_SL_GAP`` between)."""
    ys: List[float] = []
    y = float(BODY_TOP)
    for h in heights:
        ys.append(y)
        y += float(h) + _SL_GAP
    return ys
# Cross-page slicer sync (matches SupplyChain-PBI `syncGroup` shape).
SYNC_TIME_CALC = "SidleySync_TimeCalculation"
SYNC_CALENDAR_RANGE = "SidleySync_CalendarDateRange"
SYNC_OFFICE = "SidleySync_OfficeName"
SYNC_PRACTICE = "SidleySync_PracticeName"
SYNC_CLIENT_TIER = "SidleySync_ClientTier"
SYNC_INDUSTRY = "SidleySync_ClientIndustry"

PAGE_CHROME: Dict[str, Tuple[str, str]] = {
    "Executive_Overview": (
        "Executive Overview",
        "Firmwide KPIs, billings trend, margin by practice, Marketing/BD industry billings mix, top clients — date range + time calc.",
    ),
    "Matter_Profitability": (
        "Matter & practice profitability",
        "Fees and realization by practice; synced office, client industry, date range, practice, and time calc.",
    ),
    "Open_Pending_Cases": (
        "Open & pending cases",
        "Waterfall: office → client industry (use drill/expand on the chart for industry within office). Click bars to filter the table. Slicers: matter-level office, industry, and status (list, multi-select).",
    ),
    "Legacy_Migration": (
        "Legacy report migration control tower",
        "Inventory, migration status, and stakeholder ownership across platforms.",
    ),
    "Stakeholder_KPIs": (
        "Stakeholder requirements / KPI catalog",
        "Backlog health, SLA risk, and priority — synced office and client industry (cross-filter story).",
    ),
    "Refresh_Monitor": (
        "Data quality & refresh monitor",
        "Pipeline success vs calendar — synced office and client industry where facts join client/office paths.",
    ),
    "RLS_Demo": (
        "RLS / office security demo",
        "Use View as in Modeling for Chicago roles; slicer syncs with Executive & Matter pages.",
    ),
    "Visual_Lab": (
        "Visual lab & motion",
        "Native treemap, donut, funnel, scatter; synced office + client industry; see docs for custom visuals and motion.",
    ),
}


VISUAL_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.4.0/schema.json"
)


def page_folder_id(emitter_key: str) -> str:
    """32-char hex folder + page `name`, matching Power BI Desktop PBIR exports."""
    return hashlib.sha256(f"sidley.pbir.page:{emitter_key}".encode()).hexdigest()[:32]


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _visual_id(page_seed: str, index: int) -> str:
    """Deterministic 20-char id (schema maxLength 50)."""
    return hashlib.sha1(f"{page_seed}|{index}".encode()).hexdigest()[:20]


def _pos(x: float, y: float, w: float, h: float, z: int = 0, tab: int = 0) -> Dict:
    return {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": tab}


def _proj_column(entity: str, prop: str, *, active: bool = False) -> Dict:
    qref = f"{entity}.{prop}"
    out: Dict = {
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": entity}},
                "Property": prop,
            }
        },
        "queryRef": qref,
        "nativeQueryRef": prop,
    }
    if active:
        out["active"] = True
    return out


def _literal_str(value: str) -> Dict:
    """Power BI expression literal for DAX-style strings (single quotes escaped)."""
    escaped = value.replace("'", "''")
    return {"expr": {"Literal": {"Value": f"'{escaped}'"}}}


def _proj_measure(entity: str, prop: str) -> Dict:
    qref = f"{entity}.{prop}"
    return {
        "field": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": entity}},
                "Property": prop,
            }
        },
        "queryRef": qref,
        "nativeQueryRef": prop,
    }


def _visual_container(
    name: str, position: Dict, visual: Dict, *, how_created: str = "InsertVisualButton"
) -> Dict:
    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": position,
        "howCreated": how_created,
        "visual": visual,
    }


def _card(name: str, position: Dict, measure: str) -> Dict:
    return _visual_container(
        name,
        position,
        {
            "visualType": "card",
            "query": {
                "queryState": {
                    "Values": {"projections": [_proj_measure("_Measures", measure)]}
                }
            },
            "drillFilterOtherVisuals": True,
        },
    )


def _report_page_tooltip_objects(tooltip_page_name: str) -> Dict:
    """Format pane → tooltip → **Report page**; `tooltip_page_name` is the tooltip page folder id."""
    return {
        "visualTooltip": [
            {
                "properties": {
                    "type": {"expr": {"Literal": {"Value": "'ReportPage'"}}},
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "section": {"expr": {"Literal": {"Value": f"'{tooltip_page_name}'"}}},
                }
            }
        ]
    }


def _line_chart(
    name: str,
    position: Dict,
    category_entity: str,
    category_prop: str,
    measure: str,
    *,
    tooltip_page_name: str | None = None,
) -> Dict:
    inner: Dict = {
        "visualType": "lineChart",
        "query": {
            "queryState": {
                "Category": {
                    "projections": [_proj_column(category_entity, category_prop)]
                },
                "Y": {"projections": [_proj_measure("_Measures", measure)]},
            }
        },
        "drillFilterOtherVisuals": True,
    }
    if tooltip_page_name:
        inner["objects"] = _report_page_tooltip_objects(tooltip_page_name)
    return _visual_container(name, position, inner)


def _clustered_column(name: str, position: Dict, category_entity: str, category_prop: str, measure: str) -> Dict:
    return _visual_container(
        name,
        position,
        {
            "visualType": "clusteredColumnChart",
            "query": {
                "queryState": {
                    "Category": {
                        "projections": [_proj_column(category_entity, category_prop)]
                    },
                    "Y": {"projections": [_proj_measure("_Measures", measure)]},
                }
            },
            "drillFilterOtherVisuals": True,
        },
    )


def _clustered_bar(name: str, position: Dict, category_entity: str, category_prop: str, measure: str) -> Dict:
    """Horizontal clustered bar (category on Y axis in Desktop)."""
    return _visual_container(
        name,
        position,
        {
            "visualType": "clusteredBarChart",
            "query": {
                "queryState": {
                    "Category": {
                        "projections": [_proj_column(category_entity, category_prop)]
                    },
                    "Y": {"projections": [_proj_measure("_Measures", measure)]},
                }
            },
            "drillFilterOtherVisuals": True,
        },
    )


def _waterfall_chart(
    name: str,
    position: Dict,
    category_levels: List[Tuple[str, str]],
    measure: str,
) -> Dict:
    """Native waterfall: drill hierarchy on Category (outer → inner), Y = measure."""
    projections: List[Dict] = []
    for i, (ent, prop) in enumerate(category_levels):
        projections.append(_proj_column(ent, prop, active=(i == 0)))
    return _visual_container(
        name,
        position,
        {
            "visualType": "waterfallChart",
            "query": {
                "queryState": {
                    "Category": {"projections": projections},
                    "Y": {"projections": [_proj_measure("_Measures", measure)]},
                }
            },
            "drillFilterOtherVisuals": True,
        },
    )


def _scatter_chart(
    name: str,
    position: Dict,
    *,
    detail_entity: str,
    detail_prop: str,
    x_measure: str,
    y_measure: str,
    size_measure: str,
) -> Dict:
    """Native scatter / bubble: one point per ``detail`` row; X/Y measures; size drives bubble area."""
    return _visual_container(
        name,
        position,
        {
            "visualType": "scatterChart",
            "query": {
                "queryState": {
                    "Details": {
                        "projections": [
                            _proj_column(detail_entity, detail_prop, active=True)
                        ]
                    },
                    "X": {"projections": [_proj_measure("_Measures", x_measure)]},
                    "Y": {"projections": [_proj_measure("_Measures", y_measure)]},
                    "Size": {"projections": [_proj_measure("_Measures", size_measure)]},
                }
            },
            "drillFilterOtherVisuals": True,
        },
    )


def _treemap(name: str, position: Dict, group_entity: str, group_prop: str, measure: str) -> Dict:
    return _visual_container(
        name,
        position,
        {
            "visualType": "treemap",
            "query": {
                "queryState": {
                    "Category": {
                        "projections": [_proj_column(group_entity, group_prop, active=True)]
                    },
                    "Values": {"projections": [_proj_measure("_Measures", measure)]},
                }
            },
            "drillFilterOtherVisuals": True,
        },
    )


def _donut_chart(name: str, position: Dict, category_entity: str, category_prop: str, measure: str) -> Dict:
    return _visual_container(
        name,
        position,
        {
            "visualType": "donutChart",
            "query": {
                "queryState": {
                    "Category": {
                        "projections": [_proj_column(category_entity, category_prop, active=True)]
                    },
                    "Y": {"projections": [_proj_measure("_Measures", measure)]},
                }
            },
            "drillFilterOtherVisuals": True,
        },
    )


def _funnel_chart(name: str, position: Dict, category_entity: str, category_prop: str, measure: str) -> Dict:
    return _visual_container(
        name,
        position,
        {
            "visualType": "funnel",
            "query": {
                "queryState": {
                    "Category": {
                        "projections": [_proj_column(category_entity, category_prop, active=True)]
                    },
                    "Y": {"projections": [_proj_measure("_Measures", measure)]},
                }
            },
            "drillFilterOtherVisuals": True,
        },
    )


def _dropdown_slicer(
    name: str,
    position: Dict,
    entity: str,
    prop: str,
    *,
    header_text: str | None = None,
    display_mode: str = "Dropdown",
    sync_group: str | None = None,
    multi_select: bool = False,
) -> Dict:
    """Categorical slicer; use ``List`` for checkbox lists; optional ``syncGroup`` for cross-page sync."""
    title = header_text if header_text is not None else prop
    objects: Dict = {
        "data": [{"properties": {"mode": _literal_str(display_mode)}}],
        "header": [
            {
                "properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "text": _literal_str(title),
                }
            }
        ],
    }
    if multi_select:
        # Format → Slicer settings → Selection: allow multiple values without Ctrl (native slicer).
        objects["selection"] = [
            {
                "properties": {
                    "singleSelect": {"expr": {"Literal": {"Value": "false"}}},
                    "strictSingleSelect": {"expr": {"Literal": {"Value": "false"}}},
                }
            }
        ]
    visual: Dict = {
        "visualType": "slicer",
        "query": {
            "queryState": {
                "Values": {"projections": [_proj_column(entity, prop, active=True)]}
            }
        },
        "objects": objects,
        "drillFilterOtherVisuals": True,
    }
    if sync_group:
        visual["syncGroup"] = {
            "groupName": sync_group,
            "fieldChanges": True,
            "filterChanges": True,
        }
    return _visual_container(name, position, visual, how_created="DraggedToCanvas")


def _calendar_between_slicer(
    name: str,
    position: Dict,
    *,
    header_text: str = "Date range",
    sync_group: str | None = None,
) -> Dict:
    """``dim_date[Date]`` in **Between** mode — filters the date table so axes and facts share one calendar window."""
    visual: Dict = {
        "visualType": "slicer",
        "query": {
            "queryState": {
                "Values": {"projections": [_proj_column("dim_date", "Date", active=True)]}
            }
        },
        "objects": {
            "data": [{"properties": {"mode": _literal_str("Between")}}],
            "header": [
                {
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": _literal_str(header_text),
                    }
                }
            ],
        },
        "drillFilterOtherVisuals": True,
    }
    if sync_group:
        visual["syncGroup"] = {
            "groupName": sync_group,
            "fieldChanges": True,
            "filterChanges": True,
        }
    return _visual_container(name, position, visual, how_created="DraggedToCanvas")


def _textbox_simple(
    name: str,
    position: Dict,
    text: str,
    *,
    font_pt: str = "18pt",
    bold: bool = False,
    color: str = "#005E85",
) -> Dict:
    style: Dict = {"fontSize": font_pt, "color": color}
    if bold:
        style["fontWeight"] = "bold"
    visual = {
        "visualType": "textbox",
        "objects": {
            "general": [
                {
                    "properties": {
                        "paragraphs": [
                            {
                                "verticalAlignment": "top",
                                "horizontalTextAlignment": "left",
                                "textRuns": [{"value": text, "textStyle": style}],
                            }
                        ]
                    }
                }
            ]
        },
        "drillFilterOtherVisuals": False,
    }
    return _visual_container(name, position, visual, how_created="InsertVisualButton")


def _as_of_card(name: str, position: Dict) -> Dict:
    """Card bound to ``As of date`` (scalar date). Hides category label so callout fits short chrome."""
    visual: Dict = {
        "visualType": "card",
        "query": {
            "queryState": {
                "Values": {"projections": [_proj_measure("_Measures", "As of date")]}
            }
        },
        "objects": {
            "categoryLabels": [
                {
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "false"}}},
                    }
                }
            ],
        },
        "drillFilterOtherVisuals": False,
    }
    return _visual_container(name, position, visual, how_created="InsertVisualButton")


def _page_chrome(seed: str, emitter_key: str) -> List[Dict]:
    title, subtitle = PAGE_CHROME[emitter_key]
    return [
        _textbox_simple(
            _visual_id(seed, 801),
            _pos(16, CHROME_TITLE_Y, SUBTITLE_MAX_W, CHROME_TITLE_H, 50, 0),
            title,
            font_pt="20pt",
            bold=True,
            color="#005E85",
        ),
        _textbox_simple(
            _visual_id(seed, 802),
            _pos(16, CHROME_SUB_Y, SUBTITLE_MAX_W, CHROME_SUB_H, 50, 1),
            subtitle,
            font_pt="11pt",
            bold=False,
            color="#3D5166",
        ),
        _textbox_simple(
            _visual_id(seed, 804),
            _pos(AS_OF_X, CHROME_AS_OF_CAPTION_Y, AS_OF_W, CHROME_AS_OF_CAPTION_H, 50, 2),
            "Certified extract · data through",
            font_pt="9pt",
            bold=False,
            color="#5A6B7D",
        ),
        _as_of_card(
            _visual_id(seed, 803),
            _pos(AS_OF_X, CHROME_AS_OF_CARD_Y, AS_OF_W, CHROME_AS_OF_CARD_H, 50, 3),
        ),
    ]


def _table(name: str, position: Dict, columns: List[Tuple[str, str]]) -> Dict:
    projections = [_proj_column(ent, prop) for ent, prop in columns]
    return _visual_container(
        name,
        position,
        {
            "visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": projections}}},
            "drillFilterOtherVisuals": True,
        },
    )


def _write_visuals(page_dir: Path, visuals: List[Dict]) -> None:
    root = page_dir / "visuals"
    if root.exists():
        shutil.rmtree(root)
    for payload in visuals:
        vid = payload["name"]
        _write_json(root / vid / "visual.json", payload)


def _patch_page_json(page_dir: Path, patch: Dict) -> None:
    """Merge keys into ``page.json`` (e.g. ``visualInteractions`` for cross-filter)."""
    path = page_dir / "page.json"
    page = json.loads(path.read_text(encoding="utf-8"))
    page.update(patch)
    path.write_text(json.dumps(page, indent=2), encoding="utf-8")


def emit_executive_overview(page_dir: Path) -> None:
    seed = "Executive_Overview"
    industry_y = BODY_TOP + EXEC_CHART_ROW_H + 8
    client_bar_top = industry_y + EXEC_INDUSTRY_BAR_H + 8
    client_bar_h = PAGE_CANVAS_H - client_bar_top - BOTTOM_MARGIN
    visuals: List[Dict] = list(_page_chrome(seed, seed))
    cards = [
        ("Total Billings", 0),
        ("Gross Margin %", 1),
        ("Realization Rate", 2),
        ("Collection Rate", 3),
        ("Migration % Complete", 4),
        ("Refresh Success Rate", 5),
    ]
    for idx, (measure, slot) in enumerate(cards):
        x = 20 + slot * 208
        visuals.append(_card(_visual_id(seed, idx), _pos(x, KPI_TOP, 198, KPI_CARD_H, 0, 20 + idx), measure))
    # Slicers: compact rail (6) — tab 10–15, then charts 30+.
    _ex_rh = [96, 76, 76, 74, 74, 68]
    _ex_ys = _rail_slicer_y(_ex_rh)
    visuals.append(
        _dropdown_slicer(
            _visual_id(seed, 5),
            _pos(16, _ex_ys[0], RAIL_W, _ex_rh[0], 0, 10),
            "Time Intelligence",
            "Time Calculation",
            header_text="Time calc",
            display_mode="List",
            sync_group=SYNC_TIME_CALC,
        )
    )
    visuals.append(
        _calendar_between_slicer(
            _visual_id(seed, 30),
            _pos(16, _ex_ys[1], RAIL_W, _ex_rh[1], 0, 11),
            header_text="Date range",
            sync_group=SYNC_CALENDAR_RANGE,
        )
    )
    visuals.append(
        _dropdown_slicer(
            _visual_id(seed, 31),
            _pos(16, _ex_ys[2], RAIL_W, _ex_rh[2], 0, 12),
            "dim_office",
            "OfficeName",
            header_text="Office",
            sync_group=SYNC_OFFICE,
        )
    )
    visuals.append(
        _dropdown_slicer(
            _visual_id(seed, 32),
            _pos(16, _ex_ys[3], RAIL_W, _ex_rh[3], 0, 13),
            "dim_practice",
            "PracticeName",
            header_text="Practice",
            sync_group=SYNC_PRACTICE,
        )
    )
    visuals.append(
        _dropdown_slicer(
            _visual_id(seed, 34),
            _pos(16, _ex_ys[4], RAIL_W, _ex_rh[4], 0, 14),
            "dim_client",
            "Industry",
            header_text="Client industry",
            display_mode="List",
            sync_group=SYNC_INDUSTRY,
        )
    )
    visuals.append(
        _dropdown_slicer(
            _visual_id(seed, 33),
            _pos(16, _ex_ys[5], RAIL_W, _ex_rh[5], 0, 15),
            "dim_client",
            "ClientTier",
            header_text="Client tier",
            sync_group=SYNC_CLIENT_TIER,
        )
    )
    visuals.append(
        _line_chart(
            _visual_id(seed, 10),
            _pos(CONTENT_X, BODY_TOP, EXEC_LINE_W, EXEC_CHART_ROW_H, 0, 30),
            "dim_date",
            "MonthYear",
            "Total Billings",
        )
    )
    visuals.append(
        _clustered_column(
            _visual_id(seed, 11),
            _pos(CONTENT_X + EXEC_LINE_W + EXEC_COL_GAP, BODY_TOP, EXEC_COL_W, EXEC_CHART_ROW_H, 0, 31),
            "dim_practice",
            "PracticeName",
            "Gross Margin %",
        )
    )
    visuals.append(
        _clustered_bar(
            _visual_id(seed, 13),
            _pos(CONTENT_X, industry_y, CONTENT_W, EXEC_INDUSTRY_BAR_H, 0, 32),
            "dim_client",
            "Industry",
            "Total Billings",
        )
    )
    visuals.append(
        _clustered_bar(
            _visual_id(seed, 12),
            _pos(CONTENT_X, client_bar_top, CONTENT_W, client_bar_h, 0, 33),
            "dim_client",
            "ClientName",
            "Total Billings",
        )
    )
    _write_visuals(page_dir, visuals)


def emit_matter_profitability(page_dir: Path) -> None:
    seed = "Matter_Profitability"
    half_w = (CONTENT_W - 12) // 2
    matter_row1_h = int(MAIN_BODY_H * 0.52)
    matter_gap = 10
    matter_scatter_y = BODY_TOP + matter_row1_h + matter_gap
    matter_scatter_h = PAGE_CANVAS_H - matter_scatter_y - BOTTOM_MARGIN
    visuals: List[Dict] = list(_page_chrome(seed, seed))
    _mt_rh = [96, 76, 76, 74, 72]
    _mt_ys = _rail_slicer_y(_mt_rh)
    visuals += [
        _card(_visual_id(seed, 0), _pos(20, KPI_TOP, 280, KPI_CARD_H, 0, 20), "Total Fees"),
        _card(_visual_id(seed, 1), _pos(316, KPI_TOP, 280, KPI_CARD_H, 0, 21), "Gross Margin %"),
        _dropdown_slicer(
            _visual_id(seed, 5),
            _pos(16, _mt_ys[0], RAIL_W, _mt_rh[0], 0, 10),
            "Time Intelligence",
            "Time Calculation",
            header_text="Time calc",
            display_mode="List",
            sync_group=SYNC_TIME_CALC,
        ),
        _calendar_between_slicer(
            _visual_id(seed, 24),
            _pos(16, _mt_ys[1], RAIL_W, _mt_rh[1], 0, 11),
            header_text="Date range",
            sync_group=SYNC_CALENDAR_RANGE,
        ),
        _dropdown_slicer(
            _visual_id(seed, 22),
            _pos(16, _mt_ys[2], RAIL_W, _mt_rh[2], 0, 12),
            "dim_office",
            "OfficeName",
            header_text="Office",
            sync_group=SYNC_OFFICE,
        ),
        _dropdown_slicer(
            _visual_id(seed, 23),
            _pos(16, _mt_ys[3], RAIL_W, _mt_rh[3], 0, 13),
            "dim_practice",
            "PracticeName",
            header_text="Practice",
            sync_group=SYNC_PRACTICE,
        ),
        _dropdown_slicer(
            _visual_id(seed, 25),
            _pos(16, _mt_ys[4], RAIL_W, _mt_rh[4], 0, 14),
            "dim_client",
            "Industry",
            header_text="Client industry",
            display_mode="List",
            sync_group=SYNC_INDUSTRY,
        ),
        _clustered_column(
            _visual_id(seed, 2),
            _pos(CONTENT_X, BODY_TOP, half_w, matter_row1_h, 0, 30),
            "dim_practice",
            "PracticeName",
            "Total Fees",
        ),
        _clustered_column(
            _visual_id(seed, 3),
            _pos(CONTENT_X + half_w + 12, BODY_TOP, half_w, matter_row1_h, 0, 31),
            "dim_practice",
            "PracticeName",
            "Realization Rate",
        ),
        _scatter_chart(
            _visual_id(seed, 4),
            _pos(CONTENT_X, matter_scatter_y, CONTENT_W, matter_scatter_h, 0, 32),
            detail_entity="dim_matter",
            detail_prop="MatterName",
            x_measure="Total Fees",
            y_measure="Gross Margin %",
            size_measure="WIP Amount",
        ),
    ]
    _write_visuals(page_dir, visuals)


def emit_open_pending_cases(page_dir: Path) -> None:
    """Open matters: office waterfall + detail table (cross-filter on bar click); office, industry, and status slicers."""
    seed = "Open_Pending_Cases"
    visuals: List[Dict] = list(_page_chrome(seed, seed))
    _op_rh = [86, 86, 86]
    _op_ys = _rail_slicer_y(_op_rh)
    wf_h = int(MAIN_BODY_H * 0.38)
    tbl_gap = 10
    tbl_y = BODY_TOP + wf_h + tbl_gap
    tbl_h = PAGE_CANVAS_H - tbl_y - BOTTOM_MARGIN
    wf_name = _visual_id(seed, 10)
    det_name = _visual_id(seed, 11)
    visuals += [
        _card(_visual_id(seed, 0), _pos(20, KPI_TOP, 280, KPI_CARD_H, 0, 20), "Open Matters"),
        _card(_visual_id(seed, 1), _pos(316, KPI_TOP, 280, KPI_CARD_H, 0, 21), "On Hold Matters"),
        _dropdown_slicer(
            _visual_id(seed, 51),
            _pos(16, _op_ys[0], RAIL_W, _op_rh[0], 0, 10),
            "dim_matter",
            "OfficeName",
            header_text="Office",
            display_mode="List",
            multi_select=True,
        ),
        _dropdown_slicer(
            _visual_id(seed, 53),
            _pos(16, _op_ys[1], RAIL_W, _op_rh[1], 0, 11),
            "dim_matter",
            "ClientIndustry",
            header_text="Client industry",
            display_mode="List",
            multi_select=True,
        ),
        _dropdown_slicer(
            _visual_id(seed, 54),
            _pos(16, _op_ys[2], RAIL_W, _op_rh[2], 0, 12),
            "dim_matter",
            "MatterStatus",
            header_text="Status",
            display_mode="List",
            multi_select=True,
        ),
        _waterfall_chart(
            wf_name,
            _pos(CONTENT_X, BODY_TOP, CONTENT_W, wf_h, 0, 30),
            [
                ("dim_matter", "OfficeName"),
                ("dim_matter", "ClientIndustry"),
            ],
            "Open Matters",
        ),
        _table(
            det_name,
            _pos(CONTENT_X, tbl_y, CONTENT_W, tbl_h, 0, 31),
            [
                ("dim_matter", "MatterNumber"),
                ("dim_matter", "MatterName"),
                ("dim_matter", "OfficeName"),
                ("dim_matter", "ClientIndustry"),
                ("dim_matter", "ClientName"),
                ("dim_matter", "LeadAttorneyName"),
                ("dim_matter", "MatterStatus"),
            ],
        ),
    ]
    _write_visuals(page_dir, visuals)
    # Cross-filter: clicking the waterfall applies a data filter to the detail table (and reverse).
    _patch_page_json(
        page_dir,
        {
            "visualInteractions": [
                {"source": wf_name, "target": det_name, "type": "DataFilter"},
                {"source": det_name, "target": wf_name, "type": "DataFilter"},
            ]
        },
    )


def emit_legacy_migration(page_dir: Path) -> None:
    seed = "Legacy_Migration"
    _lg_rh = [92, 74, 72, 70, 68]
    _lg_ys = _rail_slicer_y(_lg_rh)
    visuals: List[Dict] = list(_page_chrome(seed, seed))
    visuals += [
        _card(_visual_id(seed, 0), _pos(20, KPI_TOP, 300, KPI_CARD_H, 0, 20), "Legacy Reports"),
        _card(_visual_id(seed, 1), _pos(336, KPI_TOP, 300, KPI_CARD_H, 0, 21), "Migration % Complete"),
        _card(_visual_id(seed, 2), _pos(652, KPI_TOP, 300, KPI_CARD_H, 0, 22), "Modernization Health Score"),
        _dropdown_slicer(
            _visual_id(seed, 5),
            _pos(16, _lg_ys[0], RAIL_W, _lg_rh[0], 0, 10),
            "Time Intelligence",
            "Time Calculation",
            header_text="Time calc",
            display_mode="List",
            sync_group=SYNC_TIME_CALC,
        ),
        _calendar_between_slicer(
            _visual_id(seed, 19),
            _pos(16, _lg_ys[1], RAIL_W, _lg_rh[1], 0, 11),
            header_text="Date range",
            sync_group=SYNC_CALENDAR_RANGE,
        ),
        _dropdown_slicer(
            _visual_id(seed, 20),
            _pos(16, _lg_ys[2], RAIL_W, _lg_rh[2], 0, 12),
            "fact_legacy_report_inventory",
            "MigrationStatus",
            header_text="Migration status",
        ),
        _dropdown_slicer(
            _visual_id(seed, 26),
            _pos(16, _lg_ys[3], RAIL_W, _lg_rh[3], 0, 13),
            "dim_office",
            "OfficeName",
            header_text="Office",
            sync_group=SYNC_OFFICE,
        ),
        _dropdown_slicer(
            _visual_id(seed, 27),
            _pos(16, _lg_ys[4], RAIL_W, _lg_rh[4], 0, 14),
            "dim_client",
            "Industry",
            header_text="Client industry",
            display_mode="List",
            sync_group=SYNC_INDUSTRY,
        ),
        _donut_chart(
            _visual_id(seed, 21),
            _pos(CONTENT_X, BODY_TOP, 300, MAIN_BODY_H, 0, 30),
            "fact_legacy_report_inventory",
            "MigrationStatus",
            "Legacy Reports",
        ),
        _table(
            _visual_id(seed, 3),
            _pos(CONTENT_X + 312, BODY_TOP, CONTENT_W - 312, MAIN_BODY_H, 0, 31),
            [
                ("fact_legacy_report_inventory", "LegacyReportName"),
                ("fact_legacy_report_inventory", "LegacyPlatform"),
                ("fact_legacy_report_inventory", "MigrationStatus"),
                ("fact_legacy_report_inventory", "ValidationStatus"),
                ("fact_legacy_report_inventory", "OwningStakeholderGroup"),
            ],
        ),
    ]
    _write_visuals(page_dir, visuals)


def emit_stakeholder_kpis(page_dir: Path) -> None:
    seed = "Stakeholder_KPIs"
    _st_rh = [88, 72, 68, 68, 66, 64]
    _st_ys = _rail_slicer_y(_st_rh)
    visuals: List[Dict] = list(_page_chrome(seed, seed))
    visuals += [
        _card(_visual_id(seed, 0), _pos(20, KPI_TOP, 280, KPI_CARD_H, 0, 20), "Open Stakeholder Requests"),
        _card(_visual_id(seed, 1), _pos(316, KPI_TOP, 280, KPI_CARD_H, 0, 21), "SLA Breach Count"),
        _dropdown_slicer(
            _visual_id(seed, 5),
            _pos(16, _st_ys[0], RAIL_W, _st_rh[0], 0, 10),
            "Time Intelligence",
            "Time Calculation",
            header_text="Time calc",
            display_mode="List",
            sync_group=SYNC_TIME_CALC,
        ),
        _calendar_between_slicer(
            _visual_id(seed, 18),
            _pos(16, _st_ys[1], RAIL_W, _st_rh[1], 0, 11),
            header_text="Date range",
            sync_group=SYNC_CALENDAR_RANGE,
        ),
        _dropdown_slicer(
            _visual_id(seed, 20),
            _pos(16, _st_ys[2], RAIL_W, _st_rh[2], 0, 12),
            "fact_requirements_backlog",
            "StakeholderGroup",
            header_text="Stakeholder group",
        ),
        _dropdown_slicer(
            _visual_id(seed, 21),
            _pos(16, _st_ys[3], RAIL_W, _st_rh[3], 0, 13),
            "fact_requirements_backlog",
            "Priority",
            header_text="Priority",
        ),
        _dropdown_slicer(
            _visual_id(seed, 28),
            _pos(16, _st_ys[4], RAIL_W, _st_rh[4], 0, 14),
            "dim_office",
            "OfficeName",
            header_text="Office",
            sync_group=SYNC_OFFICE,
        ),
        _dropdown_slicer(
            _visual_id(seed, 29),
            _pos(16, _st_ys[5], RAIL_W, _st_rh[5], 0, 15),
            "dim_client",
            "Industry",
            header_text="Client industry",
            display_mode="List",
            sync_group=SYNC_INDUSTRY,
        ),
        _table(
            _visual_id(seed, 2),
            _pos(CONTENT_X, BODY_TOP, CONTENT_W, MAIN_BODY_H, 0, 30),
            [
                ("fact_requirements_backlog", "RequestTitle"),
                ("fact_requirements_backlog", "ProductManager"),
                ("fact_requirements_backlog", "EpicId"),
                ("fact_requirements_backlog", "StakeholderGroup"),
                ("fact_requirements_backlog", "KPIArea"),
                ("fact_requirements_backlog", "Priority"),
                ("fact_requirements_backlog", "RequestStatus"),
                ("fact_requirements_backlog", "TargetDate"),
                ("fact_requirements_backlog", "AcceptanceCriteria"),
            ],
        ),
    ]
    _write_visuals(page_dir, visuals)


def emit_refresh_monitor(page_dir: Path) -> None:
    seed = "Refresh_Monitor"
    _rf_rh = [96, 76, 72, 72]
    _rf_ys = _rail_slicer_y(_rf_rh)
    visuals: List[Dict] = list(_page_chrome(seed, seed))
    visuals += [
        _card(_visual_id(seed, 0), _pos(20, KPI_TOP, 300, KPI_CARD_H, 0, 20), "Refresh Success Rate"),
        _card(_visual_id(seed, 1), _pos(336, KPI_TOP, 300, KPI_CARD_H, 0, 21), "Failed Refreshes"),
        _card(_visual_id(seed, 2), _pos(652, KPI_TOP, 300, KPI_CARD_H, 0, 22), "Avg Refresh Duration Minutes"),
        _dropdown_slicer(
            _visual_id(seed, 5),
            _pos(16, _rf_ys[0], RAIL_W, _rf_rh[0], 0, 10),
            "Time Intelligence",
            "Time Calculation",
            header_text="Time calc",
            display_mode="List",
            sync_group=SYNC_TIME_CALC,
        ),
        _calendar_between_slicer(
            _visual_id(seed, 20),
            _pos(16, _rf_ys[1], RAIL_W, _rf_rh[1], 0, 11),
            header_text="Date range",
            sync_group=SYNC_CALENDAR_RANGE,
        ),
        _dropdown_slicer(
            _visual_id(seed, 35),
            _pos(16, _rf_ys[2], RAIL_W, _rf_rh[2], 0, 12),
            "dim_office",
            "OfficeName",
            header_text="Office",
            sync_group=SYNC_OFFICE,
        ),
        _dropdown_slicer(
            _visual_id(seed, 36),
            _pos(16, _rf_ys[3], RAIL_W, _rf_rh[3], 0, 13),
            "dim_client",
            "Industry",
            header_text="Client industry",
            display_mode="List",
            sync_group=SYNC_INDUSTRY,
        ),
        _line_chart(
            _visual_id(seed, 3),
            _pos(CONTENT_X, BODY_TOP, CONTENT_W, MAIN_BODY_H, 0, 30),
            "dim_date",
            "MonthYear",
            "Refresh Success Rate",
        ),
    ]
    _write_visuals(page_dir, visuals)


def emit_visual_lab(page_dir: Path) -> None:
    """Showcase native chart types + on-canvas notes for custom visuals and motion (bookmarks / transitions)."""
    seed = "Visual_Lab"
    half = (CONTENT_W - 12) // 2
    r1_h = 198
    r2_h = 228
    r1_y = BODY_TOP
    r2_y = r1_y + r1_h + 12
    r3_y = r2_y + r2_h + 12
    r3_h = PAGE_CANVAS_H - r3_y - BOTTOM_MARGIN
    motion_text = (
        "Motion in Power BI: use View → Bookmarks (data + display) and page buttons; "
        "enable page transitions under View → Page transitions. Custom visuals: insert from AppSource in Desktop, "
        "then Save PBIP and merge the exported visual.json — see docs/CUSTOM_VISUALS_AND_ANIMATION.md."
    )
    _vl_rh = [92, 76, 72, 72]
    _vl_ys = _rail_slicer_y(_vl_rh)
    visuals: List[Dict] = list(_page_chrome(seed, seed))
    visuals += [
        _dropdown_slicer(
            _visual_id(seed, 5),
            _pos(16, _vl_ys[0], RAIL_W, _vl_rh[0], 0, 10),
            "Time Intelligence",
            "Time Calculation",
            header_text="Time calc",
            display_mode="List",
            sync_group=SYNC_TIME_CALC,
        ),
        _calendar_between_slicer(
            _visual_id(seed, 6),
            _pos(16, _vl_ys[1], RAIL_W, _vl_rh[1], 0, 11),
            header_text="Date range",
            sync_group=SYNC_CALENDAR_RANGE,
        ),
        _dropdown_slicer(
            _visual_id(seed, 7),
            _pos(16, _vl_ys[2], RAIL_W, _vl_rh[2], 0, 12),
            "dim_office",
            "OfficeName",
            header_text="Office",
            sync_group=SYNC_OFFICE,
        ),
        _dropdown_slicer(
            _visual_id(seed, 8),
            _pos(16, _vl_ys[3], RAIL_W, _vl_rh[3], 0, 13),
            "dim_client",
            "Industry",
            header_text="Client industry",
            display_mode="List",
            sync_group=SYNC_INDUSTRY,
        ),
        _treemap(
            _visual_id(seed, 10),
            _pos(CONTENT_X, r1_y, half, r1_h, 0, 30),
            "dim_practice",
            "PracticeName",
            "Total Billings",
        ),
        _donut_chart(
            _visual_id(seed, 11),
            _pos(CONTENT_X + half + 12, r1_y, half, r1_h, 0, 31),
            "fact_legacy_report_inventory",
            "MigrationStatus",
            "Legacy Reports",
        ),
        _scatter_chart(
            _visual_id(seed, 12),
            _pos(CONTENT_X, r2_y, CONTENT_W, r2_h, 0, 32),
            detail_entity="dim_matter",
            detail_prop="MatterName",
            x_measure="Total Fees",
            y_measure="Gross Margin %",
            size_measure="WIP Amount",
        ),
        _funnel_chart(
            _visual_id(seed, 13),
            _pos(CONTENT_X, r3_y, half, r3_h, 0, 33),
            "fact_legacy_report_inventory",
            "MigrationStatus",
            "Legacy Reports",
        ),
        _textbox_simple(
            _visual_id(seed, 14),
            _pos(CONTENT_X + half + 12, r3_y, half, r3_h, 0, 34),
            motion_text,
            font_pt="10pt",
            bold=False,
            color="#3D5166",
        ),
    ]
    _write_visuals(page_dir, visuals)


def emit_rls_demo(page_dir: Path) -> None:
    seed = "RLS_Demo"
    _rls_rh = [92, 76, 72, 72]
    _rls_ys = _rail_slicer_y(_rls_rh)
    visuals: List[Dict] = list(_page_chrome(seed, seed))
    visuals += [
        _dropdown_slicer(
            _visual_id(seed, 5),
            _pos(16, _rls_ys[0], RAIL_W, _rls_rh[0], 0, 10),
            "Time Intelligence",
            "Time Calculation",
            header_text="Time calc",
            display_mode="List",
            sync_group=SYNC_TIME_CALC,
        ),
        _calendar_between_slicer(
            _visual_id(seed, 21),
            _pos(16, _rls_ys[1], RAIL_W, _rls_rh[1], 0, 11),
            header_text="Date range",
            sync_group=SYNC_CALENDAR_RANGE,
        ),
        _dropdown_slicer(
            _visual_id(seed, 20),
            _pos(16, _rls_ys[2], RAIL_W, _rls_rh[2], 0, 12),
            "dim_office",
            "OfficeName",
            header_text="Office",
            sync_group=SYNC_OFFICE,
        ),
        _dropdown_slicer(
            _visual_id(seed, 30),
            _pos(16, _rls_ys[3], RAIL_W, _rls_rh[3], 0, 13),
            "dim_client",
            "Industry",
            header_text="Client industry",
            display_mode="List",
            sync_group=SYNC_INDUSTRY,
        ),
        _card(_visual_id(seed, 0), _pos(20, KPI_TOP, 360, KPI_CARD_H, 0, 20), "Total Billings"),
        _table(
            _visual_id(seed, 1),
            _pos(CONTENT_X, BODY_TOP, CONTENT_W, MAIN_BODY_H, 0, 30),
            [
                ("dim_office", "OfficeName"),
                ("dim_office", "Region"),
                ("dim_office", "Country"),
            ],
        ),
    ]
    _write_visuals(page_dir, visuals)


_EMITTERS = {
    "Executive_Overview": emit_executive_overview,
    "Matter_Profitability": emit_matter_profitability,
    "Open_Pending_Cases": emit_open_pending_cases,
    "Legacy_Migration": emit_legacy_migration,
    "Stakeholder_KPIs": emit_stakeholder_kpis,
    "Refresh_Monitor": emit_refresh_monitor,
    "RLS_Demo": emit_rls_demo,
    "Visual_Lab": emit_visual_lab,
}


def emit_all_page_visuals(report_definition_dir: Path, page_specs: List[Tuple[str, str]]) -> None:
    for emitter_key, _display in page_specs:
        page_dir = report_definition_dir / "pages" / page_folder_id(emitter_key)
        fn = _EMITTERS.get(emitter_key)
        if fn:
            fn(page_dir)
