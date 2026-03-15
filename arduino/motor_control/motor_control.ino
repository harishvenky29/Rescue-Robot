/*
 * Autonomous Rescue Robot - Motor Control Module
 * Author: Harish Venkatesan Muthukumaran Rajamani
 * University of York - MSc Robotics Project
 * 
 * Description:
 *   Controls two Mecanum wheels (one side of the robot) via serial commands.
 *   Uses encoder feedback for distance/revolution tracking.
 *   Upload this sketch to BOTH Arduino motor controllers:
 *     - Arduino 1 (COM7): Front-left & Front-right motors
 *     - Arduino 2 (COM5): Rear-left & Rear-right motors
 * 
 * Serial Commands:
 *   'w' - Move forward
 *   's' - Move backward
 *   'a' - Turn left
 *   'd' - Turn right
 *   'q' - Strafe left
 *   'e' - Strafe right (or stop, depending on config)
 *   'x' - Stop all motors
 * 
 * Hardware:
 *   - 2x DC Motors with Mecanum wheels
 *   - Motor driver (e.g., L298N or similar H-bridge)
 *   - 2x Rotary encoders
 */

// ===================== Pin Definitions =====================
// Motor A (e.g., Left wheel)
#define MOTOR_A_PWM     5     // PWM pin for Motor A speed
#define MOTOR_A_DIR     4     // Direction pin for Motor A
#define ENCODER_A_PIN   2     // Encoder A interrupt pin

// Motor B (e.g., Right wheel)
#define MOTOR_B_PWM     6     // PWM pin for Motor B speed
#define MOTOR_B_DIR     7     // Direction pin for Motor B
#define ENCODER_B_PIN   3     // Encoder B interrupt pin

// ===================== Constants =====================
#define BAUD_RATE       9600
#define DEFAULT_SPEED   127   // 50% duty cycle (0-255)
#define TURN_SPEED      100   // Reduced speed for turning
#define PULSES_PER_REV  360   // Encoder pulses per wheel revolution
#define PRINT_INTERVAL  1000  // Encoder status print interval (ms)

// Direction constants
#define CW   1   // Clockwise
#define CCW  0   // Counter-clockwise

// ===================== Variables =====================
volatile long encoderA_count = 0;   // Encoder A pulse count
volatile long encoderB_count = 0;   // Encoder B pulse count
int motorA_direction = CW;          // Current direction of Motor A
int motorB_direction = CCW;         // Current direction of Motor B
unsigned long lastPrintTime = 0;    // Timer for encoder status printing
char currentCommand = 'x';         // Current movement command

// ===================== Motor Control Functions =====================

/**
 * Set the direction of a specific motor
 * @param motor: 'A' or 'B'
 * @param direction: CW or CCW
 */
void motorSetDir(char motor, int direction) {
  if (motor == 'A') {
    motorA_direction = direction;
    digitalWrite(MOTOR_A_DIR, direction);
  } else if (motor == 'B') {
    motorB_direction = direction;
    digitalWrite(MOTOR_B_DIR, direction);
  }
}

/**
 * Set the speed (PWM) of a specific motor
 * @param motor: 'A' or 'B'
 * @param speed: PWM value (0-255)
 */
void motorSetSpeed(char motor, int speed) {
  if (motor == 'A') {
    analogWrite(MOTOR_A_PWM, speed);
  } else if (motor == 'B') {
    analogWrite(MOTOR_B_PWM, speed);
  }
}

/**
 * Move the robot forward at 50% speed
 * Motor A: CW, Motor B: CCW (for Mecanum wheel configuration)
 */
void moveForward() {
  motorSetDir('A', CW);
  motorSetDir('B', CCW);
  motorSetSpeed('A', DEFAULT_SPEED);
  motorSetSpeed('B', DEFAULT_SPEED);
  Serial.println("CMD: Forward");
}

/**
 * Move the robot backward at 50% speed
 * Motor A: CCW, Motor B: CW
 */
void moveBackward() {
  motorSetDir('A', CCW);
  motorSetDir('B', CW);
  motorSetSpeed('A', DEFAULT_SPEED);
  motorSetSpeed('B', DEFAULT_SPEED);
  Serial.println("CMD: Backward");
}

/**
 * Turn the robot left
 * Both motors rotate CCW
 */
void turnLeft() {
  motorSetDir('A', CCW);
  motorSetDir('B', CCW);
  motorSetSpeed('A', TURN_SPEED);
  motorSetSpeed('B', TURN_SPEED);
  Serial.println("CMD: Turn Left");
}

/**
 * Turn the robot right
 * Both motors rotate CW
 */
void turnRight() {
  motorSetDir('A', CW);
  motorSetDir('B', CW);
  motorSetSpeed('A', TURN_SPEED);
  motorSetSpeed('B', TURN_SPEED);
  Serial.println("CMD: Turn Right");
}

/**
 * Strafe left (Mecanum wheel lateral movement)
 */
void strafeLeft() {
  motorSetDir('A', CCW);
  motorSetDir('B', CW);
  motorSetSpeed('A', DEFAULT_SPEED);
  motorSetSpeed('B', DEFAULT_SPEED);
  Serial.println("CMD: Strafe Left");
}

/**
 * Strafe right (Mecanum wheel lateral movement)
 */
void strafeRight() {
  motorSetDir('A', CW);
  motorSetDir('B', CCW);
  motorSetSpeed('A', DEFAULT_SPEED);
  motorSetSpeed('B', DEFAULT_SPEED);
  Serial.println("CMD: Strafe Right");
}

/**
 * Stop both motors
 */
void stopMotors() {
  motorSetSpeed('A', 0);
  motorSetSpeed('B', 0);
  Serial.println("CMD: Stop");
}

// ===================== Encoder ISR Functions =====================

/**
 * Interrupt Service Routine for Encoder A
 * Increments or decrements based on motor direction
 */
void ENCA_ISR() {
  if (motorA_direction == CW) {
    encoderA_count++;
  } else {
    encoderA_count--;
  }
}

/**
 * Interrupt Service Routine for Encoder B
 * Increments or decrements based on motor direction
 */
void ENCB_ISR() {
  if (motorB_direction == CW) {
    encoderB_count++;
  } else {
    encoderB_count--;
  }
}

/**
 * Get the number of revolutions from encoder count
 */
float getRevolutions(long pulseCount) {
  return (float)abs(pulseCount) / PULSES_PER_REV;
}

// ===================== Setup =====================
void setup() {
  Serial.begin(BAUD_RATE);

  // Motor pins
  pinMode(MOTOR_A_PWM, OUTPUT);
  pinMode(MOTOR_A_DIR, OUTPUT);
  pinMode(MOTOR_B_PWM, OUTPUT);
  pinMode(MOTOR_B_DIR, OUTPUT);

  // Encoder pins with interrupts
  pinMode(ENCODER_A_PIN, INPUT_PULLUP);
  pinMode(ENCODER_B_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENCODER_A_PIN), ENCA_ISR, RISING);
  attachInterrupt(digitalPinToInterrupt(ENCODER_B_PIN), ENCB_ISR, RISING);

  // Initialize motors to stopped state
  stopMotors();

  Serial.println("=== Rescue Robot Motor Control ===");
  Serial.println("Commands: w=fwd, s=back, a=left, d=right, q=strafe_L, e=strafe_R, x=stop");
  Serial.println("Motor controller ready.");
  Serial.println("---------------------------------");
}

// ===================== Main Loop =====================
void loop() {
  // Check for serial input commands
  if (Serial.available() > 0) {
    char command = Serial.read();

    // Only process if command has changed
    if (command != currentCommand) {
      currentCommand = command;

      switch (command) {
        case 'w':
          moveForward();
          break;
        case 's':
          moveBackward();
          break;
        case 'a':
          turnLeft();
          break;
        case 'd':
          turnRight();
          break;
        case 'q':
          strafeLeft();
          break;
        case 'e':
          strafeRight();
          break;
        case 'x':
          stopMotors();
          break;
        default:
          Serial.print("Unknown command: ");
          Serial.println(command);
          break;
      }
    }
  }

  // Periodically print encoder status for debugging
  unsigned long currentTime = millis();
  if (currentTime - lastPrintTime >= PRINT_INTERVAL) {
    lastPrintTime = currentTime;

    Serial.print("ENC_A: ");
    Serial.print(encoderA_count);
    Serial.print(" pulses (");
    Serial.print(getRevolutions(encoderA_count), 2);
    Serial.print(" rev) | ENC_B: ");
    Serial.print(encoderB_count);
    Serial.print(" pulses (");
    Serial.print(getRevolutions(encoderB_count), 2);
    Serial.println(" rev)");
  }
}
