"""
To prosty program do nauki programowania w Python.
Został stworzony przy wydatnej pomocy AI i mojej myśli programowej.
Wersja 1.0.0.1.
Autor AI & Tomek Masłowski / Poland

This is a simple program for learning Python programming.
It was created with substantial help from AI and my own programming ideas.
Version 1.0.0.1.
Author AI & Tomek Masłowski / Poland
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading
import re
import jedi

try:
    import black
except ImportError:
    black = None

# Import TkinterDnD dla drag & drop
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    messagebox.showerror("Brak modułu", "Proszę zainstaluj bibliotekę tkinterdnd2:\npip install tkinterdnd2")
    raise

AUTO_SAVE_INTERVAL = 30_000  # 30 sekund


class PythonEditor:
    def __init__(self, root):
        self.root = root
        self.filename = None
        self.process = None

        self.create_widgets()
        self.bind_events()
        self.auto_save()
        self.update_title()

        # Rejestrujemy drag & drop na edytorze tekstowym
        self.text.drop_target_register(DND_FILES)
        self.text.dnd_bind('<<Drop>>', self.push)

    # === Funkcja push do obsługi przeciągnięcia pliku ===
    def push(self, event):
        filepath = event.data.strip('{}')
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.text.delete(1.0, tk.END)
            self.text.insert(tk.END, content)
            self.filename = filepath
            self.highlight_syntax()
            self.update_line_numbers()
            self.text.edit_reset()
            self.update_title()
            self.output.insert(tk.END, f"\n[Załadowano plik: {filepath}]\n")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się odczytać pliku:\n{e}")

    def create_widgets(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label="Nowy", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(
            label="Otwórz", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(
            label="Zapisz", command=self.save_file, accelerator="Ctrl+S")
        menubar.add_cascade(label="Plik", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(
            label="Cofnij", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(
            label="Przywróć", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(
            label="Kontrola wcięć", command=self.check_indentation, accelerator="Ctrl+I")
        menubar.add_cascade(label="Edycja", menu=edit_menu)

        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(
            label="Uruchom", command=self.run_code, accelerator="F5")
        run_menu.add_command(
            label="Zatrzymaj", command=self.stop_code, accelerator="Ctrl+Q")
        menubar.add_cascade(label="Kod", menu=run_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Pomoc", menu=help_menu)

        self.root.config(menu=menubar)

        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=1)

        # Scrollbar pionowy
        self.v_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Panel numerów linii
        self.line_numbers = tk.Text(
            frame, width=4, padx=4, takefocus=0, border=0,
            background="#282a36", foreground="#ffffff", state="disabled",
            font=("Consolas", 12)
        )
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        # Główny edytor tekstu
        self.text = tk.Text(frame, undo=True, wrap="none", font=(
            "Consolas", 12), yscrollcommand=self.on_text_scroll,
            background="#1e1e1e", foreground="#d4d4d4", insertbackground="#d4d4d4")

        self.text.pack(fill=tk.BOTH, expand=1, side=tk.LEFT)

        self.v_scroll.config(command=self.on_scrollbar)

        # Konfiguracja tagów kolorów
        self.text.tag_config("keyword", foreground="#800080")  # fioletowy
        self.text.tag_config("string", foreground="#CE9178")
        self.text.tag_config("comment", foreground="#6A9955")
        self.text.tag_config("function", foreground="#DCDCAA")
        self.text.tag_config("search", background="#264F78")
        self.text.tag_config("bracket", foreground="#D4D4D4", font=(
            "Consolas", 12, "bold"))
        self.text.tag_config("self", foreground="#9CDCFE", font=(
            "Consolas", 12, "bold"))
        self.text.tag_config("current_line", background="#44475a")
        # czerwone tło dla błędu wcięcia
        self.text.tag_config("indent_error", background="#FF0000")
        # czerwone tło błędu składni
        self.text.tag_config("syntax_error", background="#FF4444")

        self.output = tk.Text(self.root, height=8, bg="#1e1e1e",
                              fg="#d4d4d4", font=("Consolas", 10))
        self.output.pack(fill=tk.X)

        self.popup = tk.Listbox(
            self.root, height=6, bg="#252526", fg="#d4d4d4", selectbackground="#094771")
        self.popup.bind("<Double-Button-1>", self.select_autocomplete)
        self.popup.bind("<Return>", self.select_autocomplete)

    def on_text_scroll(self, *args):
        self.v_scroll.set(*args)
        self.line_numbers.yview_moveto(args[0])

    def on_scrollbar(self, *args):
        self.text.yview(*args)
        self.v_scroll.set(*args)
        self.line_numbers.yview_moveto(args[0])

    def bind_events(self):
        # Skróty globalne
        self.root.bind_all("<F5>", lambda e: (self.run_code(), "break"))
        self.root.bind_all(
            "<Control-s>", lambda e: (self.save_file(), "break"))
        self.root.bind_all(
            "<Control-o>", lambda e: (self.open_file(), "break"))
        self.root.bind_all("<Control-n>", lambda e: (self.new_file(), "break"))
        self.root.bind_all("<Control-z>", lambda e: (self.undo(), "break"))
        self.root.bind_all("<Control-y>", lambda e: (self.redo(), "break"))
        self.root.bind_all(
            "<Control-i>", lambda e: (self.check_indentation(), "break"))
        self.root.bind_all(
            "<Control-q>", lambda e: (self.stop_code(), "break"))

        self.text.bind("<KeyRelease>", self.on_key_release)
        self.text.bind("<Control-space>", self.show_autocomplete)
        self.text.bind("<Tab>", self.select_autocomplete)
        self.text.bind("<Escape>", lambda e: self.popup.place_forget())
        self.text.bind("<Return>", self.smart_indent)
        self.text.bind("<Control-Shift-F>", self.format_code)
        self.text.bind("<Control-f>", self.open_search)
        self.text.bind("<Any-KeyPress>", lambda e: self.popup.place_forget())
        self.text.bind("<MouseWheel>", self.on_mousewheel)
        self.line_numbers.bind("<MouseWheel>", self.on_mousewheel)
        self.text.bind("<Button-1>", self.on_click)
        self.text.bind("<ButtonRelease-1>", self.highlight_current_line)

    def on_key_release(self, event=None):
        self.highlight_syntax()
        self.update_line_numbers()
        self.highlight_current_line()
        self.highlight_indent_errors()
        self.highlight_syntax_errors()

    def on_mousewheel(self, event):
        delta = int(-1 * (event.delta / 120))
        self.text.yview_scroll(delta, "units")
        self.line_numbers.yview_scroll(delta, "units")
        return "break"

    def auto_save(self):
        if self.filename:
            self.save_file()
        self.root.after(AUTO_SAVE_INTERVAL, self.auto_save)

    def update_title(self):
        if self.filename:
            shortname = self.filename.split("/")[-1].split("\\")[-1]
            self.root.title(f"Python Edytor - {shortname}")
        else:
            self.root.title("Python Edytor - [Nowy plik]")

    # ==== PLIKI ====
    def new_file(self):
        self.text.delete(1.0, tk.END)
        self.filename = None
        self.update_line_numbers()
        self.update_title()

    def open_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Python Files", "*.py")])
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                self.text.delete(1.0, tk.END)
                self.text.insert(tk.END, f.read())
                self.filename = file_path
                self.highlight_syntax()
                self.update_line_numbers()
                self.text.edit_reset()
                self.update_title()

    def save_file(self):
        if not self.filename:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".py", filetypes=[("Python Files", "*.py")])
            if not file_path:
                return
            self.filename = file_path
            self.update_title()
        with open(self.filename, "w", encoding="utf-8") as f:
            f.write(self.text.get(1.0, tk.END))

    # ==== URUCHAMIANIE ====
    def run_code(self, event=None):
        self.save_file()
        if self.filename:
            self.output.delete(1.0, tk.END)
            self.process = subprocess.Popen(
                ["python", self.filename],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            threading.Thread(target=self.read_output, daemon=True).start()

    def read_output(self):
        for line in self.process.stdout:
            self.output.insert(tk.END, line)
            self.output.see(tk.END)
        self.process = None

    def stop_code(self, event=None):
        if self.process:
            self.process.kill()
            self.process = None
            self.output.insert(tk.END, "\n[Zatrzymano]\n")
        else:
            self.output.insert(
                tk.END, "\n[Brak uruchomionego procesu do zatrzymania]\n")

    # ==== SYNTAX ====
    def highlight_syntax(self):
        code = self.text.get(1.0, tk.END)
        for tag in ["keyword", "string", "comment", "function", "search", "bracket", "self"]:
            self.text.tag_remove(tag, "1.0", tk.END)

        patterns = [
            (r"\b(?:def|class|return|if|else|elif|try|except|import|from|as|while|for|in|with|break|continue|pass|raise|yield|lambda|global|nonlocal|assert|is|not|and|or|True|False|None)\b", "keyword"),
            (r"([\"'])(?:(?=(\\?))\2.)*?\1", "string"),
            (r"#.*", "comment"),
            (r"\b\w+(?=\()", "function"),
            (r"[\(\)\[\]\{\}]", "bracket"),
            (r"\bself\b|\bcls\b", "self"),
        ]

        for pattern, tag in patterns:
            for match in re.finditer(pattern, code):
                start = f"1.0+{match.start()}c"
                end = f"1.0+{match.end()}c"
                self.text.tag_add(tag, start, end)

    # ==== LINIE ====
    def update_line_numbers(self):
        self.line_numbers.config(state="normal")
        self.line_numbers.delete(1.0, tk.END)

        last_line = int(self.text.index("end-1c").split(".")[0])
        for i in range(1, last_line + 1):
            self.line_numbers.insert(tk.END, f"{i}\n")

        self.line_numbers.config(state="disabled")

    def highlight_current_line(self, event=None):
        self.text.tag_remove("current_line", "1.0", tk.END)
        line_index = self.text.index("insert").split(".")[0]
        self.text.tag_add(
            "current_line", f"{line_index}.0", f"{line_index}.end")

    def on_click(self, event):
        self.text.mark_set(tk.INSERT, f"@{event.x},{event.y}")
        self.highlight_current_line()

    # ==== AUTOUZUPEŁNIANIE ====
    def show_autocomplete(self, event=None):
        cursor = self.text.index(tk.INSERT)
        line, col = map(int, cursor.split("."))
        source = self.text.get("1.0", tk.END)
        script = jedi.Script(source, path=self.filename or "")
        completions = script.complete(line, col)
        if not completions:
            self.popup.place_forget()
            return
        self.popup.delete(0, tk.END)
        for c in completions:
            self.popup.insert(tk.END, c.name)
        try:
            x, y, width, height = self.text.bbox(tk.INSERT)
            abs_x = self.text.winfo_rootx() + x
            abs_y = self.text.winfo_rooty() + y + height
            self.popup.place(x=abs_x, y=abs_y)
        except Exception:
            self.popup.place(x=0, y=0)
        self.popup.lift()
        self.popup.focus_set()

    def select_autocomplete(self, event=None):
        if self.popup.winfo_ismapped():
            selection = self.popup.curselection()
            if selection:
                word = self.popup.get(selection[0])
                cursor = self.text.index(tk.INSERT)
                line, col = map(int, cursor.split("."))
                line_text = self.text.get(f"{line}.0", cursor)
                match = re.search(r"[\w_]+$", line_text)
                if match:
                    start_col = match.start()
                else:
                    start_col = col
                start = f"{line}.{start_col}"
                self.text.delete(start, cursor)
                self.text.insert(start, word)
                self.popup.place_forget()
                return "break"

    # ==== FORMATOWANIE KODU ====
    def format_code(self, event=None):
        if black is None:
            self.output.insert(tk.END, "Black nie jest zainstalowany\n")
            return
        try:
            source = self.text.get(1.0, tk.END)
            formatted = black.format_str(source, mode=black.Mode())
            self.text.delete(1.0, tk.END)
            self.text.insert(1.0, formatted)
        except Exception as e:
            self.output.insert(tk.END, f"Błąd formatowania: {e}\n")

    # ==== INNE ====
    def smart_indent(self, event):
        line = self.text.get("insert linestart", "insert")
        indent = re.match(r"\s*", line).group()
        self.text.insert(tk.INSERT, "\n" + indent)
        return "break"

    def undo(self, event=None):
        try:
            self.text.edit_undo()
        except Exception:
            pass

    def redo(self, event=None):
        try:
            self.text.edit_redo()
        except Exception:
            pass

    def open_search(self, event=None):
        pass

    # ==== KONTROLA I PODŚWIETLANIE BŁĘDÓW WCIĘĆ ====
    def check_indentation(self):
        lines = self.text.get(1.0, tk.END).splitlines()
        errors = []
        for i, line in enumerate(lines, start=1):
            if line.strip() == "":
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent % 4 != 0:
                errors.append(
                    f"Linia {i}: Niepoprawne wcięcie ({indent} spacji)")
        self.output.insert(tk.END, "\nKontrola wcięć:\n")
        if errors:
            for err in errors:
                self.output.insert(tk.END, err + "\n")
        else:
            self.output.insert(tk.END, "Wszystkie wcięcia są poprawne.\n")
        self.highlight_indent_errors()

    def highlight_indent_errors(self):
        self.text.tag_remove("indent_error", "1.0", tk.END)
        lines = self.text.get(1.0, tk.END).splitlines()
        for i, line in enumerate(lines, start=1):
            if line.strip() == "":
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent % 4 != 0:
                self.text.tag_add("indent_error", f"{i}.0", f"{i}.end")

    # ==== PODŚWIETLANIE BŁĘDÓW SKŁADNI ====
    def highlight_syntax_errors(self):
        self.text.tag_remove("syntax_error", "1.0", tk.END)
        code = self.text.get(1.0, tk.END)
        try:
            compile(code, self.filename or "<string>", "exec")
        except SyntaxError as e:
            lineno = e.lineno
            msg = e.msg
            self.output.insert(tk.END, f"Błąd składni: {msg}\n")
            if lineno:
                self.text.tag_add(
                    "syntax_error", f"{lineno}.0", f"{lineno}.end")

    def show_about(self):
        messagebox.showinfo(
            "About",
            "tmfgroup / Tomek Masłowski\n"
            "copyright 2025 - AI ChatGPT 4.5/5"
        )


def main():
    root = TkinterDnD.Tk()  # zamiast tk.Tk(), żeby obsługiwać DnD
    root.geometry("900x700")
    root.title("Python Edytor")
    editor = PythonEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()

