"""
Banking Transaction Visualizer
================================
A GUI app that simulates concurrent banking transactions,
detects conflicts, builds a precedence graph, runs DFS cycle
detection, and performs rollback on unsafe schedules.

Run:  python main.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import networkx as nx

from accounts import Account
from transactions import build_schedule
from conflict_detector import detect_conflicts
from graph_generator import build_precedence_graph, draw_graph
from cycle_detection import has_cycle, find_cycle_path
from rollback import RollbackManager
from scheduler import execute_schedule

# ─────────────────────────────────────────────
# Colour palette
# ─────────────────────────────────────────────
BG       = "#0f1923"
PANEL    = "#162032"
ACCENT   = "#00bcd4"
ACCENT2  = "#ff6b35"
TEXT     = "#e8eaf6"
SUBTEXT  = "#90a4ae"
GREEN    = "#26a69a"
RED      = "#ef5350"
BORDER   = "#1e3048"

FONT_H   = ("Courier New", 13, "bold")
FONT_B   = ("Courier New", 10)
FONT_S   = ("Courier New", 9)


# ─────────────────────────────────────────────
# Preset Schedules for demo
# ─────────────────────────────────────────────
PRESETS = {
    "Safe Schedule": [
        ("T1", "read",  "A", 0),
        ("T1", "write", "A", -2000),
        ("T2", "read",  "B", 0),
        ("T2", "write", "B", 3000),
    ],
    "Unsafe — Write-Write": [
        ("T1", "read",  "A", 0),
        ("T2", "write", "A", 1000),
        ("T1", "write", "A", -500),
        ("T2", "read",  "A", 0),
    ],
    "Unsafe — Cycle T1↔T2": [
        ("T1", "read",  "A", 0),
        ("T2", "write", "A", 500),
        ("T2", "read",  "B", 0),
        ("T1", "write", "B", -1000),
    ],
    "3-Transaction Safe": [
        ("T1", "read",  "A", 0),
        ("T1", "write", "A", -1000),
        ("T2", "read",  "B", 0),
        ("T3", "write", "B", 2000),
        ("T2", "write", "C", -500),
    ],
}

QUIZ_SCENARIOS = [
    {
        "schedule": [
            ("T1", "read",  "X", 0),
            ("T2", "write", "X", 100),
            ("T1", "write", "X", -50),
        ],
        "answer": "Unsafe",
        "hint": "T1 reads X before T2 writes → T1 must precede T2.\nBut T1 also writes X after T2 → T2 must precede T1.\nThis creates a cycle!"
    },
    {
        "schedule": [
            ("T1", "read",  "A", 0),
            ("T1", "write", "A", -200),
            ("T2", "read",  "B", 0),
            ("T2", "write", "B", 300),
        ],
        "answer": "Safe",
        "hint": "T1 and T2 operate on different accounts.\nNo conflict → no edge in the precedence graph → no cycle."
    },
    {
        "schedule": [
            ("T1", "write", "A", 500),
            ("T2", "read",  "A", 0),
            ("T2", "write", "B", -200),
            ("T3", "read",  "B", 0),
        ],
        "answer": "Safe",
        "hint": "T1→T2 (write then read on A), T2→T3 (write then read on B).\nLinear chain — no cycle → SAFE."
    },
]


class BankingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Banking Transaction Visualizer")
        self.configure(bg=BG)
        self.geometry("1280x820")
        self.resizable(True, True)

        # State
        self.accounts = {
            "A": Account("A", "Alice",   10000),
            "B": Account("B", "Bob",      8000),
            "C": Account("C", "Carol",    6000),
            "X": Account("X", "Xavier",   5000),
        }
        self.rollback_mgr = RollbackManager()
        self.current_schedule = []
        self.quiz_idx = 0

        # Build UI
        self._build_header()
        self._build_notebook()
        self._update_account_labels()

    # ───────── Header ─────────
    def _build_header(self):
        hf = tk.Frame(self, bg=ACCENT, height=4)
        hf.pack(fill="x")

        top = tk.Frame(self, bg=BG, pady=10)
        top.pack(fill="x", padx=20)

        tk.Label(top, text="⬡ BANKING TRANSACTION VISUALIZER",
                 bg=BG, fg=ACCENT, font=("Courier New", 16, "bold")).pack(side="left")
        tk.Label(top, text="Concurrency · Graph · DFS",
                 bg=BG, fg=SUBTEXT, font=FONT_S).pack(side="left", padx=12)

    # ───────── Notebook Tabs ─────────
    def _build_notebook(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=TEXT,
                        font=FONT_B, padding=(14, 6))
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.tab_accounts   = self._make_frame(nb)
        self.tab_scheduler  = self._make_frame(nb)
        self.tab_graph      = self._make_frame(nb)
        self.tab_quiz       = self._make_frame(nb)

        nb.add(self.tab_accounts,  text="  Accounts  ")
        nb.add(self.tab_scheduler, text="  Scheduler  ")
        nb.add(self.tab_graph,     text="  Graph / DFS  ")
        nb.add(self.tab_quiz,      text="  Quiz Mode  ")

        self._build_accounts_tab()
        self._build_scheduler_tab()
        self._build_graph_tab()
        self._build_quiz_tab()

    def _make_frame(self, parent):
        f = tk.Frame(parent, bg=BG)
        return f

    # ═══════════════════════════════════════════
    # TAB 1 — Accounts
    # ═══════════════════════════════════════════
    def _build_accounts_tab(self):
        f = self.tab_accounts
        tk.Label(f, text="Account Balances", bg=BG, fg=ACCENT,
                 font=FONT_H).pack(pady=(16, 8))

        self.acc_frame = tk.Frame(f, bg=BG)
        self.acc_frame.pack()

        self.acc_labels = {}

        # Quick-action panel
        action = tk.LabelFrame(f, text=" Quick Action ", bg=PANEL,
                                fg=ACCENT, font=FONT_B, bd=1, relief="groove")
        action.pack(padx=40, pady=20, fill="x")

        row1 = tk.Frame(action, bg=PANEL)
        row1.pack(pady=8)

        for label, val in [("Account:", ""), ("Amount ₹:", "")]:
            tk.Label(row1, text=label, bg=PANEL, fg=TEXT, font=FONT_B).pack(side="left", padx=4)
            e = tk.Entry(row1, width=8, bg=BORDER, fg=TEXT, insertbackground=TEXT,
                         font=FONT_B, relief="flat")
            e.pack(side="left", padx=4)
            if "Account" in label:
                self.qa_acc = e
                e.insert(0, "A")
            else:
                self.qa_amt = e
                e.insert(0, "1000")

        row2 = tk.Frame(action, bg=PANEL)
        row2.pack(pady=6)
        for text, cmd in [("Deposit", self._qa_deposit),
                           ("Withdraw", self._qa_withdraw)]:
            btn = tk.Button(row2, text=text, command=cmd,
                            bg=GREEN if text == "Deposit" else RED,
                            fg="white", font=FONT_B, relief="flat",
                            padx=16, pady=5, cursor="hand2")
            btn.pack(side="left", padx=8)

        btn_reset = tk.Button(action, text="↺ Reset All Balances",
                              command=self._reset_balances,
                              bg=ACCENT2, fg="white", font=FONT_B,
                              relief="flat", padx=12, pady=4, cursor="hand2")
        btn_reset.pack(pady=(4, 10))

    def _update_account_labels(self):
        for w in self.acc_frame.winfo_children():
            w.destroy()

        colors = [ACCENT, ACCENT2, GREEN, "#ab47bc"]
        for i, (aid, acc) in enumerate(self.accounts.items()):
            c = colors[i % len(colors)]
            card = tk.Frame(self.acc_frame, bg=PANEL, bd=0, relief="flat",
                            padx=24, pady=16)
            card.grid(row=0, column=i, padx=14, pady=8)
            tk.Label(card, text=aid, bg=PANEL, fg=c,
                     font=("Courier New", 22, "bold")).pack()
            tk.Label(card, text=acc.name, bg=PANEL, fg=TEXT,
                     font=FONT_B).pack()
            lbl = tk.Label(card, text=f"₹{acc.balance:,}", bg=PANEL, fg=c,
                           font=("Courier New", 18, "bold"))
            lbl.pack(pady=4)
            self.acc_labels[aid] = lbl

    def _qa_deposit(self):
        self._qa_action("deposit")

    def _qa_withdraw(self):
        self._qa_action("withdraw")

    def _qa_action(self, action):
        aid = self.qa_acc.get().strip().upper()
        try:
            amt = float(self.qa_amt.get())
        except ValueError:
            messagebox.showerror("Input Error", "Invalid amount.")
            return
        if aid not in self.accounts:
            messagebox.showerror("Error", f"Account '{aid}' not found.")
            return
        try:
            if action == "deposit":
                self.accounts[aid].deposit(amt)
            else:
                self.accounts[aid].withdraw(amt)
            self._update_account_labels()
        except ValueError as e:
            messagebox.showerror("Transaction Failed", str(e))

    def _reset_balances(self):
        defaults = {"A": 10000, "B": 8000, "C": 6000, "X": 5000}
        for aid, bal in defaults.items():
            self.accounts[aid].balance = bal
        self._update_account_labels()
        messagebox.showinfo("Reset", "All balances restored to defaults.")

    # ═══════════════════════════════════════════
    # TAB 2 — Scheduler
    # ═══════════════════════════════════════════
    def _build_scheduler_tab(self):
        f = self.tab_scheduler

        left = tk.Frame(f, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=12, pady=12)

        right = tk.Frame(f, bg=BG)
        right.pack(side="right", fill="both", expand=True, padx=12, pady=12)

        # ── Left: Schedule editor ──
        tk.Label(left, text="Schedule Editor", bg=BG, fg=ACCENT,
                 font=FONT_H).pack(anchor="w")
        tk.Label(left, text="Format: TID  OP  ACCOUNT  AMOUNT\n"
                             "OP: read or write | AMOUNT: positive=deposit, negative=withdraw",
                 bg=BG, fg=SUBTEXT, font=FONT_S, justify="left").pack(anchor="w", pady=(2, 6))

        self.schedule_editor = scrolledtext.ScrolledText(
            left, width=44, height=14, bg=PANEL, fg=TEXT,
            insertbackground=TEXT, font=("Courier New", 11),
            relief="flat", bd=0)
        self.schedule_editor.pack(fill="both", expand=True)
        self._load_preset_text("Safe Schedule")

        # Presets
        pf = tk.Frame(left, bg=BG)
        pf.pack(fill="x", pady=6)
        tk.Label(pf, text="Preset:", bg=BG, fg=TEXT, font=FONT_B).pack(side="left")
        self.preset_var = tk.StringVar(value="Safe Schedule")
        combo = ttk.Combobox(pf, textvariable=self.preset_var,
                             values=list(PRESETS.keys()), width=24,
                             font=FONT_B, state="readonly")
        combo.pack(side="left", padx=6)
        combo.bind("<<ComboboxSelected>>",
                   lambda e: self._load_preset_text(self.preset_var.get()))

        btn_run = tk.Button(left, text="▶  RUN SCHEDULE",
                            command=self._run_schedule,
                            bg=ACCENT, fg=BG, font=FONT_H,
                            relief="flat", padx=20, pady=8, cursor="hand2")
        btn_run.pack(pady=6)

        # ── Right: Execution log ──
        tk.Label(right, text="Execution Log", bg=BG, fg=ACCENT,
                 font=FONT_H).pack(anchor="w")

        self.exec_log = scrolledtext.ScrolledText(
            right, width=46, height=20, bg=PANEL, fg=TEXT,
            insertbackground=TEXT, font=("Courier New", 10),
            relief="flat", bd=0, state="disabled")
        self.exec_log.pack(fill="both", expand=True)

        self.status_banner = tk.Label(right, text="",
                                      bg=BG, fg=TEXT, font=FONT_H)
        self.status_banner.pack(pady=6)

        btn_rollback = tk.Button(right, text="↺ ROLLBACK",
                                 command=self._do_rollback,
                                 bg=ACCENT2, fg="white", font=FONT_B,
                                 relief="flat", padx=12, pady=5, cursor="hand2")
        btn_rollback.pack()

    def _load_preset_text(self, name):
        steps = PRESETS.get(name, [])
        self.schedule_editor.delete("1.0", "end")
        for tid, op, acc, amt in steps:
            self.schedule_editor.insert("end", f"{tid}  {op}  {acc}  {amt}\n")

    def _parse_editor(self):
        lines = self.schedule_editor.get("1.0", "end").strip().splitlines()
        schedule = []
        for ln in lines:
            parts = ln.split()
            if len(parts) < 3:
                continue
            tid, op, acc = parts[0], parts[1].lower(), parts[2].upper()
            amount = float(parts[3]) if len(parts) >= 4 else 0
            schedule.append((tid, op, acc, amount))
        return schedule

    def _run_schedule(self):
        raw = self._parse_editor()
        if not raw:
            messagebox.showwarning("Empty", "No schedule to run.")
            return

        self.rollback_mgr.save_checkpoint(self.accounts)
        schedule = build_schedule(raw)
        self.current_schedule = schedule

        logs = []
        logs.append("═" * 44)
        logs.append(" EXECUTING SCHEDULE")
        logs.append("═" * 44)

        exec_logs = execute_schedule(schedule, self.accounts,
                                     log_fn=lambda m: None)
        logs.extend(exec_logs)

        conflicts = detect_conflicts(schedule)
        logs.append("")
        logs.append("─" * 44)
        logs.append(f" CONFLICTS DETECTED: {len(conflicts)}")
        for c in conflicts:
            logs.append(f"  {c[0]} ↔ {c[1]} on {c[2]}  [{c[3]}]")

        G = build_precedence_graph(conflicts)
        cycle = has_cycle(G)
        path = find_cycle_path(G)

        logs.append("")
        logs.append("─" * 44)
        if cycle:
            logs.append(f" ⚠ CYCLE DETECTED: {' → '.join(path)}")
            logs.append(" SCHEDULE IS UNSAFE")
            self.status_banner.config(text="⚠ UNSAFE SCHEDULE", fg=RED, bg=BG)
        else:
            logs.append(" ✓ NO CYCLE FOUND")
            logs.append(" SCHEDULE IS SAFE")
            self.status_banner.config(text="✓ SAFE SCHEDULE", fg=GREEN, bg=BG)

        logs.append("═" * 44)

        self._write_log(self.exec_log, "\n".join(logs))
        self._update_account_labels()

        # Auto-update graph tab
        self._draw_main_graph(G, not cycle)

    def _do_rollback(self):
        restored = self.rollback_mgr.rollback(self.accounts)
        self._update_account_labels()
        msg = "Rolled back:\n" + "\n".join(restored) if restored else "No checkpoint to roll back."
        self._write_log(self.exec_log,
                        self.exec_log.get("1.0", "end") +
                        "\n[ROLLBACK]\n" + msg + "\n")
        messagebox.showinfo("Rollback", msg)

    def _write_log(self, widget, text):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(state="disabled")
        widget.see("end")

    # ═══════════════════════════════════════════
    # TAB 3 — Graph / DFS
    # ═══════════════════════════════════════════
    def _build_graph_tab(self):
        f = self.tab_graph

        tk.Label(f, text="Precedence Graph & DFS Cycle Detection",
                 bg=BG, fg=ACCENT, font=FONT_H).pack(pady=(12, 4))
        tk.Label(f, text="Run a schedule in the Scheduler tab to populate this graph.",
                 bg=BG, fg=SUBTEXT, font=FONT_S).pack()

        self.graph_fig, self.graph_ax = plt.subplots(figsize=(7, 5))
        self.graph_fig.patch.set_facecolor(BG)
        self.graph_ax.set_facecolor(BG)

        self.graph_canvas = FigureCanvasTkAgg(self.graph_fig, master=f)
        self.graph_canvas.get_tk_widget().pack(fill="both", expand=True,
                                                padx=20, pady=12)

        self.dfs_info = tk.Label(f, text="No graph yet.", bg=BG, fg=TEXT,
                                 font=FONT_B, wraplength=700, justify="left")
        self.dfs_info.pack(pady=6)

        # Draw empty placeholder
        G_empty = nx.DiGraph()
        draw_graph(G_empty, True, ax=self.graph_ax)
        self.graph_canvas.draw()

    def _draw_main_graph(self, G, is_safe):
        draw_graph(G, is_safe, ax=self.graph_ax)
        self.graph_canvas.draw()

        path = find_cycle_path(G)
        if path:
            info = f"DFS found cycle: {' → '.join(path)}\nSchedule is UNSAFE — rollback recommended."
            self.dfs_info.config(text=info, fg=RED)
        else:
            edges = list(G.edges())
            if edges:
                info = f"Edges: {edges}\nNo cycle found — schedule is SAFE."
            else:
                info = "No conflicts → no edges in graph → trivially SAFE."
            self.dfs_info.config(text=info, fg=GREEN)

    # ═══════════════════════════════════════════
    # TAB 4 — Quiz Mode
    # ═══════════════════════════════════════════
    def _build_quiz_tab(self):
        f = self.tab_quiz
        self.quiz_idx = 0

        tk.Label(f, text="Quiz Mode — Is this schedule Safe or Unsafe?",
                 bg=BG, fg=ACCENT, font=FONT_H).pack(pady=(16, 4))

        mid = tk.Frame(f, bg=BG)
        mid.pack(fill="both", expand=True, padx=20)

        left = tk.Frame(mid, bg=PANEL, padx=16, pady=16)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        right = tk.Frame(mid, bg=BG)
        right.pack(side="right", fill="both", expand=True)

        tk.Label(left, text="Schedule:", bg=PANEL, fg=ACCENT,
                 font=FONT_B).pack(anchor="w")
        self.quiz_schedule_lbl = tk.Label(left, text="", bg=PANEL, fg=TEXT,
                                           font=("Courier New", 11),
                                           justify="left")
        self.quiz_schedule_lbl.pack(anchor="w", pady=6)

        btn_frame = tk.Frame(left, bg=PANEL)
        btn_frame.pack(pady=12)
        tk.Button(btn_frame, text="✓  SAFE", command=lambda: self._quiz_answer("Safe"),
                  bg=GREEN, fg="white", font=FONT_H, relief="flat",
                  padx=18, pady=8, cursor="hand2").pack(side="left", padx=10)
        tk.Button(btn_frame, text="⚠  UNSAFE", command=lambda: self._quiz_answer("Unsafe"),
                  bg=RED, fg="white", font=FONT_H, relief="flat",
                  padx=18, pady=8, cursor="hand2").pack(side="left", padx=10)

        self.quiz_result_lbl = tk.Label(left, text="", bg=PANEL, fg=TEXT,
                                         font=FONT_B, wraplength=340, justify="left")
        self.quiz_result_lbl.pack(pady=8)

        self.quiz_score_lbl = tk.Label(left, text="Score: 0 / 0",
                                        bg=PANEL, fg=SUBTEXT, font=FONT_B)
        self.quiz_score_lbl.pack(pady=4)

        tk.Button(left, text="Next Question →", command=self._next_quiz,
                  bg=ACCENT, fg=BG, font=FONT_B, relief="flat",
                  padx=12, pady=5, cursor="hand2").pack(pady=4)

        # Graph area
        self.quiz_fig, self.quiz_ax = plt.subplots(figsize=(5, 4))
        self.quiz_fig.patch.set_facecolor(BG)
        self.quiz_ax.set_facecolor(BG)
        self.quiz_canvas = FigureCanvasTkAgg(self.quiz_fig, master=right)
        self.quiz_canvas.get_tk_widget().pack(fill="both", expand=True)

        self.quiz_score = [0, 0]  # [correct, total]
        self._load_quiz_question()

    def _load_quiz_question(self):
        q = QUIZ_SCENARIOS[self.quiz_idx % len(QUIZ_SCENARIOS)]
        lines = "\n".join(f"  {tid}  {op.upper():6}  {acc}  {amt if amt else ''}"
                          for tid, op, acc, amt in q["schedule"])
        self.quiz_schedule_lbl.config(text=lines)
        self.quiz_result_lbl.config(text="")
        self.quiz_ax.clear()
        self.quiz_ax.text(0.5, 0.5, "Graph revealed\nafter you answer",
                          ha="center", va="center", color=SUBTEXT,
                          fontsize=11, transform=self.quiz_ax.transAxes)
        self.quiz_ax.axis("off")
        self.quiz_canvas.draw()

    def _quiz_answer(self, user_ans):
        q = QUIZ_SCENARIOS[self.quiz_idx % len(QUIZ_SCENARIOS)]
        raw = [(tid, op, acc, amt) for tid, op, acc, amt in q["schedule"]]
        sched = [{"tid": t, "op": o, "account": a, "amount": m}
                 for t, o, a, m in raw]
        conflicts = detect_conflicts(sched)
        G = build_precedence_graph(conflicts)
        cycle = has_cycle(G)
        correct_ans = "Unsafe" if cycle else "Safe"

        self.quiz_score[1] += 1
        if user_ans == correct_ans:
            self.quiz_score[0] += 1
            result = f"✓ Correct!\n\n{q['hint']}"
            self.quiz_result_lbl.config(text=result, fg=GREEN)
        else:
            result = f"✗ Wrong. Correct: {correct_ans}\n\n{q['hint']}"
            self.quiz_result_lbl.config(text=result, fg=RED)

        self.quiz_score_lbl.config(
            text=f"Score: {self.quiz_score[0]} / {self.quiz_score[1]}")

        draw_graph(G, not cycle, ax=self.quiz_ax, title="Reveal: Precedence Graph")
        self.quiz_canvas.draw()

    def _next_quiz(self):
        self.quiz_idx += 1
        self._load_quiz_question()


# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = BankingApp()
    app.mainloop()
