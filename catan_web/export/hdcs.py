"""Convert engine GameState to HDCS JSON.

HDCS is the project native schema (meta, map, players). Because the server has
full information, the exported HDCS is ground truth: res_k and devs are exact
and res_u collapses to certainty. Phase 4 implements this and validates the
output against the existing project HDCS model in a read only test.
"""
from __future__ import annotations


def to_hdcs(state: dict) -> dict:
    """Serialize the engine state into an HDCS dict.

    To be implemented in Phase 4.
    """
    raise NotImplementedError("Phase 4: HDCS export")
