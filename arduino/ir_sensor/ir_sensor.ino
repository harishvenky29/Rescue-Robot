/*
 * Autonomous Rescue Robot - IR Sensor Module
 * Author: Harish Venkatesan Muthukumaran Rajamani
 * University of York - MSc Robotics Project
 * 
 * Description:
 *   Reads distance data from 4 IR sensors via I2C bus using a multiplexer.
 *   Calculates distance using the formula: Distance = (high * 16 + low) / (16 * 2^shift)
 *   Sends distance data over Serial to the central controller (Raspberry Pi / PC).
 * 
 * Hardware:
 *   - 4x IR distance sensors (I2C)
 *   - TCA9548A I2C Multiplexer
 *   - Arduino (COM8 - Sensor Arduino)
 */

#include <Wire.h>

// ===================== Configuration =====================
#define NUM_SENSORS     4
#define MUX_ADDRESS     0x70    // TCA9548A I2C multiplexer address
#define SENSOR_ADDRESS  0x80    // IR sensor I2C address (7-bit: 0x40)
#define SHIFT_REGISTER  0x35    // Register address for shift value
#define DIST_HIGH_REG   0x5E    // Register address for distance high byte
#define DIST_LOW_REG    0x5F    // Register address for distance low byte
#define LOOP_DELAY      550     // Delay between measurement cycles (ms)
#define BAUD_RATE       9600

// ===================== Variables =====================
float distance[NUM_SENSORS];    // Calculated distance values for each sensor
uint8_t shift[NUM_SENSORS];     // Shift values from each sensor's shift register
uint8_t distHigh[NUM_SENSORS];  // High byte of distance reading
uint8_t distLow[NUM_SENSORS];   // Low byte of distance reading

// Sensor labels for serial output
const char* sensorLabels[] = {"FRONT", "REAR", "LEFT", "RIGHT"};

// ===================== Functions =====================

/**
 * Select the I2C channel on the TCA9548A multiplexer
 * @param channel: The I2C bus channel to select (0-7)
 */
void selectMuxChannel(uint8_t channel) {
  Wire.beginTransmission(MUX_ADDRESS);
  Wire.write(1 << channel);
  Wire.endTransmission();
}

/**
 * Read a single byte from a specific register of the IR sensor
 * @param reg: Register address to read from
 * @return: The byte value read from the register
 */
uint8_t readSensorRegister(uint8_t reg) {
  Wire.beginTransmission(SENSOR_ADDRESS >> 1);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)(SENSOR_ADDRESS >> 1), (uint8_t)1);
  if (Wire.available()) {
    return Wire.read();
  }
  return 0;
}

/**
 * Read distance from a specific IR sensor
 * @param sensorIndex: Index of the sensor (0-3)
 */
void readSensorDistance(uint8_t sensorIndex) {
  // Select the correct I2C bus for this sensor
  selectMuxChannel(sensorIndex);
  delay(10);  // Allow multiplexer to settle

  // Read shift value from sensor's shift register
  shift[sensorIndex] = readSensorRegister(SHIFT_REGISTER);

  // Read high and low bytes of distance
  distHigh[sensorIndex] = readSensorRegister(DIST_HIGH_REG);
  distLow[sensorIndex] = readSensorRegister(DIST_LOW_REG);

  // Calculate distance using formula: (high * 16 + low) / (16 * 2^shift)
  float rawDistance = (float)(distHigh[sensorIndex] * 16 + distLow[sensorIndex]);
  float divisor = 16.0 * pow(2, shift[sensorIndex]);

  if (divisor != 0) {
    distance[sensorIndex] = rawDistance / divisor;
  } else {
    distance[sensorIndex] = -1;  // Error value
  }
}

// ===================== Setup =====================
void setup() {
  Serial.begin(BAUD_RATE);
  Wire.begin();

  Serial.println("=== Rescue Robot IR Sensor Module ===");
  Serial.println("Initializing sensors...");

  // Verify multiplexer is connected
  Wire.beginTransmission(MUX_ADDRESS);
  if (Wire.endTransmission() == 0) {
    Serial.println("I2C Multiplexer detected.");
  } else {
    Serial.println("ERROR: I2C Multiplexer not found!");
  }

  Serial.println("Sensor module ready.");
  Serial.println("-----------------------------------");
}

// ===================== Main Loop =====================
void loop() {
  // Read distance from all four IR sensors
  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    readSensorDistance(i);
  }

  // Send distance data over Serial in CSV format for the central controller
  // Format: FRONT,REAR,LEFT,RIGHT
  Serial.print(distance[0], 2);  // Front
  Serial.print(",");
  Serial.print(distance[1], 2);  // Rear
  Serial.print(",");
  Serial.print(distance[2], 2);  // Left
  Serial.print(",");
  Serial.println(distance[3], 2);  // Right

  // Also print human-readable format for debugging
  #ifdef DEBUG
  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    Serial.print(sensorLabels[i]);
    Serial.print(": ");
    Serial.print(distance[i], 2);
    Serial.print(" cm  |  ");
  }
  Serial.println();
  #endif

  // Wait before next measurement cycle
  delay(LOOP_DELAY);
}
