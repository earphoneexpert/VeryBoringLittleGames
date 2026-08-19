规则：
  * 每块由 5 个单位方格组成，且边相连（仅顶点相连不算连通）
  * 旋转后能重合 → 同一种形状；仅镜像能重合 → 算不同形状
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

ROWS, COLS = 6, 10
LETTERS = "ABCDEFGHIJKLMNOPQR"   # 最多 18 种拼图的标签


# ---------------- 1. 生成全部五格拼图（镜像视为不同） ----------------
def rotations(shape):
    """返回 shape 旋转 0°/90°/180°/270° 后的规范化形式。"""
    out = []
    for k in range(4):
        cells = list(shape)
        for _ in range(k):
            cells = [(c, -r) for r, c in cells]          # 顺时针转 90°
        r0 = min(r for r, _ in cells)
        c0 = min(c for _, c in cells)
        out.append(tuple(sorted((r - r0, c - c0) for r, c in cells)))
    return out


def generate_pentominoes():
    """DFS 枚举所有 5 格连通图形，按旋转去重 → 得到 18 种。"""
    seen, result = set(), []

    def grow(cells, k):
        if k == 5:
            can = min(rotations(cells))                  # 旋转下的规范形
            if can not in seen:
                seen.add(can)
                result.append(can)
            return
        nbrs = set()
        for r, c in cells:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if (r + dr, c + dc) not in cells:
                    nbrs.add((r + dr, c + dc))
        for nb in nbrs:
            grow(cells | {nb}, k + 1)

    grow({(0, 0)}, 1)
    return result


# ---------------- 2. 回溯搜索：选 12 种不同形状铺满 5×12 ----------------
def solve(pieces):
    # 预先算出每块拼图的全部不同朝向（格子按行主序排序）
    orients = []
    for p in pieces:
        orients.append([tuple(sorted(rot)) for rot in set(rotations(p))])

    grid = [[-1] * COLS for _ in range(ROWS)]
    used = [False] * len(pieces)
    solution = []

    def first_empty():
        """按行主序找第一个空格。"""
        for r in range(ROWS):
            for c in range(COLS):
                if grid[r][c] == -1:
                    return r, c
        return None

    def backtrack(n):
        if n == 12:
            return True
        pos = first_empty()
        if pos is None:
            return False
        r0, c0 = pos
        for i in range(len(pieces)):
            if used[i]:
                continue
            for ori in orients[i]:
                # 拼图中"行主序最小格"必须恰好落在第一个空格上，
                # 否则会覆盖已填格子，因此只需试这一种锚点
                ar, ac = ori[0]
                dr, dc = r0 - ar, c0 - ac
                cells = [(r + dr, c + dc) for r, c in ori]
                if all(0 <= r < ROWS and 0 <= c < COLS and grid[r][c] == -1
                       for r, c in cells):
                    for r, c in cells:
                        grid[r][c] = i
                    used[i] = True
                    solution.append((i, cells))
                    if backtrack(n + 1):
                        return True
                    for r, c in cells:
                        grid[r][c] = -1
                    used[i] = False
                    solution.pop()
        return False

    return (grid, solution) if backtrack(0) else (None, None)


# ---------------- 3. 绘图 ----------------
def draw(grid, solution):
    colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
              '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe',
              '#008080', '#9a6324']
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei',
                                       'PingFang SC', 'Arial Unicode MS',
                                       'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    color_of = {idx: colors[k] for k, (idx, _) in enumerate(solution)}

    fig, ax = plt.subplots(figsize=(13, 6))
    for r in range(ROWS):
        for c in range(COLS):
            ax.add_patch(mpatches.Rectangle(
                (c, ROWS - 1 - r), 1, 1,
                facecolor=color_of[grid[r][c]],
                edgecolor='black', linewidth=1.8))

    # 在每块拼图的重心处标注字母
    for idx, cells in solution:
        cr = sum(r for r, _ in cells) / 5
        cc = sum(c for _, c in cells) / 5
        ax.text(cc + 0.5, ROWS - 0.5 - cr, LETTERS[idx],
                ha='center', va='center', fontsize=14, fontweight='bold')

    ax.set_xlim(0, COLS)
    ax.set_ylim(0, ROWS)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('5×12 矩形由 12 个互不相同的五格拼图铺满')
    plt.tight_layout()
    plt.savefig('pentomino_tiling.png', dpi=150, bbox_inches='tight')
    print('图片已保存为 pentomino_tiling.png')
    plt.show()


# ---------------- 主程序 ----------------
if __name__ == '__main__':
    pieces = generate_pentominoes()
    print(f'镜像视为不同时，五格拼图共有 {len(pieces)} 种')   # 应为 18

    grid, solution = solve(pieces)
    if grid is None:
        print('不能')
    else:
        print('可以！找到一种铺法（字母代表不同拼图）：')
        for r in range(ROWS):
            print('  ' + ' '.join(LETTERS[grid[r][c]] for c in range(COLS)))
        draw(grid, solution)
