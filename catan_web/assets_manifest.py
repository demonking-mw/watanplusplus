"""Asset manifest for the Catan frontend.

Maps game concepts to the image files kept under catan_web/assets/imgs. The
engine stays free of any rendering concern, so this lives at the package level
rather than in the engine. The frontend loads these over the /assets URL
prefix, which server.py serves as static files. Paths are relative to
catan_web/assets/imgs and use forward slashes.

If a path does not match a real file on disk, fix the path. The test in
catan_web/tests/test_assets.py checks every entry against the filesystem.
"""
from __future__ import annotations

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "imgs"
ASSET_URL_PREFIX = "/assets"

# Which resource each land terrain produces. Desert produces nothing. This is
# the link to the engine: terrain art is chosen by the resource a hex yields.
RESOURCE_BY_TERRAIN = {
    "forest": "lumber",
    "hill": "brick",
    "pasture": "wool",
    "field": "grain",
    "mountain": "ore",
    "desert": None,
}

# Terrain hex art, one SVG per terrain type.
TERRAIN = {
    "forest": "hexes/vector/forest.svg",
    "hill": "hexes/vector/hill.svg",
    "pasture": "hexes/vector/pasture.svg",
    "field": "hexes/vector/field.svg",
    "mountain": "hexes/vector/mountain.svg",
    "desert": "hexes/vector/desert.svg",
}

# Resource card art plus the card back.
RESOURCE_CARDS = {
    "brick": "resources/vector/resources--brick.png",
    "lumber": "resources/vector/resources--lumber.png",
    "grain": "resources/vector/resources--grain.png",
    "wool": "resources/vector/resources--wool.png",
    "ore": "resources/vector/resources--ore.png",
    "back": "resources/vector/resources--back.png",
}

# Development card art plus the back. Four action types and five victory point
# types, matching the standard base game deck.
DEV_CARDS = {
    "knight": "dcs/vector/dcs__knight.png",
    "road_building": "dcs/vector/dcs__roadBuilding.png",
    "year_of_plenty": "dcs/vector/dcs__yearOfPlenty.png",
    "monopoly": "dcs/vector/dcs__monopoly.png",
    "chapel": "dcs/vector/dcs__chapel.png",
    "library": "dcs/vector/dcs__library.png",
    "market": "dcs/vector/dcs__market.png",
    "palace": "dcs/vector/dcs__palace.png",
    "university": "dcs/vector/dcs__university.png",
    "back": "dcs/vector/dcs__back.png",
}

# Dice faces 1 through 6. String keys so the JSON manifest is clean.
DICE = {str(face): f"dice/vector/dice-{face}.png" for face in range(1, 7)}

# The robber piece.
ROBBER = "robber/vector/robber.png"

# Sprite sheets, kept whole for now and sliced in the frontend later.
SHEETS = {
    "pieces": "pieces/150dpi masked/pieces--.png",
    "number_tokens": "number_tokens/150dpi masked/number_token--.png",
}

# Harbor (port) tile art. Nine ports total, four 3:1 and five 2:1. The mapping
# from each file to a specific port type is confirmed in Phase 6, so these are
# listed rather than typed.
HARBORS = [
    "harbors/150dpi masked/harbor.png",
    "harbors/150dpi masked/harbor 1.png",
    "harbors/150dpi masked/harbor 2.png",
    "harbors/150dpi masked/harbor 3.png",
    "harbors/150dpi masked/harbor 4.png",
    "harbors/150dpi masked/harbor 5.png",
    "harbors/150dpi masked/harbor 6.png",
    "harbors/150dpi masked/harbor 7.png",
]

# Harbor art keyed by port type for the ocean ring tiles.
HARBOR_BY_PORT = {
    "generic": "harbors/150dpi masked/harbor.png",
    "lumber": "harbors/150dpi masked/harbor 1.png",
    "brick": "harbors/150dpi masked/harbor 2.png",
    "wool": "harbors/150dpi masked/harbor 3.png",
    "grain": "harbors/150dpi masked/harbor 4.png",
    "ore": "harbors/150dpi masked/harbor 5.png",
}

# Reference and special cards.
SPECIAL_CARDS = {
    "largest_army": "special_cards/vector/army_card.png",
    "longest_road": "special_cards/vector/road_card.png",
    "harbor": "special_cards/150dpi unmasked/harbor_card.png",
    "building_costs": "building_costs_cards/vector/building_costs.png",
}

# Optional branding. Set LOGO to None if you removed the logo.
LOGO = "logo/settlers-of-catan-logo.png"


def _all_relpaths() -> list[str]:
    """Every asset relative path referenced by this manifest."""
    paths: list[str] = []
    paths.extend(TERRAIN.values())
    paths.extend(RESOURCE_CARDS.values())
    paths.extend(DEV_CARDS.values())
    paths.extend(DICE.values())
    paths.append(ROBBER)
    paths.extend(SHEETS.values())
    paths.extend(HARBORS)
    paths.extend(HARBOR_BY_PORT.values())
    paths.extend(SPECIAL_CARDS.values())
    if LOGO:
        paths.append(LOGO)
    return paths


def url_for(relpath: str) -> str:
    """Browser URL for an asset relative path."""
    return f"{ASSET_URL_PREFIX}/{relpath}"


def missing_assets() -> list[str]:
    """Relative paths in the manifest that do not exist on disk."""
    return [rp for rp in _all_relpaths() if not (ASSETS_DIR / rp).exists()]


def manifest() -> dict:
    """The full manifest as plain data with browser URLs, for the frontend."""
    return {
        "prefix": ASSET_URL_PREFIX,
        "resource_by_terrain": RESOURCE_BY_TERRAIN,
        "terrain": {k: url_for(v) for k, v in TERRAIN.items()},
        "resource_cards": {k: url_for(v) for k, v in RESOURCE_CARDS.items()},
        "dev_cards": {k: url_for(v) for k, v in DEV_CARDS.items()},
        "dice": {k: url_for(v) for k, v in DICE.items()},
        "robber": url_for(ROBBER),
        "sheets": {k: url_for(v) for k, v in SHEETS.items()},
        "harbors": [url_for(v) for v in HARBORS],
        "harbor_by_port": {k: url_for(v) for k, v in HARBOR_BY_PORT.items()},
        "special_cards": {k: url_for(v) for k, v in SPECIAL_CARDS.items()},
        "logo": url_for(LOGO) if LOGO else None,
    }
