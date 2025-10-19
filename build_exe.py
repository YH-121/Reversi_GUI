"""
PyInstaller で Tkinter を含めて .exe を作るためのビルドスクリプト。

ポイント
- _tkinter の DLL エラー回避のため、Tcl/Tk データを自動同梱
- `--onefile` を付けたい場合は引数に指定
- `icon.ico` が def/ にあれば自動でアイコン適用

使い方（PowerShell）
- `cd def`
- 標準: `uv run python build_exe.py`
- 1ファイル: `uv run python build_exe.py --onefile`

出力
- フォルダ版: `def/dist/Reversi/Reversi.exe`
- 1ファイル版: `def/dist/Reversi.exe`
"""

from __future__ import annotations

import glob
import os
import sys

import PyInstaller.__main__


def collect_tcl_tk_add_data() -> list[str]:
    """Tcl/Tk のディレクトリを探索して --add-data を返す。

    Windows/conda 環境も考慮し、以下の候補を順に探索:
      - <base>/tcl/
      - <base>/Library/tcl/
    """
    add_data: list[str] = []
    base = sys.base_prefix
    candidates = [
        os.path.join(base, "tcl"),
        os.path.join(base, "Library", "tcl"),
    ]
    for tcl_root in candidates:
        if not os.path.isdir(tcl_root):
            continue
        for name in os.listdir(tcl_root):
            if not (name.startswith("tcl") or name.startswith("tk")):
                continue
            src = os.path.join(tcl_root, name)
            if os.path.isdir(src):
                dst = os.path.join("tcl", name)
                add_data.extend([f"{src}{os.pathsep}{dst}"])
    return add_data


def collect_tk_binaries() -> list[str]:
    """_tkinter が依存する DLL を探索して --add-binary で同梱する指定を返す。

    探索対象:
      - <base>/DLLs/_tkinter.pyd（CPython 標準）
      - <base>/DLLs/tk*.dll, tcl*.dll
      - <base>/Library/bin/tk*.dll, tcl*.dll（conda 系）
    """
    base = sys.base_prefix
    bins: list[str] = []

    def add_if_exists(path: str, dst: str = ".") -> None:
        if os.path.isfile(path):
            bins.extend([f"{path}{os.pathsep}{dst}"])

    # _tkinter.pyd（念のため明示同梱）
    add_if_exists(os.path.join(base, "DLLs", "_tkinter.pyd"))

    # tcl/tk DLL（CPython 配置）
    dlls_dir = os.path.join(base, "DLLs")
    if os.path.isdir(dlls_dir):
        for name in os.listdir(dlls_dir):
            lower = name.lower()
            if lower.startswith("tcl") and lower.endswith(".dll"):
                add_if_exists(os.path.join(dlls_dir, name))
            if lower.startswith("tk") and lower.endswith(".dll"):
                add_if_exists(os.path.join(dlls_dir, name))

    # conda 系: Library/bin 下の DLL
    lib_bin = os.path.join(base, "Library", "bin")
    if os.path.isdir(lib_bin):
        for name in os.listdir(lib_bin):
            lower = name.lower()
            if lower.startswith("tcl") and lower.endswith(".dll"):
                add_if_exists(os.path.join(lib_bin, name))
            if lower.startswith("tk") and lower.endswith(".dll"):
                add_if_exists(os.path.join(lib_bin, name))

    return bins


def main() -> None:
    opts: list[str] = [
        "--noconsole",
        "--name",
        "Reversi",
        # 隠しインポート（保険）
        "--hidden-import",
        "tkinter",
        "--hidden-import",
        "tkinter.ttk",
        # tkinter のデータ/バイナリを収集（PyInstaller 6+）
        "--collect-all",
        "tkinter",
        # 念のため _tkinter を明示
        "--hidden-import",
        "_tkinter",
    ]

    if "--onefile" in sys.argv:
        opts.append("--onefile")

    # アイコンがあれば付与
    icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    if os.path.exists(icon_path):
        opts += ["--icon", icon_path]

    # Tcl/Tk のデータを同梱
    for spec in collect_tcl_tk_add_data():
        opts += ["--add-data", spec]

    # _tkinter.pyd と tcl/tk の DLL を同梱
    for spec in collect_tk_binaries():
        opts += ["--add-binary", spec]

    # ランタイムフックで実行時に tcl/tk の場所を解決
    rt_hook = os.path.join(os.path.dirname(__file__), "rt_tk_path.py")
    if os.path.exists(rt_hook):
        opts += ["--runtime-hook", rt_hook]

    # エントリ（パッケージ側の main から起動 → GUI）
    opts.append(os.path.join("reversi", "main.py"))

    print("PyInstaller options:")
    for o in opts:
        print(" ", o)

    PyInstaller.__main__.run(opts)


if __name__ == "__main__":
    main()
