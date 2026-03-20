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

        self.size = random.uniform(12, 30)

        # 다양한 도형 선택
        self.shape = random.choice(["circle", "square", "triangle", "diamond", "star"])

        # 부드러운 색감
        self.color = (
            random.randint(180, 255),
            random.randint(150, 255),
            random.randint(200, 255)
        )

    def update(self):
        self.x += self.vx
        self.y += self.vy

        # 중력
        self.vy += 0.07

        # 살짝 감속
        self.vx *= 0.99
        self.vy *= 0.99

        self.life -= 1

    def draw(self, surf):
        if self.life <= 0:
            return

        alpha = int(255 * (self.life / self.max_life))
        size = int(self.size * (self.life / self.max_life))

        glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.color, alpha // 3), (30, 30), size * 2)
        surf.blit(glow, (self.x - 30, self.y - 30))

        x = int(self.x)
        y = int(self.y)

        # ---------- 여러 도형 ----------

        if self.shape == "circle":
            pygame.draw.circle(surf, self.color, (x, y), size)

        elif self.shape == "square":
            pygame.draw.rect(surf, self.color, (x - size, y - size, size * 2, size * 2))

        elif self.shape == "triangle":
            pygame.draw.polygon(
                surf,
                self.color,
                [(x, y - size), (x - size, y + size), (x + size, y + size)]
            )

        elif self.shape == "diamond":
            pygame.draw.polygon(
                surf,
                self.color,
                [(x, y - size), (x - size, y), (x, y + size), (x + size, y)]
            )

        elif self.shape == "star":
            points = []
            for i in range(10):
                angle = i * math.pi / 5
                r = size if i % 2 == 0 else size // 2
                px = x + math.cos(angle) * r
                py = y + math.sin(angle) * r
                points.append((px, py))
            pygame.draw.polygon(surf, self.color, points)

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
        for _ in range(1):
            particles.append(Particle(mouse[0], mouse[1]))

    # Right click = burst explosion
    if buttons[2]:
        for _ in range(4):
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
