import argparse
import sys
from pathlib import Path

# Import your local modules
from . import config
from .processing.board_processor import BoardProcessor
from .outputs.json_writer import JsonWriter
from .outputs.visualizer import Visualizer

def parse_args():
    parser = argparse.ArgumentParser(
        description="Catan Board Detection using YOLOv8 Segmentation"
    )
    parser.add_argument(
        "--image",
        type=str,
        required=True,
        help="Path to input image of Catan board",
    )
    return parser.parse_args()

def main():
    # 1. Parse Arguments
    args = parse_args()
    input_path = Path(args.image)

    # Simple check to ensure file exists before crashing later
    if not input_path.exists():
        print(f"❌ Error: Image not found at {input_path}")
        sys.exit(1)

    # 2. Setup
    print(f"Loading model from: {config.MODEL_PATH}")
    processor = BoardProcessor(config.MODEL_PATH)
    visualizer = Visualizer(config.VIZ_DIR)
    config.JSON_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Run Processing
    # Note: We use .process_image() instead of .run() to match the refactored class
    print(f"Processing image: {input_path}")
    board, yolo_results, robber_id = processor.process_image(input_path)

    # 4. Export Data (JSON)
    output_json = config.JSON_DIR / "catan_map.json"
    JsonWriter.save(board, robber_id, output_json)

    # 5. Export Visuals
    # Save full board overview (all detections in one image)
    visualizer.save_board_overview(processor.parser.model, input_path)

    # Save per-class group images (Roads only, Hexes only, etc.)
    visualizer.save_yolo_groups(processor.parser.model, input_path)
    
    # Save the high-detail geometric debug map
    visualizer.save_debug_images(
        input_path, 
        board, 
        processor.dx, 
        processor.dy, 
        yolo_results
    )

    print(f"✅ Process Complete.")
    print(f"   JSON Saved to: {output_json}")
    print(f"   Visuals Saved to: {config.VIZ_DIR}")

if __name__ == "__main__":
    main()