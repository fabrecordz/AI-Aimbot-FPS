import ctypes
import cv2
import json
import math
import mss
import os
import sys
import time
import torch
import numpy as np
import win32api
from termcolor import colored
from ultralytics import YOLO
import serial

# Auto Screen Resolution
screensize = {
    'X': ctypes.windll.user32.GetSystemMetrics(0),
    'Y': ctypes.windll.user32.GetSystemMetrics(1)
}

screen_res_x = screensize['X']
screen_res_y = screensize['Y']

screen_x = int(screen_res_x / 2)
screen_y = int(screen_res_y / 2)

PUL = ctypes.POINTER(ctypes.c_ulong)

class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort)
    ]

class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class Input_I(ctypes.Union):
    _fields_ = [
        ("ki", KeyBdInput),
        ("mi", MouseInput),
        ("hi", HardwareInput)
    ]

class Input(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", Input_I)
    ]

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class Aimbot:
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    screen = mss.mss()

    # Load initial config
    with open("lib/config/config.json") as f:
        config = json.load(f)

    aimbot_status = colored("ENABLED", 'green')
    mouse_dll = None

    def __init__(self, box_constant=None, collect_data=False):
        self.load_config(Aimbot.config)
        
        self.box_constant = box_constant if box_constant else Aimbot.config.get("box_constant", 350)
        self.collect_data = collect_data

        print("[INFO] Loading YOLO model")
        self.model = YOLO('lib/yolov11.engine')
        if torch.cuda.is_available():
            print(colored("CUDA ACCELERATION [ENABLED]", "green"))
        else:
            print(colored("[!] CUDA ACCELERATION IS UNAVAILABLE", "red"))
            print(colored("[!] Check your PyTorch installation, else performance will be poor", "red"))

        # Open serial port
        try:
            self.ser = serial.Serial(
                Aimbot.config.get("serial_port", "COM2"),
                Aimbot.config.get("serial_baudrate", 115200),
                timeout=Aimbot.config.get("serial_timeout", 1)
            )
            time.sleep(2)
            print("[INFO] Serial COM2 opened successfully.")
        except Exception as e:
            print(f"[ERROR] Could not open COM2: {e}")
            sys.exit(1)

        print("\n[INFO] PRESS 'F1' TO TOGGLE AIMBOT\n[INFO] PRESS 'F2' TO QUIT")

    def load_config(self, config_data):
        """Load values from config dict into instance variables"""
        self.mouse_delay = config_data.get("mouse_delay", 0.0009)
        self.aim_height = config_data.get("aim_height", 10)
        self.conf = config_data.get("confidence", 0.45)
        self.iou = config_data.get("iou", 0.45)
        self.use_trigger_bot = config_data.get("use_trigger_bot", True)
        self.debug_mode = config_data.get("debug_mode", False)
        self.targeting_scale = config_data.get("targeting_scale", 10.0)
        self.pixel_increment = config_data.get("pixel_increment", 1.0)

        if self.debug_mode:
            print("[DEBUG] Config loaded:", config_data)

    def reload_config(self):
        """Reload config file from disk and apply new settings live"""
        try:
            with open("lib/config/config.json") as f:
                new_config = json.load(f)
            self.load_config(new_config)
            if self.debug_mode:
                print("[DEBUG] Config reloaded.")
        except Exception as e:
            print(f"[ERROR] Failed to reload config: {e}")

    def update_status_aimbot():
        if Aimbot.aimbot_status == colored("ENABLED", 'green'):
            Aimbot.aimbot_status = colored("DISABLED", 'red')
        else:
            Aimbot.aimbot_status = colored("ENABLED", 'green')
        sys.stdout.write("\033[K")
        print(f"[!] AIMBOT IS [{Aimbot.aimbot_status}]", end = "\r")

    def left_click(self):
        self.ser.write(b"km.left(1)\r\n")
        time.sleep(0.02)
        self.ser.write(b"km.left(0)\r\n")
        if self.debug_mode:
            print("[DEBUG] Sent left click")

    def sleep(duration, get_now = time.perf_counter):
        if duration == 0: return
        now = get_now()
        end = now + duration
        while now < end:
            now = get_now()

    def is_aimbot_enabled():
        return Aimbot.aimbot_status == colored("ENABLED", 'green')

    def is_shooting():
        return win32api.GetKeyState(0x01) in (-127, -128)

    def is_targeted():
        return win32api.GetKeyState(0x02) in (-127, -128)

    def is_target_locked(x, y):
        threshold = 5
        return (screen_x - threshold <= x <= screen_x + threshold and
                screen_y - threshold <= y <= screen_y + threshold)

    def move_crosshair(self, absolute_x, absolute_y):
        scale = self.targeting_scale
        pixel_inc = max(self.pixel_increment, 0.1)

        total_dx = (absolute_x - screen_x) * scale
        total_dy = (absolute_y - screen_y) * scale

        distance = math.hypot(total_dx, total_dy)
        steps = max(int(distance / pixel_inc), 1)

        step_dx = total_dx / steps
        step_dy = total_dy / steps

        for _ in range(steps):
            dx = int(round(step_dx))
            dy = int(round(step_dy))

            if abs(dx) < 1 and abs(dy) < 1:
                continue

            cmd = f"km.move({dx},{dy})\r\n"
            self.ser.write(cmd.encode())

            if self.debug_mode:
                print(f"[DEBUG] Sent move {dx}, {dy}")

            if self.mouse_delay > 0:
                time.sleep(self.mouse_delay)

    def start(self):
        print("[INFO] Beginning screen capture")
        Aimbot.update_status_aimbot()

        half_screen_width = ctypes.windll.user32.GetSystemMetrics(0) / 2
        half_screen_height = ctypes.windll.user32.GetSystemMetrics(1) / 2
        detection_box = {
            'left': int(half_screen_width - self.box_constant // 2),
            'top': int(half_screen_height - self.box_constant // 2),
            'width': int(self.box_constant),
            'height': int(self.box_constant)
        }

        frame_counter = 0

        while True:
            start_time = time.perf_counter()

            frame_counter += 1
            if frame_counter % 30 == 0:
                self.reload_config()

            initial_frame = Aimbot.screen.grab(detection_box)
            frame = np.array(initial_frame, dtype=np.uint8)
            if frame is None or frame.size == 0:
                continue
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            boxes = self.model.predict(source=frame, verbose=False, conf=self.conf, iou=self.iou, half=True)
            result = boxes[0]
            if len(result.boxes.xyxy) != 0:
                least_crosshair_dist = False
                closest_detection = False
                player_in_frame = False

                for box in result.boxes.xyxy:
                    x1, y1, x2, y2 = map(int, box)
                    x1y1 = (x1, y1)
                    x2y2 = (x2, y2)
                    height = y2 - y1
                    relative_head_X = int((x1 + x2) / 2)
                    relative_head_Y = int((y1 + y2) / 2 - height / self.aim_height)
                    own_player = x1 < 15 or (x1 < self.box_constant / 5 and y2 > self.box_constant / 1.2)

                    crosshair_dist = math.dist(
                        (relative_head_X, relative_head_Y),
                        (self.box_constant / 2, self.box_constant / 2)
                    )

                    if not least_crosshair_dist:
                        least_crosshair_dist = crosshair_dist

                    if crosshair_dist <= least_crosshair_dist and not own_player:
                        least_crosshair_dist = crosshair_dist
                        closest_detection = {
                            "x1y1": x1y1,
                            "x2y2": x2y2,
                            "relative_head_X": relative_head_X,
                            "relative_head_Y": relative_head_Y
                        }

                    if own_player:
                        own_player = False
                        if not player_in_frame:
                            player_in_frame = True

                if closest_detection:
                    cv2.circle(
                        frame,
                        (closest_detection["relative_head_X"], closest_detection["relative_head_Y"]),
                        5,
                        (115, 244, 113),
                        -1
                    )

                    cv2.line(
                        frame,
                        (closest_detection["relative_head_X"], closest_detection["relative_head_Y"]),
                        (self.box_constant // 2, self.box_constant // 2),
                        (244, 242, 113),
                        2
                    )

                    absolute_head_X = closest_detection["relative_head_X"] + detection_box['left']
                    absolute_head_Y = closest_detection["relative_head_Y"] + detection_box['top']
                    x1, y1 = closest_detection["x1y1"]

                    if Aimbot.is_target_locked(absolute_head_X, absolute_head_Y):
                        if self.use_trigger_bot and not Aimbot.is_shooting():
                            self.left_click()

                        cv2.putText(
                            frame,
                            "LOCKED",
                            (x1 + 40, y1),
                            cv2.FONT_HERSHEY_DUPLEX,
                            0.5,
                            (115, 244, 113),
                            2
                        )
                    else:
                        cv2.putText(
                            frame,
                            "TARGETING",
                            (x1 + 40, y1),
                            cv2.FONT_HERSHEY_DUPLEX,
                            0.5,
                            (115, 113, 244),
                            2
                        )

                    if Aimbot.is_aimbot_enabled():
                        self.move_crosshair(absolute_head_X, absolute_head_Y)

            elapsed = time.perf_counter() - start_time
            fps = int(1 / elapsed) if elapsed > 0 else 0

            cv2.putText(
                frame,
                f"FPS: {fps}",
                (5, 30),
                cv2.FONT_HERSHEY_DUPLEX,
                1,
                (113, 116, 244),
                2
            )
            cv2.imshow("Screen Capture", frame)

            sleep_time = max(0, (1/60) - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

            if cv2.waitKey(1) & 0xFF == ord('0'):
                break

    def clean_up():
        print("\n[INFO] F2 WAS PRESSED. QUITTING...")
        Aimbot.screen.close()
        os._exit(0)


if __name__ == "__main__":
    print("You are in the wrong directory and are running the wrong file; you must run lunar.py")
