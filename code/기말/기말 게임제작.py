import os
import pygame
import sys
import json

# Pygame 초기화
pygame.init()

# ==================== 한글 폰트 자동 탐색 함수 ====================
def get_korean_font(size, bold=False):
    font_names = ['nanumgothic', 'apple sd gothic neo', 'applegothic', 'dotum', 'gulim', 'batang', 'malgungothic']
    for name in font_names:
        if pygame.font.match_font(name):
            return pygame.font.SysFont(name, size, bold=bold)
    return pygame.font.SysFont(None, size, bold=bold)

info = pygame.display.Info()
DESKTOP_W, DESKTOP_H = info.current_w, info.current_h
os.environ['SDL_VIDEO_CENTERED'] = '1'

LOGICAL_WIDTH, LOGICAL_HEIGHT = 1920, 1080
display_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))

# [핵심 추가] 게임 화면만 보여줄 뷰포트(Viewport) 설정
# 좌우 마진 360px, 상하 마진 90px (양옆이 훨씬 넓음)
VIEW_MARGIN_X = 320
VIEW_MARGIN_Y = 70
VIEW_W = LOGICAL_WIDTH - (VIEW_MARGIN_X * 2)  # 1200
VIEW_H = LOGICAL_HEIGHT - (VIEW_MARGIN_Y * 2) # 900
view_surface = pygame.Surface((VIEW_W, VIEW_H))

current_width, current_height = 1600, 900
screen = pygame.display.set_mode((current_width, current_height))
pygame.display.set_caption("단죄의 시간 (Time of Condemnation)")
clock = pygame.time.Clock()

# ==================== 이미지 자원 관리 ====================
IMAGES = {}

def load_images():
    try:
        # 원본 이미지 딱 한 번만 불러오기
        naye_base = pygame.image.load("./code/기말/assets/image/나예 기본.png").convert_alpha()
        naye_surprised = pygame.image.load("./code/기말/assets/image/나예 놀람.png").convert_alpha()
        naye_fearful = pygame.image.load("./code/기말/assets/image/나예 두려움.png").convert_alpha()
        naye_sad = pygame.image.load("./code/기말/assets/image/나예 슬픔.png").convert_alpha()
        naye_happy = pygame.image.load("./code/기말/assets/image/나예 행복.png").convert_alpha()
        naye_disgusted = pygame.image.load("./code/기말/assets/image/나예 혐오.png").convert_alpha()
        naye_angry = pygame.image.load("./code/기말/assets/image/나예 화남.png").convert_alpha()

        # 2. 좌측 UI 일러스트용 (크기 250x250) 미리 만들어서 따로 저장!
        IMAGES['naye_base'] = pygame.transform.scale(naye_base, (1700, 900))
        IMAGES['naye_surprised'] = pygame.transform.scale(naye_surprised, (1700, 900))
        IMAGES['naye_fearful'] = pygame.transform.scale(naye_fearful, (1700, 900))
        IMAGES['naye_sad'] = pygame.transform.scale(naye_sad, (1700, 900))
        IMAGES['naye_happy'] = pygame.transform.scale(naye_happy, (1700, 900))
        IMAGES['naye_disgusted'] = pygame.transform.scale(naye_disgusted, (1700, 900))
        IMAGES['naye_angry'] = pygame.transform.scale(naye_angry, (1700, 900))
        # 3. 인게임 플레이어 대기(Idle) 애니메이션 리스트
        IMAGES['player_idle'] = []
        
        # 1. 먼저 3장의 이미지를 각각 불러와서 크기를 맞춥니다.
        # (파일 경로는 실제 파일 이름에 맞게 수정해 주세요!)
        idle_1 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/대기 모션_1.png").convert_alpha(), (100, 100))
        idle_2 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/대기 모션_2.png").convert_alpha(), (100, 100))
        idle_3 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/대기 모션_3.png").convert_alpha(), (100, 100))

        # 2. 원하는 재생 순서대로 리스트에 쏙쏙 담아줍니다!
        IMAGES['player_idle'] = [idle_1, idle_2, idle_2, idle_3, idle_3, idle_2, idle_2, idle_1]
    except Exception as e:
        print(f"이미지 로딩 중 오류 발생: {e}")

# ==================== 게임 전체 상태 정의 ====================
APP_MAIN_MENU = 0
APP_PLAYING = 1

# ==================== 맵(스테이지) 데이터 정의 ====================
TILE_SIZE = 45 # 1.5배 확대 유지
MAP_DATA = [
    {"name": "교실", "cols": 40, "rows": 30},
    {"name": "화장실", "cols": 25, "rows": 15},
    {"name": "보건실", "cols": 20, "rows": 30},
    {"name": "체육관", "cols": 60, "rows": 60},
    {"name": "급식실", "cols": 50, "rows": 60},
    {"name": "컴퓨터실", "cols": 50, "rows": 50},
    {"name": "도서관", "cols": 60, "rows": 50},
    {"name": "교장실", "cols": 80, "rows": 60} 
]

# ==================== 설정(Config) 시스템 ====================
CONFIG_FILE = "settings.json"
config = {
    'display_mode': 'WINDOW', 'volume': 50, 'combat_volume': 50, 'voice_volume': 50,
    'keys': {'UP': pygame.K_w, 'DOWN': pygame.K_s, 'LEFT': pygame.K_a, 'RIGHT': pygame.K_d}
}

def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                for k, v in loaded.items():
                    if isinstance(v, dict) and k in config: config[k].update(v)
                    else: config[k] = v
        except: pass

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

# ==================== 세이브/로드 시스템 ====================
SAVE_FILE = "save_data.json"

def get_save_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"slot_1": None, "slot_2": None, "slot_3": None}

def write_save_data(data):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

# 색상
BG_COLOR = (20, 20, 25); ROOM_COLOR = (40, 40, 45); GRID_COLOR = (60, 60, 70)
PLAYER_COLOR = (50, 150, 255); BULLET_COLOR = (255, 230, 50)
ENEMY_COLOR = (255, 60, 60); BOSS_COLOR = (200, 50, 255)
DOOR_OPEN_COLOR = (100, 255, 100); DOOR_LOCKED_COLOR = (150, 50, 50)

# 방 상태
ROOM_WAITING = 0; ROOM_COMBAT = 1; ROOM_CLEARED = 2

def get_scaled_mouse_pos():
    mx, my = pygame.mouse.get_pos()
    return int(mx * (LOGICAL_WIDTH / current_width)), int(my * (LOGICAL_HEIGHT / current_height))

class Button:
    def __init__(self, rel_x, y, w, h, text, font_size=30, base_col=(80, 80, 90), hover_col=(120, 120, 130)):
        self.rel_x, self.y, self.w, self.h = rel_x, y, w, h
        self.text = text
        self.font = get_korean_font(font_size)
        self.base_color, self.hover_color = base_col, hover_col
        self.rect = pygame.Rect(0, y, w, h)

    def draw(self, surface, center_x, scaled_mouse_pos):
        self.rect.x = center_x + self.rel_x - self.w // 2
        color = self.hover_color if self.rect.collidepoint(scaled_mouse_pos) else self.base_color
        pygame.draw.rect(surface, color, self.rect, border_radius=10) 
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        surface.blit(text_surf, (self.rect.centerx - text_surf.get_width()//2, self.rect.centery - text_surf.get_height()//2 - 5))

    def is_clicked(self, event, scaled_mouse_pos):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(scaled_mouse_pos)

# ==================== 게임 객체 ====================
class Player:
    def __init__(self, room_w, room_h):
        self.pos = pygame.math.Vector2(room_w // 2, room_h - 90)
        self.normal_speed = 600
        self.speed = self.normal_speed
        self.radius = 18
        
        # ==================== 대쉬 관련 변수 ====================
        self.is_dashing = False
        self.dash_speed = 1800            
        self.dash_duration = 0.15         
        self.dash_cooldown = 1.0          
        self.dash_time_left = 0           
        self.dash_cooldown_left = 0       
        self.dash_direction = pygame.math.Vector2(0, 0)
        
        # ==================== 애니메이션 관련 변수 ====================
        self.frame_index = 0.0          # 현재 보여줄 이미지 프레임 (소수점 포함)
        self.animation_speed = 6.0      # 애니메이션 속도 (1초에 6프레임 전환)

    def move(self, dt, room_w, room_h):
        # 1. 쿨타임 감소 로직
        if self.dash_cooldown_left > 0:
            self.dash_cooldown_left -= dt

        # 2. 대쉬 진행 중일 때의 로직
        if self.is_dashing:
            self.dash_time_left -= dt
            if self.dash_time_left <= 0:
                self.is_dashing = False
                self.speed = self.normal_speed
            else:
                self.pos += self.dash_direction * self.speed * dt
                self.pos.x = max(self.radius, min(room_w - self.radius, self.pos.x))
                self.pos.y = max(self.radius, min(room_h - self.radius, self.pos.y))
                return 

        # 3. 일반 이동 로직
        keys = pygame.key.get_pressed()
        direction = pygame.math.Vector2(0, 0)
        if keys[config['keys']['UP']]: direction.y -= 1
        if keys[config['keys']['DOWN']]: direction.y += 1
        if keys[config['keys']['LEFT']]: direction.x -= 1
        if keys[config['keys']['RIGHT']]: direction.x += 1

        if direction.length() > 0: 
            direction = direction.normalize()

        # 4. 대쉬 발동 조건 확인
        if keys[pygame.K_SPACE] and self.dash_cooldown_left <= 0 and direction.length() > 0:
            self.is_dashing = True
            self.dash_time_left = self.dash_duration
            self.dash_cooldown_left = self.dash_cooldown
            self.speed = self.dash_speed
            self.dash_direction = direction
            self.pos += self.dash_direction * self.speed * dt
        else:
            self.pos += direction * self.speed * dt
            
        # 5. [추가] 애니메이션 프레임 업데이트 로직
        if direction.length() == 0 and not self.is_dashing:
            # 가만히 있을 때(대기 상태) 타이머 증가
            self.frame_index += self.animation_speed * dt
        else:
            # 움직일 때는 일단 프레임을 초기화
            self.frame_index = 0.0

        # 맵 바깥으로 나가지 못하게 보정
        self.pos.x = max(self.radius, min(room_w - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(room_h - self.radius, self.pos.y))

    def draw(self, surface, cam_x, cam_y):
        draw_x = int(self.pos.x - cam_x)
        draw_y = int(self.pos.y - cam_y)
        
        # 대쉬 중일 때의 컬러 
        current_color = (150, 255, 255) if self.is_dashing else PLAYER_COLOR
        
        # [수정] 대기 애니메이션 리스트가 정상적으로 로드되었는지 확인
        idle_frames = IMAGES.get('player_idle', [])
        
        if len(idle_frames) > 0:
            # 현재 프레임 인덱스에 맞는 이미지를 가져옵니다. (리스트 길이를 넘어가면 0으로 순환)
            current_frame = int(self.frame_index) % len(idle_frames)
            img_to_draw = idle_frames[current_frame]
            
            surface.blit(img_to_draw, (draw_x - self.radius, draw_y - self.radius))
            
            # 대쉬 중일 때 외곽선 효과
            if self.is_dashing:
                pygame.draw.circle(surface, current_color, (draw_x, draw_y), self.radius + 2, 3)
                
        # 리스트가 비어있고 그냥 'player'라는 단일 이미지만 있으면 호환용으로 그림
        elif 'player' in IMAGES: 
            surface.blit(IMAGES['player'], (draw_x - self.radius, draw_y - self.radius))
        else:
            pygame.draw.circle(surface, current_color, (draw_x, draw_y), self.radius)

class Bullet:
    def __init__(self, x, y, target_x, target_y):
        self.pos = pygame.math.Vector2(x, y)
        self.speed = 1200
        self.radius = 9
        direction = pygame.math.Vector2(target_x - x, target_y - y)
        self.direction = direction.normalize() if direction.length() > 0 else pygame.math.Vector2(1, 0)

    def update(self, dt): self.pos += self.direction * self.speed * dt
    def draw(self, surface, cam_x, cam_y):
        pygame.draw.circle(surface, BULLET_COLOR, (int(self.pos.x - cam_x), int(self.pos.y - cam_y)), self.radius)

class Enemy:
    def __init__(self, x, y, is_boss=False):
        self.pos = pygame.math.Vector2(x, y)
        self.is_boss = is_boss
        if is_boss:
            self.speed, self.radius, self.hp, self.max_hp = 180, 45, 50, 50 
            self.color = BOSS_COLOR
        else:
            self.speed, self.radius, self.hp, self.max_hp = 270, 18, 5, 5 
            self.color = ENEMY_COLOR

    def update(self, dt, target_pos):
        direction = target_pos - self.pos
        if direction.length() > 0: direction = direction.normalize()
        self.pos += direction * self.speed * dt

    def draw(self, surface, cam_x, cam_y):
        draw_x, draw_y = int(self.pos.x - cam_x), int(self.pos.y - cam_y)
        pygame.draw.circle(surface, self.color, (draw_x, draw_y), self.radius)
        bar_w = 60 if self.is_boss else 36
        pygame.draw.rect(surface, (255, 255, 255), (draw_x - bar_w//2, draw_y - self.radius - 15, bar_w, 6))
        pygame.draw.rect(surface, self.color, (draw_x - bar_w//2, draw_y - self.radius - 15, bar_w * (self.hp/self.max_hp), 6))

def update_display(mode):
    global screen, current_width, current_height
    config['display_mode'] = mode
    save_config()
    screen.fill((0, 0, 0)); pygame.display.flip()
    if mode == 'FULLSCREEN': screen = pygame.display.set_mode((DESKTOP_W, DESKTOP_H), pygame.FULLSCREEN)
    elif mode == 'BORDERLESS':
        os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
        screen = pygame.display.set_mode((DESKTOP_W, DESKTOP_H), pygame.NOFRAME)
    else:
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        if 'SDL_VIDEO_WINDOW_POS' in os.environ: del os.environ['SDL_VIDEO_WINDOW_POS']
        screen = pygame.display.set_mode((1600, 900))
    current_width, current_height = screen.get_width(), screen.get_height()

def main():
    global current_width, current_height, screen
    load_config()
    update_display(config['display_mode'])
    load_images()
    
    app_state = APP_MAIN_MENU 
    
    current_map_idx = 0
    # [수정] 방을 깼는지 추적하는 리스트 (왔다 갔다 할 때 적 재생성 방지)
    cleared_rooms = [False] * len(MAP_DATA)
    
    cols, rows = MAP_DATA[0]['cols'], MAP_DATA[0]['rows']
    room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
    
    player = Player(room_w, room_h)
    bullets = []; enemies = []; room_state = ROOM_WAITING
    saves_data = get_save_data(); current_play_time = 0.0
    camera_x, camera_y = 0, 0
    
    title_font = get_korean_font(100, bold=True)
    font = get_korean_font(30)
    large_font = get_korean_font(40)

    current_overlay = None; current_tab = "VIDEO"; waiting_for_key = None
    confirm_delete_slot = None; confirm_save_slot = None

    menu_btn_start = Button(-710, 660, 240, 70, "새로 시작")
    menu_btn_continue = Button(-710, 740, 240, 70, "이어하기")
    menu_btn_settings = Button(-710, 820, 240, 70, "설정")
    menu_btn_quit = Button(-710, 900, 240, 70, "게임 종료", base_col=(180, 50, 50), hover_col=(220, 80, 80))

    btn_video = Button(-200, 200, 180, 60, "화면 설정")
    btn_audio = Button(0, 200, 180, 60, "음향 설정")
    btn_keys = Button(200, 200, 180, 60, "단축키")
    
    btn_window = Button(0, 320, 320, 60, "창 모드 (1600x900)")
    btn_borderless = Button(0, 390, 320, 60, "테두리 없는 전체화면")
    btn_fullscreen = Button(0, 460, 320, 60, "독점 전체화면")
    
    btn_vol_down = Button(-100, 310, 60, 60, "-", 40); btn_vol_up = Button(100, 310, 60, 60, "+", 40)
    btn_combat_vol_down = Button(-100, 440, 60, 60, "-", 40); btn_combat_vol_up = Button(100, 440, 60, 60, "+", 40)
    btn_voice_vol_down = Button(-100, 570, 60, 60, "-", 40); btn_voice_vol_up = Button(100, 570, 60, 60, "+", 40)
    
    key_buttons = {'UP': Button(80, 320, 220, 60, ""), 'DOWN': Button(80, 390, 220, 60, ""), 'LEFT': Button(80, 460, 220, 60, ""), 'RIGHT': Button(80, 530, 220, 60, "")}
    key_labels = {'UP': "위 (UP):", 'DOWN': "아래 (DOWN):", 'LEFT': "왼쪽 (LEFT):", 'RIGHT': "오른쪽 (RIGHT):"}

    btn_close_overlay = Button(0, 680, 260, 70, "닫기", base_col=(80, 80, 90))
    btn_return_main = Button(-140, 680, 260, 70, "나가기", base_col=(180, 50, 50))
    btn_close_settings_game = Button(140, 680, 260, 70, "설정 닫기", base_col=(80, 80, 90))

    slot_buttons = [Button(-50, 250, 320, 80, "슬롯 1", 26), Button(-50, 380, 320, 80, "슬롯 2", 26), Button(-50, 510, 320, 80, "슬롯 3", 26)]
    delete_buttons = [Button(160, 250, 80, 80, "삭제", 24, (180, 50, 50)), Button(160, 380, 80, 80, "삭제", 24, (180, 50, 50)), Button(160, 510, 80, 80, "삭제", 24, (180, 50, 50))]
    
    btn_confirm_yes_del = Button(-120, 450, 200, 70, "예 (삭제)", base_col=(180, 50, 50))
    btn_confirm_yes_save = Button(-120, 450, 200, 70, "예 (저장)", base_col=(60, 150, 60))
    btn_confirm_no = Button(120, 450, 200, 70, "아니오", base_col=(80, 80, 90))

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        scaled_mouse_pos = get_scaled_mouse_pos()
        center_x = LOGICAL_WIDTH // 2

        # ----------------- UI 텍스트 동적 업데이트 -----------------
        for i in range(3):
            slot_key = f"slot_{i+1}"
            if saves_data[slot_key]:
                slot_buttons[i].text = f"슬롯 {i+1} [{format_time(saves_data[slot_key].get('play_time', 0.0))}]"
                slot_buttons[i].base_color = (60, 120, 60)
            else:
                slot_buttons[i].text = f"슬롯 {i+1} [비어있음]"
                slot_buttons[i].base_color = (80, 80, 90)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if confirm_delete_slot: confirm_delete_slot = None
                    elif confirm_save_slot: confirm_save_slot = None
                    elif current_overlay: current_overlay = None; waiting_for_key = None
                    elif app_state == APP_PLAYING: current_overlay = 'SETTINGS' 
                elif event.key == pygame.K_q and app_state == APP_PLAYING and not current_overlay:
                    current_overlay = 'SAVE'

            if current_overlay:
                if current_overlay == 'SETTINGS':
                    if waiting_for_key and event.type == pygame.KEYDOWN:
                        if event.key != pygame.K_ESCAPE: config['keys'][waiting_for_key] = event.key; save_config()
                        waiting_for_key = None
                    elif not waiting_for_key:
                        if btn_video.is_clicked(event, scaled_mouse_pos): current_tab = "VIDEO"
                        if btn_audio.is_clicked(event, scaled_mouse_pos): current_tab = "AUDIO"
                        if btn_keys.is_clicked(event, scaled_mouse_pos): current_tab = "KEYS"
                        
                        if app_state == APP_MAIN_MENU and btn_close_overlay.is_clicked(event, scaled_mouse_pos): current_overlay = None
                        elif app_state == APP_PLAYING:
                            if btn_close_settings_game.is_clicked(event, scaled_mouse_pos): current_overlay = None
                            if btn_return_main.is_clicked(event, scaled_mouse_pos):
                                app_state = APP_MAIN_MENU; current_overlay = None; player = Player(room_w, room_h)
                                bullets.clear(); enemies.clear(); room_state = ROOM_WAITING; current_play_time = 0.0
                                cleared_rooms = [False] * len(MAP_DATA) # 초기화

                        if current_tab == "VIDEO":
                            if btn_window.is_clicked(event, scaled_mouse_pos): update_display('WINDOW')
                            if btn_borderless.is_clicked(event, scaled_mouse_pos): update_display('BORDERLESS')
                            if btn_fullscreen.is_clicked(event, scaled_mouse_pos): update_display('FULLSCREEN')
                        elif current_tab == "AUDIO":
                            if btn_vol_down.is_clicked(event, scaled_mouse_pos): config['volume'] = max(0, config['volume'] - 10); save_config()
                            if btn_vol_up.is_clicked(event, scaled_mouse_pos): config['volume'] = min(100, config['volume'] + 10); save_config()
                            if btn_combat_vol_down.is_clicked(event, scaled_mouse_pos): config['combat_volume'] = max(0, config['combat_volume'] - 10); save_config()
                            if btn_combat_vol_up.is_clicked(event, scaled_mouse_pos): config['combat_volume'] = min(100, config['combat_volume'] + 10); save_config()
                            if btn_voice_vol_down.is_clicked(event, scaled_mouse_pos): config['voice_volume'] = max(0, config['voice_volume'] - 10); save_config()
                            if btn_voice_vol_up.is_clicked(event, scaled_mouse_pos): config['voice_volume'] = min(100, config['voice_volume'] + 10); save_config()
                        elif current_tab == "KEYS":
                            for action, btn in key_buttons.items():
                                if btn.is_clicked(event, scaled_mouse_pos): waiting_for_key = action
                
                elif current_overlay in ['SAVE', 'LOAD']:
                    if confirm_delete_slot:
                        if btn_confirm_yes_del.is_clicked(event, scaled_mouse_pos):
                            saves_data[f"slot_{confirm_delete_slot}"] = None; write_save_data(saves_data); confirm_delete_slot = None 
                        elif btn_confirm_no.is_clicked(event, scaled_mouse_pos): confirm_delete_slot = None 
                    elif confirm_save_slot:
                        if btn_confirm_yes_save.is_clicked(event, scaled_mouse_pos):
                            saves_data[f"slot_{confirm_save_slot}"] = {
                                "map_idx": current_map_idx, "play_time": current_play_time,
                                "player_x": player.pos.x, "player_y": player.pos.y, "room_state": room_state,
                                "cleared_rooms": cleared_rooms, # 클리어 상태도 저장
                                "enemies": [{"x": e.pos.x, "y": e.pos.y, "hp": e.hp, "is_boss": e.is_boss} for e in enemies]
                            }
                            write_save_data(saves_data); confirm_save_slot = None; current_overlay = None 
                        elif btn_confirm_no.is_clicked(event, scaled_mouse_pos): confirm_save_slot = None
                    else:
                        if btn_close_overlay.is_clicked(event, scaled_mouse_pos): current_overlay = None
                        for i in range(3):
                            slot_key = f"slot_{i+1}"
                            if saves_data[slot_key] and delete_buttons[i].is_clicked(event, scaled_mouse_pos):
                                confirm_delete_slot = i + 1; break 
                            if slot_buttons[i].is_clicked(event, scaled_mouse_pos):
                                if current_overlay == 'SAVE': confirm_save_slot = i + 1 
                                elif current_overlay == 'LOAD' and saves_data[slot_key]:
                                    sd = saves_data[slot_key]
                                    current_map_idx = sd.get("map_idx", 0)
                                    cleared_rooms = sd.get("cleared_rooms", [False] * len(MAP_DATA))
                                    cols, rows = MAP_DATA[current_map_idx]['cols'], MAP_DATA[current_map_idx]['rows']
                                    room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                                    
                                    current_play_time = sd.get("play_time", 0.0)
                                    player.pos.x, player.pos.y = sd["player_x"], sd["player_y"]
                                    room_state = sd["room_state"]
                                    
                                    enemies.clear()
                                    for e in sd["enemies"]:
                                        en = Enemy(e["x"], e["y"], e.get("is_boss", False))
                                        en.hp = e["hp"]
                                        enemies.append(en)
                                        
                                    bullets.clear(); app_state = APP_PLAYING; current_overlay = None; break

            elif app_state == APP_MAIN_MENU:
                if menu_btn_start.is_clicked(event, scaled_mouse_pos):
                    # 완전 초기화 로직
                    current_map_idx = 0
                    cleared_rooms = [False] * len(MAP_DATA)
                    cols, rows = MAP_DATA[0]['cols'], MAP_DATA[0]['rows']
                    room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                    player = Player(room_w, room_h)
                    bullets.clear(); enemies.clear()
                    room_state = ROOM_WAITING; current_play_time = 0.0
                    app_state = APP_PLAYING
                elif menu_btn_continue.is_clicked(event, scaled_mouse_pos): current_overlay = 'LOAD'
                elif menu_btn_settings.is_clicked(event, scaled_mouse_pos): current_overlay = 'SETTINGS'
                elif menu_btn_quit.is_clicked(event, scaled_mouse_pos): running = False

            elif app_state == APP_PLAYING and room_state in [ROOM_COMBAT, ROOM_CLEARED]:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # 마우스 좌표 보정 (뷰포트 오프셋 계산 반영)
                    mx, my = scaled_mouse_pos
                    if VIEW_MARGIN_X <= mx <= VIEW_MARGIN_X + VIEW_W and VIEW_MARGIN_Y <= my <= VIEW_MARGIN_Y + VIEW_H:
                        target_x = mx - VIEW_MARGIN_X + camera_x
                        target_y = my - VIEW_MARGIN_Y + camera_y
                        bullets.append(Bullet(player.pos.x, player.pos.y, target_x, target_y))

        # === 게임 로직 업데이트 ===
        if not current_overlay and app_state == APP_PLAYING:
            player.move(dt, room_w, room_h)
            current_play_time += dt

            # 카메라 업데이트 로직 (뷰포트 크기 기준으로 카메라 계산)
            if room_w >= VIEW_W: camera_x = max(0, min(player.pos.x - VIEW_W / 2, room_w - VIEW_W))
            else: camera_x = -(VIEW_W - room_w) // 2
                
            if room_h >= VIEW_H: camera_y = max(0, min(player.pos.y - VIEW_H / 2, room_h - VIEW_H))
            else: camera_y = -(VIEW_H - room_h) // 2

            # 전투 진입 인식 (아직 클리어하지 않은 방일 경우에만)
            # 전투 진입 인식 (아직 클리어하지 않은 방일 경우에만)
            if room_state == ROOM_WAITING:
                if not cleared_rooms[current_map_idx]: # 플레이어 위치 조건(y < room_h - 300) 삭제
                    room_state = ROOM_COMBAT
                    if current_map_idx == len(MAP_DATA) - 1: # 마지막 교장실(보스룸)
                        enemies.append(Enemy(room_w // 2, room_h // 2, is_boss=True))
                    else: # 일반 맵
                        spawn_margin_x, spawn_margin_y = min(225, room_w // 4), min(225, room_h // 4)
                        enemies.append(Enemy(spawn_margin_x, spawn_margin_y))
                        enemies.append(Enemy(room_w - spawn_margin_x, spawn_margin_y))
                        enemies.append(Enemy(room_w // 2, spawn_margin_y + 150))
            elif room_state == ROOM_COMBAT:
                for enemy in enemies: enemy.update(dt, player.pos)
                for bullet in bullets[:]:
                    bullet.update(dt)
                    if not (0 <= bullet.pos.x <= room_w and 0 <= bullet.pos.y <= room_h):
                        bullets.remove(bullet); continue
                    for enemy in enemies[:]:
                        if bullet.pos.distance_to(enemy.pos) < bullet.radius + enemy.radius:
                            enemy.hp -= 1
                            if bullet in bullets: bullets.remove(bullet)
                            if enemy.hp <= 0: enemies.remove(enemy)
                            break
                if len(enemies) == 0: 
                    room_state = ROOM_CLEARED
                    cleared_rooms[current_map_idx] = True # 현재 방 클리어 처리!
                
            elif room_state in [ROOM_WAITING, ROOM_CLEARED]:
                for bullet in bullets[:]: bullet.update(dt)
                
                # [핵심 수정] 양방향 문 이동 (북쪽 문 -> 다음 맵 / 남쪽 문 -> 이전 맵)
                if room_w//2 - 90 < player.pos.x < room_w//2 + 90:
                    # 북쪽 문 (다음 맵으로)
                    if player.pos.y < 30 and current_map_idx < len(MAP_DATA) - 1:
                        current_map_idx += 1
                        cols, rows = MAP_DATA[current_map_idx]['cols'], MAP_DATA[current_map_idx]['rows']
                        room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                        player.pos.x, player.pos.y = room_w // 2, room_h - 90 # 남쪽에서 스폰
                        room_state = ROOM_CLEARED if cleared_rooms[current_map_idx] else ROOM_WAITING
                        bullets.clear(); enemies.clear()
                    
                    # 남쪽 문 (이전 맵으로)
                    elif player.pos.y > room_h - 30 and current_map_idx > 0:
                        current_map_idx -= 1
                        cols, rows = MAP_DATA[current_map_idx]['cols'], MAP_DATA[current_map_idx]['rows']
                        room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                        player.pos.x, player.pos.y = room_w // 2, 90 # 북쪽에서 스폰
                        room_state = ROOM_CLEARED if cleared_rooms[current_map_idx] else ROOM_WAITING
                        bullets.clear(); enemies.clear()

        # ==================== 렌더링 (그리기) ====================
        display_surface.fill((0, 0, 0)) # 전체 배경 딥블랙 유지

        if app_state == APP_MAIN_MENU:
            display_surface.blit(title_font.render("단죄의 시간", True, (255, 255, 255)), (150, 150))
            display_surface.blit(font.render("Time of Condemnation", True, (150, 150, 150)), (160, 280))
            menu_btn_start.draw(display_surface, center_x, scaled_mouse_pos)
            menu_btn_continue.draw(display_surface, center_x, scaled_mouse_pos)
            menu_btn_settings.draw(display_surface, center_x, scaled_mouse_pos)
            menu_btn_quit.draw(display_surface, center_x, scaled_mouse_pos)

        elif app_state == APP_PLAYING:
            # [핵심 수정] 뷰포트에만 게임 화면 그리기
            view_surface.fill((0, 0, 0))
            pygame.draw.rect(view_surface, ROOM_COLOR, (-camera_x, -camera_y, room_w, room_h))
            
            for i in range(cols + 1):
                x_pos = i * TILE_SIZE - camera_x
                pygame.draw.line(view_surface, GRID_COLOR, (x_pos, -camera_y), (x_pos, room_h - camera_y), 1)
            for i in range(rows + 1):
                y_pos = i * TILE_SIZE - camera_y
                pygame.draw.line(view_surface, GRID_COLOR, (-camera_x, y_pos), (room_w - camera_x, y_pos), 1)

            door_color = DOOR_OPEN_COLOR if room_state in [ROOM_WAITING, ROOM_CLEARED] else DOOR_LOCKED_COLOR
            # 북쪽 문
            if current_map_idx < len(MAP_DATA) - 1:
                pygame.draw.rect(view_surface, door_color, (room_w//2 - 90 - camera_x, -camera_y, 180, 30))
            # 남쪽 문 (첫 번째 맵 제외)
            if current_map_idx > 0:
                pygame.draw.rect(view_surface, door_color, (room_w//2 - 90 - camera_x, room_h - 30 - camera_y, 180, 30))

            if room_state == ROOM_COMBAT:
                for enemy in enemies: enemy.draw(view_surface, camera_x, camera_y)
            for bullet in bullets: bullet.draw(view_surface, camera_x, camera_y)
            player.draw(view_surface, camera_x, camera_y)

            # 완성된 뷰포트를 화면 정중앙 (마진 고려)에 찍어냄
            display_surface.blit(view_surface, (VIEW_MARGIN_X, VIEW_MARGIN_Y))

            # UI 인터페이스 렌더링 (블랙바 여백에 렌더링됨)
            display_surface.blit(font.render(f"진행 시간: {format_time(current_play_time)} | [ESC] 설정 | [Q] 저장", True, (200, 200, 200)), (40, 30))
            
            map_name_str = MAP_DATA[current_map_idx]['name']
            map_name_surf = large_font.render(f"- {map_name_str} -", True, (255, 255, 255))
            display_surface.blit(map_name_surf, (LOGICAL_WIDTH - map_name_surf.get_width() - 40, 20))

            # ==================== 좌측 캐릭터 일러스트 렌더링 ====================
            if 'naye_base' in IMAGES:
                # [수정] 기존 UI(설정창 등)가 망가지지 않도록 변수명을 illust_x, illust_y로 변경했습니다!
                illust_x = VIEW_MARGIN_X // 2
                illust_y = LOGICAL_HEIGHT - 550
                
                # 이미지 중심을 찰떡같이 맞추기
                ui_rect = IMAGES['naye_base'].get_rect(center=(illust_x, illust_y))
                
                # 화면에 그리기
                display_surface.blit(IMAGES['naye_base'], ui_rect)
                
                # 캐릭터 이름표 달아주기
                name_tag = font.render("나예", True, (255, 255, 255))
                name_rect = name_tag.get_rect(center=(illust_x, ui_rect.bottom + 30))
                
                bg_rect = pygame.Rect(0, 0, 90, 40)
                bg_rect.center = name_rect.center
                pygame.draw.rect(display_surface, (50, 50, 60), bg_rect, border_radius=5)
                display_surface.blit(name_tag, name_rect)
            # =========================================================================

            # ==================== 미니맵 렌더링 (아이작 스타일) ====================
            minimap_room_size = 24  # 미니맵 방 하나의 크기
            minimap_margin = 8      # 방과 방 사이의 간격(문)
            minimap_start_x = LOGICAL_WIDTH - 80 # 화면 우측 여백에 배치
            minimap_start_y = 90    # 현재 맵 이름(교실 등) 텍스트 아래에 배치

            # 전체 맵 개수만큼 반복하며 그리기
            for i in range(len(MAP_DATA)):
                # 맵 인덱스가 클수록 북쪽(위)이므로, 화면 위쪽부터 큰 인덱스가 그려지도록 역순 계산
                draw_idx = (len(MAP_DATA) - 1) - i
                
                rect_x = minimap_start_x
                rect_y = minimap_start_y + i * (minimap_room_size + minimap_margin)

                # --- 시야(안개) 처리 ---
                is_cleared = cleared_rooms[draw_idx]
                is_current = (draw_idx == current_map_idx)
                is_adjacent = abs(draw_idx - current_map_idx) == 1 # 바로 윗방이거나 아랫방
                
                # 아이작처럼: 클리어한 방, 현재 방, 현재 방에 바로 인접한 방만 렌더링
                if not (is_cleared or is_current or is_adjacent):
                    continue

                # --- 통로(문) 그리기 ---
                if i < len(MAP_DATA) - 1:
                    next_draw_idx = draw_idx - 1
                    # 아래쪽 방도 내 시야에 보이는 방일 때만 통로를 기름
                    next_is_visible = cleared_rooms[next_draw_idx] or (next_draw_idx == current_map_idx) or (abs(next_draw_idx - current_map_idx) == 1)
                    if next_is_visible:
                        pygame.draw.rect(display_surface, (100, 100, 100), 
                                         (rect_x + minimap_room_size//2 - 2, rect_y + minimap_room_size, 4, minimap_margin))

                # --- 방 색상 및 테두리 결정 ---
                if is_current:
                    bg_color = (200, 200, 200)       # 현재 방: 밝은 회색
                    border_color = (255, 255, 255)   # 테두리: 흰색 강조
                elif is_cleared:
                    bg_color = (70, 70, 70)          # 클리어한 방: 중간 회색
                    border_color = (130, 130, 130)
                else: 
                    bg_color = (30, 30, 30)          # 미발견 인접 방: 아주 어두운 회색
                    border_color = (80, 80, 80)

                # 방 사각형 그리기 (내부 채우기 + 테두리 선)
                pygame.draw.rect(display_surface, bg_color, (rect_x, rect_y, minimap_room_size, minimap_room_size), border_radius=3)
                pygame.draw.rect(display_surface, border_color, (rect_x, rect_y, minimap_room_size, minimap_room_size), 2, border_radius=3)

                # --- 현재 내 위치(플레이어 마커) 표시 ---
                if is_current:
                    # 현재 플레이어 색상과 동일한 파란색 원을 미니맵 방 중앙에 그림
                    pygame.draw.circle(display_surface, PLAYER_COLOR, 
                                       (rect_x + minimap_room_size//2, rect_y + minimap_room_size//2), 5)
            # =========================================================================

        # 3. 오버레이(팝업창) 그리기
        if current_overlay:
            overlay_bg = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
            overlay_bg.fill((0, 0, 0, 180)); display_surface.blit(overlay_bg, (0, 0))
            pygame.draw.rect(display_surface, (40, 40, 45), (center_x - 350, 150, 700, 600), border_radius=15)
            pygame.draw.rect(display_surface, (200, 200, 200), (center_x - 350, 150, 700, 600), 3, border_radius=15)

            if current_overlay == 'SETTINGS':
                btn_video.draw(display_surface, center_x, scaled_mouse_pos)
                btn_audio.draw(display_surface, center_x, scaled_mouse_pos)
                btn_keys.draw(display_surface, center_x, scaled_mouse_pos)
                
                if app_state == APP_MAIN_MENU: btn_close_overlay.draw(display_surface, center_x, scaled_mouse_pos)
                elif app_state == APP_PLAYING:
                    btn_return_main.draw(display_surface, center_x, scaled_mouse_pos); btn_close_settings_game.draw(display_surface, center_x, scaled_mouse_pos)

                if current_tab == "VIDEO":
                    btn_window.draw(display_surface, center_x, scaled_mouse_pos); btn_borderless.draw(display_surface, center_x, scaled_mouse_pos); btn_fullscreen.draw(display_surface, center_x, scaled_mouse_pos)
                elif current_tab == "AUDIO":
                    display_surface.blit(font.render(f"마스터 볼륨: {config['volume']}%", True, (255, 255, 255)), (center_x - 120, 270))
                    btn_vol_down.draw(display_surface, center_x, scaled_mouse_pos); btn_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
                    
                    display_surface.blit(font.render(f"전투 볼륨: {config['combat_volume']}%", True, (255, 255, 255)), (center_x - 120, 400))
                    btn_combat_vol_down.draw(display_surface, center_x, scaled_mouse_pos); btn_combat_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
                    
                    display_surface.blit(font.render(f"음성 볼륨: {config['voice_volume']}%", True, (255, 255, 255)), (center_x - 120, 530))
                    btn_voice_vol_down.draw(display_surface, center_x, scaled_mouse_pos); btn_voice_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
                elif current_tab == "KEYS":
                    for action, btn in key_buttons.items():
                        btn.text = "[ 입력 대기중 ]" if waiting_for_key == action else pygame.key.name(config['keys'][action]).upper()
                        btn.base_color = (200, 100, 100) if waiting_for_key == action else (80, 80, 90)
                        ls = font.render(key_labels[action], True, (255, 255, 255))
                        display_surface.blit(ls, ((center_x - 40) - ls.get_width(), btn.rect.y + (btn.rect.height - ls.get_height()) // 2))
                        btn.draw(display_surface, center_x, scaled_mouse_pos)

            elif current_overlay in ['SAVE', 'LOAD']:
                if confirm_delete_slot:
                    l1 = large_font.render(f"슬롯 {confirm_delete_slot}의 데이터를 정말", True, (255, 100, 100)); l2 = large_font.render("삭제하시겠습니까?", True, (255, 100, 100))
                    display_surface.blit(l1, (center_x - l1.get_width()//2, 290)); display_surface.blit(l2, (center_x - l2.get_width()//2, 350))
                    btn_confirm_yes_del.draw(display_surface, center_x, scaled_mouse_pos); btn_confirm_no.draw(display_surface, center_x, scaled_mouse_pos)
                elif confirm_save_slot:
                    l1 = large_font.render(f"슬롯 {confirm_save_slot}에 진행상황을", True, (100, 255, 100)); l2 = large_font.render("저장하시겠습니까?", True, (100, 255, 100))
                    display_surface.blit(l1, (center_x - l1.get_width()//2, 290)); display_surface.blit(l2, (center_x - l2.get_width()//2, 350))
                    btn_confirm_yes_save.draw(display_surface, center_x, scaled_mouse_pos); btn_confirm_no.draw(display_surface, center_x, scaled_mouse_pos)
                else:
                    ts = large_font.render("진행상황 저장" if current_overlay == 'SAVE' else "게임 불러오기", True, (255, 255, 255))
                    display_surface.blit(ts, (center_x - ts.get_width()//2, 170))
                    for i in range(3): slot_buttons[i].draw(display_surface, center_x, scaled_mouse_pos); delete_buttons[i].draw(display_surface, center_x, scaled_mouse_pos) if saves_data[f"slot_{i+1}"] else None
                    btn_close_overlay.draw(display_surface, center_x, scaled_mouse_pos)

        screen.blit(pygame.transform.scale(display_surface, (current_width, current_height)), (0, 0))
        pygame.display.flip()
    pygame.quit(); sys.exit()

if __name__ == "__main__": main()