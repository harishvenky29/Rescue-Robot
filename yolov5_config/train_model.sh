#!/bin/bash
# ============================================================
# Autonomous Rescue Robot - YOLOv5 Training Script
# Author: Harish Venkatesan Muthukumaran Rajamani
# University of York - MSc Robotics Project
# ============================================================

echo "=== Rescue Robot - YOLOv5 Custom Training ==="
echo ""

# -------- Configuration --------
IMG_SIZE=640
BATCH_SIZE=16
EPOCHS=50
DATA_YAML="custom_data.yaml"
WEIGHTS="yolov5s.pt"
PROJECT="runs/rescue_robot"
NAME="train_run"

# -------- Step 1: Clone YOLOv5 (if not already present) --------
if [ ! -d "yolov5" ]; then
    echo "[1/5] Cloning YOLOv5 repository..."
    git clone https://github.com/ultralytics/yolov5.git
    cd yolov5
    pip install -r requirements.txt
    cd ..
else
    echo "[1/5] YOLOv5 already cloned. Skipping."
fi

# -------- Step 2: Verify dataset structure --------
echo "[2/5] Verifying dataset structure..."
REQUIRED_DIRS=("dataset/train/images" "dataset/train/labels" "dataset/val/images" "dataset/val/labels")
ALL_EXIST=true

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "  WARNING: Missing directory: $dir"
        ALL_EXIST=false
    else
        COUNT=$(ls -1 "$dir" | wc -l)
        echo "  OK: $dir ($COUNT files)"
    fi
done

if [ "$ALL_EXIST" = false ]; then
    echo "  Please create missing directories and add data before training."
    echo "  Expected structure:"
    echo "    dataset/"
    echo "    ├── train/"
    echo "    │   ├── images/   (training images)"
    echo "    │   └── labels/   (YOLO format .txt annotations)"
    echo "    ├── val/"
    echo "    │   ├── images/   (validation images)"
    echo "    │   └── labels/   (YOLO format .txt annotations)"
    echo "    └── test/"
    echo "        └── images/   (test images)"
    exit 1
fi

# -------- Step 3: Train the model --------
echo "[3/5] Starting training..."
echo "  Image size: ${IMG_SIZE}"
echo "  Batch size: ${BATCH_SIZE}"
echo "  Epochs: ${EPOCHS}"
echo "  Weights: ${WEIGHTS}"
echo "  Config: ${DATA_YAML}"
echo ""

cd yolov5
python train.py \
    --img $IMG_SIZE \
    --batch $BATCH_SIZE \
    --epochs $EPOCHS \
    --data ../$DATA_YAML \
    --weights $WEIGHTS \
    --project ../$PROJECT \
    --name $NAME

# -------- Step 4: Evaluate the model --------
echo "[4/5] Evaluating model on validation set..."
python val.py \
    --data ../$DATA_YAML \
    --weights ../$PROJECT/$NAME/weights/best.pt \
    --img $IMG_SIZE \
    --task test

# -------- Step 5: Export model --------
echo "[5/5] Exporting trained model..."
python export.py \
    --weights ../$PROJECT/$NAME/weights/best.pt \
    --include torchscript onnx

cd ..

echo ""
echo "=== Training Complete ==="
echo "Best weights saved at: $PROJECT/$NAME/weights/best.pt"
echo "Results and metrics at: $PROJECT/$NAME/"
