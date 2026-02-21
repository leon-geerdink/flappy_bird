import pygame
import sys
import random
import math
import array
from dataclasses import dataclass

# --- Constants ---
WIDTH, HEIGHT = 600, 600
FPS = 60
GROUND_HEIGHT = 60

# Colors
SKY_BLUE = (135, 206, 235)
GROUND_COLOR = (210, 180, 140)
GROUND_GREEN = (80, 170, 50)
GROUND_LINE = (190, 160, 120)
GROUND_LINE_GREEN = (60, 140, 35)
BIRD_YELLOW = (255, 210, 50)
BIRD_ORANGE = (230, 140, 30)
PIPE_GREEN = (200, 40, 40)
PIPE_CAP_GREEN = (160, 30, 30)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Bird
BIRD_X = 80
BIRD_RADIUS = 17
JUMP_VELOCITY = -6.5

# Pipes
PIPE_WIDTH = 52
PIPE_CAP_HEIGHT = 20
PIPE_CAP_OVERHANG = 4
PIPE_MIN_Y = 80
PIPE_MAX_Y = HEIGHT - GROUND_HEIGHT - 80
MIN_PIPE_DISTANCE = 200

POINTS_PER_LEVEL = 3
LEVEL_BANNER_DURATION = 120  # frames to show "NEXT LEVEL" banner
CONFETTI_COLORS = [(255, 50, 50), (50, 255, 50), (50, 100, 255), (255, 255, 50),
                   (255, 100, 200), (50, 255, 255), (255, 150, 30)]

# Animation speeds
WING_FLAP_SPEED = 0.3
HAIR_SWAY_SPEED = 0.15
LEG_WALK_SPEED = 0.25
EAR_SWAY_SPEED = 0.1
TAIL_SWAY_SPEED = 0.15
WIN_PULSE_SPEED = 0.1

# Llama
LLAMA_SCALE = 1.8
LLAMA_BODY = (210, 190, 160)
LLAMA_DARK = (170, 150, 120)

# Flowers
FLOWER_COLORS = [(255, 80, 80), (255, 160, 200), (255, 255, 100), (200, 130, 255), (255, 180, 50)]
STEM_GREEN = (50, 150, 30)

WIN_SCORE = 30
GOLD = (255, 215, 0)


# --- Dataclasses ---

@dataclass
class LevelConfig:
    num: int
    name: str
    gravity: float
    max_fall: float
    gap: int
    speed: float
    spawn: int


@dataclass
class GameState:
    bird_y: float
    bird_vel: float
    pipes: list
    score: int
    frame_count: int
    game_active: bool
    won: bool
    flowers: list
    clouds: list
    level: LevelConfig
    level_banner_timer: int
    confetti: list


# --- Audio ---

def create_burp_sound():
    """Generate a burp sound programmatically."""
    sample_rate = 44100
    duration = 0.5
    n_samples = int(sample_rate * duration)
    samples = array.array('h')  # signed short

    for i in range(n_samples):
        t = i / sample_rate
        progress = i / n_samples

        # Envelope: quick attack, hold, then fade
        if progress < 0.03:
            envelope = progress / 0.03
        elif progress < 0.3:
            envelope = 1.0
        else:
            envelope = 1.0 - (progress - 0.3) / 0.7

        # Low rumbling base frequency that drops over time
        freq = 120 - 60 * progress

        # Gurgling: modulate with a slow wobble
        wobble = math.sin(2 * math.pi * 8 * t) * 20
        freq += wobble

        # Mix of low harmonics for a throaty rumble
        val = 0.0
        val += math.sin(2 * math.pi * freq * t) * 0.5
        val += math.sin(2 * math.pi * freq * 1.5 * t) * 0.3
        val += math.sin(2 * math.pi * freq * 2.3 * t) * 0.15

        # Add noise/grit for texture
        val += (random.random() * 2 - 1) * 0.15 * envelope

        # Bubbling pulses
        bubble = math.sin(2 * math.pi * 15 * t) * 0.3
        val *= 1.0 + bubble * max(0, 1 - progress * 2)

        sample = int(val * envelope * 10000)
        sample = max(-32767, min(32767, sample))
        samples.append(sample)

    sound = pygame.mixer.Sound(buffer=samples)
    sound.set_volume(0.35)
    return sound


# --- Level ---

def get_level(score):
    """Return the level config for the given score. New level every 3 points."""
    lvl_num = score // POINTS_PER_LEVEL  # 0, 1, 2, ... 9
    t = min(lvl_num / 9.0, 1.0)  # progress 0.0 to 1.0 across 10 levels
    return LevelConfig(
        num=lvl_num + 1,
        name=f"Level {lvl_num + 1}",
        gravity=0.25 + 0.17 * t,
        max_fall=7 + 3 * t,
        gap=int(230 - 65 * t),
        speed=2.0 + 1.8 * t,
        spawn=int(130 - 50 * t),
    )


# --- Flowers ---

def make_flower(x):
    return {"x": float(x), "color": random.choice(FLOWER_COLORS),
            "petals": random.randint(4, 7), "stem_h": random.randint(12, 22)}


def generate_flowers():
    return [make_flower(random.randint(10, WIDTH + 100)) for _ in range(15)]


def update_flowers(flowers, speed):
    for f in flowers:
        f["x"] -= speed
    flowers[:] = [f for f in flowers if f["x"] > -20]
    # Spawn new flowers on the right
    if not flowers or max(f["x"] for f in flowers) < WIDTH - 20:
        flowers.append(make_flower(WIDTH + random.randint(10, 40)))


# --- Clouds ---

def lerp_color(c1, c2, t):
    """Linearly interpolate between two RGB colors. t=0 gives c1, t=1 gives c2."""
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def make_cloud(x=None):
    if x is None:
        x = WIDTH + random.randint(20, 150)
    return {
        "x": float(x),
        "y": float(random.randint(30, 180)),
        "w": random.randint(60, 120),
        "h": random.randint(25, 45),
        "speed": random.uniform(0.3, 0.8),
    }


def update_clouds(clouds):
    for c in clouds:
        c["x"] -= c["speed"]
    clouds[:] = [c for c in clouds if c["x"] + c["w"] > -20]
    if len(clouds) < 5 and (not clouds or max(c["x"] for c in clouds) < WIDTH - 100):
        clouds.append(make_cloud())


def draw_clouds(screen, clouds, alpha):
    """Draw clouds with given opacity (0-255)."""
    if alpha <= 0:
        return
    for c in clouds:
        cx, cy, w, h = int(c["x"]), int(c["y"]), c["w"], c["h"]
        surf = pygame.Surface((w + 20, h + 20), pygame.SRCALPHA)
        color = (255, 255, 255, int(alpha))
        shadow = (200, 200, 210, int(alpha * 0.3))
        # Cloud = overlapping ellipses
        pygame.draw.ellipse(surf, shadow, (4, 8, w, h))
        pygame.draw.ellipse(surf, color, (0, 0, w, h))
        pygame.draw.ellipse(surf, color, (w // 4, -h // 3, w // 2, h))
        pygame.draw.ellipse(surf, color, (w // 6, h // 6, w * 2 // 3, h * 2 // 3))
        screen.blit(surf, (cx, cy))


# --- Drawing ---

def draw_background(screen, flowers, score, clouds):
    screen.fill(SKY_BLUE)

    # Ground color: gradually turn green between score 10-20
    ground_t = max(0.0, min(1.0, (score - 10) / 10.0))
    ground_col = lerp_color(GROUND_COLOR, GROUND_GREEN, ground_t)
    ground_line_col = lerp_color(GROUND_LINE, GROUND_LINE_GREEN, ground_t)

    pygame.draw.rect(screen, ground_col, (0, HEIGHT - GROUND_HEIGHT, WIDTH, GROUND_HEIGHT))
    pygame.draw.line(screen, ground_line_col, (0, HEIGHT - GROUND_HEIGHT), (WIDTH, HEIGHT - GROUND_HEIGHT), 2)

    # Clouds: fade in between score 20-25
    cloud_alpha = max(0.0, min(1.0, (score - 20) / 5.0)) * 200
    draw_clouds(screen, clouds, cloud_alpha)

    fy = HEIGHT - GROUND_HEIGHT
    for flower in flowers:
        fx = int(flower["x"])
        color = flower["color"]
        size = flower["petals"]
        stem_h = flower["stem_h"]
        # Stem
        pygame.draw.line(screen, STEM_GREEN, (fx, fy), (fx, fy - stem_h), 2)
        # Petals
        center_y = fy - stem_h
        for angle in range(0, 360, 72):
            px = fx + int(math.cos(math.radians(angle)) * size)
            py = center_y + int(math.sin(math.radians(angle)) * size)
            pygame.draw.circle(screen, color, (px, py), size - 1)
        # Center
        pygame.draw.circle(screen, (255, 220, 50), (fx, center_y), size - 2)


def draw_bird(screen, bird_y, bird_vel, frame_count):
    by = int(bird_y)

    # Wings (drawn behind body)
    flap = math.sin(frame_count * WING_FLAP_SPEED) * 14
    f = int(flap)

    wing_dark = (200, 160, 30)
    wing_mid = (230, 185, 40)
    wing_light = BIRD_YELLOW

    # Back wing (further from viewer, slightly smaller)
    bw_points = [
        (BIRD_X - 3, by - 2),
        (BIRD_X - 12, by - 18 + f),
        (BIRD_X - 24, by - 14 + f),
        (BIRD_X - 20, by - 4 + f // 2),
        (BIRD_X - 10, by + 4),
    ]
    pygame.draw.polygon(screen, wing_dark, bw_points)

    # Body
    pygame.draw.circle(screen, BIRD_YELLOW, (BIRD_X, by), BIRD_RADIUS)

    # Front wing (closer to viewer, larger, layered feathers)
    # Outer feather layer
    fw_outer = [
        (BIRD_X - 2, by + 1),
        (BIRD_X - 8, by - 10 - f),
        (BIRD_X - 22, by - 16 - f),
        (BIRD_X - 30, by - 10 - f),
        (BIRD_X - 22, by + 2 - f // 3),
        (BIRD_X - 10, by + 8),
    ]
    pygame.draw.polygon(screen, wing_mid, fw_outer)
    # Inner feather layer
    fw_inner = [
        (BIRD_X - 2, by + 2),
        (BIRD_X - 6, by - 4 - f),
        (BIRD_X - 16, by - 10 - f),
        (BIRD_X - 20, by - 4 - f),
        (BIRD_X - 14, by + 4 - f // 4),
        (BIRD_X - 6, by + 8),
    ]
    pygame.draw.polygon(screen, wing_light, fw_inner)

    # Hair (orange tufts on top)
    hair_color = (240, 120, 20)
    for i, (dx, length, curve) in enumerate([(-6, 14, -3), (-1, 16, 1), (5, 13, 4)]):
        sway = int(math.sin(frame_count * HAIR_SWAY_SPEED + i) * 2)
        base_x = BIRD_X + dx
        base_y = by - BIRD_RADIUS + 3
        tip_x = base_x + curve + sway
        tip_y = base_y - length
        mid_x = (base_x + tip_x) // 2 + curve // 2
        mid_y = (base_y + tip_y) // 2
        pygame.draw.line(screen, hair_color, (base_x, base_y), (mid_x, mid_y), 3)
        pygame.draw.line(screen, hair_color, (mid_x, mid_y), (tip_x, tip_y), 2)

    # Eye
    eye_x = BIRD_X + 7
    eye_y = by - 4
    pygame.draw.circle(screen, WHITE, (eye_x, eye_y), 6)
    pygame.draw.circle(screen, BLACK, (eye_x + 2, eye_y), 3)

    # Glasses (side-view: one visible lens + arm)
    glass_color = (50, 50, 50)
    pygame.draw.circle(screen, glass_color, (eye_x, eye_y), 8, 2)
    # Arm going back over the head
    pygame.draw.line(screen, glass_color, (eye_x - 7, eye_y - 3), (BIRD_X - 12, eye_y - 2), 2)
    pygame.draw.line(screen, glass_color, (BIRD_X - 12, eye_y - 2), (BIRD_X - 16, eye_y + 2), 2)

    # Beak
    beak_points = [
        (BIRD_X + BIRD_RADIUS, by),
        (BIRD_X + BIRD_RADIUS + 10, by + 3),
        (BIRD_X + BIRD_RADIUS, by + 6),
    ]
    pygame.draw.polygon(screen, BIRD_ORANGE, beak_points)


def spawn_confetti(confetti):
    """Spawn confetti particles from the llama's mouth (burp!)."""
    s = LLAMA_SCALE
    lx = BIRD_X
    ground_y = HEIGHT - GROUND_HEIGHT
    head_x = lx + int(21 * s)
    head_y = ground_y - int(66 * s)
    # Mouth position
    cx = head_x + int(14 * s)
    cy = head_y + int(8 * s)
    for _ in range(40):
        angle = random.uniform(-math.pi * 0.6, math.pi * 0.15)  # spray forward and upward
        speed = random.uniform(3, 9)
        confetti.append({
            "x": float(cx),
            "y": float(cy),
            "vx": math.cos(angle) * speed + random.uniform(-1, 1),
            "vy": math.sin(angle) * speed,
            "color": random.choice(CONFETTI_COLORS),
            "size": random.randint(3, 7),
            "life": random.randint(60, 120),
            "rot": random.uniform(0, 360),
            "rot_speed": random.uniform(-10, 10),
        })


def update_confetti(confetti):
    for p in confetti:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vy"] += 0.15  # gravity on confetti
        p["life"] -= 1
        p["rot"] += p["rot_speed"]
    confetti[:] = [p for p in confetti if p["life"] > 0 and p["y"] < HEIGHT]


def draw_confetti(screen, confetti):
    for p in confetti:
        alpha = min(255, p["life"] * 4)
        size = p["size"]
        # Draw as small rotating rectangles
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        color = (*p["color"], alpha)
        pygame.draw.rect(surf, color, (0, 0, size, size))
        rotated = pygame.transform.rotate(surf, p["rot"])
        rect = rotated.get_rect(center=(int(p["x"]), int(p["y"])))
        screen.blit(rotated, rect)


def draw_llama(screen, frame_count):
    s = LLAMA_SCALE
    lx = BIRD_X
    ground_y = HEIGHT - GROUND_HEIGHT

    # Leg animation
    leg_offset = int(math.sin(frame_count * LEG_WALK_SPEED) * 8 * s)

    # Legs (4 legs, animated in pairs)
    leg_color = LLAMA_DARK
    lw = max(2, int(3 * s))
    # Back legs
    pygame.draw.line(screen, leg_color, (lx - int(10 * s), ground_y - int(18 * s)), (lx - int(14 * s) - leg_offset, ground_y), lw)
    pygame.draw.line(screen, leg_color, (lx - int(4 * s), ground_y - int(18 * s)), (lx - int(0 * s) + leg_offset, ground_y), lw)
    # Front legs
    pygame.draw.line(screen, leg_color, (lx + int(10 * s), ground_y - int(20 * s)), (lx + int(6 * s) + leg_offset, ground_y), lw)
    pygame.draw.line(screen, leg_color, (lx + int(16 * s), ground_y - int(20 * s)), (lx + int(20 * s) - leg_offset, ground_y), lw)

    # Body (oval-ish)
    body_rect = pygame.Rect(lx - int(16 * s), ground_y - int(34 * s), int(36 * s), int(18 * s))
    pygame.draw.ellipse(screen, LLAMA_BODY, body_rect)

    # Neck
    neck_points = [
        (lx + int(14 * s), ground_y - int(30 * s)),
        (lx + int(18 * s), ground_y - int(60 * s)),
        (lx + int(24 * s), ground_y - int(58 * s)),
        (lx + int(20 * s), ground_y - int(28 * s)),
    ]
    pygame.draw.polygon(screen, LLAMA_BODY, neck_points)

    # Head (longer snout shape - two overlapping ellipses)
    head_x = lx + int(21 * s)
    head_y = ground_y - int(66 * s)
    # Back of head (rounder)
    pygame.draw.ellipse(screen, LLAMA_BODY, (head_x - int(6 * s), head_y - int(2 * s), int(14 * s), int(14 * s)))
    # Snout (elongated, sticks forward)
    pygame.draw.ellipse(screen, LLAMA_BODY, (head_x + int(2 * s), head_y + int(2 * s), int(14 * s), int(10 * s)))

    # Ears (taller, more pointy with inner color)
    ear_sway = int(math.sin(frame_count * EAR_SWAY_SPEED) * 1)
    # Left ear
    ear1 = [(head_x - int(1 * s), head_y - int(1 * s)),
            (head_x - int(4 * s), head_y - int(14 * s) + ear_sway),
            (head_x + int(3 * s), head_y - int(2 * s))]
    pygame.draw.polygon(screen, LLAMA_BODY, ear1)
    pygame.draw.polygon(screen, (230, 180, 180), [
        (head_x - int(1 * s), head_y - int(2 * s)),
        (head_x - int(3 * s), head_y - int(11 * s) + ear_sway),
        (head_x + int(1 * s), head_y - int(2 * s))])
    # Right ear
    ear2 = [(head_x + int(4 * s), head_y - int(1 * s)),
            (head_x + int(6 * s), head_y - int(13 * s) + ear_sway),
            (head_x + int(9 * s), head_y - int(1 * s))]
    pygame.draw.polygon(screen, LLAMA_BODY, ear2)
    pygame.draw.polygon(screen, (230, 180, 180), [
        (head_x + int(5 * s), head_y - int(2 * s)),
        (head_x + int(6 * s), head_y - int(10 * s) + ear_sway),
        (head_x + int(8 * s), head_y - int(2 * s))])

    # Eye (white with pupil)
    eye_cx = head_x + int(4 * s)
    eye_cy = head_y + int(4 * s)
    pygame.draw.circle(screen, WHITE, (eye_cx, eye_cy), int(3 * s))
    pygame.draw.circle(screen, BLACK, (eye_cx + int(1 * s), eye_cy), int(1.5 * s))

    # Nostrils
    nose_y = head_y + int(6 * s)
    pygame.draw.circle(screen, LLAMA_DARK, (head_x + int(13 * s), nose_y), int(1.2 * s))
    pygame.draw.circle(screen, LLAMA_DARK, (head_x + int(13 * s), nose_y + int(3 * s)), int(1.2 * s))

    # Mouth
    pygame.draw.line(screen, LLAMA_DARK,
                     (head_x + int(10 * s), head_y + int(9 * s)),
                     (head_x + int(14 * s), head_y + int(8 * s)), 2)

    # Tail (little tuft)
    tail_sway = int(math.sin(frame_count * TAIL_SWAY_SPEED) * 4 * s)
    pygame.draw.line(screen, LLAMA_DARK, (lx - int(16 * s), ground_y - int(30 * s)), (lx - int(24 * s) + tail_sway, ground_y - int(38 * s)), lw)
    pygame.draw.circle(screen, LLAMA_BODY, (lx - int(24 * s) + tail_sway, ground_y - int(40 * s)), int(4 * s))


# --- Pipes ---

def create_pipe():
    gap_y = random.randint(PIPE_MIN_Y, PIPE_MAX_Y)
    return {"x": float(WIDTH), "gap_y": float(gap_y), "scored": False}


def update_pipes(pipes, frame_count, speed, spawn_interval):
    for pipe in pipes:
        pipe["x"] -= speed

    if frame_count % spawn_interval == 0:
        # Only spawn if the last pipe is far enough away
        if not pipes or (WIDTH - pipes[-1]["x"]) >= MIN_PIPE_DISTANCE:
            pipes.append(create_pipe())

    pipes[:] = [p for p in pipes if p["x"] + PIPE_WIDTH > -10]


def draw_pipes(screen, pipes, gap):
    for pipe in pipes:
        x = int(pipe["x"])
        gap_y = int(pipe["gap_y"])
        top_of_gap = gap_y - gap // 2
        bottom_of_gap = gap_y + gap // 2

        # Top pipe body
        pygame.draw.rect(screen, PIPE_GREEN, (x, 0, PIPE_WIDTH, top_of_gap - PIPE_CAP_HEIGHT))
        # Top pipe cap
        pygame.draw.rect(
            screen, PIPE_CAP_GREEN,
            (x - PIPE_CAP_OVERHANG, top_of_gap - PIPE_CAP_HEIGHT,
             PIPE_WIDTH + PIPE_CAP_OVERHANG * 2, PIPE_CAP_HEIGHT)
        )

        # Bottom pipe body
        bottom_pipe_top = bottom_of_gap + PIPE_CAP_HEIGHT
        pygame.draw.rect(screen, PIPE_GREEN, (x, bottom_pipe_top, PIPE_WIDTH, HEIGHT - GROUND_HEIGHT - bottom_pipe_top))
        # Bottom pipe cap
        pygame.draw.rect(
            screen, PIPE_CAP_GREEN,
            (x - PIPE_CAP_OVERHANG, bottom_of_gap,
             PIPE_WIDTH + PIPE_CAP_OVERHANG * 2, PIPE_CAP_HEIGHT)
        )


# --- Collision ---

def circle_rect_collision(cx, cy, radius, rx, ry, rw, rh):
    closest_x = max(rx, min(cx, rx + rw))
    closest_y = max(ry, min(cy, ry + rh))
    dx = cx - closest_x
    dy = cy - closest_y
    return (dx * dx + dy * dy) < (radius * radius)


def check_collision(bird_y, pipes, gap):
    # Ceiling
    if bird_y - BIRD_RADIUS <= 0:
        return True
    # Ground
    if bird_y + BIRD_RADIUS >= HEIGHT - GROUND_HEIGHT:
        return True

    for pipe in pipes:
        x = pipe["x"]
        gap_y = pipe["gap_y"]
        top_of_gap = gap_y - gap // 2
        bottom_of_gap = gap_y + gap // 2

        # Top pipe rect (body + cap)
        top_rect = (x - PIPE_CAP_OVERHANG, 0,
                    PIPE_WIDTH + PIPE_CAP_OVERHANG * 2, top_of_gap)
        # Bottom pipe rect (cap + body)
        bottom_rect = (x - PIPE_CAP_OVERHANG, bottom_of_gap,
                       PIPE_WIDTH + PIPE_CAP_OVERHANG * 2, HEIGHT - GROUND_HEIGHT - bottom_of_gap)

        if circle_rect_collision(BIRD_X, bird_y, BIRD_RADIUS, *top_rect):
            return True
        if circle_rect_collision(BIRD_X, bird_y, BIRD_RADIUS, *bottom_rect):
            return True

    return False


# --- Score ---

def update_score(pipes, score):
    for pipe in pipes:
        if not pipe["scored"] and pipe["x"] + PIPE_WIDTH < BIRD_X:
            pipe["scored"] = True
            score += 1
    return score


def draw_outlined_text(screen, text, font, x, y, color, outline_color, offset=2):
    """Draw text with an outline by rendering the outline color offset in 4 directions."""
    outline = font.render(text, True, outline_color)
    main = font.render(text, True, color)
    for dx, dy in [(-offset, 0), (offset, 0), (0, -offset), (0, offset)]:
        screen.blit(outline, (x + dx, y + dy))
    screen.blit(main, (x, y))


def draw_score(screen, score, level, font, small_font):
    text = str(score)
    rendered = font.render(text, True, WHITE)
    tx = WIDTH // 2 - rendered.get_width() // 2
    draw_outlined_text(screen, text, font, tx, 48, WHITE, BLACK)

    lvl_text = level.name
    lvl_rendered = small_font.render(lvl_text, True, WHITE)
    lx = WIDTH // 2 - lvl_rendered.get_width() // 2
    draw_outlined_text(screen, lvl_text, small_font, lx, 15, WHITE, BLACK, offset=1)


# --- Game Over ---

def draw_game_over(screen, score, font, small_font):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (0, 0))

    go_text = font.render("GAME OVER", True, WHITE)
    screen.blit(go_text, (WIDTH // 2 - go_text.get_width() // 2, HEIGHT // 2 - 80))

    score_text = small_font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2 - 20))

    restart_text = small_font.render("Press SPACE to restart", True, WHITE)
    screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 30))


# --- Win ---

def draw_ice_cream(screen, x, y, scale=1.0):
    """Draw an ice cream cone at (x, y) where y is the top of the scoops."""
    s = scale
    # Cone
    cone_color = (210, 170, 90)
    cone_dark = (180, 140, 60)
    cone_top = int(y + 12 * s)
    cone_bottom = int(y + 40 * s)
    cone_w = int(12 * s)
    pygame.draw.polygon(screen, cone_color, [
        (int(x - cone_w), cone_top),
        (int(x + cone_w), cone_top),
        (int(x), cone_bottom),
    ])
    # Cone cross pattern
    for i in range(3):
        ly = int(cone_top + (cone_bottom - cone_top) * (i + 1) / 4)
        hw = int(cone_w * (1 - (i + 1) / 4))
        pygame.draw.line(screen, cone_dark, (x - hw, ly), (x + hw, ly), 1)

    # Scoops
    scoop_colors = [(255, 105, 180), (255, 255, 150), (160, 230, 160)]
    for i, color in enumerate(scoop_colors):
        sy = int(y + (2 - i) * 9 * s - 6 * s)
        r = int(11 * s)
        pygame.draw.circle(screen, color, (int(x), sy), r)
        # Highlight
        pygame.draw.circle(screen, (255, 255, 255), (int(x - 3 * s), int(sy - 3 * s)), int(3 * s))


def draw_win(screen, score, font, small_font, frame_count, bird_y):
    # Draw ice cream for the bird (in its beak, to the right)
    bird_ice_x = BIRD_X + BIRD_RADIUS + 14
    bird_ice_y = int(bird_y) - 10
    draw_ice_cream(screen, bird_ice_x, bird_ice_y, scale=0.8)

    # Draw ice cream for the llama (held near its mouth)
    s = LLAMA_SCALE
    lx = BIRD_X
    ground_y = HEIGHT - GROUND_HEIGHT
    head_x = lx + int(21 * s)
    head_y = ground_y - int(66 * s)
    llama_ice_x = head_x + int(16 * s) + 10
    llama_ice_y = head_y + int(4 * s) - 15
    draw_ice_cream(screen, llama_ice_x, llama_ice_y, scale=1.2)

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (0, 0))

    # Pulsating gold title
    pulse = 1.0 + 0.1 * math.sin(frame_count * WIN_PULSE_SPEED)
    win_font = pygame.font.SysFont(None, int(64 * pulse))
    win_text = win_font.render("YOU WIN!", True, GOLD)
    screen.blit(win_text, (WIDTH // 2 - win_text.get_width() // 2, HEIGHT // 2 - 90))

    score_text = small_font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2 - 20))

    congrats_text = small_font.render("Congratulations!", True, GOLD)
    screen.blit(congrats_text, (WIDTH // 2 - congrats_text.get_width() // 2, HEIGHT // 2 + 20))

    restart_text = small_font.render("Press ENTER for new game", True, WHITE)
    screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 60))


# --- Game State ---

def reset_game():
    return GameState(
        bird_y=HEIGHT / 2.5,
        bird_vel=0.0,
        pipes=[],
        score=0,
        frame_count=0,
        game_active=True,
        won=False,
        flowers=generate_flowers(),
        clouds=[make_cloud(random.randint(0, WIDTH)) for _ in range(4)],
        level=get_level(0),
        level_banner_timer=0,
        confetti=[],
    )


# --- Event Handling ---

def handle_events(state):
    """Process pygame events. Returns (new_state_or_None, toggle_fullscreen)."""
    toggle_fullscreen = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            toggle_fullscreen = True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if state.game_active:
                state.bird_vel = JUMP_VELOCITY
            elif not state.won:
                return reset_game(), toggle_fullscreen
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            if not state.game_active:
                return reset_game(), toggle_fullscreen
        if event.type == pygame.MOUSEBUTTONDOWN:
            if state.game_active:
                state.bird_vel = JUMP_VELOCITY
            elif not state.won:
                return reset_game(), toggle_fullscreen

    return None, toggle_fullscreen


# --- Game Update ---

def update_game(state, burp_sound):
    """Update bird physics, pipes, flowers, clouds, confetti, scoring, and collision."""
    if not state.game_active:
        return

    lvl = state.level

    # Update bird
    state.bird_vel += lvl.gravity
    if state.bird_vel > lvl.max_fall:
        state.bird_vel = lvl.max_fall
    state.bird_y += state.bird_vel

    # Clamp bird position
    if state.bird_y - BIRD_RADIUS < 0:
        state.bird_y = float(BIRD_RADIUS)
        state.bird_vel = 0
    if state.bird_y + BIRD_RADIUS > HEIGHT - GROUND_HEIGHT:
        state.bird_y = float(HEIGHT - GROUND_HEIGHT - BIRD_RADIUS)

    # Update pipes
    update_pipes(state.pipes, state.frame_count, lvl.speed, lvl.spawn)
    update_flowers(state.flowers, lvl.speed)
    update_clouds(state.clouds)

    # Score
    state.score = update_score(state.pipes, state.score)

    # Level check
    new_level = get_level(state.score)
    if new_level.num != state.level.num:
        state.level_banner_timer = LEVEL_BANNER_DURATION
        state.level = new_level
        spawn_confetti(state.confetti)
        burp_sound.play()

    if state.level_banner_timer > 0:
        state.level_banner_timer -= 1

    update_confetti(state.confetti)

    # Win check
    if state.score >= WIN_SCORE:
        state.game_active = False
        state.won = True

    # Collision
    if check_collision(state.bird_y, state.pipes, lvl.gap):
        state.game_active = False


# --- Main ---

def main():
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.init()
    display_info = pygame.display.Info()
    full_w, full_h = display_info.current_w, display_info.current_h

    is_fullscreen = False
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    game_surface = pygame.Surface((WIDTH, HEIGHT))
    pygame.display.set_caption("Flappy Bird")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont(None, 64)
    small_font = pygame.font.SysFont(None, 36)
    burp_sound = create_burp_sound()

    state = reset_game()

    while True:
        new_state, toggle_fullscreen = handle_events(state)
        if new_state is not None:
            state = new_state

        if toggle_fullscreen:
            is_fullscreen = not is_fullscreen
            if is_fullscreen:
                screen = pygame.display.set_mode((full_w, full_h), pygame.FULLSCREEN)
                pygame.mouse.set_visible(False)
            else:
                screen = pygame.display.set_mode((WIDTH, HEIGHT))
                pygame.mouse.set_visible(True)

        state.frame_count += 1

        update_game(state, burp_sound)

        # Draw to game surface
        lvl = state.level
        draw_background(game_surface, state.flowers, state.score, state.clouds)
        draw_llama(game_surface, state.frame_count)
        draw_confetti(game_surface, state.confetti)
        draw_pipes(game_surface, state.pipes, lvl.gap)
        draw_bird(game_surface, state.bird_y, state.bird_vel, state.frame_count)
        draw_score(game_surface, state.score, state.level, font, small_font)

        if not state.game_active:
            if state.won:
                draw_win(game_surface, state.score, font, small_font, state.frame_count, state.bird_y)
            else:
                draw_game_over(game_surface, state.score, font, small_font)

        # Scale game surface to screen
        screen_w, screen_h = screen.get_size()
        scale = min(screen_w / WIDTH, screen_h / HEIGHT)
        scaled_w = int(WIDTH * scale)
        scaled_h = int(HEIGHT * scale)
        scaled = pygame.transform.scale(game_surface, (scaled_w, scaled_h))
        screen.fill(BLACK)
        screen.blit(scaled, ((screen_w - scaled_w) // 2, (screen_h - scaled_h) // 2))

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
