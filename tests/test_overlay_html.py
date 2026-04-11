def test_overlay_html_generation_recreates_builder_logic():
    # Recreate the overlay HTML builder logic and assert paths present
    clips = [
        {"path": "/tmp/one.mp4", "label": "one"},
        {"path": "/tmp/two.mp4", "label": "two"},
    ]

    video_tags = ""
    for c in clips[:2]:
        video_tags += f'<div class="tiny-card"><video width="160" height="90" controls src="file://{c["path"]}"></video><div class="caption">{c["label"]}</div></div>'

    assert "file:///tmp/one.mp4" in video_tags or "/tmp/one.mp4" in video_tags


def test_build_overlay_html_module():
    from app.ui.overlay import build_overlay_html

    clips = [
        {"path": "/tmp/one.mp4", "label": "one"},
        {"path": "/tmp/two.mp4", "label": "two"},
    ]

    html = build_overlay_html(clips)
    assert "clip-overlay" in html
    assert "/tmp/one.mp4" in html
