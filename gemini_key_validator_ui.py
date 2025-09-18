
import customtkinter as ctk
import asyncio
import re
import sys
import aiohttp
import threading
import queue

# --- Core Validation Logic (from previous script) ---

API_KEY_PATTERN = r"AIza[0-9A-Za-z\-_]{35}"
MODEL_TO_VALIDATE = "gemini-1.5-flash"

async def check_key(session: aiohttp.ClientSession, key: str, result_queue: queue.Queue):
    """
    Validates a single Gemini API Key and puts the result into a queue.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_TO_VALIDATE}?key={key}"
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                result_queue.put(f"[  OK  ] Key ...{key[-4:]} is VALID.")
                return key
            else:
                try:
                    error_data = await response.json()
                    error_message = error_data.get("error", {}).get("message", "Unknown error")
                    result_queue.put(f"[ FAIL ] Key ...{key[-4:]} is INVALID. Status: {response.status}, Reason: {error_message}")
                except Exception:
                    result_queue.put(f"[ FAIL ] Key ...{key[-4:]} is INVALID. Status: {response.status}, Reason: {response.reason}")
                return None
    except asyncio.TimeoutError:
        result_queue.put(f"[ FAIL ] Key ...{key[-4:]} timed out.")
        return None
    except Exception as e:
        result_queue.put(f"[ FAIL ] Key ...{key[-4:]} failed with an unexpected error: {e}")
        return None

async def validate_keys_async(keys: list, result_queue: queue.Queue):
    """
    Asynchronously validates a list of keys.
    """
    valid_keys = []
    async with aiohttp.ClientSession() as session:
        tasks = [check_key(session, key, result_queue) for key in keys]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            if result:
                valid_keys.append(result)
    
    result_queue.put(("DONE", valid_keys)) # Signal completion

# --- UI Application ---

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Gemini API Key Validator")
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Input textbox
        self.grid_rowconfigure(3, weight=1) # Output textbox

        # --- Widgets ---
        self.title_label = ctk.CTkLabel(self, text=f"Gemini Key Validator for Model: {MODEL_TO_VALIDATE}", font=ctk.CTkFont(size=16, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        self.input_textbox = ctk.CTkTextbox(self, height=150)
        self.input_textbox.grid(row=1, column=0, padx=20, pady=5, sticky="nsew")
        self.input_textbox.insert("0.0", "Paste your API keys here...")

        self.validate_button = ctk.CTkButton(self, text="Validate Keys", command=self.start_validation_thread)
        self.validate_button.grid(row=2, column=0, padx=20, pady=10)

        self.output_textbox = ctk.CTkTextbox(self, state="disabled", height=200)
        self.output_textbox.grid(row=3, column=0, padx=20, pady=5, sticky="nsew")

        self.summary_label = ctk.CTkLabel(self, text="Ready.", font=ctk.CTkFont(size=12))
        self.summary_label.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="w")

        self.result_queue = queue.Queue()

    def start_validation_thread(self):
        """Starts the validation process in a separate thread to avoid freezing the UI."""
        self.validate_button.configure(state="disabled", text="Validating...")
        self.output_textbox.configure(state="normal")
        self.output_textbox.delete("1.0", "end")
        self.output_textbox.configure(state="disabled")
        self.summary_label.configure(text="Starting validation...")

        # Clear the queue
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break

        user_input = self.input_textbox.get("1.0", "end")
        keys_found = re.findall(API_KEY_PATTERN, user_input)
        unique_keys = sorted(list(set(keys_found)))

        if not unique_keys:
            self.summary_label.configure(text="No valid API key format found in input.")
            self.validate_button.configure(state="normal", text="Validate Keys")
            return

        self.summary_label.configure(text=f"Found {len(unique_keys)} unique keys. Starting validation...")

        # Run the async validation in a separate thread
        self.validation_thread = threading.Thread(
            target=lambda: asyncio.run(validate_keys_async(unique_keys, self.result_queue)),
            daemon=True
        )
        self.validation_thread.start()
        self.after(100, self.process_queue)

    def process_queue(self):
        """Periodically checks the queue for messages from the worker thread."""
        try:
            while True:
                message = self.result_queue.get_nowait()
                
                if isinstance(message, tuple) and message[0] == "DONE":
                    # Validation is complete
                    valid_keys = message[1]
                    total_keys = len(re.findall(API_KEY_PATTERN, self.input_textbox.get("1.0", "end")))
                    self.summary_label.configure(text=f"Validation complete. Found {len(valid_keys)} valid key(s) out of {total_keys} unique keys.")
                    self.validate_button.configure(state="normal", text="Validate Keys")
                    
                    if valid_keys:
                        self.log_to_output("\n--- VALID KEYS ---")
                        for key in valid_keys:
                            self.log_to_output(key)
                    return # Stop polling
                else:
                    self.log_to_output(message)

        except queue.Empty:
            pass # No new messages

        # If thread is alive, continue polling
        if self.validation_thread.is_alive():
            self.after(100, self.process_queue)
        else: # Thread finished but no DONE signal, something might be wrong
            self.validate_button.configure(state="normal", text="Validate Keys")
            if "Validation complete" not in self.summary_label.cget("text"):
                 self.summary_label.configure(text="Validation finished or terminated unexpectedly.")

    def log_to_output(self, message):
        """Appends a message to the output textbox."""
        self.output_textbox.configure(state="normal")
        self.output_textbox.insert("end", message + "\n")
        self.output_textbox.see("end")
        self.output_textbox.configure(state="disabled")

if __name__ == "__main__":
    # On Windows, the default event loop policy can cause issues with aiohttp in threads.
    # WindowsSelectorEventLoopPolicy is a robust choice.
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    app = App()
    app.mainloop()
