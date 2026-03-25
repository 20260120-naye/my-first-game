import pygame
import sys
import math

pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("OBB + AABB + Circle Collision Display")

GRAY = (150, 150, 150)
RED = (255, 0, 0)      # AABB
BLUE = (0, 150, 255)   # Circle BB
GREEN = (0, 255, 0)    # OBB
COLLISION_COLOR = (255, 0, 0)  # OBB 충돌 배경
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# 폰트 설정
font = pygame.font.SysFont(None, 30)

# 플레이어
player = pygame.Rect(100, 100, 100, 100)
speed = 2

# 회전 사각형
fixed_center = (400, 300)
fixed_size = 150
fixed_angle = 0
rotation_speed = 1
fast_rotation_speed = 5

clock = pygame.time.Clock()
FPS = 60

# 회전 사각형 모서리 계산
def get_rotated_corners(center, size, angle):
    cx, cy = center
    half = size / 2
    corners = [(-half, -half), (half, -half), (half, half), (-half, half)]
    rad = math.radians(angle)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    return [(cx + x * cos_a - y * sin_a, cy + x * sin_a + y * cos_a) for x, y in corners]

def get_axes(corners):
    axes = []
    for i in range(4):
        p1 = corners[i]
        p2 = corners[(i+1)%4]
        edge = (p2[0]-p1[0], p2[1]-p1[1])
        normal = (edge[1], -edge[0])
        length = math.hypot(*normal)
        axes.append((normal[0]/length, normal[1]/length))
    return axes

def project_polygon(corners, axis):
    dots = [corner[0]*axis[0] + corner[1]*axis[1] for corner in corners]
    return min(dots), max(dots)

def sat_collision(corners1, corners2):
    axes1 = get_axes(corners1)
    axes2 = get_axes(corners2)
    axes = axes1 + axes2
    for axis in axes:
        min1, max1 = project_polygon(corners1, axis)
        min2, max2 = project_polygon(corners2, axis)
        if max1 < min2 or max2 < min1:
            return False
    return True

def get_rect_corners(rect):
    return [rect.topleft, rect.topright, rect.bottomright, rect.bottomleft]

def get_aabb(corners):
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    return pygame.Rect(min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys))

running = True
while running:
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 플레이어 이동
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]: player.x -= speed
    if keys[pygame.K_RIGHT]: player.x += speed
    if keys[pygame.K_UP]: player.y -= speed
    if keys[pygame.K_DOWN]: player.y += speed

    # 회전 속도
    current_rotation_speed = fast_rotation_speed if keys[pygame.K_z] else rotation_speed
    fixed_angle += current_rotation_speed

    # 중심점
    player_center = player.center
    player_radius = player.width // 2
    fixed_radius = fixed_size // 2

    # 원형 충돌
    dx = player_center[0] - fixed_center[0]
    dy = player_center[1] - fixed_center[1]
    circle_collision = dx*dx + dy*dy <= (player_radius + fixed_radius)**2

    # OBB 충돌
    player_corners = get_rect_corners(player)
    fixed_corners = get_rotated_corners(fixed_center, fixed_size, fixed_angle)
    obb_collision = sat_collision(player_corners, fixed_corners)

    # AABB 충돌 (단순 직교)
    aabb_rect = get_aabb(fixed_corners)
    aabb_collision = player.colliderect(aabb_rect)

    # 배경은 OBB 충돌 색
    screen.fill(COLLISION_COLOR if obb_collision else BLACK)

    # 플레이어
    pygame.draw.rect(screen, GRAY, player)
    pygame.draw.rect(screen, RED, player, 2)
    pygame.draw.circle(screen, BLUE, player_center, player_radius, 2)

    # 회전 사각형
    pygame.draw.polygon(screen, GRAY, fixed_corners)
    pygame.draw.polygon(screen, GREEN, fixed_corners, 2)
    pygame.draw.circle(screen, BLUE, fixed_center, fixed_radius, 2)  # 원형 BB

    # 회전 사각형 AABB
    pygame.draw.rect(screen, RED, aabb_rect, 2)

    # 화면 왼쪽 상단 충돌 상태 표시
    texts = [
        f"Circle: {'HIT' if circle_collision else 'NO'}",
        f"AABB: {'HIT' if aabb_collision else 'NO'}",
        f"OBB: {'HIT' if obb_collision else 'NO'}"
    ]
    for i, text in enumerate(texts):
        surf = font.render(text, True, WHITE)
        screen.blit(surf, (10, 10 + i*30))

    pygame.display.flip()

pygame.quit()
sys.exit()