import tkinter as tk
from tkinter import ttk, scrolledtext
import requests
import threading
import re
import json
import os

CONFIG_FILE = "config.json"
TIMEOUT = 120

# Kolory Dark Theme
COLORS = {
    'bg_primary': '#1e1e1e',
    'bg_secondary': '#252526',
    'bg_input': '#3c3c3c',
    'fg_primary': '#cccccc',
    'fg_secondary': '#969696',
    'accent': '#007acc',
    'accent_hover': '#1177bb',
    'border': '#464647',
    'selection': '#264f78',
    'success': '#4ec9b0',
    'error': '#f44747',
    'warning': '#ffcc02',
    'keyword': '#569cd6',
    'string': '#ce9178',
    'comment': '#6a9955',
    'number': '#b5cea8',
    'function': '#dcdcaa',
    'operator': '#d4d4d4'
}

# --- Konfiguracja --- #
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "lm_studio": {"ip": "127.0.0.1", "port": 7860},
        "proxy_agent": {"ip": "localhost", "port": 3000}
    }

def save_config():
    config["lm_studio"]["ip"] = lm_ip_var.get()
    config["lm_studio"]["port"] = int(lm_port_var.get())
    config["proxy_agent"]["ip"] = proxy_ip_var.get()
    config["proxy_agent"]["port"] = int(proxy_port_var.get())
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

config = load_config()

# --- Funkcje kolorowania kodu Python --- #
def colorize_python_code(text_widget, start_index):
    try:
        content = text_widget.get(start_index, tk.END)
        code_blocks = re.finditer(r'```(?:python)?\s*\n?(.*?)```', content, re.DOTALL | re.IGNORECASE)
        for match in code_blocks:
            try:
                code_content = match.group(1)
                code_start_index = text_widget.index(f"{start_index}+{match.start(1)}c")
                code_end_index = text_widget.index(f"{start_index}+{match.end(1)}c")
                text_widget.tag_add('code_block', code_start_index, code_end_index)

                keywords = ['def', 'class', 'if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally', 
                            'import', 'from', 'as', 'return', 'yield', 'break', 'continue', 'pass', 'lambda',
                            'and', 'or', 'not', 'in', 'is', 'None', 'True', 'False', 'with', 'async', 'await']
                for keyword in keywords:
                    for kw_match in re.finditer(r'\b' + re.escape(keyword) + r'\b', code_content):
                        kw_start_pos = text_widget.index(f"{code_start_index}+{kw_match.start()}c")
                        kw_end_pos   = text_widget.index(f"{code_start_index}+{kw_match.end()}c")
                        text_widget.tag_add('keyword', kw_start_pos, kw_end_pos)

                for pattern in [r'"[^"]*"', r"'[^']*'"]:
                    for str_match in re.finditer(pattern, code_content):
                        str_start_pos = text_widget.index(f"{code_start_index}+{str_match.start()}c")
                        str_end_pos   = text_widget.index(f"{code_start_index}+{str_match.end()}c")
                        text_widget.tag_add('string', str_start_pos, str_end_pos)

                for comment_match in re.finditer(r'#.*$', code_content, re.MULTILINE):
                    com_start_pos = text_widget.index(f"{code_start_index}+{comment_match.start()}c")
                    com_end_pos   = text_widget.index(f"{code_start_index}+{comment_match.end()}c")
                    text_widget.tag_add('comment', com_start_pos, com_end_pos)

                for num_match in re.finditer(r'\b\d+\.?\d*\b', code_content):
                    num_start_pos = text_widget.index(f"{code_start_index}+{num_match.start()}c")
                    num_end_pos   = text_widget.index(f"{code_start_index}+{num_match.end()}c")
                    text_widget.tag_add('number', num_start_pos, num_end_pos)

            except tk.TclError:
                pass
    except Exception:
        pass

# --- Funkcje do wysyłania requestów --- #
def get_current_url(endpoint):
    save_config()
    if endpoint == "Chat":
        return f"http://{lm_ip_var.get()}:{lm_port_var.get()}/v1/chat/completions"
    else:  # Agent
        return f"http://{proxy_ip_var.get()}:{proxy_port_var.get()}/v1/agents"

def send_request_thread():
    endpoint = endpoint_var.get()
    text = input_text.get("1.0", tk.END).strip()
    if not text:
        log_text.configure(state=tk.NORMAL)
        log_text.insert(tk.END, "❌ Nie wpisano tekstu!\n", 'error')
        log_text.configure(state=tk.DISABLED)
        return

    url = get_current_url(endpoint)
    try:
        if endpoint == "Chat":
            body = {"model": "deepseek-coder-v2-lite-instruct",
                    "messages": [{"role": "user", "content": text}],
                    "max_tokens": 4000}
        else:
            body = {"query": text}

        log_text.configure(state=tk.NORMAL)
        log_text.insert(tk.END, f"🔥 Wysyłam do {endpoint}...\n", 'info')
        log_text.see(tk.END)
        log_text.update()

        response = requests.post(url, json=body, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        content = data['choices'][0]['message']['content']
        log_text.insert(tk.END, f"✅ Odpowiedź:\n", 'success')
        response_start = log_text.index(tk.END)
        log_text.insert(tk.END, f"{content}\n\n", 'response')
        colorize_python_code(log_text, response_start)

    except requests.exceptions.RequestException as e:
        log_text.insert(tk.END, f"❌ Błąd żądania: {e}\n\n", 'error')
    except KeyError:
        log_text.insert(tk.END, "❌ Nieprawidłowa odpowiedź od serwera\n\n", 'error')
    finally:
        log_text.see(tk.END)
        log_text.configure(state=tk.DISABLED)

def send_request():
    threading.Thread(target=send_request_thread, daemon=True).start()

def on_button_enter(event):
    event.widget.config(bg=COLORS['accent_hover'])

def on_button_leave(event):
    event.widget.config(bg=COLORS['accent'])

# --- GUI --- #
root = tk.Tk()
root.title("MCP Proxy Chat + Agent")
root.geometry("1000x900")
root.configure(bg=COLORS['bg_primary'])

style = ttk.Style()
style.theme_use('clam')
style.configure('Dark.TLabel', background=COLORS['bg_primary'], foreground=COLORS['fg_primary'], font=('Consolas', 10))
style.configure('Dark.TButton', background=COLORS['accent'], foreground='white', borderwidth=1, font=('Consolas', 10, 'bold'))
style.map('Dark.TButton', background=[('active', COLORS['accent_hover']), ('pressed', COLORS['accent'])])
style.configure('Dark.TFrame', background=COLORS['bg_primary'])
style.configure('Dark.TCombobox', background=COLORS['bg_input'], foreground=COLORS['fg_primary'], font=('Consolas', 10), fieldbackground=COLORS['bg_input'], selectbackground=COLORS['selection'], selectforeground=COLORS['fg_primary'])

root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

main_frame = ttk.Frame(root, style='Dark.TFrame')
main_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
for i in range(12):
    main_frame.rowconfigure(i, weight=1)
main_frame.columnconfigure(0, weight=1)
main_frame.columnconfigure(1, weight=1)

# Nagłówek
header_label = ttk.Label(main_frame, text="🚀 MCP Proxy Chat + Agent", style='Dark.TLabel', font=('Consolas', 14, 'bold'))
header_label.grid(row=0, column=0, columnspan=2, sticky='w', pady=(0,10))

# Endpoint
ttk.Label(main_frame, text="Endpoint:", style='Dark.TLabel').grid(row=1, column=0, sticky='w')
endpoint_var = tk.StringVar(value="Agent")
endpoint_combo = ttk.Combobox(main_frame, textvariable=endpoint_var, values=["Agent", "Chat"], state="readonly", style='Dark.TCombobox', width=15)
endpoint_combo.grid(row=1, column=1, sticky='w')

# Tekst wejściowy
ttk.Label(main_frame, text="Tekst do wysłania:", style='Dark.TLabel').grid(row=2, column=0, sticky='w', pady=(10,5), columnspan=2)
input_text = scrolledtext.ScrolledText(main_frame, height=6, bg=COLORS['bg_input'], fg=COLORS['fg_primary'], insertbackground=COLORS['fg_primary'], selectbackground=COLORS['selection'], selectforeground=COLORS['fg_primary'], font=('Consolas', 11), relief='flat', borderwidth=1, wrap=tk.WORD)
input_text.grid(row=3, column=0, columnspan=2, sticky='nsew', pady=(0,10))

# Przycisk Wyślij
send_button = tk.Button(main_frame, text="▶ Wyślij", command=send_request, bg=COLORS['accent'], fg='white', font=('Consolas', 11, 'bold'), relief='flat', borderwidth=0, padx=20, pady=8, cursor='hand2')
send_button.grid(row=4, column=1, sticky='e', pady=(0,10))
send_button.bind('<Enter>', on_button_enter)
send_button.bind('<Leave>', on_button_leave)

# LM Studio IP / Port
ttk.Label(main_frame, text="LM Studio IP:", style='Dark.TLabel').grid(row=5, column=0, sticky='w')
lm_ip_var = tk.StringVar(value=config["lm_studio"]["ip"])
lm_ip_entry = ttk.Entry(main_frame, textvariable=lm_ip_var)
lm_ip_entry.grid(row=5, column=1, sticky='ew')

ttk.Label(main_frame, text="LM Studio Port:", style='Dark.TLabel').grid(row=6, column=0, sticky='w')
lm_port_var = tk.StringVar(value=str(config["lm_studio"]["port"]))
lm_port_entry = ttk.Entry(main_frame, textvariable=lm_port_var)
lm_port_entry.grid(row=6, column=1, sticky='ew')

# Proxy Agent IP / Port
ttk.Label(main_frame, text="Proxy Agent IP:", style='Dark.TLabel').grid(row=7, column=0, sticky='w')
proxy_ip_var = tk.StringVar(value=config["proxy_agent"]["ip"])
proxy_ip_entry = ttk.Entry(main_frame, textvariable=proxy_ip_var)
proxy_ip_entry.grid(row=7, column=1, sticky='ew')

ttk.Label(main_frame, text="Proxy Agent Port:", style='Dark.TLabel').grid(row=8, column=0, sticky='w')
proxy_port_var = tk.StringVar(value=str(config["proxy_agent"]["port"]))
proxy_port_entry = ttk.Entry(main_frame, textvariable=proxy_port_var)
proxy_port_entry.grid(row=8, column=1, sticky='ew')

# Log / odpowiedź
ttk.Label(main_frame, text="Odpowiedź:", style='Dark.TLabel').grid(row=9, column=0, sticky='w', pady=(10,5), columnspan=2)
log_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
log_frame.grid(row=10, column=0, columnspan=2, sticky='nsew', pady=(0,5))
log_frame.rowconfigure(0, weight=1)
log_frame.columnconfigure(0, weight=1)

log_scrollbar = tk.Scrollbar(log_frame, orient=tk.VERTICAL, bg=COLORS['bg_secondary'], troughcolor=COLORS['bg_secondary'], activebackground=COLORS['accent'])
log_scrollbar.grid(row=0, column=1, sticky='ns')

log_text = tk.Text(log_frame, bg=COLORS['bg_input'], fg=COLORS['fg_primary'], insertbackground=COLORS['fg_primary'], selectbackground=COLORS['selection'], selectforeground=COLORS['fg_primary'], font=('Consolas', 10), relief='flat', borderwidth=1, wrap=tk.NONE, yscrollcommand=log_scrollbar.set)
log_text.grid(row=0, column=0, sticky='nsew')
log_scrollbar.config(command=log_text.yview)

# Tagi kolorowania
log_text.tag_configure('error', foreground=COLORS['error'])
log_text.tag_configure('success', foreground=COLORS['success'])
log_text.tag_configure('info', foreground=COLORS['accent'])
log_text.tag_configure('warning', foreground=COLORS['warning'])
log_text.tag_configure('response', foreground=COLORS['fg_primary'], font=('Consolas', 10))
log_text.tag_configure('code_block', background=COLORS['bg_secondary'], font=('Consolas', 10))
log_text.tag_configure('keyword', foreground=COLORS['keyword'], font=('Consolas', 10, 'bold'))
log_text.tag_configure('string', foreground=COLORS['string'], font=('Consolas', 10))
log_text.tag_configure('comment', foreground=COLORS['comment'], font=('Consolas', 10, 'italic'))
log_text.tag_configure('number', foreground=COLORS['number'], font=('Consolas', 10))
log_text.tag_configure('function', foreground=COLORS['function'], font=('Consolas', 10))
log_text.tag_configure('operator', foreground=COLORS['operator'], font=('Consolas', 10))

# Wiadomość powitalna
log_text.insert(tk.END, "🌟 MCP Proxy Client gotowy do pracy!\n", 'success')
log_text.insert(tk.END, "💡 Tip: Użyj Ctrl+Enter aby wysłać zapytanie\n\n", 'info')
log_text.configure(state=tk.DISABLED)

# Bind Ctrl+Enter
def on_enter_key(event):
    if event.state & 0x4:  # Ctrl+Enter
        send_request()
        return 'break'

input_text.bind('<Control-Return>', on_enter_key)
input_text.focus_set()

root.mainloop()
