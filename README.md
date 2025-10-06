# ⚠️ Educational / Research Use Only

**THIS PROJECT IS FOR EDUCATIONAL & RESEARCH PURPOSES ONLY.**  
Do **not** use this software to gain unfair advantage in online games or to violate game Terms of Service. The authors are not responsible for any consequences (account bans, legal claims, or other damages) resulting from misuse.

If youʼre interested in building vision/ML systems for legitimate purposes (accessibility tools, research, security testing with explicit permission), check the links below.

# 🧠 YoloV12 AI Aimbot - Lunar LITE
I added a GUI to tweak the below configurations, and implemented a serial command so you can integrate it with a microcontroller (ESP32 is a great model)

---

## ❓ What Is an AI Aimbot?

Lunar uses screen capture + YOLO object detection to locate enemies in real-time.

> It doesn’t touch memory or inject code — think of it as a robot that watches your screen and gives you precise X,Y coordinates of targets.
 Preconfigured for **Fortnite** — some sensitivity tuning may be needed for other games.

**Summary**
🎯 Aiming and movement parameters
Variable	Purpose	Effect / Notes
xy_sens |	Legacy sensitivity constant	
targeting_sens | replaced by targeting_scale.
xy_scale |General scaling constant.  legacy.
targeting_scale |	Multiplier controlling how far the crosshair moves per detected pixel offset.	Higher values make the crosshair move faster/aggressively toward the target. Default 0.4 (in JSON) but overwritten to 10.0 in aimbot.py defaults
pixel_increment |	Minimum step size per frame when moving the crosshair.	Prevents zero-movement “microsteps.” Larger = coarser movement, smaller = smoother (but more serial commands for an ESP32).

🧠 Model detection parameters
aim_height |	Vertical aiming offset (divisor).	Adjusts where within the bounding box the crosshair aims (e.g., head vs torso). Larger number → higher aim point (closer to top).
confidence |	Minimum YOLO detection confidence.	Lower value detects more objects but increases false positives. Typical range 0.25–0.6.
iou	| Intersection-over-Union threshold for overlapping boxes.

🖱️ Input timing and control
mouse_delay |	Delay between incremental mouse movements (seconds).	Higher = smoother but slower. 0.0009 in code defaults; 0.0 in your JSON = fastest possible.
use_trigger_bot	| Automatically fires when target is locked. If true, script calls left_click() when crosshair overlaps target; false disables auto-shoot.
debug_mode |	Verbose console output.	If true, prints every movement, reload, and left-click to console. Useful for testing but slows down loop.

🔌 Hardware / Serial communication
serial_port	Serial port used to send movement/click commands.	Must match your ESP32 or microcontroller COM port. Example: "COM2" You can change the port to any available one.
serial_baudrate	Communication speed in bits per second.	Must match firmware (ESP32 side). Default 115200.
serial_timeout	Seconds before serial read/write timeout.	Typically 1 is fine; not critical unless reading responses.

---

## 🔧 YOLOv12 Support

Lunar LITE works with:
- [YOLOv8](https://github.com/ultralytics/ultralytics)
- [YOLOv10](https://github.com/ultralytics/ultralytics)
- [YOLOv12](https://github.com/ultralytics/ultralytics)

---

![Lunar Lite Banner](https://github.com/user-attachments/assets/05864acf-cdd1-484f-be79-fa4a9643e8c2)
![Thumbnail](https://github.com/user-attachments/assets/afa30dd2-8168-4c64-999e-bedb0bef4dec)

---




<details>
<summary>📦 <strong>Installation</strong></summary>

1. Install [Python 3.10.5](https://www.python.org/downloads/release/python-3105/)
2. Install **CUDA Toolkit** 11.8, 12.4, or 12.6 (**12.6 recommended**)
3. Navigate to the root folder and run:
    ```
    install_requirements.bat
    ```
4. Launch with:
    ```
    start.bat
    ```

</details>

---

<details>
<summary>⚙️ <strong>Usage / Troubleshooting</strong></summary>

### If you get `CUDA IS UNAVAILABLE` error:
1. Make sure your installed CUDA version matches.
2. Visit [pytorch.org](https://pytorch.org/get-started/locally/) and install the right build.

Command for CUDA 12.6:
```
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

---

### If the console closes instantly:
```
python lunar.py
```

---

### To configure sensitivity:
```
python lunar.py setup
```

---

### To collect training images:
```
python lunar.py collect_data
```

</details>

---


