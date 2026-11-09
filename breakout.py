import math
import random
import sys
import pygame

# Initialize Pygame and Audio Mixer
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# --- CONFIGURATION & CONSTANTS ---
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 700
FPS = 60

# Cyberpunk Neon Palette
COLOR_BG = (15, 12, 28)
COLOR_GRID = (28, 22, 55)
COLOR_TEXT = (240, 240, 255)
COLOR_PADDLE = (0, 255, 204)      # Cyan
COLOR_BALL = (255, 0, 128)        # Neon Pink
COLOR_SHIELD = (0, 150, 255)

COLOR_BRICK_RED = (255, 42, 109)   # 1 Hit
COLOR_BRICK_BLUE = (5, 217, 232)   # 2 Hits
COLOR_BRICK_YELLOW = (255, 190, 11) # 3 Hits
COLOR_BRICK_STEEL = (140, 150, 170) # Indestructible
COLOR_BRICK_BOMB = (255, 87, 34)   # Explosive

# --- SYNTHESIZED SOUND GENERATOR ---
def generate_sound(sound_type):
    sample_rate = 44100
    duration = 0.1
    if sound_type == 'paddle':
        freq_start, freq_end = 400, 200
        duration = 0.08
    elif sound_type == 'brick':
        freq_start, freq_end = 600, 900
        duration = 0.06
    elif sound_type == 'powerup':
        freq_start, freq_end = 300, 1200
        duration = 0.2
    elif sound_type == 'laser':
        freq_start, freq_end = 1000, 400
        duration = 0.05
    elif sound_type == 'explode':
        freq_start, freq_end = 150, 50
        duration = 0.25
    else:
        freq_start, freq_end = 300, 300

    n_samples = int(sample_rate * duration)
    buf = bytearray()
    for i in range(n_samples):
        t = i / n_samples
        freq = freq_start + (freq_end - freq_start) * t
        val = int(127 * math.sin(2 * math.pi * freq * (i / sample_rate)) * (1 - t))
        val = max(-128, min(127, val))
        buf.append(val & 0xFF)
        buf.append(val & 0xFF)
    return pygame.mixer.Sound(buffer=bytes(buf))

SOUND_PADDLE = generate_sound('paddle')
SOUND_BRICK = generate_sound('brick')
SOUND_POWERUP = generate_sound('powerup')
SOUND_LASER = generate_sound('laser')
SOUND_EXPLODE = generate_sound('explode')

# --- GAME OBJECT CLASSES ---

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.vx = random.uniform(-4, 4)
        self.vy = random.uniform(-4, 4)
        self.size = random.uniform(3, 7)
        self.life = 1.0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.size *= 0.92
        self.life -= 0.03

    def draw(self, surface):
        if self.life > 0 and self.size > 0.5:
            alpha = int(self.life * 255)
            s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
            surface.blit(s, (self.x - self.size, self.y - self.size))

class Laser:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x - 2, y, 4, 15)
        self.speed = 12

    def update(self):
        self.rect.y -= self.speed

    def draw(self, surface):
        pygame.draw.rect(surface, (0, 255, 204), self.rect)
        pygame.draw.rect(surface, (255, 255, 255), self.rect.inflate(-2, -4))

class PowerUp:
    TYPES = ['MULTIBALL', 'LASER', 'PADDLE_WIDE', 'FIREBALL', 'SHIELD']
    COLORS = {
        'MULTIBALL': (255, 0, 255),
        'LASER': (0, 255, 204),
        'PADDLE_WIDE': (255, 255, 0),
        'FIREBALL': (255, 87, 34),
        'SHIELD': (0, 150, 255)
    }

    def __init__(self, x, y, kind):
        self.rect = pygame.Rect(x - 12, y - 12, 24, 24)
        self.kind = kind
        self.speed = 3.5

    def update(self):
        self.rect.y += self.speed

    def draw(self, surface):
        color = self.COLORS[self.kind]
        pygame.draw.circle(surface, color, self.rect.center, 12)
        pygame.draw.circle(surface, (255, 255, 255), self.rect.center, 12, 2)
        font = pygame.font.SysFont('arial', 12, bold=True)
        txt = font.render(self.kind[0], True, (0, 0, 0))
        surface.blit(txt, txt.get_rect(center=self.rect.center))

class Paddle:
    def __init__(self):
        self.base_width = 120
        self.width = self.base_width
        self.height = 16
        self.rect = pygame.Rect((SCREEN_WIDTH - self.width) // 2, SCREEN_HEIGHT - 50, self.width, self.height)
        self.speed = 9
        self.has_laser = False
        self.laser_timer = 0
        self.wide_timer = 0

    def update(self):
        keys = pygame.key.get_pressed()
        if (keys[pygame.K_LEFT] or keys[pygame.K_a]) and self.rect.left > 10:
            self.rect.x -= self.speed
        if (keys[pygame.K_RIGHT] or keys[pygame.K_d]) and self.rect.right < SCREEN_WIDTH - 10:
            self.rect.x += self.speed

        if self.wide_timer > 0:
            self.wide_timer -= 1
            if self.wide_timer == 0:
                self.rect.width = self.base_width
        if self.laser_timer > 0:
            self.laser_timer -= 1
            if self.laser_timer == 0:
                self.has_laser = False

    def make_wide(self):
        self.rect.width = 180
        self.wide_timer = 450

    def enable_laser(self):
        self.has_laser = True
        self.laser_timer = 360

    def draw(self, surface):
        glow_rect = self.rect.inflate(8, 8)
        glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (0, 255, 204, 80), glow_surf.get_rect(), border_radius=8)
        surface.blit(glow_surf, glow_rect.topleft)
        pygame.draw.rect(surface, COLOR_PADDLE, self.rect, border_radius=6)
        pygame.draw.rect(surface, (255, 255, 255), self.rect.inflate(-4, -4), border_radius=4)

class Ball:
    def __init__(self, x, y):
        self.radius = 9
        self.rect = pygame.Rect(x - self.radius, y - self.radius, self.radius * 2, self.radius * 2)
        self.vx = random.choice([-5, 5])
        self.vy = -6
        self.is_fireball = False
        self.fire_timer = 0

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy

        if self.rect.left <= 10:
            self.rect.left = 10
            self.vx *= -1
            SOUND_PADDLE.play()
        elif self.rect.right >= SCREEN_WIDTH - 10:
            self.rect.right = SCREEN_WIDTH - 10
            self.vx *= -1
            SOUND_PADDLE.play()
        if self.rect.top <= 40:
            self.rect.top = 40
            self.vy *= -1
            SOUND_PADDLE.play()

        if self.fire_timer > 0:
            self.fire_timer -= 1
            if self.fire_timer == 0:
                self.is_fireball = False

    def enable_fireball(self):
        self.is_fireball = True
        self.fire_timer = 360

    def draw(self, surface):
        color = (255, 87, 34) if self.is_fireball else COLOR_BALL
        glow_surf = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color, 90), (self.radius * 2, self.radius * 2), self.radius * 2)
        surface.blit(glow_surf, (self.rect.centerx - self.radius * 2, self.rect.centery - self.radius * 2))
        pygame.draw.circle(surface, color, self.rect.center, self.radius)
        pygame.draw.circle(surface, (255, 255, 255), self.rect.center, self.radius - 3)

class Brick:
    def __init__(self, x, y, width, height, hits, brick_type='NORMAL'):
        self.rect = pygame.Rect(x, y, width, height)
        self.hits = hits
        self.max_hits = hits
        self.type = brick_type

    def draw(self, surface):
        if self.type == 'STEEL':
            color = COLOR_BRICK_STEEL
        elif self.type == 'BOMB':
            color = COLOR_BRICK_BOMB
        else:
            if self.hits == 3: color = COLOR_BRICK_YELLOW
            elif self.hits == 2: color = COLOR_BRICK_BLUE
            else: color = COLOR_BRICK_RED

        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        inner = self.rect.inflate(-4, -4)
        pygame.draw.rect(surface, (255, 255, 255, 50), inner, border_radius=2, width=1)
        
        if self.type == 'BOMB':
            font = pygame.font.SysFont('arial', 12, bold=True)
            lbl = font.render('X', True, (255, 255, 255))
            surface.blit(lbl, lbl.get_rect(center=self.rect.center))

# --- MAIN GAME ENGINE ---

class CyberBreakout:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Cyberpunk Brick Breaker Arcade")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont('consolas', 42, bold=True)
        self.font_medium = pygame.font.SysFont('consolas', 24, bold=True)
        
        self.reset_game()

    def reset_game(self):
        self.score = 0
        self.lives = 3
        self.level = 1
        self.state = 'START'
        self.shield_active = False
        self.particles = []
        self.powerups = []
        self.lasers = []
        self.paddle = Paddle()
        self.balls = []
        self.bricks = []
        self.laser_cooldown = 0
        self.load_level(self.level)

    def load_level(self, level):
        self.bricks.clear()
        self.powerups.clear()
        self.lasers.clear()
        self.balls = [Ball(self.paddle.rect.centerx, self.paddle.rect.top - 15)]

        rows = 4 + min(level, 4)
        cols = 10
        b_width = (SCREEN_WIDTH - 120) // cols
        b_height = 24

        for r in range(rows):
            for c in range(cols):
                x = 60 + c * b_width
                y = 70 + r * (b_height + 6)
                
                rand = random.random()
                if rand < 0.08 and level > 1:
                    b_type, hits = 'STEEL', 999
                elif rand < 0.18:
                    b_type, hits = 'BOMB', 1
                else:
                    b_type = 'NORMAL'
                    hits = 3 if r == 0 else (2 if r < 3 else 1)

                self.bricks.append(Brick(x, y, b_width - 4, b_height, hits, b_type))

    def create_particles(self, x, y, color, count=15):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def trigger_explosion(self, center_x, center_y):
        SOUND_EXPLODE.play()
        self.create_particles(center_x, center_y, COLOR_BRICK_BOMB, 30)
        blast_radius = 80
        for b in self.bricks[:]:
            if b.type != 'STEEL':
                dist = math.hypot(b.rect.centerx - center_x, b.rect.centery - center_y)
                if dist <= blast_radius:
                    self.score += 50
                    self.create_particles(b.rect.centerx, b.rect.centery, COLOR_BRICK_RED, 10)
                    self.bricks.remove(b)

    def handle_collisions(self):
        for ball in self.balls[:]:
            if ball.rect.colliderect(self.paddle.rect) and ball.vy > 0:
                ball.rect.bottom = self.paddle.rect.top
                hit_pos = (ball.rect.centerx - self.paddle.rect.left) / self.paddle.rect.width
                ball.vx = 14 * (hit_pos - 0.5)
                ball.vy = -abs(ball.vy)
                SOUND_PADDLE.play()

            for brick in self.bricks[:]:
                if ball.rect.colliderect(brick.rect):
                    SOUND_BRICK.play()
                    self.create_particles(ball.rect.centerx, ball.rect.centery, COLOR_BRICK_RED)
                    
                    if not ball.is_fireball and brick.type != 'STEEL':
                        ball.vy *= -1

                    if brick.type == 'BOMB':
                        self.trigger_explosion(brick.rect.centerx, brick.rect.centery)
                        if brick in self.bricks:
                            self.bricks.remove(brick)
                    elif brick.type != 'STEEL' or ball.is_fireball:
                        brick.hits -= 1
                        if brick.hits <= 0 or ball.is_fireball:
                            self.score += 100
                            if random.random() < 0.25:
                                kind = random.choice(PowerUp.TYPES)
                                self.powerups.append(PowerUp(brick.rect.centerx, brick.rect.centery, kind))
                            self.bricks.remove(brick)
                    break

            if ball.rect.top > SCREEN_HEIGHT:
                self.balls.remove(ball)

        if not self.balls:
            if self.shield_active:
                self.shield_active = False
                self.balls.append(Ball(self.paddle.rect.centerx, self.paddle.rect.top - 15))
            else:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = 'GAMEOVER'
                else:
                    self.balls.append(Ball(self.paddle.rect.centerx, self.paddle.rect.top - 15))

    def update(self):
        if self.state != 'PLAYING':
            return

        self.paddle.update()

        for ball in self.balls:
            ball.update()

        for particle in self.particles[:]:
            particle.update()
            if particle.life <= 0:
                self.particles.remove(particle)

        for laser in self.lasers[:]:
            laser.update()
            if laser.rect.bottom < 0:
                self.lasers.remove(laser)
            else:
                for brick in self.bricks[:]:
                    if laser.rect.colliderect(brick.rect):
                        if brick in self.bricks and brick.type != 'STEEL':
                            self.bricks.remove(brick)
                            self.score += 50
                        if laser in self.lasers:
                            self.lasers.remove(laser)
                        break

        for pw in self.powerups[:]:
            pw.update()
            if pw.rect.colliderect(self.paddle.rect):
                SOUND_POWERUP.play()
                if pw.kind == 'MULTIBALL':
                    self.balls.append(Ball(self.paddle.rect.centerx, self.paddle.rect.top - 15))
                elif pw.kind == 'LASER':
                    self.paddle.enable_laser()
                elif pw.kind == 'PADDLE_WIDE':
                    self.paddle.make_wide()
                elif pw.kind == 'FIREBALL':
                    for b in self.balls: b.enable_fireball()
                elif pw.kind == 'SHIELD':
                    self.shield_active = True
                self.powerups.remove(pw)
            elif pw.rect.top > SCREEN_HEIGHT:
                self.powerups.remove(pw)

        self.handle_collisions()

        # Check Win Condition
        remaining = [b for b in self.bricks if b.type != 'STEEL']
        if not remaining:
            self.level += 1
            if self.level > 3:
                self.state = 'VICTORY'
            else:
                self.load_level(self.level)

    def draw(self):
        self.screen.fill(COLOR_BG)

        # Draw Grid Background
        for x in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(self.screen, COLOR_GRID, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(self.screen, COLOR_GRID, (0, y), (SCREEN_WIDTH, y))

        if self.shield_active:
            pygame.draw.line(self.screen, COLOR_SHIELD, (0, SCREEN_HEIGHT - 10), (SCREEN_WIDTH, SCREEN_HEIGHT - 10), 5)

        self.paddle.draw(self.screen)
        for ball in self.balls: ball.draw(self.screen)
        for brick in self.bricks: brick.draw(self.screen)
        for particle in self.particles: particle.draw(self.screen)
        for laser in self.lasers: laser.draw(self.screen)
        for pw in self.powerups: pw.draw(self.screen)

        # UI Overlay
        score_txt = self.font_medium.render(f"SCORE: {self.score}", True, COLOR_TEXT)
        lives_txt = self.font_medium.render(f"LIVES: {self.lives}", True, COLOR_TEXT)
        level_txt = self.font_medium.render(f"LEVEL: {self.level}", True, COLOR_TEXT)

        self.screen.blit(score_txt, (20, 10))
        self.screen.blit(level_txt, (SCREEN_WIDTH // 2 - 50, 10))
        self.screen.blit(lives_txt, (SCREEN_WIDTH - 140, 10))

        if self.state == 'START':
            txt = self.font_large.render("PRESS SPACE TO START", True, COLOR_PADDLE)
            self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
        elif self.state == 'GAMEOVER':
            txt = self.font_large.render("GAME OVER - PRESS R TO RESTART", True, (255, 50, 50))
            self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
        elif self.state == 'VICTORY':
            txt = self.font_large.render("VICTORY! PRESS R TO PLAY AGAIN", True, (0, 255, 100))
            self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

        pygame.display.flip()

    def run(self):
        while True:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        if self.state == 'START':
                            self.state = 'PLAYING'
                        elif self.state == 'PLAYING' and self.paddle.has_laser:
                            self.lasers.append(Laser(self.paddle.rect.left + 10, self.paddle.rect.top))
                            self.lasers.append(Laser(self.paddle.rect.right - 10, self.paddle.rect.top))
                            SOUND_LASER.play()
                    if event.key == pygame.K_r and self.state in ['GAMEOVER', 'VICTORY']:
                        self.reset_game()
                        self.state = 'PLAYING'

            self.update()
            self.draw()

if __name__ == '__main__':
    game = CyberBreakout()
    game.run()