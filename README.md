# 🤖 Autonomous Rescue Robot — Navigation & Vision System

> **MSc Intelligent Robotics** · University of York · 2024  
> Autonomous ground robot for search-and-rescue in maze/disaster environments

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Arduino](https://img.shields.io/badge/Arduino-C++-00979D?logo=arduino&logoColor=white)](https://www.arduino.cc/)
[![YOLOv5](https://img.shields.io/badge/YOLOv5-Object%20Detection-00FFFF)](https://github.com/ultralytics/yolov5)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?logo=opencv)](https://opencv.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

This repository contains my contributions to a group MSc Robotics project: an **autonomous rescue robot** that navigates a maze, detects victims and obstacles using computer vision, and retrieves a target ("Mr. York") in simulated disaster scenarios.

**My responsibilities covered the core software stack:**
- Multi-board serial communication architecture (3 Arduinos ↔ Raspberry Pi)
- IR sensor-based obstacle avoidance with 360° environmental awareness
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
     │  (4x IR)    │    │          │    │  (4 Mecanum)  │
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

### IR Sensor Obstacle Avoidance
- 4 IR sensors via I2C multiplexer (TCA9548A) providing 360° environmental awareness
- Distance calculated using raw register data: `Distance = (high × 16 + low) / (16 × 2^shift)`
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
│   │   └── ir_sensor.ino              # I2C multiplexed IR sensor readings
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

## Getting Started

### Prerequisites
- Python 3.8+
- Arduino IDE
- USB camera
- 3× Arduino boards connected via USB serial

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/rescue-robot.git
cd rescue-robot

# Install Python dependencies
pip install -r requirements.txt
```

### Upload Arduino Firmware

1. Open `arduino/ir_sensor/ir_sensor.ino` in Arduino IDE → upload to **sensor Arduino**
2. Open `arduino/motor_control/motor_control.ino` → upload to **both motor Arduinos**

### Train the Object Detection Model

```bash
# Prepare dataset in dataset/{train,val,test}/{images,labels}
chmod +x yolov5_config/train_model.sh
./yolov5_config/train_model.sh
```

### Run the Robot

```bash
# Option 1: Obstacle avoidance only (no camera)
python python/robot_controller.py

# Option 2: Object detection only (camera feed)
python python/detect_objects.py

# Option 3: Full autonomous mode
python python/integrated_controller.py
```

---

## Results

| Metric | Value |
|--------|-------|
| Object detection mAP | **86%** |
| Detection classes | Mr. York, Car, Blocks |
| Sensor coverage | 360° (4× IR sensors) |
| Movement | Omnidirectional (Mecanum) |
| Control architecture | 3 Arduinos + Raspberry Pi |

---

## Tech Stack

| Category | Technologies |
|----------|-------------|
| Languages | Python, C++ (Arduino) |
| Computer Vision | YOLOv5, OpenCV, CVAT |
| Hardware | Arduino Nano 33 BLE, Raspberry Pi 4, Mecanum wheels |
| Communication | UART serial, I2C (multiplexed) |
| Sensors | GP2Y0E02B IR distance sensors, USB camera |
| Tools | PySerial, PyTorch, Git |

---

## Context

This was part of a 4-person MSc group project. The broader system also included a Tello drone for aerial scanning, LiDAR-based SLAM mapping, A* path planning, and a 4-jaw gripper — developed by teammates. This repo contains **my individual contributions**: the communication architecture, motor control, sensor integration, and the full YOLOv5 pipeline.

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

- **Supervisors**: Dr. Mark Post, Dr. Peter Ellison — University of York
- **Teammates**: Ruike Chen, Jiarui Liu, Dudekula Yaseen Basha
- [Ultralytics YOLOv5](https://github.com/ultralytics/yolov5)
