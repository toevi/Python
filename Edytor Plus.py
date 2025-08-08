import tkinter as tk
from tkinter import filedialog, simpledialog
import subprocess
import threading
import re
import jedi
try:
    import black
except ImportError:
    black = None

AUTO_SAVE_INTERVAL = 5000  # ms

class PythonEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Edytor Pythona")

        self.filename = None
        self.process = None

        # Text widget for code
        self.text = tk.Text(root, wrap="none", undo=True)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Line numbers widget
        self.line_numbers = tk.Text(root, width=4, padx=4, takefocus=0, border=0, background='#2b2b2b', foreground='white', state='disabled')
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        # Canvas for indent guides
        self.canvas_indent = tk.Canvas(root, width=20, bg="#1e1e1e", highlightthickness=0)
        self.canvas_indent.pack(side=tk.LEFT, fill=tk.Y)

        # Scrollbar
        self.scrollbar = tk.Scrollbar(root, orient="vertical", command=self.on_scrollbar)
        self.scrollbar.pack(side=tk.RIGHT, fill="y")

        self.text.config(yscrollcommand=self.on_text_scroll)
        self.line_numbers.config(yscrollcommand=self.on_text_scroll)
        self.canvas_indent.config(yscrollcommand=self.on_text_scroll)

        # Output area
        self.output = tk.Text(root, height=10, bg="black", fg="lime", insertbackground="white")
        self.output.pack(fill=tk.X)

        # Autocomplete popup
        self.popup = tk.Listbox(root)

        # Key bindings
        self.text.bind("<KeyRelease>", self.on_key_release)
        self.text.bind("<Return>", self.smart_indent)
        self.text.bind("<Control-space>", self.show_autocomplete)
        self.text.bind("<Tab>", self.select_autocomplete)
        self.text.bind("<Control-f>", self.open_search)
        self.text.bind("<Control-Shift-F>", self.format_code)
        self.text.bind("<Control-i>", lambda e: self.check_indentation_errors())
        self.text.bind("<Control-z>", self.undo)
        self.text.bind("<Control-y>", self.redo)

        # Mouse and scroll events
        self.text.bind("<Configure>", lambda e: self.draw_indent_guides())
        self.text.bind("<Motion>", lambda e: self.draw_indent_guides())
        self.text.bind("<MouseWheel>", self.on_mousewheel)
        self.text.bind("<Button-1>", self.on_click)

        # Syntax highlighting tags
        self.text.tag_configure("keyword", foreground="orange")
        self.text.tag_configure("string", foreground="lightgreen")
        self.text.tag_configure("comment", foreground="grey")
        self.text.tag_configure("function", foreground="cyan")
        self.text.tag_configure("self", foreground="violet")
        self.text.tag_configure("search", background="yellow")
        self.text.tag_configure("indent_error", background="red")

        # Initialize auto-save, line numbers, and indent guides
        self.auto_save()
        self.update_line_numbers()
        self.draw_indent_guides()

    def draw_indent_guides(self):
        # Clear previous indent guides
        self.canvas_indent.delete("all")
        lines = int(self.text.index("end-1c").split(".")[0])

        for i in range(1, lines + 1):
            line_index = f"{i}.0"
            text = self.text.get(line_index, f"{i}.end")
            spaces = len(text) - len(text.lstrip(' '))
            indent_level = spaces // 4
            if spaces == 0:
                continue

            # Get bounding box of the line to position the indent guides
            bbox = self.text.bbox(line_index)
            if not bbox:
                continue
            y = bbox[1]
            line_height = bbox[3]

            # Draw vertical lines for each indentation level
            for j in range(indent_level):
                x = 5 + j * 8
                self.canvas_indent.create_line(x, y, x, y + line_height, fill="#444")

    def on_mousewheel(self, event):
        self.text.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.line_numbers.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.canvas_indent.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.update_line_numbers()
        self.draw_indent_guides()
        return "break"

    def on_scrollbar(self, *args):
        self.text.yview(*args)
        self.line_numbers.yview(*args)
        self.canvas_indent.yview(*args)
        self.update_line_numbers()
        self.draw_indent_guides()

    def on_text_scroll(self, *args):
        self.scrollbar.set(*args)
        self.line_numbers.yview_moveto(args[0])
        self.canvas_indent.yview_moveto(args[0])
        self.update_line_numbers()
        self.draw_indent_guides()

    def on_click(self, event):
        self.update_line_numbers()
        self.draw_indent_guides()

    def update_line_numbers(self):
        self.line_numbers.config(state="normal")
        self.line_numbers.delete("1.0", tk.END)
        line_count = int(self.text.index("end-1c").split(".")[0])
        lines = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert("1.0", lines)
        self.line_numbers.config(state="disabled")

    def auto_save(self):
        if self.filename:
            self.save_file()
        self.root.after(AUTO_SAVE_INTERVAL, self.auto_save)

    def new_file(self):
        self.filename = None
        self.text.delete("1.0", tk.END)
        self.output.delete("1.0", tk.END)
        self.update_title()

    def open_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                self.text.delete("1.0", tk.END)
                self.text.insert("1.0", f.read())
            self.filename = filename
            self.update_title()
            self.update_line_numbers()
            self.draw_indent_guides()

    def save_file(self):
        if not self.filename:
            self.filename = filedialog.asksaveasfilename(defaultextension=".py")
        if self.filename:
            with open(self.filename, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", tk.END))
            self.update_title()

    def update_title(self):
        title = "Edytor Pythona"
        if self.filename:
            title += f" - {self.filename}"
        self.root.title(title)

    def run_code(self):
        if self.process:
            self.stop_code()

        code = self.text.get("1.0", tk.END)
        self.output.delete("1.0", tk.END)

        def target():
            try:
                self.process = subprocess.Popen(
                    ["python", "-u", "-c", code],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for line in self.process.stdout:
                    self.output.insert(tk.END, line)
                for line in self.process.stderr:
                    self.output.insert(tk.END, line)
            except Exception as e:
                self.output.insert(tk.END, str(e))
            finally:
                self.process = None

        threading.Thread(target=target).start()

    def stop_code(self):
        if self.process:
            self.process.terminate()
            self.output.insert(tk.END, "\n[Zatrzymano]\n")
            self.process = None

    def on_key_release(self, event):
        self.highlight_syntax()
        self.update_line_numbers()
        self.draw_indent_guides()

    def highlight_syntax(self):
        code = self.text.get("1.0", tk.END)
        self.text.tag_remove("keyword", "1.0", tk.END)
        self.text.tag_remove("string", "1.0", tk.END)
        self.text.tag_remove("comment", "1.0", tk.END)
        self.text.tag_remove("function", "1.0", tk.END)
        self.text.tag_remove("self", "1.0", tk.END)

        for match in re.finditer(r"\b(def|class|return|if|else|elif|while|for|try|except|import|from|as|pass|with|yield|lambda|in|is|and|or|not|global|nonlocal|assert|break|continue|finally|del|raise)\b", code):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text.tag_add("keyword", start, end)

        for match in re.finditer(r"#.*", code):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text.tag_add("comment", start, end)

        for match in re.finditer(r"(['\"])((?:(?!\1).)*)\1", code):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text.tag_add("string", start, end)

        for match in re.finditer(r"\bself\b", code):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text.tag_add("self", start, end)

        for match in re.finditer(r"def\s+(\w+)", code):
            start = f"1.0+{match.start(1)}c"
            end = f"1.0+{match.end(1)}c"
            self.text.tag_add("function", start, end)

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

if __name__ == "__main__":
    root = tk.Tk()
    app = PythonEditor(root)
    root.mainloop()