from ultralytics import YOLO
import torch
from pathlib import Path

# ---------------- Configuration ----------------
# if error in data_yaml, replace with absolute path of data.yaml file
PROJECT_ROOT = Path(__file__).parent
DATA_YAML = PROJECT_ROOT / "data.yaml"
MODEL_SIZE = "yolov8m-seg.pt"

EPOCHS = 175
IMAGE_SIZE = 640
BATCH_SIZE = 4

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
RUN_NAME = "catan_yolo8m"


# ---------------- Main Training Script ----------------
def main():
    print("=" * 60)
    print("Catan Board Detection - YOLOv8m Segmentation")
    print("=" * 60)

    # Check dataset
    if not Path(DATA_YAML).exists():
        print(f"❌ ERROR: data.yaml not found at {DATA_YAML}")
        return

    # System info
    print(f"\n🔍 Checking system...")
    print(f"PyTorch version: {torch.__version__}")
    print(f"MPS (Metal) available: {torch.backends.mps.is_available()}")
    print(f"Device selected: {DEVICE}")

    # Load YOLOv8m segmentation model
    print(f"\n📦 Loading model {MODEL_SIZE}...")
    model = YOLO(MODEL_SIZE)  # auto-download if not found

    # Start training
    print(f"\n🚀 Starting training...")
    print(f"Dataset: {DATA_YAML}")
    print(f"Epochs: {EPOCHS}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Image size: {IMAGE_SIZE}")
    print(f"Device: {DEVICE}")
    print("-" * 60)

    model.train(
        data=DATA_YAML,
        epochs=EPOCHS,
        imgsz=IMAGE_SIZE,
        batch=BATCH_SIZE,
        device=DEVICE,
        name=RUN_NAME,
        pretrained=True,
        optimizer="auto",
        verbose=True,
        save=True,
        save_period=10,
        val=True,
        plots=True,
        project=str(PROJECT_ROOT / "runs"),
    )

    print("\n" + "=" * 60)
    print("✅ Training Complete!")
    print("=" * 60)

    # Run final validation
    print("\n📊 Running final validation...")
    metrics = model.val()

    print("\n📈 Final Metrics:")
    print(f"mAP50 (Box): {metrics.box.map50:.3f}")
    print(f"mAP50-95 (Box): {metrics.box.map:.3f}")
    if hasattr(metrics, "seg"):
        print(f"mAP50 (Mask): {metrics.seg.map50:.3f}")
        print(f"mAP50-95 (Mask): {metrics.seg.map:.3f}")

    # Model path
    save_dir = Path(model.trainer.save_dir) / "weights"
    best_model = save_dir / "best.pt"
    print(f"\n💾 Model saved to: {best_model}")

    print("\n🎯 To use your model:")
    print(f"   model = YOLO('{best_model}')")
    print("   results = model('catan_board.jpg')")


if __name__ == "__main__":
    main()
