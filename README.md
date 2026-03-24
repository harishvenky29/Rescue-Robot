# 🤖 Autonomous Rescue Robot — Navigation & Vision System

> **MSc Intelligent Robotics** · University of York · 2024  
> Autonomous ground robot for search-and-rescue in maze/disaster environments

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Arduino](https://img.shields.io/badge/Arduino-C++-00979D?logo=arduino&logoColor=white)](https://www.arduino.cc/)
[![YOLOv5](https://img.shields.io/badge/YOLOv5-Object%20Detection-00FFFF)](https://github.com/ultralytics/yolov5)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?logo=opencv)](https://opencv.org/)
[![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-red.svg)](LICENSE)


---

## Overview

An **autonomous rescue robot** built as part of my MSc Robotics degree, designed to navigate a maze, detect victims and obstacles using computer vision, and retrieve a target ("Mr. York") in simulated disaster scenarios.

**This project covers the full software stack:**
- Multi-board serial communication architecture (3 Arduinos ↔ Raspberry Pi)
- IR & Ultrasonic sensor-based obstacle avoidance with 360° environmental awareness
- Motor control for Mecanum omnidirectional wheels
- Custom YOLOv5 object detection — data pipeline, training, and real-time deployment

The full system achieved **86% mAP** on custom object detection and demonstrated reliable autonomous navigation in confined maze environments.

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Raspberry Pi (Central Controller)   │
│                                                       │
│   ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│   │  Obstacle     │  │   YOLOv5     │  │  Decision  │ │
│   │  Avoidance    │──│  Detection   │──│  Engine    │ │
│   └──────┬───────┘  └──────┬───────┘  └─────┬─────┘ │
│          │                 │                 │        │
└──────────┼─────────────────┼─────────────────┼────────┘
           │ Serial          │ Camera          │ Serial
           │ (COM8)          │ (USB)           │ (COM7/COM5)
     ┌─────┴──────┐    ┌────┴─────┐    ┌──────┴───────┐
     │  Arduino    │    │  USB     │    │  2x Arduino   │
     │  Sensor     │    │  Camera  │    │  Motor Ctrl   │
     │(IR + Ultra) │    │          │    │  (4 Mecanum)  │
     └────────────┘    └──────────┘    └───────────────┘
```

---

## Key Features

### Serial Communication & Synchronization
- Designed a **multi-Arduino communication protocol** over UART, coordinating 3 microcontrollers via a central Python controller
- Solved half-duplex limitations through sequential polling — alternating sensor reads and motor writes to prevent data loss
- Both motor Arduinos receive commands near-simultaneously for synchronized wheel control

### Motor Control (Mecanum Wheels)
- **Omnidirectional movement**: forward, backward, strafing, diagonal, and in-place rotation
- Encoder-based feedback for real-time distance and revolution tracking
- Distributed control: each Arduino manages one side of the robot (front/rear), reducing processing bottleneck

### IR & Ultrasonic Sensor Obstacle Avoidance
- 4 IR sensors via I2C multiplexer (TCA9548A) providing 360° environmental awareness
- Ultrasonic sensors for complementary distance measurement and cross-validation
- IR distance calculated using raw register data: `Distance = (high × 16 + low) / (16 × 2^shift)`
- Reactive navigation: turns toward the side with more clearance when obstacles are detected

### YOLOv5 Custom Object Detection
- End-to-end ML pipeline: data collection → CVAT annotation → training → real-time deployment
- Trained on 3 custom classes: **Mr. York** (victim), **Car** (obstacle), **Blocks** (debris)
- Achieved **86% mAP** with reliable detection under varying lighting conditions
- Integrated with motor control for vision-guided victim approach behaviour

---

## Project Structure

```
├── arduino/
│   ├── ir_sensor/
│   │   └── ir_sensor.ino              # I2C multiplexed IR & Ultrasonic sensor readings
│   └── motor_control/
│       └── motor_control.ino          # Mecanum wheel control + encoder ISR
│
├── python/
│   ├── robot_controller.py            # Serial hub: sensors + motors + obstacle avoidance
│   ├── detect_objects.py              # Standalone YOLOv5 real-time detection
│   └── integrated_controller.py       # Full autonomous mode (state machine)
│
├── yolov5_config/
│   ├── custom_data.yaml               # Dataset config (3 classes)
│   └── train_model.sh                 # End-to-end training pipeline
│
├── docs/
│   └── architecture.md                # Detailed system design notes
│
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```


---

## Results

| Metric | Value |
|--------|-------|
| Object detection mAP | **86%** |
| Detection classes | Mr. York, Car, Blocks |
| Sensor coverage | 360° (IR + Ultrasonic) |
| Movement | Omnidirectional (Mecanum) |
| Control architecture | 3 Arduinos + Raspberry Pi |

### YOLOv5 Detection Output

| Victim Detection (Mr. York) | Obstacle Detection (Blocks) |
|:--:|:--:|
| ![Mr. York Detection](docs/images/blocks_detection.png) | ![Blocks Detection](docs/images/victim_detection.png) |

|https://www.youtube.com/watch?v=4F5axwGFdGk |

> Real-time inference detecting victims (Mr. York — 83% confidence) and obstacles (Blocks — up to 87% confidence) in the maze environment.

---

## Tech Stack

| Category | Technologies |
|----------|-------------|
| Languages | Python, C++ (Arduino) |
| Computer Vision | YOLOv5, OpenCV, CVAT |
| Hardware | Arduino Nano 33 BLE, Raspberry Pi 4, Mecanum wheels |
| Communication | UART serial, I2C (multiplexed) |
| Sensors | GP2Y0E02B IR distance sensors, HC-SR04 Ultrasonic sensors, USB camera |
| Tools | PySerial, PyTorch, Git |


---

## License

This project is proprietary. All rights reserved — see [LICENSE](LICENSE) for details.

---
