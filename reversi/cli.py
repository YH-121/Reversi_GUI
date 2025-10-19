"""
テキストベースのCLI UI。

役割
- 盤面の描画
- 入力受付（モード選択/色選択/座標入力）
- ターン進行と勝敗表示

設計のポイント
- ルール判定は `logic`、CPU手は `ai` に委譲してUIに専念
- 例外 `KeyboardInterrupt` で中断（Ctrl+C や `q` 入力を同扱い）
"""

from __future__ import annotations

from typing import Optional

from . import logic
from .ai import best_move


def _render_cell(v: int) -> str:
    """セルの内部値を表示用文字に変換。"""
    if v == logic.BLACK:
        return "●"
    if v == logic.WHITE:
        return "○"
    return "."


def print_board(board) -> None:
    """盤面を座標ラベル付きで描画。"""
    n = len(board)
    header = "   " + " ".join(chr(ord("A") + i) for i in range(n))
    print(header)
    for r in range(n):
        row = " ".join(_render_cell(board[r][c]) for c in range(n))
        print(f"{r+1:>2} {row}")


def choose_mode() -> str:
    """対戦モードを選択（1=人間同士, 2=人間vsCPU）。"""
    print("モードを選択してください:")
    print("  1) 人間 vs 人間")
    print("  2) 人間 vs CPU")
    while True:
        s = input("> ").strip()
        if s in {"1", "2"}:
            return s
        print("'1' または '2' を入力してください。")


def choose_color() -> int:
    """人間の手番色を選択（黒=先手, 白=後手）。"""
    print("先手(黒=●)か後手(白=○)か選択してください [b/w]:")
    while True:
        s = input("> ").strip().lower()
        if s in {"b", "black", "先手", "黒"}:
            return logic.BLACK
        if s in {"w", "white", "後手", "白"}:
            return logic.WHITE
        print("b(黒) または w(白) を入力してください。")


def prompt_move(player: int) -> Optional[logic.Coord]:
    """座標入力を受け付ける（`pass` は手が無い時のみ許可）。"""
    side = "黒(●)" if player == logic.BLACK else "白(○)"
    s = input(f"{side} の手番です。座標を入力 (例: d3) / pass / q: ").strip()
    if s.lower() in {"q", "quit", "exit"}:
        raise KeyboardInterrupt
    if s.lower() in {"pass", "p"}:
        return None
    coord = logic.parse_coord(s)
    if coord is None:
        print("座標の形式が正しくありません。例: d3 または 3d")
    return coord


def game_loop(vs_cpu: bool, human_color: Optional[int] = None, size: int = 8) -> None:
    """ゲームのメインループ。

    - `vs_cpu` が True の場合は人間 vs CPU、False の場合は人間同士
    - `human_color` で人間の色を指定（vs_cpu=True のときのみ有効）
    """
    board = logic.create_board(size)
    player = logic.BLACK  # Black starts
    passed_last = False

    while True:
        print_board(board)
        b, w = logic.score(board)
        print(f"スコア: 黒={b} 白={w}")

        if logic.game_over(board):
            print("ゲーム終了！")
            if b > w:
                print("黒(●) の勝ち！")
            elif w > b:
                print("白(○) の勝ち！")
            else:
                print("引き分け！")
            return

        moves = logic.valid_moves(board, player)
        if not moves:
            side = "黒(●)" if player == logic.BLACK else "白(○)"
            print(f"{side} は打てる手がありません。パスします。")
            if passed_last:
                # Both players passed
                continue
            passed_last = True
            player = logic.opponent(player)
            continue
        else:
            passed_last = False

        is_human_turn = True
        if vs_cpu and human_color is not None:
            is_human_turn = (player == human_color)

        if is_human_turn:
            print("合法手:", ", ".join(sorted(logic.coord_to_str(m) for m in moves)))
            while True:
                coord = prompt_move(player)
                if coord is None:
                    # pass requested, only allow if no legal moves
                    if moves:
                        print("合法手があります。パスはできません。")
                        continue
                else:
                    if coord in moves:
                        board = logic.apply_move(board, player, coord)
                        break
                    else:
                        print("その手は打てません。")
                        continue
                break  # explicit pass when no moves
        else:
            mv = best_move(board, player)
            if mv is None:
                print("CPU はパスします。")
            else:
                print(f"CPU の手: {logic.coord_to_str(mv)}")
                board = logic.apply_move(board, player, mv)

        player = logic.opponent(player)


def main() -> None:
    """エントリーポイント：モード選択→ゲーム開始。"""
    print("==== リバーシ (オセロ) ====")
    mode = choose_mode()
    if mode == "1":
        game_loop(vs_cpu=False)
        return
    human = choose_color()
    game_loop(vs_cpu=True, human_color=human)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n中断しました。")
