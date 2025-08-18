import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import subprocess
import os
import re
import threading
import time

# Próba zaimportowania tkinterdnd2 dla funkcji "przeciągnij i upuść"
try:
    from tkinterdnd2 import TkinterDnD
    is_dnd_supported = True
    _TkBase = TkinterDnD.Tk
except ImportError:
    is_dnd_supported = False
    _TkBase = tk.Tk

# Próba zaimportowania jedi
try:
    import jedi
    is_jedi_supported = True
except ImportError:
    is_jedi_supported = False
    messagebox.showwarning("Brak biblioteki", "Biblioteka 'jedi' nie została znaleziona. Podpowiedzi kodu nie będą działać.")

class PythonEditor(_TkBase):  # type: ignore
    def __init__(self):
        super().__init__()
        self.title("Prosty Edytor Pythona")
        self.geometry("1000x800")
        self.file_path = None
        self.unsaved_changes = False
        
        self.last_dot_time = 0
        self.script = None
        self.autocomplete_window = None
        self.last_key_press_time = 0
        
        self.setup_ui()
        self.bind_shortcuts()
        if is_dnd_supported:
            self.setup_drag_and_drop()
        
        self.after(100, self.update_line_numbers)
        self.text_widget.bind("<<Modified>>", self.schedule_update)
        self.text_widget.bind("<KeyRelease>", self.highlight_syntax_and_whitespace_and_check_errors)
        self.text_widget.bind("<Button-1>", self.update_line_numbers_and_hide_autocomplete)
        self.text_widget.bind("<Configure>", self.update_line_numbers)
        self.text_widget.bind("<MouseWheel>", self.update_line_numbers)
        self.text_widget.bind("<Key>", self.handle_key_press)
        self.text_widget.bind("<Tab>", self.handle_tab_key)
        self.text_widget.bind("<Motion>", self.highlight_matching_delimiters)
        self.text_widget.bind("<Return>", self.handle_return_key)
        
        # Nowe wiązanie do sprawdzania niezapisanych zmian przy zamykaniu
        self.protocol("WM_DELETE_WINDOW", self.check_for_unsaved_changes)

    def setup_ui(self):
        """Konfiguruje interfejs użytkownika edytora."""
        
        self.bg_color = "#1e1e1e"
        self.fg_color = "#d4d4d4"
        self.line_num_bg = "#2c2c2c"
        self.line_num_fg = "#9e9e9e"
        self.selection_bg = "#264f78"
        self.indent_bg = "#3e3e3e"
        self.error_bg = "#ff6347"

        # Kontener na edytor tekstu i numery linii
        editor_frame = tk.Frame(self, bg=self.bg_color)
        editor_frame.pack(fill="both", expand=True)

        self.line_number_bar = tk.Text(editor_frame, width=4, padx=5, takefocus=0, border=0,
                                       background=self.line_num_bg, foreground=self.line_num_fg,
                                       font=("Consolas", 12))
        self.line_number_bar.pack(side="left", fill="y")
        self.line_number_bar.config(state="disabled")

        self.text_widget = tk.Text(editor_frame, wrap="word", undo=True,
                                   background=self.bg_color, foreground=self.fg_color,
                                   insertbackground="white", border=0,
                                   selectbackground=self.selection_bg,
                                   font=("Consolas", 12))
        self.text_widget.pack(side="left", fill="both", expand=True)

        self.scrollbar = tk.Scrollbar(editor_frame, command=self.on_scroll)
        self.scrollbar.pack(side="right", fill="y")
        self.text_widget.config(yscrollcommand=self.on_yscroll)
        
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Plik", menu=file_menu)
        file_menu.add_command(label="Nowy", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Otwórz...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Zapisz", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Zapisz jako...", command=self.save_as_file, accelerator="Ctrl+Shift+S")
        file_menu.add_command(label="Wyjście", command=self.check_for_unsaved_changes, accelerator="Ctrl+Q")
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edycja", menu=edit_menu)
        edit_menu.add_command(label="Cofnij", command=self.text_widget.edit_undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Ponów", command=self.text_widget.edit_redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Wytnij", command=self.cut_text, accelerator="Ctrl+X")
        edit_menu.add_command(label="Kopiuj", command=self.copy_text, accelerator="Ctrl+C")
        edit_menu.add_command(label="Wklej", command=self.paste_text, accelerator="Ctrl+V")

        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Uruchom", menu=run_menu)
        run_menu.add_command(label="Uruchom program", command=self.run_code, accelerator="F5")
        
        self.setup_syntax_highlighting()
        
        self.status_bar = tk.Label(self, text="Gotowy", bd=1, relief="sunken", anchor="w",
                                   bg=self.bg_color, fg=self.fg_color)
        self.status_bar.pack(side="bottom", fill="x")

        self.error_bar = tk.Label(self, text="", bd=1, relief="sunken", anchor="w",
                                  bg=self.bg_color, fg=self.fg_color)
        self.error_bar.pack(side="bottom", fill="x")
        
        # Menu podręczne
        self.popup_menu = tk.Menu(self, tearoff=0)
        self.popup_menu.add_command(label="Wytnij", command=self.cut_text)
        self.popup_menu.add_command(label="Kopiuj", command=self.copy_text)
        self.popup_menu.add_command(label="Wklej", command=self.paste_text)
        self.text_widget.bind("<Button-3>", self.show_popup_menu)
        
    def check_for_unsaved_changes(self):
        """Sprawdza, czy są niezapisane zmiany i pyta o ich zapisanie przed zamknięciem."""
        if self.unsaved_changes:
            response = messagebox.askyesnocancel("Niezapisane zmiany", "Czy chcesz zapisać zmiany przed wyjściem?")
            if response is None:  # Cancel
                return
            elif response:  # Yes
                self.save_file()
                if self.unsaved_changes:  # If save_file failed (e.g. user canceled save_as)
                    return
        self.destroy()

    def set_unsaved_changes(self, modified=True):
        """Ustawia flagę niezapisanych zmian i aktualizuje tytuł okna."""
        self.unsaved_changes = modified
        title = self.file_path if self.file_path else "Nowy Plik"
        if self.unsaved_changes:
            self.title(f"Prosty Edytor Pythona - {os.path.basename(title)}*")
        else:
            self.title(f"Prosty Edytor Pythona - {os.path.basename(title)}")
    
    def highlight_matching_delimiters(self, event=None):
        # pylint: disable=unused-argument
        """Podświetla dopasowane nawiasy, klamry i cudzysłowy."""
        self.text_widget.tag_remove("delimiter", "1.0", "end")
        
        cursor_index = self.text_widget.index(tk.INSERT)
        char = self.text_widget.get(cursor_index + "-1c")

        # Nawiasy i klamry
        if char in "([{":
            matching_char = { "(": ")", "[": "]", "{": "}" }[char]
            count = 1
            pos = cursor_index
            while count > 0 and pos != "end":
                pos = self.text_widget.search(r"[\(\[\{\)\]\}]", pos + "+1c", stopindex="end", regexp=True)
                if not pos:
                    break
                
                next_char = self.text_widget.get(pos)
                if next_char == matching_char:
                    count -= 1
                elif next_char in "([{":
                    count += 1
            if pos:
                self.text_widget.tag_add("delimiter", cursor_index + "-1c", cursor_index)
                self.text_widget.tag_add("delimiter", pos)

        # Cudzysłowy
        elif char in "'\"":
            matching_char = char
            start_index = self.text_widget.search(f"{matching_char}", "1.0", tk.INSERT, backwards=True)
            if start_index:
                if self.text_widget.get(start_index + "+1c") == matching_char:
                    return

                end_index = self.text_widget.search(f"{matching_char}", tk.INSERT, "end")
                if end_index:
                    self.text_widget.tag_add("delimiter", start_index)
                    self.text_widget.tag_add("delimiter", end_index)
    
    def handle_key_press(self, event):
        # pylint: disable=unused-argument
        """Obsługuje naciśnięcia klawiszy, w tym podpowiedzi i automatyczne parowanie."""
        self.handle_auto_pair_and_indent(event)
        
        if not is_jedi_supported:
            return

        self.set_unsaved_changes()
        
        current_time = time.time()
        # Wyzwalanie podpowiedzi po kropce lub literze
        if event.char and (event.char == "." or event.char.isalnum() or event.char == "_"):
            self.last_dot_time = current_time
            line, col = map(int, self.text_widget.index(tk.INSERT).split('.'))
            code = self.text_widget.get("1.0", tk.END)

            threading.Thread(target=self.get_completions_in_thread, args=(code, line, col)).start()
        else:
            self.hide_autocomplete_suggestions()

    def get_completions_in_thread(self, code, line, col):
        """Pobiera podpowiedzi od Jedi w osobnym wątku."""
        try:
            script = jedi.Script(code)
            completions = script.complete(line, col)
            self.after_idle(self.show_autocomplete_suggestions, completions)
        except Exception:
            self.after_idle(self.hide_autocomplete_suggestions)

    def show_autocomplete_suggestions(self, completions):
        """Tworzy i wyświetla okno z podpowiedziami."""
        self.hide_autocomplete_suggestions()

        if not completions:
            return

        cursor_pos = self.text_widget.index(tk.INSERT)
        x, y, _, _ = self.text_widget.bbox(cursor_pos)
        x_root = self.winfo_rootx() + x
        y_root = self.winfo_rooty() + y + 20

        self.autocomplete_window = tk.Toplevel(self)
        self.autocomplete_window.wm_overrideredirect(True)
        self.autocomplete_window.geometry(f"+{x_root}+{y_root}")
        
        listbox = tk.Listbox(self.autocomplete_window, bg=self.bg_color, fg=self.fg_color, selectbackground=self.selection_bg, border=0)
        listbox.pack(fill="both", expand=True)
        
        for completion in completions:
            listbox.insert(tk.END, completion.name)
        
        listbox.bind("<<ListboxSelect>>", self.insert_autocomplete_suggestion_from_listbox)
        listbox.bind("<Return>", self.insert_autocomplete_suggestion_from_listbox)
        listbox.bind("<Escape>", lambda event: self.hide_autocomplete_suggestions())

    def insert_autocomplete_suggestion_from_listbox(self, event):
        # pylint: disable=unused-argument
        """Wstawia wybraną podpowiedź do edytora z listy."""
        if not self.autocomplete_window:
            return
        
        try:
            selected_indices = event.widget.curselection()
            if not selected_indices:
                return
            
            selected_item = event.widget.get(selected_indices[0])
            
            current_word_start = self.text_widget.index(tk.INSERT + " wordstart")
            self.text_widget.delete(current_word_start, tk.INSERT)
            self.text_widget.insert(tk.INSERT, selected_item)
            
            self.hide_autocomplete_suggestions()
            
        except tk.TclError:
            pass

    def hide_autocomplete_suggestions(self):
        """Ukrywa okno z podpowiedziami."""
        if self.autocomplete_window:
            self.autocomplete_window.destroy()
            self.autocomplete_window = None

    def update_line_numbers_and_hide_autocomplete(self, event=None):
        # pylint: disable=unused-argument
        self.update_line_numbers()
        self.hide_autocomplete_suggestions()

    def show_popup_menu(self, event):
        # pylint: disable=unused-argument
        """Wyświetla menu podręczne w miejscu kliknięcia."""
        self.popup_menu.post(event.x_root, event.y_yroot)

    def cut_text(self):
        self.text_widget.event_generate("<<Cut>>")
        self.set_unsaved_changes()

    def copy_text(self):
        self.text_widget.event_generate("<<Copy>>")

    def paste_text(self):
        self.text_widget.event_generate("<<Paste>>")
        self.set_unsaved_changes()

    def handle_auto_pair_and_indent(self, event):
        # pylint: disable=unused-argument
        """Wstawia pasujące nawiasy/cudzysłowy i skacze po nich."""
        
        self.set_unsaved_changes()
        
        # Automatyczne parowanie nawiasów
        if event.char in ['(', '[', '{', "'", '"']:
            pair_map = {'(': ')', '[': ']', '{': '}', "'": "'", '"': '"'}
            self.text_widget.insert(tk.INSERT, pair_map[event.char])
            self.text_widget.mark_set(tk.INSERT, "insert-1c")
            return "break"
        
        # Skok po nawiasie, jeśli następny znak to pasujący nawias
        if event.keysym in ['parenright', 'bracketright', 'braceright']:
            next_char = self.text_widget.get("insert", "insert+1c")
            if next_char == event.char:
                self.text_widget.mark_set(tk.INSERT, "insert+1c")
                return "break"

    def handle_return_key(self, event):
        # pylint: disable=unused-argument
        """Wstawia wcięcie po Enter."""
        self.set_unsaved_changes()
        line_start_index = self.text_widget.index(f"{tk.INSERT} linestart")
        line_end_index = self.text_widget.index(f"{tk.INSERT} lineend")
        current_line = self.text_widget.get(line_start_index, line_end_index)
        
        # Wstaw nowy wiersz
        self.text_widget.insert(tk.INSERT, '\n')
        
        # Znajdź bieżące wcięcie
        indent = re.match(r'^\s*', current_line)
        if indent: # type: ignore
            indent_str = indent.group()
        else:
            indent_str = ""
        
        # Dodaj dodatkowe wcięcie po dwukropku
        if current_line.strip().endswith(':'):
            indent_str += "    "
        
        self.text_widget.insert(tk.INSERT, indent_str)
        self.update_line_numbers()
        
        return "break"

    def handle_tab_key(self, event):
        # pylint: disable=unused-argument
        """Wstawia 4 spacje zamiast tabulatora."""
        self.text_widget.insert(tk.INSERT, "    ")
        self.set_unsaved_changes()
        return "break"

    def setup_syntax_highlighting(self):
        """Konfiguruje tagi do podświetlania składni (jak w VS Code)."""
        self.text_widget.tag_configure("keyword", foreground="#c586c0")
        self.text_widget.tag_configure("string", foreground="#d69d85")
        self.text_widget.tag_configure("comment", foreground="#6a9955")
        self.text_widget.tag_configure("number", foreground="#b5cea8")
        self.text_widget.tag_configure("function", foreground="#dcdcaa")
        self.text_widget.tag_configure("class", foreground="#4ec9b0")
        self.text_widget.tag_configure("self", foreground="#d7ba7d", font=("Consolas", 12, "italic"))
        self.text_widget.tag_configure("delimiters", foreground="#d4d4d4")
        self.text_widget.tag_configure("indent", background=self.indent_bg)
        self.text_widget.tag_configure("syntax_error", background="#ff6347", foreground="white")
        self.text_widget.tag_configure("delimiter", background="#3a3a3a")
        
    def setup_drag_and_drop(self):
        """Konfiguruje obsługę przeciągnij i upuść (Drag and Drop)."""
        self.text_widget.drop_target_register(1) # pylint: disable=no-member
        self.text_widget.dnd_bind('<<Drop>>', self.handle_dnd_drop) # pylint: disable=no-member

    def handle_dnd_drop(self, event):
        # pylint: disable=unused-argument
        """Obsługuje upuszczenie pliku na edytor."""
        file_path = event.data
        if os.path.isfile(file_path) and file_path.endswith('.py'):
            self.open_file_by_path(file_path)
        else:
            messagebox.showwarning("Błąd", "Możesz upuścić tylko plik Pythona (.py).")

    def open_file_by_path(self, path):
        """Otwiera plik o podanej ścieżce."""
        if self.unsaved_changes:
            response = messagebox.askyesnocancel("Niezapisane zmiany", "Czy chcesz zapisać zmiany w bieżącym pliku?")
            if response is None:
                return
            if response:
                self.save_file()
        
        try:
            with open(path, "r", encoding="utf-8") as file:
                code = file.read()
                self.text_widget.delete("1.0", tk.END)
                self.text_widget.insert("1.0", code)
            self.file_path = path
            self.set_unsaved_changes(False)
            self.title(f"Prosty Edytor Pythona - {os.path.basename(self.file_path)}")
            self.status_bar.config(text=f"Otwarto: {self.file_path}")
            self.highlight_syntax_and_whitespace_and_check_errors()
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się otworzyć pliku: {e}")

    def highlight_syntax_and_whitespace_and_check_errors(self, event=None):
        # pylint: disable=unused-argument
        """Podświetla składnię, wizualizuje wcięcia i sprawdza błędy."""
        self.highlight_syntax()
        self.visualize_whitespace()
        self.check_syntax_error()

    def highlight_syntax(self):
        """Podświetla składnię w czasie rzeczywistym."""
        code = self.text_widget.get("1.0", tk.END)
        self.text_widget.mark_set("range_start", "1.0")
        
        for tag in ["keyword", "string", "comment", "number", "function", "class", "self", "delimiters"]:
            self.text_widget.tag_remove(tag, "1.0", tk.END)
        
        lines = code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            comment_match = re.search(r'#.*', line)
            if comment_match:
                start, end = comment_match.span()
                self.text_widget.tag_add("comment", f"{line_num}.{start}", f"{line_num}.{end}")
            
            # Podświetlanie słów kluczowych, self, liczb, nawiasów i operatorów
            for match in re.finditer(r'\b\w+\b|\S', line):
                word = match.group()
                if word in ["def"]:
                    start_pos = f"{line_num}.{match.start()}"
                    end_pos = f"{line_num}.{match.end()}"
                    self.text_widget.tag_add("keyword", start_pos, end_pos)
                    
                    # Dodatkowe podświetlanie nazwy funkcji
                    func_name_match = re.search(r'\bdef\s+([_a-zA-Z]\w*)\s*\(', line)
                    if func_name_match:
                        start_pos = f"{line_num}.{func_name_match.start(1)}"
                        end_pos = f"{line_num}.{func_name_match.end(1)}"
                        self.text_widget.tag_add("function", start_pos, end_pos)
                        
                elif word in ["class"]:
                    start_pos = f"{line_num}.{match.start()}"
                    end_pos = f"{line_num}.{match.end()}"
                    self.text_widget.tag_add("keyword", start_pos, end_pos)
                    
                    # Dodatkowe podświetlanie nazwy klasy
                    class_name_match = re.search(r'\bclass\s+([_a-zA-Z]\w*)', line)
                    if class_name_match:
                        start_pos = f"{line_num}.{class_name_match.start(1)}"
                        end_pos = f"{line_num}.{class_name_match.end(1)}"
                        self.text_widget.tag_add("class", start_pos, end_pos)
                
                elif word in ["__init__", "None"]:
                    start_pos = f"{line_num}.{match.start()}"
                    end_pos = f"{line_num}.{match.end()}"
                    self.text_widget.tag_add("function", start_pos, end_pos)
                
                elif word in ["if", "else", "elif", "for", "while", "import", "from", "as", "return", "True", "False"]:
                    start_pos = f"{line_num}.{match.start()}"
                    end_pos = f"{line_num}.{match.end()}"
                    self.text_widget.tag_add("keyword", start_pos, end_pos)
                
                elif word == 'self':
                    start_pos = f"{line_num}.{match.start()}"
                    end_pos = f"{line_num}.{match.end()}"
                    self.text_widget.tag_add("self", start_pos, end_pos)
                
                elif re.match(r'^\d+(\.\d*)?$', word):
                    start_pos = f"{line_num}.{match.start()}"
                    end_pos = f"{line_num}.{match.end()}"
                    self.text_widget.tag_add("number", start_pos, end_pos)
                
                elif word in '()[]{},:.+-*/%':
                    start_pos = f"{line_num}.{match.start()}"
                    end_pos = f"{line_num}.{match.end()}"
                    self.text_widget.tag_add("delimiters", start_pos, end_pos)

    def visualize_whitespace(self):
        """Wizualizuje wcięcia i tabulatory."""
        self.text_widget.tag_remove("indent", "1.0", "end")
        
        for line_num in range(1, int(self.text_widget.index(tk.END).split('.')[0])):
            line_text = self.text_widget.get(f"{line_num}.0", f"{line_num}.end")
            
            indent_length = len(line_text) - len(line_text.lstrip())
            if indent_length > 0:
                self.text_widget.tag_add("indent", f"{line_num}.0", f"{line_num}.{indent_length}")

    def check_syntax_error(self):
        """Sprawdza błędy składni w kodzie i je podświetla."""
        code = self.text_widget.get("1.0", tk.END)
        self.text_widget.tag_remove("syntax_error", "1.0", "end")
        self.error_bar.config(text="", bg=self.bg_color, fg=self.fg_color)
        
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            line_num = e.lineno
            self.text_widget.tag_add("syntax_error", f"{line_num}.0", f"{line_num}.end")
            self.error_bar.config(text=f"Błąd składni w linii {line_num}: {e.msg}", bg=self.error_bg, fg="white")
            
    def bind_shortcuts(self):
        """Przypisuje skróty klawiaturowe do operacji."""
        self.bind("<Control-n>", lambda event: self.new_file())
        self.bind("<Control-o>", lambda event: self.open_file())
        self.bind("<Control-s>", lambda event: self.save_file())
        self.bind("<Control-Shift-s>", lambda event: self.save_as_file())
        self.bind("<Control-z>", lambda event: self.text_widget.edit_undo())
        self.bind("<Control-y>", lambda event: self.text_widget.edit_redo())
        self.bind("<F5>", lambda event: self.run_code())
        self.bind("<Control-x>", lambda event: self.cut_text())
        self.bind("<Control-c>", lambda event: self.copy_text())
        self.bind("<Control-v>", lambda event: self.paste_text())
        self.bind("<Control-q>", lambda event: self.check_for_unsaved_changes())

    def new_file(self):
        """Tworzy nowy, pusty plik."""
        if self.unsaved_changes:
            response = messagebox.askyesnocancel("Niezapisane zmiany", "Czy chcesz zapisać zmiany w bieżącym pliku?")
            if response is None:
                return
            if response:
                self.save_file()

        self.text_widget.delete("1.0", tk.END)
        self.file_path = None
        self.set_unsaved_changes(False)
        self.title("Prosty Edytor Pythona - Nowy Plik")
        self.status_bar.config(text="Nowy plik")
        self.error_bar.config(text="", bg=self.bg_color, fg=self.fg_color)

    def open_file(self):
        """Otwiera istniejący plik."""
        self.file_path = filedialog.askopenfilename(defaultextension=".py",
                                                    filetypes=[("Pliki Pythona", "*.py"), ("Wszystkie pliki", "*.*")])
        if self.file_path:
            self.open_file_by_path(self.file_path)

    def save_file(self):
        """Zapisuje bieżący plik."""
        if self.file_path:
            with open(self.file_path, "w", encoding="utf-8") as file:
                file.write(self.text_widget.get("1.0", tk.END))
            self.status_bar.config(text=f"Zapisano: {self.file_path}")
            self.set_unsaved_changes(False)
        else:
            self.save_as_file()

    def save_as_file(self):
        """Zapisuje plik pod nową nazwą."""
        self.file_path = filedialog.asksaveasfilename(defaultextension=".py",
                                                      filetypes=[("Pliki Pythona", "*.py"), ("Wszystkie pliki", "*.*")])
        if self.file_path:
            with open(self.file_path, "w", encoding="utf-8") as file:
                file.write(self.text_widget.get("1.0", tk.END))
            self.set_unsaved_changes(False)
            self.title(f"Prosty Edytor Pythona - {os.path.basename(self.file_path)}")
            self.status_bar.config(text=f"Zapisano jako: {self.file_path}")

    def run_code(self):
        """Uruchamia kod w bieżącym pliku."""
        if not self.file_path:
            messagebox.showwarning("Błąd", "Zapisz plik przed uruchomieniem.")
            return

        self.save_file()
        
        try:
            python_executable = "python3" if os.name == "posix" else "python"
            process = subprocess.Popen([python_executable, self.file_path],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, encoding='utf-8')
            stdout, stderr = process.communicate()
            
            output_window = tk.Toplevel(self)
            output_window.title("Wynik Uruchomienia")
            output_window.geometry("600x400")
            output_text = scrolledtext.ScrolledText(output_window, wrap="word", background="black", foreground="white")
            output_text.pack(fill="both", expand=True)
            
            if stdout:
                output_text.insert(tk.END, "--- Standardowe Wyjście ---\n", ("green",))
                output_text.insert(tk.END, stdout)
            
            if stderr:
                output_text.insert(tk.END, "\n--- Błędy ---\n", ("red",))
                output_text.insert(tk.END, stderr)
            
            output_text.config(state="disabled")
            
        except FileNotFoundError:
            messagebox.showerror("Błąd", "Nie znaleziono interpretera Pythona. Sprawdź, czy Python jest poprawnie zainstalowany i dodany do ścieżki systemowej (PATH).)")

    def on_scroll(self, *args):
        # pylint: disable=unused-argument
        """Synchronizuje przewijanie tekstu z paskiem przewijania."""
        self.text_widget.yview(*args)
        self.update_line_numbers()

    def on_yscroll(self, *args):
        # pylint: disable=unused-argument
        """Synchronizuje przewijanie z paskiem numerów linii."""
        self.scrollbar.set(*args)
        self.line_number_bar.yview_moveto(args[0])
        self.update_line_numbers()
        
    def schedule_update(self, event=None):
        # pylint: disable=unused-argument
        """Zaplanuj aktualizację numerów linii i podświetlania."""
        self.after(50, self.update_line_numbers)
        self.after(50, self.highlight_syntax_and_whitespace_and_check_errors)
        
    def update_line_numbers(self, event=None):
        # pylint: disable=unused-argument
        """Aktualizuje zawartość paska numerów linii."""
        self.line_number_bar.config(state="normal")
        self.line_number_bar.delete("1.0", tk.END)
        
        first_line = int(self.text_widget.index("@0,0").split('.')[0])
        last_line = int(self.text_widget.index(f"@0,{self.text_widget.winfo_height()}").split('.')[0])
        total_lines = int(self.text_widget.index("end-1c").split('.')[0])
        
        for i in range(first_line, min(last_line + 2, total_lines + 1)):
            line_str = f"{i}\n"
            self.line_number_bar.insert(tk.END, line_str)
        
        dline = self.text_widget.dlineinfo("1.0")
        if dline:
            self.line_number_bar.yview_moveto(dline[1] / self.text_widget.winfo_height())
        
        self.line_number_bar.config(state="disabled")
        self.text_widget.edit_modified(False)

if __name__ == "__main__":
    app = PythonEditor()
    app.mainloop()