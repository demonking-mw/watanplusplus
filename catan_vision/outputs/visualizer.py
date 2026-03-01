import os
import cv2
import config


class Visualizer:
    def __init__(self, viz_dir):
        self.viz_dir = viz_dir
        os.makedirs(self.viz_dir, exist_ok=True)

    def save_debug_images(self, img_path, board, dx, dy, yolo_results):
        # 1. Save Standard YOLO Group Visuals
        for g_name, ids in config.CLASS_GROUPS.items():
            # Filter boxes by class ID
            # Note: Ultralytics 'save' saves the whole image with all boxes.
            # To save specific classes we need to filter or re-predict.
            # The original code did a re-predict call:
            # res = model(..., classes=ids)
            # We will replicate that behavior in main or pass the model here?
            # To keep it simple and stateless, we usually just assume
            # the user wants the raw yolo debug.
            # BUT, the original code ran `model` AGAIN for specific classes.
            pass

        # 2. Save High-Detail Debug Image (Grid Overlay)
        dbg_img = cv2.imread(str(img_path))
        hw, hh = int(dx * 0.5), int(dy * 0.5)

        for tid, (cx, cy) in board.centers.items():
            cx, cy = int(cx), int(cy)
            is_land = config.TILE_MASK[tid]
            is_port = board.tiles[tid][1] == config.PORT_FLAG

            color = (
                (0, 200, 0)
                if is_land
                else ((0, 165, 255) if is_port else (255, 200, 0))
            )

            if is_land:
                cv2.circle(dbg_img, (cx, cy), 6, color, -1)
            else:
                cv2.rectangle(dbg_img, (cx - hw, cy - hh), (cx + hw, cy + hh), color, 2)

            label = f"{tid}" + (
                f" {config.PORT_NAMES.get(board.tiles[tid][0], '')}" if is_port else ""
            )
            cv2.putText(
                dbg_img,
                label,
                (cx - 10, cy - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1,
            )

        cv2.imwrite(os.path.join(self.viz_dir, "ocean_tiles_debug.jpg"), dbg_img)

    def save_yolo_groups(self, model, img_path):
        # Replicates the original 'save group visuals' logic
        for g_name, ids in config.CLASS_GROUPS.items():
            res = model(
                img_path, classes=ids, conf=config.CONF_THRESHOLD, verbose=False
            )[0]
            res.save(os.path.join(self.viz_dir, f"{g_name}_only.jpg"))
