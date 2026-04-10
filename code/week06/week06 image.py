import pygame
import random  # ── 랜덤 위치를 지정하기 위해 추가 ──

pygame.init()
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("Sprite Basics - Random Respawn")
clock = pygame.time.Clock()

# ── ① 이미지 로드 및 크기 조절 ─────────────────
img = pygame.image.load("./code/week06/assets/images/player.jpg").convert_alpha()
img = pygame.transform.scale(img, (100, 100))

rect = img.get_rect()

# 시작할 때도 랜덤한 위치에서 시작하도록 변경
pos_x = random.randint(-50, 350)
pos_y = -100

running = True
while running:
    clock.tick(60)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    # ── ⑤ 이동 로직 ────────────────────────────────
    pos_x += 1.0  
    pos_y += 0.75

    # ── ⑥ 화면 밖으로 나가면 랜덤 위치에서 재등장 ───
    # 이미지가 오른쪽 화면 밖(400)이거나 아래쪽 화면 밖(300)으로 완전히 나가면
    if pos_x > 400 or pos_y > 300:
        
        # 'top'(위쪽)과 'left'(왼쪽) 중 어디서 등장할지 동전 던지기(랜덤)
        spawn_edge = random.choice(["top", "left"])
        
        if spawn_edge == "top":
            # 위쪽 화면 밖에서 등장하되, 가로(X) 위치는 랜덤
            pos_x = float(random.randint(-50, 350))
            pos_y = -100.0
        else:
            # 왼쪽 화면 밖에서 등장하되, 세로(Y) 위치는 랜덤
            pos_x = -100.0
            pos_y = float(random.randint(-50, 250))

    # 계산된 실수 좌표를 rect에 적용
    rect.x = int(pos_x)
    rect.y = int(pos_y)

    # ── 화면 업데이트 ──────────────────────────────
    screen.fill((30, 30, 40))
    screen.blit(img, rect)
    pygame.display.flip()

pygame.quit()