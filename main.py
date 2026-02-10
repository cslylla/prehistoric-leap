"""
Prehistoric Leap — A Flappy-Bird-style game set in prehistoric times.

Guide your baby T-Rex through ancient rock formations while dodging
enemy raptors in a volcanic cave adventure!

Controls:
    SPACE  or  Left Mouse Click  →  Flap

Assets expected:
    assets/images/player.png   – baby T-Rex sprite
    assets/images/enemy.png    – raptor sprite
    assets/images/map.png      – volcanic background
    assets/images/coin.png     – gold coin collectible sprite
    assets/sounds/flap.mp3     – flap sound effect
    assets/sounds/coin.mp3     – coin collection sound
    assets/sounds/enemy.mp3    – enemy appearance sound
    assets/sounds/gameover.mp3 – game-over sting
    assets/sounds/bg.mp3       – background music loop
"""

import pygame
import sys
import json
import os
import random
import math

# ═══════════════════════════════════════════════════════════════════════
#  Initialisation
# ═══════════════════════════════════════════════════════════════════════
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Prehistoric Leap")
clock = pygame.time.Clock()

# ── Colour palette ────────────────────────────────────────────────────
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
STONE_BASE = (130, 95, 60)
STONE_DARK = (85, 60, 38)
STONE_LIGHT = (170, 130, 85)
STONE_EDGE = (65, 45, 28)
MOSS_GREEN = (70, 95, 40)
TEXT_GOLD = (255, 220, 110)
TEXT_SHADOW = (50, 35, 18)
BTN_NORMAL = (165, 105, 55)
BTN_HOVER = (195, 135, 75)
BTN_BORDER = (85, 55, 30)

# ── Paths ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, "assets", "images")
SOUNDS_DIR = os.path.join(BASE_DIR, "assets", "sounds")
LEVELS_FILE = os.path.join(BASE_DIR, "levels.json")
HIGHSCORE_FILE = os.path.join(BASE_DIR, "highscore.json")

# ── Sprite sizing ─────────────────────────────────────────────────────
PLAYER_W, PLAYER_H = 70, 70
PLAYER_X = 150  # fixed horizontal position on screen
ENEMY_W, ENEMY_H = 70, 70
COIN_W, COIN_H = 32, 32
WALL_WIDTH = 72
WALL_TIP = 22  # length of the jagged rocky tip (pixels)


# ═══════════════════════════════════════════════════════════════════════
#  Asset helpers
# ═══════════════════════════════════════════════════════════════════════

def load_scaled_image(filename, size):
    """Load a PNG from assets/images and smooth-scale it."""
    path = os.path.join(IMAGES_DIR, filename)
    img = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(img, size)


def load_levels():
    """Read level definitions from levels.json."""
    with open(LEVELS_FILE, "r") as fh:
        return json.load(fh)


def load_highscore():
    """Read the persisted high score (returns 0 on first run)."""
    try:
        with open(HIGHSCORE_FILE, "r") as fh:
            return json.load(fh).get("high_score", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0


def save_highscore(score):
    """Write the high score if it beats the existing record."""
    current = load_highscore()
    if score > current:
        with open(HIGHSCORE_FILE, "w") as fh:
            json.dump({"high_score": score}, fh, indent=2)
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════
#  Procedural rock-pillar surfaces  (prehistoric cave walls)
# ═══════════════════════════════════════════════════════════════════════

def _jagged_edge(surface, x0, x1, base_y, direction, tip_max):
    """
    Draw a row of rocky teeth on *surface*.

    direction:  1 → teeth point downward  (stalactite tip)
               -1 → teeth point upward    (stalagmite tip)
    """
    num_teeth = random.randint(3, 5)
    tooth_w = (x1 - x0) // num_teeth
    pts = [(x0, base_y)]
    for i in range(num_teeth):
        peak_x = x0 + i * tooth_w + tooth_w // 2 + random.randint(-3, 3)
        peak_y = base_y + direction * random.randint(8, tip_max)
        pts.append((peak_x, peak_y))
        if i < num_teeth - 1:
            valley_x = x0 + (i + 1) * tooth_w + random.randint(-2, 2)
            valley_y = base_y + direction * random.randint(1, 4)
            pts.append((valley_x, valley_y))
    pts.append((x1, base_y))
    pygame.draw.polygon(surface, STONE_BASE, pts)
    pygame.draw.lines(surface, STONE_EDGE, False, pts, 2)


def create_rock_surface(width, height, direction="up"):
    """
    Return a Surface containing a stone pillar with jagged tip.

    direction='down' → stalactite  (body at top, tip hangs down)
    direction='up'   → stalagmite  (body at bottom, tip points up)
    """
    tip = WALL_TIP
    surf = pygame.Surface((width, height + tip), pygame.SRCALPHA)

    # ── Decide body & tip regions ──
    if direction == "down":
        body_y0, body_h = 0, height
        _jagged_edge(surf, 0, width, height, 1, tip - 2)
    else:
        body_y0, body_h = tip, height
        _jagged_edge(surf, 0, width, tip, -1, tip - 2)

    # ── Main stone body ──
    pygame.draw.rect(surf, STONE_BASE, (0, body_y0, width, body_h))

    body_y1 = body_y0 + body_h  # bottom edge of body

    # ── Horizontal stone layers ──
    for ly in range(body_y0 + 10, body_y1 - 4, 14):
        jitter = random.randint(-1, 1)
        pygame.draw.line(surf, STONE_DARK,
                         (3, ly + jitter), (width - 3, ly + jitter), 1)

    # ── Vertical cracks ──
    for _ in range(max(1, height // 80)):
        cx = random.randint(8, width - 8)
        cy = random.randint(body_y0 + 12, body_y1 - 12)
        for _ in range(random.randint(2, 4)):
            nx = cx + random.randint(-4, 4)
            ny = cy + random.randint(4, 8)
            if body_y0 < ny < body_y1:
                pygame.draw.line(surf, STONE_EDGE, (cx, cy), (nx, ny), 1)
                cx, cy = nx, ny

    # ── Light highlight (left) & dark shadow (right) ──
    pygame.draw.line(surf, STONE_LIGHT, (2, body_y0), (2, body_y1), 2)
    pygame.draw.line(surf, STONE_EDGE,
                     (width - 2, body_y0), (width - 2, body_y1), 2)

    # ── Moss patches ──
    for _ in range(random.randint(1, 3)):
        mx = random.randint(6, width - 6)
        my = random.randint(body_y0 + 6, body_y1 - 6)
        r = random.randint(3, 6)
        moss = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(moss, (*MOSS_GREEN, 120), (r, r), r)
        surf.blit(moss, (mx - r, my - r))

    # ── Body border ──
    pygame.draw.rect(surf, STONE_EDGE, (0, body_y0, width, body_h), 2)

    return surf


# ═══════════════════════════════════════════════════════════════════════
#  Game objects
# ═══════════════════════════════════════════════════════════════════════

class Player:
    """The baby T-Rex controlled by the player."""

    def __init__(self):
        self.base_image = load_scaled_image("player.png", (PLAYER_W, PLAYER_H))
        self.x = PLAYER_X
        self.y = float(SCREEN_HEIGHT // 2 - PLAYER_H // 2)
        self.vel = 0.0
        self.alive = True
        self.bob_t = 0.0  # start-screen bobbing timer

        # Physics defaults (gravity overridden per level)
        self.gravity = 0.3
        self.flap_power = -6.0
        self.max_fall = 7.0

    # ── Collision rect (slightly inset for forgiving hits) ──
    @property
    def rect(self):
        return pygame.Rect(self.x + 8, int(self.y) + 8,
                           PLAYER_W - 16, PLAYER_H - 16)

    def flap(self):
        if self.alive:
            self.vel = self.flap_power

    def update(self, gravity=None, grace=False):
        """Apply gravity & move; *grace* suspends gravity briefly."""
        if gravity is not None:
            self.gravity = gravity

        if not grace:
            self.vel += self.gravity
            self.vel = min(self.vel, self.max_fall)
        else:
            self.vel = 0.0

        self.y += self.vel

        # Ceiling clamp
        if self.y < 0:
            self.y = 0.0
            self.vel = 0.0

        # Floor → death
        if self.y > SCREEN_HEIGHT - PLAYER_H:
            self.y = float(SCREEN_HEIGHT - PLAYER_H)
            self.alive = False

    def bob(self):
        """Gentle floating animation used on the start screen."""
        self.bob_t += 0.04
        self.y = SCREEN_HEIGHT // 2 - PLAYER_H // 2 + math.sin(self.bob_t) * 18

    def draw(self, surface):
        angle = max(-25, min(20, -self.vel * 3))
        rotated = pygame.transform.rotate(self.base_image, angle)
        r = rotated.get_rect(
            center=(self.x + PLAYER_W // 2, int(self.y) + PLAYER_H // 2))
        surface.blit(rotated, r)

    def reset(self):
        self.y = float(SCREEN_HEIGHT // 2 - PLAYER_H // 2)
        self.vel = 0.0
        self.alive = True
        self.bob_t = 0.0


class WallPair:
    """Top stalactite + bottom stalagmite with a flyable gap between them."""

    def __init__(self, x, gap_size, speed, gap_y=None):
        self.x = float(x)
        self.speed = speed
        self.gap_size = gap_size
        self.scored = False

        # Random gap centre (clamped so pillars aren't too short)
        margin = 70
        min_gy = margin + gap_size // 2
        max_gy = SCREEN_HEIGHT - margin - gap_size // 2
        self.gap_y = gap_y if gap_y else random.randint(min_gy, max_gy)

        # Pillar heights
        top_h = self.gap_y - gap_size // 2
        bot_h = SCREEN_HEIGHT - (self.gap_y + gap_size // 2)

        self.top_surf = create_rock_surface(WALL_WIDTH, max(10, top_h), "down")
        self.bot_surf = create_rock_surface(WALL_WIDTH, max(10, bot_h), "up")

        self._top_h = max(10, top_h)
        self._bot_start = self.gap_y + gap_size // 2

    # Collision rectangles (body only — tips are cosmetic)
    @property
    def top_rect(self):
        return pygame.Rect(int(self.x), 0, WALL_WIDTH, self._top_h)

    @property
    def bot_rect(self):
        return pygame.Rect(int(self.x), self._bot_start,
                           WALL_WIDTH, SCREEN_HEIGHT - self._bot_start)

    def update(self):
        self.x -= self.speed

    def draw(self, surface):
        ix = int(self.x)
        # Stalactite – top of screen
        surface.blit(self.top_surf, (ix, 0))
        # Stalagmite – offset upward by WALL_TIP so the jagged tip
        # visually connects to the gap edge
        surface.blit(self.bot_surf, (ix, self._bot_start - WALL_TIP))

    def off_screen(self):
        return self.x + WALL_WIDTH < -10

    def collides(self, player_rect):
        return (self.top_rect.colliderect(player_rect)
                or self.bot_rect.colliderect(player_rect))


class Enemy:
    """A raptor flying in from the right on a sinusoidal path."""

    def __init__(self, speed):
        img = load_scaled_image("enemy.png", (ENEMY_W, ENEMY_H))
        self.image = pygame.transform.flip(img, True, False)  # face left
        self.x = float(SCREEN_WIDTH + random.randint(20, 120))
        self.base_y = float(
            random.randint(40, SCREEN_HEIGHT - ENEMY_H - 40))
        self.y = self.base_y
        self.speed = speed
        self.wave_t = random.uniform(0, 2 * math.pi)
        self.wave_amp = random.randint(25, 55)
        self.wave_spd = random.uniform(0.025, 0.055)

    @property
    def rect(self):
        return pygame.Rect(int(self.x) + 10, int(self.y) + 10,
                           ENEMY_W - 20, ENEMY_H - 20)

    def update(self):
        self.x -= self.speed
        self.wave_t += self.wave_spd
        self.y = self.base_y + math.sin(self.wave_t) * self.wave_amp

    def draw(self, surface):
        surface.blit(self.image, (int(self.x), int(self.y)))

    def off_screen(self):
        return self.x + ENEMY_W < -10

    def collides(self, player_rect):
        return self.rect.colliderect(player_rect)


class Coin:
    """Collectible gold coin that scrolls from right to left with a gentle bob."""

    def __init__(self, x, y, speed):
        self.image = load_scaled_image("coin.png", (COIN_W, COIN_H))
        self.x = float(x)
        self.base_y = float(y)
        self.y = self.base_y
        self.speed = speed
        self.bob_t = random.uniform(0, 2 * math.pi)

    @property
    def rect(self):
        return pygame.Rect(int(self.x) + 4, int(self.y) + 4,
                           COIN_W - 8, COIN_H - 8)

    def update(self):
        self.x -= self.speed
        self.bob_t += 0.08
        self.y = self.base_y + math.sin(self.bob_t) * 6

    def draw(self, surface):
        surface.blit(self.image, (int(self.x), int(self.y)))

    def off_screen(self):
        return self.x + COIN_W < -10

    def collides(self, player_rect):
        return self.rect.colliderect(player_rect)


class Button:
    """Simple clickable button with hover highlight."""

    def __init__(self, cx, cy, w, h, text, font_size=36):
        self.rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        self.text = text
        self.font = pygame.font.Font(None, font_size)
        self.hover = False

    def update(self, mouse_pos):
        self.hover = self.rect.collidepoint(mouse_pos)

    def draw(self, surface):
        colour = BTN_HOVER if self.hover else BTN_NORMAL
        # Drop shadow
        pygame.draw.rect(surface, BTN_BORDER,
                         self.rect.move(0, 3), border_radius=10)
        # Body
        pygame.draw.rect(surface, colour, self.rect, border_radius=10)
        pygame.draw.rect(surface, BTN_BORDER, self.rect, 3, border_radius=10)
        # Label
        ts = self.font.render(self.text, True, WHITE)
        surface.blit(ts, ts.get_rect(center=self.rect.center))

    def clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


# ═══════════════════════════════════════════════════════════════════════
#  Game controller
# ═══════════════════════════════════════════════════════════════════════

class Game:
    """Manages state, updates and rendering for the entire game."""

    START = 0
    PLAYING = 1
    GAME_OVER = 2

    def __init__(self):
        # ── Background ──
        self.bg = load_scaled_image("map.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.bg_x = 0.0

        # ── Sounds (each loaded independently for robustness) ──
        self.snd_flap = self._try_load_sound("flap.mp3", 0.5)
        self.snd_enemy = self._try_load_sound("enemy.mp3", 0.35)
        self.snd_gameover = self._try_load_sound("gameover.mp3", 0.6)
        self.snd_coin = self._try_load_sound("coin.mp3", 0.6)

        try:
            pygame.mixer.music.load(os.path.join(SOUNDS_DIR, "bg.mp3"))
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

        # ── Levels & high score ──
        cfg = load_levels()
        self.levels = cfg["levels"]
        self.high_score = load_highscore()

        # ── Fonts ──
        self.font_title = pygame.font.Font(None, 68)
        self.font_score = pygame.font.Font(None, 52)
        self.font_info = pygame.font.Font(None, 30)
        self.font_small = pygame.font.Font(None, 24)

        # ── UI buttons ──
        self.btn_start = Button(
            SCREEN_WIDTH // 2, 410, 210, 55, "START", 42)
        self.btn_restart = Button(
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80, 220, 55,
            "PLAY AGAIN", 38)

        # ── Coin HUD icon (small version of coin sprite) ──
        self.coin_hud_img = load_scaled_image("coin.png", (22, 22))

        # ── Game state ──
        self.state = self.START
        self.player = Player()
        self.walls: list[WallPair] = []
        self.enemies: list[Enemy] = []
        self.coins: list[Coin] = []
        self.score = 0
        self.coins_collected = 0
        self.grace_frames = 0   # no-gravity grace at round start
        self.enemy_timer = 0
        self.level_idx = 0

    # ── Sound helper ──────────────────────────────────────────────────

    @staticmethod
    def _try_load_sound(filename, volume):
        """Load a sound effect; returns None on failure."""
        try:
            snd = pygame.mixer.Sound(os.path.join(SOUNDS_DIR, filename))
            snd.set_volume(volume)
            return snd
        except Exception:
            return None

    # ── Level look-up ─────────────────────────────────────────────────

    def _level(self):
        """Return the level dict whose score_threshold the player
        hasn't exceeded yet."""
        for i, lv in enumerate(self.levels):
            if self.score < lv.get("score_threshold", 999999):
                self.level_idx = i
                return lv
        self.level_idx = len(self.levels) - 1
        return self.levels[-1]

    # ── State transitions ─────────────────────────────────────────────

    def _start_game(self):
        self.state = self.PLAYING
        self.player.reset()
        self.walls.clear()
        self.enemies.clear()
        self.coins.clear()
        self.score = 0
        self.coins_collected = 0
        self.grace_frames = 50  # ~0.8 s of hovering before gravity kicks in
        self.enemy_timer = 0
        self.level_idx = 0

    def _game_over(self):
        self.state = self.GAME_OVER
        self.player.alive = False
        if self.snd_gameover:
            self.snd_gameover.play()
        if save_highscore(self.score):
            self.high_score = self.score

    # ── Event handling ────────────────────────────────────────────────

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self._quit()

            # --- Start screen ---
            if self.state == self.START:
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self.btn_start.clicked(ev.pos):
                        self._start_game()

            # --- Playing ---
            elif self.state == self.PLAYING:
                do_flap = False
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
                    do_flap = True
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    do_flap = True
                if do_flap:
                    self.player.flap()
                    if self.snd_flap:
                        self.snd_flap.play()
                    # First flap cancels the grace hover
                    if self.grace_frames > 0:
                        self.grace_frames = 0

            # --- Game over ---
            elif self.state == self.GAME_OVER:
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self.btn_restart.clicked(ev.pos):
                        self._start_game()
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
                    self._start_game()

    # ── Update logic ──────────────────────────────────────────────────

    def update(self):
        mouse_pos = pygame.mouse.get_pos()

        # ····· START SCREEN ·····
        if self.state == self.START:
            self.btn_start.update(mouse_pos)
            self.player.bob()
            self.bg_x -= 0.3
            if self.bg_x <= -SCREEN_WIDTH:
                self.bg_x += SCREEN_WIDTH

        # ····· PLAYING ·····
        elif self.state == self.PLAYING:
            lv = self._level()
            grav = lv.get("gravity", 0.3)

            # Grace period (bird hovers at start)
            grace = self.grace_frames > 0
            if grace:
                self.grace_frames -= 1

            self.player.update(gravity=grav, grace=grace)
            if not self.player.alive:
                self._game_over()
                return

            # Background parallax
            self.bg_x -= lv.get("wall_speed", 2.0) * 0.25
            if self.bg_x <= -SCREEN_WIDTH:
                self.bg_x += SCREEN_WIDTH

            # ── Wall spawning ──
            wall_speed = lv.get("wall_speed", 2.0)
            gap_size = max(lv.get("gap_size", 200), PLAYER_H + 80)
            wall_spacing = lv.get("wall_spacing", 350)

            wall_just_spawned = False
            if ((not self.walls)
                    or self.walls[-1].x < SCREEN_WIDTH - wall_spacing):
                self.walls.append(
                    WallPair(SCREEN_WIDTH + 40, gap_size, wall_speed))
                wall_just_spawned = True

            # ── Wall update ──
            for w in self.walls[:]:
                w.update()
                # Score when the player passes a wall
                if not w.scored and w.x + WALL_WIDTH < self.player.x:
                    w.scored = True
                    self.score += 1
                # Collision
                if w.collides(self.player.rect):
                    self._game_over()
                    return
                # Clean-up
                if w.off_screen():
                    self.walls.remove(w)

            # ── Enemy spawning ──
            enemy_speed = lv.get("enemy_speed", 1.5)
            enemy_freq = lv.get("enemy_spawn_frames", 500)
            self.enemy_timer += 1
            if self.enemy_timer >= enemy_freq:
                self.enemies.append(Enemy(enemy_speed))
                self.enemy_timer = 0
                if self.snd_enemy:
                    self.snd_enemy.play()

            # ── Enemy update ──
            for e in self.enemies[:]:
                e.update()
                if e.collides(self.player.rect):
                    self._game_over()
                    return
                if e.off_screen():
                    self.enemies.remove(e)

            # ── Coin spawning (triggered alongside wall spawn) ──
            if wall_just_spawned:
                coin_chance = lv.get("coin_spawn_chance", 0.5)
                max_coins = lv.get("max_coins_on_screen", 3)
                if (random.random() < coin_chance
                        and len(self.coins) < max_coins):
                    speed_mult = lv.get("coin_speed_multiplier", 1.0)
                    min_gap_px = lv.get("coin_min_gap_from_walls_px", 100)
                    y_pad = lv.get("coin_y_padding_px", 50)
                    latest = self.walls[-1]
                    # Centre coin in the open space between walls
                    space = wall_spacing + 40 - WALL_WIDTH
                    coin_x = (latest.x + WALL_WIDTH
                              + space // 2 - COIN_W // 2
                              + random.randint(-20, 20))
                    coin_x = max(coin_x,
                                 latest.x + WALL_WIDTH + min_gap_px)
                    # Y near the flyable gap with some variation
                    coin_y = (latest.gap_y
                              + random.randint(-latest.gap_size // 3,
                                               latest.gap_size // 3)
                              - COIN_H // 2)
                    coin_y = max(y_pad,
                                 min(SCREEN_HEIGHT - y_pad - COIN_H,
                                     coin_y))
                    self.coins.append(
                        Coin(coin_x, coin_y,
                             wall_speed * speed_mult))

            # ── Coin update ──
            coin_value = lv.get("coin_value", 1)
            for c in self.coins[:]:
                c.update()
                if c.collides(self.player.rect):
                    self.coins_collected += coin_value
                    self.coins.remove(c)
                    if self.snd_coin:
                        self.snd_coin.play()
                elif c.off_screen():
                    self.coins.remove(c)

        # ····· GAME OVER ·····
        elif self.state == self.GAME_OVER:
            self.btn_restart.update(mouse_pos)
            self.bg_x -= 0.15
            if self.bg_x <= -SCREEN_WIDTH:
                self.bg_x += SCREEN_WIDTH

    # ── Drawing ───────────────────────────────────────────────────────

    def draw(self):
        # Scrolling background (two copies side by side)
        bx = int(self.bg_x)
        screen.blit(self.bg, (bx, 0))
        screen.blit(self.bg, (bx + SCREEN_WIDTH, 0))

        if self.state == self.START:
            self._draw_start()
        elif self.state == self.PLAYING:
            self._draw_playing()
        elif self.state == self.GAME_OVER:
            self._draw_gameover()

        pygame.display.flip()

    # -- helper: dark overlay
    def _overlay(self, alpha=130):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, alpha))
        screen.blit(ov, (0, 0))

    # -- helper: centred text
    def _text(self, text, font, colour, y, shadow=False):
        cx = SCREEN_WIDTH // 2
        if shadow:
            s = font.render(text, True, TEXT_SHADOW)
            screen.blit(s, s.get_rect(center=(cx + 2, y + 2)))
        t = font.render(text, True, colour)
        screen.blit(t, t.get_rect(center=(cx, y)))

    # -- Start screen
    def _draw_start(self):
        self._overlay(100)

        self._text("PREHISTORIC LEAP", self.font_title,
                    TEXT_GOLD, 120, shadow=True)
        self._text("Guide your baby dino through ancient caves!",
                    self.font_info, (225, 210, 175), 185)

        self.player.draw(screen)

        self._text("SPACE  or  LEFT CLICK  to flap",
                    self.font_small, (210, 200, 165), 345)

        self.btn_start.draw(screen)

        if self.high_score > 0:
            self._text(f"High Score: {self.high_score}",
                       self.font_info, TEXT_GOLD, SCREEN_HEIGHT - 55)

        self._text(f"{len(self.levels)} levels available",
                   self.font_small, (185, 175, 150), SCREEN_HEIGHT - 28)

    # -- Active gameplay
    def _draw_playing(self):
        for w in self.walls:
            w.draw(screen)
        for c in self.coins:
            c.draw(screen)
        for e in self.enemies:
            e.draw(screen)
        self.player.draw(screen)

        # HUD – score (centre)
        self._text(str(self.score), self.font_score, WHITE, 40, shadow=True)
        # HUD – level name
        lv_name = self.levels[self.level_idx].get(
            "name", f"Level {self.level_idx + 1}")
        self._text(lv_name, self.font_small, TEXT_GOLD, 72)
        # HUD – coin counter (top-left)
        screen.blit(self.coin_hud_img, (14, 16))
        coin_txt = self.font_info.render(
            f"x {self.coins_collected}", True, TEXT_GOLD)
        screen.blit(coin_txt, (40, 14))

    # -- Game-over overlay
    def _draw_gameover(self):
        # Keep the last frame visible behind the overlay
        for w in self.walls:
            w.draw(screen)
        for c in self.coins:
            c.draw(screen)
        for e in self.enemies:
            e.draw(screen)
        self.player.draw(screen)

        self._overlay(160)

        self._text("GAME OVER", self.font_title,
                    (225, 65, 45), 155, shadow=True)
        self._text(f"Score: {self.score}", self.font_score,
                    WHITE, SCREEN_HEIGHT // 2 - 50, shadow=True)
        self._text(f"Coins Collected: {self.coins_collected}",
                    self.font_info, TEXT_GOLD, SCREEN_HEIGHT // 2 - 12)

        if self.score >= self.high_score and self.score > 0:
            self._text("NEW HIGH SCORE!", self.font_info,
                        TEXT_GOLD, SCREEN_HEIGHT // 2 + 18)
        else:
            self._text(f"High Score: {self.high_score}", self.font_info,
                        TEXT_GOLD, SCREEN_HEIGHT // 2 + 18)

        self.btn_restart.draw(screen)

        self._text("Press SPACE or click PLAY AGAIN",
                    self.font_small, (185, 175, 150),
                    SCREEN_HEIGHT // 2 + 130)

    # ── Main loop ─────────────────────────────────────────────────────

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            clock.tick(FPS)

    def _quit(self):
        save_highscore(max(self.score, self.high_score))
        pygame.mixer.music.stop()
        pygame.quit()
        sys.exit()


# ═══════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    game = Game()
    game.run()
