"""
PyInstaller 実行時に Tcl/Tk の参照先をアプリ内に向けるランタイムフック。

exe 内の `tcl/` 以下に格納された `tcl8.x` / `tk8.x` を `TCL_LIBRARY`/`TK_LIBRARY` に設定。
環境変数はプロセス内でのみ設定されるため、システム環境は変更しません。
"""

from __future__ import annotations

import glob
import os
import sys


def _candidate_base() -> str:
    # onefile 時は展開先、onedir 時は実行ファイルのディレクトリ
    return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))


def _first(pattern: str) -> str | None:
    paths = glob.glob(pattern)
    return paths[0] if paths else None


def setup_tcl_tk_env() -> None:
    base = _candidate_base()
    tcl_dir = _first(os.path.join(base, "tcl", "tcl*"))
    tk_dir = _first(os.path.join(base, "tcl", "tk*"))
    if tcl_dir and not os.environ.get("TCL_LIBRARY"):
        os.environ["TCL_LIBRARY"] = tcl_dir
    if tk_dir and not os.environ.get("TK_LIBRARY"):
        os.environ["TK_LIBRARY"] = tk_dir


setup_tcl_tk_env()

