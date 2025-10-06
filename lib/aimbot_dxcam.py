import json
import threading
import time
import numpy as np
import dxcam
from ultralytics import YOLO
import win32gui
import win32con
import win32api
import win32ui
import ctypes
import serial

# Screen info
user32 = ctypes.windll.user32
screen_res_x = user32.GetSystemMetrics(0)
screen_res_y = user32.GetSystemMetrics(1)
screen_x = screen_res_x // 2
screen_y = screen_res_y // 2

# Config
with open("lib/config/config.json") as f:
    CONFIG = json.load(f)

# Serial
try:
    ser = serial.Serial(
        CONFIG.get("serial_port", "COM2"),
        CONFIG.get("serial_baudrate", 115200),
        timeout=CONFIG.get("serial_timeout", 1)
    )
    time.sleep(2)
    print("[INFO] Serial COM2 opened successfully.")
except Exception as e:
    print(f"[ERROR] Could not open COM2: {e}")
    exit(1)

# Load YOLO
model = YOLO("lib/yolov11.engine")

# Shared state
latest_frame = None
latest_detection = None
frame_lock = threading.Lock()
detection_lock = threading.Lock()

# Find Chiaki-ng window
def get_chiaki_window_rect():
    hwnd = win32gui.FindWindow(None, "Chiaki-ng")
    if not hwnd:
        raise Exception("Chiaki-ng window not found.")
    rect = win32gui.GetClientRect(hwnd)
    left, top = win32gui.ClientToScreen(hwnd, (0, 0))
    right, bottom = left + rect[2], top + rect[3]
    return left, top, right, bottom

left, top, right, bottom = get_chiaki_window_rect()
region = (left, top, right, bottom)

# Overlay (transparent window)
class OverlayWindow:
    def __init__(self, width, height):
        self.hInstance = win32api.GetModuleHandle(None)
        self.className = "MyOverlayClass"
        wndClass = win32gui.WNDCLASS()
        wndClass.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        wndClass.lpfnWndProc = self.wndProc
        wndClass.hInstance = self.hInstance
        wndClass.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wndClass.hbrBackground = win32con.COLOR_WINDOW
        wndClass.lpszClassName = self.className
        self.classAtom = win32gui.RegisterClass(wndClass)

        style = win32con.WS_POPUP
        exStyle = win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOPMOST
        self.hwnd = win32gui.CreateWindowEx(
            exStyle,
            self.classAtom,
            None,
            style,
            left, top, right-left, bottom-top,
            0, 0, self.hInstance, None
        )
        win32gui.SetLayeredWindowAttributes(self.hwnd, 0x00ffffff, 255, win32con.LWA_COLORKEY)
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)

    def wndProc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_PAINT:
            hdc, paintStruct = win32gui.BeginPaint(hwnd)
            self.onPaint(hdc)
            win32gui.EndPaint(hwnd, paintStruct)
            return 0
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        else:
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def onPaint(self, hdc):
        # Draw crosshair or boxes
        if latest_detection:
            head_x = latest_detection["absolute_x"] - left
            head_y = latest_detection["absolute_y"] - top
            radius = 10
            win32gui.SelectObject(hdc, win32gui.GetStockObject(win32con.NULL_BRUSH))
            win32gui.Ellipse(hdc,
                head_x - radius,
                head_y - radius,
                head_x + radius,
                head_y + radius
            )
            win32gui.MoveToEx(hdc, head_x, head_y, None)
            win32gui.LineTo(hdc, (right-left)//2, (bottom-top)//2)

    def update(self):
        win32gui.InvalidateRect(self.hwnd, None, True)

overlay = OverlayWindow(right-left, bottom-top)

# Threads
camera = dxcam.create()

def capture_thread():
    global latest_frame
    while True:
        frame = camera.grab(region=region)
        if frame is not None:
            with frame_lock:
                latest_frame = frame
        time.sleep(0.001)

def detection_thread():
    global latest_frame, latest_detection
    while True:
        with frame_lock:
            frame = latest_frame.copy() if latest_frame is not None else None
        if frame is None:
            continue

        # YOLO expects RGB
        result = model.predict(
            source=frame,
            verbose=False,
            imgsz=320,
            conf=CONFIG.get("confidence", 0.4),
            iou=CONFIG.get("iou", 0.45),
            half=True
        )
        detections = result[0].boxes.xyxy.cpu().numpy() if len(result) else []
        closest = None
        least_dist = float("inf")
        for box in detections:
            x1, y1, x2, y2 = map(int, box)
            height = y2 - y1
            relative_x = int((x1 + x2) / 2)
            relative_y = int((y1 + y2) / 2 - height / CONFIG.get("aim_height", 4))
            dist = np.linalg.norm(
                [relative_x - (right-left)//2, relative_y - (bottom-top)//2]
            )
            if dist < least_dist:
                least_dist = dist
                closest = (relative_x, relative_y)

        if closest:
            absolute_x = closest[0] + left
            absolute_y = closest[1] + top
            with detection_lock:
                latest_detection = {
                    "absolute_x": absolute_x,
                    "absolute_y": absolute_y
                }
        else:
            with detection_lock:
                latest_detection = None

def aiming_thread():
    while True:
        with detection_lock:
            detection = latest_detection
        if detection:
            # Move instantly to measured position
            dx = int(round((detection["absolute_x"] - screen_x) * CONFIG.get("targeting_scale", 0.4)))
            dy = int(round((detection["absolute_y"] - screen_y) * CONFIG.get("targeting_scale", 0.4)))
            cmd = f"km.move({dx},{dy})\r\n"
            ser.write(cmd.encode())
            if CONFIG.get("debug_mode", False):
                print(f"[DEBUG] Sent move {dx}, {dy}")
        overlay.update()
        time.sleep(CONFIG.get("mouse_delay", 0.001))

# Start threads
threading.Thread(target=capture_thread, daemon=True).start()
threading.Thread(target=detection_thread, daemon=True).start()
threading.Thread(target=aiming_thread, daemon=True).start()

# Overlay window message loop
win32gui.PumpMessages()
