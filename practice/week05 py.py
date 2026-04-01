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

# 색상 설정
WHITE  = (255, 255, 255)
BLACK  = (0,   0,   0)
RED    = (255, 0,   0)   
YELLOW = (255, 255, 0)   
GRAY_BLADE = (200, 200, 200) 
GRAY_HILT  = (100, 100, 100) 
BROWN_HANDLE = (139, 69, 19)  
BLOOD_RED = (180, 0, 0) 
GRAY = (150, 150, 150) 

# 캐릭터 전용 색상
CHAR_SKIN = (255, 218, 185)
CHAR_HAIR = (147, 112, 219) # 연보라색 머리
CHAR_DRESS = (255, 182, 193) # 분홍색 치마
CHAR_EYE = (50, 50, 50)
CHAR_BLUSH = (255, 160, 160)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Undertale Knife Pattern Upgrade")

canvas = pygame.Surface((WIDTH, HEIGHT)) 
clock = pygame.time.Clock()

font = get_korean_font(36)
font_big = get_korean_font(72)
font_mid = get_korean_font(50)   
font_small = get_korean_font(24) 

# --- 전투 박스 (아레나) 설정 ---
ARENA_W, ARENA_H = 250, 250 
ARENA_X = (WIDTH - ARENA_W) // 2
ARENA_Y = (HEIGHT - ARENA_H) // 2
arena_rect = pygame.Rect(ARENA_X, ARENA_Y, ARENA_W, ARENA_H)

# 메뉴 진입 시 사용될 넓은 텍스트 박스
MENU_BOX_RECT = pygame.Rect(50, HEIGHT - 350, WIDTH - 100, 200)
BORDER_THICKNESS = 5 

# 플레이어 크기
PLAYER_W, PLAYER_H = 20, 20 

# --- 메뉴 버튼 설정 ---
menu_options = ["공격", "사랑", "회복"] 
button_w, button_h = 160, 60
button_y = HEIGHT - 100
button_gap = (WIDTH - (3 * button_w)) // 4 
button_rects = []
for i in range(3): 
    bx = button_gap + i * (button_w + button_gap)
    button_rects.append(pygame.Rect(bx, button_y, button_w, button_h))

# 공격 패턴의 칼 그리기 함수 (캐릭터가 들 수 있게 순서를 위로 올림)
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

# --- 귀여운 캐릭터 그리기 함수 ---
def draw_cute_girl(surf, cx, cy):
    # 1. 뒷머리 (큰 타원)
    pygame.draw.ellipse(surf, CHAR_HAIR, (cx - 70, cy - 60, 140, 160))

    # 2. 다리 (직사각형)
    pygame.draw.rect(surf, CHAR_SKIN, (cx - 25, cy + 90, 12, 60))
    pygame.draw.rect(surf, CHAR_SKIN, (cx + 13, cy + 90, 12, 60))

    # 3. 신발 (반원/타원)
    pygame.draw.ellipse(surf, CHAR_EYE, (cx - 30, cy + 140, 20, 15))
    pygame.draw.ellipse(surf, CHAR_EYE, (cx + 10, cy + 140, 20, 15))

    # 4. 드레스 (삼각형)
    pygame.draw.polygon(surf, CHAR_DRESS, [(cx, cy + 20), (cx - 70, cy + 110), (cx + 70, cy + 110)])
    
    # 5. 드레스 밑단 포인트 (다각형)
    pygame.draw.polygon(surf, WHITE, [(cx - 70, cy + 110), (cx + 70, cy + 110), (cx, cy + 95)])

    # 6. 팔 (굵은 선)
    pygame.draw.line(surf, CHAR_SKIN, (cx - 25, cy + 40), (cx - 55, cy + 80), 10)
    pygame.draw.line(surf, CHAR_SKIN, (cx + 25, cy + 40), (cx + 55, cy + 80), 10)

    # ==========================================
    # 6-5. 공격 패턴의 칼(Realistic Knife) 장착
    # ==========================================
    kw, kh = 18, 55 # 장애물 칼의 기본 크기
    # 왼손과 오른손 끝 좌표(cy + 80)에 손잡이가 오도록 Y좌표 조절 (cy + 30)
    left_knife_rect = pygame.Rect(cx - 55 - kw//2, cy + 30, kw, kh)
    right_knife_rect = pygame.Rect(cx + 55 - kw//2, cy + 30, kw, kh)

    # 칼날이 위를 향하도록('up') 양손에 그립니다.
    draw_realistic_knife(surf, left_knife_rect, 'up')
    draw_realistic_knife(surf, right_knife_rect, 'up')
    # ==========================================

    # 7. 얼굴 (원)
    pygame.draw.circle(surf, CHAR_SKIN, (cx, cy), 50)

    # 8. 앞머리 (다각형)
    pygame.draw.polygon(surf, CHAR_HAIR, [(cx - 50, cy - 10), (cx - 60, cy - 50), (cx - 10, cy - 50)])
    pygame.draw.polygon(surf, CHAR_HAIR, [(cx + 50, cy - 10), (cx + 60, cy - 50), (cx + 10, cy - 50)])
    pygame.draw.polygon(surf, CHAR_HAIR, [(cx - 20, cy), (cx - 30, cy - 60), (cx + 30, cy - 60), (cx + 20, cy)])

    # 9. 눈 (원)
    pygame.draw.circle(surf, CHAR_EYE, (cx - 18, cy + 5), 6)
    pygame.draw.circle(surf, CHAR_EYE, (cx + 18, cy + 5), 6)
    # 눈동자 하이라이트
    pygame.draw.circle(surf, WHITE, (cx - 19, cy + 3), 2)
    pygame.draw.circle(surf, WHITE, (cx + 17, cy + 3), 2)

    # 10. 볼터치 (타원)
    pygame.draw.ellipse(surf, CHAR_BLUSH, (cx - 35, cy + 15, 16, 8))
    pygame.draw.ellipse(surf, CHAR_BLUSH, (cx + 19, cy + 15, 16, 8))

    # 11. 입 (작은 다각형 미소)
    pygame.draw.polygon(surf, CHAR_EYE, [(cx - 6, cy + 25), (cx + 6, cy + 25), (cx, cy + 32)])

    # 12. 가슴 리본 (삼각형 2개와 중앙 원)
    pygame.draw.polygon(surf, RED, [(cx, cy + 45), (cx - 20, cy + 35), (cx - 20, cy + 55)])
    pygame.draw.polygon(surf, RED, [(cx, cy + 45), (cx + 20, cy + 35), (cx + 20, cy + 55)])
    pygame.draw.circle(surf, YELLOW, (cx, cy + 45), 6)

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
    
    game_state = "DODGE" 
    menu_index = 0

    current_pattern = 1
    pattern_timer = 0
    
    spawn_timer = 0
    spawn_rate = 18 
    
    shake_timer = 0
    
    spin_timer = 0
    spin_duration = 120 
    current_spin_val = 1
    heal_amount = 0

    while True:
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if e.type == pygame.KEYDOWN:
                if game_state == "MENU":
                    if e.key == pygame.K_a:
                        menu_index = max(0, menu_index - 1)
                    elif e.key == pygame.K_d:
                        menu_index = min(2, menu_index + 1)
                    elif e.key == pygame.K_z or e.key == pygame.K_RETURN:
                        if menu_index == 2:
                            game_state = "HEAL_WAIT"
                        else:
                            game_state = "DODGE"
                            pattern_timer = 0
                            current_pattern = 1
                            player.centerx = arena_rect.centerx
                            player.centery = arena_rect.centery
                            knives.clear()
                            
                elif game_state == "HEAL_WAIT":
                    if e.key == pygame.K_z or e.key == pygame.K_RETURN:
                        game_state = "HEAL_SPIN"
                        spin_timer = spin_duration
                    elif e.key == pygame.K_ESCAPE:
                        game_state = "MENU"
                        
                elif game_state == "HEAL_RESULT":
                    if e.key == pygame.K_z or e.key == pygame.K_RETURN:
                        game_state = "DODGE"
                        pattern_timer = 0
                        current_pattern = 1
                        player.centerx = arena_rect.centerx
                        player.centery = arena_rect.centery
                        knives.clear()

        keys = pygame.key.get_pressed()
        
        if game_state == "DODGE":
            if keys[pygame.K_a] or keys[pygame.K_LEFT]: player.x -= 5
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]: player.x += 5
            if keys[pygame.K_w] or keys[pygame.K_UP]: player.y -= 5
            if keys[pygame.K_s] or keys[pygame.K_DOWN]: player.y += 5

            if player.left < arena_rect.left + BORDER_THICKNESS: player.left = arena_rect.left + BORDER_THICKNESS
            if player.right > arena_rect.right - BORDER_THICKNESS: player.right = arena_rect.right - BORDER_THICKNESS
            if player.top < arena_rect.top + BORDER_THICKNESS: player.top = arena_rect.top + BORDER_THICKNESS
            if player.bottom > arena_rect.bottom - BORDER_THICKNESS: player.bottom = arena_rect.bottom - BORDER_THICKNESS

            pattern_timer += 1 

            if current_pattern == 1:
                spawn_timer += 1
                if spawn_timer >= spawn_rate:
                    spawn_timer = 0
                    rect, dx, dy, direction = spawn_knife()
                    knives.append([rect, dx, dy, direction])
                
                if pattern_timer >= 600:
                    game_state = "MENU"
                    knives.clear() 
                    menu_index = 0 

        if game_state == "HEAL_SPIN":
            spin_timer -= 1
            if spin_timer % 5 == 0:
                current_spin_val = random.randint(1, 3)
            
            if spin_timer <= 0:
                heal_amount = random.randint(1, 3)
                lives = min(max_lives, lives + heal_amount)
                game_state = "HEAL_RESULT"

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
            
            if game_state == "DODGE" and invincible == 0 and player_hitbox.colliderect(knife_hitbox):
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

        canvas.fill(BLACK)
        
        if game_state == "DODGE":
            pygame.draw.rect(canvas, WHITE, arena_rect, BORDER_THICKNESS)
            for knife in knives:
                draw_realistic_knife(canvas, knife[0], knife[3])
                
            if invincible == 0 or (invincible // 5) % 2 == 0:
                pygame.draw.rect(canvas, RED, player)
                
        elif game_state in ["MENU", "HEAL_WAIT", "HEAL_SPIN", "HEAL_RESULT"]:
            
            # 중앙 상단 빈 공간에 무기를 장착한 여자 캐릭터 그리기
            draw_cute_girl(canvas, WIDTH // 2, 170)

            # 1. 넓은 대화창 그리기
            pygame.draw.rect(canvas, WHITE, MENU_BOX_RECT, BORDER_THICKNESS)
            
            line1_text = font.render("상태창", True, WHITE)
            canvas.blit(line1_text, (MENU_BOX_RECT.x + 30, MENU_BOX_RECT.y + 30))

            info_move_text = font_small.render("이동: A(좌) D(우)", True, GRAY)
            info_select_text = font_small.render("선택: Enter", True, GRAY)
            
            move_y = MENU_BOX_RECT.bottom - 75
            select_y = MENU_BOX_RECT.bottom - 45
            
            canvas.blit(info_move_text, (MENU_BOX_RECT.x + 30, move_y))
            canvas.blit(info_select_text, (MENU_BOX_RECT.x + 30, select_y))

            # 2. 하단 버튼 그리기
            for i, rect in enumerate(button_rects):
                color = YELLOW if i == menu_index else WHITE
                pygame.draw.rect(canvas, color, rect, 3) 
                
                btn_text = font.render(menu_options[i], True, color)
                t_x = rect.x + (rect.width - btn_text.get_width()) // 2
                t_y = rect.y + (rect.height - btn_text.get_height()) // 2
                canvas.blit(btn_text, (t_x, t_y))
                
                if i == menu_index and game_state == "MENU":
                    heart_x = rect.x + 15
                    heart_y = rect.y + (rect.height - PLAYER_H) // 2
                    pygame.draw.rect(canvas, RED, (heart_x, heart_y, PLAYER_W, PLAYER_H))

            # 3. 룰렛 상태일 때 중앙에 네모난 룰렛 박스 그리기
            if game_state in ["HEAL_WAIT", "HEAL_SPIN", "HEAL_RESULT"]:
                roulette_w, roulette_h = 400, 200
                roulette_rect = pygame.Rect(WIDTH//2 - roulette_w//2, HEIGHT//2 - roulette_h//2, roulette_w, roulette_h)
                
                pygame.draw.rect(canvas, BLACK, roulette_rect)
                pygame.draw.rect(canvas, WHITE, roulette_rect, BORDER_THICKNESS)
                
                if game_state == "HEAL_WAIT":
                    info_text = font_small.render("랜덤으로 체력 1~3 회복", True, YELLOW)
                    text1 = font.render("회복하려면", True, WHITE)
                    text2 = font.render("엔터(Enter)를 누르세요", True, WHITE)
                    text3 = font.render("취소: ESC", True, GRAY_BLADE) 
                    
                    canvas.blit(info_text, (roulette_rect.centerx - info_text.get_width()//2, roulette_rect.centery - 70))
                    canvas.blit(text1, (roulette_rect.centerx - text1.get_width()//2, roulette_rect.centery - 30))
                    canvas.blit(text2, (roulette_rect.centerx - text2.get_width()//2, roulette_rect.centery + 10))
                    canvas.blit(text3, (roulette_rect.centerx - text3.get_width()//2, roulette_rect.centery + 50))
                
                elif game_state == "HEAL_SPIN":
                    text = font_mid.render(f"체력 {current_spin_val} 회복", True, GRAY_BLADE)
                    canvas.blit(text, (roulette_rect.centerx - text.get_width()//2, roulette_rect.centery - text.get_height()//2))
                
                elif game_state == "HEAL_RESULT":
                    text = font_mid.render(f"체력 {heal_amount} 회복!", True, YELLOW)
                    text2 = font.render("엔터를 눌러 복귀", True, WHITE)
                    
                    gap = 10 
                    total_height = text.get_height() + gap + text2.get_height()
                    start_y = roulette_rect.centery - (total_height // 2)

                    canvas.blit(text, (roulette_rect.centerx - text.get_width()//2, start_y))
                    canvas.blit(text2, (roulette_rect.centerx - text2.get_width()//2, start_y + text.get_height() + gap))

        # --- 체력 UI 렌더링 (공통) ---
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

        shake_x, shake_y = 0, 0
        if shake_timer > 0:
            shake_x = random.randint(-8, 8)
            shake_y = random.randint(-8, 8)
            shake_timer -= 1

        screen.fill(BLACK) 
        screen.blit(canvas, (shake_x, shake_y))

        pygame.display.flip()

if __name__ == "__main__":
    main()