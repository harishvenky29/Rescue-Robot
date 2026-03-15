# System Architecture — Detailed Notes

## Communication Architecture

The robot uses **3 Arduino microcontrollers** connected to a central **Raspberry Pi** via USB serial:

| Arduino | Port | Role |
|---------|------|------|
| Sensor Arduino | COM8 | Reads 4× IR sensors via I2C multiplexer |
| Motor Arduino A | COM7 | Controls front-left & front-right Mecanum wheels |
| Motor Arduino B | COM5 | Controls rear-left & rear-right Mecanum wheels |

### Why 3 Arduinos?

A single Arduino lacked sufficient I/O pins and processing power to handle 4 IR sensors (I2C), 4 motor drivers (PWM + direction), and 4 encoders (interrupts) simultaneously. Splitting the workload across 3 boards also isolates sensor noise from motor driver interference.

### Half-Duplex Challenge

UART serial is half-duplex per port — you can only send OR receive at any moment. The central controller solves this with a **sequential polling loop**:

```
1. Read sensor data from COM8  (receive)
2. Process obstacle avoidance logic
3. Send motor command to COM7   (send)
4. Send motor command to COM5   (send)
5. Sleep 250ms
6. Repeat
```

Commands to both motor Arduinos are sent back-to-back (near-simultaneously) to keep wheel movements synchronized.

---

## IR Sensor System

**Hardware**: 4× GP2Y0E02B IR distance sensors connected through a TCA9548A I2C multiplexer.

**Distance Formula**:
```
Distance = (high_byte × 16 + low_byte) / (16 × 2^shift)
```

The shift value is read from each sensor's internal shift register (address `0x35`), and the high/low distance bytes come from registers `0x5E` and `0x5F`. The multiplexer selects one sensor at a time by writing a channel bitmask to address `0x70`.

**Measurement cycle**: ~550ms per full sweep of all 4 sensors.

---

## Motor Control

**Mecanum Wheels** allow omnidirectional movement by combining different wheel rotation directions:

| Movement | Motor A | Motor B |
|----------|---------|---------|
| Forward | CW | CCW |
| Backward | CCW | CW |
| Turn Left | CCW | CCW |
| Turn Right | CW | CW |
| Strafe Left | CCW | CW |
| Strafe Right | CW | CCW |

Each motor has a rotary encoder tracked via hardware interrupts. The ISR increments or decrements a pulse counter based on direction, enabling distance measurement (360 pulses per revolution).

---

## YOLOv5 Object Detection Pipeline

### Training Data
- **Collection**: Real-world photos from the maze environment, captured at varying angles, distances, and lighting
- **Annotation**: CVAT (Computer Vision Annotation Tool) with YOLO-format bounding box labels
- **Split**: 70% train / 20% validation / 10% test
- **Classes**: Mr. York (victim), Car (vehicle obstacle), Blocks (debris)

### Model Training
- Base model: `yolov5s.pt` (pretrained on COCO)
- Fine-tuned for 50 epochs, batch size 16, image size 640×640
- Achieved **86% mAP** on validation set

### Deployment
The trained `.pt` model runs on the Raspberry Pi, processing live camera frames through OpenCV. Detections feed into the integrated controller's state machine for vision-guided navigation.

---

## Integrated State Machine

The `integrated_controller.py` combines all subsystems into a state machine:

```
SEARCHING ──────────► OBSTACLE_AVOIDANCE
    │                        │
    │ (victim detected)      │ (clear)
    ▼                        │
VICTIM_FOUND ◄──────────────┘
    │
    │ (centered on target)
    ▼
APPROACHING_VICTIM
    │
    │ (within range)
    ▼
STOPPED (victim reached)
```

Priority order: **Victim detection > Obstacle avoidance > Forward search**
