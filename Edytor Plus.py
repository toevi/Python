import tkinter as tk from tkinter import filedialog, messagebox import subprocess import jedi import os import black

class PythonEditor: def init(self, root): self.root = root self.root.title("Python Editor") self.filename = None self.create_widgets() self.bind_events()

def create_widgets(self):
    frame = tk.Frame(self.root)
    frame.pack(fill=tk.BOTH, expand=True)

    self.indent_canvas = tk.Canvas(frame, width=20, bg="#1e1e1e", highlightthickness=0)
    self.indent_canvas.pack(side=tk.LEFT, fill=tk.Y)

    self.line_numbers = tk.Text(
        frame, width=4, padx=2, takefocus=0, border=0,
        background="#282a36", foreground="#6272a4", state="disabled",
        font=("Consolas", 12)
    )
    self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

    self.text = tk.Text(
        frame, wrap=tk.NONE, font=("Consolas", 12), undo=True,
        background="#1e1e1e", foreground="#f8f8f2", insertbackground="white"
    )
    self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    self.scrollbar = tk.Scrollbar(frame, command=self.on_scrollbar)
    self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    self.text.config(yscrollcommand=self.on_textscroll)

    self.output = tk.Text(
        self.root, height=10, bg="#1e1e1e", fg="white",
        font=("Consolas", 10), state="normal"
    )
    self.output.pack(fill=tk.X)

def bind_events(self):
    self.text.bind("<KeyRelease>", self.on_key_release)
    self.text.bind("<Button-1>", self.update_line_numbers)
    self.text.bind("<MouseWheel>", self.on_mousewheel)
    self.root.bind("<Control-s>", lambda e: self.save_file())
    self.root.bind("<Control-o>", lambda e: self.open_file())
    self.root.bind("<Control-r>", lambda e: self.run_code())
    self.text.bind("<Control-i>", lambda e: self.check_indentation_errors())

def on_scrollbar(self, *args):
    self.text.yview(*args)
    self.line_numbers.yview(*args)
    self.indent_canvas.yview(*args)
    self.draw_indent_guides()

def on_textscroll(self, *args):
    self.scrollbar.set(*args)
    self.line_numbers.yview_moveto(args[0])
    self.indent_canvas.yview_moveto(args[0])
    self.draw_indent_guides()

def on_mousewheel(self, event):
    self.text.yview("scroll", int(-1*(event.delta/120)), "units")
    self.line_numbers.yview("scroll", int(-1*(event.delta/120)), "units")
    self.indent_canvas.yview("scroll", int(-1*(event.delta/120)), "units")
    self.draw_indent_guides()
    return "break"

def on_key_release(self, event=None):
    self.update_line_numbers()
    self.highlight_current_line()
    self.show_autocomplete()
    self.draw_indent_guides()

def update_line_numbers(self, event=None):
    self.line_numbers.config(state="normal")
    self.line_numbers.delete("1.0", tk.END)
    line_count = self.text.index("end-1c").split(".")[0]
    for i in range(1, int(line_count)):
        self.line_numbers.insert(tk.END, f"{i}\n")
    self.line_numbers.config(state="disabled")
    self.draw_indent_guides()

def highlight_current_line(self):
    self.text.tag_remove("current_line", "1.0", tk.END)
    self.text.tag_add("current_line", "insert linestart", "insert lineend+1c")
    self.text.tag_configure("current_line", background="#2c2c2c")

def show_autocomplete(self):
    code = self.text.get("1.0", "end-1c")
    cursor_index = self.text.index(tk.INSERT)
    row, col = map(int, cursor_index.split("."))
    script = jedi.Script(code, path=self.filename)
    try:
        completions = script.complete(line=row, column=col)
        if completions:
            menu = tk.Menu(self.root, tearoff=0)
            for c in completions:
                menu.add_command(label=c.name, command=lambda name=c.name: self.insert_completion(name))
            menu.tk_popup(self.text.winfo_rootx(), self.text.winfo_rooty() + 20)
    except Exception:
        pass

def insert_completion(self, name):
    self.text.insert(tk.INSERT, name)

def save_file(self):
    if not self.filename:
        self.filename = filedialog.asksaveasfilename(defaultextension=".py")
    if self.filename:
        code = self.text.get("1.0", tk.END)
        try:
            formatted_code = black.format_str(code, mode=black.Mode())
            with open(self.filename, "w", encoding="utf-8") as f:
                f.write(formatted_code)
            self.output.insert(tk.END, f"Zapisano: {self.filename}\n")
            self.output.see(tk.END)
        except Exception as e:
            self.output.insert(tk.END, f"Błąd zapisu: {e}\n")
            self.output.see(tk.END)

def open_file(self):
    self.filename = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
    if self.filename:
        with open(self.filename, "r", encoding="utf-8") as f:
            code = f.read()
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", code)
        self.update_line_numbers()
        self.draw_indent_guides()

def run_code(self):
    self.save_file()
    self.check_indentation_errors()
    if not self.filename:
        return
    try:
        result = subprocess.run([
            "python", self.filename
        ], capture_output=True, text=True, timeout=10)
        self.output.insert(tk.END, result.stdout)
        self.output.insert(tk.END, result.stderr)
        self.output.see(tk.END)
    except subprocess.TimeoutExpired:
        self.output.insert(tk.END, "Błąd: przekroczono limit czasu\n")

def draw_indent_guides(self):
    self.indent_canvas.delete("all")
    code_lines = self.text.get("1.0", tk.END).splitlines()
    try:
        line_height = self.text.dlineinfo("1.0")[3]
    except TypeError:
        line_height = 20

    for i, line in enumerate(code_lines):
        indent_chars = len(line) - len(line.lstrip(" \t"))
        indent_level = indent_chars // 4
        y = i * line_height
        for level in range(indent_level):
            x = 5 + level * 8
            self.indent_canvas.create_line(x, y, x, y + line_height, fill="#44475a")

def check_indentation_errors(self):
    source = self.text.get("1.0", tk.END)
    try:
        compile(source, self.filename or "<string>", "exec")
    except IndentationError as e:
        self.output.insert(tk.END, f"[IndentationError] {e}\n")
        self.output.see(tk.END)
    except SyntaxError as e:
        if "indent" in str(e):
            self.output.insert(tk.END, f"[SyntaxError] {e}\n")
            self.output.see(tk.END)

if name == "main": root = tk.Tk() app = PythonEditor(root) root.mainloop()

