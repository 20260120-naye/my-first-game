import pygame
import random
import math

pygame.init()

WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ultra Fancy Particle Playground ✨")

clock = pygame.time.Clock()
particles = []

# ---------- Helper functions ----------

def lerp(a, b, t):
    return a + (b - a) * t


def draw_gradient_background(surface, t):
    for y in range(HEIGHT):
        r = int(30 + 20 * math.sin(y * 0.01 + t))
        g = int(40 + 40 * math.sin(y * 0.008 + t * 1.2))
        b = int(80 + 60 * math.sin(y * 0.012 + t * 0.8))
        pygame.draw.line(surface, (r, g, b), (0, y), (WIDTH, y))


# ---------- Particle Class ----------

class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y

        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2, 7)

        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

        self.life = random.randint(50, 100)
        self.max_life = self.life

        self.size = random.uniform(3, 8)

        # Soft pastel colors
        self.color = (
            random.randint(180, 255),
            random.randint(150, 255),
            random.randint(200, 255)
        )

    def update(self):
        self.x += self.vx
        self.y += self.vy

        # Gravity
        self.vy += 0.07

        # Slow down slightly
        self.vx *= 0.99
        self.vy *= 0.99

        self.life -= 1

    def draw(self, surf):
        if self.life <= 0:
            return

        # Fade effect
        alpha = int(255 * (self.life / self.max_life))

        glow_surface = pygame.Surface((40, 40), pygame.SRCALPHA)
        glow_color = (*self.color, alpha // 2)
        pygame.draw.circle(glow_surface, glow_color, (20, 20), int(self.size * 2.2))

        surf.blit(glow_surface, (self.x - 20, self.y - 20))

        # Main particle
        pygame.draw.circle(
            surf,
            self.color,
            (int(self.x), int(self.y)),
            int(self.size * (self.life / self.max_life))
        )

    def alive(self):
        return self.life > 0


# ---------- Main Loop ----------

running = True
time = 0

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    mouse = pygame.mouse.get_pos()
    buttons = pygame.mouse.get_pressed()

    # Left click = normal particles
    if buttons[0]:
        for _ in range(10):
            particles.append(Particle(mouse[0], mouse[1]))

    # Right click = burst explosion
    if buttons[2]:
        for _ in range(40):
            particles.append(Particle(mouse[0], mouse[1]))

    time += 0.03

    draw_gradient_background(screen, time)

    # Update & draw
    for p in particles:
        p.update()
        p.draw(screen)

    particles = [p for p in particles if p.alive()]

    # Mouse glow effect
    glow = pygame.Surface((120, 120), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 255, 255, 20), (60, 60), 60)
    screen.blit(glow, (mouse[0] - 60, mouse[1] - 60))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
