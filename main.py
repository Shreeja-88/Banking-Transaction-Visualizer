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
from transactions import Operation, build_schedule
from conflict_detector import detect_conflicts
from graph_generator import build_precedence_graph, draw_graph
from cycle_detection import has_cycle, find_cycle_path
from rollback import RollbackManager

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
        self.animation_job = None
        self.animation_index = 0
        self.animation_logs = []
        self.conflict_rows = set()
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

        top = tk.Frame(f, bg=BG)
        top.pack(fill="x", padx=12, pady=(12, 6))

        tk.Label(top, text="Live Scheduler Dashboard", bg=BG, fg=ACCENT,
                 font=FONT_H).pack(anchor="w")
        tk.Label(top, text="Transactions, execution log, and precedence graph stay visible while the schedule runs.",
                 bg=BG, fg=SUBTEXT, font=FONT_S).pack(anchor="w", pady=(2, 0))

        body = tk.Frame(f, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=2)
        body.columnconfigure(2, weight=3)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        middle = tk.Frame(body, bg=BG)
        middle.grid(row=0, column=1, sticky="nsew", padx=8)

        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        tk.Label(left, text="Schedule Editor", bg=BG, fg=ACCENT,
                 font=FONT_H).pack(anchor="w")
        tk.Label(left, text="TID  OP  ACCOUNT  AMOUNT",
                 bg=BG, fg=SUBTEXT, font=FONT_S).pack(anchor="w", pady=(2, 6))

        self.schedule_editor = scrolledtext.ScrolledText(
            left, width=36, height=13, bg=PANEL, fg=TEXT,
            insertbackground=TEXT, font=("Courier New", 11),
            relief="flat", bd=0)
        self.schedule_editor.pack(fill="both", expand=False)

        pf = tk.Frame(left, bg=BG)
        pf.pack(fill="x", pady=(8, 4))
        tk.Label(pf, text="Preset:", bg=BG, fg=TEXT, font=FONT_B).pack(side="left")
        self.preset_var = tk.StringVar(value="Safe Schedule")
        combo = ttk.Combobox(pf, textvariable=self.preset_var,
                             values=list(PRESETS.keys()), width=22,
                             font=FONT_B, state="readonly")
        combo.pack(side="left", padx=(6, 0), fill="x", expand=True)
        combo.bind("<<ComboboxSelected>>",
                   lambda e: self._load_preset_text(self.preset_var.get()))

        btns = tk.Frame(left, bg=BG)
        btns.pack(fill="x", pady=6)
        self.run_button = tk.Button(btns, text="RUN ANIMATION",
                                    command=self._run_schedule,
                                    bg=ACCENT, fg=BG, font=FONT_H,
                                    relief="flat", padx=14, pady=8, cursor="hand2")
        self.run_button.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_rollback = tk.Button(btns, text="ROLLBACK",
                                 command=self._do_rollback,
                                 bg=ACCENT2, fg="white", font=FONT_B,
                                 relief="flat", padx=12, pady=8, cursor="hand2")
        btn_rollback.pack(side="left")

        self.status_banner = tk.Label(left, text="Ready to run",
                                      bg=PANEL, fg=TEXT, font=FONT_H,
                                      padx=10, pady=10)
        self.status_banner.pack(fill="x", pady=(8, 0))

        tk.Label(middle, text="Transactions", bg=BG, fg=ACCENT,
                 font=FONT_H).pack(anchor="w")
        self.txn_hint = tk.Label(middle, text="Rows highlight as each operation executes.",
                                 bg=BG, fg=SUBTEXT, font=FONT_S)
        self.txn_hint.pack(anchor="w", pady=(2, 6))

        stream = tk.Frame(middle, bg=PANEL)
        stream.pack(fill="both", expand=True)
        self.txn_canvas = tk.Canvas(stream, bg=PANEL, highlightthickness=0)
        txn_scroll = ttk.Scrollbar(stream, orient="vertical",
                                   command=self.txn_canvas.yview)
        self.txn_rows_frame = tk.Frame(self.txn_canvas, bg=PANEL)
        self.txn_rows_frame.bind(
            "<Configure>",
            lambda e: self.txn_canvas.configure(scrollregion=self.txn_canvas.bbox("all")))
        self.txn_canvas.create_window((0, 0), window=self.txn_rows_frame,
                                      anchor="nw")
        self.txn_canvas.configure(yscrollcommand=txn_scroll.set)
        self.txn_canvas.pack(side="left", fill="both", expand=True)
        txn_scroll.pack(side="right", fill="y")
        self.txn_rows = []

        self.conflict_summary = tk.Label(middle, text="No conflicts calculated yet.",
                                         bg=BG, fg=SUBTEXT, font=FONT_B,
                                         wraplength=360, justify="left")
        self.conflict_summary.pack(fill="x", pady=(8, 0))

        tk.Label(right, text="Precedence Graph", bg=BG, fg=ACCENT,
                 font=FONT_H).pack(anchor="w")
        self.live_fig, self.live_ax = plt.subplots(figsize=(5.4, 3.6))
        self.live_fig.patch.set_facecolor(BG)
        self.live_ax.set_facecolor(BG)
        self.live_canvas = FigureCanvasTkAgg(self.live_fig, master=right)
        self.live_canvas.get_tk_widget().pack(fill="both", expand=True,
                                               pady=(4, 8))

        tk.Label(right, text="Execution Log", bg=BG, fg=ACCENT,
                 font=FONT_H).pack(anchor="w")

        self.exec_log = scrolledtext.ScrolledText(
            right, width=44, height=9, bg=PANEL, fg=TEXT,
            insertbackground=TEXT, font=("Courier New", 10),
            relief="flat", bd=0, state="disabled")
        self.exec_log.pack(fill="both", expand=False)

        self._load_preset_text("Safe Schedule")
        self._refresh_live_graph([])

    def _load_preset_text(self, name):
        self._cancel_animation()
        steps = PRESETS.get(name, [])
        self.schedule_editor.delete("1.0", "end")
        for tid, op, acc, amt in steps:
            self.schedule_editor.insert("end", f"{tid}  {op}  {acc}  {amt}\n")
        if hasattr(self, "txn_rows_frame"):
            self._render_transaction_flow(build_schedule(steps))
            self._refresh_live_graph([])
            self.status_banner.config(text="Ready to run", fg=TEXT, bg=PANEL)
            self.conflict_summary.config(text="No conflicts calculated yet.",
                                         fg=SUBTEXT)

    def _parse_editor(self):
        lines = self.schedule_editor.get("1.0", "end").strip().splitlines()
        schedule = []
        for line_no, ln in enumerate(lines, start=1):
            parts = ln.split()
            if len(parts) < 3:
                continue
            tid, op, acc = parts[0], parts[1].lower(), parts[2].upper()
            if op not in (Operation.READ, Operation.WRITE):
                raise ValueError(f"Line {line_no}: op must be read or write.")
            try:
                amount = float(parts[3]) if len(parts) >= 4 else 0
            except ValueError as exc:
                raise ValueError(f"Line {line_no}: amount must be a number.") from exc
            schedule.append((tid, op, acc, amount))
        return schedule

    def _run_schedule(self):
        self._cancel_animation()
        try:
            raw = self._parse_editor()
        except ValueError as exc:
            messagebox.showerror("Input Error", str(exc))
            return
        if not raw:
            messagebox.showwarning("Empty", "No schedule to run.")
            return

        self.rollback_mgr.save_checkpoint(self.accounts)
        schedule = build_schedule(raw)
        self.current_schedule = schedule
        self.animation_index = 0
        self.animation_logs = [
            "=" * 44,
            " EXECUTING SCHEDULE",
            "=" * 44,
        ]
        self.conflict_rows = self._conflict_indexes(schedule)
        self._render_transaction_flow(schedule)
        self._write_log(self.exec_log, "\n".join(self.animation_logs))
        self._refresh_live_graph([])
        self.status_banner.config(text="Running animation...", fg=ACCENT, bg=PANEL)
        self.run_button.config(state="disabled")
        self._animate_schedule_step()

    def _cancel_animation(self):
        if self.animation_job is not None:
            self.after_cancel(self.animation_job)
            self.animation_job = None
        if hasattr(self, "run_button"):
            self.run_button.config(state="normal")

    def _animate_schedule_step(self):
        if self.animation_index >= len(self.current_schedule):
            self._finish_schedule_animation()
            return

        index = self.animation_index
        self._set_transaction_state(index, "active")
        self._refresh_live_graph(self.current_schedule[:index + 1])
        self.status_banner.config(
            text=f"Executing step {index + 1} of {len(self.current_schedule)}",
            fg=ACCENT,
            bg=PANEL,
        )
        self.animation_job = self.after(650, lambda: self._commit_animated_step(index))

    def _commit_animated_step(self, index):
        step = self.current_schedule[index]
        self.animation_logs.append(self._apply_schedule_step(step))
        self._write_log(self.exec_log, "\n".join(self.animation_logs))
        self._update_account_labels()
        state = "conflict" if index in self.conflict_rows else "done"
        self._set_transaction_state(index, state)
        self.animation_index += 1
        self.animation_job = self.after(350, self._animate_schedule_step)

    def _finish_schedule_animation(self):
        self.animation_job = None
        self.run_button.config(state="normal")

        conflicts = detect_conflicts(self.current_schedule)
        G = build_precedence_graph(conflicts)
        cycle = has_cycle(G)
        path = find_cycle_path(G)

        self.animation_logs.append("")
        self.animation_logs.append("-" * 44)
        self.animation_logs.append(f" CONFLICTS DETECTED: {len(conflicts)}")
        for c in conflicts:
            self.animation_logs.append(f"  {c[0]} <-> {c[1]} on {c[2]}  [{c[3]}]")

        self.animation_logs.append("")
        self.animation_logs.append("-" * 44)
        if cycle:
            self.animation_logs.append(f" CYCLE DETECTED: {' -> '.join(path)}")
            self.animation_logs.append(" SCHEDULE IS UNSAFE")
            self.status_banner.config(text="UNSAFE SCHEDULE", fg=RED, bg=PANEL)
        else:
            self.animation_logs.append(" NO CYCLE FOUND")
            self.animation_logs.append(" SCHEDULE IS SAFE")
            self.status_banner.config(text="SAFE SCHEDULE", fg=GREEN, bg=PANEL)
        self.animation_logs.append("=" * 44)

        self._write_log(self.exec_log, "\n".join(self.animation_logs))
        self._refresh_live_graph(self.current_schedule)
        self._draw_main_graph(G, not cycle)

        if conflicts:
            summary = f"{len(conflicts)} conflict(s): " + ", ".join(
                f"{a}->{b} on {acc}" for a, b, acc, _reason in conflicts)
            self.conflict_summary.config(text=summary, fg=RED if cycle else ACCENT2)
        else:
            self.conflict_summary.config(text="No conflicts: graph stays empty and safe.",
                                         fg=GREEN)

    def _apply_schedule_step(self, step):
        tid = step["tid"]
        op = step["op"]
        acc_id = step["account"]
        amount = step.get("amount", 0)

        if acc_id not in self.accounts:
            return f"[ERROR] {tid}: Account '{acc_id}' not found."

        acc = self.accounts[acc_id]
        if op == Operation.READ:
            return f"[{tid}] READ  {acc_id} ({acc.name}): Rs.{acc.balance}"

        if op == Operation.WRITE:
            try:
                if amount > 0:
                    acc.deposit(amount)
                    return f"[{tid}] WRITE {acc_id} ({acc.name}): +Rs.{amount} -> Rs.{acc.balance}"
                if amount < 0:
                    acc.withdraw(abs(amount))
                    return f"[{tid}] WRITE {acc_id} ({acc.name}): -Rs.{abs(amount)} -> Rs.{acc.balance}"
                return f"[{tid}] WRITE {acc_id} ({acc.name}): amount=0, no change"
            except ValueError as exc:
                return f"[{tid}] ERROR {acc_id}: {exc}"

        return f"[{tid}] UNKNOWN op '{op}' on {acc_id}"

    def _render_transaction_flow(self, schedule):
        for child in self.txn_rows_frame.winfo_children():
            child.destroy()
        self.txn_rows = []

        if not schedule:
            tk.Label(self.txn_rows_frame, text="No transactions yet.",
                     bg=PANEL, fg=SUBTEXT, font=FONT_B, padx=12,
                     pady=12).pack(fill="x")
            return

        for idx, step in enumerate(schedule):
            row = tk.Frame(self.txn_rows_frame, bg=PANEL, padx=8, pady=8,
                           highlightthickness=1, highlightbackground=BORDER)
            row.pack(fill="x", padx=8, pady=(8, 0))

            status = tk.Label(row, text="WAIT", bg=PANEL, fg=SUBTEXT,
                              font=FONT_S, width=7, anchor="w")
            status.grid(row=0, column=0, sticky="w")
            main = tk.Label(row,
                            text=f"{idx + 1:02d}  {step['tid']}  {step['op'].upper()}",
                            bg=PANEL, fg=TEXT, font=FONT_B, anchor="w")
            main.grid(row=0, column=1, sticky="ew", padx=6)
            meta = tk.Label(row,
                            text=f"{step['account']}  {step.get('amount', 0):g}",
                            bg=PANEL, fg=SUBTEXT, font=FONT_S, anchor="e")
            meta.grid(row=0, column=2, sticky="e")
            row.columnconfigure(1, weight=1)
            self.txn_rows.append((row, status, main, meta))

    def _set_transaction_state(self, index, state):
        if index >= len(self.txn_rows):
            return

        colors = {
            "idle": (PANEL, SUBTEXT, "WAIT"),
            "active": ("#243b53", ACCENT, "RUN"),
            "done": ("#16382f", GREEN, "DONE"),
            "conflict": ("#412534", ACCENT2, "EDGE"),
        }
        bg, fg, label = colors[state]
        row, status, main, meta = self.txn_rows[index]
        row.config(bg=bg, highlightbackground=fg)
        for widget in (status, main, meta):
            widget.config(bg=bg)
        status.config(text=label, fg=fg)
        main.config(fg=TEXT)
        meta.config(fg=fg if state != "idle" else SUBTEXT)
        self.txn_canvas.yview_moveto(max(0, index / max(1, len(self.txn_rows))))

    def _refresh_live_graph(self, schedule):
        conflicts = detect_conflicts(schedule) if schedule else []
        G = build_precedence_graph(conflicts)
        is_safe = not has_cycle(G)
        draw_graph(G, is_safe, ax=self.live_ax, title="Live Precedence Graph")
        self.live_canvas.draw()

    def _conflict_indexes(self, schedule):
        indexes = set()
        for i, s1 in enumerate(schedule):
            for j in range(i + 1, len(schedule)):
                s2 = schedule[j]
                if s1["tid"] == s2["tid"]:
                    continue
                if s1["account"] != s2["account"]:
                    continue
                if s1["op"] == Operation.WRITE or s2["op"] == Operation.WRITE:
                    indexes.update({i, j})
        return indexes

    def _do_rollback(self):
        self._cancel_animation()
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
