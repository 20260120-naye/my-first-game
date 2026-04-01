import pygame
import random
import sys

pygame.init()

def get_korean_font(size):
    candidates = ["malgungothic", "applegothic", "nanumgothic", "notosanscjk"]
    for name in candidates:
        font = pygame.font.SysFont(name, size)
        if font.get_ascent() > 0:
            return font
    return pygame.font.SysFont(None, size)

WIDTH, HEIGHT = 1024, 768
FPS = 60

# 색상 설정 (언더테일 감성)
WHITE  = (255, 255, 255)
BLACK  = (0,   0,   0)
RED    = (255, 0,   0)   # 플레이어 및 하트
GRAY_BLADE = (200, 200, 200) # 칼날 (연회색)
GRAY_HILT  = (100, 100, 100) # 검막이/코 (진회색)
BROWN_HANDLE = (139, 69, 19)  # 손잡이 (갈색)
BLOOD_RED = (180, 0, 0) # 피 색상 (약간 검붉은 색상으로 디테일 추가)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Undertale Knife Pattern Upgrade")

# 화면 흔들림 효과를 위해 모든 그림을 그릴 가상의 도화지(canvas) 생성
canvas = pygame.Surface((WIDTH, HEIGHT)) 
clock = pygame.time.Clock()

font = get_korean_font(36)
font_big = get_korean_font(72)

# --- 전투 박스 (아레나) 설정 ---
ARENA_W, ARENA_H = 250, 250 
ARENA_X = (WIDTH - ARENA_W) // 2
ARENA_Y = (HEIGHT - ARENA_H) // 2
arena_rect = pygame.Rect(ARENA_X, ARENA_Y, ARENA_W, ARENA_H)
BORDER_THICKNESS = 5 

# 플레이어 크기 20x20
PLAYER_W, PLAYER_H = 20, 20 

def draw_realistic_knife(surf, rect, direction):
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    
    if direction == 'down': 
        pygame.draw.rect(surf, BROWN_HANDLE, (x + w*0.3, y, w*0.4, h*0.3))
        pygame.draw.rect(surf, GRAY_HILT, (x, y + h*0.3, w, h*0.1))
        blade_points = [(x + w*0.1, y + h*0.4), (x + w*0.9, y + h*0.4), (x + w/2, y + h)]
        pygame.draw.polygon(surf, GRAY_BLADE, blade_points)
        blood_points = [(x + w*0.25, y + h*0.65), (x + w*0.75, y + h*0.65), (x + w/2, y + h)]
        pygame.draw.polygon(surf, BLOOD_RED, blood_points)
        pygame.draw.rect(surf, BLOOD_RED, (x + w*0.45, y + h*0.45, w*0.1, h*0.25))
        
    elif direction == 'up': 
        pygame.draw.rect(surf, BROWN_HANDLE, (x + w*0.3, y + h*0.7, w*0.4, h*0.3))
        pygame.draw.rect(surf, GRAY_HILT, (x, y + h*0.6, w, h*0.1))
        blade_points = [(x + w*0.1, y + h*0.6), (x + w*0.9, y + h*0.6), (x + w/2, y)]
        pygame.draw.polygon(surf, GRAY_BLADE, blade_points)
        blood_points = [(x + w*0.25, y + h*0.35), (x + w*0.75, y + h*0.35), (x + w/2, y)]
        pygame.draw.polygon(surf, BLOOD_RED, blood_points)
        pygame.draw.rect(surf, BLOOD_RED, (x + w*0.45, y + h*0.3, w*0.1, h*0.25))

    elif direction == 'right': 
        pygame.draw.rect(surf, BROWN_HANDLE, (x, y + h*0.3, w*0.3, h*0.4))
        pygame.draw.rect(surf, GRAY_HILT, (x + w*0.3, y, w*0.1, h))
        blade_points = [(x + w*0.4, y + h*0.1), (x + w*0.4, y + h*0.9), (x + w, y + h/2)]
        pygame.draw.polygon(surf, GRAY_BLADE, blade_points)
        blood_points = [(x + w*0.65, y + h*0.25), (x + w*0.65, y + h*0.75), (x + w, y + h/2)]
        pygame.draw.polygon(surf, BLOOD_RED, blood_points)
        pygame.draw.rect(surf, BLOOD_RED, (x + w*0.45, y + h*0.45, w*0.25, h*0.1))

    elif direction == 'left': 
        pygame.draw.rect(surf, BROWN_HANDLE, (x + w*0.7, y + h*0.3, w*0.3, h*0.4))
        pygame.draw.rect(surf, GRAY_HILT, (x + w*0.6, y, w*0.1, h))
        blade_points = [(x + w*0.6, y + h*0.1), (x + w*0.6, y + h*0.9), (x, y + h/2)]
        pygame.draw.polygon(surf, GRAY_BLADE, blade_points)
        blood_points = [(x + w*0.35, y + h*0.25), (x + w*0.35, y + h*0.75), (x, y + h/2)]
        pygame.draw.polygon(surf, BLOOD_RED, blood_points)
        pygame.draw.rect(surf, BLOOD_RED, (x + w*0.3, y + h*0.45, w*0.25, h*0.1))


def spawn_knife():
    side = random.randint(0, 3)
    speed = random.randint(7, 12) 
    
    K_LONG = 55
    K_SHORT = 18

    if side == 0:
        x = random.randint(arena_rect.left, arena_rect.right - K_SHORT)
        y = -100
        return pygame.Rect(x, y, K_SHORT, K_LONG), 0, speed, 'down'
    elif side == 1: 
        x = random.randint(arena_rect.left, arena_rect.right - K_SHORT)
        y = HEIGHT + 100
        return pygame.Rect(x, y, K_SHORT, K_LONG), 0, -speed, 'up'
    elif side == 2: 
        x = -100
        y = random.randint(arena_rect.top, arena_rect.bottom - K_SHORT)
        return pygame.Rect(x, y, K_LONG, K_SHORT), speed, 0, 'right'
    else: 
        x = WIDTH + 100
        y = random.randint(arena_rect.top, arena_rect.bottom - K_SHORT)
        return pygame.Rect(x, y, K_LONG, K_SHORT), -speed, 0, 'left'

def game_over_screen():
    screen.fill(BLACK)
    text1 = font_big.render("GAME OVER", True, RED)
    text2 = font.render("Press 'R' to Restart", True, WHITE)
    screen.blit(text1, (WIDTH // 2 - text1.get_width() // 2, HEIGHT // 2 - 50))
    screen.blit(text2, (WIDTH // 2 - text2.get_width() // 2, HEIGHT // 2 + 30))
    pygame.display.flip()
    
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r: 
                    return
                if e.key == pygame.K_q: 
                    pygame.quit()
                    sys.exit()

def main():
    player = pygame.Rect(
        arena_rect.centerx - PLAYER_W // 2, 
        arena_rect.centery - PLAYER_H // 2, 
        PLAYER_W, PLAYER_H
    )

    max_lives = 5
    lives = max_lives
    invincible = 0  
    
    knives = []     
    
    # [추가] 패턴 관리를 위한 변수들
    current_pattern = 1
    pattern_timer = 0
    
    spawn_timer = 0
    spawn_rate = 18 
    
    shake_timer = 0

    while True:
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_a]: player.x -= 5
        if keys[pygame.K_d]: player.x += 5
        if keys[pygame.K_w]: player.y -= 5
        if keys[pygame.K_s]: player.y += 5

        if player.left < arena_rect.left + BORDER_THICKNESS: 
            player.left = arena_rect.left + BORDER_THICKNESS
        if player.right > arena_rect.right - BORDER_THICKNESS: 
            player.right = arena_rect.right - BORDER_THICKNESS
        if player.top < arena_rect.top + BORDER_THICKNESS: 
            player.top = arena_rect.top + BORDER_THICKNESS
        if player.bottom > arena_rect.bottom - BORDER_THICKNESS: 
            player.bottom = arena_rect.bottom - BORDER_THICKNESS

        # --- [수정] 패턴 시스템 도입 ---
        pattern_timer += 1 # 게임이 시작된 후 계속 증가하며 시간을 잽니다.

        if current_pattern == 1:
            # 파트 1: 기존의 무작위 스폰 패턴
            spawn_timer += 1
            if spawn_timer >= spawn_rate:
                spawn_timer = 0
                rect, dx, dy, direction = spawn_knife()
                knives.append([rect, dx, dy, direction])
            
            # (예시) 파트 1이 600프레임(약 10초) 동안 지속된 후 파트 2로 넘어갈 경우:
            # if pattern_timer >= 600:
            #     current_pattern = 2
            #     pattern_timer = 0
        
        elif current_pattern == 2:
            pass # 나중에 여기에 파트 2 패턴을 작성하면 됩니다.


        if invincible > 0:
            invincible -= 1

        player_hitbox = pygame.Rect(0, 0, 8, 8)
        player_hitbox.center = player.center

        survived_knives = []
        for knife in knives:
            rect, dx, dy, direction = knife[0], knife[1], knife[2], knife[3]
            rect.x += dx
            rect.y += dy
            
            knife_hitbox = rect 
            
            if invincible == 0 and player_hitbox.colliderect(knife_hitbox):
                lives -= 1
                invincible = 90
                shake_timer = 6  
                
                if lives <= 0:
                    game_over_screen()
                    main() 
                    return
            
            if -150 < rect.x < WIDTH + 150 and -150 < rect.y < HEIGHT + 150:
                survived_knives.append(knife)
                
        knives = survived_knives

        # --- 그리기 과정 ---
        canvas.fill(BLACK)
        pygame.draw.rect(canvas, WHITE, arena_rect, BORDER_THICKNESS)

        for knife in knives:
            draw_realistic_knife(canvas, knife[0], knife[3])

        if invincible == 0 or (invincible // 5) % 2 == 0:
            pygame.draw.rect(canvas, RED, player)

        hp_label = font.render("HP: ", True, RED)
        heart_surf = font.render("♥ ", True, RED)
        
        label_w = hp_label.get_width()
        heart_w = heart_surf.get_width()
        
        total_hp_width = label_w + heart_w * max_lives
        hp_x = WIDTH - total_hp_width - 20
        hp_y = 20
        
        canvas.blit(hp_label, (hp_x, hp_y))
        
        for i in range(lives):
            canvas.blit(heart_surf, (hp_x + label_w + i * heart_w, hp_y))
            
        if invincible > 0 and (invincible // 5) % 2 == 0:
            canvas.blit(heart_surf, (hp_x + label_w + lives * heart_w, hp_y))

        # 흔들림 효과 계산
        shake_x, shake_y = 0, 0
        if shake_timer > 0:
            shake_x = random.randint(-8, 8)
            shake_y = random.randint(-8, 8)
            shake_timer -= 1

        # 완성된 도화지를 실제 메인 화면에 덮어씌웁니다 (흔들림 좌표 적용)
        screen.fill(BLACK) 
        screen.blit(canvas, (shake_x, shake_y))

        pygame.display.flip()

if __name__ == "__main__":
    main()