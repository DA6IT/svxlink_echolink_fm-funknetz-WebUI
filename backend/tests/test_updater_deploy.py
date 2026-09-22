from pathlib import Path

from app import update_worker_deploy


def test_deploy_frontend_replaces_existing_files(
    tmp_path,
    monkeypatch,
):
    live = tmp_path / "live"
    source = tmp_path / "dist"

    (live / "assets").mkdir(
        parents=True
    )

    (source / "assets").mkdir(
        parents=True
    )

    (live / "index.html").write_text(
        "old",
        encoding="utf-8",
    )

    (
        live
        / "assets"
        / "app.js"
    ).write_text(
        "old",
        encoding="utf-8",
    )

    (source / "index.html").write_text(
        "new",
        encoding="utf-8",
    )

    (
        source
        / "assets"
        / "app.js"
    ).write_text(
        "new",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        update_worker_deploy,
        "DOCROOT",
        live,
    )

    update_worker_deploy.deploy_frontend(
        source
    )

    assert (
        live
        / "index.html"
    ).read_text(
        encoding="utf-8"
    ) == "new"

    assert (
        live
        / "assets"
        / "app.js"
    ).read_text(
        encoding="utf-8"
    ) == "new"


def test_deploy_frontend_removes_stale_assets(
    tmp_path,
    monkeypatch,
):
    live = tmp_path / "live"
    source = tmp_path / "dist"

    (live / "assets").mkdir(
        parents=True
    )

    (source / "assets").mkdir(
        parents=True
    )

    (live / "index.html").write_text(
        "old",
        encoding="utf-8",
    )

    (
        live
        / "assets"
        / "old.js"
    ).write_text(
        "old",
        encoding="utf-8",
    )

    (source / "index.html").write_text(
        "new",
        encoding="utf-8",
    )

    (
        source
        / "assets"
        / "new.js"
    ).write_text(
        "new",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        update_worker_deploy,
        "DOCROOT",
        live,
    )

    update_worker_deploy.deploy_frontend(
        source
    )

    assert not (
        live
        / "assets"
        / "old.js"
    ).exists()

    assert (
        live
        / "assets"
        / "new.js"
    ).is_file()
