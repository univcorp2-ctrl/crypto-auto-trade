from pathlib import Path


def test_readme_assets_exist() -> None:
    for path in [
        "docs/assets/hero-overview.svg",
        "docs/assets/strategy-overview.svg",
        "docs/assets/regime-guard-detail.svg",
        "docs/assets/trailing-stop.svg",
        "docs/assets/architecture-overview.svg",
        "docs/assets/dashboard-screen.svg",
    ]:
        assert Path(path).exists(), path
