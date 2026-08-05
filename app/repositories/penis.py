import pyautogui
import random
import time

pyautogui.FAILSAFE = True

time.sleep(3)

width, height = pyautogui.size()

pyautogui.mouseDown(button="right")

try:
    while True:
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        pyautogui.moveTo(x, y, duration=0.15)
finally:
    pyautogui.mouseUp(button="right")