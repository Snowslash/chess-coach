from pathlib import Path

from chess_coach.web_app import STATIC_DIR, static_asset_text


def test_root_html_mentions_chess_coach_and_local_privacy():
    html = static_asset_text("index.html")

    assert "Chess Coach" in html
    assert "Runs locally" in html or "Runs locally." in html
    assert "window.chessCoachDesktop" not in html


def test_static_js_uses_fetch_and_not_electron_bridge():
    app_js = static_asset_text("app.js")

    assert "window.chessCoachDesktop" not in app_js
    assert "fetch(" in app_js
    assert "/api/bootstrap" in app_js
    assert "/api/config" in app_js
    assert "/api/analyse" in app_js


def test_static_js_uses_username_and_date_specific_workflow_outputs():
    app_js = static_asset_text("app.js")

    import_default_body = app_js.split("function defaultImportedPgnPath", 1)[1].split("function defaultAnnotatedPgnPath", 1)[0]
    sync_body = app_js.split("function syncWorkflowDefaults", 1)[1].split("function fillForm", 1)[0]
    assert "input/sample_games.pgn" not in import_default_body
    assert "function defaultAnalysisReportPath" in app_js
    assert "todaySlug()" in app_js
    assert "reports/latest.md" not in sync_body


def test_static_ui_has_reset_workflow_paths_button_and_handler():
    html = static_asset_text("index.html")
    app_js = static_asset_text("app.js")

    assert 'id="resetWorkflowPathsButton"' in html
    assert "function resetWorkflowPaths" in app_js
    assert "delete $(id).dataset.manual" in app_js
    assert "resetWorkflowPathsButton" in app_js


def test_static_css_contains_layout_rules():
    css = static_asset_text("styles.css")

    assert ".layout" in css
    assert ".panel" in css
    assert "@media" in css


def test_static_directory_contains_expected_files():
    names = {path.name for path in Path(STATIC_DIR).iterdir() if path.is_file()}

    assert {"index.html", "app.js", "styles.css"}.issubset(names)
