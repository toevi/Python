import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import threading
import re
import json
import os
import sys
from pathlib import Path

# Określenie ścieżki do pliku konfiguracyjnego
def get_config_path():
    """
    Zwraca bezpieczną ścieżkę do pliku konfiguracyjnego
    """
    try:
        # Próbuj użyć katalogu skryptu
        if hasattr(sys, '_MEIPASS'):
            # Jeśli aplikacja jest spakowana (PyInstaller)
            script_dir = Path(sys.executable).parent
        else:
            # Normalny tryb
            script_dir = Path(__file__).parent
        
        config_path = script_dir / "config.json"
        
        # Sprawdź czy można pisać w tym katalogu
        test_file = script_dir / "test_write.tmp"
        try:
            test_file.write_text("test")
            test_file.unlink()
            return str(config_path)
        except (PermissionError, OSError):
            pass
    except:
        pass
    
    # Fallback do katalogu domowego użytkownika
    home_dir = Path.home()
    config_path = home_dir / ".proxy_lm_studio" / "config.json"
    config_path.parent.mkdir(exist_ok=True)
    return str(config_path)

CONFIG_FILE = get_config_path()
TIMEOUT = 120

# --- Kolory Dark Theme --- #
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
    """
    Ładuje konfigurację z pliku JSON z obsługą błędów
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding='utf-8') as f:
                config = json.load(f)
                return config
    except (PermissionError, OSError) as e:
        print(f"Błąd odczytu konfiguracji: {e}")
        messagebox.showwarning("Błąd konfiguracji", 
                             f"Nie można odczytać pliku konfiguracyjnego:\n{CONFIG_FILE}\n\nUżywane będą domyślne ustawienia.")
    except json.JSONDecodeError as e:
        print(f"Błąd parsowania JSON: {e}")
        messagebox.showwarning("Błąd konfiguracji", 
                             "Plik konfiguracyjny jest uszkodzony. Używane będą domyślne ustawienia.")
    except Exception as e:
        print(f"Nieoczekiwany błąd: {e}")
    
    # Zwróć domyślną konfigurację
    return {
        "lm_studio": {"ip": "127.0.0.1", "port": 7860},
        "proxy_agent": {"ip": "localhost", "port": 3000}
    }

def save_config():
    """
    Zapisuje konfigurację do pliku JSON z obsługą błędów
    """
    try:
        config_data = {
            "lm_studio": {"ip": lm_ip_var.get(), "port": int(lm_port_var.get())},
            "proxy_agent": {"ip": proxy_ip_var.get(), "port": int(proxy_port_var.get())}
        }
        
        # Upewnij się, że katalog istnieje
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        with open(CONFIG_FILE, "w", encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        print(f"Konfiguracja zapisana w: {CONFIG_FILE}")
        
    except PermissionError:
        messagebox.showerror("Błąd zapisu", 
                           f"Brak uprawnień do zapisu w:\n{CONFIG_FILE}")
    except ValueError as e:
        messagebox.showerror("Błąd danych", 
                           f"Nieprawidłowe wartości w konfiguracji:\n{e}")
    except OSError as e:
        messagebox.showerror("Błąd systemu", 
                           f"Nie można zapisać pliku konfiguracyjnego:\n{e}")
    except Exception as e:
        messagebox.showerror("Błąd", 
                           f"Nieoczekiwany błąd podczas zapisu:\n{e}")

def validate_config_inputs():
    """
    Walidacja wprowadzonych danych konfiguracyjnych
    """
    try:
        # Sprawdź porty
        lm_port = int(lm_port_var.get())
        proxy_port = int(proxy_port_var.get())
        
        if not (1 <= lm_port <= 65535):
            raise ValueError("Port LM Studio musi być między 1 a 65535")
        if not (1 <= proxy_port <= 65535):
            raise ValueError("Port Proxy Agent musi być między 1 a 65535")
            
        # Sprawdź IP (podstawowa walidacja)
        lm_ip = lm_ip_var.get().strip()
        proxy_ip = proxy_ip_var.get().strip()
        
        if not lm_ip:
            raise ValueError("IP LM Studio nie może być pusty")
        if not proxy_ip:
            raise ValueError("IP Proxy Agent nie może być pusty")
            
        return True
        
    except ValueError as e:
        messagebox.showerror("Błąd walidacji", str(e))
        return False

# Załaduj konfigurację
config = load_config()

# --- Lista przycisków kopiowania --- #
copy_buttons = []

def clear_copy_buttons():
    """Usuń wszystkie przyciski kopiowania"""
    global copy_buttons
    for button in copy_buttons:
        try:
            button.destroy()
        except:
            pass
    copy_buttons.clear()

def copy_code_to_clipboard(code_text):
    """Kopiuje kod do schowka i pokazuje komunikat"""
    try:
        root.clipboard_clear()
        root.clipboard_append(code_text)
        
        # Pokaż tymczasowy komunikat
        temp_label = tk.Label(log_text, text="✅ Skopiowano!", 
                             bg=COLORS['success'], fg='white', font=('Consolas', 8, 'bold'),
                             relief='flat', padx=5, pady=2)
        
        # Umieść w prawym górnym rogu
        temp_label.place(relx=0.95, rely=0.05, anchor='ne')
        
        # Usuń po 2 sekundach
        root.after(2000, temp_label.destroy)
        
    except Exception as e:
        print(f"Błąd kopiowania: {e}")

def create_copy_button(text_widget, code_start, code_end, code_content):
    """Tworzy przycisk kopiowania dla bloku kodu"""
    def try_create_button():
        try:
            # Upewnij się, że widget jest widoczny i ma layout
            text_widget.update_idletasks()
            
            # Pobierz pozycję bloku kodu na ekranie
            bbox = text_widget.bbox(code_start)
            if bbox:
                x, y, width, height = bbox
                
                # Sprawdź czy pozycja jest sensowna
                if x >= 0 and y >= 0:
                    # Utwórz przycisk
                    copy_btn = tk.Button(text_widget, text="📋 Copy", 
                                       command=lambda: copy_code_to_clipboard(code_content),
                                       bg=COLORS['accent'], fg='white', 
                                       font=('Consolas', 7, 'bold'),
                                       relief='flat', borderwidth=0, 
                                       padx=4, pady=2, cursor='hand2')
                    
                    # Pobierz szerokość tekstu w tym wierszu aby umieścić przycisk na końcu
                    line_start = text_widget.index(f"{code_start} linestart")
                    line_end = text_widget.index(f"{code_start} lineend")
                    line_bbox = text_widget.bbox(line_end)
                    
                    if line_bbox:
                        btn_x = line_bbox[0] - 60  # 60 pikseli od prawej krawędzi linii
                        btn_y = y + 2
                    else:
                        btn_x = x + max(200, width - 60)  # Fallback
                        btn_y = y + 2
                    
                    # Umieść przycisk
                    copy_btn.place(x=btn_x, y=btn_y)
                    
                    # Dodaj hover effect
                    def on_copy_enter(event):
                        event.widget.config(bg=COLORS['accent_hover'])
                    def on_copy_leave(event):
                        event.widget.config(bg=COLORS['accent'])
                        
                    copy_btn.bind('<Enter>', on_copy_enter)
                    copy_btn.bind('<Leave>', on_copy_leave)
                    
                    # Dodaj do listy do późniejszego usunięcia
                    copy_buttons.append(copy_btn)
                    return True
            return False
        except Exception as e:
            print(f"Błąd tworzenia przycisku: {e}")
            return False
    
    # Spróbuj utworzyć przycisk z opóźnieniem
    def delayed_create(attempt=0):
        if try_create_button():
            return
        elif attempt < 5:  # Maksymalnie 5 prób
            root.after(200 + attempt * 100, lambda: delayed_create(attempt + 1))
    
    # Rozpocznij proces tworzenia
    root.after(300, delayed_create)

# --- Kolorowanie kodu Python --- #
def colorize_python_code(text_widget, start_index):
    try:
        content = text_widget.get(start_index, tk.END)
        code_blocks = re.finditer(r'```(?:python|py|javascript|js|java|c\+\+|cpp|c|html|css|sql|json|xml|yaml|yml|bash|shell|powershell)?\s*\n?(.*?)```', content, re.DOTALL | re.IGNORECASE)
        
        for match in code_blocks:
            try:
                code_content = match.group(1).strip()
                if not code_content:  # Pomiń puste bloki
                    continue
                    
                code_start_index = text_widget.index(f"{start_index}+{match.start(1)}c")
                code_end_index = text_widget.index(f"{start_index}+{match.end(1)}c")
                text_widget.tag_add('code_block', code_start_index, code_end_index)

                # Utwórz przycisk kopiowania dla tego bloku
                create_copy_button(text_widget, code_start_index, code_end_index, code_content)

                keywords = ['def', 'class', 'if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally', 
                            'import', 'from', 'as', 'return', 'yield', 'break', 'continue', 'pass', 'lambda',
                            'and', 'or', 'not', 'in', 'is', 'None', 'True', 'False', 'with', 'async', 'await',
                            'function', 'var', 'let', 'const', 'public', 'private', 'static', 'void', 'int', 'string']
                
                for keyword in keywords:
                    for kw_match in re.finditer(r'\b' + re.escape(keyword) + r'\b', code_content):
                        kw_start_pos = text_widget.index(f"{code_start_index}+{kw_match.start()}c")
                        kw_end_pos   = text_widget.index(f"{code_start_index}+{kw_match.end()}c")
                        text_widget.tag_add('keyword', kw_start_pos, kw_end_pos)

                for pattern in [r'"[^"]*"', r"'[^']*'", r'`[^`]*`']:
                    for str_match in re.finditer(pattern, code_content):
                        str_start_pos = text_widget.index(f"{code_start_index}+{str_match.start()}c")
                        str_end_pos   = text_widget.index(f"{code_start_index}+{str_match.end()}c")
                        text_widget.tag_add('string', str_start_pos, str_end_pos)

                for comment_match in re.finditer(r'(#.*$|//.*$|/\*.*?\*/)', code_content, re.MULTILINE | re.DOTALL):
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

# --- Funkcje requestów --- #
def get_current_url(endpoint):
    if validate_config_inputs():
        save_config()
    
    if endpoint == "Chat":
        return f"http://{lm_ip_var.get()}:{lm_port_var.get()}/v1/chat/completions"
    else:
        return f"http://{proxy_ip_var.get()}:{proxy_port_var.get()}/v1/agents"

def stream_text_to_log(text, tag='response', chunk_size=3, delay=0.02):
    """
    Wyświetla tekst w logu znak po znaku dla efektu płynnego pisania
    """
    global stop_streaming
    
    log_text.configure(state=tk.NORMAL)
    
    # Znajdź pozycję startu dla kolorowania kodu
    response_start = log_text.index(tk.END)
    
    # Dodaj tekst znak po znaku
    for i in range(0, len(text), chunk_size):
        if stop_streaming:
            break
            
        chunk = text[i:i+chunk_size]
        log_text.insert(tk.END, chunk, tag)
        log_text.see(tk.END)
        log_text.update()
        
        # Małe opóźnienie dla efektu płynnego pisania
        threading.Event().wait(delay)
    
    # Po zakończeniu dodaj nową linię i kolorowanie kodu
    if not stop_streaming:
        log_text.insert(tk.END, "\n\n", tag)
        # Usuń stare przyciski przed dodaniem nowych
        clear_copy_buttons()
        # Dodaj opóźnienie dla pełnego renderowania
        root.after(500, lambda: colorize_python_code(log_text, response_start))
    
    log_text.see(tk.END)
    log_text.configure(state=tk.DISABLED)

def send_request_thread():
    global streaming_active, stop_streaming
    
    streaming_active = True
    send_button.config(state='disabled', text="⏳ Wysyłam...")
    stop_button.config(state='normal', command=stop_stream)
    
    try:
        endpoint = endpoint_var.get()
        text = input_text.get("1.0", tk.END).strip()
        if not text:
            log_text.configure(state=tk.NORMAL)
            log_text.insert(tk.END, "❌ Nie wpisano tekstu!\n", 'error')
            log_text.configure(state=tk.DISABLED)
            return

        url = get_current_url(endpoint)
        
        if endpoint == "Chat":
            body = {"model": "deepseek-coder-v2-lite-instruct",
                    "messages": [{"role": "user", "content": text}],
                    "max_tokens": 4000,
                    "stream": True}  # Włącz streaming
        else:
            body = {"query": text}

        log_text.configure(state=tk.NORMAL)
        log_text.insert(tk.END, f"🔥 Wysyłam do {endpoint}...\n", 'info')
        log_text.see(tk.END)
        log_text.update()
        log_text.configure(state=tk.DISABLED)

        if endpoint == "Chat" and "stream" in body:
            # Obsługa streamingu dla Chat
            with requests.post(url, json=body, timeout=TIMEOUT, stream=True) as response:
                if stop_streaming:
                    return
                    
                response.raise_for_status()
                
                log_text.configure(state=tk.NORMAL)
                log_text.insert(tk.END, f"✅ Odpowiedź:\n", 'success')
                log_text.see(tk.END)
                log_text.update()
                
                response_start = log_text.index(tk.END)
                content_buffer = ""
                
                for line in response.iter_lines():
                    if stop_streaming:
                        log_text.insert(tk.END, "\n[PRZERWANO]\n\n", 'warning')
                        break
                        
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data_str = line[6:]  # Usuń "data: "
                            if data_str.strip() == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if 'choices' in data and len(data['choices']) > 0:
                                    delta = data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        chunk_text = delta['content']
                                        content_buffer += chunk_text
                                        
                                        # Wyświetl znak po znaku
                                        for char in chunk_text:
                                            if stop_streaming:
                                                break
                                            log_text.insert(tk.END, char, 'response')
                                            log_text.see(tk.END)
                                            log_text.update()
                                            threading.Event().wait(0.008)  # Małe opóźnienie
                                            
                            except json.JSONDecodeError:
                                continue
                
                # Po zakończeniu streamingu dodaj kolorowanie
                if not stop_streaming:
                    log_text.insert(tk.END, "\n\n")
                    # Usuń stare przyciski przed dodaniem nowych
                    clear_copy_buttons()
                    # Dodaj opóźnienie dla pełnego renderowania
                    root.after(500, lambda: colorize_python_code(log_text, response_start))
                
                log_text.configure(state=tk.DISABLED)
                
        else:
            # Standardowe żądanie bez streamingu
            response = requests.post(url, json=body, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            # Univerzalne parsowanie odpowiedzi
            content = None
            
            # Sprawdź czy to format Chat API (dla obu endpointów)
            if 'choices' in data and len(data['choices']) > 0:
                if 'message' in data['choices'][0]:
                    content = data['choices'][0]['message']['content']
                elif 'text' in data['choices'][0]:
                    content = data['choices'][0]['text']
            
            # Fallback dla innych formatów
            elif 'response' in data:
                content = data['response']
            elif 'content' in data:
                content = data['content']
            elif 'text' in data:
                content = data['text']
            elif 'answer' in data:
                content = data['answer']
            else:
                # Jeśli nie znamy formatu, wyświetl całą odpowiedź
                content = json.dumps(data, indent=2, ensure_ascii=False)
            
            log_text.configure(state=tk.NORMAL)
            log_text.insert(tk.END, f"✅ Odpowiedź:\n", 'success')
            log_text.see(tk.END)
            log_text.update()
            log_text.configure(state=tk.DISABLED)
            
            # Użyj funkcji streamingu nawet dla zwykłej odpowiedzi
            if content:
                # Usuń stare przyciski przed streamingiem
                clear_copy_buttons()
                stream_text_to_log(content, 'response', chunk_size=2, delay=0.015)
            else:
                clear_copy_buttons()
                stream_text_to_log("Brak treści w odpowiedzi", 'error', chunk_size=2, delay=0.015)

    except requests.exceptions.RequestException as e:
        log_text.configure(state=tk.NORMAL)
        log_text.insert(tk.END, f"❌ Błąd żądania: {e}\n\n", 'error')
        log_text.see(tk.END)
        log_text.configure(state=tk.DISABLED)
    except KeyError as e:
        log_text.configure(state=tk.NORMAL)
        log_text.insert(tk.END, f"❌ Nieprawidłowa odpowiedź od serwera: {e}\n\n", 'error')
        log_text.see(tk.END)
        log_text.configure(state=tk.DISABLED)
    except Exception as e:
        log_text.configure(state=tk.NORMAL)
        log_text.insert(tk.END, f"❌ Nieoczekiwany błąd: {e}\n\n", 'error')
        log_text.see(tk.END)
        log_text.configure(state=tk.DISABLED)
    finally:
        streaming_active = False
        send_button.config(state='normal', text="▶ Wyślij")
        stop_button.config(state='disabled')

# Zmienne globalne dla kontroli streamingu
streaming_active = False
stop_streaming = False

def send_request():
    global streaming_active, stop_streaming
    if not streaming_active:
        stop_streaming = False
        threading.Thread(target=send_request_thread, daemon=True).start()
    
def stop_stream():
    global stop_streaming
    stop_streaming = True

def on_button_enter(event):
    event.widget.config(bg=COLORS['accent_hover'])

def on_button_leave(event):
    event.widget.config(bg=COLORS['accent'])

# --- GUI --- #
root = tk.Tk()
root.title("Proxy - LM Studio Frontend")
root.geometry("1000x900")
root.configure(bg=COLORS['bg_primary'])

style = ttk.Style()
style.theme_use('clam')
style.configure('Dark.TLabel', background=COLORS['bg_primary'], foreground=COLORS['fg_primary'], font=('Consolas', 10))
style.configure('Dark.TButton', background=COLORS['accent'], foreground='white', borderwidth=1, font=('Consolas', 10, 'bold'))
style.map('Dark.TButton', background=[('active', COLORS['accent_hover']), ('pressed', COLORS['accent'])])
style.configure('Dark.TFrame', background=COLORS['bg_primary'])
style.configure('Dark.TCombobox', background=COLORS['bg_input'], foreground=COLORS['fg_primary'], font=('Consolas', 10), fieldbackground=COLORS['bg_input'], selectbackground=COLORS['selection'], selectforeground=COLORS['fg_primary'])
style.configure('Dark.TEntry', fieldbackground=COLORS['bg_input'], foreground=COLORS['fg_primary'], background=COLORS['bg_input'])

root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

main_frame = ttk.Frame(root, style='Dark.TFrame')
main_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
for i in range(12):
    main_frame.rowconfigure(i, weight=1)
main_frame.columnconfigure(0, weight=1)
main_frame.columnconfigure(1, weight=1)
main_frame.columnconfigure(2, weight=1)

# Nagłówek
header_label = ttk.Label(main_frame, text="🚀 Proxy - LM Studio Frontend", style='Dark.TLabel', font=('Consolas', 14, 'bold'))
header_label.grid(row=0, column=0, columnspan=3, sticky='w', pady=(0,10))

# Wyświetl ścieżkę do konfiguracji
config_path_label = ttk.Label(main_frame, text=f"Konfiguracja: {CONFIG_FILE}", style='Dark.TLabel', font=('Consolas', 8))
config_path_label.grid(row=0, column=0, columnspan=3, sticky='e', pady=(0,10))

# --- Endpoint + Status --- #
endpoint_var = tk.StringVar(value="Agent")
status_var = tk.StringVar()

endpoint_frame = ttk.Frame(main_frame, style='Dark.TFrame')
endpoint_frame.grid(row=1, column=0, columnspan=3, sticky='w', pady=(0,10))
endpoint_frame.columnconfigure(0, weight=0)
endpoint_frame.columnconfigure(1, weight=0)
endpoint_frame.columnconfigure(2, weight=1)

endpoint_combo = ttk.Combobox(endpoint_frame, textvariable=endpoint_var, values=["Agent", "Chat"],
                              state="readonly", style='Dark.TCombobox', width=12)
endpoint_combo.grid(row=0, column=0, sticky='w')

status_entry = ttk.Entry(endpoint_frame, textvariable=status_var, width=30, style='Dark.TEntry', state='readonly')
status_entry.grid(row=0, column=1, sticky='w', padx=(10,0))

# --- Tekst wejściowy --- #
ttk.Label(main_frame, text="Tekst do wysłania:", style='Dark.TLabel').grid(row=2, column=0, sticky='w', pady=(10,5), columnspan=3)

input_text = scrolledtext.ScrolledText(main_frame, height=6, bg=COLORS['bg_input'], fg=COLORS['fg_primary'],
                                       insertbackground=COLORS['fg_primary'], selectbackground=COLORS['selection'],
                                       selectforeground=COLORS['fg_primary'], font=('Consolas', 11), relief='flat', borderwidth=1)
input_text.grid(row=3, column=0, columnspan=3, sticky='nsew')

# --- Przyciski --- #
button_frame = ttk.Frame(main_frame, style='Dark.TFrame')
button_frame.grid(row=4, column=0, columnspan=3, sticky='ew', pady=(5,10))
button_frame.columnconfigure(0, weight=1)

# --- Przycisk Clear --- #
clear_button = tk.Button(button_frame, text="🗑 Wyczyść", 
                        command=lambda: (log_text.configure(state=tk.NORMAL), 
                                       log_text.delete(1.0, tk.END),
                                       clear_copy_buttons(),
                                       log_text.insert(tk.END, "🌟 Log wyczyszczony!\n\n", 'info'),
                                       log_text.configure(state=tk.DISABLED)),
                        bg=COLORS['warning'], fg='white', font=('Consolas', 10, 'bold'),
                        relief='flat', borderwidth=0, padx=15, pady=6, cursor='hand2')
clear_button.grid(row=0, column=0, sticky='w')
stop_button = tk.Button(button_frame, text="⏹ Stop", command=lambda: None,
                       bg=COLORS['error'], fg='white', font=('Consolas', 10, 'bold'),
                       relief='flat', borderwidth=0, padx=15, pady=6, cursor='hand2',
                       state='disabled')
stop_button.grid(row=0, column=1, sticky='e', padx=(0,5))

# Przycisk Wyślij
send_button = tk.Button(button_frame, text="▶ Wyślij", command=send_request,
                        bg=COLORS['accent'], fg='white', font=('Consolas', 11, 'bold'),
                        relief='flat', borderwidth=0, padx=20, pady=8, cursor='hand2')
send_button.grid(row=0, column=2, sticky='e')
send_button.bind('<Enter>', on_button_enter)
send_button.bind('<Leave>', on_button_leave)

# --- IP i Port --- #
lm_ip_var = tk.StringVar(value=str(config["lm_studio"]["ip"]))
lm_port_var = tk.StringVar(value=str(config["lm_studio"]["port"]))
proxy_ip_var = tk.StringVar(value=str(config["proxy_agent"]["ip"]))
proxy_port_var = tk.StringVar(value=str(config["proxy_agent"]["port"]))

# LM Studio w jednej linii
lm_row = ttk.Frame(main_frame, style='Dark.TFrame')
lm_row.grid(row=5, column=0, columnspan=3, sticky='w', pady=(5,2))
ttk.Label(lm_row, text="LM Studio IP:", style='Dark.TLabel').grid(row=0, column=0, sticky='w')
ttk.Entry(lm_row, textvariable=lm_ip_var, width=15, style='Dark.TEntry').grid(row=0, column=1, sticky='w', padx=(2,6))
ttk.Label(lm_row, text="Port:", style='Dark.TLabel').grid(row=0, column=2, sticky='w')
ttk.Entry(lm_row, textvariable=lm_port_var, width=5, style='Dark.TEntry').grid(row=0, column=3, sticky='w', padx=(2,0))

# Proxy Agent w jednej linii
proxy_row = ttk.Frame(main_frame, style='Dark.TFrame')
proxy_row.grid(row=6, column=0, columnspan=3, sticky='w', pady=(5,2))
ttk.Label(proxy_row, text="Proxy Agent IP:", style='Dark.TLabel').grid(row=0, column=0, sticky='w')
ttk.Entry(proxy_row, textvariable=proxy_ip_var, width=15, style='Dark.TEntry').grid(row=0, column=1, sticky='w', padx=(2,6))
ttk.Label(proxy_row, text="Port:", style='Dark.TLabel').grid(row=0, column=2, sticky='w')
ttk.Entry(proxy_row, textvariable=proxy_port_var, width=5, style='Dark.TEntry').grid(row=0, column=3, sticky='w', padx=(2,0))

# --- Logi / Odpowiedź --- #
ttk.Label(main_frame, text="Odpowiedź:", style='Dark.TLabel').grid(row=9, column=0, sticky='w', pady=(10,5), columnspan=3)

log_text = scrolledtext.ScrolledText(main_frame, bg=COLORS['bg_input'], fg=COLORS['fg_primary'], insertbackground=COLORS['fg_primary'],
                                     selectbackground=COLORS['selection'], selectforeground=COLORS['fg_primary'], font=('Consolas', 10),
                                     relief='flat', borderwidth=1, wrap=tk.WORD)
log_text.grid(row=10, column=0, columnspan=3, sticky='nsew')

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
log_text.configure(state=tk.DISABLED)

# --- Bind Ctrl+Enter --- #
def on_enter_key(event):
    if event.state & 0x4:
        send_request()
        return 'break'
input_text.bind('<Control-Return>', on_enter_key)
input_text.focus_set()

# --- Aktualizacja tytułu i statusu --- #
def update_title():
    ep = endpoint_var.get()
    if ep == "Chat":
        ip = lm_ip_var.get()
        port = lm_port_var.get()
    else:
        ip = proxy_ip_var.get()
        port = proxy_port_var.get()
    root.title(f"Proxy - LM Studio Frontend [{ep} {ip}:{port}]")
    status_var.set(f"{ep} {ip}:{port}")

endpoint_var.trace_add("write", lambda *args: update_title())
lm_ip_var.trace_add("write", lambda *args: update_title())
lm_port_var.trace_add("write", lambda *args: update_title())
proxy_ip_var.trace_add("write", lambda *args: update_title())
proxy_port_var.trace_add("write", lambda *args: update_title())
update_title()

# --- Wiadomość powitalna --- #
log_text.configure(state=tk.NORMAL)
log_text.insert(tk.END, "🌟 Proxy - LM Studio Frontend gotowy do pracy!\n", 'success')
log_text.insert(tk.END, "💡 Tip: Użyj Ctrl+Enter aby wysłać zapytanie\n", 'info')
log_text.insert(tk.END, f"📁 Konfiguracja: {CONFIG_FILE}\n\n", 'info')
log_text.configure(state=tk.DISABLED)

root.mainloop()