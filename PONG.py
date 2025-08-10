import tkinter as tk
import random

# ====== USTAWIENIA ======
CANVAS_W = 800
CANVAS_H = 400
PADDLE_W = 12
PADDLE_H = 100
PADDLE_SPEED = 40        # ~40 zgodnie z prośbą
BALL_SIZE = 18
BALL_SPEED_X = 6
BALL_SPEED_Y = 4
TICK_MS = 20             # czas pętli gry (co ~20ms)

# ====== GŁÓWNE OKNO ======
root = tk.Tk()
root.title("Pong")
root.resizable(False, False)

# ---------- MENU (frame) ----------
menu_frame = tk.Frame(root, padx=20, pady=20)
menu_frame.pack(fill="both", expand=True)

tk.Label(menu_frame, text="PONG", font=("Arial", 28, "bold")).pack(pady=(10, 20))
tk.Label(menu_frame, text="Wybierz tryb gry:", font=("Arial", 14)).pack(pady=(0,10))

chosen_mode = tk.IntVar(value=1)  # 1 = vs AI, 2 = PvP
rb1 = tk.Radiobutton(menu_frame, text="Gracz vs AI", variable=chosen_mode, value=1, font=("Arial", 12))
rb2 = tk.Radiobutton(menu_frame, text="Gracz vs Gracz", variable=chosen_mode, value=2, font=("Arial", 12))
rb1.pack(anchor="w", padx=40, pady=6)
rb2.pack(anchor="w", padx=40, pady=6)

tk.Label(menu_frame, text="Paletki: szybkie (≈40)", font=("Arial", 10)).pack(pady=(10,5))

start_btn = tk.Button(menu_frame, text="Start", font=("Arial", 12), width=16)
start_btn.pack(pady=18)

# ---------- ELEMENTY GRY (utworzymy później) ----------
game_frame = None
canvas = None
score_label = None
controls_frame = None

# stan gry (będzie inicjalizowany przy starcie)
state = {}

# ====== RUCH PRZY TRZYMANIU PRZYCISKU: pomocnicze ======
def start_hold_move(paddle_key, dy):
    """rozpocznij ciągły ruch paletki podczas trzymania przycisku"""
    state[f"hold_{paddle_key}"] = True
    def loop():
        if state.get(f"hold_{paddle_key}", False):
            move_paddle(paddle_key, dy)
            root.after(60, loop)  # jak często wykonuje się ruch przy trzymaniu
    loop()

def stop_hold_move(paddle_key):
    state[f"hold_{paddle_key}"] = False

# ====== FUNKCJE GŁÓWNE GRY ======
def move_paddle(which, dy):
    """which: 'left' lub 'right' - porusza paletkę o dy (z ograniczeniami)"""
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
    # losowy kierunek
    state["ball_dx"] = random.choice([-BALL_SPEED_X, BALL_SPEED_X])
    state["ball_dy"] = random.choice([-BALL_SPEED_Y, BALL_SPEED_Y])

def update_score_label():
    state["score_label"].config(text=f"{state['score_left']}  :  {state['score_right']}")

def game_tick():
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
        state["ball_dx"] = abs(state["ball_dx"])
        # odrobina losowej wariacji y
        state["ball_dy"] += random.choice([-1, 0, 1])

    # prawa paletka
    if bx2 >= rx1 and by2 >= ry1 and by1 <= ry2 and state["ball_dx"] > 0:
        state["ball_dx"] = -abs(state["ball_dx"])
        state["ball_dy"] += random.choice([-1, 0, 1])

    # punktacja
    if bx1 <= 0:
        state["score_right"] += 1
        update_score_label()
        reset_ball()
    elif bx2 >= CANVAS_W:
        state["score_left"] += 1
        update_score_label()
        reset_ball()

    # AI (jeśli włączone)
    if state["mode"] == 1:
        # AI reaguje powoli i tylko gdy piłka leci do prawej
        if state["ball_dx"] > 0:
            # prosty algorytm: dążenie środka paletki do środka piłki
            paddle_center = (ry1 + ry2) / 2
            ball_center = (by1 + by2) / 2
            if paddle_center < ball_center - 10:
                move_paddle("right", PADDLE_SPEED//3)
            elif paddle_center > ball_center + 10:
                move_paddle("right", -PADDLE_SPEED//3)

    # uruchom kolejny tick
    root.after(TICK_MS, game_tick)

# ====== TWORZENIE UI GRY ======
def start_play(mode):
    """Wywołane po wyborze trybu z menu. mode: 1=vsAI, 2=PvP"""
    # ukryj menu frame i zbuduj UI gry w tym samym oknie
    menu_frame.pack_forget()

    # frame gry
    global game_frame, canvas, score_label, controls_frame
    game_frame = tk.Frame(root)
    game_frame.pack()

    canvas = tk.Canvas(game_frame, width=CANVAS_W, height=CANVAS_H, bg="black", highlightthickness=0)
    canvas.pack()

    # liczniki pod oknem (między canvas a przyciskami)
    score_label = tk.Label(game_frame, text="0  :  0", font=("Arial", 16))
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

    # spacer
    spacer = tk.Label(controls_frame, text="   ", width=8)
    spacer.grid(row=0, column=1)

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
    state["score_left"] = 0
    state["score_right"] = 0
    state["mode"] = mode

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

    # losowy kierunek piłki
    state["ball_dx"] = random.choice([-BALL_SPEED_X, BALL_SPEED_X])
    state["ball_dy"] = random.choice([-BALL_SPEED_Y, BALL_SPEED_Y])

    # ustaw lokalny label punktów
    state["score_left"] = 0
    state["score_right"] = 0
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
        # vs AI: dezaktywuj przyciski prawej paletki (albo zostaw jako informacja)
        btn_r_up.config(state="disabled")
        btn_r_dn.config(state="disabled")

    # dodatkowo: sterowanie klawiaturą (opcjonalne)
    def key_press(ev):
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

    # rysuj środkową przerwany pasek (opcjonalne)
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