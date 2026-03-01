"""AI-powered initial board state analysis agent.

Takes a completed setup board (all 8 settlements placed) and performs
a 2-call sequential AI analysis to produce a relative win-probability
4-tuple.

Architecture
------------
**Call 1 — Situational Analysis**
    Feed: full board layout, ports, roads, settlements, init_eval scores,
    starting hands, open spots, per-number production, robber predictions.
    Ask:  core objectives per player, races for key spots, activation
    difficulty, building space.

**Call 2 — Strategic Dynamics + Win Probability Synthesis**
    Feed: Call 1 output + trade synergy data, algorithmic targeting,
    baseline scores.
    Ask:  race winners, trade exploits, geopolitical targeting,
    final 4-tuple win probabilities with justification.

Usage::

    import asyncio
    from settle_process import analyze_init_board

    probs, report = asyncio.run(analyze_init_board(gs))
    # probs = (0.22, 0.31, 0.19, 0.28)
    # report = full text from the 3 AI calls
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

from ai import query_ai_async, AIProvider
from base_computes.game_state import GameState, VALID_NODES, compute_starting_hands
from base_computes.init_eval import evaluate_init_board, PlayerEval
from base_computes.settle_eval_simple import (
    rank_all_spots,
    _number_to_pips,
    _spot_production,
    _compute_relative_strengths,
    _total_production_by_resource,
    _bfs_from_node,
    BASE_RESOURCE_STRENGTH,
)
from base_computes.robber_predict import predict_robber


# ── Tunable Parameters ──────────────────────────────────────────────────────

# AI call settings
AGENT_TEMPERATURE: float = 0.4  # low temperature for analytical tasks
AGENT_MAX_TOKENS_1: int = 5000  # call 1: situational analysis (includes full board)
AGENT_MAX_TOKENS_2: int = 5500  # call 2: dynamics + win probability synthesis


# ── Data preparation helpers ────────────────────────────────────────────────

RESOURCE_NAMES = ["Wood", "Brick", "Wool", "Grain", "Ore"]

# Tile resource types beyond the 5 player resources
_RES_LABELS = {
    0: "Wood",
    1: "Brick",
    2: "Wool",
    3: "Grain",
    4: "Ore",
    5: "Desert",
    6: "Ocean",
}

_PORT_LABELS = {
    0: "2:1 Wood",
    1: "2:1 Brick",
    2: "2:1 Wool",
    3: "2:1 Grain",
    4: "2:1 Ore",
    5: "3:1 any",
}

# Row sizes for the hex grid (row-major, top-to-bottom)
_BOARD_ROW_SIZES = [4, 5, 6, 7, 6, 5, 4]


def _board_layout(gs: GameState) -> str:
    """Full board tile layout in a compact, row-by-row format.

    Each tile is shown as: TileID:Resource(#Number) or TileID:Port(type).
    This gives the AI spatial awareness of resource distribution and adjacency.
    """
    lines = []
    idx = 0
    for row_i, size in enumerate(_BOARD_ROW_SIZES):
        row_tiles = []
        for _ in range(size):
            res_id, num = gs.map.tiles[idx]
            label = _RES_LABELS.get(res_id, f"R{res_id}")
            if num == -1:
                # Port tile
                port_type = _PORT_LABELS.get(res_id, f"port:{res_id}")
                row_tiles.append(f"T{idx}:Port({port_type})")
            elif num == 0:
                # Desert or plain ocean
                row_tiles.append(f"T{idx}:{label}")
            else:
                pips = _number_to_pips(num)
                row_tiles.append(f"T{idx}:{label}(#{num},{pips}pip)")
            idx += 1
        # Indent inner rows more to approximate hex shape
        indent = "  " * abs(3 - row_i)
        lines.append(f"{indent}{' | '.join(row_tiles)}")

    lines.append(f"  Robber on: T{gs.map.robber}")
    return "\n".join(lines)


def _ports_summary(gs: GameState) -> str:
    """List all port access nodes and their types."""
    if not gs.map.ports:
        return "  (no ports)"
    lines = []
    for node_key, pt in sorted(gs.map.ports.items()):
        label = _PORT_LABELS.get(pt, f"type:{pt}")
        lines.append(f"  {node_key}: {label}")
    return "\n".join(lines)


def _roads_summary(gs: GameState) -> str:
    """List all placed roads (edges)."""
    if not gs.map.edges:
        return "  (no roads placed)"
    lines = []
    for edge_key, pid in sorted(gs.map.edges.items()):
        lines.append(f"  Player {pid} road at {edge_key}")
    return "\n".join(lines)


def _settlement_details(gs: GameState) -> str:
    """Human-readable summary of each player's settlements and adjacent tiles."""
    lines = []
    for node_key, (pid, btype) in gs.map.nodes.items():
        bname = "settlement" if btype == 1 else "city"
        tile_parts = []
        for tid_str in node_key.split("_"):
            tid = int(tid_str)
            res_id, num = gs.map.tiles[tid]
            if 0 <= res_id <= 4 and num >= 2:
                pips = _number_to_pips(num)
                tile_parts.append(f"{RESOURCE_NAMES[res_id]}(#{num}, {pips}pip)")
            elif res_id == 5:
                tile_parts.append("Desert")
            elif res_id == 6:
                tile_parts.append("Ocean")
        # Check for port
        port_str = ""
        if node_key in gs.map.ports:
            pt = gs.map.ports[node_key]
            port_str = (
                f" [PORT: {'3:1 any' if pt == 5 else f'2:1 {RESOURCE_NAMES[pt]}'}]"
            )
        lines.append(
            f"  Player {pid} {bname} at {node_key}: {', '.join(tile_parts)}{port_str}"
        )
    return "\n".join(lines)


def _production_by_number(gs: GameState) -> str:
    """For each dice number (2-12), list which player produces what."""
    # Build: number -> [(player_id, resource, pips)]
    number_prod: Dict[int, List[Tuple[int, str, int]]] = {}
    for num in range(2, 13):
        if num == 7:
            continue
        number_prod[num] = []

    for node_key, (pid, btype) in gs.map.nodes.items():
        mult = 2 if btype == 2 else 1
        for tid_str in node_key.split("_"):
            tid = int(tid_str)
            res_id, num = gs.map.tiles[tid]
            if 0 <= res_id <= 4 and num >= 2:
                number_prod.setdefault(num, []).append(
                    (pid, RESOURCE_NAMES[res_id], _number_to_pips(num) * mult)
                )

    lines = []
    for num in sorted(number_prod.keys()):
        entries = number_prod[num]
        if not entries:
            continue
        prob = _dice_probability(num)
        parts = [f"P{pid}:{res}({pips}pip)" for pid, res, pips in entries]
        lines.append(f"  #{num} ({prob:.1%} chance): {', '.join(parts)}")
    return "\n".join(lines)


def _dice_probability(num: int) -> float:
    """Probability of rolling a given sum on 2d6."""
    ways = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1}
    return ways.get(num, 0) / 36.0


def _trade_synergies(gs: GameState) -> str:
    """Identify same-number co-production opportunities for trades.

    When two players produce complementary resources on the same number,
    a dice roll creates a natural trade opportunity.
    """
    # number -> {player_id: {resource: total_pips}}
    per_number: Dict[int, Dict[int, Dict[str, int]]] = {}
    for node_key, (pid, btype) in gs.map.nodes.items():
        mult = 2 if btype == 2 else 1
        for tid_str in node_key.split("_"):
            tid = int(tid_str)
            res_id, num = gs.map.tiles[tid]
            if 0 <= res_id <= 4 and num >= 2:
                per_number.setdefault(num, {}).setdefault(pid, {})
                rname = RESOURCE_NAMES[res_id]
                per_number[num][pid][rname] = (
                    per_number[num][pid].get(rname, 0) + _number_to_pips(num) * mult
                )

    synergies = []
    # Complement pairs for trade analysis
    complement_labels = [("Wood", "Brick"), ("Grain", "Ore")]

    for num, players_prod in sorted(per_number.items()):
        if len(players_prod) < 2:
            continue
        pids = sorted(players_prod.keys())
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                pa, pb = pids[i], pids[j]
                res_a = players_prod[pa]
                res_b = players_prod[pb]
                for r1, r2 in complement_labels:
                    # Player A has r1 surplus, Player B has r2 surplus
                    if r1 in res_a and r2 in res_b and r1 not in res_b:
                        synergies.append(
                            f"  #{num}: P{pa} gets {res_a[r1]}pip {r1}, "
                            f"P{pb} gets {res_b[r2]}pip {r2} → natural {r1}/{r2} trade"
                        )
                    if r2 in res_a and r1 in res_b and r2 not in res_b:
                        synergies.append(
                            f"  #{num}: P{pa} gets {res_a[r2]}pip {r2}, "
                            f"P{pb} gets {res_b[r1]}pip {r1} → natural {r2}/{r1} trade"
                        )

    return (
        "\n".join(synergies)
        if synergies
        else "  (no clear same-number trade synergies found)"
    )


def _open_spots_summary(gs: GameState) -> str:
    """Summarise the top open settlement spots and which players are closest."""
    ranked = rank_all_spots(gs, top_n=12)
    if not ranked:
        return "  (no open spots)"

    lines = []
    for node_key, score in ranked:
        # Which players are nearby (BFS from each player's settlements)
        nearby = []
        for nk, (pid, _) in gs.map.nodes.items():
            reachable = _bfs_from_node(gs, nk, max_dist=4)
            if node_key in reachable:
                dist, _ = reachable[node_key]
                if dist <= 4:
                    nearby.append(f"P{pid}({dist} roads)")
        # Spot resources
        tile_parts = []
        for tid_str in node_key.split("_"):
            tid = int(tid_str)
            res_id, num = gs.map.tiles[tid]
            if 0 <= res_id <= 4 and num >= 2:
                tile_parts.append(f"{RESOURCE_NAMES[res_id]}(#{num})")
            elif res_id == 5:
                tile_parts.append("Desert")
        port_str = ""
        if node_key in gs.map.ports:
            pt = gs.map.ports[node_key]
            port_str = f" [PORT: {'3:1' if pt == 5 else f'2:1 {RESOURCE_NAMES[pt]}'}]"

        lines.append(
            f"  {node_key} (score={score:.1f}): "
            f"{', '.join(tile_parts)}{port_str} | Nearby: {', '.join(nearby) if nearby else 'none'}"
        )
    return "\n".join(lines)


def _format_eval_results(
    scores: Tuple[float, ...],
    results: List[PlayerEval],
) -> str:
    """Format init_eval results into a readable string."""
    lines = [
        f"Algorithmic normalised win-likelihood: {tuple(round(s, 4) for s in scores)}"
    ]
    lines.append("")
    for ev in results:
        lines.append(f"Player {ev.player_id}:  raw_score={ev.total_score:.2f}")
        lines.append(
            f"  Strategy index: {ev.strategy_index:.3f} (0=road/WoodBrick, 1=city/OreWheatSheep)"
        )
        lines.append(
            f"  Raw production (pre-robber): W={ev.raw_prod[0]:.1f} B={ev.raw_prod[1]:.1f} Sh={ev.raw_prod[2]:.1f} Wh={ev.raw_prod[3]:.1f} O={ev.raw_prod[4]:.1f}"
        )
        lines.append(
            f"  Post-robber production:      W={ev.base_prod[0]:.1f} B={ev.base_prod[1]:.1f} Sh={ev.base_prod[2]:.1f} Wh={ev.base_prod[3]:.1f} O={ev.base_prod[4]:.1f}"
        )
        lines.append(
            f"  Paired production:           W={ev.paired_prod[0]:.1f} B={ev.paired_prod[1]:.1f} Sh={ev.paired_prod[2]:.1f} Wh={ev.paired_prod[3]:.1f} O={ev.paired_prod[4]:.1f}"
        )
        lines.append(f"  Prod pairs: {ev.prod_pairs if ev.prod_pairs else 'none'}")
        lines.append(f"  Port access bonus: {'yes' if ev.has_port_access else 'no'}")
        lines.append(f"  Targets: Player {ev.target}")
        bd = ev.breakdown
        breakdown_items = []
        for k, v in bd.items():
            if k not in (
                "wb_ows_power",
                "strategy_index",
                "total_pips",
                "total_prod",
                "valued_prod",
                "target",
            ):
                breakdown_items.append(f"{k}={v:.2f}")
        lines.append(f"  Score components: {', '.join(breakdown_items)}")
        lines.append("")
    return "\n".join(lines)


def _format_starting_hands(hands: List[List[int]]) -> str:
    """Format starting hands into readable string."""
    lines = []
    for pid, hand in enumerate(hands):
        parts = [f"{RESOURCE_NAMES[r]}={hand[r]}" for r in range(5) if hand[r] > 0]
        total = sum(hand)
        lines.append(
            f"  Player {pid}: {', '.join(parts) if parts else '(empty)'} (total={total})"
        )
    return "\n".join(lines)


def _format_robber_predictions(gs: GameState) -> str:
    """Format robber prediction as readable string."""
    preds = predict_robber(gs)
    lines = []
    for pid, player_preds in enumerate(preds):
        parts = []
        for tile_id, prob in player_preds:
            res_id, num = gs.map.tiles[tile_id]
            rname = RESOURCE_NAMES[res_id] if 0 <= res_id <= 4 else "?"
            parts.append(f"T{tile_id}({rname}#{num}, {prob:.1%})")
        lines.append(f"  Player {pid} rob targets: {', '.join(parts)}")
    return "\n".join(lines)


# ── System prompt ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert Catan strategy analyst. You are analysing the board state at the moment when all 4 players have finished placing their initial two settlements (8 total) and before the game begins.

Key Catan facts for reference:
- Road costs 1 Wood + 1 Brick
- Settlement costs 1 Wood + 1 Brick + 1 Wool + 1 Grain
- City costs 2 Grain + 3 Ore
- Development card costs 1 Wool + 1 Grain + 1 Ore
- Longest Road (5+ roads) = 2 VP; Largest Army (3+ knights) = 2 VP
- Win at 10 VP; settlements = 1 VP, cities = 2 VP
- When 7 is rolled, players with 8+ cards discard half; then robber is moved
- Robber blocks production on the tile it sits on
- Resource scarcity creates trade leverage; 4:1 bank trade is always available
- Pips measure expected production: a 6 or 8 = 5 pips (5/36 chance), 5 or 9 = 4 pips, etc.
- Strategy index: 0 = pure Wood/Brick ("road" strategy), 1 = pure Ore/Wheat/Sheep ("city/dev" strategy)
- In the setup phase, each player receives one of each resource from tiles adjacent to their SECOND settlement
- Complement pairs: Wood+Brick (for roads/settlements), Grain+Ore (for cities)

IMPORTANT: You are supplementing an algorithmic analysis, not replacing it. The algorithmic evaluation is reasonable but lacks strategic depth: it doesn't model races, trade dynamics, activation order, or geopolitical factors. Your job is to add THAT strategic nuance. Be specific and justify claims with board data."""


# ── Prompt builders ─────────────────────────────────────────────────────────


def _build_prompt_1(
    gs: GameState,
    scores: Tuple[float, ...],
    results: List[PlayerEval],
    hands: List[List[int]],
) -> str:
    """Build the prompt for Call 1: Situational Analysis."""

    settlement_info = _settlement_details(gs)
    eval_info = _format_eval_results(scores, results)
    hand_info = _format_starting_hands(hands)
    prod_by_num = _production_by_number(gs)
    open_spots = _open_spots_summary(gs)
    robber_info = _format_robber_predictions(gs)
    board_info = _board_layout(gs)
    ports_info = _ports_summary(gs)
    roads_info = _roads_summary(gs)

    return f"""Analyse this Catan board state at the start of the game (after setup, before first turn).

=== FULL BOARD LAYOUT ===
The board is a hex grid of 37 tiles (IDs 0-36), laid out row-major (top-to-bottom, left-to-right) in rows of size [4, 5, 6, 7, 6, 5, 4]. The 19 inner tiles are land (resource + number token); the 18 outer tiles are ocean (some are ports). Two tiles are adjacent if they share an edge in the hex grid. A settlement sits at the intersection of exactly 3 mutually adjacent tiles, keyed as "T1_T2_T3" (sorted ascending). A road sits on the edge between 2 adjacent tiles, keyed as "T1_T2".
Format: TileID:Resource(#NumberToken, pips) — pips = expected rolls per 36 dice throws.
{board_info}

=== PORTS ===
Port access nodes (settlement spots that grant port trading). Each node is "T1_T2_T3". Two nodes with the same port type are the two access points of one physical port. Types: 2:1 trades a specific resource at 2:1 ratio; 3:1 trades any resource at 3:1 ratio.
{ports_info}

=== ROADS PLACED ===
{roads_info}

=== SETTLEMENT PLACEMENTS ===
Each player has 2 settlements. The tiles adjacent to each settlement produce resources when their number is rolled.
{settlement_info}

=== ALGORITHMIC EVALUATION (init_eval) ===
This is a heuristic scoring of each player's position. It accounts for post-robber production, strategy alignment, port access, number pairing bonuses, and targeting. The normalised scores are NOT win probabilities — they are relative positional strength.
{eval_info}

=== STARTING HANDS ===
Each player received one resource card per resource tile adjacent to their SECOND settlement.
{hand_info}

=== PRODUCTION BY DICE NUMBER ===
What each player receives when a specific number is rolled. Higher pip count = more production from that tile per roll.
{prod_by_num}

=== TOP OPEN SETTLEMENT SPOTS ===
The highest-scoring available spots for future expansion, with distance to each player's existing settlements in road hops.
{open_spots}

=== ROBBER PREDICTION ===
Algorithmic prediction of where each player would place the robber. Used to estimate post-robber production. Probabilities per player sum to 1.
{robber_info}

Please analyse the following (be specific, reference board positions and numbers):

1. **Core Objectives**: For each player, what must they do ASAP to "fully activate" their setup? Consider:
   - What resources do they lack? What key spot would complete their strategy?
   - For road players (low strategy index): what expansion paths give them critical resources?
   - For city/dev players (high strategy index): can they reach a city quickly?
   - Rate each player's activation difficulty on a scale of 1-5 (1=already activated, 5=very hard).

2. **Races**: Identify cases where two or more players want the same open spot or mutually exclusive spots. For each race:
   - Which spot is contested?
   - Which players are competing?
   - How many roads does each player need to get there?
   - Who has the starting cards to build roads faster?

3. **Building Space**: For each road-oriented player, how many viable expansion spots do they have within 3-4 roads? Can opponents cut them off?

4. **Activation Timeline**: Estimate roughly how many turns each player needs to reach their first major milestone (3rd settlement, first city, or longest road).

Output your analysis in structured sections."""


def _build_prompt_2(
    gs: GameState,
    call1_output: str,
    algo_scores: Tuple[float, ...],
    results: List[PlayerEval],
) -> str:
    """Build the prompt for Call 2: Strategic Dynamics + Win Probability Synthesis."""

    trade_synergies = _trade_synergies(gs)

    return f"""Continue your Catan analysis. Below is your previous situational analysis, plus new data on trade dynamics. After your analysis, you will produce final win probabilities.

=== YOUR PREVIOUS ANALYSIS (Call 1) ===
{call1_output}

=== TRADE SYNERGIES ===
When a number is rolled, multiple players often receive resources simultaneously. If they produce complementary resources on the same number, a natural trade opportunity exists. These are the algorithmically detected same-number trade synergies:
{trade_synergies}

=== ALGORITHMIC TARGETING ===
The algorithmic evaluator predicted these targeting relationships (each player targets a rival):
{chr(10).join(f"  Player {r.player_id} targets Player {r.target}" for r in results)}

=== ALGORITHMIC BASELINE SCORES ===
The pure algorithmic evaluator (init_eval) produced these normalised scores:
  Player 0: {algo_scores[0]:.4f}
  Player 1: {algo_scores[1]:.4f}
  Player 2: {algo_scores[2]:.4f}
  Player 3: {algo_scores[3]:.4f}
These capture production quality, strategy alignment, port access, number pairing, and basic targeting, but do NOT capture: races, trade dynamics, activation timing, geopolitical factors, or building space.

--- PART A: STRATEGIC DYNAMICS ---

Analyse the following:

1. **Race Winners**: For each race you identified, who is most likely to win and why? Consider:
   - Starting hand advantage (who can build a road immediately?)
   - Production advantage (who gets road materials faster?)
   - Does winning the race require specific dice rolls?

2. **Trade Exploits**: Can any player leverage natural trade synergies to win a race or gain advantage?
   - Identify players who co-produce complementary resources on the same number
   - Could a third player's trade with one racer decide the outcome of a race?

3. **Geopolitical Targeting**: After the first 3-5 turns:
   - Who will likely be seen as the leader and get robbed?
   - If someone wins a key race, do they become a target?
   - Are there alliances of convenience (e.g. two city players who don't compete for the same spots)?

--- PART B: WIN PROBABILITY SYNTHESIS ---

Now synthesise everything (your Call 1 analysis + the dynamics above + the algorithmic baseline) into final win probabilities. You MUST:

1. For each player, write 2-3 sentences summarising their strongest advantage and biggest risk.

2. State any significant adjustment you're making to the algorithmic scores and why (e.g., "Player 2 is likely to lose the race for spot X, reducing their expected production significantly").

3. Output your final win probabilities in EXACTLY this format on its own line:
PROBABILITIES: [X.XX, X.XX, X.XX, X.XX]

The four values must sum to 1.00 (within rounding). They represent Player 0, 1, 2, 3 respectively.

IMPORTANT: The probabilities should reflect relative likelihood of winning the game, not just positional strength. A player with great position but likely to be targeted may have lower win probability. A player with moderate position but good activation timing and no enemies may outperform."""


# ── Response parsing ────────────────────────────────────────────────────────


def _parse_probabilities(text: str) -> Optional[Tuple[float, float, float, float]]:
    """Extract the PROBABILITIES: [a, b, c, d] line from AI output."""
    # Look for the PROBABILITIES line
    pattern = r"PROBABILITIES:\s*\[([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\]"
    match = re.search(pattern, text)
    if match:
        vals = [float(match.group(i)) for i in range(1, 5)]
        total = sum(vals)
        if total > 0:
            # Normalise to ensure they sum to exactly 1
            vals = [v / total for v in vals]
        return (vals[0], vals[1], vals[2], vals[3])
    return None


# ── Public API ──────────────────────────────────────────────────────────────


async def analyze_init_board(
    gs: GameState,
    *,
    provider: Optional[AIProvider] = None,
    model: Optional[str] = None,
    verbose: bool = False,
    debug: bool = False,
) -> Tuple[Tuple[float, float, float, float], str]:
    """Run the 2-call AI analysis pipeline on an initial board state.

    Parameters
    ----------
    gs : GameState
        Board with all 8 settlements placed (end of setup phase).
    provider : AIProvider, optional
        AI provider override (default: use configured default).
    model : str, optional
        Model override.
    verbose : bool
        If True, print progress to stdout.
    debug : bool
        If True, print AI prompts and responses to terminal.

    Returns
    -------
    (probabilities, full_report)
        probabilities: 4-tuple of floats summing to 1.
        full_report:   concatenation of all AI call outputs.
    """
    # ── Step 0: run algorithmic evaluations ──────────────────────────
    if verbose:
        print("[Agent] Running algorithmic evaluations...")

    algo_scores, eval_results = evaluate_init_board(gs)
    hands = compute_starting_hands(gs)

    ai_kwargs = {}
    if provider is not None:
        ai_kwargs["provider"] = provider
    if model is not None:
        ai_kwargs["model"] = model

    # ── Call 1: Situational Analysis ─────────────────────────────────
    if verbose:
        print("[Agent] Call 1: Situational Analysis...")

    prompt1 = _build_prompt_1(gs, algo_scores, eval_results, hands)
    call1_output = await query_ai_async(
        prompt1,
        system=SYSTEM_PROMPT,
        temperature=AGENT_TEMPERATURE,
        max_tokens=AGENT_MAX_TOKENS_1,
        debug=debug,
        **ai_kwargs,
    )

    if verbose:
        print(f"[Agent] Call 1 complete ({len(call1_output)} chars)")

    # ── Call 2: Strategic Dynamics + Win Probability Synthesis ───────
    if verbose:
        print("[Agent] Call 2: Dynamics & Win Probabilities...")

    prompt2 = _build_prompt_2(gs, call1_output, algo_scores, eval_results)
    call2_output = await query_ai_async(
        prompt2,
        system=SYSTEM_PROMPT,
        temperature=AGENT_TEMPERATURE,
        max_tokens=AGENT_MAX_TOKENS_2,
        debug=debug,
        **ai_kwargs,
    )

    if verbose:
        print(f"[Agent] Call 2 complete ({len(call2_output)} chars)")

    # ── Parse probabilities ──────────────────────────────────────────
    probs = _parse_probabilities(call2_output)
    if probs is None:
        if verbose:
            print(
                "[Agent] WARNING: Could not parse probabilities from AI output, "
                "falling back to algorithmic scores"
            )
        probs = algo_scores

    # ── Compile full report ──────────────────────────────────────────
    separator = "\n" + "=" * 72 + "\n"
    full_report = (
        f"{'=' * 72}\n"
        f"CALL 1: SITUATIONAL ANALYSIS\n"
        f"{'=' * 72}\n\n"
        f"{call1_output}\n"
        f"{separator}"
        f"CALL 2: DYNAMICS & WIN PROBABILITIES\n"
        f"{'=' * 72}\n\n"
        f"{call2_output}\n"
        f"{separator}"
        f"FINAL PROBABILITIES: {probs}\n"
        f"ALGORITHMIC BASELINE: {algo_scores}\n"
    )

    return probs, full_report
