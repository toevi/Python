import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import requests
import json
import threading
from datetime import datetime
import os

class LMStudioChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("LM Studio Chat Client")
        self.root.geometry("900x700")
        
        # Konfiguracja
        self.api_base = "http://localhost:1234/v1"
        self.current_model = None
        self.chat_history = []
        
        # Tworzenie interfejsu
        self.create_widgets()
        self.load_models()
        self.load_chat_history()
        
    def create_widgets(self):
        # Frame górny - konfiguracja
        config_frame = ttk.Frame(self.root, padding="10")
        config_frame.pack(fill=tk.X)
        
        # Serwer i port
        ttk.Label(config_frame, text="Serwer:").grid(row=0, column=0, sticky=tk.W)
        self.server_var = tk.StringVar(value="localhost:1234")
        server_entry = ttk.Entry(config_frame, textvariable=self.server_var, width=20)
        server_entry.grid(row=0, column=1, padx=5)
        
        # Przycisk połączenia
        connect_btn = ttk.Button(config_frame, text="Połącz", command=self.connect_to_server)
        connect_btn.grid(row=0, column=2, padx=5)
        
        # Status połączenia
        self.status_var = tk.StringVar(value="Nie połączono")
        status_label = ttk.Label(config_frame, textvariable=self.status_var, foreground="red")
        status_label.grid(row=0, column=3, padx=10)
        
        # Wybór modelu
        ttk.Label(config_frame, text="Model:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(config_frame, textvariable=self.model_var, width=30, state="readonly")
        self.model_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W)
        
        # Odświeżanie modeli
        refresh_btn = ttk.Button(config_frame, text="Odśwież modele", command=self.load_models)
        refresh_btn.grid(row=1, column=3, padx=5)
        
        # Frame środkowy - chat
        chat_frame = ttk.Frame(self.root, padding="10")
        chat_frame.pack(fill=tk.BOTH, expand=True)
        
        # Historia chatu
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, 
            wrap=tk.WORD, 
            width=80, 
            height=25,
            font=("Consolas", 10),
            state=tk.DISABLED
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Konfiguracja kolorów dla chatu
        self.chat_display.tag_config("user", foreground="blue", font=("Consolas", 10, "bold"))
        self.chat_display.tag_config("assistant", foreground="green")
        self.chat_display.tag_config("system", foreground="gray", font=("Consolas", 9, "italic"))
        
        # Frame dolny - input
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X)
        
        # Pole tekstowe do wpisywania
        self.message_text = scrolledtext.ScrolledText(
            input_frame, 
            wrap=tk.WORD, 
            width=70, 
            height=4,
            font=("Consolas", 10)
        )
        self.message_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Frame przycisków
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Przyciski
        send_btn = ttk.Button(button_frame, text="Wyślij", command=self.send_message)
        send_btn.pack(fill=tk.X, pady=2)
        
        clear_btn = ttk.Button(button_frame, text="Wyczyść", command=self.clear_chat)
        clear_btn.pack(fill=tk.X, pady=2)
        
        save_btn = ttk.Button(button_frame, text="Zapisz", command=self.save_chat_to_file)
        save_btn.pack(fill=tk.X, pady=2)
        
        load_btn = ttk.Button(button_frame, text="Wczytaj", command=self.load_chat_from_file)
        load_btn.pack(fill=tk.X, pady=2)
        
        # Skróty klawiszowe
        self.message_text.bind("<Control-Return>", lambda e: self.send_message())
        self.root.bind("<Control-s>", lambda e: self.save_chat_to_file())
        
    def connect_to_server(self):
        """Połączenie z serwerem LM Studio"""
        server = self.server_var.get()
        self.api_base = f"http://{server}/v1"
        
        try:
            response = requests.get(f"{self.api_base}/models", timeout=5)
            if response.status_code == 200:
                self.status_var.set("Połączono")
                self.status_var.set("Połączono ✓")
                # Zmiana koloru na zielony (może wymagać dodatkowego Label)
                self.load_models()
                self.add_system_message(f"Połączono z serwerem: {server}")
            else:
                raise requests.RequestException(f"Status: {response.status_code}")
        except requests.RequestException as e:
            self.status_var.set("Błąd połączenia")
            messagebox.showerror("Błąd", f"Nie można połączyć z serwerem:\n{e}")
    
    def load_models(self):
        """Ładowanie dostępnych modeli"""
        try:
            response = requests.get(f"{self.api_base}/models", timeout=5)
            if response.status_code == 200:
                models_data = response.json()
                models = [model["id"] for model in models_data.get("data", [])]
                self.model_combo["values"] = models
                if models:
                    self.model_combo.set(models[0])
                    self.current_model = models[0]
                    self.add_system_message(f"Załadowano {len(models)} modeli")
            else:
                self.add_system_message("Błąd podczas ładowania modeli")
        except requests.RequestException:
            self.add_system_message("Brak połączenia z serwerem")
    
    def send_message(self):
        """Wysyłanie wiadomości do AI"""
        message = self.message_text.get("1.0", tk.END).strip()
        if not message:
            return
        
        if not self.model_var.get():
            messagebox.showwarning("Uwaga", "Wybierz model przed wysłaniem wiadomości")
            return
        
        # Wyświetl wiadomość użytkownika
        self.add_user_message(message)
        self.message_text.delete("1.0", tk.END)
        
        # Dodaj do historii
        self.chat_history.append({"role": "user", "content": message, "timestamp": datetime.now()})
        
        # Wyślij do AI w osobnym wątku
        threading.Thread(target=self.get_ai_response, args=(message,), daemon=True).start()
    
    def get_ai_response(self, user_message):
        """Otrzymywanie odpowiedzi od AI"""
        try:
            # Przygotuj historię dla API
            messages = [{"role": msg["role"], "content": msg["content"]} 
                       for msg in self.chat_history[-10:]]  # Ostatnie 10 wiadomości
            
            payload = {
                "model": self.model_var.get(),
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000,
                "stream": False
            }
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                ai_response = data["choices"][0]["message"]["content"]
                
                # Wyświetl odpowiedź AI
                self.root.after(0, self.add_ai_message, ai_response)
                
                # Dodaj do historii
                self.chat_history.append({
                    "role": "assistant", 
                    "content": ai_response, 
                    "timestamp": datetime.now()
                })
                
                # Zapisz historię
                self.root.after(0, self.save_chat_history)
            else:
                error_msg = f"Błąd API: {response.status_code}"
                self.root.after(0, self.add_system_message, error_msg)
                
        except requests.RequestException as e:
            error_msg = f"Błąd połączenia: {str(e)}"
            self.root.after(0, self.add_system_message, error_msg)
    
    def add_user_message(self, message):
        """Dodaj wiadomość użytkownika do wyświetlania"""
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] Ty: ", "user")
        self.chat_display.insert(tk.END, f"{message}\n\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def add_ai_message(self, message):
        """Dodaj odpowiedź AI do wyświetlania"""
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        model_name = self.model_var.get() or "AI"
        self.chat_display.insert(tk.END, f"[{timestamp}] {model_name}: ", "assistant")
        self.chat_display.insert(tk.END, f"{message}\n\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def add_system_message(self, message):
        """Dodaj wiadomość systemową"""
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] System: {message}\n", "system")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def clear_chat(self):
        """Wyczyść okno chatu"""
        if messagebox.askyesno("Potwierdzenie", "Czy na pewno chcesz wyczyścić chat?"):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.chat_history.clear()
            self.add_system_message("Chat wyczyszczony")
    
    def save_chat_history(self):
        """Zapisz historię chatu do pliku JSON"""
        try:
            if not os.path.exists("chat_history"):
                os.makedirs("chat_history")
            
            history_data = []
            for msg in self.chat_history:
                history_data.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["timestamp"].isoformat()
                })
            
            filename = f"chat_history/chat_{datetime.now().strftime('%Y%m%d')}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.add_system_message(f"Błąd zapisu historii: {e}")
    
    def load_chat_history(self):
        """Wczytaj historię chatu z dzisiejszego pliku"""
        try:
            filename = f"chat_history/chat_{datetime.now().strftime('%Y%m%d')}.json"
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
                
                self.chat_history.clear()
                for msg in history_data:
                    self.chat_history.append({
                        "role": msg["role"],
                        "content": msg["content"],
                        "timestamp": datetime.fromisoformat(msg["timestamp"])
                    })
                
                # Wyświetl ostatnie wiadomości
                for msg in self.chat_history[-10:]:  # Ostatnie 10
                    if msg["role"] == "user":
                        self.add_user_message(msg["content"])
                    else:
                        self.add_ai_message(msg["content"])
                        
                if self.chat_history:
                    self.add_system_message(f"Wczytano historię: {len(self.chat_history)} wiadomości")
                    
        except Exception as e:
            pass  # Ignoruj błędy ładowania - może nie ma historii
    
    def save_chat_to_file(self):
        """Zapisz chat do wybranego pliku"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Pliki tekstowe", "*.txt"), ("Pliki JSON", "*.json"), ("Wszystkie pliki", "*.*")]
        )
        
        if filename:
            try:
                if filename.endswith(".json"):
                    # Zapisz jako JSON
                    history_data = []
                    for msg in self.chat_history:
                        history_data.append({
                            "role": msg["role"],
                            "content": msg["content"],
                            "timestamp": msg["timestamp"].isoformat()
                        })
                    
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(history_data, f, ensure_ascii=False, indent=2)
                else:
                    # Zapisz jako tekst
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(f"Chat LM Studio - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write("="*50 + "\n\n")
                        
                        for msg in self.chat_history:
                            timestamp = msg["timestamp"].strftime("%H:%M:%S")
                            role = "Ty" if msg["role"] == "user" else "AI"
                            f.write(f"[{timestamp}] {role}: {msg['content']}\n\n")
                
                self.add_system_message(f"Chat zapisany: {filename}")
                
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie można zapisać pliku:\n{e}")
    
    def load_chat_from_file(self):
        """Wczytaj chat z pliku"""
        filename = filedialog.askopenfilename(
            filetypes=[("Pliki JSON", "*.json"), ("Wszystkie pliki", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
                
                if messagebox.askyesno("Potwierdzenie", "Czy wyczyścić obecny chat przed wczytaniem?"):
                    self.clear_chat()
                
                self.chat_history.clear()
                for msg in history_data:
                    self.chat_history.append({
                        "role": msg["role"],
                        "content": msg["content"],
                        "timestamp": datetime.fromisoformat(msg["timestamp"])
                    })
                
                # Wyświetl wczytane wiadomości
                for msg in self.chat_history:
                    if msg["role"] == "user":
                        self.add_user_message(msg["content"])
                    else:
                        self.add_ai_message(msg["content"])
                
                self.add_system_message(f"Wczytano chat: {len(self.chat_history)} wiadomości")
                
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie można wczytać pliku:\n{e}")

def main():
    root = tk.Tk()
    app = LMStudioChatClient(root)
    root.mainloop()

if __name__ == "__main__":
    main()