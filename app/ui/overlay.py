"""Overlay HTML builder for floating mini-players."""

from typing import List, Dict


def build_overlay_html(
    clips: List[Dict], position: str = "bottom-right", hide_on_mobile: bool = True
) -> str:
    """Return HTML string for a floating overlay showing up to two clips.

    clips: list of dicts with keys 'path' and 'label'
    position: one of 'bottom-right', 'bottom-left'
    hide_on_mobile: whether to hide overlay using media query for narrow screens
    """
    if position not in ("bottom-right", "bottom-left"):
        position = "bottom-right"

    right_style = "right: 12px;" if position == "bottom-right" else "left: 12px;"

    video_tags = ""
    for c in clips[:2]:
        # escape minimal values by casting to str
        path = str(c.get("path", ""))
        label = str(c.get("label", ""))
        video_tags += (
            '<div class="tiny-card">'
            f'<video width="160" height="90" controls src="file://{path}"></video>'
            f'<div class="caption">{label}</div>'
            "</div>"
        )

    media_rule = (
        "@media (max-width: 480px) { .clip-overlay { display: none; } }"
        if hide_on_mobile
        else ""
    )

    html = f"""
    <style>
    .clip-overlay {{
        position: fixed;
        {right_style}
        bottom: 12px;
        z-index: 9999;
        display: flex;
        gap: 8px;
        align-items: flex-end;
    }}
    .tiny-card {{
        background: rgba(0,0,0,0.6);
        padding: 6px;
        border-radius: 8px;
        color: white;
        font-size: 12px;
    }}
    {media_rule}
    </style>
    <div class="clip-overlay">
        {video_tags}
    </div>
    """

    return html
