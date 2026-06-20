"""Asset manifest tests. Every referenced file must exist on disk."""
from catan_web import assets_manifest


def test_no_missing_assets():
    missing = assets_manifest.missing_assets()
    assert missing == [], f"Missing asset files: {missing}"


def test_terrain_resource_mapping():
    assert assets_manifest.RESOURCE_BY_TERRAIN["desert"] is None
    produced = {v for v in assets_manifest.RESOURCE_BY_TERRAIN.values() if v}
    assert produced == {"lumber", "brick", "wool", "grain", "ore"}


def test_manifest_urls_use_prefix():
    m = assets_manifest.manifest()
    assert m["terrain"]["forest"].startswith("/assets/")
    assert m["dice"]["1"].startswith("/assets/")
    assert m["robber"].startswith("/assets/")
