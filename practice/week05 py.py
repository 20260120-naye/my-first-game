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
YELLOW = (255, 255, 0)   # 메뉴 선택 색상
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

# 메뉴 진입 시 사용될 넓은 텍스트 박스
MENU_BOX_RECT = pygame.Rect(50, HEIGHT - 350, WIDTH - 100, 200)
BORDER_THICKNESS = 5 

# 플레이어 크기 20x20
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
    
    # 게임 상태 관리 ("DODGE", "MENU", "HEAL_WAIT", "HEAL_SPIN", "HEAL_RESULT")
    game_state = "DODGE" 
    menu_index = 0

    current_pattern = 1
    pattern_timer = 0
    
    spawn_timer = 0
    spawn_rate = 18 
    
    shake_timer = 0
    
    # 회복 룰렛 관련 변수
    spin_timer = 0
    spin_duration = 60 # 1초 (60프레임)
    current_spin_val = 1
    heal_amount = 0

    while True:
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # 메뉴창 및 룰렛에서의 키 입력 처리
            if e.type == pygame.KEYDOWN:
                if game_state == "MENU":
                    if e.key == pygame.K_a:
                        menu_index = max(0, menu_index - 1)
                    elif e.key == pygame.K_d:
                        menu_index = min(2, menu_index + 1)
                    elif e.key == pygame.K_z or e.key == pygame.K_RETURN:
                        if menu_index == 2: # '회복' 선택 시 룰렛 대기 상태로 이동
                            game_state = "HEAL_WAIT"
                        else:
                            # 다른 행동 선택 시 다시 닷지 모드로 돌아가기
                            game_state = "DODGE"
                            pattern_timer = 0
                            current_pattern = 1
                            player.centerx = arena_rect.centerx
                            player.centery = arena_rect.centery
                            knives.clear()
                            
                elif game_state == "HEAL_WAIT":
                    if e.key == pygame.K_z or e.key == pygame.K_RETURN:
                        # 엔터를 누르면 룰렛 회전 시작
                        game_state = "HEAL_SPIN"
                        spin_timer = spin_duration
                    elif e.key == pygame.K_ESCAPE:
                        # ESC를 누르면 선택을 취소하고 다시 메뉴로 돌아감
                        game_state = "MENU"
                        
                elif game_state == "HEAL_RESULT":
                    if e.key == pygame.K_z or e.key == pygame.K_RETURN:
                        # 결과를 확인하고 다시 닷지 모드로 복귀
                        game_state = "DODGE"
                        pattern_timer = 0
                        current_pattern = 1
                        player.centerx = arena_rect.centerx
                        player.centery = arena_rect.centery
                        knives.clear()

        keys = pygame.key.get_pressed()
        
        # 회피(DODGE) 모드일 때만 플레이어 조작 가능
        if game_state == "DODGE":
            if keys[pygame.K_a] or keys[pygame.K_LEFT]: player.x -= 5
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]: player.x += 5
            if keys[pygame.K_w] or keys[pygame.K_UP]: player.y -= 5
            if keys[pygame.K_s] or keys[pygame.K_DOWN]: player.y += 5

            if player.left < arena_rect.left + BORDER_THICKNESS: player.left = arena_rect.left + BORDER_THICKNESS
            if player.right > arena_rect.right - BORDER_THICKNESS: player.right = arena_rect.right - BORDER_THICKNESS
            if player.top < arena_rect.top + BORDER_THICKNESS: player.top = arena_rect.top + BORDER_THICKNESS
            if player.bottom > arena_rect.bottom - BORDER_THICKNESS: player.bottom = arena_rect.bottom - BORDER_THICKNESS

            # 패턴 시스템 진행
            pattern_timer += 1 

            if current_pattern == 1:
                spawn_timer += 1
                if spawn_timer >= spawn_rate:
                    spawn_timer = 0
                    rect, dx, dy, direction = spawn_knife()
                    knives.append([rect, dx, dy, direction])
                
                # 10초(600 프레임) 경과 시 메뉴 모드로 전환
                if pattern_timer >= 600:
                    game_state = "MENU"
                    knives.clear() 
                    menu_index = 0 

        # --- 룰렛 진행 (프레임 업데이트) ---
        if game_state == "HEAL_SPIN":
            spin_timer -= 1
            # 5프레임마다 숫자를 바꿔줌 (시각적 룰렛 효과)
            if spin_timer % 5 == 0:
                current_spin_val = random.randint(1, 3)
            
            # 시간이 끝나면 결과 도출 및 체력 회복
            if spin_timer <= 0:
                heal_amount = random.randint(1, 3)
                # 최대 체력(5)을 넘지 않도록 처리
                lives = min(max_lives, lives + heal_amount)
                game_state = "HEAL_RESULT"

        # --- 피격 및 무적 판정 ---
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

        # --- 그리기 과정 ---
        canvas.fill(BLACK)
        
        # 화면 모드에 따라 UI 다르게 그리기
        if game_state == "DODGE":
            pygame.draw.rect(canvas, WHITE, arena_rect, BORDER_THICKNESS)
            for knife in knives:
                draw_realistic_knife(canvas, knife[0], knife[3])
                
            if invincible == 0 or (invincible // 5) % 2 == 0:
                pygame.draw.rect(canvas, RED, player)
                
        elif game_state in ["MENU", "HEAL_WAIT", "HEAL_SPIN", "HEAL_RESULT"]:
            # 1. 넓은 대화창 그리기
            pygame.draw.rect(canvas, WHITE, MENU_BOX_RECT, BORDER_THICKNESS)
            
            # 텍스트 줄바꿈 처리 
            line1_text = font.render("상태창", True, WHITE)
            line2_text = font.render("선택: Enter", True, WHITE)
            canvas.blit(line1_text, (MENU_BOX_RECT.x + 30, MENU_BOX_RECT.y + 30))
            canvas.blit(line2_text, (MENU_BOX_RECT.x + 30, MENU_BOX_RECT.y + 80)) 

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
                
                # 기존 화면을 가리기 위해 검은색으로 채우고 흰색 테두리 그리기
                pygame.draw.rect(canvas, BLACK, roulette_rect)
                pygame.draw.rect(canvas, WHITE, roulette_rect, BORDER_THICKNESS)
                
                if game_state == "HEAL_WAIT":
                    # 수정된 텍스트 및 취소 안내
                    text1 = font.render("회복하려면", True, WHITE)
                    text2 = font.render("엔터(Enter)를 누르세요", True, WHITE)
                    text3 = font.render("취소: ESC", True, GRAY_BLADE) 
                    canvas.blit(text1, (roulette_rect.centerx - text1.get_width()//2, roulette_rect.centery - 45))
                    canvas.blit(text2, (roulette_rect.centerx - text2.get_width()//2, roulette_rect.centery - 5))
                    canvas.blit(text3, (roulette_rect.centerx - text3.get_width()//2, roulette_rect.centery + 35))
                
                elif game_state == "HEAL_SPIN":
                    text = font_big.render(f"체력 {current_spin_val} 회복", True, GRAY_BLADE)
                    canvas.blit(text, (roulette_rect.centerx - text.get_width()//2, roulette_rect.centery - text.get_height()//2))
                
                elif game_state == "HEAL_RESULT":
                    text = font_big.render(f"체력 {heal_amount} 회복!", True, YELLOW)
                    text2 = font.render("엔터를 눌러 전투로 복귀", True, WHITE)
                    canvas.blit(text, (roulette_rect.centerx - text.get_width()//2, roulette_rect.centery - 45))
                    canvas.blit(text2, (roulette_rect.centerx - text2.get_width()//2, roulette_rect.centery + 45))

        # --- 체력 UI 렌더링 (공통) ---
        hp_label = font.render("HP: ", True, RED)
        heart_surf = font.render("♥ ", True, RED)
        
        label_w = hp_label.get_width()
        heart_w = heart_surf.get_width()
        
        total_hp_width = label_w + heart_w * max_lives
        hp_x = WIDTH - total_hp_width - 20
        hp_y = 20
        
        canvas.blit(hp_label, (hp_x, hp_y))
        
        # 남은 체력 하트
        for i in range(lives):
            canvas.blit(heart_surf, (hp_x + label_w + i * heart_w, hp_y))
            
        # 피격 무적 깜빡임 효과
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