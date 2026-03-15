"""
Autonomous Rescue Robot - YOLOv5 Real-Time Object Detection
Author: Harish Venkatesan Muthukumaran Rajamani
University of York - MSc Robotics Project

Description:
    Deploys the trained YOLOv5 model on the rescue robot for real-time
    object detection using the robot's camera. Detects objects such as
    victims (Mr. York), cars, and blocks in the rescue environment.

    This script captures frames from the robot's camera, runs YOLOv5
    inference, and returns detected objects with their bounding boxes
    and confidence scores.

Requirements:
    pip install torch torchvision opencv-python
"""

import torch
import cv2
import sys
import time
import logging
import numpy as np
from pathlib import Path

# ===================== Configuration =====================
MODEL_PATH = 'runs/rescue_robot/train_run/weights/best.pt'  # Path to trained model
CONFIDENCE_THRESHOLD = 0.5    # Minimum confidence for detection
IOU_THRESHOLD = 0.45          # IoU threshold for NMS
CAMERA_INDEX = 0              # Camera device index
FRAME_WIDTH = 640             # Camera frame width
FRAME_HEIGHT = 480            # Camera frame height

# Class names (must match custom_data.yaml)
CLASS_NAMES = ['Mr.York', 'Car', 'Blocks']

# Colors for bounding boxes (BGR format)
CLASS_COLORS = {
    'Mr.York': (0, 0, 255),     # Red - high priority (victim)
    'Car': (0, 255, 0),          # Green - obstacle
    'Blocks': (255, 165, 0)      # Orange - debris
}

# ===================== Logging Setup =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# ===================== Model Loading =====================
def load_model(model_path):
    """
    Load the trained YOLOv5 model.
    
    Args:
        model_path: Path to the trained .pt weights file
    
    Returns:
        YOLOv5 model object
    """
    try:
        logger.info(f"Loading YOLOv5 model from: {model_path}")
        model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)
        model.conf = CONFIDENCE_THRESHOLD
        model.iou = IOU_THRESHOLD
        logger.info("Model loaded successfully!")
        return model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        sys.exit(1)


# ===================== Detection Functions =====================
def detect_objects(model, frame):
    """
    Run YOLOv5 inference on a single frame.
    
    Args:
        model: Loaded YOLOv5 model
        frame: OpenCV image (BGR numpy array)
    
    Returns:
        List of detections, each containing:
        {class_name, confidence, bbox: (x1, y1, x2, y2)}
    """
    results = model(frame)
    detections = []
    
    # Parse results
    for *box, conf, cls in results.xyxy[0].cpu().numpy():
        x1, y1, x2, y2 = map(int, box)
        class_id = int(cls)
        class_name = CLASS_NAMES[class_id] if class_id < len(CLASS_NAMES) else f"class_{class_id}"
        confidence = float(conf)
        
        detections.append({
            'class_name': class_name,
            'confidence': confidence,
            'bbox': (x1, y1, x2, y2)
        })
    
    return detections


def draw_detections(frame, detections):
    """
    Draw bounding boxes and labels on the frame.
    
    Args:
        frame: OpenCV image to draw on
        detections: List of detection dictionaries
    
    Returns:
        Annotated frame
    """
    annotated = frame.copy()
    
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        class_name = det['class_name']
        confidence = det['confidence']
        color = CLASS_COLORS.get(class_name, (255, 255, 255))
        
        # Draw bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        
        # Draw label background
        label = f"{class_name}: {confidence:.2f}"
        label_size, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        y1_label = max(y1 - 10, label_size[1])
        cv2.rectangle(annotated, 
                      (x1, y1_label - label_size[1] - 5),
                      (x1 + label_size[0], y1_label + baseline - 5),
                      color, cv2.FILLED)
        
        # Draw label text
        cv2.putText(annotated, label, (x1, y1_label - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return annotated


def get_detection_summary(detections):
    """
    Generate a summary of detected objects for the robot controller.
    
    Args:
        detections: List of detection dictionaries
    
    Returns:
        Dictionary with object counts and closest object info
    """
    summary = {
        'total_objects': len(detections),
        'victims_found': 0,
        'obstacles': [],
        'victim_location': None
    }
    
    for det in detections:
        if det['class_name'] == 'Mr.York':
            summary['victims_found'] += 1
            # Calculate center of bounding box for navigation
            x1, y1, x2, y2 = det['bbox']
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            bbox_area = (x2 - x1) * (y2 - y1)
            summary['victim_location'] = {
                'center': (center_x, center_y),
                'area': bbox_area,
                'confidence': det['confidence']
            }
        else:
            summary['obstacles'].append({
                'type': det['class_name'],
                'bbox': det['bbox']
            })
    
    return summary


# ===================== Camera Functions =====================
def init_camera(camera_index=CAMERA_INDEX):
    """
    Initialize the robot's camera.
    
    Args:
        camera_index: Camera device index
    
    Returns:
        OpenCV VideoCapture object
    """
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    if not cap.isOpened():
        logger.error("Failed to open camera!")
        return None
    
    logger.info(f"Camera initialized ({FRAME_WIDTH}x{FRAME_HEIGHT})")
    return cap


# ===================== Main Detection Loop =====================
def main():
    """
    Main real-time detection loop for the rescue robot.
    
    Captures frames from the camera, runs YOLOv5 detection,
    displays annotated results, and logs detection summaries.
    """
    logger.info("=" * 50)
    logger.info("Rescue Robot - YOLOv5 Object Detection")
    logger.info("=" * 50)

    # Load model
    model = load_model(MODEL_PATH)

    # Initialize camera
    cap = init_camera()
    if cap is None:
        sys.exit(1)

    logger.info("Starting real-time detection... (Press 'q' to quit)")
    logger.info("-" * 50)

    frame_count = 0
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to capture frame. Retrying...")
                continue

            frame_count += 1

            # Run detection
            detections = detect_objects(model, frame)

            # Get summary for robot controller
            summary = get_detection_summary(detections)

            # Log detections
            if detections:
                logger.info(f"Frame {frame_count}: Detected {summary['total_objects']} objects "
                           f"({summary['victims_found']} victims)")
                
                if summary['victim_location']:
                    loc = summary['victim_location']
                    logger.info(f"  VICTIM found at {loc['center']} "
                               f"(confidence: {loc['confidence']:.2f})")

            # Draw annotations and display
            annotated_frame = draw_detections(frame, detections)

            # Add FPS counter
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            cv2.putText(annotated_frame, f"FPS: {fps:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Display
            cv2.imshow('Rescue Robot - Object Detection', annotated_frame)

            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        logger.info("\nDetection stopped by user.")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        elapsed = time.time() - start_time
        logger.info(f"Processed {frame_count} frames in {elapsed:.1f}s "
                    f"(avg {frame_count/elapsed:.1f} FPS)")
        logger.info("Object detection shutdown complete.")


if __name__ == "__main__":
    main()
