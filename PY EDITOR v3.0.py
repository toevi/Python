import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import subprocess
import os
import re
import sys
import shlex

# Próba zaimportowania tkinterdnd2 dla funkcji "przeciągnij i upuść"
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    is_dnd_supported = True
    _TkBase = TkinterDnD.Tk
except ImportError:
    is_dnd_supported = False
    _TkBase = tk.Tk

class PythonEditor(_TkBase):
    """
    Klasa głównego okna edytora Pythona.
    """
    def __init__(self):
        super().__init__()
        self.title("PY Editor ver 3.0")
        self.geometry("1000x800")
        self.file_path: str | None = None
        self.unsaved_changes: bool = False

        # Zmienne do obsługi wyszukiwania
        self.find_dialog: tk.Toplevel | None = None
        self.find_text_var: tk.StringVar = tk.StringVar()
        self.replace_text_var: tk.StringVar = tk.StringVar()
        self.last_found_index: str = "1.0"

        self.process: subprocess.Popen | None = None

        # Zdefiniowanie motywów
        self.themes = {
            "Ciemny": {
                "bg_color": "#1e1e1e",
                "fg_color": "#d4d4d4",
                "line_num_bg": "#2c2c2c",
                "line_num_fg": "#d3d3d3",
                "selection_bg": "#264f78",
                "indent_bg": "#3e3e3e",
                "error_bg": "#ff6347",
                "terminal_bg": "#000000",
                "terminal_fg": "#ffffff",
                "keyword": "#569cd6",
                "string": "#ce9178",
                "comment": "#6a9955",
                "number": "#b5cea8",
                "function": "#dcdcaa",
                "class": "#4ec9b0",
                "self": "#9cdcfe",
                "delimiters": "#d4d4d4",
                "delimiter_match": "#3a3a3a",
                "find_highlight": "#4a4a4a"
            },
            "Jasny": {
                "bg_color": "#ffffff",
                "fg_color": "#000000",
                "line_num_bg": "#f0f0f0",
                "line_num_fg": "#a0a0a0",
                "selection_bg": "#b5d5ff",
                "indent_bg": "#e6e6e6",
                "error_bg": "#ff6347",
                "terminal_bg": "#f0f0f0",
                "terminal_fg": "#000000",
                "keyword": "#0000ff",
                "string": "#8b0000",
                "comment": "#008000",
                "number": "#ff0000",
                "function": "#800080",
                "class": "#00008b",
                "self": "#a52a2a",
                "delimiters": "#000000",
                "delimiter_match": "#e0e0e0",
                "find_highlight": "#ffff00"
            }
        }

        self.current_theme_name = "Ciemny"

        self.setup_ui()
        self.bind_shortcuts()
        if is_dnd_supported:
            self.setup_drag_and_drop()

        # Ulepszone wiązania
        self.text_widget.bind("<<Modified>>", self.schedule_update)
        self.text_widget.bind("<KeyRelease>", self.handle_key_release)
        self.text_widget.bind("<Button-1>", self.update_line_numbers)
        self.text_widget.bind("<Configure>", self.update_line_numbers)
        self.text_widget.bind("<MouseWheel>", self.update_line_numbers)
        self.text_widget.bind("<Key>", self.handle_key_press)
        self.text_widget.bind("<Tab>", self.handle_tab_key)
        self.text_widget.bind("<Motion>", self.highlight_matching_delimiters)
        self.text_widget.bind("<Return>", self.handle_return_key)
        self.text_widget.bind("<Up>", lambda event: None)
        self.text_widget.bind("<Down>", lambda event: None)
        self.text_widget.bind("<BackSpace>", self.handle_backspace)
        self.text_widget.bind("<Delete>", self.handle_delete)

        self.protocol("WM_DELETE_WINDOW", self.check_for_unsaved_changes)
        
        # Inicjalizacja _after_id
        self._after_id = None

    def setup_ui(self):
        """Konfiguruje interfejs użytkownika edytora."""
        self.set_colors()

        editor_frame = tk.Frame(self, bg=self.bg_color)
        editor_frame.pack(side="top", fill="both", expand=True)

        self.line_number_bar: tk.Text = tk.Text(editor_frame, width=4, padx=5, takefocus=0, border=0,
                                                 background=self.line_num_bg, foreground=self.line_num_fg,
                                                 font=("Consolas", 12))
        self.line_number_bar.pack(side="left", fill="y")
        self.line_number_bar.config(state="disabled")

        self.text_widget: tk.Text = tk.Text(editor_frame, wrap="word", undo=True,
                                             background=self.bg_color, foreground=self.fg_color,
                                             insertbackground="white", border=0,
                                             selectbackground=self.selection_bg,
                                             font=("Consolas", 12))
        self.text_widget.pack(side="left", fill="both", expand=True)

        self.scrollbar: tk.Scrollbar = tk.Scrollbar(editor_frame, command=self.on_scroll)
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
        edit_menu.add_separator()
        edit_menu.add_command(label="Znajdź...", command=self.show_find_dialog, accelerator="Ctrl+F")

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Widok", menu=view_menu)
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Motyw", menu=theme_menu)
        theme_menu.add_command(label="Ciemny", command=lambda: self.change_theme("Ciemny"))
        theme_menu.add_command(label="Jasny", command=lambda: self.change_theme("Jasny"))

        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Uruchom", menu=run_menu)
        run_menu.add_command(label="Uruchom program", command=self.run_code, accelerator="F5")
        run_menu.add_command(label="Zatrzymaj", command=self.stop_code, accelerator="Shift+F5")
        run_menu.add_command(label="Otwórz terminal systemowy", command=self.open_system_terminal, accelerator="Ctrl+T")

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Pomoc", menu=help_menu)
        help_menu.add_command(label="O programie", command=self.show_about_dialog)

        self.terminal_frame = tk.Frame(self, bg=self.terminal_bg, height=200)
        self.terminal_frame.pack(side="bottom", fill="x", expand=False)
        self.terminal_frame.pack_propagate(False)

        self.terminal_text: scrolledtext.ScrolledText = scrolledtext.ScrolledText(self.terminal_frame, wrap="word",
                                                                                    background=self.terminal_bg, foreground=self.terminal_fg,
                                                                                    insertbackground="white", border=0,
                                                                                    font=("Consolas", 10))
        self.terminal_text.pack(fill="both", expand=True)
        self.terminal_text.config(state="disabled")

        self.status_bar = tk.Label(self, text="Gotowy", bd=1, relief="sunken", anchor="w",
                                    bg=self.bg_color, fg=self.fg_color)
        self.status_bar.pack(side="bottom", fill="x")

        self.error_bar = tk.Label(self, text="", bd=1, relief="sunken", anchor="w",
                                  bg=self.bg_color, fg=self.fg_color)
        self.error_bar.pack(side="bottom", fill="x")

        self.popup_menu = tk.Menu(self, tearoff=0)
        self.popup_menu.add_command(label="Wytnij", command=self.cut_text)
        self.popup_menu.add_command(label="Kopiuj", command=self.copy_text)
        self.popup_menu.add_command(label="Wklej", command=self.paste_text)
        self.text_widget.bind("<Button-3>", self.show_popup_menu)

        self.setup_syntax_highlighting()

    def set_colors(self):
        """Ustawia kolory na podstawie wybranego motywu."""
        theme = self.themes[self.current_theme_name]
        self.bg_color = theme["bg_color"]
        self.fg_color = theme["fg_color"]
        self.line_num_bg = theme["line_num_bg"]
        self.line_num_fg = theme["line_num_fg"]
        self.selection_bg = theme["selection_bg"]
        self.indent_bg = theme["indent_bg"]
        self.error_bg = theme["error_bg"]
        self.terminal_bg = theme["terminal_bg"]
        self.terminal_fg = theme["terminal_fg"]
        self.delimiter_match = theme["delimiter_match"]
        self.find_highlight = theme["find_highlight"]

    def change_theme(self, theme_name):
        """Zmienia motyw edytora."""
        self.current_theme_name = theme_name
        self.set_colors()

        # Aktualizacja kolorów widżetów
        self.config(bg=self.bg_color)
        self.text_widget.config(bg=self.bg_color, fg=self.fg_color, selectbackground=self.selection_bg, insertbackground=self.fg_color)
        self.line_number_bar.config(bg=self.line_num_bg, fg=self.line_num_fg)
        self.terminal_text.config(bg=self.terminal_bg, fg=self.terminal_fg)
        self.status_bar.config(bg=self.bg_color, fg=self.fg_color)
        self.error_bar.config(bg=self.bg_color, fg=self.fg_color)

        self.setup_syntax_highlighting()
        self.highlight_syntax_and_whitespace_and_check_errors()

    def bind_shortcuts(self):
        """Wiąże skróty klawiaturowe z funkcjami edytora."""
        self.bind("<Control-n>", lambda event: self.new_file())
        self.bind("<Control-o>", lambda event: self.open_file())
        self.bind("<Control-s>", lambda event: self.save_file())
        self.bind("<Control-S>", lambda event: self.save_as_file())
        self.bind("<Control-q>", lambda event: self.check_for_unsaved_changes())
        self.bind("<Control-f>", lambda event: self.show_find_dialog())
        self.bind("<Control-t>", lambda event: self.open_system_terminal())
        self.bind("<F5>", lambda event: self.run_code())
        self.bind("<Shift-F5>", lambda event: self.stop_code())

    def show_about_dialog(self):
        """Wyświetla okno "O programie"."""
        messagebox.showinfo(
            "O programie",
            "PY EDITOR ver 3.0. Prosty edytor Pythona do nauki programowania.\n\nProjekt i pomysł: Tomek Masłowski\nWykonanie: Gemini"
        )

    def check_for_unsaved_changes(self):
        """Sprawdza, czy są niezapisane zmiany przed wyjściem."""
        if self.unsaved_changes:
            response = messagebox.askyesnocancel("Niezapisane zmiany", "Czy chcesz zapisać zmiany przed wyjściem?")
            if response is None:
                return
            elif response:
                self.save_file()
                if self.unsaved_changes:
                    return
        self.destroy()

    def set_unsaved_changes(self, modified=True):
        """Ustawia flagę niezapisanych zmian i aktualizuje tytuł okna."""
        self.unsaved_changes = modified
        title = self.file_path if self.file_path else "Nowy Plik"
        if self.unsaved_changes:
            self.title(f"PY Editor ver 3.0 - {os.path.basename(title)}*")
        else:
            self.title(f"PY Editor ver 3.0 - {os.path.basename(title)}")

    def highlight_matching_delimiters(self, event=None):
        """Podświetla pasujące nawiasy i cudzysłowy."""
        self.text_widget.tag_remove("delimiter", "1.0", "end")

        cursor_index = self.text_widget.index(tk.INSERT)
        char = self.text_widget.get(cursor_index + "-1c")

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

        elif char in ")]}":
            matching_char = { ")": "(", "]": "[", "}": "{" }[char]
            count = 1
            pos = cursor_index
            while count > 0 and pos != "1.0":
                pos = self.text_widget.search(r"[\(\[\{\)\]\}]", pos + "-1c", stopindex="1.0", backwards=True, regexp=True)
                if not pos:
                    break

                next_char = self.text_widget.get(pos)
                if next_char == matching_char:
                    count -= 1
                elif next_char in ")]}":
                    count += 1
            if pos:
                self.text_widget.tag_add("delimiter", cursor_index + "-1c", cursor_index)
                self.text_widget.tag_add("delimiter", pos)

        elif char in "'\"":
            matching_char = char
            start_index = self.text_widget.search(f"{matching_char}", "1.0", tk.INSERT, backwards=True, regexp=True)
            if start_index:
                # Sprawdzanie, czy to nie jest potrójny cudzysłów
                if self.text_widget.get(f"{start_index}-2c", f"{start_index}") == matching_char*3 or \
                   self.text_widget.get(f"{start_index}+1c", f"{start_index}+3c") == matching_char*2:
                    return None
                end_index = self.text_widget.search(f"{matching_char}", tk.INSERT, "end", regexp=True)
                if end_index:
                    self.text_widget.tag_add("delimiter", start_index)
                    self.text_widget.tag_add("delimiter", end_index)
        return None

    def handle_key_press(self, event):
        """Obsługuje zdarzenia naciśnięcia klawisza."""
        self.handle_auto_pair_and_indent(event)
        self.set_unsaved_changes()

        return None

    def handle_key_release(self, event=None):
        """Obsługuje zdarzenia zwolnienia klawisza."""
        self.update_line_numbers()
        self.highlight_syntax_and_whitespace_and_check_errors()
        return None

    def update_line_numbers_and_hide_autocomplete(self, event=None):
        """Aktualizuje numery linii i ukrywa podpowiedzi."""
        self.update_line_numbers()
        return None

    def show_popup_menu(self, event):
        """Wyświetla menu kontekstowe."""
        self.popup_menu.post(event.x_root, event.y_root)

    def cut_text(self):
        """Wycina zaznaczony tekst."""
        self.text_widget.event_generate("<<Cut>>")
        self.set_unsaved_changes()

    def copy_text(self):
        """Kopiuje zaznaczony tekst."""
        self.text_widget.event_generate("<<Copy>>")

    def paste_text(self):
        """Wkleja tekst ze schowka."""
        self.text_widget.event_generate("<<Paste>>")
        self.set_unsaved_changes()

    def handle_auto_pair_and_indent(self, event):
        """Obsługuje automatyczne parowanie nawiasów i cudzysłowów."""
        self.set_unsaved_changes()

        if event.char in ['(', '[', '{', "'", '"']:
            pair_map = {'(': ')', '[': ']', '{': '}', "'": "'", '"': '"'}
            self.text_widget.insert(tk.INSERT, pair_map[event.char])
            self.text_widget.mark_set(tk.INSERT, "insert-1c")
            return "break"

        if event.keysym in ['parenright', 'bracketright', 'braceright']:
            next_char = self.text_widget.get("insert", "insert+1c")
            if next_char == event.char:
                self.text_widget.mark_set(tk.INSERT, "insert+1c")
                return "break"
        return None

    def handle_backspace(self, event):
        """Obsługuje klawisz Backspace, usuwając parę nawiasów/cudzysłowów, jeśli to konieczne."""
        start = self.text_widget.index(tk.INSERT)
        end = self.text_widget.index(f"{start}+1c")
        if start == end:
            return None # nic nie zaznaczone
        
        char_before = self.text_widget.get(f"{start}-1c", start)
        char_after = self.text_widget.get(start, end)
        
        pairs = {"(": ")", "[": "]", "{": "}", "'": "'", '"': '"'}
        
        if char_before in pairs and pairs[char_before] == char_after:
            self.text_widget.delete(start, end)
            
    def handle_delete(self, event):
        """Obsługuje klawisz Delete, usuwając parę nawiasów/cudzysłowów, jeśli to konieczne."""
        start = self.text_widget.index(tk.INSERT)
        end = self.text_widget.index(f"{start}+1c")
        if start == end:
            return None
        
        char_before = self.text_widget.get(f"{start}-1c", start)
        char_after = self.text_widget.get(start, end)
        
        pairs = {"(": ")", "[": "]", "{": "}", "'": "'", '"': '"'}
        
        if char_after in pairs.values() and pairs.get(char_before) == char_after:
            self.text_widget.delete(start, end)

    def handle_return_key(self, event):
        """Obsługuje klawisz Enter, w tym wcięcie."""
        self.set_unsaved_changes()
        line_start_index = self.text_widget.index(f"{tk.INSERT} linestart")
        line_end_index = self.text_widget.index(f"{tk.INSERT} lineend")
        current_line = self.text_widget.get(line_start_index, line_end_index)

        self.text_widget.insert(tk.INSERT, '\n')

        indent = re.match(r'^\s*', current_line)
        indent_str = indent.group() if indent else ""

        if current_line.strip().endswith((':', '[', '(')):
            indent_str += "    "

        self.text_widget.insert(tk.INSERT, indent_str)
        self.update_line_numbers()

        return "break"

    def handle_tab_key(self, event):
        """Obsługuje klawisz Tab, wstawiając 4 spacje."""
        self.text_widget.insert(tk.INSERT, "    ")
        self.set_unsaved_changes()
        return "break"

    def setup_syntax_highlighting(self):
        """Konfiguruje znaczniki do podświetlania składni."""
        theme = self.themes[self.current_theme_name]

        self.text_widget.tag_configure("keyword", foreground=theme["keyword"])
        self.text_widget.tag_configure("string", foreground=theme["string"])
        self.text_widget.tag_configure("comment", foreground=theme["comment"])
        self.text_widget.tag_configure("number", foreground=theme["number"])
        self.text_widget.tag_configure("function", foreground=theme["function"])
        self.text_widget.tag_configure("class", foreground=theme["class"])
        self.text_widget.tag_configure("self", foreground=theme["self"], font=("Consolas", 12, "italic"))
        self.text_widget.tag_configure("delimiters", foreground=theme["delimiters"])
        self.text_widget.tag_configure("indent", background=self.indent_bg)
        self.text_widget.tag_configure("syntax_error", background=theme["error_bg"], foreground="white")
        self.text_widget.tag_configure("delimiter", background=theme["delimiter_match"])

        self.terminal_text.tag_configure("success", foreground="#33ff33")
        self.terminal_text.tag_configure("error", foreground="#ff6347")
        self.terminal_text.tag_configure("info", foreground="#87ceeb")
        self.terminal_text.tag_configure("prompt", foreground="lightgray")

        self.text_widget.tag_configure("find_highlight", background=theme["find_highlight"], foreground="white")

    def show_find_dialog(self):
        """Wyświetla okno "Znajdź i zamień"."""
        if self.find_dialog is None or not self.find_dialog.winfo_exists():
            self.find_dialog = tk.Toplevel(self)
            self.find_dialog.title("Znajdź i zamień")
            self.find_dialog.geometry("350x200")
            self.find_dialog.transient(self)
            self.find_dialog.resizable(False, False)

            self.find_dialog.protocol("WM_DELETE_WINDOW", self.find_dialog.destroy)

            find_frame = tk.LabelFrame(self.find_dialog, text="Znajdź")
            find_frame.pack(padx=5, pady=5, fill="x")

            tk.Label(find_frame, text="Znajdź:").pack(side="left", padx=5)
            self.find_entry = tk.Entry(find_frame, textvariable=self.find_text_var, width=30)
            self.find_entry.pack(side="left", padx=5, fill="x", expand=True)
            self.find_entry.focus_set()

            replace_frame = tk.LabelFrame(self.find_dialog, text="Zamień")
            replace_frame.pack(padx=5, pady=5, fill="x")

            tk.Label(replace_frame, text="Zamień na:").pack(side="left", padx=5)
            self.replace_entry = tk.Entry(replace_frame, textvariable=self.replace_text_var, width=30)
            self.replace_entry.pack(side="left", padx=5, fill="x", expand=True)

            button_frame = tk.Frame(self.find_dialog)
            button_frame.pack(pady=5)

            tk.Button(button_frame, text="Znajdź Następny", command=self.find_text).pack(side="left", padx=5)
            tk.Button(button_frame, text="Zamień", command=self.replace_text).pack(side="left", padx=5)
            tk.Button(button_frame, text="Zamień wszystko", command=self.replace_all_text).pack(side="left", padx=5)

            self.find_entry.bind("<Return>", lambda event: self.find_text())

    def find_text(self):
        """Znajduje następne wystąpienie tekstu."""
        search_text = self.find_text_var.get()
        if not search_text:
            self.text_widget.tag_remove("find_highlight", "1.0", tk.END)
            self.last_found_index = "1.0"
            self.status_bar.config(text="Pole wyszukiwania jest puste.")
            return

        self.text_widget.tag_remove("find_highlight", "1.0", tk.END)

        start_index = self.text_widget.index(tk.INSERT)
        pos = self.text_widget.search(search_text, start_index, stopindex=tk.END)

        if not pos:
            # Wróć na początek pliku, jeśli nic nie znaleziono
            pos = self.text_widget.search(search_text, "1.0", stopindex=tk.END)
            if not pos:
                self.last_found_index = "1.0"
                self.status_bar.config(text=f"Nie znaleziono '{search_text}'")
                return

        end_pos = f"{pos}+{len(search_text)}c"
        self.last_found_index = end_pos

        self.text_widget.tag_add("find_highlight", pos, end_pos)
        self.text_widget.mark_set(tk.INSERT, end_pos)
        self.text_widget.see(pos)
        self.status_bar.config(text=f"Znaleziono '{search_text}'")

    def replace_text(self):
        """Zamienia jedno wystąpienie tekstu."""
        search_text = self.find_text_var.get()
        replace_with = self.replace_text_var.get()

        if not search_text:
            self.status_bar.config(text="Pole wyszukiwania jest puste.")
            return

        current_selection = self.text_widget.tag_ranges("find_highlight")

        if current_selection:
            start_pos, end_pos = current_selection[0], current_selection[1]

            if self.text_widget.get(start_pos, end_pos) == search_text:
                self.text_widget.delete(start_pos, end_pos)
                self.text_widget.insert(start_pos, replace_with)
                self.set_unsaved_changes()
                self.status_bar.config(text=f"Zamieniono '{search_text}' na '{replace_with}'")

            self.find_text() # Znajdź następne wystąpienie po zamianie

    def replace_all_text(self):
        """Zamienia wszystkie wystąpienia tekstu."""
        search_text = self.find_text_var.get()
        replace_with = self.replace_text_var.get()

        if not search_text:
            self.status_bar.config(text="Pole wyszukiwania jest puste.")
            return

        count = 0
        start_index = "1.0"
        while True:
            pos = self.text_widget.search(search_text, start_index, stopindex=tk.END)
            if not pos:
                break

            end_pos = f"{pos}+{len(search_text)}c"
            self.text_widget.delete(pos, end_pos)
            self.text_widget.insert(pos, replace_with)
            start_index = f"{pos}+{len(replace_with)}c"
            count += 1

        if count > 0:
            self.set_unsaved_changes()
            self.status_bar.config(text=f"Zamieniono {count} wystąpień.")
        else:
            self.status_bar.config(text=f"Nie znaleziono '{search_text}'.")
        self.text_widget.tag_remove("find_highlight", "1.0", tk.END)

    def setup_drag_and_drop(self):
        """Konfiguruje funkcjonalność przeciągnij i upuść."""
        self.text_widget.drop_target_register(DND_FILES)
        self.text_widget.dnd_bind('<<Drop>>', self.handle_dnd_drop)

    def handle_dnd_drop(self, event):
        """
        Obsługuje upuszczanie pliku.
        Ulepszono, aby poprawnie obsługiwać ścieżki z nazwami zawierającymi spacje
        na systemie Windows, gdzie są one otaczane nawiasami klamrowymi.
        """
        try:
            # Sprawdzenie, czy dane są otoczone nawiasami klamrowymi (typowe dla Windows)
            raw_paths = str(event.data)
            if raw_paths.startswith('{') and raw_paths.endswith('}'):
                # Usunięcie nawiasów i traktowanie całej zawartości jako jednej ścieżki
                file_paths = [raw_paths.strip('{}')]
            else:
                # W przeciwnym razie, użycie shlex.split (działa lepiej na Unix/Linux)
                file_paths = shlex.split(raw_paths)

            if len(file_paths) > 1:
                messagebox.showwarning("Ostrzeżenie", "Możesz upuścić tylko jeden plik naraz.")
                return

            if file_paths:
                file_path = file_paths[0]
                if os.path.isfile(file_path) and file_path.endswith('.py'):
                    self.open_file_by_path(file_path)
                else:
                    messagebox.showwarning("Błąd", "Możesz upuścić tylko plik Pythona (.py).")
            else:
                messagebox.showwarning("Błąd", "Nie udało się odczytać ścieżki pliku.")

        except Exception as e:
            messagebox.showerror("Błąd", f"Wystąpił nieoczekiwany błąd podczas przeciągania i upuszczania: {e}")
            
    def open_file_by_path(self, path):
        """Otwiera plik o podanej ścieżce."""
        if self.unsaved_changes:
            response = messagebox.askyesnocancel("Niezapisane zmiany", "Czy chcesz zapisać zmiany w bieżącym pliku?")
            if response is None:
                return
            if response:
                self.save_file()
                if self.unsaved_changes:
                    return

        try:
            with open(path, "r", encoding="utf-8") as file:
                code = file.read()
                self.text_widget.delete("1.0", tk.END)
                self.text_widget.insert("1.0", code)
            self.file_path = path
            self.set_unsaved_changes(False)
            self.title(f"PY Editor ver 3.0 - {os.path.basename(self.file_path)}")
            self.status_bar.config(text=f"Otwarto: {self.file_path}")
            self.highlight_syntax_and_whitespace_and_check_errors()
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się otworzyć pliku: {e}")

    def highlight_syntax_and_whitespace_and_check_errors(self):
        """Wywołuje wszystkie funkcje związane z podświetlaniem i sprawdzaniem błędów."""
        self.highlight_syntax()
        self.visualize_whitespace()
        self.check_syntax_error()

    def highlight_syntax(self):
        """Podświetla składnię kodu."""
        code = self.text_widget.get("1.0", "end-1c")

        # Usunięcie wszystkich znaczników przed ponownym kolorowaniem
        for tag in ["keyword", "string", "comment", "number", "function", "class", "self", "delimiters"]:
            self.text_widget.tag_remove(tag, "1.0", tk.END)

        # Ulepszona logika podświetlania z użyciem bardziej zaawansowanych wyrażeń regularnych
        keywords = r'\b(if|else|elif|for|while|import|from|as|return|True|False|def|class|try|except|finally|pass|break|continue|in|is|None|not|or|and|yield|lambda|global|nonlocal|with|await|async)\b'
        self.apply_regex_highlighting(keywords, "keyword")

        functions = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        self.apply_regex_highlighting(functions, "function", offset_end=1)

        classes = r'\b(class)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b'
        self.apply_regex_highlighting(classes, "class", group=2)

        self_match = r'\bself\b'
        self.apply_regex_highlighting(self_match, "self")

        numbers = r'\b\d+(\.\d*)?([eE][+-]?\d+)?\b'
        self.apply_regex_highlighting(numbers, "number")

        strings_re = r'(".*?"|\'.*?\')'
        self.apply_regex_highlighting(strings_re, "string")

        comments_re = r'(#.*)'
        self.apply_regex_highlighting(comments_re, "comment")
    
    def check_syntax_error(self):
        """Sprawdza błędy składni i podświetla je."""
        self.error_bar.config(text="")
        self.text_widget.tag_remove("syntax_error", "1.0", tk.END)
        code = self.text_widget.get("1.0", "end-1c")

        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            error_line = e.lineno
            self.error_bar.config(text=f"Błąd składni w linii {error_line}: {e.msg}", bg=self.error_bg, fg="white")
            
            error_start = f"{error_line}.0"
            error_end = f"{error_line}.end"
            
            self.text_widget.tag_add("syntax_error", error_start, error_end)

    def apply_regex_highlighting(self, pattern, tag, offset_end=0, group=0):
        """Pomocnicza funkcja do podświetlania na podstawie wyrażeń regularnych."""
        code = self.text_widget.get("1.0", tk.END)
        for match in re.finditer(pattern, code):
            start_index = f"1.0+{match.start()}c"
            end_index = f"1.0+{match.end()}c"
            if group > 0:
                start_index = f"1.0+{match.start(group)}c"
                end_index = f"1.0+{match.end(group)}c"
            self.text_widget.tag_add(tag, start_index, end_index)
        
    def visualize_whitespace(self):
        """Wizualizuje wcięcia."""
        self.text_widget.tag_remove("indent", "1.0", tk.END)
        code_lines = self.text_widget.get("1.0", "end-1c").split('\n')
        for i, line in enumerate(code_lines):
            indent_match = re.match(r'^\s*', line)
            if indent_match:
                indent_len = len(indent_match.group())
                if indent_len > 0:
                    start_index = f"{i+1}.0"
                    end_index = f"{i+1}.{indent_len}"
                    self.text_widget.tag_add("indent", start_index, end_index)
        
    def new_file(self):
        """Tworzy nowy, pusty plik."""
        if self.unsaved_changes:
            response = messagebox.askyesnocancel("Niezapisane zmiany", "Czy chcesz zapisać zmiany w bieżącym pliku?")
            if response is None:
                return
            if response:
                self.save_file()
                if self.unsaved_changes:
                    return

        self.text_widget.delete("1.0", tk.END)
        self.file_path = None
        self.set_unsaved_changes(False)
        self.title("PY Editor ver 3.0 - Nowy Plik")
        self.status_bar.config(text="Stworzono nowy plik.")

    def open_file(self):
        """Otwiera plik wybrany przez użytkownika."""
        if self.unsaved_changes:
            response = messagebox.askyesnocancel("Niezapisane zmiany", "Czy chcesz zapisać zmiany w bieżącym pliku?")
            if response is None:
                return
            if response:
                self.save_file()
                if self.unsaved_changes:
                    return

        file_path = filedialog.askopenfilename(defaultextension=".py",
                                            filetypes=[("Pliki Pythona", "*.py"), ("Wszystkie pliki", "*.*")])
        if file_path:
            self.open_file_by_path(file_path)

    def save_file(self):
        """Zapisuje bieżący plik."""
        if self.file_path:
            try:
                with open(self.file_path, "w", encoding="utf-8") as file:
                    file.write(self.text_widget.get("1.0", tk.END))
                self.set_unsaved_changes(False)
                self.status_bar.config(text=f"Zapisano: {os.path.basename(self.file_path)}")
                return True
            except Exception as e:
                messagebox.showerror("Błąd zapisu", f"Nie udało się zapisać pliku: {e}")
                return False
        else:
            return self.save_as_file()

    def save_as_file(self):
        """Zapisuje plik pod nową nazwą."""
        file_path = filedialog.asksaveasfilename(defaultextension=".py",
                                                filetypes=[("Pliki Pythona", "*.py"), ("Wszystkie pliki", "*.*")])
        if file_path:
            self.file_path = file_path
            return self.save_file()
        return False

    def run_code(self):
        """Uruchamia kod Pythona w terminalu."""
        if not self.save_file():
            return

        self.terminal_text.config(state="normal")
        self.terminal_text.delete("1.0", tk.END)
        self.terminal_text.insert(tk.END, "Uruchamianie programu...\n", "info")
        self.terminal_text.config(state="disabled")

        if self.process and self.process.poll() is None:
            self.stop_code()
        
        try:
            # Upewnij się, że używamy ścieżki do interpretera, który uruchomił skrypt
            interpreter = sys.executable
            self.process = subprocess.Popen(
                [interpreter, self.file_path],
                cwd=os.path.dirname(self.file_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            self.after(100, self.check_process)
        except Exception as e:
            self.terminal_text.config(state="normal")
            self.terminal_text.insert(tk.END, f"Błąd uruchamiania: {e}\n", "error")
            self.terminal_text.config(state="disabled")

    def check_process(self):
        """Sprawdza stan procesu i pobiera dane z stdout/stderr."""
        if self.process:
            output = self.process.stdout.read()
            errors = self.process.stderr.read()

            self.terminal_text.config(state="normal")
            if output:
                self.terminal_text.insert(tk.END, output, "success")
            if errors:
                self.terminal_text.insert(tk.END, errors, "error")

            if self.process.poll() is not None:
                self.terminal_text.insert(tk.END, f"\nProgram zakończono z kodem wyjścia {self.process.returncode}.\n", "info")
                self.process = None
                self.status_bar.config(text="Program zakończono.")
            else:
                self.after(100, self.check_process)
            self.terminal_text.config(state="disabled")
            self.terminal_text.see(tk.END)

    def stop_code(self):
        """Zatrzymuje bieżący proces."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.terminal_text.config(state="normal")
            self.terminal_text.insert(tk.END, "\nProgram został zatrzymany.\n", "info")
            self.terminal_text.config(state="disabled")
            self.status_bar.config(text="Program został zatrzymany.")

    def open_system_terminal(self):
        """Otwiera terminal systemowy w katalogu bieżącego pliku."""
        try:
            if self.file_path and os.path.isfile(self.file_path):
                working_dir = os.path.dirname(self.file_path)
            else:
                working_dir = os.getcwd()

            if sys.platform.startswith('win'):
                # Użyj "start cmd" dla Windows
                command = 'start cmd'
            elif sys.platform.startswith('linux'):
                # Użyj 'gnome-terminal' dla Linuxa (można zmienić na 'xterm' lub 'konsole')
                command = 'gnome-terminal'
            elif sys.platform.startswith('darwin'):
                # Użyj 'open -a Terminal' dla macOS
                command = 'open -a Terminal'
            else:
                messagebox.showwarning("Ostrzeżenie", "Nieobsługiwany system operacyjny.")
                return

            subprocess.Popen(command, cwd=working_dir, shell=True)
            self.status_bar.config(text="Otwarto terminal systemowy.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się otworzyć terminala: {e}")

    def on_scroll(self, *args):
        """Synchronizuje przewijanie widgetu tekstu i numerów linii."""
        self.text_widget.yview(*args)
        self.line_number_bar.yview(*args)
        self.update_line_numbers()
        self.text_widget.after(10, self.highlight_matching_delimiters)

    def on_yscroll(self, *args):
        """Obsługuje przewijanie widgetu tekstu i aktualizuje pasek przewijania."""
        self.line_number_bar.yview_moveto(args[0])
        self.scrollbar.set(*args)
        self.update_line_numbers()

    def update_line_numbers(self, event=None):
        """Aktualizuje numery linii."""
        self.line_number_bar.config(state="normal")
        self.line_number_bar.delete("1.0", tk.END)

        start_line_index = self.text_widget.index("@0,0")
        end_line_index = self.text_widget.index(f"@0,{self.text_widget.winfo_height()}")
        
        start_line_num = int(start_line_index.split('.')[0])
        end_line_num = int(end_line_index.split('.')[0]) + 1

        line_count = int(self.text_widget.index('end-1c').split('.')[0])
        if end_line_num > line_count:
            end_line_num = line_count + 1

        for i in range(start_line_num, end_line_num):
            self.line_number_bar.insert(tk.END, f"{i}\n")
        
        self.line_number_bar.config(state="disabled")

    def schedule_update(self, event=None):
        """Planuje aktualizację po krótkim opóźnieniu, aby uniknąć częstych wywołań."""
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(100, self.update_and_mark)

    def update_and_mark(self):
        """Aktualizuje i oznacza, że zmiany zostały zapisane."""
        self.set_unsaved_changes()
        self.text_widget.edit_modified(False)
        self.update_line_numbers()
        self.highlight_syntax_and_whitespace_and_check_errors()
        self._after_id = None

if __name__ == "__main__":
    app = PythonEditor()
    app.mainloop()
