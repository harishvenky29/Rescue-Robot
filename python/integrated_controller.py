"""
Autonomous Rescue Robot - Integrated Controller
Author: Harish Venkatesan Muthukumaran Rajamani
University of York - MSc Robotics Project

Description:
    Integrates all robot subsystems into a single autonomous controller:
    - IR sensor-based obstacle avoidance
    - YOLOv5 real-time object detection
    - Motor control via dual Arduino setup
    
    The robot navigates autonomously through environments, avoiding obstacles
    and detecting victims/objects using its trained YOLOv5 model.

Usage:
    python integrated_controller.py

Requirements:
    pip install pyserial torch torchvision opencv-python
"""

import serial
import torch
import cv2
import time
import sys
import logging
import threading
from enum import Enum

# ===================== Configuration =====================
# Serial ports
SENSOR_PORT = 'COM8'
MOTOR_A_PORT = 'COM7'
MOTOR_B_PORT = 'COM5'
BAUD_RATE = 9600

# YOLOv5 model
MODEL_PATH = 'runs/rescue_robot/train_run/weights/best.pt'
CONFIDENCE_THRESHOLD = 0.5
CLASS_NAMES = ['Mr.York', 'Car', 'Blocks']

# Navigation thresholds (cm)
OBSTACLE_FRONT = 10
OBSTACLE_SIDE = 5
VICTIM_APPROACH_DISTANCE = 15

# Timing
CONTROL_LOOP_DELAY = 0.25
CAMERA_INDEX = 0

# Commands
CMD = {
    'forward': 'w',
    'backward': 's',
    'left': 'a',
    'right': 'd',
    'strafe_left': 'q',
    'strafe_right': 'e',
    'stop': 'x'
}

# ===================== Logging =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('rescue_robot_integrated.log')
    ]
)
logger = logging.getLogger(__name__)


# ===================== Robot State =====================
class RobotState(Enum):
    SEARCHING = "searching"
    NAVIGATING = "navigating"
    VICTIM_FOUND = "victim_found"
    APPROACHING_VICTIM = "approaching_victim"
    OBSTACLE_AVOIDANCE = "obstacle_avoidance"
    STOPPED = "stopped"


class RescueRobot:
    """Main robot controller class integrating all subsystems."""

    def __init__(self):
        self.state = RobotState.SEARCHING
        self.sensor_data = None
        self.detections = []
        self.victim_detected = False
        self.running = False

        # Serial connections
        self.arduino_sensor = None
        self.arduino_motor_A = None
        self.arduino_motor_B = None

        # Camera and model
        self.camera = None
        self.model = None

        # Thread-safe data sharing
        self.lock = threading.Lock()

    def init_serial(self, port):
        """Initialize a serial connection."""
        try:
            ser = serial.Serial(port, BAUD_RATE, timeout=1)
            time.sleep(2)
            logger.info(f"Connected to {port}")
            return ser
        except serial.SerialException as e:
            logger.error(f"Failed to connect to {port}: {e}")
            return None

    def init_all_connections(self):
        """Initialize all hardware connections."""
        logger.info("Initializing hardware connections...")

        # Serial connections
        self.arduino_sensor = self.init_serial(SENSOR_PORT)
        self.arduino_motor_A = self.init_serial(MOTOR_A_PORT)
        self.arduino_motor_B = self.init_serial(MOTOR_B_PORT)

        if not all([self.arduino_sensor, self.arduino_motor_A, self.arduino_motor_B]):
            logger.error("Not all Arduinos connected!")
            return False

        # Camera
        self.camera = cv2.VideoCapture(CAMERA_INDEX)
        if not self.camera.isOpened():
            logger.error("Camera not available!")
            return False

        # YOLOv5 model
        try:
            self.model = torch.hub.load('ultralytics/yolov5', 'custom', path=MODEL_PATH)
            self.model.conf = CONFIDENCE_THRESHOLD
            logger.info("YOLOv5 model loaded.")
        except Exception as e:
            logger.error(f"Failed to load YOLOv5 model: {e}")
            return False

        logger.info("All systems initialized!")
        return True

    # ---- Sensor Reading ----
    def read_sensors(self):
        """Read IR sensor data."""
        try:
            if self.arduino_sensor.in_waiting > 0:
                raw = self.arduino_sensor.readline().decode('utf-8').strip()
                values = raw.split(',')
                if len(values) == 4:
                    with self.lock:
                        self.sensor_data = tuple(float(v) for v in values)
                    return self.sensor_data
        except Exception as e:
            logger.warning(f"Sensor read error: {e}")
        return None

    # ---- Motor Control ----
    def send_command(self, command):
        """Send command to both motor Arduinos."""
        try:
            self.arduino_motor_A.write(command.encode('utf-8'))
            self.arduino_motor_B.write(command.encode('utf-8'))
        except Exception as e:
            logger.error(f"Motor command error: {e}")

    # ---- Object Detection ----
    def run_detection(self, frame):
        """Run YOLOv5 detection on a camera frame."""
        results = self.model(frame)
        detections = []

        for *box, conf, cls in results.xyxy[0].cpu().numpy():
            x1, y1, x2, y2 = map(int, box)
            class_id = int(cls)
            class_name = CLASS_NAMES[class_id] if class_id < len(CLASS_NAMES) else "unknown"

            detections.append({
                'class': class_name,
                'confidence': float(conf),
                'bbox': (x1, y1, x2, y2),
                'center_x': (x1 + x2) // 2,
                'area': (x2 - x1) * (y2 - y1)
            })

        with self.lock:
            self.detections = detections
            self.victim_detected = any(d['class'] == 'Mr.York' for d in detections)

        return detections

    # ---- Decision Making ----
    def decide_action(self):
        """
        Core decision-making logic combining sensor data and detections.
        
        Priority:
        1. If victim detected -> approach victim
        2. If obstacle ahead -> avoid obstacle
        3. Otherwise -> search (move forward)
        """
        with self.lock:
            sensors = self.sensor_data
            detections = self.detections
            victim = self.victim_detected

        if sensors is None:
            self.send_command(CMD['stop'])
            self.state = RobotState.STOPPED
            return

        front, rear, left, right = sensors

        # Priority 1: Victim found - navigate towards them
        if victim:
            self.state = RobotState.VICTIM_FOUND
            victim_det = next(d for d in detections if d['class'] == 'Mr.York')
            frame_center = 320  # Assuming 640px wide frame

            if victim_det['center_x'] < frame_center - 50:
                self.send_command(CMD['left'])
                logger.info("VICTIM: Adjusting left to center on victim")
            elif victim_det['center_x'] > frame_center + 50:
                self.send_command(CMD['right'])
                logger.info("VICTIM: Adjusting right to center on victim")
            elif front > VICTIM_APPROACH_DISTANCE:
                self.send_command(CMD['forward'])
                self.state = RobotState.APPROACHING_VICTIM
                logger.info("VICTIM: Moving forward to approach")
            else:
                self.send_command(CMD['stop'])
                logger.info("VICTIM REACHED! Stopping.")
            return

        # Priority 2: Obstacle avoidance
        if front < OBSTACLE_FRONT:
            self.state = RobotState.OBSTACLE_AVOIDANCE
            if left > right:
                self.send_command(CMD['left'])
                logger.info(f"Obstacle ahead ({front:.1f}cm). Turning left.")
            else:
                self.send_command(CMD['right'])
                logger.info(f"Obstacle ahead ({front:.1f}cm). Turning right.")
            return

        if left < OBSTACLE_SIDE:
            self.send_command(CMD['strafe_right'])
            return
        if right < OBSTACLE_SIDE:
            self.send_command(CMD['strafe_left'])
            return

        # Default: Move forward (searching)
        self.state = RobotState.SEARCHING
        self.send_command(CMD['forward'])

    # ---- Main Loop ----
    def run(self):
        """Main autonomous control loop."""
        if not self.init_all_connections():
            logger.error("Initialization failed. Exiting.")
            return

        self.running = True
        logger.info("=" * 50)
        logger.info("AUTONOMOUS RESCUE MODE ACTIVE")
        logger.info("=" * 50)

        try:
            while self.running:
                # Read sensors
                self.read_sensors()

                # Capture and process camera frame
                ret, frame = self.camera.read()
                if ret:
                    self.run_detection(frame)

                    # Display annotated frame (for debugging)
                    for det in self.detections:
                        x1, y1, x2, y2 = det['bbox']
                        color = (0, 0, 255) if det['class'] == 'Mr.York' else (0, 255, 0)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, f"{det['class']} {det['confidence']:.2f}",
                                    (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                    cv2.putText(frame, f"State: {self.state.value}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.imshow('Rescue Robot', frame)

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                # Make navigation decision
                self.decide_action()

                time.sleep(CONTROL_LOOP_DELAY)

        except KeyboardInterrupt:
            logger.info("Shutdown requested.")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown of all systems."""
        self.running = False
        self.send_command(CMD['stop'])

        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()

        for conn in [self.arduino_sensor, self.arduino_motor_A, self.arduino_motor_B]:
            if conn and conn.is_open:
                conn.close()

        logger.info("Robot shutdown complete.")


# ===================== Entry Point =====================
if __name__ == "__main__":
    robot = RescueRobot()
    robot.run()
