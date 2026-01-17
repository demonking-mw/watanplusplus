Board view:
![alt text](image.png)

# Catan Board Model Definition

## Overview
- **Tile**: A hexagonal terrain piece. Produces resources.
- **Settle (Intersection)**: A corner shared by up to 3 tiles. Players build Settlements and Cities here.
- **Road (Edge)**: A path connecting two intersections.

## 1. Tile Class
Represents a hexagonal terrain tile.
*   `terrain`: (Enum/Str) Type of resource ('forest'->wood, 'hill'->brick, 'pasture'->sheep, 'field'->wheat, 'mountain'->ore, 'desert').
*   `token_num`: (Int) The dice number (2-12) that triggers this tile.
*   `has_robber`: (Bool) `True` if the Robber is currently on this tile (blocks resources).
*   `neighbors`: (List[Tile]) Adjacent hexes (Size 6).
    *   `[0]`=TopLeft(NW), `[1]`=TopRight(NE), `[2]`=Right(E), `[3]`=BottomRight(SE), `[4]`=BottomLeft(SW), `[5]`=Left(W).
*   `corners`: (List[Settle]) The 6 vertices of the hex (Size 6).
    *   `[0]`=Top, `[1]`=TopLeft, `[2]`=BottomLeft, `[3]`=Bottom, `[4]`=BottomRight, `[5]`=TopRight.
*   `borders`: (List[Road]) The 6 edges of the hex (Size 6).
    *   Indices correspond to `neighbors` directions.

## 2. Settle Class (Vertex)
Represents an intersection where 3 hexes meet.
*   `owner`: (Int) `0`=Unoccupied, `1-4`=Player ID, `-1`=Unbuildable (Distance Rule violations).
*   `building`: (Int) `0`=None, `1`=Settlement (1 VP), `2`=City (2 VP).
*   `adj_hexes`: (List[Tile]) The 3 tiles touching this corner (used for resource distribution).
    *   `[0]`=Left, `[1]`=Right, `[2]`=Vertical (Up/Down depending on orientation).
*   `adj_roads`: (List[Road]) The 3 roads branching from this corner (used for connectivity).
*   `port`: (Str/None) Type of harbor if present (e.g., "Generic 3:1", "Wool 2:1").

## 3. Road Class (Edge)
Represents the path between two Settlements.
*   `owner`: (Int) `0`=Unoccupied, `1-4`=Player ID.
*   `connects`: (List[Settle]) The 2 Settlements this road links (Start/End).


## 4. Board Class
Manages the global state, the graph of connected components, and coordinate lookups.

### Data Structures
*   `hex_grid`: (2D List[Tile]) A 2D array representation of the board for coordinate access.
    *   **Coordinate System**: Axes are Horizontal (x/col) and Diagonal Left-Down (y/row).
    *   **Ocean Layer**: The playable board is surrounded by a ring of "Ocean" tiles (some containing Ports).
    *   **Mapping**:
        *   `[0, 0]` = Top-left Ocean/Port tile.
        *   `[1, 1]` = Top-left Resource Tile (first row of actual terrain).
        *   `[1, 3]` = Top-right Resource Tile (skips indices due to hex stagger/offset).
*   `vertex_grid`: (2D List[Settle]) A flattened 2D array for accessing intersection points (Settlements) by row.
    *   **Row Flattening**: The "zig-zag" pattern of vertices (peaks and valleys) along a hex row is flattened into a linear list.
    *   **Example**: The top 3 vertices (peaks) of the top row of 3 tiles are stored sequentially in `vertex_grid[0]`.
*   `graph_network`: (Graph Structure) The logical web of pointers.
    *   Ensures every `Tile` points to its valid neighbors.
    *   Ensures every `Settle` points to adjacent tiles and roads.
    *   Ensures every `Road` points to its two endpoints.

### Initialization & Methods
*   `initialize_graph()`: 
    1.  Generates the `hex_grid` (including oceans).
    2.  Generates the `vertex_grid` (flattening the zig-zags).
    3.  Creates `Road` objects to bridge adjacent `Settles`.
    4.  Links all pointers (Tile neighbors, Settle adjacencies).
*   `place_ports()`: Assigns port properties to specific Ocean tiles and their touching coastal Settlements.
*   `robber_tile`: (Tile) Pointer to the tile currently occupied by the Robber.



## 5. Player Class
Represents a player in the game, tracking their assets, hand, and AI-related state.

### Gameplay Variables
*   `player_id`: (Int) Unique identifier (1-4).
*   `settlements`: (List[Settle]) All settlements and cities this player has built.
    *   Cities are distinguished by `settle.building == 2`.
*   `roads`: (List[Road]) All roads this player has placed on the board.
*   `hand`: (Dict[Str, ufloat]) Resource cards in hand.
    *   Keys: `'wood'`, `'brick'`, `'sheep'`, `'wheat'`, `'ore'`.
    *   Values: value is only unknown when robbing happens.
*   `dev_cards`: (Dict[Str, UFloat]) Development cards the player holds.
    *   Keys: `'knight'`, `'vp'` (Victory Point), `'road_build'`, `'year_plenty'`, `'monopoly'`.
    *   Values: UFloat for the same hidden-information reasoning.
*   `vp`: (ufloat) Publicly visible Victory Points (from settlements, cities, Longest Road, Largest Army).
*   `devs_played`: (list) storing what dev cards the person played

*   `knights_played`: (Int) Number of Knight cards played (used for Largest Army calculation).

### AI / Strategy Variables
*   `skill_model`: (NeuralNet / Classifier) A model representing this player's skill or play-style.
    *   Could be used to predict their likely moves or to simulate opponents of varying difficulty.
*   `threat_target`: (Int / Player) Tracks which opponent this player perceives as the biggest threat.
    *   Influences decisions like Robber placement and trade refusals.

### Notes
*   `hand` and `dev_cards` use **UFloat** (uncertain float) to support probabilistic tracking of hidden information by AI agents or opponents.
*   `skill_model` is a placeholder for future ML integration (e.g., behavior cloning, reinforcement learning policy).


## 6. Deck Class
Manages the shared supply of Resource Cards and Development Cards available to all players.

### Resource Bank
*   `resource_bank`: (Dict[Str, Int]) The pool of resource cards remaining in the game.
    *   Keys: `'wood'`, `'brick'`, `'sheep'`, `'wheat'`, `'ore'`.
    *   Values: Count of cards left (starts at 19 each in standard Catan).
    *   **Note**: When the bank runs out of a resource, players cannot receive more of that type.

### Development Card Deck
*   `dev_remaining`: (Int) Total number of development cards left in the deck.
*   `dev_probs`: (Dict[Str, Float]) Probabilistic model of what dev cards remain.
    *   Keys: `'knight'`, `'vp'`, `'road_build'`, `'year_plenty'`, `'monopoly'`.
    *   Values: Estimated probability or expected count of each type remaining.
    *   **Standard Distribution** (25 total): 14 Knights, 5 VP, 2 Road Building, 2 Year of Plenty, 2 Monopoly.
*   `update_dev_probs(event)`: Updates `dev_probs` when new information is revealed.
    *   **Triggers**: A player plays a dev card, a VP card is revealed at game end, etc.

### Notes
*   The resource bank is public information (anyone can count cards).
*   The dev deck composition is hidden, so `dev_probs` uses Bayesian inference to estimate what's left based on observed plays.
*   This is updated when say a player held on to his dev for x turns (reduced likelihood of being knight, year-of-plenty)