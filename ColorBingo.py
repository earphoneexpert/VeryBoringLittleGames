"""
颜色 Bingo（Python 3.10+ / 3.12 + tkinter）
=============================================
终极稳定版：暴力替换 + 高轮数修复 + UI层异常兜底。
"""

import math
import random
import tkinter as tk
import tkinter.font as tkfont

# ================================================================
#  全局配置
# ================================================================

DIFFICULTIES = {
    "尝试": {"grid": 3,  "specs": [3, 3]},
    "简单": {"grid": 6,  "specs": [3, 3, 4, 4, 5, 5]},
    "中等": {"grid": 8,  "specs": [3, 3, 3, 4, 4, 4, 5, 5, 5]},
    "困难": {"grid": 10, "specs": [3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5]},
}

CELL_SIZES = {3: 90, 6: 64, 8: 56, 10: 50}
GAP = 5
MARGIN = 16
MIN_STEP_ABS = 15
MAX_GRADIENT_RETRIES = 600
MAX_PLACEMENT_RETRIES = 2000
MAX_PUZZLE_RETRIES = 300
MAX_FIX_ROUNDS = 200


# ================================================================
#  谜题生成模块
# ================================================================

def compute_step_bounds(c, n, k):
    lo, hi = -255, 255
    for j in range(n):
        t = j - k
        if t > 0:
            lo = max(lo, math.ceil(-c / t))
            hi = min(hi, (255 - c) // t)
        elif t < 0:
            hi = min(hi, c // (-t))
            lo = max(lo, math.ceil((c - 255) / t))
    return lo, hi


def pick_visible_step(lo, hi):
    candidates = [d for d in range(lo, hi + 1) if abs(d) >= MIN_STEP_ABS]
    if candidates:
        return random.choice(candidates)
    if lo <= hi:
        return random.randint(lo, hi)
    return 0


def make_gradient(n, fixed):
    if len(fixed) > 1:
        return None
    for _ in range(MAX_GRADIENT_RETRIES):
        if fixed:
            k, c0 = fixed[0]
            steps = []
            valid = True
            for ch in range(3):
                lo, hi = compute_step_bounds(c0[ch], n, k)
                if lo > hi:
                    valid = False
                    break
                steps.append(pick_visible_step(lo, hi))
            if not valid or sum(abs(s) for s in steps) < 20:
                continue
            result = []
            for i in range(n):
                result.append(tuple(c0[ch] + (i - k) * steps[ch] for ch in range(3)))
            return result
        else:
            steps = [random.randint(-60, 60) for _ in range(3)]
            if sum(abs(s) for s in steps) < 20:
                continue
            starts = []
            valid = True
            for ch in range(3):
                lo_s = max(0, -(n - 1) * steps[ch])
                hi_s = min(255, 255 - (n - 1) * steps[ch])
                if lo_s > hi_s:
                    valid = False
                    break
                starts.append(random.randint(lo_s, hi_s))
            if not valid:
                continue
            result = []
            for i in range(n):
                result.append(tuple(starts[ch] + i * steps[ch] for ch in range(3)))
            return result
    return None


def find_generation_order(lines):
    sets = [set(line) for line in lines]
    remaining = list(range(len(lines)))
    picked = set()
    order = []
    while remaining:
        found = False
        for i in remaining:
            if sum(1 for j in picked if sets[i] & sets[j]) <= 1:
                order.append(i)
                picked.add(i)
                remaining.remove(i)
                found = True
                break
        if not found:
            return None
    return order


def is_arithmetic_progression(colors):
    if len(colors) < 3:
        return False
    for ch in range(3):
        d = colors[1][ch] - colors[0][ch]
        for i in range(2, len(colors)):
            if colors[i][ch] - colors[i - 1][ch] != d:
                return False
    return True


def find_all_accidental_gradients(grid_size, colors, placed_sets):
    accidentals = []
    seen = set()
    for r in range(grid_size):
        for c in range(grid_size):
            for dr, dc in ((0, 1), (1, 0)):
                pr = r - dr
                pc = c - dc
                if 0 <= pr < grid_size and 0 <= pc < grid_size:
                    continue
                run = []
                rr = r
                cc = c
                while 0 <= rr < grid_size and 0 <= cc < grid_size:
                    run.append((rr, cc))
                    rr = rr + dr
                    cc = cc + dc
                for i in range(len(run)):
                    for j in range(i + 3, len(run) + 1):
                        seg = tuple(run[i:j])
                        if seg in seen:
                            continue
                        seen.add(seg)
                        seg_colors = [colors[p] for p in seg]
                        if is_arithmetic_progression(seg_colors):
                            seg_set = set(seg)
                            is_sub = False
                            for ps in placed_sets:
                                if seg_set <= ps:
                                    is_sub = True
                                    break
                            if not is_sub:
                                accidentals.append((seg, seg_set))
    return accidentals


def try_generate_puzzle(grid_size, specs):
    specs_shuffled = list(specs)
    random.shuffle(specs_shuffled)
    lines = []
    for length in specs_shuffled:
        placed = False
        for _ in range(MAX_PLACEMENT_RETRIES):
            if random.random() < 0.5:
                if grid_size < length:
                    continue
                r = random.randrange(grid_size)
                c = random.randrange(grid_size - length + 1)
                cells = [(r, c + i) for i in range(length)]
            else:
                if grid_size < length:
                    continue
                r = random.randrange(grid_size - length + 1)
                c = random.randrange(grid_size)
                cells = [(r + i, c) for i in range(length)]
            overlap_ok = True
            for existing in lines:
                if len(set(cells) & set(existing)) > 1:
                    overlap_ok = False
                    break
            if overlap_ok:
                lines.append(cells)
                placed = True
                break
        if not placed:
            return None

    order = find_generation_order(lines)
    if order is None:
        return None

    colors = {}
    for idx in order:
        line = lines[idx]
        fixed = []
        for i, p in enumerate(line):
            if p in colors:
                fixed.append((i, colors[p]))
        grad = make_gradient(len(line), fixed)
        if grad is None:
            return None
        for pos, col in zip(line, grad):
            colors[pos] = col

    placed_cells = set()
    for line in lines:
        for p in line:
            placed_cells.add(p)
    placed_sets = [set(line) for line in lines]

    for r in range(grid_size):
        for c in range(grid_size):
            pos = (r, c)
            if pos not in colors:
                colors[pos] = tuple(random.randint(0, 255) for _ in range(3))

    for fix_round in range(MAX_FIX_ROUNDS):
        accidentals = find_all_accidental_gradients(grid_size, colors, placed_sets)
        if not accidentals:
            return lines, colors

        cells_to_perturb = set()
        for seg, seg_set in accidentals:
            seg_colors = [colors[p] for p in seg]
            if not is_arithmetic_progression(seg_colors):
                continue
            is_sub = False
            for ps in placed_sets:
                if seg_set <= ps:
                    is_sub = True
                    break
            if is_sub:
                continue
            safe = [p for p in seg if p not in placed_cells]
            if not safe:
                safe = [seg[0]]
            target = random.choice(safe)
            cells_to_perturb.add(target)

        if not cells_to_perturb:
            return None

        for pos in cells_to_perturb:
            colors[pos] = tuple(random.randint(0, 255) for _ in range(3))

    return None


def generate_puzzle(grid_size, specs):
    for _ in range(MAX_PUZZLE_RETRIES):
        result = try_generate_puzzle(grid_size, specs)
        if result is not None:
            return result
    return _fallback_puzzle(grid_size, specs)


def _fallback_puzzle(grid_size, specs):
    global MIN_STEP_ABS
    old_min = MIN_STEP_ABS
    MIN_STEP_ABS = 1
    try:
        for _ in range(500):
            result = try_generate_puzzle(grid_size, specs)
            if result is not None:
                return result
    finally:
        MIN_STEP_ABS = old_min
    colors = {}
    for r in range(grid_size):
        for c in range(grid_size):
            colors[(r, c)] = tuple(random.randint(0, 255) for _ in range(3))
    return [], colors


# ================================================================
#  应用主窗口
# ================================================================

class ColorBingoApp:
    def __init__(self, root):
        self.root = root
        root.title("颜色 Bingo")
        root.resizable(False, False)
        self.container = tk.Frame(root)
        self.container.pack(fill="both", expand=True)
        self.show_intro()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_intro(self):
        self.clear_container()
        frame = tk.Frame(self.container, padx=40, pady=28)
        frame.pack(expand=True)

        title_label = tk.Label(frame, text="\U0001f3a8 颜色 Bingo \U0001f3a8",
                               font=("Microsoft YaHei", 26, "bold"), fg="#2c3e50")
        title_label.pack(pady=(0, 20))

        rules_text = """【游戏规则】

• 棋盘上隐藏着若干条横向或纵向相邻的"均匀渐变"色带。
  所谓"均匀渐变"，是指连续 n 个色块的 RGB 各通道值分别构成等差数列。
  例如：(1,30,100) -> (2,40,80) -> (3,50,60)，公差为 (1,10,-20)。

• 用鼠标左键点击色块即可选中（色块会缩小以示标记），
  再次点击同一色块可取消选中。

• 选好之后点击「确认」按钮进行检查（判定与点击顺序无关）：
    正确 -> 用红色虚线椭圆圈出该渐变，该条计为已找到
    数量不对 / 不成一排 / 非渐变 -> 提示"选择错误"
    只选了较长渐变中的一段 -> 提示"选择不全"

• 找到所有隐藏渐变即获胜！也可点击「看答案」直接揭示。

• 提示：仔细观察相邻色块的颜色过渡，渐变的色带通常有规律可循。
"""
        rules_label = tk.Label(frame, text=rules_text, justify="left", anchor="w",
                               font=("Microsoft YaHei", 11), fg="#34495e")
        rules_label.pack(anchor="w", pady=(0, 24))

        hint_label = tk.Label(frame, text="请选择难度开始游戏：",
                              font=("Microsoft YaHei", 14, "bold"), fg="#2c3e50")
        hint_label.pack(pady=(0, 12))

        btn_frame = tk.Frame(frame)
        btn_frame.pack()

        difficulty_config = [
            ("尝试", "3x3 棋盘\n2 条长度 3", "#a8e6cf"),
            ("简单", "6x6 棋盘\n2x3 + 2x4 + 2x5", "#dcedc1"),
            ("中等", "8x8 棋盘\n3x3 + 3x4 + 3x5", "#ffd3b6"),
            ("困难", "10x10 棋盘\n4x3 + 4x4 + 4x5", "#ffaaa5"),
        ]
        for name, desc, color in difficulty_config:
            btn_text = name + "\n" + desc
            btn = tk.Button(btn_frame, text=btn_text, width=14, height=3,
                            font=("Microsoft YaHei", 10), bg=color,
                            relief="raised", cursor="hand2",
                            command=lambda n=name: self.start_game(n))
            btn.pack(side="left", padx=10)

    def start_game(self, difficulty_name):
        self.clear_container()
        config = DIFFICULTIES[difficulty_name]
        GameBoard(parent=self.container, config=config,
                  difficulty_name=difficulty_name, on_back=self.show_intro)


# ================================================================
#  游戏面板
# ================================================================

class GameBoard:
    def __init__(self, parent, config, difficulty_name, on_back):
        self.grid_size = config["grid"]
        self.specs = config["specs"]
        self.difficulty_name = difficulty_name
        self.on_back = on_back
        self.cell = CELL_SIZES.get(self.grid_size, 55)
        # 【修复】单行计算，避免多行表达式语法歧义
        self.board_px = 2 * MARGIN + self.grid_size * self.cell + (self.grid_size - 1) * GAP

        self.frame = tk.Frame(parent)
        self.frame.pack(fill="both", expand=True)

        info_text = "难度：" + difficulty_name + "（" + str(self.grid_size) + "x" + str(self.grid_size) + "，共 " + str(len(self.specs)) + " 条渐变）"
        info_label = tk.Label(self.frame, text=info_text, font=("Microsoft YaHei", 11), fg="#555")
        info_label.pack(pady=(10, 2))

        self.canvas = tk.Canvas(self.frame, width=self.board_px, height=self.board_px,
                                bg="#1a1e24", highlightthickness=0)
        self.canvas.pack(padx=16, pady=(4, 4))
        self.canvas.bind("<Button-1>", self.on_click)

        self.status_var = tk.StringVar()
        status_label = tk.Label(self.frame, textvariable=self.status_var,
                                font=("Microsoft YaHei", 12), fg="#333")
        status_label.pack(pady=3)

        self.btn_frame = tk.Frame(self.frame)
        self.btn_frame.pack(pady=(2, 14))

        self.font_msg = tkfont.Font(family="Microsoft YaHei", size=15, weight="bold")
        self._after_id = None
        self.new_game()

    def _clear_buttons(self):
        for w in self.btn_frame.winfo_children():
            w.destroy()

    def set_game_buttons(self):
        self._clear_buttons()
        buttons = [
            ("确认", self.confirm),
            ("看答案", self.show_answer),
            ("返回", self.on_back),
            ("退出", self.frame.winfo_toplevel().destroy),
        ]
        for text, cmd in buttons:
            btn = tk.Button(self.btn_frame, text=text, width=7,
                            font=("Microsoft YaHei", 10), command=cmd)
            btn.pack(side="left", padx=5)

    def set_end_buttons(self):
        self._clear_buttons()
        buttons = [
            ("下一局", self.new_game),
            ("返回", self.on_back),
            ("退出", self.frame.winfo_toplevel().destroy),
        ]
        for text, cmd in buttons:
            btn = tk.Button(self.btn_frame, text=text, width=7,
                            font=("Microsoft YaHei", 10), command=cmd)
            btn.pack(side="left", padx=5)

    def new_game(self):
        if self._after_id is not None:
            self.frame.after_cancel(self._after_id)
            self._after_id = None
        try:
            self.lines, self.colors = generate_puzzle(self.grid_size, self.specs)
        except Exception:
            self.lines, self.colors = _fallback_puzzle(self.grid_size, self.specs)
        self.found = [False] * len(self.lines)
        self.selected = set()
        self.locked = False
        self.revealed = False
        self.message = None
        self.update_status()
        self.set_game_buttons()
        self.redraw()

    def update_status(self):
        cnt = {}
        for line, f in zip(self.lines, self.found):
            if not f:
                n = len(line)
                cnt[n] = cnt.get(n, 0) + 1
        if cnt:
            parts = []
            for k in sorted(cnt):
                parts.append("长度 " + str(k) + " 还剩 " + str(cnt[k]) + " 条")
            self.status_var.set("    ".join(parts))
        else:
            self.status_var.set("\U0001f389 全部找到！")

    def cell_rect(self, r, c, shrink=False):
        x0 = MARGIN + c * (self.cell + GAP)
        y0 = MARGIN + r * (self.cell + GAP)
        x1 = x0 + self.cell
        y1 = y0 + self.cell
        if shrink:
            d = self.cell * 0.13
            x0 = x0 + d
            y0 = y0 + d
            x1 = x1 - d
            y1 = y1 - d
        return x0, y0, x1, y1

    def draw_ring(self, line):
        rs = [p[0] for p in line]
        cs = [p[1] for p in line]
        pad = 8
        x0 = MARGIN + min(cs) * (self.cell + GAP) - pad
        y0 = MARGIN + min(rs) * (self.cell + GAP) - pad
        x1 = MARGIN + max(cs) * (self.cell + GAP) + self.cell + pad
        y1 = MARGIN + max(rs) * (self.cell + GAP) + self.cell + pad
        self.canvas.create_oval(x0, y0, x1, y1, outline="red", width=3, dash=(7, 4))

    def redraw(self):
        cv = self.canvas
        cv.delete("all")
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                sel = (r, c) in self.selected
                x0, y0, x1, y1 = self.cell_rect(r, c, shrink=sel)
                rgb = self.colors[(r, c)]
                fill_color = "#%02x%02x%02x" % rgb
                outline_color = "gold" if sel else "#1a1e24"
                line_width = 2 if sel else 1
                cv.create_rectangle(x0, y0, x1, y1, fill=fill_color,
                                    outline=outline_color, width=line_width)
        for line, f in zip(self.lines, self.found):
            if f or self.revealed:
                self.draw_ring(line)
        if self.message:
            tw = self.font_msg.measure(self.message)
            cx = self.board_px / 2
            cy = self.board_px / 2
            pad_x = 22
            pad_y = 28
            cv.create_rectangle(cx - tw / 2 - pad_x, cy - pad_y,
                                cx + tw / 2 + pad_x, cy + pad_y,
                                fill="#fffde6", outline="red", width=2)
            cv.create_text(cx, cy, text=self.message, font=self.font_msg, fill="red")

    def flash(self, text, duration_ms=2000):
        self.message = text
        if self._after_id is not None:
            self.frame.after_cancel(self._after_id)
        self._after_id = self.frame.after(duration_ms, self._clear_message)
        self.redraw()

    def _clear_message(self):
        self.message = None
        self._after_id = None
        self.redraw()

    def on_click(self, event):
        if self.locked:
            return
        c = round((event.x - MARGIN - self.cell / 2) / (self.cell + GAP))
        r = round((event.y - MARGIN - self.cell / 2) / (self.cell + GAP))
        if not (0 <= r < self.grid_size and 0 <= c < self.grid_size):
            return
        pos = (r, c)
        if pos in self.selected:
            self.selected.discard(pos)
        else:
            self.selected.add(pos)
        self.redraw()

    @staticmethod
    def is_contiguous_subsegment(sel, line):
        if len(sel) >= len(line):
            return False
        pos_map = {}
        for i, p in enumerate(line):
            pos_map[p] = i
        indices = []
        for p in sel:
            if p not in pos_map:
                return False
            indices.append(pos_map[p])
        indices.sort()
        expected = list(range(indices[0], indices[0] + len(indices)))
        return indices == expected

    def confirm(self):
        if self.locked:
            return
        sel = set(self.selected)
        if len(sel) in (3, 4, 5):
            for i, line in enumerate(self.lines):
                if not self.found[i] and set(line) == sel:
                    self.found[i] = True
                    self.selected.clear()
                    self.update_status()
                    if all(self.found):
                        self.locked = True
                        self.message = "你赢了，是否开始下一局？"
                        self.set_end_buttons()
                    self.redraw()
                    return
            for i, line in enumerate(self.lines):
                if not self.found[i] and self.is_contiguous_subsegment(sel, line):
                    self.selected.clear()
                    self.flash("选择不全")
                    return
        self.selected.clear()
        self.flash("选择错误")

    def show_answer(self):
        if self.locked:
            return
        self.locked = True
        self.revealed = True
        self.selected.clear()
        self.set_end_buttons()
        self.redraw()


# ================================================================
#  程序入口
# ================================================================

def main():
    root = tk.Tk()
    ColorBingoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
