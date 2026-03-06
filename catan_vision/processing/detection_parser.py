from ultralytics import YOLO
from .. import config


class DetectionParser:
    def __init__(self, model_path):
        self.model = YOLO(model_path)

    def parse(self, img_path):
        results = self.model(img_path, conf=config.CONF_THRESHOLD)[0]

        raw = {
            "hex": [],
            "num": [],
            "build": [],
            "road": [],
            "port": [],
            "robber": None,
        }

        # Parsing YOLO detections
        for i, box in enumerate(results.boxes.xyxy):
            cls_id = int(results.boxes.cls[i])
            conf = float(results.boxes.conf[i])
            name = results.names[cls_id]

            cx = int((box[0] + box[2]) // 2)
            cy = int((box[1] + box[3]) // 2)

            if name in ["wood", "brick", "sheep", "wheat", "ore", "desert"]:
                raw["hex"].append({"id": cls_id, "center": (cx, cy), "box": box})
            elif "number" in name or "token" in name:
                # Extracts '5' from 'token_5'
                val = int(name.split("_")[-1])
                raw["num"].append({"val": val, "center": (cx, cy)})
            elif "settlement" in name or "city" in name:
                raw["build"].append({"name": name, "center": (cx, cy)})
            elif "road" in name:
                raw["road"].append({"name": name, "center": (cx, cy)})
            elif name.startswith("port_"):
                raw["port"].append(
                    {
                        "res_id": config.YOLO_TO_PORT.get(cls_id),
                        "center": (cx, cy),
                        "conf": conf,
                    }
                )
            elif name == "robber":
                raw["robber"] = (cx, cy)

        return raw, results  # Return results for visualization reuse
