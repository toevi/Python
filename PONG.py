import tkinter as tk
import random

# ====== USTAWIENIA ======
CANVAS_W = 800
CANVAS_H = 400
PADDLE_W = 12
PADDLE_H = 100
PADDLE_SPEED = 40
BALL_SIZE = 18
TICK_MS = 20
WIN_SCORE = 10

# Poziomy trudności
DIFFICULTY_LEVELS = {
    1: {"name": "Easy", "ball_speed_x": 4, "ball_speed_y": 3, "ai_speed": 25},
    2: {"name": "Medium", "ball_speed_x": 6, "ball_speed_y": 4, "ai_speed": 35},
    3: {"name": "Hard", "ball_speed_x": 8, "ball_speed_y": 6, "ai_speed": 45}
}

# ====== GŁÓWNE OKNO ======
root = tk.Tk()
root.title("Pong")
root.resizable(False, False)

# ---------- MENU (frame) ----------
menu_frame = tk.Frame(root, padx=20, pady=20)
menu_frame.pack(fill="both", expand=True)

tk.Label(menu_frame, text="PONG", font=("Arial", 28, "bold")).pack(pady=(10, 20))

# Wybór trybu gry
tk.Label(menu_frame, text="Choose game mode:", font=("Arial", 14)).pack(pady=(0,10))

chosen_mode = tk.IntVar(value=1)  # 1 = vs AI, 2 = PvP
rb1 = tk.Radiobutton(menu_frame, text="Player vs AI", variable=chosen_mode, value=1, font=("Arial", 12))
rb2 = tk.Radiobutton(menu_frame, text="Player vs Player", variable=chosen_mode, value=2, font=("Arial", 12))
rb1.pack(anchor="w", padx=40, pady=6)
rb2.pack(anchor="w", padx=40, pady=6)

# Wybór poziomu trudności
tk.Label(menu_frame, text="Difficulty level:", font=("Arial", 14)).pack(pady=(20,10))

chosen_difficulty = tk.IntVar(value=2)  # domyślnie średni
for level, config in DIFFICULTY_LEVELS.items():
    rb = tk.Radiobutton(menu_frame, text=config['name'], 
                        variable=chosen_difficulty, value=level, font=("Arial", 11))
    rb.pack(anchor="w", padx=40, pady=3)

tk.Label(menu_frame, text="Game to 10 points", font=("Arial", 10)).pack(pady=(10,5))

start_btn = tk.Button(menu_frame, text="Start", font=("Arial", 12), width=16)
start_btn.pack(pady=18)

# ---------- ELEMENTY GRY (utworzymy później) ----------
game_frame = None
canvas = None
score_label = None
controls_frame = None
game_over_frame = None

# stan gry (będzie inicjalizowany przy starcie)
state = {}

# ====== RUCH PRZY TRZYMANIU PRZYCISKU: pomocnicze ======
def start_hold_move(paddle_key, dy):
    """rozpocznij ciągły ruch paletki podczas trzymania przycisku"""
    if state.get("game_running", False):
        state[f"hold_{paddle_key}"] = True
        def loop():
            if state.get(f"hold_{paddle_key}", False) and state.get("game_running", False):
                move_paddle(paddle_key, dy)
                root.after(60, loop)  # jak często wykonuje się ruch przy trzymaniu
        loop()

def stop_hold_move(paddle_key):
    state[f"hold_{paddle_key}"] = False

# ====== FUNKCJE GŁÓWNE GRY ======
def move_paddle(which, dy):
    """which: 'left' lub 'right' - porusza paletkę o dy (z ograniczeniami)"""
    if not state.get("game_running", False):
        return
    
    c = state["canvas"]
    if which == "left":
        item = state["paddle_left"]
    else:
        item = state["paddle_right"]
    c.move(item, 0, dy)
    x1, y1, x2, y2 = c.coords(item)
    # ograniczenie w pionie
    if y1 < 0:
        c.move(item, 0, -y1)
    if y2 > CANVAS_H:
        c.move(item, 0, CANVAS_H - y2)

def reset_ball():
    c = state["canvas"]
    c.coords(state["ball"], CANVAS_W//2 - BALL_SIZE//2, CANVAS_H//2 - BALL_SIZE//2,
             CANVAS_W//2 + BALL_SIZE//2, CANVAS_H//2 + BALL_SIZE//2)
    
    # resetuj prędkość do bazowych wartości z poziomu trudności
    state["ball_dx"] = random.choice([-state["base_ball_speed_x"], state["base_ball_speed_x"]])
    state["ball_dy"] = random.choice([-state["base_ball_speed_y"], state["base_ball_speed_y"]])

def update_score_label():
    difficulty_name = DIFFICULTY_LEVELS[state["difficulty"]]["name"]
    mode_text = "PvP" if state["mode"] == 2 else "vs AI"
    state["score_label"].config(text=f"{state['score_left']}  :  {state['score_right']}  |  {difficulty_name}  |  {mode_text}")

def check_game_over():
    """Sprawdza czy gra się skończyła (10 punktów)"""
    if state["score_left"] >= WIN_SCORE or state["score_right"] >= WIN_SCORE:
        state["game_running"] = False
        
        # określ zwycięzcę
        if state["score_left"] >= WIN_SCORE:
            winner = "Left player wins!"
        else:
            winner = "Right player wins!" if state["mode"] == 2 else "AI wins!"
        
        show_game_over(winner)
        return True
    return False

def show_game_over(winner_text):
    """Pokazuje ekran końca gry"""
    global game_over_frame
    
    # ukryj elementy gry (ale zostaw canvas żeby zobaczyć końcowy stan)
    controls_frame.pack_forget()
    
    # pokaż ekran końca gry
    game_over_frame = tk.Frame(game_frame)
    game_over_frame.pack(pady=20)
    
    tk.Label(game_over_frame, text="GAME OVER!", font=("Arial", 20, "bold"), fg="red").pack(pady=10)
    tk.Label(game_over_frame, text=winner_text, font=("Arial", 16)).pack(pady=5)
    
    buttons_frame = tk.Frame(game_over_frame)
    buttons_frame.pack(pady=15)
    
    new_game_btn = tk.Button(buttons_frame, text="New Game", font=("Arial", 12), width=12, command=restart_game)
    menu_btn = tk.Button(buttons_frame, text="Main Menu", font=("Arial", 12), width=12, command=back_to_menu)
    
    new_game_btn.pack(side="left", padx=10)
    menu_btn.pack(side="left", padx=10)

def restart_game():
    """Całkowicie restartuje grę - wraca do menu wyboru poziomu"""
    cleanup_game()
    menu_frame.pack(fill="both", expand=True)

def back_to_menu():
    """Powraca do menu głównego"""
    cleanup_game()
    menu_frame.pack(fill="both", expand=True)

def cleanup_game():
    """Czyści wszystkie elementy gry"""
    global game_frame, canvas, score_label, controls_frame, game_over_frame
    
    # zatrzymaj grę
    state["game_running"] = False
    
    # usuń wszystkie hold states
    for key in list(state.keys()):
        if key.startswith("hold_"):
            del state[key]
    
    # usuń frame gry
    if game_frame:
        game_frame.destroy()
        game_frame = None
        canvas = None
        score_label = None
        controls_frame = None
        game_over_frame = None

def game_tick():
    if not state.get("game_running", False):
        return
        
    c = state["canvas"]
    # przesuwamy piłkę
    c.move(state["ball"], state["ball_dx"], state["ball_dy"])
    bx1, by1, bx2, by2 = c.coords(state["ball"])

    # odbicie od góry/dół
    if by1 <= 0 or by2 >= CANVAS_H:
        state["ball_dy"] *= -1

    # kolizje z paletkami
    lx1, ly1, lx2, ly2 = c.coords(state["paddle_left"])
    rx1, ry1, rx2, ry2 = c.coords(state["paddle_right"])

    # lewa paletka
    if bx1 <= lx2 and by2 >= ly1 and by1 <= ly2 and state["ball_dx"] < 0:
        # odbij w przeciwnym kierunku, zachowując bazową prędkość X
        state["ball_dx"] = state["base_ball_speed_x"]
        # resetuj Y do bazowej prędkości z małą losową wariancją
        state["ball_dy"] = random.choice([-state["base_ball_speed_y"], state["base_ball_speed_y"]])
        state["ball_dy"] += random.choice([-1, 0, 1])

    # prawa paletka
    if bx2 >= rx1 and by2 >= ry1 and by1 <= ry2 and state["ball_dx"] > 0:
        # odbij w przeciwnym kierunku, zachowując bazową prędkość X
        state["ball_dx"] = -state["base_ball_speed_x"]
        # resetuj Y do bazowej prędkości z małą losową wariancją
        state["ball_dy"] = random.choice([-state["base_ball_speed_y"], state["base_ball_speed_y"]])
        state["ball_dy"] += random.choice([-1, 0, 1])

    # punktacja
    if bx1 <= 0:
        state["score_right"] += 1
        update_score_label()
        if not check_game_over():  # sprawdź czy gra się skończyła
            reset_ball()
    elif bx2 >= CANVAS_W:
        state["score_left"] += 1
        update_score_label()
        if not check_game_over():  # sprawdź czy gra się skończyła
            reset_ball()

    # AI (jeśli włączone)
    if state["mode"] == 1:
        # AI reaguje z prędkością zależną od poziomu trudności
        if state["ball_dx"] > 0:
            # prosty algorytm: dążenie środka paletki do środka piłki
            paddle_center = (ry1 + ry2) / 2
            ball_center = (by1 + by2) / 2
            ai_speed = DIFFICULTY_LEVELS[state["difficulty"]]["ai_speed"]
            if paddle_center < ball_center - 10:
                move_paddle("right", ai_speed//3)
            elif paddle_center > ball_center + 10:
                move_paddle("right", -ai_speed//3)

    # uruchom kolejny tick tylko jeśli gra trwa
    if state.get("game_running", False):
        root.after(TICK_MS, game_tick)

# ====== TWORZENIE UI GRY ======
def start_play(mode):
    """Wywołane po wyborze trybu z menu. mode: 1=vsAI, 2=PvP"""
    # ukryj menu frame i zbuduj UI gry w tym samym oknie
    menu_frame.pack_forget()

    # pobierz wybrany poziom trudności
    difficulty = chosen_difficulty.get()

    # frame gry
    global game_frame, canvas, score_label, controls_frame
    game_frame = tk.Frame(root)
    game_frame.pack()

    canvas = tk.Canvas(game_frame, width=CANVAS_W, height=CANVAS_H, bg="black", highlightthickness=0)
    canvas.pack()

    # liczniki pod oknem (między canvas a przyciskami)
    difficulty_name = DIFFICULTY_LEVELS[difficulty]["name"]
    info_text = f"0  :  0  |  {difficulty_name}"
    if mode == 2:
        info_text += "  |  PvP"
    else:
        info_text += "  |  vs AI"
    
    score_label = tk.Label(game_frame, text=info_text, font=("Arial", 14))
    score_label.pack(pady=(6, 8))

    # controls frame - przyciski pod spodem
    controls_frame = tk.Frame(game_frame)
    controls_frame.pack(pady=(0,10))

    # lewa paletka przyciski (kolumna)
    left_frame = tk.Frame(controls_frame)
    left_frame.grid(row=0, column=0, padx=30)
    btn_l_up = tk.Button(left_frame, text="↑", font=("Arial", 14), width=4, height=1)
    btn_l_dn = tk.Button(left_frame, text="↓", font=("Arial", 14), width=4, height=1)
    btn_l_up.grid(row=0, column=0, pady=4)
    btn_l_dn.grid(row=1, column=0, pady=4)

    # środek - przycisk new game
    center_frame = tk.Frame(controls_frame)
    center_frame.grid(row=0, column=1, padx=20)
    new_game_btn = tk.Button(center_frame, text="New Game", font=("Arial", 10), width=8, command=restart_game)
    new_game_btn.pack()

    # prawa paletka przyciski (kolumna)
    right_frame = tk.Frame(controls_frame)
    right_frame.grid(row=0, column=2, padx=30)
    btn_r_up = tk.Button(right_frame, text="↑", font=("Arial", 14), width=4, height=1)
    btn_r_dn = tk.Button(right_frame, text="↓", font=("Arial", 14), width=4, height=1)
    btn_r_up.grid(row=0, column=0, pady=4)
    btn_r_dn.grid(row=1, column=0, pady=4)

    # inicjalizacja stanu
    state["canvas"] = canvas
    state["score_label"] = score_label
    state["mode"] = mode
    state["difficulty"] = difficulty
    state["game_running"] = True
    state["score_left"] = 0
    state["score_right"] = 0
    
    # zapisz bazowe prędkości dla tego poziomu trudności
    difficulty_config = DIFFICULTY_LEVELS[difficulty]
    state["base_ball_speed_x"] = difficulty_config["ball_speed_x"]
    state["base_ball_speed_y"] = difficulty_config["ball_speed_y"]

    # paletki & piłka
    left_x = 20
    left_y = CANVAS_H//2 - PADDLE_H//2
    right_x = CANVAS_W - 20 - PADDLE_W
    right_y = left_y
    state["paddle_left"] = canvas.create_rectangle(left_x, left_y, left_x + PADDLE_W, left_y + PADDLE_H, fill="white")
    state["paddle_right"] = canvas.create_rectangle(right_x, right_y, right_x + PADDLE_W, right_y + PADDLE_H, fill="white")
    bx = CANVAS_W//2 - BALL_SIZE//2
    by = CANVAS_H//2 - BALL_SIZE//2
    state["ball"] = canvas.create_oval(bx, by, bx + BALL_SIZE, by + BALL_SIZE, fill="white")

    # ustaw początkową prędkość piłki
    state["ball_dx"] = random.choice([-state["base_ball_speed_x"], state["base_ball_speed_x"]])
    state["ball_dy"] = random.choice([-state["base_ball_speed_y"], state["base_ball_speed_y"]])

    # zaktualizuj label punktów
    update_score_label()

    # przypnij działania przycisków - przytrzymanie = ruch ciągły
    btn_l_up.bind("<ButtonPress-1>", lambda e: start_hold_move("left", -PADDLE_SPEED))
    btn_l_up.bind("<ButtonRelease-1>", lambda e: stop_hold_move("left"))
    btn_l_dn.bind("<ButtonPress-1>", lambda e: start_hold_move("left", PADDLE_SPEED))
    btn_l_dn.bind("<ButtonRelease-1>", lambda e: stop_hold_move("left"))

    if mode == 2:
        # PvP: prawa paletka sterowana przyciskami
        btn_r_up.bind("<ButtonPress-1>", lambda e: start_hold_move("right", -PADDLE_SPEED))
        btn_r_up.bind("<ButtonRelease-1>", lambda e: stop_hold_move("right"))
        btn_r_dn.bind("<ButtonPress-1>", lambda e: start_hold_move("right", PADDLE_SPEED))
        btn_r_dn.bind("<ButtonRelease-1>", lambda e: stop_hold_move("right"))
    else:
        # vs AI: dezaktywuj przyciski prawej paletki
        btn_r_up.config(state="disabled")
        btn_r_dn.config(state="disabled")

    # sterowanie klawiaturą
    def key_press(ev):
        if not state.get("game_running", False):
            return
            
        k = ev.keysym.lower()
        if k == "w":
            move_paddle("left", -PADDLE_SPEED)
        elif k == "s":
            move_paddle("left", PADDLE_SPEED)
        elif mode == 2:
            if ev.keysym == "Up":
                move_paddle("right", -PADDLE_SPEED)
            elif ev.keysym == "Down":
                move_paddle("right", PADDLE_SPEED)

    root.bind_all("<KeyPress>", key_press)

    # rysuj środkową przerwany pasek
    for y in range(0, CANVAS_H, 24):
        canvas.create_line(CANVAS_W//2, y, CANVAS_W//2, y+12, fill="gray")

    # start pętli gry
    root.after(TICK_MS, game_tick)

# ====== PODŁĄCZENIE PRZYCISKU START ======
def on_start_click():
    mode = chosen_mode.get()  # 1 albo 2
    start_play(mode)

start_btn.config(command=on_start_click)

# ====== URUCHOMIENIE APLIKACJI ======
root.mainloop()