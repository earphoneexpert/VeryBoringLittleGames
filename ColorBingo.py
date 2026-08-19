"""
颜色 Bingo（Python 3.12 + tkinter）
=====================================
功能：
  - 引导页：展示游戏规则 + 四档难度选择
  - 游戏页：6×6（或其他尺寸）随机色块棋盘，隐藏若干条"均匀渐变"色带
  - 严格保证：有且仅有指定数量的渐变，不会多也不会少
  - 交互：点击选中/取消、确认判定、看答案、返回引导页、退出

难度配置：
  尝试：3×3 棋盘，2 条长度 3
  简单：6×6 棋盘，2×长度3 + 2×长度4 + 2×长度5
  中等：8×8 棋盘，3×长度3 + 3×长度4 + 3×长度5
  困难：10×10 棋盘，4×长度3 + 4×长度4 + 4×长度5

运行方式：python color_bingo.py
"""

import math
import random
import tkinter as tk
import tkinter.font as tkfont

# ================================================================
#  全局配置
# ================================================================

# 各难度的棋盘大小和渐变线段规格
DIFFICULTIES = {
    "尝试": {"grid": 3,  "specs": [3, 3]},
    "简单": {"grid": 6,  "specs": [3, 3, 4, 4, 5, 5]},
    "中等": {"grid": 8,  "specs": [3, 3, 3, 4, 4, 4, 5, 5, 5]},
    "困难": {"grid": 10, "specs": [3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5]},
}

# 各棋盘尺寸对应的色块边长（像素），保证窗口大小适中
CELL_SIZES = {3: 90, 6: 64, 8: 56, 10: 50}

GAP = 5          # 色块之间的间隙（像素）
MARGIN = 16      # 画布四周留白（像素）

# 渐变公差的最小绝对值（低于此值肉眼难以分辨）
MIN_STEP_ABS = 15

# 生成渐变时的最大重试次数
MAX_GRADIENT_RETRIES = 600

# 放置线段时的最大重试次数
MAX_PLACEMENT_RETRIES = 2000

# 整体谜题生成的最大重试次数（防止极端情况死循环）
MAX_PUZZLE_RETRIES = 500


# ================================================================
#  谜题生成模块
# ================================================================

def compute_step_bounds(c, n, k):
    """
    已知一条长度为 n 的等差数列中，第 k 项（0-indexed）的某个颜色通道值为 c，
    计算使所有 n 项都落在 [0, 255] 范围内的公差 d 的合法整数区间 [lo, hi]。

    推导：第 j 项的值 = c + (j - k) * d，需要 0 <= c + (j-k)*d <= 255 对所有 j。
    """
    lo, hi = -255, 255
    for j in range(n):
        t = j - k  # t 表示第 j 项相对于第 k 项的偏移
        if t > 0:
            # c + t*d >= 0  =>  d >= -c/t
            # c + t*d <= 255 =>  d <= (255-c)/t
            lo = max(lo, math.ceil(-c / t))
            hi = min(hi, (255 - c) // t)
        elif t < 0:
            # c + t*d >= 0  =>  d <= c/(-t)   （注意 t<0 翻转不等号）
            # c + t*d <= 255 =>  d >= (255-c)/(-t)  =>  d >= (c-255)/t
            hi = min(hi, c // (-t))
            lo = max(lo, math.ceil((c - 255) / t))
        # t == 0 时无约束
    return lo, hi


def pick_visible_step(lo, hi):
    """
    在合法公差范围 [lo, hi] 内选取一个"肉眼可见"的公差值。
    优先选 |d| >= MIN_STEP_ABS 的值；若不存在则退而求其次。
    """
    candidates = [d for d in range(lo, hi + 1) if abs(d) >= MIN_STEP_ABS]
    if candidates:
        return random.choice(candidates)
    # 如果范围内没有足够大的公差，就随机选一个
    if lo <= hi:
        return random.randint(lo, hi)
    return 0  # 理论上不应到达这里


def make_gradient(n, fixed):
    """
    生成长度为 n 的 RGB 等差渐变序列。

    参数：
      n     : 渐变长度（3、4 或 5）
      fixed : 列表，至多包含一个元组 (位置k, 已固定的颜色RGB)。
              当此渐变线段与其他线段共享一个格子时，该格子的颜色已被确定，
              新生成的渐变必须经过该颜色。

    返回：
      长度为 n 的列表，每个元素是 (R, G, B) 元组；失败返回 None。
    """
    if len(fixed) > 1:
        # 一条线最多与已放置线共享 1 个格子（由放置逻辑保证）
        return None

    for _ in range(MAX_GRADIENT_RETRIES):
        if fixed:
            # 有固定点：以该点为锚，生成经过它的渐变
            k, c0 = fixed[0]
            steps = []
            valid = True
            for ch in range(3):
                lo, hi = compute_step_bounds(c0[ch], n, k)
                if lo > hi:
                    valid = False
                    break
                steps.append(pick_visible_step(lo, hi))
            if not valid:
                continue
            # 检查渐变是否足够明显（三个通道的公差绝对值之和）
            if sum(abs(s) for s in steps) < 20:
                continue
            # 生成序列
            return [
                tuple(c0[ch] + (i - k) * steps[ch] for ch in range(3))
                for i in range(n)
            ]
        else:
            # 无固定点：自由生成
            steps = [random.randint(-60, 60) for _ in range(3)]
            if sum(abs(s) for s in steps) < 20:
                continue
            starts = []
            valid = True
            for ch in range(3):
                # 首项范围：确保末项也在 [0,255]
                lo_s = max(0, -(n - 1) * steps[ch])
                hi_s = min(255, 255 - (n - 1) * steps[ch])
                if lo_s > hi_s:
                    valid = False
                    break
                starts.append(random.randint(lo_s, hi_s))
            if not valid:
                continue
            return [
                tuple(starts[ch] + i * steps[ch] for ch in range(3))
                for i in range(n)
            ]
    return None


def find_generation_order(lines):
    """
    为已放置的线段找一个生成顺序，使得每条线在生成渐变颜色时，
    最多只有一个格子已被之前的线固定。

    这保证了 make_gradient 的 fixed 参数至多含一个元素，从而一定能生成兼容的渐变。

    算法：贪心——每次从剩余线中选一条与已选线集合交集 ≤1 的线。
    """
    sets = [set(line) for line in lines]
    remaining = list(range(len(lines)))
    picked = set()
    order = []

    while remaining:
        found = False
        for i in remaining:
            # 计算 line[i] 与所有已选线的重合格子总数
            overlap_count = sum(1 for j in picked if sets[i] & sets[j])
            if overlap_count <= 1:
                order.append(i)
                picked.add(i)
                remaining.remove(i)
                found = True
                break
        if not found:
            return None  # 无法找到合法顺序（理论上不应发生）
    return order


def is_arithmetic_progression(colors):
    """
    判断一串颜色是否每个 RGB 通道都构成等差数列。
    colors: 长度 ≥ 2 的颜色列表。
    """
    if len(colors) < 3:
        return False
    for ch in range(3):
        d = colors[1][ch] - colors[0][ch]
        for i in range(2, len(colors)):
            if colors[i][ch] - colors[i - 1][ch] != d:
                return False
    return True


def verify_no_extra_gradients(grid_size, colors, placed_lines):
    """
    【关键校验函数】
    严格验证：在整个 grid_size × grid_size 棋盘中，
    所有长度 ≥ 3 的横向/纵向连续段里，凡是构成等差渐变的，
    必须是某条已放置线段的子集。

    如果存在任何"意外渐变"（不属于任何已放置线段的子段），返回 False。
    这确保了"有且仅有"指定数量的渐变。

    参数：
      grid_size    : 棋盘边长
      colors       : dict, (r,c) -> (R,G,B)
      placed_lines : 已放置的线段列表，每条是 [(r,c), ...] 的列表
    """
    placed_sets = [set(line) for line in placed_lines]

    for r in range(grid_size):
        for c in range(grid_size):
            # 只从每行/每列的起点开始扫描，避免重复
            for dr, dc in ((0, 1), (1, 0)):
                # 检查 (r,c) 是否是该方向的起点
                pr, pc = r - dr, c - dc
                if 0 <= pr < grid_size and 0 <= pc < grid_size:
                    continue  # 不是起点，跳过

                # 收集该方向上的完整序列
                run = []
                rr, cc = r, c
                while 0 <= rr < grid_size and 0 <= cc < grid_size:
                    run.append((rr, cc))
                    rr += dr
                    cc += dc

                # 检查该序列中所有长度 ≥ 3 的连续子段
                for i in range(len(run)):
                    for j in range(i + 3, len(run) + 1):
                        seg = run[i:j]
                        seg_colors = [colors[p] for p in seg]
                        if is_arithmetic_progression(seg_colors):
                            # 这段是渐变——检查它是否是某条已放置线的子集
                            seg_set = set(seg)
                            is_subset_of_placed = any(
                                seg_set <= ps for ps in placed_sets
                            )
                            if not is_subset_of_placed:
                                return False  # 发现意外渐变！
    return True


def try_generate_puzzle(grid_size, specs):
    """
    尝试生成一局谜题。成功返回 (lines, colors)，失败返回 None。

    步骤：
      1. 随机放置所有线段（保证任意两条最多重合 1 格）
      2. 找到安全的颜色生成顺序
      3. 按顺序生成每条线的渐变颜色（处理重合格的颜色兼容）
      4. 用随机颜色填充剩余格子
      5. 严格校验不存在意外渐变
    """
    # --- 步骤 1：放置线段 ---
    specs_shuffled = list(specs)
    random.shuffle(specs_shuffled)  # 随机打乱放置顺序，增加多样性

    lines = []
    for length in specs_shuffled:
        placed = False
        for _ in range(MAX_PLACEMENT_RETRIES):
            # 随机选择方向：水平或垂直
            if random.random() < 0.5:
                # 水平线段
                if grid_size < length:
                    continue
                r = random.randrange(grid_size)
                c = random.randrange(grid_size - length + 1)
                cells = [(r, c + i) for i in range(length)]
            else:
                # 垂直线段
                if grid_size < length:
                    continue
                r = random.randrange(grid_size - length + 1)
                c = random.randrange(grid_size)
                cells = [(r + i, c) for i in range(length)]

            # 检查与所有已放置线的重合：任意两条最多共享 1 个格子
            if all(len(set(cells) & set(existing)) <= 1 for existing in lines):
                lines.append(cells)
                placed = True
                break

        if not placed:
            return None  # 放置失败

    # --- 步骤 2：找生成顺序 ---
    order = find_generation_order(lines)
    if order is None:
        return None

    # --- 步骤 3：按顺序生成渐变颜色 ---
    colors = {}
    for idx in order:
        line = lines[idx]
        # 找出该线中已被之前线段固定颜色的格子
        fixed = [(i, colors[p]) for i, p in enumerate(line) if p in colors]
        grad = make_gradient(len(line), fixed)
        if grad is None:
            return None
        for pos, col in zip(line, grad):
            colors[pos] = col

    # --- 步骤 4：填充随机底色 ---
    for r in range(grid_size):
        for c in range(grid_size):
            if (r, c) not in colors:
                colors[(r, c)] = tuple(random.randint(0, 255) for _ in range(3))

    # --- 步骤 5：严格校验 ---
    if not verify_no_extra_gradients(grid_size, colors, lines):
        return None  # 存在意外渐变，本次生成作废

    return lines, colors


def generate_puzzle(grid_size, specs):
    """
    反复尝试生成谜题，直到成功。
    由于有 MAX_PUZZLE_RETRIES 上限，极端情况下不会死循环。
    """
    for _ in range(MAX_PUZZLE_RETRIES):
        result = try_generate_puzzle(grid_size, specs)
        if result is not None:
            return result
    # 极端情况兜底（正常不应到达）
    raise RuntimeError("谜题生成失败，请重试")


# ================================================================
#  应用主窗口（管理引导页和游戏页的切换）
# ================================================================

class ColorBingoApp:
    """
    应用主窗口。负责：
      - 显示引导页（规则 + 难度选择）
      - 切换到游戏页
      - 从游戏页返回引导页
    """

    def __init__(self, root):
        self.root = root
        root.title("颜色 Bingo")
        root.resizable(False, False)

        # 主容器：所有页面都放在这个 Frame 里，切换时清空重建
        self.container = tk.Frame(root)
        self.container.pack(fill="both", expand=True)

        # 显示引导页
        self.show_intro()

    def clear_container(self):
        """清空主容器中的所有控件。"""
        for widget in self.container.winfo_children():
            widget.destroy()

    # -------------------- 引导页 --------------------
    def show_intro(self):
        """显示游戏规则引导页。"""
        self.clear_container()

        frame = tk.Frame(self.container, padx=40, pady=28)
        frame.pack(expand=True)

        # 标题
        tk.Label(
            frame, text="🎨 颜色 Bingo 🎨",
            font=("Microsoft YaHei", 26, "bold"), fg="#2c3e50"
        ).pack(pady=(0, 20))

        # 规则文本
        rules_text = (
            "【游戏规则】\n"
            "\n"
            "• 棋盘上隐藏着若干条横向或纵向相邻的"均匀渐变"色带。\n"
            "  所谓"均匀渐变"，是指连续 n 个色块的 RGB 各通道值分别构成等差数列。\n"
            "  例如：(1,30,100) → (2,40,80) → (3,50,60)，公差为 (1,10,-20)。\n"
            "\n"
            "• 用鼠标左键点击色块即可选中（色块会缩小以示标记），\n"
            "  再次点击同一色块可取消选中。\n"
            "\n"
            "• 选好之后点击「确认」按钮进行检查（判定与点击顺序无关）：\n"
            "    ✓ 正确 → 用红色虚线椭圆圈出该渐变，该条计为已找到\n"
            "    ✗ 数量不对 / 不成一排 / 非渐变 → 提示"选择错误"\n"
            "    ⚠ 只选了较长渐变中的一段 → 提示"选择不全"\n"
            "\n"
            "• 找到所有隐藏渐变即获胜！也可点击「看答案」直接揭示。\n"
            "\n"
            "• 提示：仔细观察相邻色块的颜色过渡，渐变的色带通常有规律可循。\n"
        )
        tk.Label(
            frame, text=rules_text, justify="left", anchor="w",
            font=("Microsoft YaHei", 11), fg="#34495e"
        ).pack(anchor="w", pady=(0, 24))

        # 难度选择
        tk.Label(
            frame, text="请选择难度开始游戏：",
            font=("Microsoft YaHei", 14, "bold"), fg="#2c3e50"
        ).pack(pady=(0, 12))

        btn_frame = tk.Frame(frame)
        btn_frame.pack()

        # 各难度的按钮配置
        difficulty_config = [
            ("尝试", "3×3 棋盘\n2 条长度 3", "#a8e6cf"),
            ("简单", "6×6 棋盘\n2×3 + 2×4 + 2×5", "#dcedc1"),
            ("中等", "8×8 棋盘\n3×3 + 3×4 + 3×5", "#ffd3b6"),
            ("困难", "10×10 棋盘\n4×3 + 4×4 + 4×5", "#ffaaa5"),
        ]

        for name, desc, color in difficulty_config:
            tk.Button(
                btn_frame, text=f"{name}\n{desc}",
                width=14, height=3,
                font=("Microsoft YaHei", 10),
                bg=color, relief="raised", cursor="hand2",
                command=lambda n=name: self.start_game(n)
            ).pack(side="left", padx=10)

    # -------------------- 进入游戏 --------------------
    def start_game(self, difficulty_name):
        """切换到游戏页面。"""
        self.clear_container()
        config = DIFFICULTIES[difficulty_name]
        GameBoard(
            parent=self.container,
            config=config,
            difficulty_name=difficulty_name,
            on_back=self.show_intro  # 返回引导页的回调
        )


# ================================================================
#  游戏面板（核心游戏逻辑）
# ================================================================

class GameBoard:
    """
    游戏面板：负责棋盘绘制、交互逻辑、判定、状态管理。
    """

    def __init__(self, parent, config, difficulty_name, on_back):
        self.grid_size = config["grid"]
        self.specs = config["specs"]
        self.difficulty_name = difficulty_name
        self.on_back = on_back
        self.cell = CELL_SIZES.get(self.grid_size, 55)

        # 计算画布像素尺寸
        self.board_px = 2 * MARGIN + self.grid_size * self.cell + (self.grid_size - 1) * GAP

        # 构建 UI
        self.frame = tk.Frame(parent)
        self.frame.pack(fill="both", expand=True)

        # 难度标签
        tk.Label(
            self.frame,
            text=f"难度：{difficulty_name}（{self.grid_size}×{self.grid_size}，"
                 f"共 {len(self.specs)} 条渐变）",
            font=("Microsoft YaHei", 11), fg="#555"
        ).pack(pady=(10, 2))

        # 画布
        self.canvas = tk.Canvas(
            self.frame, width=self.board_px, height=self.board_px,
            bg="#1a1e24", highlightthickness=0
        )
        self.canvas.pack(padx=16, pady=(4, 4))
        self.canvas.bind("<Button-1>", self.on_click)

        # 状态栏（显示剩余条数）
        self.status_var = tk.StringVar()
        tk.Label(
            self.frame, textvariable=self.status_var,
            font=("Microsoft YaHei", 12), fg="#333"
        ).pack(pady=3)

        # 按钮栏
        self.btn_frame = tk.Frame(self.frame)
        self.btn_frame.pack(pady=(2, 14))

        # 提示文字的字体
        self.font_msg = tkfont.Font(family="Microsoft YaHei", size=15, weight="bold")

        # 定时器 ID（用于 2 秒后清除提示）
        self._after_id = None

        # 开始新一局
        self.new_game()

    # -------------------- 按钮管理 --------------------
    def _clear_buttons(self):
        """清空按钮栏。"""
        for w in self.btn_frame.winfo_children():
            w.destroy()

    def set_game_buttons(self):
        """设置游戏中的按钮：确认、看答案、返回、退出。"""
        self._clear_buttons()
        buttons = [
            ("确认", self.confirm),
            ("看答案", self.show_answer),
            ("返回", self.on_back),
            ("退出", self.frame.winfo_toplevel().destroy),
        ]
        for text, cmd in buttons:
            tk.Button(
                self.btn_frame, text=text, width=7,
                font=("Microsoft YaHei", 10), command=cmd
            ).pack(side="left", padx=5)

    def set_end_buttons(self):
        """设置结束时的按钮：下一局、返回、退出。"""
        self._clear_buttons()
        buttons = [
            ("下一局", self.new_game),
            ("返回", self.on_back),
            ("退出", self.frame.winfo_toplevel().destroy),
        ]
        for text, cmd in buttons:
            tk.Button(
                self.btn_frame, text=text, width=7,
                font=("Microsoft YaHei", 10), command=cmd
            ).pack(side="left", padx=5)

    # -------------------- 游戏生命周期 --------------------
    def new_game(self):
        """开始新一局：生成谜题、重置状态。"""
        # 取消可能存在的定时器
        if self._after_id is not None:
            self.frame.after_cancel(self._after_id)
            self._after_id = None

        # 生成谜题
        self.lines, self.colors = generate_puzzle(self.grid_size, self.specs)

        # 重置状态
        self.found = [False] * len(self.lines)  # 每条线是否已被找到
        self.selected = set()                    # 当前选中的格子集合
        self.locked = False                      # 棋盘是否锁定（胜利/看答案后）
        self.revealed = False                    # 是否已揭示所有答案
        self.message = None                      # 当前显示的提示文字

        self.update_status()
        self.set_game_buttons()
        self.redraw()

    def update_status(self):
        """更新底部状态栏，显示各长度还剩几条未找到。"""
        cnt = {}
        for line, f in zip(self.lines, self.found):
            if not f:
                n = len(line)
                cnt[n] = cnt.get(n, 0) + 1

        if cnt:
            parts = [f"长度 {k} 还剩 {cnt[k]} 条" for k in sorted(cnt)]
            self.status_var.set("    ".join(parts))
        else:
            self.status_var.set("🎉 全部找到！")

    # -------------------- 绘制 --------------------
    def cell_rect(self, r, c, shrink=False):
        """
        计算格子 (r, c) 在画布上的矩形坐标。
        shrink=True 时缩小（表示选中状态）。
        """
        x0 = MARGIN + c * (self.cell + GAP)
        y0 = MARGIN + r * (self.cell + GAP)
        x1, y1 = x0 + self.cell, y0 + self.cell
        if shrink:
            d = self.cell * 0.13  # 缩小 13%
            x0 += d
            y0 += d
            x1 -= d
            y1 -= d
        return x0, y0, x1, y1

    def draw_ring(self, line):
        """
        用红色虚线椭圆（鼓形）圈住一条线段。
        只画边框，不填充，不会遮挡色块。
        """
        rs = [p[0] for p in line]
        cs = [p[1] for p in line]
        pad = 8  # 椭圆比色块区域稍大
        x0 = MARGIN + min(cs) * (self.cell + GAP) - pad
        y0 = MARGIN + min(rs) * (self.cell + GAP) - pad
        x1 = MARGIN + max(cs) * (self.cell + GAP) + self.cell + pad
        y1 = MARGIN + max(rs) * (self.cell + GAP) + self.cell + pad
        self.canvas.create_oval(x0, y0, x1, y1,
                                outline="red", width=3, dash=(7, 4))

    def redraw(self):
        """完整重绘画布。"""
        cv = self.canvas
        cv.delete("all")

        # 1. 画所有色块
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                sel = (r, c) in self.selected
                x0, y0, x1, y1 = self.cell_rect(r, c, shrink=sel)
                fill_color = "#%02x%02x%02x" % self.colors[(r, c)]
                cv.create_rectangle(
                    x0, y0, x1, y1,
                    fill=fill_color,
                    outline="gold" if sel else "#1a1e24",
                    width=2 if sel else 1
                )

        # 2. 画已找到 / 已揭示的红色虚线椭圆
        for line, f in zip(self.lines, self.found):
            if f or self.revealed:
                self.draw_ring(line)

        # 3. 画中央提示文字（如果有）
        if self.message:
            tw = self.font_msg.measure(self.message)
            cx, cy = self.board_px / 2, self.board_px / 2
            pad_x, pad_y = 22, 28
            cv.create_rectangle(
                cx - tw / 2 - pad_x, cy - pad_y,
                cx + tw / 2 + pad_x, cy + pad_y,
                fill="#fffde6", outline="red", width=2
            )
            cv.create_text(
                cx, cy, text=self.message,
                font=self.font_msg, fill="red"
            )

    def flash(self, text, duration_ms=2000):
        """
        在画布中央显示提示文字，duration_ms 毫秒后自动消失。
        """
        self.message = text
        if self._after_id is not None:
            self.frame.after_cancel(self._after_id)
        self._after_id = self.frame.after(duration_ms, self._clear_message)
        self.redraw()

    def _clear_message(self):
        """清除提示文字并重绘。"""
        self.message = None
        self._after_id = None
        self.redraw()

    # -------------------- 交互逻辑 --------------------
    def on_click(self, event):
        """处理鼠标点击：选中/取消选中色块。"""
        if self.locked:
            return

        # 将像素坐标转换为格子坐标
        c = round((event.x - MARGIN - self.cell / 2) / (self.cell + GAP))
        r = round((event.y - MARGIN - self.cell / 2) / (self.cell + GAP))

        if not (0 <= r < self.grid_size and 0 <= c < self.grid_size):
            return

        pos = (r, c)
        if pos in self.selected:
            self.selected.discard(pos)  # 取消选中
        else:
            self.selected.add(pos)      # 选中
        self.redraw()

    @staticmethod
    def is_contiguous_subsegment(sel, line):
        """
        判断 sel（选中的格子集合）是否是 line（一条完整渐变线段）中
        一段连续的、且长度更短的子段。

        用于检测"选择不全"的情况：
        例如线是 5 格，但玩家只选了其中连续的 3 格。
        """
        if len(sel) >= len(line):
            return False
        # 建立 line 中每个格子的位置索引
        pos_map = {p: i for i, p in enumerate(line)}
        indices = []
        for p in sel:
            if p not in pos_map:
                return False  # sel 中有不属于 line 的格子
            indices.append(pos_map[p])
        indices.sort()
        # 检查是否连续
        return indices == list(range(indices[0], indices[0] + len(indices)))

    def confirm(self):
        """
        点击「确认」按钮后的判定逻辑。
        判定与选择顺序无关（使用集合比较）。
        """
        if self.locked:
            return

        sel = set(self.selected)

        # 首先检查数量是否合法
        if len(sel) in (3, 4, 5):
            # 检查是否完全命中某条未找到的线
            for i, line in enumerate(self.lines):
                if not self.found[i] and set(line) == sel:
                    # 命中！
                    self.found[i] = True
                    self.selected.clear()
                    self.update_status()
                    if all(self.found):
                        # 全部找到，获胜
                        self.locked = True
                        self.message = "你赢了，是否开始下一局？"
                        self.set_end_buttons()
                    self.redraw()
                    return

            # 检查是否是某条较长线的连续子段（"选择不全"）
            for i, line in enumerate(self.lines):
                if not self.found[i] and self.is_contiguous_subsegment(sel, line):
                    self.selected.clear()
                    self.flash("选择不全")
                    return

        # 其他情况：选择错误
        self.selected.clear()
        self.flash("选择错误")

    def show_answer(self):
        """点击「看答案」：揭示所有渐变，锁定棋盘。"""
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
    app = ColorBingoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
