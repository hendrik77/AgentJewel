import pygame
import random
import math
import sys

pygame.init()

# ── Constants ──────────────────────────────────────────────────────────
COLS, ROWS = 8, 8
CELL = 72
MARGIN = 4
BOARD_OFFSET_X = 60
BOARD_OFFSET_Y = 140
BOARD_W = COLS * CELL
BOARD_H = ROWS * CELL
WIN_W = BOARD_W + BOARD_OFFSET_X * 2
WIN_H = BOARD_H + BOARD_OFFSET_Y + 60

FPS = 60

# Pastel jewel colours (fill, highlight, shadow)
JEWEL_STYLES = [
    {"name": "ruby",     "fill": (255, 100, 130), "hi": (255, 180, 200), "sh": (180,  40,  70)},
    {"name": "sapphire", "fill": ( 80, 140, 255), "hi": (160, 200, 255), "sh": ( 30,  70, 180)},
    {"name": "emerald",  "fill": ( 80, 210, 130), "hi": (160, 240, 190), "sh": ( 30, 140,  80)},
    {"name": "topaz",    "fill": (255, 210,  60), "hi": (255, 240, 160), "sh": (180, 140,  20)},
    {"name": "amethyst", "fill": (200, 100, 255), "hi": (230, 180, 255), "sh": (130,  40, 190)},
    {"name": "coral",    "fill": (255, 160,  80), "hi": (255, 210, 160), "sh": (190,  90,  20)},
]
NUM_TYPES = len(JEWEL_STYLES)

# UI colours
BG_TOP    = (255, 240, 250)
BG_BOT    = (230, 200, 245)
BOARD_BG  = (255, 255, 255, 60)
CELL_A    = (255, 245, 252)
CELL_B    = (245, 230, 250)
SEL_COL   = (255, 220,  80)
MATCH_COL = (255, 255, 255)
TEXT_COL  = (120,  60, 140)
TITLE_COL = (200,  80, 160)

FONT_TITLE = pygame.font.SysFont("Arial Rounded MT Bold", 42, bold=True)
FONT_SCORE = pygame.font.SysFont("Arial Rounded MT Bold", 28)
FONT_INFO  = pygame.font.SysFont("Arial Rounded MT Bold", 20)
FONT_BIG   = pygame.font.SysFont("Arial Rounded MT Bold", 56, bold=True)

# ── Helpers ──────────────────────────────────────────────────────────

def board_rect(col, row):
    x = BOARD_OFFSET_X + col * CELL + MARGIN
    y = BOARD_OFFSET_Y + row * CELL + MARGIN
    return pygame.Rect(x, y, CELL - MARGIN * 2, CELL - MARGIN * 2)


def cell_from_pos(mx, my):
    col = (mx - BOARD_OFFSET_X) // CELL
    row = (my - BOARD_OFFSET_Y) // CELL
    if 0 <= col < COLS and 0 <= row < ROWS:
        return col, row
    return None, None


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out(t):
    return 1 - (1 - t) ** 3


# ── Drawing ──────────────────────────────────────────────────────────

def draw_gradient(surf, top_col, bot_col):
    h = surf.get_height()
    for y in range(h):
        t = y / h
        r = int(lerp(top_col[0], bot_col[0], t))
        g = int(lerp(top_col[1], bot_col[1], t))
        b = int(lerp(top_col[2], bot_col[2], t))
        pygame.draw.line(surf, (r, g, b), (0, y), (surf.get_width(), y))


def draw_jewel(surf, style, rect, alpha=255, scale=1.0, glow=False):
    cx, cy = rect.centerx, rect.centery
    r = int((rect.width // 2 - 2) * scale)
    if r < 2:
        return

    fill = style["fill"]
    hi   = style["hi"]
    sh   = style["sh"]

    # Outer glow for selected / matched
    if glow:
        glow_surf = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
        for gr in range(18, 0, -2):
            a = max(0, 120 - gr * 6)
            pygame.draw.circle(glow_surf, (*SEL_COL, a),
                               (glow_surf.get_width() // 2, glow_surf.get_height() // 2), r + gr)
        surf.blit(glow_surf, (cx - glow_surf.get_width() // 2, cy - glow_surf.get_height() // 2))

    # Shadow
    pygame.draw.circle(surf, sh, (cx + 2, cy + 3), r)
    # Body
    pygame.draw.circle(surf, fill, (cx, cy), r)
    # Highlight spot
    hx = cx - r // 3
    hy = cy - r // 3
    hr = max(2, r // 3)
    pygame.draw.circle(surf, hi, (hx, hy), hr)
    # Tiny sparkle
    sp = max(1, r // 6)
    pygame.draw.circle(surf, (255, 255, 255), (hx + hr // 2, hy - hr // 2), sp)


def draw_board_bg(surf):
    for row in range(ROWS):
        for col in range(COLS):
            rect = board_rect(col, row)
            col_fill = CELL_A if (col + row) % 2 == 0 else CELL_B
            pygame.draw.rect(surf, col_fill, rect, border_radius=12)


def draw_rounded_panel(surf, rect, colour, radius=18, alpha=200):
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (*colour, alpha), s.get_rect(), border_radius=radius)
    surf.blit(s, rect.topleft)


# ── Board logic ──────────────────────────────────────────────────────────

def new_board():
    board = [[0] * COLS for _ in range(ROWS)]
    for row in range(ROWS):
        for col in range(COLS):
            choices = list(range(NUM_TYPES))
            # Avoid immediate matches on creation
            if col >= 2 and board[row][col-1] == board[row][col-2]:
                choices.remove(board[row][col-1])
            if row >= 2 and board[row-1][col] == board[row-2][col]:
                choices.remove(board[row-1][col])
            board[row][col] = random.choice(choices)
    return board


def find_matches(board):
    matched = set()
    for row in range(ROWS):
        for col in range(COLS - 2):
            if board[row][col] == board[row][col+1] == board[row][col+2] >= 0:
                matched |= {(row, col), (row, col+1), (row, col+2)}
    for col in range(COLS):
        for row in range(ROWS - 2):
            if board[row][col] == board[row+1][col] == board[row+2][col] >= 0:
                matched |= {(row, col), (row+1, col), (row+2, col)}
    return matched


def swap(board, c1, r1, c2, r2):
    board[r1][c1], board[r2][c2] = board[r2][c2], board[r1][c1]


def gravity(board):
    moved = False
    for col in range(COLS):
        write = ROWS - 1
        for row in range(ROWS - 1, -1, -1):
            if board[row][col] >= 0:
                board[write][col] = board[row][col]
                if write != row:
                    board[row][col] = -1
                    moved = True
                write -= 1
        for row in range(write, -1, -1):
            board[row][col] = -1
            moved = True
    return moved


def fill_empty(board):
    for row in range(ROWS):
        for col in range(COLS):
            if board[row][col] == -1:
                board[row][col] = random.randint(0, NUM_TYPES - 1)


def are_adjacent(c1, r1, c2, r2):
    return abs(c1 - c2) + abs(r1 - r2) == 1


# ── Particle system ──────────────────────────────────────────────────────────

class Particle:
    def __init__(self, x, y, colour):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.tau)
        speed = random.uniform(2, 6)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.colour = colour
        self.life = 1.0
        self.decay = random.uniform(0.03, 0.07)
        self.size = random.randint(3, 7)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.18
        self.life -= self.decay
        return self.life > 0

    def draw(self, surf):
        a = int(255 * self.life)
        r = max(1, int(self.size * self.life))
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.colour, a), (r, r), r)
        surf.blit(s, (int(self.x) - r, int(self.y) - r))


# ── Falling jewel animation ───────────────────────────────────────────────────

class FallingJewel:
    def __init__(self, jewel_type, col, target_row, start_y):
        self.jewel_type = jewel_type
        self.col = col
        self.target_row = target_row
        self.target_y = BOARD_OFFSET_Y + target_row * CELL + MARGIN
        self.y = start_y
        self.done = False

    def update(self):
        self.y += (self.target_y - self.y) * 0.25 + 2
        if self.y >= self.target_y:
            self.y = self.target_y
            self.done = True

    def draw(self, surf):
        x = BOARD_OFFSET_X + self.col * CELL + MARGIN
        rect = pygame.Rect(x, int(self.y), CELL - MARGIN * 2, CELL - MARGIN * 2)
        draw_jewel(surf, JEWEL_STYLES[self.jewel_type], rect)


# ── Swap animation ──────────────────────────────────────────────────────────

class SwapAnim:
    def __init__(self, c1, r1, c2, r2, board):
        self.c1, self.r1 = c1, r1
        self.c2, self.r2 = c2, r2
        self.t1 = board[r1][c1]
        self.t2 = board[r2][c2]
        self.progress = 0.0
        self.done = False
        self.reverse = False

    def set_reverse(self):
        self.reverse = True
        self.progress = 0.0

    def update(self):
        self.progress = min(1.0, self.progress + 0.12)
        if self.progress >= 1.0:
            self.done = True

    def draw(self, surf):
        p = ease_out(self.progress)
        if self.reverse:
            p = 1.0 - ease_out(self.progress)

        r1 = board_rect(self.c1, self.r1)
        r2 = board_rect(self.c2, self.r2)
        ax1 = lerp(r1.x, r2.x, p)
        ay1 = lerp(r1.y, r2.y, p)
        ax2 = lerp(r2.x, r1.x, p)
        ay2 = lerp(r2.y, r1.y, p)
        draw_jewel(surf, JEWEL_STYLES[self.t1], pygame.Rect(ax1, ay1, r1.w, r1.h))
        draw_jewel(surf, JEWEL_STYLES[self.t2], pygame.Rect(ax2, ay2, r2.w, r2.h))


# ── Main game ──────────────────────────────────────────────────────────

class JewelShuffle:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Jewel Shuffle ✨")
        self.clock = pygame.time.Clock()
        self.reset()

    def reset(self):
        self.board = new_board()
        while find_matches(self.board):
            self.board = new_board()
        self.score = 0
        self.moves = 20
        self.selected = None
        self.particles = []
        self.falling = []
        self.swap_anim = None
        self.matched_cells = set()
        self.flash_timer = 0
        self.state = "idle"
        self.combo = 0
        self.combo_text = []
        self.bg = pygame.Surface((WIN_W, WIN_H))
        draw_gradient(self.bg, BG_TOP, BG_BOT)

    def handle_click(self, mx, my):
        if self.state != "idle":
            return
        col, row = cell_from_pos(mx, my)
        if col is None:
            self.selected = None
            return
        if self.selected is None:
            self.selected = (col, row)
        else:
            sc, sr = self.selected
            if (sc, sr) == (col, row):
                self.selected = None
            elif are_adjacent(sc, sr, col, row):
                self.try_swap(sc, sr, col, row)
                self.selected = None
            else:
                self.selected = (col, row)

    def try_swap(self, c1, r1, c2, r2):
        self.swap_anim = SwapAnim(c1, r1, c2, r2, self.board)
        swap(self.board, c1, r1, c2, r2)
        matches = find_matches(self.board)
        if not matches:
            swap(self.board, c1, r1, c2, r2)
            self.swap_anim.set_reverse()
        else:
            self.moves -= 1
            self.combo = 0
        self.state = "swapping"

    def finish_swap(self):
        if self.swap_anim.reverse:
            self.swap_anim = None
            self.state = "idle"
        else:
            self.swap_anim = None
            self.process_matches()

    def process_matches(self):
        matches = find_matches(self.board)
        if not matches:
            self.state = "idle" if self.moves > 0 else "gameover"
            return
        self.combo += 1
        pts = len(matches) * 10 * self.combo
        self.score += pts
        self.matched_cells = matches
        self.flash_timer = 18
        self.state = "matching"
        for (r, c) in matches:
            rect = board_rect(c, r)
            style = JEWEL_STYLES[self.board[r][c]]
            for _ in range(8):
                self.particles.append(Particle(rect.centerx, rect.centery, style["fill"]))
        if self.combo > 1:
            cx = WIN_W // 2
            cy = BOARD_OFFSET_Y + BOARD_H // 2
            self.combo_text.append([f"COMBO x{self.combo}! +{pts}", cx, cy, 60])
        for (r, c) in matches:
            self.board[r][c] = -1

    def start_falling(self):
        self.falling = []

        # Snapshot which rows had jewels before gravity (per column)
        old_jewel_rows = {}
        for col in range(COLS):
            old_jewel_rows[col] = [r for r in range(ROWS) if self.board[r][col] >= 0]

        gravity(self.board)
        fill_empty(self.board)

        # Only animate jewels that actually moved or are brand-new
        for col in range(COLS):
            num_removed = ROWS - len(old_jewel_rows[col])
            if num_removed == 0:
                continue

            for new_row in range(ROWS):
                jtype = self.board[new_row][col]
                if new_row < num_removed:
                    # Brand-new jewel: fall in from above the board
                    start_y = BOARD_OFFSET_Y - CELL * (num_removed - new_row)
                    self.falling.append(FallingJewel(jtype, col, new_row, start_y))
                else:
                    # Existing jewel that shifted down
                    old_row = old_jewel_rows[col][new_row - num_removed]
                    if old_row != new_row:
                        start_y = BOARD_OFFSET_Y + old_row * CELL + MARGIN
                        self.falling.append(FallingJewel(jtype, col, new_row, start_y))

        self.state = "falling"

    def update(self):
        self.particles = [p for p in self.particles if p.update()]
        for ct in self.combo_text:
            ct[3] -= 1
            ct[2] -= 0.5
        self.combo_text = [ct for ct in self.combo_text if ct[3] > 0]

        if self.state == "swapping":
            self.swap_anim.update()
            if self.swap_anim.done:
                self.finish_swap()

        elif self.state == "matching":
            self.flash_timer -= 1
            if self.flash_timer <= 0:
                self.matched_cells = set()
                self.start_falling()

        elif self.state == "falling":
            for fj in self.falling:
                fj.update()
            if all(fj.done for fj in self.falling):
                self.falling = []
                self.process_matches()

    def draw(self):
        self.screen.blit(self.bg, (0, 0))

        title = FONT_TITLE.render("✨ Jewel Shuffle ✨", True, TITLE_COL)
        self.screen.blit(title, title.get_rect(centerx=WIN_W // 2, y=12))

        panel = pygame.Rect(BOARD_OFFSET_X, 70, BOARD_W, 54)
        draw_rounded_panel(self.screen, panel, (255, 220, 240), radius=16, alpha=180)
        score_s = FONT_SCORE.render(f"Score: {self.score}", True, TEXT_COL)
        moves_s = FONT_SCORE.render(f"Moves: {self.moves}", True, TEXT_COL)
        self.screen.blit(score_s, score_s.get_rect(midleft=(panel.x + 18, panel.centery)))
        self.screen.blit(moves_s, moves_s.get_rect(midright=(panel.right - 18, panel.centery)))

        board_bg_rect = pygame.Rect(BOARD_OFFSET_X - 6, BOARD_OFFSET_Y - 6, BOARD_W + 12, BOARD_H + 12)
        draw_rounded_panel(self.screen, board_bg_rect, (220, 190, 240), radius=20, alpha=220)
        draw_board_bg(self.screen)

        # Cells currently being animated by a FallingJewel — skip in board draw
        falling_cells = {(fj.col, fj.target_row) for fj in self.falling if not fj.done}

        # Cells being animated by swap (forward or reverse) — always skip in board draw
        swap_cells = set()
        if self.swap_anim:
            swap_cells = {(self.swap_anim.c1, self.swap_anim.r1),
                          (self.swap_anim.c2, self.swap_anim.r2)}

        for row in range(ROWS):
            for col in range(COLS):
                jtype = self.board[row][col]
                if jtype < 0:
                    continue
                if (col, row) in falling_cells or (col, row) in swap_cells:
                    continue
                rect = board_rect(col, row)
                is_sel = self.selected == (col, row)
                is_matched = (row, col) in self.matched_cells

                if is_matched:
                    flash = abs(math.sin(self.flash_timer * 0.4))
                    s = pygame.Surface(rect.size, pygame.SRCALPHA)
                    pygame.draw.rect(s, (255, 255, 255, int(flash * 200)), s.get_rect(), border_radius=10)
                    self.screen.blit(s, rect.topleft)
                    draw_jewel(self.screen, JEWEL_STYLES[jtype], rect, glow=True)
                else:
                    scale = 1.1 if is_sel else 1.0
                    draw_jewel(self.screen, JEWEL_STYLES[jtype], rect, glow=is_sel, scale=scale)

        for fj in self.falling:
            fj.draw(self.screen)

        if self.swap_anim:
            self.swap_anim.draw(self.screen)

        for p in self.particles:
            p.draw(self.screen)

        for ct in self.combo_text:
            text, x, y, timer = ct
            a = min(255, timer * 6)
            surf = FONT_SCORE.render(text, True, (255, 230, 50))
            surf.set_alpha(a)
            self.screen.blit(surf, surf.get_rect(centerx=int(x), centery=int(y)))

        if self.state == "idle":
            hint = FONT_INFO.render("Click a jewel, then click a neighbour to swap!", True, (180, 120, 200))
            self.screen.blit(hint, hint.get_rect(centerx=WIN_W // 2, y=WIN_H - 38))

        if self.state == "gameover":
            overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            overlay.fill((50, 0, 80, 170))
            self.screen.blit(overlay, (0, 0))
            go = FONT_BIG.render("Game Over!", True, (255, 200, 100))
            sc = FONT_SCORE.render(f"Final Score: {self.score}", True, (255, 255, 255))
            re = FONT_INFO.render("Click anywhere to play again  ✨", True, (255, 220, 255))
            self.screen.blit(go, go.get_rect(centerx=WIN_W // 2, centery=WIN_H // 2 - 60))
            self.screen.blit(sc, sc.get_rect(centerx=WIN_W // 2, centery=WIN_H // 2 + 10))
            self.screen.blit(re, re.get_rect(centerx=WIN_W // 2, centery=WIN_H // 2 + 56))

        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == "gameover":
                        self.reset()
                    else:
                        self.handle_click(*event.pos)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    self.reset()

            self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    JewelShuffle().run()
