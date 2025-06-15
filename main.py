# File: main.py
import tkinter as tk
from gui import AutoAnswerGUI
import os

if __name__ == "__main__":
    # This helps with high-DPI displays
    if os.name == 'nt':
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
            
    root = tk.Tk()
    app = AutoAnswerGUI(root)
    root.mainloop()