# File: gui.py
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import threading
import time
import os
import browser_handler
import ai_handler
import config_manager

class AutoAnswerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("U-Campus AI Assistant v2.0")
        self.root.geometry("650x850")
        self.driver = None

        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.create_text_boxes(main_frame)
        self.create_controls(main_frame)
        self.create_status_bar()
        
        self.log("Welcome! Please start by connecting to the browser.")

    def create_text_boxes(self, parent):
        self.log_text = self.create_labeled_text(parent, "Logs", height=8)
        self.question_text = self.create_labeled_text(parent, "Extracted Questions", height=8)
        self.prompt_text = self.create_labeled_text(parent, "Final Prompt for AI", height=10)
        self.response_text = self.create_labeled_text(parent, "Raw AI Response", height=6)

    def create_labeled_text(self, parent, label, height):
        frame = tk.LabelFrame(parent, text=label, padx=5, pady=5)
        frame.pack(fill=tk.X, pady=5)
        text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=height)
        text_widget.pack(fill=tk.BOTH, expand=True)
        return text_widget

    def create_controls(self, parent):
        controls_frame = tk.Frame(parent)
        controls_frame.pack(fill=tk.X, pady=10)

        tk.Label(controls_frame, text="Select AI Model:").pack(side=tk.LEFT, padx=(0, 5))
        self.selected_model = tk.StringVar()
        self.model_dropdown = ttk.Combobox(controls_frame, textvariable=self.selected_model, state="readonly")
        self.model_dropdown['values'] = list(ai_handler.AI_PROVIDERS.keys())
        self.model_dropdown.current(0)
        self.model_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=5)
        self.start_button = tk.Button(button_frame, text="Connect to Browser", command=self.start_browser_thread)
        self.start_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.run_button = tk.Button(button_frame, text="Auto-Answer", command=self.start_auto_answer_thread, state=tk.DISABLED)
        self.run_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.clear_button = tk.Button(button_frame, text="Clear Blanks", command=self.start_clear_inputs_thread, state=tk.DISABLED)
        self.clear_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
    def create_status_bar(self):
        self.status_label = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.status_label.config(text=message)
        print(message)

    def start_browser_thread(self):
        self.log("Attempting to connect to browser...")
        self.start_button.config(state=tk.DISABLED)
        threading.Thread(target=self.connect_browser, daemon=True).start()

    def start_auto_answer_thread(self):
        self.log("Starting auto-answer process...")
        self.run_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.DISABLED)
        threading.Thread(target=self.run_auto_answer, daemon=True).start()

    def start_clear_inputs_thread(self):
        self.log("Clearing all input fields...")
        self.clear_button.config(state=tk.DISABLED)
        threading.Thread(target=self.clear_inputs, daemon=True).start()

    def connect_browser(self):
        try:
            driver_path = config_manager.get_driver_path()
            if not driver_path or not os.path.exists(driver_path):
                self.log(f"Error: ChromeDriver not found at {driver_path}")
                messagebox.showerror("Driver Error", f"ChromeDriver not found at:\n{driver_path}\nPlease check config.ini.")
                self.start_button.config(state=tk.NORMAL)
                return

            self.driver = browser_handler.connect_or_start_chrome(driver_path)
            self.log("Browser connection successful.")
            browser_handler.check_and_navigate(self.driver)
            self.log("Page checked and ready.")
            
            self.run_button.config(state=tk.NORMAL)
            self.clear_button.config(state=tk.NORMAL)
            self.start_button.config(text="Reconnect Browser", state=tk.NORMAL)

        except Exception as e:
            self.log(f"Failed to connect to browser: {e}")
            messagebox.showerror("Browser Connection Failed", str(e))
            self.start_button.config(state=tk.NORMAL)

    def run_auto_answer(self):
        if not self.driver:
            self.log("Browser not connected.")
            return
        try:
            self.log("Extracting questions...")
            page_data = browser_handler.extract_questions_from_page(self.driver)
            if not page_data.get("questions"):
                self.log("Failed to extract questions. Aborting.")
                messagebox.showwarning("Extraction Failed", "Could not find questions. Please navigate to the correct page.")
                return

            self.question_text.delete(1.0, tk.END)
            self.question_text.insert(1.0, "\n".join(page_data['questions']))
            self.log(f"Extracted {len(page_data['questions'])} questions.")

            blank_counts = browser_handler.get_blank_counts(self.driver, len(page_data['questions']))
            self.log(f"Blank counts: {blank_counts}")
            
            prompt = ai_handler.build_prompt(**page_data, blank_counts=blank_counts)
            self.prompt_text.delete(1.0, tk.END)
            self.prompt_text.insert(1.0, prompt)
            self.log("Generated prompt.")

            model_name = self.selected_model.get()
            provider_key_name = model_name.split(" ")[0].lower()
            api_key = config_manager.get_api_key(provider_key_name)
            
            if not api_key or "YOUR_" in api_key:
                self.log(f"API Key for {model_name} is not set in config.ini.")
                messagebox.showerror("API Key Error", f"Please set the API key for {model_name} in config.ini.")
                return

            self.log(f"Calling {model_name}...")
            provider = ai_handler.get_ai_provider(model_name, api_key)
            ai_response = provider.call_ai(prompt)
            self.response_text.delete(1.0, tk.END)
            self.response_text.insert(1.0, ai_response)
            
            self.log("Parsing AI response...")
            answers = ai_handler.parse_ai_response(ai_response)
            if not answers:
                self.log("Could not parse a valid answer from the AI response.")
                messagebox.showwarning("Parsing Failed", "The AI response was not in the expected format.")
                return
            
            self.log(f"Parsed answers: {answers}")
            self.log("Filling answers into webpage...")
            browser_handler.fill_answers_to_webpage(self.driver, answers)
            self.log("Auto-answering complete!")

        except Exception as e:
            self.log(f"An error occurred: {e}")
            messagebox.showerror("Runtime Error", str(e))
        finally:
            self.run_button.config(state=tk.NORMAL)
            self.clear_button.config(state=tk.NORMAL)

    def clear_inputs(self):
        if not self.driver:
            self.log("Browser not connected.")
            return
        try:
            browser_handler.clear_all_inputs(self.driver)
            self.log("All input fields have been cleared.")
        except Exception as e:
            self.log(f"Failed to clear inputs: {e}")
            messagebox.showerror("Clear Failed", str(e))
        finally:
            self.clear_button.config(state=tk.NORMAL)