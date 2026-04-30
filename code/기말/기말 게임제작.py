import os
import pygame
import sys
import json

# Pygame 초기화
pygame.init()

# ==================== 한글 폰트 자동 탐색 함수 ====================
def get_korean_font(size, bold=False):
    font_names = ['malgungothic', 'apple sd gothic neo', 'applegothic', 'nanumgothic', 'dotum', 'gulim']
    for name in font_names:
        if pygame.font.match_font(name):
            return pygame.font.SysFont(name, size, bold=bold)
    return pygame.font.SysFont(None, size, bold=bold)

# 첫 창을 띄우기 전에 모니터의 실제 최대 해상도를 미리 저장해둡니다.
info = pygame.display.Info()
DESKTOP_W, DESKTOP_H = info.current_w, info.current_h

# 처음에 창이 모니터 정중앙에 뜨도록 OS 환경변수 설정
os.environ['SDL_VIDEO_CENTERED'] = '1'

# 1. 논리적 해상도 (게임이 실제로 돌아가는 고정 크기 도화지)
LOGICAL_WIDTH, LOGICAL_HEIGHT = 1920, 1080
display_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))

# 2. 실제 물리적 창 크기 초기 설정
current_width, current_height = 1600, 900
screen = pygame.display.set_mode((current_width, current_height))
pygame.display.set_caption("단죄의 시간 (Time of Condemnation)")
clock = pygame.time.Clock()

# ==================== 게임 전체 상태 정의 ====================
APP_MAIN_MENU = 0
APP_PLAYING = 1

# ==================== 맵 크기 설정 ====================
GRID_COLS = 30
GRID_ROWS = 30
TILE_SIZE = 30

ROOM_WIDTH = GRID_COLS * TILE_SIZE   # 900 픽셀
ROOM_HEIGHT = GRID_ROWS * TILE_SIZE  # 900 픽셀

OFFSET_X = (LOGICAL_WIDTH - ROOM_WIDTH) // 2
OFFSET_Y = (LOGICAL_HEIGHT - ROOM_HEIGHT) // 2

# ==================== 설정(Config) 시스템 ====================
CONFIG_FILE = "settings.json"

config = {
    'display_mode': 'WINDOW',
    'volume': 50,
    'combat_volume': 50,
    'voice_volume': 50,
    'keys': {
        'UP': pygame.K_w, 'DOWN': pygame.K_s,
        'LEFT': pygame.K_a, 'RIGHT': pygame.K_d
    }
}

def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # 딕셔너리 업데이트 (기본값 누락 방지)
                for k, v in loaded.items():
                    if isinstance(v, dict) and k in config:
                        config[k].update(v)
                    else:
                        config[k] = v
        except:
            pass

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

# ==================== 세이브/로드 시스템 ====================
SAVE_FILE = "save_data.json"

def get_save_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"slot_1": None, "slot_2": None, "slot_3": None}

def write_save_data(data):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

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
        self.font = get_korean_font(font_size)
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
        self.pos = pygame.math.Vector2(OFFSET_X + ROOM_WIDTH // 2, OFFSET_Y + ROOM_HEIGHT - 60)
        self.speed = 400
        self.radius = 12

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
        self.radius = 6
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
        self.radius = 12
        self.hp = 5

    def update(self, dt, target_pos):
        direction = target_pos - self.pos
        if direction.length() > 0:
            direction = direction.normalize()
        self.pos += direction * self.speed * dt

    def draw(self, surface):
        pygame.draw.circle(surface, ENEMY_COLOR, (int(self.pos.x), int(self.pos.y)), self.radius)
        pygame.draw.rect(surface, (255, 255, 255), (self.pos.x - 12, self.pos.y - 20, 24, 4))
        pygame.draw.rect(surface, ENEMY_COLOR, (self.pos.x - 12, self.pos.y - 20, 24 * (self.hp/5), 4))

# ==================== 화면 설정 함수 ====================
def update_display(mode):
    global screen, current_width, current_height
    config['display_mode'] = mode
    save_config() # 화면 모드가 변경되면 즉시 저장
    
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
    
    # 1. 설정 불러오기 및 디스플레이 적용
    load_config()
    update_display(config['display_mode'])
    
    app_state = APP_MAIN_MENU 
    
    player = Player()
    bullets = []
    enemies = []
    room_state = ROOM_WAITING
    saves_data = get_save_data()
    
    current_play_time = 0.0
    
    title_font = get_korean_font(100, bold=True)
    font = get_korean_font(30)
    large_font = get_korean_font(40)

    current_overlay = None
    current_tab = "VIDEO"
    waiting_for_key = None
    
    # 팝업 상태 관리
    confirm_delete_slot = None
    confirm_save_slot = None

    # --- 메인 메뉴 버튼 ---
    menu_btn_start = Button(-710, 660, 200, 60, "새로 시작")
    menu_btn_continue = Button(-710, 740, 200, 60, "이어하기")
    menu_btn_settings = Button(-710, 820, 200, 60, "설정")
    menu_btn_quit = Button(-710, 900, 200, 60, "게임 종료", base_col=(180, 50, 50), hover_col=(220, 80, 80))

    # --- 설정창 탭 선택 버튼 ---
    btn_video = Button(-250, 200, 150, 50, "화면 설정")
    btn_audio = Button(0, 200, 150, 50, "음향 설정")
    btn_keys = Button(250, 200, 150, 50, "단축키")
    
    # [1] 화면 탭 버튼
    btn_window = Button(0, 320, 300, 50, "창 모드 (1600x900)")
    btn_borderless = Button(0, 390, 300, 50, "테두리 없는 전체화면")
    btn_fullscreen = Button(0, 460, 300, 50, "독점 전체화면")
    
    # [2] 음향 탭 버튼
    btn_vol_down = Button(-100, 310, 60, 60, "-", 40)
    btn_vol_up = Button(100, 310, 60, 60, "+", 40)

    btn_combat_vol_down = Button(-100, 440, 60, 60, "-", 40)
    btn_combat_vol_up = Button(100, 440, 60, 60, "+", 40)

    btn_voice_vol_down = Button(-100, 570, 60, 60, "-", 40)
    btn_voice_vol_up = Button(100, 570, 60, 60, "+", 40)
    
    # [3] 단축키 탭 버튼 모음
    key_buttons = {
        'UP': Button(80, 320, 200, 50, ""), 'DOWN': Button(80, 390, 200, 50, ""),
        'LEFT': Button(80, 460, 200, 50, ""), 'RIGHT': Button(80, 530, 200, 50, "")
    }
    key_labels = {
        'UP': "위 (UP):", 'DOWN': "아래 (DOWN):",
        'LEFT': "왼쪽 (LEFT):", 'RIGHT': "오른쪽 (RIGHT):"
    }

    # [수정] 하단 제어 버튼 높이를 60으로 키워 글씨 짤림 완벽 해결
    btn_close_overlay = Button(0, 680, 240, 60, "닫기", base_col=(80, 80, 90), hover_col=(120, 120, 130))
    btn_return_main = Button(-130, 680, 240, 60, "나가기", base_col=(180, 50, 50), hover_col=(220, 80, 80))
    btn_close_settings_game = Button(130, 680, 240, 60, "설정 닫기", base_col=(80, 80, 90), hover_col=(120, 120, 130))

    # --- 세이브/로드 슬롯 버튼 ---
    slot_buttons = [
        Button(-50, 250, 320, 80, "슬롯 1", 26),
        Button(-50, 380, 320, 80, "슬롯 2", 26),
        Button(-50, 510, 320, 80, "슬롯 3", 26)
    ]
    delete_buttons = [
        Button(160, 250, 80, 80, "삭제", 24, base_col=(180, 50, 50), hover_col=(220, 80, 80)),
        Button(160, 380, 80, 80, "삭제", 24, base_col=(180, 50, 50), hover_col=(220, 80, 80)),
        Button(160, 510, 80, 80, "삭제", 24, base_col=(180, 50, 50), hover_col=(220, 80, 80))
    ]

    # --- 삭제/저장 확인 팝업창 버튼 ---
    btn_confirm_yes_del = Button(-100, 450, 150, 60, "예 (삭제)", base_col=(180, 50, 50), hover_col=(220, 80, 80))
    btn_confirm_yes_save = Button(-100, 450, 150, 60, "예 (저장)", base_col=(60, 150, 60), hover_col=(90, 180, 90))
    btn_confirm_no = Button(100, 450, 150, 60, "아니오", base_col=(80, 80, 90), hover_col=(120, 120, 130))

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        scaled_mouse_pos = get_scaled_mouse_pos()
        center_x = LOGICAL_WIDTH // 2

        # ----------------- UI 텍스트 동적 업데이트 -----------------
        for i in range(3):
            slot_key = f"slot_{i+1}"
            if saves_data[slot_key]:
                ptime = saves_data[slot_key].get("play_time", 0.0)
                time_str = format_time(ptime)
                slot_buttons[i].text = f"슬롯 {i+1} [{time_str}]"
                slot_buttons[i].base_color = (60, 120, 60)
            else:
                slot_buttons[i].text = f"슬롯 {i+1} [비어있음]"
                slot_buttons[i].base_color = (80, 80, 90)
        # -----------------------------------------------------------

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # 단축키 처리
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if confirm_delete_slot is not None:
                        confirm_delete_slot = None
                    elif confirm_save_slot is not None:
                        confirm_save_slot = None
                    elif current_overlay:
                        current_overlay = None 
                        waiting_for_key = None
                    elif app_state == APP_PLAYING:
                        current_overlay = 'SETTINGS' 
                
                elif event.key == pygame.K_q and app_state == APP_PLAYING and not current_overlay:
                    current_overlay = 'SAVE'

            # [1] 오버레이(설정/세이브/로드)가 켜져 있을 때의 입력 처리
            if current_overlay:
                if current_overlay == 'SETTINGS':
                    if waiting_for_key and event.type == pygame.KEYDOWN:
                        if event.key != pygame.K_ESCAPE:
                            config['keys'][waiting_for_key] = event.key
                            save_config() # 단축키 변경 시 바로 저장
                        waiting_for_key = None
                    elif not waiting_for_key:
                        if btn_video.is_clicked(event, scaled_mouse_pos): current_tab = "VIDEO"
                        if btn_audio.is_clicked(event, scaled_mouse_pos): current_tab = "AUDIO"
                        if btn_keys.is_clicked(event, scaled_mouse_pos): current_tab = "KEYS"
                        
                        if app_state == APP_MAIN_MENU:
                            if btn_close_overlay.is_clicked(event, scaled_mouse_pos):
                                current_overlay = None
                        elif app_state == APP_PLAYING:
                            if btn_close_settings_game.is_clicked(event, scaled_mouse_pos):
                                current_overlay = None
                            
                            if btn_return_main.is_clicked(event, scaled_mouse_pos):
                                app_state = APP_MAIN_MENU
                                current_overlay = None
                                player = Player()
                                bullets.clear()
                                enemies.clear()
                                room_state = ROOM_WAITING
                                current_play_time = 0.0

                        if current_tab == "VIDEO":
                            if btn_window.is_clicked(event, scaled_mouse_pos): update_display('WINDOW')
                            if btn_borderless.is_clicked(event, scaled_mouse_pos): update_display('BORDERLESS')
                            if btn_fullscreen.is_clicked(event, scaled_mouse_pos): update_display('FULLSCREEN')
                            
                        elif current_tab == "AUDIO":
                            # 볼륨 변경 시 바로 저장
                            if btn_vol_down.is_clicked(event, scaled_mouse_pos): 
                                config['volume'] = max(0, config['volume'] - 10)
                                save_config()
                            if btn_vol_up.is_clicked(event, scaled_mouse_pos): 
                                config['volume'] = min(100, config['volume'] + 10)
                                save_config()
                            
                            if btn_combat_vol_down.is_clicked(event, scaled_mouse_pos): 
                                config['combat_volume'] = max(0, config['combat_volume'] - 10)
                                save_config()
                            if btn_combat_vol_up.is_clicked(event, scaled_mouse_pos): 
                                config['combat_volume'] = min(100, config['combat_volume'] + 10)
                                save_config()
                            
                            if btn_voice_vol_down.is_clicked(event, scaled_mouse_pos): 
                                config['voice_volume'] = max(0, config['voice_volume'] - 10)
                                save_config()
                            if btn_voice_vol_up.is_clicked(event, scaled_mouse_pos): 
                                config['voice_volume'] = min(100, config['voice_volume'] + 10)
                                save_config()
                            
                        elif current_tab == "KEYS":
                            for action, btn in key_buttons.items():
                                if btn.is_clicked(event, scaled_mouse_pos): waiting_for_key = action
                
                # 세이브 & 로드 오버레이 입력 처리
                elif current_overlay in ['SAVE', 'LOAD']:
                    if confirm_delete_slot is not None:
                        if btn_confirm_yes_del.is_clicked(event, scaled_mouse_pos):
                            slot_key = f"slot_{confirm_delete_slot}"
                            saves_data[slot_key] = None
                            write_save_data(saves_data)
                            confirm_delete_slot = None 
                        elif btn_confirm_no.is_clicked(event, scaled_mouse_pos):
                            confirm_delete_slot = None 
                            
                    elif confirm_save_slot is not None:
                        if btn_confirm_yes_save.is_clicked(event, scaled_mouse_pos):
                            slot_key = f"slot_{confirm_save_slot}"
                            saves_data[slot_key] = {
                                "play_time": current_play_time,
                                "player_x": player.pos.x,
                                "player_y": player.pos.y,
                                "room_state": room_state,
                                "enemies": [{"x": e.pos.x, "y": e.pos.y, "hp": e.hp} for e in enemies]
                            }
                            write_save_data(saves_data)
                            confirm_save_slot = None
                            current_overlay = None
                        elif btn_confirm_no.is_clicked(event, scaled_mouse_pos):
                            confirm_save_slot = None
                            
                    else:
                        if btn_close_overlay.is_clicked(event, scaled_mouse_pos):
                            current_overlay = None
                        
                        for i in range(3):
                            slot_key = f"slot_{i+1}"
                            
                            if saves_data[slot_key]:
                                if delete_buttons[i].is_clicked(event, scaled_mouse_pos):
                                    confirm_delete_slot = i + 1 
                                    break 
                            
                            if slot_buttons[i].is_clicked(event, scaled_mouse_pos):
                                if current_overlay == 'SAVE':
                                    confirm_save_slot = i + 1 
                                    
                                elif current_overlay == 'LOAD':
                                    if saves_data[slot_key]:
                                        save_info = saves_data[slot_key]
                                        current_play_time = save_info.get("play_time", 0.0)
                                        player.pos.x = save_info["player_x"]
                                        player.pos.y = save_info["player_y"]
                                        room_state = save_info["room_state"]
                                        
                                        enemies.clear()
                                        for e_data in save_info["enemies"]:
                                            en = Enemy(e_data["x"], e_data["y"])
                                            en.hp = e_data["hp"]
                                            enemies.append(en)
                                            
                                        bullets.clear()
                                        app_state = APP_PLAYING
                                        current_overlay = None
                                        break

            # [2] 오버레이가 없고 메인 메뉴 상태일 때
            elif app_state == APP_MAIN_MENU:
                if menu_btn_start.is_clicked(event, scaled_mouse_pos):
                    player = Player()
                    bullets.clear()
                    enemies.clear()
                    room_state = ROOM_WAITING
                    current_play_time = 0.0
                    app_state = APP_PLAYING
                elif menu_btn_continue.is_clicked(event, scaled_mouse_pos):
                    current_overlay = 'LOAD'
                elif menu_btn_settings.is_clicked(event, scaled_mouse_pos):
                    current_overlay = 'SETTINGS'
                elif menu_btn_quit.is_clicked(event, scaled_mouse_pos):
                    running = False

            # [3] 오버레이가 없고 인게임 상태일 때
            elif app_state == APP_PLAYING and room_state in [ROOM_COMBAT, ROOM_CLEARED]:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = scaled_mouse_pos
                    bullets.append(Bullet(player.pos.x, player.pos.y, mx, my))

        # === 게임 로직 업데이트 ===
        if not current_overlay and app_state == APP_PLAYING:
            player.move(dt)
            current_play_time += dt

            if room_state == ROOM_WAITING:
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


        # ==================== 렌더링 (그리기) ====================
        display_surface.fill((0, 0, 0))

        if app_state == APP_MAIN_MENU:
            title_text = title_font.render("단죄의 시간", True, (255, 255, 255))
            display_surface.blit(title_text, (150, 150))
            
            sub_text = font.render("Time of Condemnation", True, (150, 150, 150))
            display_surface.blit(sub_text, (160, 280))

            menu_btn_start.draw(display_surface, center_x, scaled_mouse_pos)
            menu_btn_continue.draw(display_surface, center_x, scaled_mouse_pos)
            menu_btn_settings.draw(display_surface, center_x, scaled_mouse_pos)
            menu_btn_quit.draw(display_surface, center_x, scaled_mouse_pos)

        elif app_state == APP_PLAYING:
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

            time_str = format_time(current_play_time)
            ui_text = f"진행 시간: {time_str} | [ESC] 설정 | [Q] 진행상황 저장"
            display_surface.blit(font.render(ui_text, True, (200, 200, 200)), (20, 20))

        # 3. 오버레이(팝업창) 그리기
        if current_overlay:
            overlay_bg = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
            overlay_bg.fill((0, 0, 0, 180))
            display_surface.blit(overlay_bg, (0, 0))

            panel_rect = pygame.Rect(center_x - 350, 150, 700, 600)
            pygame.draw.rect(display_surface, (40, 40, 45), panel_rect, border_radius=15)
            pygame.draw.rect(display_surface, (200, 200, 200), panel_rect, width=3, border_radius=15)

            if current_overlay == 'SETTINGS':
                btn_video.draw(display_surface, center_x, scaled_mouse_pos)
                btn_audio.draw(display_surface, center_x, scaled_mouse_pos)
                btn_keys.draw(display_surface, center_x, scaled_mouse_pos)
                
                if app_state == APP_MAIN_MENU:
                    btn_close_overlay.draw(display_surface, center_x, scaled_mouse_pos)
                elif app_state == APP_PLAYING:
                    btn_return_main.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_close_settings_game.draw(display_surface, center_x, scaled_mouse_pos)

                if current_tab == "VIDEO":
                    btn_window.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_borderless.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_fullscreen.draw(display_surface, center_x, scaled_mouse_pos)
                    
                elif current_tab == "AUDIO":
                    vol_text = font.render(f"마스터 볼륨: {config['volume']}%", True, (255, 255, 255))
                    display_surface.blit(vol_text, (center_x - vol_text.get_width()//2, 270))
                    btn_vol_down.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
                    
                    combat_vol_text = font.render(f"전투 볼륨: {config['combat_volume']}%", True, (255, 255, 255))
                    display_surface.blit(combat_vol_text, (center_x - combat_vol_text.get_width()//2, 400))
                    btn_combat_vol_down.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_combat_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
                    
                    voice_vol_text = font.render(f"음성 볼륨: {config['voice_volume']}%", True, (255, 255, 255))
                    display_surface.blit(voice_vol_text, (center_x - voice_vol_text.get_width()//2, 530))
                    btn_voice_vol_down.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_voice_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
                    
                elif current_tab == "KEYS":
                    for action, btn in key_buttons.items():
                        key_name = pygame.key.name(config['keys'][action]).upper()
                        if waiting_for_key == action:
                            btn.text = "[ 입력 대기중 ]"
                            btn.base_color = (200, 100, 100)
                        else:
                            btn.text = f"{key_name}"
                            btn.base_color = (80, 80, 90)
                        
                        label_str = key_labels[action]
                        label_surf = font.render(label_str, True, (255, 255, 255))
                        label_x = (center_x - 40) - label_surf.get_width()
                        label_y = btn.rect.y + (btn.rect.height - label_surf.get_height()) // 2
                        display_surface.blit(label_surf, (label_x, label_y))
                        
                        btn.draw(display_surface, center_x, scaled_mouse_pos)

            elif current_overlay in ['SAVE', 'LOAD']:
                if confirm_delete_slot is not None:
                    line1_surf = large_font.render(f"슬롯 {confirm_delete_slot}의 데이터를 정말", True, (255, 100, 100))
                    display_surface.blit(line1_surf, (center_x - line1_surf.get_width()//2, 290))
                    line2_surf = large_font.render("삭제하시겠습니까?", True, (255, 100, 100))
                    display_surface.blit(line2_surf, (center_x - line2_surf.get_width()//2, 350))
                    
                    btn_confirm_yes_del.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_confirm_no.draw(display_surface, center_x, scaled_mouse_pos)
                    
                elif confirm_save_slot is not None:
                    line1_surf = large_font.render(f"슬롯 {confirm_save_slot}에 진행상황을", True, (100, 255, 100))
                    display_surface.blit(line1_surf, (center_x - line1_surf.get_width()//2, 290))
                    line2_surf = large_font.render("저장하시겠습니까?", True, (100, 255, 100))
                    display_surface.blit(line2_surf, (center_x - line2_surf.get_width()//2, 350))
                    
                    btn_confirm_yes_save.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_confirm_no.draw(display_surface, center_x, scaled_mouse_pos)
                    
                else:
                    title_str = "진행상황 저장 (저장할 슬롯 클릭)" if current_overlay == 'SAVE' else "저장된 게임 불러오기"
                    title_surf = large_font.render(title_str, True, (255, 255, 255))
                    display_surface.blit(title_surf, (center_x - title_surf.get_width()//2, 170))
                    
                    for i in range(3):
                        slot_buttons[i].draw(display_surface, center_x, scaled_mouse_pos)
                        if saves_data[f"slot_{i+1}"]:
                            delete_buttons[i].draw(display_surface, center_x, scaled_mouse_pos)
                    
                    btn_close_overlay.draw(display_surface, center_x, scaled_mouse_pos)

        scaled_surface = pygame.transform.scale(display_surface, (current_width, current_height))
        screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()