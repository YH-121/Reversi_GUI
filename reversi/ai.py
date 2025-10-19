"""
簡易CPUの評価関数と指し手選択。

方針
- 先読みはせず、1手先の静的評価で貪欲に選ぶ
- 評価は盤面の位置に対する重み（角>辺>その他）を用いる
- 盤サイズ 8 以外（12/16）にも対応するため、動的な位置重みを用意

注意
- 強さは控えめです。強化するにはミニマックス + αβ枝刈り等を追加してください。
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .logic import BLACK, WHITE, Player, Coord, apply_move, valid_moves


def _pos_weight(n: int, r: int, c: int) -> int:
    """盤サイズ `n` に応じた位置重みを返す（角>辺>その他）。

    - 角: +100
    - 角の直隣（上下左右）: -50（いわゆるCマス）
    - 角の斜め隣: -20（いわゆるXマス）
    - 辺: +10
    - それ以外: -1（やや控えめに減点）
    """
    last = n - 1
    # 角
    if (r in (0, last)) and (c in (0, last)):
        return 100
    # 角の直隣（上下左右）
    if (r in (0, last) and c in (1, last - 1)) or (c in (0, last) and r in (1, last - 1)):
        return -50
    # 角の斜め隣
    if (r, c) in {(1, 1), (1, last - 1), (last - 1, 1), (last - 1, last - 1)}:
        return -20
    # 辺
    if r in (0, last) or c in (0, last):
        return 10
    # その他
    return -1


def evaluate(board: Sequence[Sequence[int]], player: Player) -> int:
    """静的評価値を返す。大きいほど `player` に有利。

    盤面上の各セルについて、
    - `player` の石なら +重み
    - 相手の石なら -重み
    を合計する。重みは盤サイズに応じて動的に決定する。
    """
    score = 0
    n = len(board)
    for r, row in enumerate(board):
        for c, cell in enumerate(row):
            if cell == 0:
                continue
            w = _pos_weight(n, r, c)
            score += w if cell == player else -w
    return score


def best_move(board: Sequence[Sequence[int]], player: Player) -> Optional[Coord]:
    """合法手の中から、適用後の静的評価が最大となる着手を返す。"""
    moves = valid_moves(board, player)
    if not moves:
        return None
    best = None
    best_score = -10**9
    for m in moves:
        next_board = apply_move(board, player, m)
        sc = evaluate(next_board, player)
        if sc > best_score:
            best_score = sc
            best = m
    return best
