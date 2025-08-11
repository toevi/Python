import tkinter as tk
import random
import time

class MatrixRain:
    def __init__(self):
        # Ustawienia okna
        self.root = tk.Tk()
        self.root.title("Matrix Rain - Opadający Kod")
        self.root.configure(bg='black')
        self.root.geometry("800x600")
        
        # Canvas do rysowania
        self.canvas = tk.Canvas(self.root, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Parametry animacji
        self.width = 800
        self.height = 600
        self.font_size = 4  # 5 razy mniejszy (20/5 = 4)
        self.columns = self.width // self.font_size
        
        # Znaki Matrix
        self.matrix_chars = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        # Kolumny z opadającym kodem
        self.drops = []
        self.init_drops()
        
        # Obsługa zamykania
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)
        self.root.bind("<Escape>", lambda e: self.close_window())
        self.root.focus_set()
        
        self.running = True
        self.animate()
    
    def init_drops(self):
        """Inicjalizuj kolumny opadającego kodu"""
        for i in range(self.columns):
            drop = {
                'x': i * self.font_size,
                'y': random.randint(-self.height, 0),
                'speed': random.randint(2, 5),  # Przyspieszenie opadania
                'chars': [random.choice(self.matrix_chars) for _ in range(random.randint(30, 80))],  # Więcej znaków w kolumnie
                'length': random.randint(30, 80)  # Dłuższe kolumny
            }
            self.drops.append(drop)
    
    def update_drops(self):
        """Aktualizuj pozycje i znaki"""
        for drop in self.drops:
            drop['y'] += drop['speed']
            
            # Losowo zmień niektóre znaki
            if random.random() < 0.1:
                for i in range(len(drop['chars'])):
                    if random.random() < 0.05:
                        drop['chars'][i] = random.choice(self.matrix_chars)
            
            # Reset gdy kolumna zejdzie poza ekran
            if drop['y'] > self.height + drop['length'] * self.font_size:
                drop['y'] = random.randint(-self.height, -self.font_size)
                drop['speed'] = random.randint(2, 5)  # Przyspieszenie opadania
                drop['length'] = random.randint(30, 80)  # Dłuższe kolumny
                drop['chars'] = [random.choice(self.matrix_chars) for _ in range(drop['length'])]
    
    def draw_drops(self):
        """Rysuj opadający kod"""
        self.canvas.delete("all")  # Wyczyść canvas
        
        for drop in self.drops:
            for i, char in enumerate(drop['chars']):
                char_y = drop['y'] + i * self.font_size
                
                # Sprawdź czy znak jest widoczny
                if -self.font_size <= char_y <= self.height:
                    # Wybierz kolor w zależności od pozycji w kolumnie
                    if i == 0:  # Pierwszy znak - najjaśniejszy
                        color = "#00FF00"  # Jasna zieleń
                    elif i < len(drop['chars']) * 0.3:  # Początek kolumny
                        color = "#00DD00"  # Średnia zieleń
                    elif i < len(drop['chars']) * 0.7:  # Środek kolumny
                        color = "#00BB00"  # Nieco ciemniejsza
                    else:  # Koniec kolumny
                        color = "#006600"  # Ciemna zieleń
                    
                    # Rysuj znak
                    self.canvas.create_text(
                        drop['x'], char_y,
                        text=char,
                        fill=color,
                        font=("Courier", self.font_size, "normal"),  # Zmiana na "normal" bo "bold" może być za grube dla małych czcionek
                        anchor="nw"
                    )
    
    def animate(self):
        """Główna pętla animacji"""
        if self.running:
            self.update_drops()
            self.draw_drops()
            self.root.after(100, self.animate)  # 100ms delay = ~10 FPS
    
    def close_window(self):
        """Zamknij okno"""
        self.running = False
        self.root.destroy()
    
    def run(self):
        """Uruchom aplikację"""
        print("Matrix Rain Effect - Tkinter")
        print("Naciśnij ESC lub zamknij okno aby wyjść")
        self.root.mainloop()

# Uruchomienie aplikacji
if __name__ == "__main__":
    matrix = MatrixRain()
    matrix.run()