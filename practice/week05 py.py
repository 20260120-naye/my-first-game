import pygame
import random
import sys
import math # 각도 및 대각선 계산을 위해 추가

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

# 캐릭터 전용 기본 색상
CHAR_SKIN = (255, 218, 185)
CHAR_HAIR = (147, 112, 219)
CHAR_DRESS = (255, 182, 193)
CHAR_EYE = (50, 50, 50)
CHAR_BLUSH = (255, 160, 160)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Undertale Knife Pattern Upgrade")

canvas = pygame.Surface((WIDTH, HEIGHT)) 
clock = pygame.time.Clock()

font = get_korean_font(36)
font_big = get_korean_font(72)
font_mid = get_korean_font(50) 
font_sub = get_korean_font(30)    
font_small = get_korean_font(24) 

# --- 베이스 칼 이미지 생성 함수 ---
# 모든 방향과 각도로 회전시키기 위해 기본(위쪽을 향하는) 칼 이미지를 생성합니다.
def create_base_knife():
    w, h = 18, 55
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    x, y = 0, 0
    pygame.draw.rect(surf, BROWN_HANDLE, (x + w*0.3, y + h*0.7, w*0.4, h*0.3))
    pygame.draw.rect(surf, GRAY_HILT, (x, y + h*0.6, w, h*0.1))
    blade_points = [(x + w*0.1, y + h*0.6), (x + w*0.9, y + h*0.6), (x + w/2, y)]
    pygame.draw.polygon(surf, GRAY_BLADE, blade_points)
    blood_points = [(x + w*0.25, y + h*0.35), (x + w*0.75, y + h*0.35), (x + w/2, y)]
    pygame.draw.polygon(surf, BLOOD_RED, blood_points)
    pygame.draw.rect(surf, BLOOD_RED, (x + w*0.45, y + h*0.3, w*0.1, h*0.25))
    return surf

BASE_KNIFE_IMG = create_base_knife()

# --- 전투 박스 (아레나) 설정 ---
ARENA_W, ARENA_H = 250, 250 
ARENA_X = (WIDTH - ARENA_W) // 2
ARENA_Y = (HEIGHT - ARENA_H) // 2
arena_rect = pygame.Rect(ARENA_X, ARENA_Y, ARENA_W, ARENA_H)

MENU_BOX_RECT = pygame.Rect(50, HEIGHT - 350, WIDTH - 100, 200)
BORDER_THICKNESS = 5 

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

# 공격 패턴의 칼 그리기 함수 (회전 기능 추가)
def draw_realistic_knife(surf, rect, direction, alpha=255):
    # direction이 문자열이면 기본 각도로 매핑, 숫자(float/int)면 직접 각도로 사용
    angle = 0
    if direction == 'up': angle = 0
    elif direction == 'down': angle = 180
    elif direction == 'left': angle = 90
    elif direction == 'right': angle = -90
    elif isinstance(direction, (int, float)): angle = direction

    img = BASE_KNIFE_IMG.copy()
    if alpha < 255:
        img.set_alpha(alpha)

    # 지정된 각도만큼 이미지 회전
    rotated_img = pygame.transform.rotate(img, angle)
    # 기존 rect의 중앙을 기준으로 회전된 이미지 위치 재조정
    new_rect = rotated_img.get_rect(center=rect.center)
    surf.blit(rotated_img, new_rect.topleft)

# --- 귀여운 캐릭터 그리기 함수 ---
def draw_cute_girl(surf, cx, cy, is_happy=False, is_dead=False, is_hurt=False):
    skin = (255, 100, 100) if is_hurt else CHAR_SKIN
    hair = (200, 50, 50) if is_hurt else CHAR_HAIR
    dress = (255, 50, 50) if is_hurt else CHAR_DRESS
    eye_color = RED if is_hurt else CHAR_EYE
    blush = RED if is_hurt else CHAR_BLUSH

    pygame.draw.ellipse(surf, hair, (cx - 70, cy - 60, 140, 160))
    pygame.draw.rect(surf, skin, (cx - 25, cy + 90, 12, 60))
    pygame.draw.rect(surf, skin, (cx + 13, cy + 90, 12, 60))
    pygame.draw.ellipse(surf, eye_color, (cx - 30, cy + 140, 20, 15))
    pygame.draw.ellipse(surf, eye_color, (cx + 10, cy + 140, 20, 15))
    pygame.draw.polygon(surf, dress, [(cx, cy + 20), (cx - 70, cy + 110), (cx + 70, cy + 110)])
    pygame.draw.polygon(surf, WHITE, [(cx - 70, cy + 110), (cx + 70, cy + 110), (cx, cy + 95)])
    pygame.draw.line(surf, skin, (cx - 25, cy + 40), (cx - 55, cy + 80), 10)
    pygame.draw.line(surf, skin, (cx + 25, cy + 40), (cx + 55, cy + 80), 10)

    kw, kh = 18, 55 
    left_knife_rect = pygame.Rect(0, 0, kw, kh)
    left_knife_rect.center = (cx - 55, cy + 50)
    right_knife_rect = pygame.Rect(0, 0, kw, kh)
    right_knife_rect.center = (cx + 55, cy + 50)

    draw_realistic_knife(surf, left_knife_rect, 'up')
    draw_realistic_knife(surf, right_knife_rect, 'up')

    pygame.draw.circle(surf, skin, (cx, cy), 50)
    pygame.draw.polygon(surf, hair, [(cx - 50, cy - 10), (cx - 60, cy - 50), (cx - 10, cy - 50)])
    pygame.draw.polygon(surf, hair, [(cx + 50, cy - 10), (cx + 60, cy - 50), (cx + 10, cy - 50)])
    pygame.draw.polygon(surf, hair, [(cx - 20, cy), (cx - 30, cy - 60), (cx + 30, cy - 60), (cx + 20, cy)])
    
    if is_dead:
        pygame.draw.line(surf, eye_color, (cx - 24, cy - 5), (cx - 12, cy + 7), 5)
        pygame.draw.line(surf, eye_color, (cx - 24, cy + 7), (cx - 12, cy - 5), 5)
        pygame.draw.line(surf, eye_color, (cx + 12, cy - 5), (cx + 24, cy + 7), 5)
        pygame.draw.line(surf, eye_color, (cx + 12, cy + 7), (cx + 24, cy - 5), 5)
        pygame.draw.line(surf, eye_color, (cx - 5, cy + 25), (cx + 5, cy + 25), 3)
    elif is_happy:
        for eye_x in [cx - 18, cx + 18]:
            eye_y = cy + 5
            pygame.draw.circle(surf, RED, (eye_x - 3, eye_y - 2), 4)
            pygame.draw.circle(surf, RED, (eye_x + 3, eye_y - 2), 4)
            pygame.draw.polygon(surf, RED, [(eye_x - 7, eye_y), (eye_x + 7, eye_y), (eye_x, eye_y + 7)])
            pygame.draw.circle(surf, WHITE, (eye_x - 2, eye_y - 2), 1)
    else:
        pygame.draw.circle(surf, eye_color, (cx - 18, cy + 5), 6)
        pygame.draw.circle(surf, eye_color, (cx + 18, cy + 5), 6)
        pygame.draw.circle(surf, WHITE, (cx - 19, cy + 3), 2)
        pygame.draw.circle(surf, WHITE, (cx + 17, cy + 3), 2)
        
    pygame.draw.ellipse(surf, blush, (cx - 35, cy + 15, 16, 8))
    pygame.draw.ellipse(surf, blush, (cx + 19, cy + 15, 16, 8))
    
    if not is_dead:
        pygame.draw.polygon(surf, eye_color, [(cx - 6, cy + 25), (cx + 6, cy + 25), (cx, cy + 32)])
        pygame.draw.polygon(surf, RED, [(cx, cy + 45), (cx - 20, cy + 35), (cx - 20, cy + 55)])
        pygame.draw.polygon(surf, RED, [(cx, cy + 45), (cx + 20, cy + 35), (cx + 20, cy + 55)])
        pygame.draw.circle(surf, YELLOW, (cx, cy + 45), 6)

def spawn_knife(side_override=None):
    side = side_override if side_override is not None else random.randint(0, 3)
    speed = random.randint(7, 12) 
    
    K_LONG = 55
    K_SHORT = 18

    if side == 0:
        x = random.randint(arena_rect.left, arena_rect.right - K_SHORT)
        y = -100
        return pygame.Rect(x, y, K_SHORT, K_LONG), 0, speed, 'down', 0
    elif side == 1: 
        x = random.randint(arena_rect.left, arena_rect.right - K_SHORT)
        y = HEIGHT + 100
        return pygame.Rect(x, y, K_SHORT, K_LONG), 0, -speed, 'up', 0
    elif side == 2: 
        x = -100
        y = random.randint(arena_rect.top, arena_rect.bottom - K_SHORT)
        return pygame.Rect(x, y, K_LONG, K_SHORT), speed, 0, 'right', 0
    else: 
        x = WIDTH + 100
        y = random.randint(arena_rect.top, arena_rect.bottom - K_SHORT)
        return pygame.Rect(x, y, K_LONG, K_SHORT), -speed, 0, 'left', 0

def game_over_screen():
    screen.fill(BLACK)
    text1 = font_big.render("GAME OVER", True, RED)
    text2 = font.render("다시 시작 'R'", True, WHITE)
    text3 = font.render("종료 'Q'", True, GRAY)
    
    screen.blit(text1, (WIDTH // 2 - text1.get_width() // 2, HEIGHT // 2 - 80))
    screen.blit(text2, (WIDTH // 2 - text2.get_width() // 2, HEIGHT // 2 + 10))
    screen.blit(text3, (WIDTH // 2 - text3.get_width() // 2, HEIGHT // 2 + 70))
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
    
    # 패턴 2에서 십자/대각선을 번갈아 스폰하기 위한 변수
    pattern2_mode = "cross" 
    
    shake_timer = 0
    enemy_hit_timer = 0

    spin_timer = 0
    spin_duration = 120 
    current_spin_val = 1
    heal_amount = 0

    affection = 0 
    max_affection = 3 
    
    yandere_hp = 3
    max_yandere_hp = 3

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
                        if menu_index == 2: game_state = "HEAL_WAIT"
                        elif menu_index == 1: game_state = "LOVE_WAIT" 
                        elif menu_index == 0: game_state = "ATTACK_WAIT"
                            
                elif game_state == "ATTACK_WAIT":
                    if e.key == pygame.K_z or e.key == pygame.K_RETURN:
                        yandere_hp -= 1
                        enemy_hit_timer = 20 
                        game_state = "ATTACK_RESULT"
                    elif e.key == pygame.K_ESCAPE:
                        game_state = "MENU"
                        
                elif game_state == "ATTACK_RESULT":
                    if e.key == pygame.K_z or e.key == pygame.K_RETURN:
                        if yandere_hp <= 0:
                            game_state = "BAD_ENDING"
                        else:
                            game_state = "DODGE"
                            pattern_timer = 0
                            player.centerx, player.centery = arena_rect.centerx, arena_rect.centery
                            knives.clear()
                            
                            current_pattern += 1
                            if current_pattern > 8: current_pattern = 1
                            
                elif game_state == "LOVE_WAIT":
                    if e.key == pygame.K_z or e.key == pygame.K_RETURN:
                        affection += 1 
                        game_state = "LOVE_RESULT"
                    elif e.key == pygame.K_ESCAPE:
                        game_state = "MENU" 
                        
                elif game_state == "LOVE_RESULT":
                    if e.key == pygame.K_z or e.key == pygame.K_RETURN:
                        if affection >= max_affection:
                            game_state = "TRUE_ENDING" 
                        else:
                            game_state = "DODGE"
                            pattern_timer = 0
                            player.centerx, player.centery = arena_rect.centerx, arena_rect.centery
                            knives.clear()
                            
                            current_pattern += 1
                            if current_pattern > 8: current_pattern = 1
                            
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
                        player.centerx, player.centery = arena_rect.centerx, arena_rect.centery
                        knives.clear()
                        
                        current_pattern += 1
                        if current_pattern > 8: current_pattern = 1
                        
                elif game_state in ["TRUE_ENDING", "BAD_ENDING"]:
                    if e.key == pygame.K_r: 
                        main()
                        return
                    elif e.key == pygame.K_q: 
                        pygame.quit()
                        sys.exit()

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
            spawn_timer += 1

            # ================= [공격 패턴 구현 구간] =================
            if current_pattern == 1: 
                if spawn_timer >= 18:
                    spawn_timer = 0
                    rect, dx, dy, direction, delay = spawn_knife()
                    knives.append([rect, dx, dy, direction, delay])
                    
           # elif current_pattern == 2:
                if spawn_timer >= 50:
                    spawn_timer = 0
                    speed = 18
                    dist = 220 
                    delay_frames = 40 
                    px = player.centerx
                    py = player.centery

                    if pattern2_mode == "cross":
                        angles = [0, 90, 180, 270] 
                        pattern2_mode = "diagonal"
                    else:
                        angles = [45, 135, 225, 315] 
                        pattern2_mode = "cross"

                    for ang in angles:
                        rad = math.radians(ang)
                        
                        sx = px + math.cos(rad) * dist
                        sy = py - math.sin(rad) * dist 
                        
                        dx = -math.cos(rad) * speed
                        dy = math.sin(rad) * speed
                        
                        face_angle = math.degrees(math.atan2(-dx, -dy))
                        
                        rect = pygame.Rect(0, 0, 18, 18)
                        rect.center = (int(sx), int(sy))
                        
                        knives.append([rect, dx, dy, face_angle, delay_frames, sx, sy])
                    
           # elif current_pattern == 3: 
                if spawn_timer >= 40: 
                    spawn_timer = 0
                    speed = 6 
                    K_LONG = 55
                    K_SHORT = 18
                    delay_frames = 30 
                    
                    num_knives = ARENA_W // K_SHORT + 1
                    
                    gap_start = random.randint(0, num_knives - 4)
                    
                    for i in range(num_knives):
                        if gap_start <= i <= gap_start + 2:
                            continue
                            
                        sx = ARENA_X + (i * K_SHORT)
                        sy = ARENA_Y + ARENA_H + (K_LONG // 2) 
                        
                        dx = 0
                        dy = -speed
                        face_angle = 0 
                        
                        rect = pygame.Rect(0, 0, K_SHORT, K_LONG)
                        rect.center = (int(sx), int(sy))
                        
                        knives.append([rect, dx, dy, face_angle, delay_frames, sx, sy])
            
            # elif current_pattern == 4:
                # 유튜브 3:34~3:41 구간 - 육각형 포위망 조여오기 패턴
                current_spawn_rate = 60
                
                if spawn_timer >= current_spawn_rate:
                    spawn_timer = 0
                    speed = 10          
                    dist = 220          
                    delay_frames = 25   
                    
                    px = player.centerx
                    py = player.centery
                    
                    base_angle = random.randint(0, 359)
                    
                    for i in range(6): 
                        ang = base_angle + (i * 60)
                        rad = math.radians(ang)
                        
                        sx = px + math.cos(rad) * dist
                        sy = py - math.sin(rad) * dist
                        
                        dx = -math.cos(rad) * speed
                        dy = math.sin(rad) * speed
                        
                        face_angle = math.degrees(math.atan2(-dx, -dy))
                        
                        rect = pygame.Rect(0, 0, 18, 18)
                        rect.center = (int(sx), int(sy))
                        
                        alpha = 255      
                        life_timer = 0   
                        
                        knives.append([rect, dx, dy, face_angle, delay_frames, sx, sy, alpha, life_timer])

            elif current_pattern == 5:
                # 유튜브 2:47~2:51 - 아스고어 조여오는 원형 패턴 (빈틈 뚫린 포위망)
                if spawn_timer >= 45: 
                    spawn_timer = 0
                    speed = 6  
                    dist = 400 # 화면 바깥쪽 생성
                    delay_frames = 0 
                    
                    # 아레나 정중앙을 타겟
                    cx = arena_rect.centerx
                    cy = arena_rect.centery
                    
                    num_knives = 20 # 원을 이루는 총 칼 개수
                    gap_size = 4 # 안전지대 구멍 크기
                    gap_start = random.randint(0, num_knives - 1) 
                    
                    gap_indices = [(gap_start + j) % num_knives for j in range(gap_size)]
                    
                    for i in range(num_knives):
                        if i in gap_indices:
                            continue 
                            
                        ang = i * (360 / num_knives)
                        rad = math.radians(ang)
                        
                        # 생성 좌표
                        sx = cx + math.cos(rad) * dist
                        sy = cy - math.sin(rad) * dist
                        
                        # 방향 벡터
                        dx = -math.cos(rad) * speed
                        dy = math.sin(rad) * speed
                        
                        face_angle = math.degrees(math.atan2(-dx, -dy))
                        
                        rect = pygame.Rect(0, 0, 18, 18)
                        rect.center = (int(sx), int(sy))
                        
                        alpha = 255      
                        life_timer = 0 # 이동한 시간을 잴 타이머
                        
                        knives.append([rect, dx, dy, face_angle, delay_frames, sx, sy, alpha, life_timer])
                        
            elif current_pattern == 6: pass
            elif current_pattern == 7: pass
            elif current_pattern == 8: pass
            # =========================================================

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
            delay = knife[4] if len(knife) > 4 else 0
            is_active = True
            
            if delay > 0:
                knife[4] -= 1
                is_active = False 
            else:
                if len(knife) > 5:
                    knife[5] += dx 
                    knife[6] += dy 
                    rect.centerx = int(knife[5])
                    rect.centery = int(knife[6])
                else:
                    rect.x += dx
                    rect.y += dy

                # === [추가 및 변경된 부분: 소멸 로직 수정] ===
                if len(knife) > 7: 
                    knife[8] += 1  # life_timer 증가

                    threshold = 0
                    if current_pattern == 4:
                        threshold = 22 # 육각형 패턴
                    elif current_pattern == 5:
                        threshold = 67 # 400(거리) / 6(속도) = 66.6... (원형 패턴 정중앙 도착 시점)

                    if threshold > 0 and knife[8] >= threshold:
                        if current_pattern == 5:
                            # 5번 패턴은 겹치는 즉시 사라지게 (리스트에 추가 안 함)
                            continue 
                        else:
                            # 4번 패턴은 기존처럼 빠르게 페이드아웃
                            knife[7] -= 50 
                            if knife[7] <= 0:
                                continue 

            knife_hitbox = rect 
            
            if game_state == "DODGE" and invincible == 0 and is_active and player_hitbox.colliderect(knife_hitbox):
                lives -= 1
                invincible = 45
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
                delay = knife[4] if len(knife) > 4 else 0
                alpha = knife[7] if len(knife) > 7 else 255 
                
                if delay > 0:
                    blink_speed = 2 if delay < 15 else 5
                    if (delay // blink_speed) % 2 == 0:
                        draw_realistic_knife(canvas, knife[0], knife[3], alpha) 
                else:
                    draw_realistic_knife(canvas, knife[0], knife[3], alpha) 
                
            if invincible == 0 or (invincible // 5) % 2 == 0:
                pygame.draw.rect(canvas, RED, player)
                
            pattern_text = font_small.render(f"패턴 {current_pattern}", True, GRAY)
            canvas.blit(pattern_text, (arena_rect.x, arena_rect.y - 30))
                
        elif game_state in ["MENU", "HEAL_WAIT", "HEAL_SPIN", "HEAL_RESULT", "LOVE_WAIT", "LOVE_RESULT", "ATTACK_WAIT", "ATTACK_RESULT"]:
            draw_x = WIDTH // 2
            draw_y = 170
            is_hurt = False
            
            if enemy_hit_timer > 0:
                draw_x += random.randint(-8, 8)
                draw_y += random.randint(-8, 8)
                is_hurt = True
                enemy_hit_timer -= 1

            draw_cute_girl(canvas, draw_x, draw_y, is_hurt=is_hurt)

            pygame.draw.rect(canvas, WHITE, MENU_BOX_RECT, BORDER_THICKNESS)
            
            line1_text = font.render("상태창", True, WHITE)
            canvas.blit(line1_text, (MENU_BOX_RECT.x + 30, MENU_BOX_RECT.y + 30))

            info_move_text = font_small.render("이동: A(좌) D(우)", True, GRAY)
            info_select_text = font_small.render("선택: Enter", True, GRAY)
            
            move_y = MENU_BOX_RECT.bottom - 75
            select_y = MENU_BOX_RECT.bottom - 45
            
            canvas.blit(info_move_text, (MENU_BOX_RECT.x + 30, move_y))
            canvas.blit(info_select_text, (MENU_BOX_RECT.x + 30, select_y))

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

        if game_state in ["HEAL_WAIT", "HEAL_SPIN", "HEAL_RESULT", "LOVE_WAIT", "LOVE_RESULT", "ATTACK_WAIT", "ATTACK_RESULT"]:
            roulette_w, roulette_h = 450, 200
            roulette_rect = pygame.Rect(WIDTH//2 - roulette_w//2, HEIGHT//2 - roulette_h//2, roulette_w, roulette_h)
            
            pygame.draw.rect(canvas, BLACK, roulette_rect)
            pygame.draw.rect(canvas, WHITE, roulette_rect, BORDER_THICKNESS)
            
            if game_state == "ATTACK_WAIT":
                text1 = font_sub.render("얀데레를 공격 하시겠습니까?", True, RED) 
                text2 = font_small.render("확인: Enter   취소: ESC", True, WHITE)
                gap = 15
                total_h = text1.get_height() + gap + text2.get_height()
                start_y = roulette_rect.centery - total_h // 2
                canvas.blit(text1, (roulette_rect.centerx - text1.get_width()//2, start_y))
                canvas.blit(text2, (roulette_rect.centerx - text2.get_width()//2, start_y + text1.get_height() + gap))
                
            elif game_state == "ATTACK_RESULT":
                text1 = font_sub.render("얀데레를 공격했습니다!", True, RED)
                text2 = font_small.render(f"얀데레 체력: {yandere_hp} / {max_yandere_hp}", True, YELLOW)
                text3 = font_small.render("엔터(Enter)를 눌러 복귀", True, GRAY_BLADE)
                gap = 15
                total_h = text1.get_height() + gap + text2.get_height() + gap + text3.get_height()
                start_y = roulette_rect.centery - total_h // 2
                canvas.blit(text1, (roulette_rect.centerx - text1.get_width()//2, start_y))
                canvas.blit(text2, (roulette_rect.centerx - text2.get_width()//2, start_y + text1.get_height() + gap))
                canvas.blit(text3, (roulette_rect.centerx - text3.get_width()//2, start_y + text1.get_height() + gap*2 + text2.get_height()))
            
            elif game_state == "LOVE_WAIT":
                text1_a = font_sub.render("얀데레에게 사랑을", True, CHAR_DRESS) 
                text1_b = font_sub.render("보내겠습니까?", True, CHAR_DRESS) 
                text2 = font_small.render("확인: Enter   취소: ESC", True, WHITE)
                gap = 15
                total_h = text1_a.get_height() + gap + text1_b.get_height() + gap + text2.get_height()
                start_y = roulette_rect.centery - total_h // 2
                canvas.blit(text1_a, (roulette_rect.centerx - text1_a.get_width()//2, start_y))
                canvas.blit(text1_b, (roulette_rect.centerx - text1_b.get_width()//2, start_y + text1_a.get_height() + gap))
                canvas.blit(text2, (roulette_rect.centerx - text2.get_width()//2, start_y + text1_a.get_height() + text1_b.get_height() + gap * 2))
            
            elif game_state == "LOVE_RESULT":
                text1 = font_sub.render("얀데레에게 사랑을 보냈습니다!", True, RED)
                text2 = font_small.render(f"현재 호감도: {affection} / {max_affection}", True, YELLOW)
                text3 = font_small.render("엔터(Enter)를 눌러 복귀", True, GRAY_BLADE)
                gap = 15
                total_h = text1.get_height() + gap + text2.get_height() + gap + text3.get_height()
                start_y = roulette_rect.centery - total_h // 2
                canvas.blit(text1, (roulette_rect.centerx - text1.get_width()//2, start_y))
                canvas.blit(text2, (roulette_rect.centerx - text2.get_width()//2, start_y + text1.get_height() + gap))
                canvas.blit(text3, (roulette_rect.centerx - text3.get_width()//2, start_y + text1.get_height() + gap*2 + text2.get_height()))

            elif game_state == "HEAL_WAIT":
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

        elif game_state == "TRUE_ENDING":
            draw_cute_girl(canvas, WIDTH // 2, HEIGHT // 2 - 100, is_happy=True)
            ending_box = pygame.Rect(100, HEIGHT - 280, WIDTH - 200, 200)
            pygame.draw.rect(canvas, BLACK, ending_box)
            pygame.draw.rect(canvas, CHAR_DRESS, ending_box, BORDER_THICKNESS) 
            text1 = font.render("그녀는 당신의 사랑을 받아들였습니다...", True, CHAR_DRESS)
            text2 = font_sub.render("얀데레의 공격이 멈췄습니다. [ 해피 엔딩 ♥ ]", True, WHITE)
            text3 = font_small.render("다시 시작 'R'   /   종료 'Q'", True, GRAY)
            gap = 20
            total_h = text1.get_height() + gap + text2.get_height() + gap + text3.get_height()
            start_y = ending_box.centery - (total_h // 2)
            canvas.blit(text1, (ending_box.centerx - text1.get_width() // 2, start_y))
            canvas.blit(text2, (ending_box.centerx - text2.get_width() // 2, start_y + text1.get_height() + gap))
            canvas.blit(text3, (ending_box.centerx - text3.get_width() // 2, start_y + text1.get_height() + gap * 2 + text2.get_height()))
            
        elif game_state == "BAD_ENDING":
            draw_cute_girl(canvas, WIDTH // 2, HEIGHT // 2 - 100, is_dead=True)
            ending_box = pygame.Rect(100, HEIGHT - 280, WIDTH - 200, 200)
            pygame.draw.rect(canvas, BLACK, ending_box)
            pygame.draw.rect(canvas, RED, ending_box, BORDER_THICKNESS) 
            text1 = font.render("당신은 그녀를 쓰러뜨렸습니다...", True, RED)
            text2 = font_sub.render("하지만 뭔가 마음이 편치 않습니다. [ 배드 엔딩 ]", True, WHITE)
            text3 = font_small.render("다시 시작 'R'   /   종료 'Q'", True, GRAY)
            gap = 20
            total_h = text1.get_height() + gap + text2.get_height() + gap + text3.get_height()
            start_y = ending_box.centery - (total_h // 2)
            canvas.blit(text1, (ending_box.centerx - text1.get_width() // 2, start_y))
            canvas.blit(text2, (ending_box.centerx - text2.get_width() // 2, start_y + text1.get_height() + gap))
            canvas.blit(text3, (ending_box.centerx - text3.get_width() // 2, start_y + text1.get_height() + gap * 2 + text2.get_height()))

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