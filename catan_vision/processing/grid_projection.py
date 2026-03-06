import numpy as np
from .. import config


class GridProjector:
    def build_layout(self, raw_hexes, raw_nums):
        """Sorts hexes into rows and assigns numbers."""
        # Associate numbers with hexes based on bounding box inclusion
        hex_data = []
        for h in raw_hexes:
            num_val = 0
            for n in raw_nums:
                # Check if number center is inside hex box
                if (
                    h["box"][0] < n["center"][0] < h["box"][2]
                    and h["box"][1] < n["center"][1] < h["box"][3]
                ):
                    num_val = n["val"]
                    break

            hex_data.append(
                {"yolo_id": h["id"], "center": h["center"], "number": num_val}
            )

        # Sort by Y to find rows
        hex_data.sort(key=lambda x: x["center"][1])

        land_rows = []
        if not hex_data:
            return [], 80, 80  # Fallback defaults

        cur_row = [hex_data[0]]
        for i in range(1, len(hex_data)):
            if (
                abs(hex_data[i]["center"][1] - cur_row[-1]["center"][1])
                < config.Y_ROW_THRESHOLD
            ):
                cur_row.append(hex_data[i])
            else:
                land_rows.append(cur_row)
                cur_row = [hex_data[i]]
        if cur_row:
            land_rows.append(cur_row)

        # Sort each row by X
        for r in land_rows:
            r.sort(key=lambda x: x["center"][0])

        return land_rows

    def project_oceans(self, land_rows):
        """Mathematically generates the centers for the 18 ocean tiles."""
        if len(land_rows) != 5:
            return {}, 80, 80

        # Calculate average hex spacing (dx)
        dx_vals = [
            r[i]["center"][0] - r[i - 1]["center"][0]
            for r in land_rows
            for i in range(1, len(r))
        ]
        dx = np.mean(dx_vals) if dx_vals else 100

        # Calculate average row spacing (dy)
        cys = [np.mean([t["center"][1] for t in r]) for r in land_rows]
        dy = np.mean(np.diff(cys)) if len(cys) > 1 else 100

        # Map logic rows (0-6) to calculated Y coordinates
        # land_rows indices 0-4 correspond to map rows 1-5
        y_map = {
            0: cys[0] - dy,
            1: cys[0],
            2: cys[1],
            3: cys[2],
            4: cys[3],
            5: cys[4],
            6: cys[4] + dy,
        }

        # Get Left (lx) and Right (rx) X-anchors from land rows
        lx = [r[0]["center"][0] for r in land_rows]
        rx = [r[-1]["center"][0] for r in land_rows]

        oceans = {}
        idx = 0
        # Hardcoded structure of the 37-tile grid
        # Row sizes: 4, 5, 6, 7, 6, 5, 4
        # Lands per row: 0, 3, 4, 5, 4, 3, 0
        row_sizes = [4, 5, 6, 7, 6, 5, 4]
        lands_per = [0, 3, 4, 5, 4, 3, 0]

        for r_idx, size in enumerate(row_sizes):
            cy = y_map[r_idx]

            # Logic to place oceans relative to land anchors
            if r_idx == 0:
                # Top row (pure ocean), align with row 1 lands
                for t in land_rows[1]:  # land_rows[1] is the middle row (5 hexes)
                    # Note: Original code logic used land_rows[1] for top row projection?
                    # Re-verifying original logic:
                    # Original: "if r_idx == 0: for t in land_rows[1]:"
                    # land_rows index 0 = 3 hexes, index 1 = 4 hexes.
                    # This logic seems to project based on the wider row below it.
                    # We keep EXACT original logic.
                    oceans[idx] = (t["center"][0], cy)
                    idx += 1
            elif r_idx == 6:
                # Bottom row
                for t in land_rows[3]:  # Symmetry
                    oceans[idx] = (t["center"][0], cy)
                    idx += 1
            else:
                # Middle rows: Ocean Left, Lands, Ocean Right
                li = r_idx - 1
                oceans[idx] = (lx[li] - dx, cy)
                idx += 1

                # Skip indices for land tiles
                idx += lands_per[r_idx]

                oceans[idx] = (rx[li] + dx, cy)
                idx += 1

        return oceans, dx, dy

    @staticmethod
    def get_dist(p1, p2):
        return np.hypot(p1[0] - p2[0], p1[1] - p2[1])
