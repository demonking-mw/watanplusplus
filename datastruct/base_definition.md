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
    *   `[0]`=TopLeft, `[1]`=TopRight, `[2]`=Right, `[3]`=BottomRight, `[4]`=BottomLeft, `[5]`=Left.
*   `corners`: (List[Settle]) The 6 vertices of the hex (Size 6).
    *   The corners of the hexagon where settlements can be built.
*   `borders`: (List[Road]) The 6 edges of the hex (Size 6).
    *   Indices correspond to `neighbors` directions.

## 2. Settle Class (Vertex)
Represents an intersection where 3 hexes meet.
*   `owner`: (Int) `0`=Unoccupied, `1-4`=Player ID, `-1`=Unbuildable (Distance Rule).
*   `building`: (Int) `0`=None, `1`=Settlement, `2`=City.
*   `adj_hexes`: (List[Tile]) The 3 tiles touching this corner (used for resource distribution).
*   `adj_roads`: (List[Road]) The 3 roads branching from this corner (used for connectivity and longest road).
*   `port`: (Str/None) Type of harbor if present (e.g., "Generic 3:1", "Wool 2:1").

## 3. Road Class (Edge)
Represents the path between two Settlements.
*   `owner`: (Int) `0`=Unoccupied, `1-4`=Player ID.
*   `connects`: (List[Settle]) The 2 Settlements this road links (Start/End).




