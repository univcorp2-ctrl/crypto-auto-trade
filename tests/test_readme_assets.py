from pathlib import Path


def test_readme_assets_exist() -> None:
    for path in [
        "docs/assets/hero-overview.svg",
        "docs/assets/strategy-overview.svg",
        "docs/assets/regime-guard-detail.svg",
        "docs/assets/trailing-stop.svg",
        "docs/assets/architecture-overview.svg",
        "docs/assets/dashboard-screen.svg",
        "docs/assets/japan-exchange-api-map.svg",
        "docs/assets/strategy-library-100.svg",
        "docs/assets/strategy-variants-map.svg",
        "docs/assets/strategy-family-vs-variant.svg",
        "docs/assets/strategy-variant-naming-guide.svg",
        "docs/assets/strategy-selection-workflow.svg",
    ]:
        assert Path(path).exists(), path


def test_strategy_variant_docs_exist() -> None:
    assert Path("STRATEGY_VARIANTS.md").exists()
    assert Path("docs/strategy-variants-explained.md").exists()
