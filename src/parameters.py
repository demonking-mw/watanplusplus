"""Centralised tunable parameters for the Watan++ Catan AI.

All algorithmic / scoring / simulation parameters live here.
Import what you need::

    from parameters import DAMPENING_FACTOR, K, ROBBER_K

Parameters are grouped by the subsystem that consumes them.
"""

from __future__ import annotations

from typing import List, Optional


# ══════════════════════════════════════════════════════════════════════════════
#  Settlement Scoring  (settle_eval_simple)
# ══════════════════════════════════════════════════════════════════════════════

# Intrinsic value multiplier per resource type.
# Index order: [Wood, Brick, Wool, Grain, Ore].
BASE_RESOURCE_STRENGTH: List[float] = [1.0, 1.03, 0.9, 1.25, 1.2]

# Controls how aggressively relative-strength is clamped.
# Applied as ``strength ** dampening_factor`` (values < 1 compress,
# values > 1 amplify).  0.5 is a square-root dampener.
DAMPENING_FACTOR: float = 0.8

# Multiplier applied to port strength when the spot has port access.
PORT_BONUS: float = 3

# Scaled bonus added when a spot has total production >= 10 *and*
# at least 3 distinct resource types.
# Actual bonus = PRIME_VARIATE_BONUS * (lowest pip among produced resources).
PRIME_VARIATE_BONUS: float = 1.2

# Multiplier for the complement-parity bonus.  For each
# complement pair (Wood/Brick, Grain/Ore), if the spot produces
# both, the bonus is ``parity_preference × min(prod_a, prod_b)``.
PARITY_PREFERENCE: float = 1.3

# Five floats that scale the five evaluation metrics before summing:
#   [0] raw_production  — sum of pips across the spot's tiles.
#   [1] scarcity_weighted — dot-product of spot production with dampened
#       resource relative-strengths (how rare each resource is on the board).
#   [2] port — port_strength × PORT_BONUS when the spot is a port access node.
#   [3] prime_variate — PRIME_VARIATE_BONUS × lowest pip of produced resources
#       when total pips ≥ 10 and ≥ 3 distinct resource types.
#   [4] parity — for each complement pair (Wood/Brick, Grain/Ore), adds
#       PARITY_PREFERENCE × min(pair_production) when both are produced.
EVAL_WEIGHTS: List[float] = [1.0, 1.5, 1.0, 1.0, 1.0]

# Score spread controller for settle_decision softmax.
# Controls probability distribution: higher K = more different probabilities (more peaked),
# lower K = more similar probabilities (more uniform). K=1.0 is standard softmax.
# ALREADY TUNED
K: float = 1.5


# ══════════════════════════════════════════════════════════════════════════════
#  Robber Prediction  (robber_predict)
# ══════════════════════════════════════════════════════════════════════════════

# How much robbing cares about raw production power vs. rare resources.
# Higher = more weight on raw production; lower = more weight on resource
# scarcity.  Added to each dampened relative strength before scoring.
RAW_POWER_PREFERENCE: float = 0.3

# Dampening factor for relative-strength calculation (same formula as
# settle scoring, but a separate value so it can be tuned independently).
# Applied as ``strength ** dampening``.  < 1 compresses, > 1 amplifies.
ROBBER_DAMPENING_FACTOR: float = 0.6

# Softmax spread factor for converting tile scores → probabilities.
# Higher = more peaked (strongest tile gets much higher probability),
# lower  = more uniform.  Separate from the settle-decision K so it
# can be tuned independently.
ROBBER_K: float = 0.2


# ══════════════════════════════════════════════════════════════════════════════
#  Initial Evaluation  (init_eval)
# ══════════════════════════════════════════════════════════════════════════════

# --- Strategy-alignment bonuses (flat additions to total score) ---
WB_BONUS: float = 2.0  # most wood/brick-focused player (lowest strategy index)
OWS_BONUS: float = 2.5  # most ore/wheat/sheep-focused player (highest strategy index)
EXTREME_BONUS: float = 1  # most polarised strategy (furthest from other players' avg)

# --- Production-pair multiplier ---
# When a player has both halves of a complement pair (wood+brick OR
# wheat+ore) on the SAME dice number, those tiles' effective production
# is multiplied by this value FOR THAT PLAYER ONLY.
PROD_PAIR_BONUS: float = 1.3

# --- Aggregate-production scoring weights ---
TOTAL_MULTIPLIER: float = 0.5  # × sum(player's paired production)
TOTAL_VALUED_MULTIPLIER: float = 0.8  # × strength-weighted paired production

# --- Port-accessibility bonus ---
PORTABILITY_BONUS: float = 2.0

# --- Positional-advantage bonuses ---
BEST_ROAD_BONUS: float = 1.5  # player with highest wood+brick production
BEST_CITY_BONUS: float = 1.5  # player with highest ore+grain production

# --- No-wheat penalty ---
# Applied when a player's pre-robber, pre-pair-bonus wheat (grain)
# production is ≤ 2 pips.  Removed entirely if the player already
# sits on a 3:1 port; reduced to 1× if a 3:1 port is reachable
# within PORT_REACH_MIN .. PORT_REACH_MAX road hops.
NO_WHEAT: float = 1.0

# --- Targeting penalty ---
# Each player targets a rival; subtract this from the target's score.
# If multiple players target the same rival, penalty stacks.
TARGET_PENALTY: float = 1

# --- Relative-strength dampening (separate from settle/robber models) ---
INIT_EVAL_DAMPENING: float = 0.7

# --- Port reachability BFS distance limits (inclusive) ---
PORT_REACH_MIN: int = 2
PORT_REACH_MAX: int = 3


# ══════════════════════════════════════════════════════════════════════════════
#  Settlement Simulation  (settle_sim)
# ══════════════════════════════════════════════════════════════════════════════

# Maximum number of placeout board states retained per settlement option.
# After each simulated placement, if cases exceed this count, only the
# top MAX_WINDOW by probability are kept and re-normalized.
MAX_WINDOW: int = 15

# Standard 4-player snake-draft settlement order.
# Round 1: 0 → 1 → 2 → 3
# Round 2: 3 → 2 → 1 → 0
SETTLE_ORDER: List[int] = [0, 1, 2, 3, 3, 2, 1, 0]


# ══════════════════════════════════════════════════════════════════════════════
#  AI Analysis  (init_analysis)
# ══════════════════════════════════════════════════════════════════════════════

# AI call settings
AGENT_TEMPERATURE: float = (
    1.0  # GPT-5 mini currently supports only the default temperature
)
AGENT_MAX_TOKENS: int = 8000  # single merged call: full analysis + win probabilities
AGENT_SERVICE_TIER: Optional[str] = "priority"


# ══════════════════════════════════════════════════════════════════════════════
#  Bot Orchestration  (settle_bot)
# ══════════════════════════════════════════════════════════════════════════════

# Per settle option, how many of the most-likely placeouts are scored
# via the full AI pipeline. Remaining placeouts use fast algorithmic
# evaluator.
AI_CUTOFF: int = 8

# OpenAI service tier override for bot AI calls.
AI_SERVICE_TIER: Optional[str] = "priority"
