from pyautogui import *
from time import sleep
from tkinter import Tk  

def _get_total_records():
    moveTo(227, 450)
    click(clicks=2)
    hotkey("ctrl", "c")
    records_count = Tk().clipboard_get().replace(" ", "").replace(",", "")
    return records_count

def open_download_page(url):
    moveTo(300, 150)
    click()
    hotkey("ctrl", "t")
    write(url)
    press("enter")
    sleep(2) # wait for security check
    moveTo(200, 400)
    click()
    sleep(0.5)
    moveTo(300, 500)
    click()
    sleep(8)
    records_count = _get_total_records()
    sleep(1)
    hotkey("ctrl", "f")
    write("csv")
    press("enter")
    press("esc")
    press("enter")
    return records_count


def select_download_date(month_diff):
    moveTo(700, 535)
    click()
    moveTo(700, 535)
    click()
    moveTo(640, 575)
    for i in range(month_diff):
        click()
    moveTo(700, 650)
    click()

    try:
        moveTo(800, 625)
        click()
    except:
        pass


def captcha():
    moveTo(950, 720)
    click()
    
def next_download(month_diff):
    moveTo(700, 535)
    click()
    hotkey("ctrl", "r")
    sleep(3)
    