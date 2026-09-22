from app import update_worker_prepare as prepare


def test_fetch_target_forces_private_tracking_ref(
    monkeypatch,
    tmp_path,
):
    target = "a" * 40
    calls = []

    monkeypatch.setattr(
        prepare,
        "UPDATE_BRANCH",
        "feature/web-updater",
    )

    monkeypatch.setattr(
        prepare,
        "remote_revision",
        lambda log: target,
    )

    def fake_git(
        *args,
        log,
        timeout=120,
    ):
        calls.append(args)

        if args[0] == "rev-parse":
            return target

        return ""

    monkeypatch.setattr(
        prepare,
        "git",
        fake_git,
    )

    prepare.fetch_target(
        target,
        tmp_path / "update.log",
    )

    fetch = next(
        args
        for args in calls
        if args[0] == "fetch"
    )

    assert fetch[-1] == (
        "+refs/heads/"
        "feature/web-updater:"
        "refs/remotes/"
        "svxlink-webui-updater/"
        "feature/web-updater"
    )
