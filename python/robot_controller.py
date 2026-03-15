"""
Autonomous Rescue Robot - Central Controller
Author: Harish Venkatesan Muthukumaran Rajamani
University of York - MSc Robotics Project

Description:
    Central control script that manages communication between:
    - Sensor Arduino (COM8): Reads IR sensor distance data
    - Motor Arduino A (COM7): Controls front-left & front-right wheels
    - Motor Arduino B (COM5): Controls rear-left & rear-right wheels

    Implements obstacle avoidance logic using IR sensor data to autonomously
    navigate through environments (e.g., maze/disaster zones).

Requirements:
    pip install pyserial
"""

import serial
import time
import sys
import logging

# ===================== Configuration =====================
SENSOR_PORT = 'COM8'        # Serial port for sensor Arduino
MOTOR_A_PORT = 'COM7'       # Serial port for Motor A Arduino (left motors)
MOTOR_B_PORT = 'COM5'       # Serial port for Motor B Arduino (right motors)
BAUD_RATE = 9600
SERIAL_TIMEOUT = 1          # Serial read timeout in seconds

# Obstacle avoidance thresholds (in cm)
OBSTACLE_THRESHOLD_FRONT = 10   # Minimum safe distance ahead
OBSTACLE_THRESHOLD_SIDE = 5     # Minimum safe distance on sides
OBSTACLE_THRESHOLD_REAR = 5     # Minimum safe distance behind

# Timing
COMMAND_DELAY = 0.25            # Delay between command cycles (seconds)
SENSOR_READ_DELAY = 0.1        # Delay for sensor data polling

# Movement commands
CMD_FORWARD = 'w'
CMD_BACKWARD = 's'
CMD_LEFT = 'a'
CMD_RIGHT = 'd'
CMD_STRAFE_LEFT = 'q'
CMD_STRAFE_RIGHT = 'e'
CMD_STOP = 'x'

# ===================== Logging Setup =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('rescue_robot.log')
    ]
)
logger = logging.getLogger(__name__)


# ===================== Serial Connection Setup =====================
def init_serial(port, baud_rate=BAUD_RATE, timeout=SERIAL_TIMEOUT):
    """
    Initialize a serial connection.
    
    Args:
        port: COM port string
        baud_rate: Communication speed
        timeout: Read timeout in seconds
    
    Returns:
        serial.Serial object or None if connection fails
    """
    try:
        ser = serial.Serial(port, baud_rate, timeout=timeout)
        time.sleep(2)  # Wait for Arduino to reset after serial connection
        logger.info(f"Connected to {port} at {baud_rate} baud")
        return ser
    except serial.SerialException as e:
        logger.error(f"Failed to connect to {port}: {e}")
        return None


# ===================== Sensor Functions =====================
def get_sensor_data(arduino_sensor):
    """
    Request and read sensor data from the sensor Arduino.
    
    The sensor Arduino sends data in CSV format: FRONT,REAR,LEFT,RIGHT
    
    Args:
        arduino_sensor: Serial connection to sensor Arduino
    
    Returns:
        Tuple of (front, rear, left, right) distances in cm, or None on error
    """
    try:
        if arduino_sensor.in_waiting > 0:
            raw_data = arduino_sensor.readline().decode('utf-8').strip()
            
            if raw_data:
                values = raw_data.split(',')
                if len(values) == 4:
                    front = float(values[0])
                    rear = float(values[1])
                    left = float(values[2])
                    right = float(values[3])
                    
                    logger.debug(f"Sensor data - Front: {front:.1f}, Rear: {rear:.1f}, "
                                f"Left: {left:.1f}, Right: {right:.1f}")
                    return (front, rear, left, right)
                else:
                    logger.warning(f"Unexpected sensor data format: {raw_data}")
        
        return None
    
    except (ValueError, UnicodeDecodeError) as e:
        logger.warning(f"Error parsing sensor data: {e}")
        return None
    except serial.SerialException as e:
        logger.error(f"Serial error reading sensor data: {e}")
        return None


# ===================== Motor Control Functions =====================
def send_motor_command(command, arduino_motor_A, arduino_motor_B):
    """
    Send the same movement command to both motor Arduinos simultaneously.
    
    By sending the same command to both Arduinos, both sets of motors receive
    the same instruction at approximately the same time, keeping the robot's
    movement synchronized.
    
    Args:
        command: Single character command (w/s/a/d/q/e/x)
        arduino_motor_A: Serial connection to Motor A Arduino (left/front)
        arduino_motor_B: Serial connection to Motor B Arduino (right/rear)
    """
    try:
        # Send to both Arduinos for synchronized movement
        arduino_motor_A.write(command.encode('utf-8'))
        arduino_motor_B.write(command.encode('utf-8'))
        logger.info(f"Sent command: '{command}' to both motor Arduinos")
    except serial.SerialException as e:
        logger.error(f"Error sending motor command: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending motor command: {e}")


# ===================== Navigation Logic =====================
def obstacle_avoidance(sensor_data, arduino_motor_A, arduino_motor_B):
    """
    Basic obstacle avoidance logic using IR sensor data.
    
    Decision process:
    1. If obstacle detected in front -> turn towards the side with more space
    2. If obstacle on both sides -> move backward
    3. Otherwise -> move forward
    
    Args:
        sensor_data: Tuple of (front, rear, left, right) distances
        arduino_motor_A: Serial connection to Motor A Arduino
        arduino_motor_B: Serial connection to Motor B Arduino
    """
    front, rear, left, right = sensor_data

    if front < OBSTACLE_THRESHOLD_FRONT:
        # Obstacle detected ahead
        logger.info(f"Obstacle ahead ({front:.1f} cm). Deciding turn direction...")
        
        if left > right:
            # More space on the left -> turn left
            logger.info(f"Turning left (left={left:.1f} > right={right:.1f})")
            send_motor_command(CMD_LEFT, arduino_motor_A, arduino_motor_B)
        elif right > left:
            # More space on the right -> turn right
            logger.info(f"Turning right (right={right:.1f} > left={left:.1f})")
            send_motor_command(CMD_RIGHT, arduino_motor_A, arduino_motor_B)
        else:
            # Equal space -> default to left turn
            logger.info("Equal space on both sides, defaulting to left turn")
            send_motor_command(CMD_LEFT, arduino_motor_A, arduino_motor_B)
    
    elif left < OBSTACLE_THRESHOLD_SIDE and right < OBSTACLE_THRESHOLD_SIDE:
        # Obstacles on both sides -> check if we can go forward
        if front >= OBSTACLE_THRESHOLD_FRONT:
            send_motor_command(CMD_FORWARD, arduino_motor_A, arduino_motor_B)
        else:
            # Surrounded -> try backward
            logger.info("Obstacles on multiple sides. Moving backward.")
            send_motor_command(CMD_BACKWARD, arduino_motor_A, arduino_motor_B)
    
    elif left < OBSTACLE_THRESHOLD_SIDE:
        # Obstacle on the left -> strafe right slightly
        logger.info(f"Obstacle on left ({left:.1f} cm). Adjusting right.")
        send_motor_command(CMD_STRAFE_RIGHT, arduino_motor_A, arduino_motor_B)
    
    elif right < OBSTACLE_THRESHOLD_SIDE:
        # Obstacle on the right -> strafe left slightly
        logger.info(f"Obstacle on right ({right:.1f} cm). Adjusting left.")
        send_motor_command(CMD_STRAFE_LEFT, arduino_motor_A, arduino_motor_B)
    
    else:
        # Path is clear -> move forward
        send_motor_command(CMD_FORWARD, arduino_motor_A, arduino_motor_B)


# ===================== Main Control Loop =====================
def main():
    """
    Main control loop for the rescue robot.
    
    Flow:
    1. Initialize serial connections to all three Arduinos
    2. Continuously read sensor data
    3. Process sensor data through obstacle avoidance logic
    4. Send appropriate motor commands
    """
    logger.info("=" * 50)
    logger.info("Autonomous Rescue Robot - Starting Controller")
    logger.info("=" * 50)

    # Initialize serial connections
    logger.info("Initializing serial connections...")
    
    arduino_sensor = init_serial(SENSOR_PORT)
    arduino_motor_A = init_serial(MOTOR_A_PORT)
    arduino_motor_B = init_serial(MOTOR_B_PORT)

    # Verify all connections
    connections = {
        'Sensor Arduino': arduino_sensor,
        'Motor A Arduino': arduino_motor_A,
        'Motor B Arduino': arduino_motor_B
    }
    
    for name, conn in connections.items():
        if conn is None:
            logger.error(f"{name} not connected. Exiting.")
            # Close any open connections
            for c in connections.values():
                if c and c.is_open:
                    c.close()
            sys.exit(1)

    logger.info("All Arduinos connected successfully!")
    logger.info("Starting autonomous navigation...")
    logger.info("-" * 50)

    try:
        while True:
            # Step 1: Request and read sensor data
            sensor_data = get_sensor_data(arduino_sensor)
            
            if sensor_data:
                # Step 2: Process sensor data and send motor commands
                obstacle_avoidance(sensor_data, arduino_motor_A, arduino_motor_B)
            else:
                # No sensor data received - stop for safety
                logger.warning("No sensor data. Stopping motors for safety.")
                send_motor_command(CMD_STOP, arduino_motor_A, arduino_motor_B)
            
            # Step 3: Wait before next cycle
            time.sleep(COMMAND_DELAY)

    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user.")
        send_motor_command(CMD_STOP, arduino_motor_A, arduino_motor_B)
    
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        send_motor_command(CMD_STOP, arduino_motor_A, arduino_motor_B)
    
    finally:
        # Clean up serial connections
        logger.info("Closing serial connections...")
        for name, conn in connections.items():
            if conn and conn.is_open:
                conn.close()
                logger.info(f"{name} disconnected.")
        logger.info("Robot controller shutdown complete.")


if __name__ == "__main__":
    main()
