"""
リバーシ（オセロ）のコアロジック。

役割
- 盤面表現・初期配置の生成
- 合法手の判定（挟み込みの検出）
- 着手の適用（石の反転）
- 終局判定とスコア計算

設計のポイント
- 盤面は `List[List[int]]`（0=空, 1=黒, -1=白）で表現
- プレイヤーは `BLACK=1`, `WHITE=-1` の整数で持つ（反転に便利）
- 8方向レイを伸ばして「相手石の連続の先に自分石がある」ラインを反転対象とする
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple


# セル状態の定数
EMPTY = 0   # 空きマス
BLACK = 1   # 黒石
WHITE = -1  # 白石（反転は掛け算で扱いやすいように -1）

Player = int  # BLACK or WHITE
Coord = Tuple[int, int]


DIRECTIONS: Tuple[Coord, ...] = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),          (0, 1),
    (1, -1),  (1, 0), (1, 1),
)


def opponent(player: Player) -> Player:
    """与えられたプレイヤーの相手側を返す。"""
    return BLACK if player == WHITE else WHITE


def create_board(size: int = 8) -> List[List[int]]:
    """`size x size` の盤面を作成し、中央4マスに初期配置を置く。

    size は偶数かつ 4 以上を想定（通常は 8）。
    """
    if size % 2 != 0 or size < 4:
        raise ValueError("Board size must be an even number >= 4")
    board = [[EMPTY for _ in range(size)] for _ in range(size)]
    mid = size // 2
    # Standard starting position
    board[mid - 1][mid - 1] = WHITE
    board[mid][mid] = WHITE
    board[mid - 1][mid] = BLACK
    board[mid][mid - 1] = BLACK
    return board


def in_bounds(board: Sequence[Sequence[int]], r: int, c: int) -> bool:
    """(r, c) が盤面内かどうか。"""
    n = len(board)
    return 0 <= r < n and 0 <= c < n


def _ray_flips(board: Sequence[Sequence[int]], player: Player, r: int, c: int, dr: int, dc: int) -> List[Coord]:
    """方向 (dr, dc) にレイを伸ばし、反転対象の座標一覧を返す。

    条件: 空マス (r,c) から見て、相手石が1つ以上連続し、その直後に自分石がある。
    その相手石の連続区間が反転対象となる。
    条件を満たさない場合は空リスト。
    """
    flips: List[Coord] = []
    rr, cc = r + dr, c + dc
    while in_bounds(board, rr, cc) and board[rr][cc] == opponent(player):
        flips.append((rr, cc))
        rr += dr
        cc += dc
    if not flips:
        return []
    if in_bounds(board, rr, cc) and board[rr][cc] == player:
        return flips
    return []


def find_flips(board: Sequence[Sequence[int]], player: Player, r: int, c: int) -> List[Coord]:
    """着手 (r, c) で裏返る座標一覧を 8 方向探索して収集する。"""
    if not in_bounds(board, r, c) or board[r][c] != EMPTY:
        return []
    flips: List[Coord] = []
    for dr, dc in DIRECTIONS:
        flips.extend(_ray_flips(board, player, r, c, dr, dc))
    return flips


def valid_moves(board: Sequence[Sequence[int]], player: Player) -> List[Coord]:
    """指定プレイヤーにとっての合法手一覧を返す。"""
    moves: List[Coord] = []
    n = len(board)
    for r in range(n):
        for c in range(n):
            if board[r][c] == EMPTY and find_flips(board, player, r, c):
                moves.append((r, c))
    return moves


def apply_move(board: Sequence[Sequence[int]], player: Player, move: Coord) -> List[List[int]]:
    """着手を適用して新しい盤面を返す（元の盤面は変更しない）。

    反転対象が無い手は `ValueError`。
    """
    r, c = move
    flips = find_flips(board, player, r, c)
    if not flips:
        raise ValueError("Invalid move: no discs flipped")
    new_board = [row[:] for row in board]
    new_board[r][c] = player
    for rr, cc in flips:
        new_board[rr][cc] = player
    return new_board


def has_valid_move(board: Sequence[Sequence[int]], player: Player) -> bool:
    """プレイヤーに合法手が1つでもあるか。"""
    return any(find_flips(board, player, r, c) for r in range(len(board)) for c in range(len(board)))


def game_over(board: Sequence[Sequence[int]]) -> bool:
    """両者とも合法手が無ければ終局。"""
    return not has_valid_move(board, BLACK) and not has_valid_move(board, WHITE)


def score(board: Sequence[Sequence[int]]) -> Tuple[int, int]:
    """(黒数, 白数) を返す。"""
    black = sum(cell == BLACK for row in board for cell in row)
    white = sum(cell == WHITE for row in board for cell in row)
    return black, white


def parse_coord(text: str) -> Optional[Coord]:
    """ユーザー入力の座標文字列から (row, col) を返す。

    受け付ける例: "d3", "3d"（大文字小文字は不問）。
    返り値は 0 始まりの行・列インデックス。
    不正な入力は None。
    """
    s = text.strip().lower()
    if len(s) < 2:
        return None
    col = s[0]
    row_str = s[1:]
    if not col.isalpha() or not row_str.isdigit():
        # Try reversed like 3d
        if s[-1].isalpha() and s[:-1].isdigit():
            row_str = s[:-1]
            col = s[-1]
        else:
            return None
    c = ord(col) - ord('a')
    try:
        r = int(row_str) - 1
    except ValueError:
        return None
    return (r, c)


def coord_to_str(coord: Coord) -> str:
    """(row, col) を "A1" 形式の座標文字列へ。"""
    r, c = coord
    return f"{chr(ord('A') + c)}{r + 1}"
