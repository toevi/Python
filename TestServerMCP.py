import tkinter as tk
from tkinter import ttk, scrolledtext
import requests
import threading

MCP_URL = "http://localhost:3000"
TIMEOUT = 120  # 2 minuty, dłuższe odpowiedzi

def send_request_thread():
    endpoint = endpoint_var.get()
    text = input_text.get("1.0", tk.END).strip()
    if not text:
        log_text.insert(tk.END, "❌ Nie wpisano tekstu!\n")
        return

    log_text.insert(tk.END, f"🔥 Wysyłam do {endpoint}...\n")
    log_text.see(tk.END)

    url_map = {
        "Chat": "/v1/chat/completions",
        "Edit": "/v1/edits",
        "Autocomplete": "/v1/completions",
        "Agent": "/v1/agents"
    }

    url = MCP_URL + url_map[endpoint]

    if endpoint == "Chat":
        body = {"model": "deepseek-coder-v2-lite-instruct",
                "messages": [{"role": "user", "content": text}],
                "max_tokens": 4000}
    elif endpoint == "Edit":
        body = {"model": "deepseek-coder-v2-lite-instruct",
                "input": text,
                "instruction": "Popraw kod lub treść"}
    elif endpoint == "Autocomplete":
        body = {"model": "deepseek-coder-v2-lite-instruct",
                "prompt": text,
                "max_tokens": 1000}
    elif endpoint == "Agent":
        body = {"query": text}

    try:
        response = requests.post(url, json=body, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if endpoint in ["Chat", "Edit", "Agent"]:
            content = data['choices'][0]['message']['content']
        elif endpoint == "Autocomplete":
            content = data['choices'][0]['text']

        log_text.insert(tk.END, f"✅ Odpowiedź:\n{content}\n\n")
    except Exception as e:
        log_text.insert(tk.END, f"❌ Błąd: {e}\n\n")
    finally:
        log_text.see(tk.END)

def send_request():
    threading.Thread(target=send_request_thread, daemon=True).start()


# GUI
root = tk.Tk()
root.title("MCP Proxy Tester")
root.geometry("900x700")
root.columnconfigure(0, weight=1)
root.rowconfigure(3, weight=1)

ttk.Label(root, text="Wybierz endpoint:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
endpoint_var = tk.StringVar(value="Chat")
ttk.OptionMenu(root, endpoint_var, "Chat", "Chat", "Edit", "Autocomplete", "Agent").grid(row=0, column=0, sticky="e", padx=5, pady=5)

ttk.Label(root, text="Tekst do wysłania:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
input_text = scrolledtext.ScrolledText(root, height=7)
input_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
root.rowconfigure(1, weight=0)

ttk.Button(root, text="Wyślij", command=send_request).grid(row=1, column=0, sticky="e", padx=10, pady=5)

ttk.Label(root, text="Odpowiedź:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
log_text = scrolledtext.ScrolledText(root)
log_text.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)

root.mainloop()
