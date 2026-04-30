import os
import pygame
import sys

# Pygame 초기화
pygame.init()

# 첫 창을 띄우기 전에 모니터의 실제 최대 해상도를 미리 저장해둡니다.
info = pygame.display.Info()
DESKTOP_W, DESKTOP_H = info.current_w, info.current_h

# 처음에 창이 모니터 정중앙에 뜨도록 OS 환경변수 설정
os.environ['SDL_VIDEO_CENTERED'] = '1'

# 1. 논리적 해상도 (게임이 실제로 돌아가는 고정 크기 도화지)
LOGICAL_WIDTH, LOGICAL_HEIGHT = 1920, 1080
display_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))

# 2. 실제 물리적 창 크기 (기본값: 1600x900 창 모드)
current_width, current_height = 1600, 900
screen = pygame.display.set_mode((current_width, current_height))
pygame.display.set_caption("Grid Room Shooter - 30x30 Padded Room")
clock = pygame.time.Clock()

# ==================== 맵 크기 설정 (상하 여백 추가) ====================
GRID_COLS = 30 # 가로 30칸
GRID_ROWS = 30 # 세로 30칸
TILE_SIZE = 30 # 타일 하나당 30x30 픽셀로 축소

ROOM_WIDTH = GRID_COLS * TILE_SIZE   # 30 * 30 = 900 픽셀
ROOM_HEIGHT = GRID_ROWS * TILE_SIZE  # 30 * 30 = 900 픽셀

# 세로가 900이 되었으므로, 위아래로 90픽셀씩 여백이 생김 (1080 - 900) / 2
OFFSET_X = (LOGICAL_WIDTH - ROOM_WIDTH) // 2
OFFSET_Y = (LOGICAL_HEIGHT - ROOM_HEIGHT) // 2
# ===============================================================

# 전역 설정
config = {
    'display_mode': 'WINDOW',
    'volume': 50,
    'keys': {
        'UP': pygame.K_w, 'DOWN': pygame.K_s,
        'LEFT': pygame.K_a, 'RIGHT': pygame.K_d
    }
}

# 색상
BG_COLOR = (20, 20, 25)
ROOM_COLOR = (40, 40, 45)
GRID_COLOR = (60, 60, 70)
PLAYER_COLOR = (50, 150, 255)
BULLET_COLOR = (255, 230, 50)
ENEMY_COLOR = (255, 60, 60)
DOOR_OPEN_COLOR = (100, 255, 100)
DOOR_LOCKED_COLOR = (150, 50, 50)

# 방 상태
ROOM_WAITING = 0
ROOM_COMBAT = 1
ROOM_CLEARED = 2

# ==================== 마우스 좌표 보정 함수 ====================
def get_scaled_mouse_pos():
    mx, my = pygame.mouse.get_pos()
    scale_x = LOGICAL_WIDTH / current_width
    scale_y = LOGICAL_HEIGHT / current_height
    return int(mx * scale_x), int(my * scale_y)

# ==================== UI 클래스 ====================
class Button:
    def __init__(self, rel_x, y, w, h, text, font_size=30, base_col=(80, 80, 90), hover_col=(120, 120, 130)):
        self.rel_x = rel_x
        self.y = y
        self.w, self.h = w, h
        self.text = text
        self.font = pygame.font.SysFont("malgungothic", font_size)
        self.base_color = base_col
        self.hover_color = hover_col
        self.rect = pygame.Rect(0, y, w, h)

    def draw(self, surface, center_x, scaled_mouse_pos):
        self.rect.x = center_x + self.rel_x - self.w // 2
        color = self.hover_color if self.rect.collidepoint(scaled_mouse_pos) else self.base_color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        surface.blit(text_surf, (self.rect.centerx - text_surf.get_width()//2, self.rect.centery - text_surf.get_height()//2))

    def is_clicked(self, event, scaled_mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(scaled_mouse_pos):
                return True
        return False

# ==================== 게임 객체 클래스 ====================
class Player:
    def __init__(self):
        # 방 세로 크기가 줄어들었으므로 시작 위치를 조금 올려줌
        self.pos = pygame.math.Vector2(OFFSET_X + ROOM_WIDTH // 2, OFFSET_Y + ROOM_HEIGHT - 60)
        self.speed = 400
        self.radius = 12 # 타일(30)에 맞춰 캐릭터 크기 더 축소

    def move(self, dt):
        keys = pygame.key.get_pressed()
        direction = pygame.math.Vector2(0, 0)

        if keys[config['keys']['UP']]: direction.y -= 1
        if keys[config['keys']['DOWN']]: direction.y += 1
        if keys[config['keys']['LEFT']]: direction.x -= 1
        if keys[config['keys']['RIGHT']]: direction.x += 1

        if direction.length() > 0:
            direction = direction.normalize()
        
        self.pos += direction * self.speed * dt
        self.pos.x = max(OFFSET_X + self.radius, min(OFFSET_X + ROOM_WIDTH - self.radius, self.pos.x))
        self.pos.y = max(OFFSET_Y + self.radius, min(OFFSET_Y + ROOM_HEIGHT - self.radius, self.pos.y))

    def draw(self, surface):
        pygame.draw.circle(surface, PLAYER_COLOR, (int(self.pos.x), int(self.pos.y)), self.radius)

class Bullet:
    def __init__(self, x, y, target_x, target_y):
        self.pos = pygame.math.Vector2(x, y)
        self.speed = 800
        self.radius = 6 # 총알도 살짝 축소
        direction = pygame.math.Vector2(target_x - x, target_y - y)
        self.direction = direction.normalize() if direction.length() > 0 else pygame.math.Vector2(1, 0)

    def update(self, dt):
        self.pos += self.direction * self.speed * dt

    def draw(self, surface):
        pygame.draw.circle(surface, BULLET_COLOR, (int(self.pos.x), int(self.pos.y)), self.radius)

class Enemy:
    def __init__(self, x, y):
        self.pos = pygame.math.Vector2(x, y)
        self.speed = 180
        self.radius = 12 # 타일(30)에 맞춰 적 크기 축소
        self.hp = 5

    def update(self, dt, target_pos):
        direction = target_pos - self.pos
        if direction.length() > 0:
            direction = direction.normalize()
        self.pos += direction * self.speed * dt

    def draw(self, surface):
        pygame.draw.circle(surface, ENEMY_COLOR, (int(self.pos.x), int(self.pos.y)), self.radius)
        # 체력바 비율 조정
        pygame.draw.rect(surface, (255, 255, 255), (self.pos.x - 12, self.pos.y - 20, 24, 4))
        pygame.draw.rect(surface, ENEMY_COLOR, (self.pos.x - 12, self.pos.y - 20, 24 * (self.hp/5), 4))

# ==================== 화면 설정 함수 ====================
def update_display(mode):
    global screen, current_width, current_height
    config['display_mode'] = mode
    
    screen.fill((0, 0, 0))
    pygame.display.flip()

    if mode == 'FULLSCREEN':
        screen = pygame.display.set_mode((DESKTOP_W, DESKTOP_H), pygame.FULLSCREEN)
    elif mode == 'BORDERLESS':
        os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
        screen = pygame.display.set_mode((DESKTOP_W, DESKTOP_H), pygame.NOFRAME)
    else: # 'WINDOW'
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        if 'SDL_VIDEO_WINDOW_POS' in os.environ:
            del os.environ['SDL_VIDEO_WINDOW_POS']
        screen = pygame.display.set_mode((1600, 900))
    
    current_width, current_height = screen.get_width(), screen.get_height()

# ==================== 메인 함수 ====================
def main():
    global current_width, current_height, screen
    
    player = Player()
    bullets = []
    enemies = []
    room_state = ROOM_WAITING
    font = pygame.font.SysFont("malgungothic", 30)

    is_paused = False
    current_tab = "VIDEO"
    waiting_for_key = None

    btn_video = Button(-250, 200, 150, 50, "화면 설정")
    btn_audio = Button(0, 200, 150, 50, "음향 설정")
    btn_keys = Button(250, 200, 150, 50, "단축키")
    
    btn_window = Button(0, 320, 250, 50, "창 모드 (1600x900)")
    btn_borderless = Button(0, 390, 250, 50, "테두리 없는 전체화면")
    btn_fullscreen = Button(0, 460, 250, 50, "전체화면")

    btn_vol_down = Button(-100, 400, 60, 60, "-", 40)
    btn_vol_up = Button(100, 400, 60, 60, "+", 40)

    key_buttons = {
        'UP': Button(0, 320, 200, 50, ""),
        'DOWN': Button(0, 390, 200, 50, ""),
        'LEFT': Button(0, 460, 200, 50, ""),
        'RIGHT': Button(0, 530, 200, 50, "")
    }

    btn_quit = Button(0, 680, 200, 50, "게임 종료", base_col=(180, 50, 50), hover_col=(220, 80, 80))

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        
        scaled_mouse_pos = get_scaled_mouse_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                is_paused = not is_paused
                waiting_for_key = None

            if is_paused:
                if waiting_for_key and event.type == pygame.KEYDOWN:
                    if event.key != pygame.K_ESCAPE:
                        config['keys'][waiting_for_key] = event.key
                    waiting_for_key = None
                
                elif not waiting_for_key:
                    if btn_video.is_clicked(event, scaled_mouse_pos): current_tab = "VIDEO"
                    if btn_audio.is_clicked(event, scaled_mouse_pos): current_tab = "AUDIO"
                    if btn_keys.is_clicked(event, scaled_mouse_pos): current_tab = "KEYS"
                    if btn_quit.is_clicked(event, scaled_mouse_pos): running = False

                    if current_tab == "VIDEO":
                        if btn_window.is_clicked(event, scaled_mouse_pos): update_display('WINDOW')
                        if btn_borderless.is_clicked(event, scaled_mouse_pos): update_display('BORDERLESS')
                        if btn_fullscreen.is_clicked(event, scaled_mouse_pos): update_display('FULLSCREEN')
                    
                    elif current_tab == "AUDIO":
                        if btn_vol_down.is_clicked(event, scaled_mouse_pos): config['volume'] = max(0, config['volume'] - 10)
                        if btn_vol_up.is_clicked(event, scaled_mouse_pos): config['volume'] = min(100, config['volume'] + 10)
                    
                    elif current_tab == "KEYS":
                        for action, btn in key_buttons.items():
                            if btn.is_clicked(event, scaled_mouse_pos): waiting_for_key = action

            elif not is_paused and room_state in [ROOM_COMBAT, ROOM_CLEARED]:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = scaled_mouse_pos
                    bullets.append(Bullet(player.pos.x, player.pos.y, mx, my))

        if not is_paused:
            player.move(dt)

            if room_state == ROOM_WAITING:
                # 방 크기가 작아졌으니 진입 인식선도 살짝 위로 당겨줌
                if player.pos.y < OFFSET_Y + ROOM_HEIGHT - 200:
                    room_state = ROOM_COMBAT
                    enemies.append(Enemy(OFFSET_X + 150, OFFSET_Y + 150))
                    enemies.append(Enemy(OFFSET_X + ROOM_WIDTH - 150, OFFSET_Y + 150))
                    enemies.append(Enemy(OFFSET_X + ROOM_WIDTH // 2, OFFSET_Y + 250))
                    
            elif room_state == ROOM_COMBAT:
                for enemy in enemies: enemy.update(dt, player.pos)
                for bullet in bullets[:]:
                    bullet.update(dt)
                    if not (OFFSET_X <= bullet.pos.x <= OFFSET_X + ROOM_WIDTH and 
                            OFFSET_Y <= bullet.pos.y <= OFFSET_Y + ROOM_HEIGHT):
                        bullets.remove(bullet)
                        continue
                    
                    for enemy in enemies[:]:
                        if bullet.pos.distance_to(enemy.pos) < bullet.radius + enemy.radius:
                            enemy.hp -= 1
                            if bullet in bullets: bullets.remove(bullet)
                            if enemy.hp <= 0: enemies.remove(enemy)
                            break
                if len(enemies) == 0: room_state = ROOM_CLEARED
            elif room_state == ROOM_CLEARED:
                for bullet in bullets[:]: bullet.update(dt)

        display_surface.fill(BG_COLOR)
        
        pygame.draw.rect(display_surface, ROOM_COLOR, (OFFSET_X, OFFSET_Y, ROOM_WIDTH, ROOM_HEIGHT))
        
        for i in range(GRID_COLS + 1):
            x_pos = OFFSET_X + i * TILE_SIZE
            pygame.draw.line(display_surface, GRID_COLOR, (x_pos, OFFSET_Y), (x_pos, OFFSET_Y + ROOM_HEIGHT), 1)
        
        for i in range(GRID_ROWS + 1):
            y_pos = OFFSET_Y + i * TILE_SIZE
            pygame.draw.line(display_surface, GRID_COLOR, (OFFSET_X, y_pos), (OFFSET_X + ROOM_WIDTH, y_pos), 1)

        door_color = DOOR_OPEN_COLOR if room_state in [ROOM_WAITING, ROOM_CLEARED] else DOOR_LOCKED_COLOR
        pygame.draw.rect(display_surface, door_color, (OFFSET_X + ROOM_WIDTH // 2 - 60, OFFSET_Y, 120, 20))
        pygame.draw.rect(display_surface, door_color, (OFFSET_X + ROOM_WIDTH // 2 - 60, OFFSET_Y + ROOM_HEIGHT - 20, 120, 20))

        if room_state == ROOM_COMBAT:
            for enemy in enemies: enemy.draw(display_surface)
        for bullet in bullets: bullet.draw(display_surface)
        player.draw(display_surface)

        state_text = "위로 이동하여 방에 진입하세요" if room_state == ROOM_WAITING else (f"전투 중! 적: {len(enemies)}" if room_state == ROOM_COMBAT else "방 클리어!")
        display_surface.blit(font.render(state_text, True, (255, 255, 255)), (20, 20))
        display_surface.blit(font.render("[ESC] 설정 및 일시정지", True, (150, 150, 150)), (20, 60))

        if is_paused:
            overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            display_surface.blit(overlay, (0, 0))

            center_x = LOGICAL_WIDTH // 2
            panel_rect = pygame.Rect(center_x - 350, 150, 700, 600)
            pygame.draw.rect(display_surface, (40, 40, 45), panel_rect, border_radius=15)
            pygame.draw.rect(display_surface, (200, 200, 200), panel_rect, width=3, border_radius=15)

            btn_video.draw(display_surface, center_x, scaled_mouse_pos)
            btn_audio.draw(display_surface, center_x, scaled_mouse_pos)
            btn_keys.draw(display_surface, center_x, scaled_mouse_pos)
            btn_quit.draw(display_surface, center_x, scaled_mouse_pos)

            if current_tab == "VIDEO":
                btn_window.draw(display_surface, center_x, scaled_mouse_pos)
                btn_borderless.draw(display_surface, center_x, scaled_mouse_pos)
                btn_fullscreen.draw(display_surface, center_x, scaled_mouse_pos)
            elif current_tab == "AUDIO":
                vol_text = font.render(f"마스터 볼륨: {config['volume']}%", True, (255, 255, 255))
                display_surface.blit(vol_text, (center_x - vol_text.get_width()//2, 330))
                btn_vol_down.draw(display_surface, center_x, scaled_mouse_pos)
                btn_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
            elif current_tab == "KEYS":
                for action, btn in key_buttons.items():
                    key_name = pygame.key.name(config['keys'][action]).upper()
                    if waiting_for_key == action:
                        btn.text = "[ 입력 대기중 ]"
                        btn.base_color = (200, 100, 100)
                    else:
                        btn.text = f"{key_name}"
                        btn.base_color = (80, 80, 90)
                    label_surf = font.render(f"이동 ({action}):", True, (255, 255, 255))
                    display_surface.blit(label_surf, (center_x - 180, btn.rect.y + 5))
                    btn.draw(display_surface, center_x, scaled_mouse_pos)

        scaled_surface = pygame.transform.scale(display_surface, (current_width, current_height))
        screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()