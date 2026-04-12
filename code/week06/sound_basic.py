import pygame

pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("Sound Basics")
clock = pygame.time.Clock()

# ── ① 효과음 로드 ──────────────────────────────
attack_sound = pygame.mixer.Sound("./code/week06/assets/sounds/얀데레공격했을때.mp3")
attack_sound.set_volume(0.5)        # 0.0 ~ 1.0

# ── ② 배경음악 로드 ────────────────────────────
pygame.mixer.music.load("./code/week06/assets/sounds/게임오버음.mp3")

# ── ③ 볼륨 조절 ────────────────────────────────
pygame.mixer.music.set_volume(0.05)

# ── ④ 배경음악 재생 ────────────────────────────
pygame.mixer.music.play(1)  # -1: 무한 반복

running = True
while running:
    clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            # ── ⑤ 스페이스바로 효과음 재생 ────
            if event.key == pygame.K_SPACE:
                attack_sound.play()

    screen.fill((30, 30, 40))
    pygame.display.flip()

pygame.quit()
