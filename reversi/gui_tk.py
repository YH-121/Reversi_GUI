"""
Tkinter を使ったリバーシのGUI実装。

目的と方針
- 既存の `logic`（ルール）と `ai`（CPU）をUIから呼び出す薄い層に徹する
- 盤描画・入力（クリック）・ターン管理・結果表示を担当
- CPU手はUIスレッド内で処理し、`after` で適度に割り込みを挿入して固まりを防ぐ

主なUI要素
- 上部バー: New Game / Quit ボタン と ステータス表示
- キャンバス: 盤面（背景・マス目・石・合法手のハイライト）

操作の流れ
1) 起動時に対戦モード（人間同士 or 人間 vs CPU）と手番色（黒/白）をダイアログで選択
2) キャンバス上のマスをクリックして着手（人間の手番のみ有効）
3) 自動で反転・手番交代・パス処理、CPU手番なら自動で指す
4) 双方が打てなくなると終局、ステータスに結果を表示
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Optional, Tuple, List

try:
    # パッケージとして実行される通常ルート
    from . import logic
    from .ai import best_move
except Exception:
    # 単体スクリプトとして実行された場合のフォールバック（PyInstaller対策）
    import os, sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from reversi import logic
    from reversi.ai import best_move


Cell = Tuple[int, int]


class ReversiApp:
    """アプリケーションクラス（盤面状態とUIの橋渡し）。"""

    def __init__(self, root: tk.Tk, size: int = 8):
        """ウィンドウや盤状態、イベントの初期化を行う。

        引数
        - root: Tk のルートウィンドウ
        - size: 盤のサイズ（通常 8）
        """
        self.root = root
        self.root.title("Reversi (Tkinter)")

        self.size = size
        # 初期ボードは後でサイズ選択後に再生成する
        self.board = logic.create_board(self.size)
        self.player = logic.BLACK

        # Game mode
        self.vs_cpu = True
        self.human_color: Optional[int] = logic.BLACK

        # UI layout
        self.status = tk.StringVar(value="Ready")
        # 上部の操作バー（新規開始・終了・状態テキスト）
        self.top = tk.Frame(root)
        self.top.pack(side=tk.TOP, fill=tk.X)
        tk.Button(self.top, text="New Game", command=self.new_game).pack(side=tk.LEFT)
        tk.Button(self.top, text="Quit", command=root.destroy).pack(side=tk.LEFT)
        tk.Label(self.top, textvariable=self.status, anchor="w").pack(side=tk.LEFT, padx=10)

        # 盤面キャンバス（正方形）。初期サイズは560px四方。
        self.canvas_size = 560
        self.canvas = tk.Canvas(root, width=self.canvas_size, height=self.canvas_size, bg="#1a7f2e")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # 左クリックで着手
        self.canvas.bind("<Button-1>", self.on_click)

        # 起動直後に画面中央へ配置（ダイアログ表示より前）
        self.center_on_screen()
        # サイズ/対戦形式/手番色をまとめて選択
        self.open_setup_dialog()
        # 選択サイズで盤面を再生成
        self.board = logic.create_board(self.size)
        self.redraw()

    # ----- Game control -----
    def ask_mode_and_color(self) -> None:
        """対戦モード（CPU対戦か否か）と、対CPU時の手番色をダイアログで選ぶ。"""
        mode = messagebox.askquestion("Mode", "CPU対戦 or 2p対戦\n(はい = CPU対戦, いいえ = 2p対戦)")
        self.vs_cpu = (mode == "yes")
        if self.vs_cpu:
            # Choose color: True -> Black, False -> White
            pick_black = messagebox.askyesno("Color", "黒側でプレイしますか?\n(はい = 黒, いいえ = 白)")
            self.human_color = logic.BLACK if pick_black else logic.WHITE
        else:
            self.human_color = None

    def new_game(self) -> None:
        """設定ダイアログ（サイズ/対戦形式/手番色）→盤を初期化して開始する。"""
        self.open_setup_dialog()
        self.board = logic.create_board(self.size)
        self.player = logic.BLACK
        self.redraw()

    # ----- Rendering -----
    def redraw(self) -> None:
        """画面全体を描き直し、必要ならCPU手番処理もスケジュールする。"""
        self.canvas.delete("all")
        self.draw_grid()
        self.draw_discs()
        self.draw_valid_hints()
        self.update_status()
        # If it's CPU's turn, let it move automatically
        self.root.after(100, self.maybe_cpu_turn)

    def cell_size(self) -> int:
        """現在のキャンバスサイズから1マスのピクセル数を算出。"""
        return min(int(self.canvas.winfo_width() / self.size), int(self.canvas.winfo_height() / self.size)) or int(self.canvas_size / self.size)

    def draw_grid(self) -> None:
        """背景とマス目、座標ラベル（A.. / 1..）を描画。"""
        n = self.size
        cs = self.cell_size()
        for r in range(n):
            for c in range(n):
                x0, y0 = c * cs, r * cs
                x1, y1 = x0 + cs, y0 + cs
                self.canvas.create_rectangle(x0, y0, x1, y1, outline="#0f4f20", fill="#1a7f2e")
        # Labels
        for i in range(n):
            self.canvas.create_text((i + 0.5) * cs, 10, text=chr(ord('A') + i), fill="white")
            self.canvas.create_text(10, (i + 0.5) * cs, text=str(i + 1), fill="white")

    def draw_discs(self) -> None:
        """石（黒/白）を描画。余白を入れて円で表現。"""
        cs = self.cell_size()
        pad = max(4, cs // 12)
        for r, row in enumerate(self.board):
            for c, v in enumerate(row):
                if v == logic.EMPTY:
                    continue
                x0, y0 = c * cs + pad, r * cs + pad
                x1, y1 = (c + 1) * cs - pad, (r + 1) * cs - pad
                color = "black" if v == logic.BLACK else "white"
                outline = "#000000" if v == logic.BLACK else "#f0f0f0"
                self.canvas.create_oval(x0, y0, x1, y1, fill=color, outline=outline, width=2)

    def draw_valid_hints(self) -> None:
        """合法手のハイライト（小さな円の枠）を描画。"""
        moves = logic.valid_moves(self.board, self.player)
        cs = self.cell_size()
        for (r, c) in moves:
            x, y = c * cs + cs // 2, r * cs + cs // 2
            self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6, outline="#ffe08a", width=2)

    def update_status(self) -> None:
        """スコアやターン、終局時の結果をステータスバーに表示。"""
        b, w = logic.score(self.board)
        if logic.game_over(self.board):
            result = "Draw"
            if b > w:
                result = "Black wins"
            elif w > b:
                result = "White wins"
            self.status.set(f"Game Over | Black={b} White={w} | {result}")
        else:
            turn = "Black" if self.player == logic.BLACK else "White"
            self.status.set(f"Turn: {turn} | Black={b} White={w}")

    # ----- Interaction -----
    def center_on_screen(self) -> None:
        """ウィンドウ全体を画面中央に移動する。

        ウィジェットのレイアウト確定後に呼ぶことで、想定サイズで中央寄せする。
        初期段階で幅/高さが未確定の場合は、キャンバスサイズと上部バーの
        要求サイズから概算する。
        """
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        if w <= 1 or h <= 1:
            # レイアウトがまだ確定していない場合のフォールバック
            self.top.update_idletasks()
            w = max(self.canvas_size, self.top.winfo_reqwidth())
            h = self.canvas_size + self.top.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, int((sw - w) / 2))
        y = max(0, int((sh - h) / 2))
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def open_setup_dialog(self) -> None:
        """起動/新規開始時の一括設定ダイアログ（ラジオボタン）を表示する。

        同一ウィンドウ上で以下を選択:
        - 盤面サイズ（8/12/16）
        - 対戦形式（人間 vs 人間 / 人間 vs CPU）
        - 手番色（黒/白、対CPU時のみ有効）
        """
        dlg = tk.Toplevel(self.root)
        dlg.title("新規対局の設定")
        dlg.transient(self.root)
        dlg.grab_set()

        # ダイアログを中央に配置
        self.root.update_idletasks()
        w, h = 380, 260
        rw = self.root.winfo_width() or 600
        rh = self.root.winfo_height() or 600
        rx = self.root.winfo_rootx()
        ry = self.root.winfo_rooty()
        x = rx + (rw - w) // 2
        y = ry + (rh - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        # 状態変数
        size_var = tk.IntVar(value=self.size if self.size in (8, 12, 16) else 8)
        mode_var = tk.StringVar(value="cpu" if self.vs_cpu else "hvh")
        color_var = tk.IntVar(value=self.human_color if self.human_color in (logic.BLACK, logic.WHITE) else logic.BLACK)

        # レイアウト
        frm = tk.Frame(dlg, padx=14, pady=12)
        frm.pack(fill=tk.BOTH, expand=True)

        # 盤面サイズ
        tk.Label(frm, text="盤面サイズ").grid(row=0, column=0, sticky="w")
        size_frame = tk.Frame(frm)
        size_frame.grid(row=1, column=0, sticky="w")
        for col, val in enumerate((8, 12, 16)):
            tk.Radiobutton(size_frame, text=f"{val} x {val}", value=val, variable=size_var).grid(row=0, column=col, padx=6)

        # 対戦形式
        tk.Label(frm, text="対戦形式").grid(row=2, column=0, sticky="w", pady=(10, 0))
        mode_frame = tk.Frame(frm)
        mode_frame.grid(row=3, column=0, sticky="w")
        tk.Radiobutton(mode_frame, text="人間 vs 人間", value="hvh", variable=mode_var).grid(row=0, column=0, padx=6)
        tk.Radiobutton(mode_frame, text="人間 vs CPU", value="cpu", variable=mode_var).grid(row=0, column=1, padx=6)

        # 手番色（対CPU時のみ有効）
        tk.Label(frm, text="手番色（対CPU時）").grid(row=4, column=0, sticky="w", pady=(10, 0))
        color_frame = tk.Frame(frm)
        color_frame.grid(row=5, column=0, sticky="w")
        rb_black = tk.Radiobutton(color_frame, text="黒（先手）", value=logic.BLACK, variable=color_var)
        rb_white = tk.Radiobutton(color_frame, text="白（後手）", value=logic.WHITE, variable=color_var)
        rb_black.grid(row=0, column=0, padx=6)
        rb_white.grid(row=0, column=1, padx=6)

        def _toggle_color_state(*_args):
            state = tk.NORMAL if mode_var.get() == "cpu" else tk.DISABLED
            rb_black.configure(state=state)
            rb_white.configure(state=state)

        mode_var.trace_add("write", _toggle_color_state)
        _toggle_color_state()

        # ボタン行
        btns = tk.Frame(frm)
        btns.grid(row=6, column=0, sticky="e", pady=(14, 0))

        def on_ok():
            self.size = size_var.get()
            self.vs_cpu = (mode_var.get() == "cpu")
            self.human_color = color_var.get() if self.vs_cpu else None
            dlg.destroy()

        def on_cancel():
            dlg.destroy()

        tk.Button(btns, text="キャンセル", command=on_cancel).pack(side=tk.RIGHT, padx=6)
        tk.Button(btns, text="はい", command=on_ok).pack(side=tk.RIGHT)

        dlg.wait_window()

    def ask_board_size(self) -> None:
        """盤面サイズを 8/12/16 の中から選択させる。

        キャンセルされた場合や不正入力の場合は 8 にフォールバックする。
        """
        while True:
            ans = simpledialog.askstring(
                "Board Size",
                "盤面サイズを選んでください (8 / 12 / 16):",
                parent=self.root,
            )
            if ans is None:
                # キャンセル時はデフォルト 8
                self.size = 8
                return
            ans = ans.strip()
            if ans in {"8", "12", "16"}:
                self.size = int(ans)
                return
            messagebox.showwarning("入力エラー", "8, 12, 16 のいずれかを入力してください。")

    def canvas_to_cell(self, x: int, y: int) -> Optional[Cell]:
        """キャンバス座標から盤座標 (row, col) を求める。範囲外は None。"""
        cs = self.cell_size()
        c, r = x // cs, y // cs
        if 0 <= r < self.size and 0 <= c < self.size:
            return (r, c)
        return None

    def on_click(self, event) -> None:
        """クリック処理。人間の手番のみ受け付け、合法手であれば着手する。"""
        if logic.game_over(self.board):
            return
        # If vs CPU and it's not human's turn, ignore clicks
        if self.vs_cpu and self.human_color is not None and self.player != self.human_color:
            return

        cell = self.canvas_to_cell(event.x, event.y)
        if cell is None:
            return
        r, c = cell
        moves = logic.valid_moves(self.board, self.player)
        if (r, c) not in moves:
            self.flash_cell(r, c)
            return

        # 反転を含む着手を適用
        self.board = logic.apply_move(self.board, self.player, (r, c))
        self.player = logic.opponent(self.player)
        self.after_move()

    def after_move(self) -> None:
        """着手後の共通処理。パスや終局の判定を行い、再描画する。"""
        # Handle passes automatically
        if not logic.valid_moves(self.board, self.player):
            # If both players cannot move -> game over
            if not logic.valid_moves(self.board, logic.opponent(self.player)):
                self.redraw()
                return
            # Otherwise, pass
            self.player = logic.opponent(self.player)
        self.redraw()

    def maybe_cpu_turn(self) -> None:
        """CPU手番なら最善手（貪欲）を指してから共通処理へ。"""
        if logic.game_over(self.board):
            return
        if not self.vs_cpu or self.human_color is None:
            return
        if self.player != self.human_color:
            mv = best_move(self.board, self.player)
            if mv is None:
                # pass
                self.player = logic.opponent(self.player)
            else:
                self.board = logic.apply_move(self.board, self.player, mv)
                self.player = logic.opponent(self.player)
            self.after_move()

    def flash_cell(self, r: int, c: int) -> None:
        """不正なクリック時に該当マスを一瞬赤枠でハイライト。"""
        cs = self.cell_size()
        x0, y0 = c * cs, r * cs
        x1, y1 = x0 + cs, y0 + cs
        rect = self.canvas.create_rectangle(x0, y0, x1, y1, outline="#ff6666", width=3)
        self.root.after(150, lambda: self.canvas.delete(rect))


def main() -> None:
    """GUIエントリーポイント。ウィンドウ生成とリサイズ対応を設定。"""
    root = tk.Tk()
    app = ReversiApp(root, size=8)
    # Adjust redraw when canvas resizes
    def _on_resize(_evt):
        app.redraw()
    app.canvas.bind("<Configure>", _on_resize)
    root.mainloop()


if __name__ == "__main__":
    main()
