"""
Vibrant dmc-based dashboard components: animated counters, progress rings,
alert cards, timelines, statistic cards.
"""

from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import dcc, html


def animated_counter(label: str, value: str, icon: str = "bi-graph-up",
                     color: str = "#6366f1", suffix: str = "") -> dmc.Paper:
    """Animated stat counter card with icon and gradient accent."""
    return dmc.Paper(
        shadow="sm", radius="md", p="md", withBorder=True,
        style={"borderTop": f"3px solid {color}"},
        children=[
            dmc.Group([
                dmc.ThemeIcon(size="lg", radius="md", color=color, variant="light",
                              children=html.I(className=f"bi {icon}")),
                dmc.Stack([
                    dmc.Text(value + suffix, size="xl", fw=700, c="#1e293b"),
                    dmc.Text(label, size="xs", c="#64748b", tt="uppercase",
                             style={"letterSpacing": "0.5px"}),
                ], gap=2),
            ], gap="sm"),
        ],
    )


def progress_ring(label: str, value: float, color: str = "#6366f1",
                  size: int = 100, thickness: int = 8) -> dmc.Paper:
    """Ring progress indicator for percentages."""
    return dmc.Paper(
        shadow="xs", radius="md", p="sm", withBorder=True,
        children=[
            dmc.Stack([
                dmc.RingProgress(
                    sections=[{"value": value, "color": color, "tooltip": f"{value}%"}],
                    size=size, thickness=thickness,
                    label=dmc.Text(f"{value}%", size="sm", fw=700, ta="center"),
                ),
                dmc.Text(label, size="xs", c="#64748b", ta="center",
                         style={"maxWidth": size + 20}),
            ], align="center", gap=4),
        ],
    )


def alert_gradient(title: str, body: str, color: str = "#ef4444",
                   icon: str = "bi-exclamation-triangle-fill") -> dmc.Alert:
    """Vibrant alert card with gradient left border."""
    return dmc.Alert(
        title=title,
        color=color.replace("#", ""),
        variant="light",
        radius="md",
        icon=html.I(className=f"bi {icon}"),
        children=[dmc.Text(body, size="sm", c="#1e293b")],
        className="vibrant-alert",
    )


def vibrantsym_card(title: str, body: str, icon: str = "bi-file-medical",
                    color: str = "#6366f1", extra: list | None = None) -> dmc.Paper:
    """Vibrant content card with icon, gradient accent, and optional extra content."""
    children = [
        dmc.Group([
            dmc.ThemeIcon(size="md", radius="md", color=color, variant="light",
                          children=html.I(className=f"bi {icon}")),
            dmc.Text(title, size="sm", fw=650, c="#1e293b"),
        ], gap="sm", mb=6),
        dmc.Text(body, size="sm", c="#475569", style={"lineHeight": 1.65}),
    ]
    if extra:
        children.append(dmc.Stack(extra, gap=4, mt=8))
    return dmc.Paper(
        shadow="xs", radius="md", p="md", withBorder=True,
        style={"borderLeft": f"3px solid {color}"},
        children=children,
    )


def timeline_component(items: list[dict], color: str = "#6366f1") -> dmc.Timeline:
    """dmc Timeline from list of {title, body, icon?} dicts."""
    dmc_items = []
    for i, item in enumerate(items):
        dmc_items.append(
            dmc.TimelineItem(
                title=item.get("title", ""),
                bullet=html.I(className=f"bi {item.get('icon', 'bi-circle-fill')}"),
                children=[
                    dmc.Text(item.get("body", ""), size="xs", c="#475569",
                             style={"lineHeight": 1.55}),
                ],
            )
        )
    return dmc.Timeline(active=0, bulletSize=24, lineWidth=2, color=color.replace("#", ""),
                        children=dmc_items)


def gradient_hero_card(title: str, subtitle: str, color: str = "#6366f1") -> dmc.Paper:
    """Section hero card with gradient background."""
    return dmc.Paper(
        shadow="md", radius="lg", p="xl",
        style={"background": f"linear-gradient(135deg, {color}15, {color}05)",
               "border": f"1px solid {color}20"},
        children=[
            dmc.Title(title, order=3, c="#1e293b"),
            dmc.Text(subtitle, size="sm", c="#64748b", mt=4),
        ],
    )
