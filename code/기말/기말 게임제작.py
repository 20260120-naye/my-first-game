import os
import pygame
import sys
import json
import csv  # Tiled CSV 파일을 읽기 위한 모듈

# Pygame 초기화
pygame.init()

# ==================== 한글 폰트 자동 탐색 함수 (로딩 속도 개선 + 예전 폰트 복구!) ====================
_cached_fonts = {}

def get_korean_font(size, bold=False):
    cache_key = (size, bold)
    
    if cache_key in _cached_fonts:
        return _cached_fonts[cache_key]
    
    font_names = ['nanumgothic', 'apple sd gothic neo', 'applegothic', 'dotum', 'gulim', 'batang', 'malgungothic']
    for name in font_names:
        if pygame.font.match_font(name):
            font = pygame.font.SysFont(name, size, bold=bold)
            _cached_fonts[cache_key] = font 
            return font
            
    font = pygame.font.SysFont(None, size, bold=bold)
    _cached_fonts[cache_key] = font
    return font

info = pygame.display.Info()
DESKTOP_W, DESKTOP_H = info.current_w, info.current_h
os.environ['SDL_VIDEO_CENTERED'] = '1'

LOGICAL_WIDTH, LOGICAL_HEIGHT = 1920, 1080
display_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))

VIEW_MARGIN_X = 320
VIEW_MARGIN_Y = 70
VIEW_W = LOGICAL_WIDTH - (VIEW_MARGIN_X * 2)  
VIEW_H = LOGICAL_HEIGHT - (VIEW_MARGIN_Y * 2) 
view_surface = pygame.Surface((VIEW_W, VIEW_H))

current_width, current_height = 1600, 900
screen = pygame.display.set_mode((current_width, current_height))
pygame.display.set_caption("단죄의 시간 (Time of Condemnation)")
clock = pygame.time.Clock()

# ==================== 색상 및 방 상태 ====================
BG_COLOR = (20, 20, 25); ROOM_COLOR = (40, 40, 45); GRID_COLOR = (60, 60, 70)
PLAYER_COLOR = (50, 150, 255); BULLET_COLOR = (255, 230, 50)
ENEMY_COLOR = (255, 60, 60); BOSS_COLOR = (200, 50, 255)
DOOR_OPEN_COLOR = (100, 255, 100); DOOR_LOCKED_COLOR = (150, 50, 50)

ROOM_WAITING = 0; ROOM_COMBAT = 1; ROOM_CLEARED = 2
APP_MAIN_MENU = 0; APP_PLAYING = 1

TILE_SIZE = 32 

MAP_DATA = [
    {"name": "교실", "cols": 40, "rows": 30},
    {"name": "화장실", "cols": 26, "rows": 15}, 
    {"name": "보건실", "cols": 20, "rows": 30},
    {"name": "체육관", "cols": 60, "rows": 60},
    {"name": "급식실", "cols": 50, "rows": 60},
    {"name": "컴퓨터실", "cols": 50, "rows": 50},
    {"name": "도서관", "cols": 60, "rows": 50},
    {"name": "교장실", "cols": 80, "rows": 60} 
]

# ==================== Tiled 충돌 맵 불러오기 함수 ====================
def load_tiled_map(filepaths, default_cols=26, default_rows=15):
    combined_map = [[0 for _ in range(default_cols)] for _ in range(default_rows)]
    loaded_any = False

    for filepath in filepaths:
        if os.path.exists(filepath):
            loaded_any = True
            try:
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    for row_idx, row in enumerate(reader):
                        clean_row = [val for val in row if val.strip() != '']
                        if not clean_row: continue
                        
                        for col_idx, val_str in enumerate(clean_row):
                            if row_idx >= default_rows or col_idx >= default_cols:
                                continue
                            
                            raw_val = int(val_str)
                            real_val = raw_val & 0x0FFFFFFF
                            
                            if real_val != -1 and real_val != 0: 
                                combined_map[row_idx][col_idx] = 1
            except Exception as e:
                print(f"맵 로딩 오류 ({filepath}): {e}")

    if not loaded_any:
        print("맵 파일이 없습니다. 임시 26x15 맵을 생성합니다.")
        combined_map = [[0 for _ in range(default_cols)] for _ in range(default_rows)]
        for i in range(default_cols): combined_map[0][i] = 1; combined_map[default_rows-1][i] = 1
        for i in range(default_rows): combined_map[i][0] = 1; combined_map[i][default_cols-1] = 1
        mid = default_cols // 2
        combined_map[default_rows-1][mid-1] = 0; combined_map[default_rows-1][mid] = 0

    return combined_map

layer_files = [
    "./code/기말/assets/naye_home/나예집_충돌.csv"
]

NAYE_HOME_MAP = load_tiled_map(layer_files, 26, 15)

# ==================== 이미지 자원 관리 ====================
IMAGES = {}

def load_images():
    try:
        bg_img = pygame.image.load("./code/기말/assets/naye_home/나예집_배경.png").convert_alpha()
        IMAGES['naye_home_bg'] = pygame.transform.scale(bg_img, (26 * TILE_SIZE, 15 * TILE_SIZE))
    except Exception as e:
        pass

    try:
        naye_base = pygame.image.load("./code/기말/assets/image/나예 기본.png").convert_alpha()
        IMAGES['naye_base'] = pygame.transform.scale(naye_base, (1700, 900))
    except Exception as e:
        pass

    # 👇 [수정] 대기 모션 이미지 축소 (90x90 -> 65x65)
    try:
        idle_1 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/대기 모션_1.png").convert_alpha(), (65, 65))
        idle_2 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/대기 모션_2.png").convert_alpha(), (65, 65))
        idle_3 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/대기 모션_3.png").convert_alpha(), (65, 65))
        IMAGES['player_idle'] = [idle_1, idle_2, idle_2, idle_3, idle_3, idle_2, idle_2, idle_1]
    except Exception as e:
        pass

    # 👇 [수정] 걷기 모션 이미지 축소 (80x80 -> 60x60)
    try:
        run_1 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/걷기 모션_1.png").convert_alpha(), (60, 60))
        run_2 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/걷기 모션_2.png").convert_alpha(), (60, 60))
        run_3 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/걷기 모션_3.png").convert_alpha(), (60, 60))
        run_4 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/걷기 모션_4.png").convert_alpha(), (60, 60))
        run_5 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/걷기 모션_5.png").convert_alpha(), (60, 60))
        run_6 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/걷기 모션_6.png").convert_alpha(), (60, 60))

        IMAGES['player_run_right'] = [run_1, run_2, run_2, run_1, run_1, run_3, run_3, run_1, run_1, run_4, run_4, run_1, run_1, run_5, run_5, run_1, run_1, run_6, run_6, run_1]
        
        IMAGES['player_run_left'] = []
        for img in IMAGES['player_run_right']:
            flipped_img = pygame.transform.flip(img, True, False) 
            IMAGES['player_run_left'].append(flipped_img)
    except Exception as e:
        pass

    # 👇 [수정] 뒷면 걷기 모션 축소 (80x80 -> 60x60)
    try:
        up_1 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/뒷면 걷기_1.png").convert_alpha(), (60, 60))
        up_2 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/뒷면 걷기_2.png").convert_alpha(), (60, 60))
        up_3 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/뒷면 걷기_3.png").convert_alpha(), (60, 60))
        IMAGES['player_run_up'] = [up_1, up_2, up_2, up_3, up_3, up_2, up_2, up_1] 
    except Exception as e:
        pass

    # 👇 [수정] 정면 걷기 모션 축소 (80x80 -> 60x60, 75x75 -> 55x55)
    try:
        down_1 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/정면 걷기_1.png").convert_alpha(), (60, 60))
        down_2 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/정면 걷기_2.png").convert_alpha(), (60, 60))
        down_3 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/정면 걷기_3.png").convert_alpha(), (60, 60))
        down_4 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/정면 걷기_4.png").convert_alpha(), (55, 55))
        down_5 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/정면 걷기_5.png").convert_alpha(), (55, 55))
        IMAGES['player_run_down'] = [down_1, down_2, down_2, down_3, down_3, down_4, down_4, down_5, down_5, down_1] 
    except Exception as e:
        pass

    try:
        att1_1 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/공격 오_왼_1.png").convert_alpha(), (140, 140))
        att1_2 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/공격 오_왼_2.png").convert_alpha(), (140, 140))
        att1_3 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/공격 오_왼_3.png").convert_alpha(), (140, 140))
        att1_4 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/공격 오_왼_4.png").convert_alpha(), (140, 140))
        
        IMAGES['attack_1_right'] = [att1_1, att1_2, att1_3, att1_4]
        
        IMAGES['attack_1_left'] = [pygame.transform.flip(img, True, False) for img in IMAGES['attack_1_right']]
        IMAGES['attack_1_up'] = [pygame.transform.rotate(img, 90) for img in IMAGES['attack_1_right']]
        IMAGES['attack_1_down'] = [pygame.transform.rotate(img, -90) for img in IMAGES['attack_1_right']]

        att2_1 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/공격 왼_오_1.png").convert_alpha(), (140, 140))
        att2_2 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/공격 왼_오_2.png").convert_alpha(), (140, 140))
        att2_3 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/공격 왼_오_3.png").convert_alpha(), (140, 140))
        att2_4 = pygame.transform.scale(pygame.image.load("./code/기말/assets/image/공격 왼_오_4.png").convert_alpha(), (140, 140))
        
        IMAGES['attack_2_right'] = [att2_1, att2_2, att2_3, att2_4]
        
        IMAGES['attack_2_left'] = [pygame.transform.flip(img, True, False) for img in IMAGES['attack_2_right']]
        IMAGES['attack_2_up'] = [pygame.transform.rotate(img, 90) for img in IMAGES['attack_2_right']]
        IMAGES['attack_2_down'] = [pygame.transform.rotate(img, -90) for img in IMAGES['attack_2_right']]
        
    except Exception as e:
        pass

# ==================== 설정(Config) 및 세이브 ====================
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
        self.normal_speed = 350
        self.speed = self.normal_speed
        
        # 👇 [수정] 캐릭터 충돌 판정(어깨너비)을 더 작게 줄여서 좁은 틈을 잘 빠져나가게 했습니다! (15 -> 12)
        self.radius = 12 
        
        self.is_dashing = False
        self.dash_speed = 700            
        self.dash_duration = 0.15         
        self.dash_cooldown = 1.0          
        self.dash_time_left = 0           
        self.dash_cooldown_left = 0       
        self.dash_direction = pygame.math.Vector2(0, 0)
        
        self.is_attacking = False
        self.attack_step = 0       
        self.attack_timer = 0.0    
        self.combo_window = 0.0    
        
        self.move_lock_timer = 0.0 
        self.attack_cooldown_timer = 0.0 
        self.pose_hold_timer = 0.0 
        
        self.frame_index = 0.0          
        self.animation_speed = 6.0      
        self.facing = 'right'           
        self.afterimages = []

    def trigger_attack(self):
        if self.is_dashing or self.attack_cooldown_timer > 0: return False
        
        if not self.is_attacking and self.combo_window <= 0:
            self.is_attacking = True
            self.attack_step = 1
            self.attack_timer = 0.3   
            self.combo_window = 0.8   
            self.frame_index = 0.0
            self.move_lock_timer = 0.15 
            return True
            
        elif self.combo_window > 0 and self.attack_step == 1:
            if self.attack_timer < 0.15: 
                self.is_attacking = True
                self.attack_step = 2
                self.attack_timer = 0.3   
                self.combo_window = 0.0  
                self.frame_index = 0.0
                self.move_lock_timer = 0.15 
                self.attack_cooldown_timer = 0.3 
                return True
                
        return False

    def move(self, dt, room_w, room_h, target_x, target_y, current_map_idx=0, tile_map=None):
        if self.dash_cooldown_left > 0: self.dash_cooldown_left -= dt
        if self.move_lock_timer > 0: self.move_lock_timer -= dt
        if self.attack_cooldown_timer > 0: self.attack_cooldown_timer -= dt
        if self.pose_hold_timer > 0: self.pose_hold_timer -= dt
            
        for ghost in self.afterimages: ghost['timer'] -= dt
        self.afterimages = [g for g in self.afterimages if g['timer'] > 0]
        
        if self.attack_timer > 0:
            self.attack_timer -= dt
            if self.attack_timer <= 0:
                self.is_attacking = False
                self.pose_hold_timer = 0.5 
                
        if self.combo_window > 0:
            self.combo_window -= dt

        if not self.is_attacking and self.pose_hold_timer <= 0:
            dx = target_x - self.pos.x
            dy = target_y - self.pos.y
            if abs(dx) > abs(dy):
                self.facing = 'right' if dx > 0 else 'left'
            else:
                self.facing = 'down' if dy > 0 else 'up'

        keys = pygame.key.get_pressed()
        direction = pygame.math.Vector2(0, 0)
        
        if self.move_lock_timer <= 0 and not self.is_dashing:
            if keys[config['keys']['UP']]: direction.y -= 1
            if keys[config['keys']['DOWN']]: direction.y += 1
            if keys[config['keys']['LEFT']]: direction.x -= 1
            if keys[config['keys']['RIGHT']]: direction.x += 1

        if direction.length() > 0: 
            direction = direction.normalize()
            self.pose_hold_timer = 0.0

        move_x, move_y = 0, 0

        if keys[pygame.K_SPACE] and self.dash_cooldown_left <= 0 and direction.length() > 0 and self.move_lock_timer <= 0 and not self.is_dashing:
            self.is_dashing = True
            self.dash_time_left = self.dash_duration
            self.dash_cooldown_left = self.dash_cooldown
            self.speed = self.dash_speed
            self.dash_direction = direction

        if self.is_dashing:
            self.dash_time_left -= dt
            if self.dash_time_left <= 0:
                self.is_dashing = False
                self.speed = self.normal_speed
            else:
                move_x = self.dash_direction.x * self.speed * dt
                move_y = self.dash_direction.y * self.speed * dt
        else:
            move_x = direction.x * self.speed * dt
            move_y = direction.y * self.speed * dt

        can_move_x, can_move_y = True, True
        if current_map_idx == -1 and tile_map:
            passable_tiles = [0] 

            check_x = self.pos.x + move_x + (self.radius if move_x > 0 else -self.radius)
            c_x = int(check_x // TILE_SIZE)
            r_cur = int(self.pos.y // TILE_SIZE)
            if move_x != 0 and 0 <= c_x < len(tile_map[0]) and 0 <= r_cur < len(tile_map):
                if tile_map[r_cur][c_x] not in passable_tiles: 
                    can_move_x = False

            check_y = self.pos.y + move_y + (self.radius if move_y > 0 else -self.radius)
            c_y = int(check_y // TILE_SIZE)
            c_cur = int(self.pos.x // TILE_SIZE)
            if move_y != 0 and 0 <= c_y < len(tile_map) and 0 <= c_cur < len(tile_map[0]):
                if tile_map[c_y][c_cur] not in passable_tiles: 
                    can_move_y = False

        if can_move_x: self.pos.x += move_x
        if can_move_y: self.pos.y += move_y
            
        if direction.length() == 0 and not self.is_dashing:
            self.frame_index += self.animation_speed * dt
        else:
            self.frame_index += (self.animation_speed * 1.5) * dt

        self.pos.x = max(self.radius, min(room_w - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(room_h - self.radius, self.pos.y))

    def draw(self, surface, cam_x, cam_y):
        draw_x = int(self.pos.x - cam_x)
        draw_y = int(self.pos.y - cam_y)
        
        keys = pygame.key.get_pressed()
        is_moving = (keys[config['keys']['UP']] or keys[config['keys']['DOWN']] or keys[config['keys']['LEFT']] or keys[config['keys']['RIGHT']])
        
        if self.move_lock_timer > 0:
            is_moving = False 

        base_anim_list = []
        if is_moving or self.is_dashing:
            if self.facing == 'right': base_anim_list = IMAGES.get('player_run_right', [])
            elif self.facing == 'left': base_anim_list = IMAGES.get('player_run_left', [])
            elif self.facing == 'up': base_anim_list = IMAGES.get('player_run_up', [])
            elif self.facing == 'down': base_anim_list = IMAGES.get('player_run_down', [])
        
        elif self.is_attacking or self.move_lock_timer > 0 or self.attack_cooldown_timer > 0 or self.pose_hold_timer > 0:
            run_anim = []
            if self.facing == 'right': run_anim = IMAGES.get('player_run_right', [])
            elif self.facing == 'left': run_anim = IMAGES.get('player_run_left', [])
            elif self.facing == 'up': run_anim = IMAGES.get('player_run_up', [])
            elif self.facing == 'down': run_anim = IMAGES.get('player_run_down', [])
            
            if len(run_anim) > 0:
                base_anim_list = [run_anim[0]] 
            else:
                base_anim_list = IMAGES.get('player_idle', [])
        else:
            base_anim_list = IMAGES.get('player_idle', [])
            
        if len(base_anim_list) == 0:
            base_anim_list = IMAGES.get('player_idle', [])

        if len(base_anim_list) > 0:
            current_frame = int(self.frame_index) % len(base_anim_list)
            base_img = base_anim_list[current_frame]
            
            if base_anim_list == IMAGES.get('player_idle', []) and self.facing == 'left':
                base_img = pygame.transform.flip(base_img, True, False)
                
            if self.is_dashing:
                self.afterimages.append({
                    'pos': pygame.math.Vector2(self.pos.x, self.pos.y),
                    'img': base_img,
                    'timer': 0.2 
                })

            for ghost in self.afterimages:
                alpha = max(0, min(255, int(120 * (ghost['timer'] / 0.2))))
                ghost_img = ghost['img'].copy()
                ghost_img.set_alpha(alpha)
                gx, gy = int(ghost['pos'].x - cam_x), int(ghost['pos'].y - cam_y)
                surface.blit(ghost_img, ghost_img.get_rect(center=(gx, gy)))
                
            base_rect = base_img.get_rect(center=(draw_x, draw_y))
            surface.blit(base_img, base_rect)
                
        elif 'player' in IMAGES: 
            surface.blit(IMAGES['player'], (draw_x - self.radius, draw_y - self.radius))
        else:
            pygame.draw.circle(surface, PLAYER_COLOR, (draw_x, draw_y), self.radius)

        if self.is_attacking:
            attack_anim_list = []
            if self.attack_step == 1:
                if self.facing == 'right': attack_anim_list = IMAGES.get('attack_1_right', [])
                elif self.facing == 'left': attack_anim_list = IMAGES.get('attack_1_left', [])
                elif self.facing == 'up': attack_anim_list = IMAGES.get('attack_1_up', [])
                elif self.facing == 'down': attack_anim_list = IMAGES.get('attack_1_down', [])
            elif self.attack_step == 2:
                if self.facing == 'right': attack_anim_list = IMAGES.get('attack_2_right', [])
                elif self.facing == 'left': attack_anim_list = IMAGES.get('attack_2_left', [])
                elif self.facing == 'up': attack_anim_list = IMAGES.get('attack_2_up', [])
                elif self.facing == 'down': attack_anim_list = IMAGES.get('attack_2_down', [])

            if len(attack_anim_list) > 0:
                progress = 1.0 - (self.attack_timer / 0.3)
                att_frame = int(progress * len(attack_anim_list))
                if att_frame >= len(attack_anim_list): att_frame = len(attack_anim_list) - 1
                
                attack_img = attack_anim_list[att_frame]
                
                # 👇 [수정] 캐릭터가 작아졌으므로 칼이 몸에서 나가는 거리(offset)도 몸 쪽으로 땡겨줍니다. (35,50 -> 30,40)
                offset_x = 30  
                offset_y = 40  
                
                ax, ay = draw_x, draw_y
                if self.facing == 'right': ax += offset_x
                elif self.facing == 'left': ax -= offset_x
                elif self.facing == 'up': ay -= offset_y
                elif self.facing == 'down': ay += offset_y
                
                attack_rect = attack_img.get_rect(center=(ax, ay))
                surface.blit(attack_img, attack_rect)

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
            self.speed, self.radius, self.hp, self.max_hp = 120, 30, 50, 50 
            self.color = BOSS_COLOR
        else:
            self.speed, self.radius, self.hp, self.max_hp = 200, 14, 5, 5 
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
    
    screen.fill((20, 20, 25))
    try:
        loading_font = get_korean_font(40, bold=True)
        text = loading_font.render("이미지 데이터를 불러오는 중입니다...", True, (255, 255, 255))
        screen.blit(text, (current_width // 2 - text.get_width() // 2, current_height // 2))
    except: pass
    pygame.display.flip()
    
    load_images()
    
    app_state = APP_MAIN_MENU 
    current_map_idx = -1 
    cleared_rooms = [False] * len(MAP_DATA)
    cols, rows = 26, 15
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
    
    btn_window = Button(0, 330, 320, 60, "창 모드 (1600x900)")
    btn_borderless = Button(0, 400, 320, 60, "테두리 없는 전체화면")
    btn_fullscreen = Button(0, 470, 320, 60, "독점 전체화면")
    
    btn_vol_down = Button(-100, 310, 60, 60, "-", 40); btn_vol_up = Button(100, 310, 60, 60, "+", 40)
    btn_combat_vol_down = Button(-100, 440, 60, 60, "-", 40); btn_combat_vol_up = Button(100, 440, 60, 60, "+", 40)
    btn_voice_vol_down = Button(-100, 570, 60, 60, "-", 40); btn_voice_vol_up = Button(100, 570, 60, 60, "+", 40)
    
    key_buttons = {'UP': Button(80, 320, 220, 60, ""), 'DOWN': Button(80, 390, 220, 60, ""), 'LEFT': Button(80, 460, 220, 60, ""), 'RIGHT': Button(80, 530, 220, 60, "")}
    key_labels = {'UP': "위 (UP):", 'DOWN': "아래 (DOWN):", 'LEFT': "왼쪽 (LEFT):", 'RIGHT': "오른쪽 (RIGHT):"}

    btn_close_overlay = Button(0, 650, 260, 70, "닫기", base_col=(80, 80, 90))
    btn_return_main = Button(-140, 650, 260, 70, "나가기", base_col=(180, 50, 50))
    btn_close_settings_game = Button(140, 650, 260, 70, "설정 닫기", base_col=(80, 80, 90))

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
                                app_state = APP_MAIN_MENU; current_overlay = None
                                current_map_idx = -1 
                                cols, rows = 26, 15 
                                room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                                player = Player(room_w, room_h)
                                bullets.clear(); enemies.clear(); room_state = ROOM_WAITING; current_play_time = 0.0
                                cleared_rooms = [False] * len(MAP_DATA) 

                        if current_tab == "VIDEO":
                            if btn_window.is_clicked(event, scaled_mouse_pos): update_display('WINDOW')
                            if btn_borderless.is_clicked(event, scaled_mouse_pos): update_display('BORDERLESS')
                            if btn_fullscreen.is_clicked(event, scaled_mouse_pos): update_display('FULLSCREEN')
                        elif current_tab == "AUDIO":
                            txt1 = font.render(f"마스터 볼륨: {config['volume']}%", True, (255, 255, 255))
                            display_surface.blit(txt1, (center_x - txt1.get_width()//2, 275))
                            btn_vol_down.draw(display_surface, center_x, scaled_mouse_pos); btn_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
                            
                            txt2 = font.render(f"전투 볼륨: {config['combat_volume']}%", True, (255, 255, 255))
                            display_surface.blit(txt2, (center_x - txt2.get_width()//2, 405))
                            btn_combat_vol_down.draw(display_surface, center_x, scaled_mouse_pos); btn_combat_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
                            
                            txt3 = font.render(f"음성 볼륨: {config['voice_volume']}%", True, (255, 255, 255))
                            display_surface.blit(txt3, (center_x - txt3.get_width()//2, 535))
                            btn_voice_vol_down.draw(display_surface, center_x, scaled_mouse_pos); btn_voice_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
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
                                "cleared_rooms": cleared_rooms,
                                "enemies": [{"x": e.pos.x, "y": e.pos.y, "hp": e.hp, "is_boss": e.is_boss} for e in enemies]
                            }
                            write_save_data(saves_data); confirm_save_slot = None; current_overlay = None 
                        elif btn_confirm_no.is_clicked(event, scaled_mouse_pos): confirm_save_slot = None
                    else:
                        if btn_close_overlay.is_clicked(event, scaled_mouse_pos): 
                            current_overlay = None
                            continue
                            
                        for i in range(3):
                            slot_key = f"slot_{i+1}"
                            if saves_data[slot_key] and delete_buttons[i].is_clicked(event, scaled_mouse_pos):
                                confirm_delete_slot = i + 1; break 
                            if slot_buttons[i].is_clicked(event, scaled_mouse_pos):
                                if current_overlay == 'SAVE': confirm_save_slot = i + 1 
                                elif current_overlay == 'LOAD' and saves_data[slot_key]:
                                    sd = saves_data[slot_key]
                                    current_map_idx = sd.get("map_idx", -1)
                                    cleared_rooms = sd.get("cleared_rooms", [False] * len(MAP_DATA))
                                    
                                    if current_map_idx == -1:
                                        cols, rows = 26, 15 
                                    else:
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
                    current_map_idx = -1
                    cleared_rooms = [False] * len(MAP_DATA)
                    cols, rows = 26, 15 
                    room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                    player = Player(room_w, room_h)
                    
                    player.pos.x = room_w // 2
                    player.pos.y = 250
                    
                    bullets.clear(); enemies.clear()
                    room_state = ROOM_CLEARED
                    current_play_time = 0.0
                    app_state = APP_PLAYING
                elif menu_btn_continue.is_clicked(event, scaled_mouse_pos): current_overlay = 'LOAD'
                elif menu_btn_settings.is_clicked(event, scaled_mouse_pos): current_overlay = 'SETTINGS'
                elif menu_btn_quit.is_clicked(event, scaled_mouse_pos): running = False

            elif app_state == APP_PLAYING and room_state in [ROOM_COMBAT, ROOM_CLEARED]:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = scaled_mouse_pos
                    if VIEW_MARGIN_X <= mx <= VIEW_MARGIN_X + VIEW_W and VIEW_MARGIN_Y <= my <= VIEW_MARGIN_Y + VIEW_H:
                        
                        target_x = mx - VIEW_MARGIN_X + camera_x
                        target_y = my - VIEW_MARGIN_Y + camera_y
                        dx = target_x - player.pos.x
                        dy = target_y - player.pos.y
                        if abs(dx) > abs(dy): player.facing = 'right' if dx > 0 else 'left'
                        else: player.facing = 'down' if dy > 0 else 'up'
                        
                        if player.trigger_attack():
                            # 👇 [수정] 작아진 캐릭터 크기에 맞춰 공격 위치도 몸 쪽으로 땡겨줌 (30, 40)
                            offset_x = 30
                            offset_y = 40
                            hx, hy = player.pos.x, player.pos.y
                            
                            if player.facing == 'right': hx += offset_x
                            elif player.facing == 'left': hx -= offset_x
                            elif player.facing == 'up': hy -= offset_y
                            elif player.facing == 'down': hy += offset_y
                            
                            hitbox_pos = pygame.math.Vector2(hx, hy)
                            hitbox_radius = 70 
                            
                            for enemy in enemies[:]:
                                if hitbox_pos.distance_to(enemy.pos) < hitbox_radius + enemy.radius:
                                    dmg = 2 if player.attack_step == 2 else 1
                                    enemy.hp -= dmg
                                    if enemy.hp <= 0:
                                        enemies.remove(enemy)

        # ==================== 게임 로직 처리 ====================
        if not current_overlay and app_state == APP_PLAYING:
            mx, my = scaled_mouse_pos
            world_mouse_x = mx - VIEW_MARGIN_X + camera_x
            world_mouse_y = my - VIEW_MARGIN_Y + camera_y
            
            player.move(dt, room_w, room_h, world_mouse_x, world_mouse_y, current_map_idx, NAYE_HOME_MAP)
            current_play_time += dt

            if room_w >= VIEW_W: camera_x = max(0, min(player.pos.x - VIEW_W / 2, room_w - VIEW_W))
            else: camera_x = -(VIEW_W - room_w) // 2
                
            if room_h >= VIEW_H: camera_y = max(0, min(player.pos.y - VIEW_H / 2, room_h - VIEW_H))
            else: camera_y = -(VIEW_H - room_h) // 2

            if room_state == ROOM_WAITING:
                if current_map_idx == -1:
                    room_state = ROOM_CLEARED
                elif not cleared_rooms[current_map_idx]: 
                    room_state = ROOM_COMBAT
                    if current_map_idx == len(MAP_DATA) - 1:
                        enemies.append(Enemy(room_w // 2, room_h // 2, is_boss=True))
                    else:
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
                    if current_map_idx >= 0:
                        cleared_rooms[current_map_idx] = True
                
            elif room_state in [ROOM_WAITING, ROOM_CLEARED]:
                for bullet in bullets[:]: bullet.update(dt)
                
                if room_w//2 - TILE_SIZE < player.pos.x < room_w//2 + TILE_SIZE:
                    
                    if player.pos.y < 40 and current_map_idx >= 0 and current_map_idx < len(MAP_DATA) - 1:
                        current_map_idx += 1
                        cols, rows = MAP_DATA[current_map_idx]['cols'], MAP_DATA[current_map_idx]['rows']
                        room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                        player.pos.x, player.pos.y = room_w // 2, room_h - 90
                        room_state = ROOM_CLEARED if cleared_rooms[current_map_idx] else ROOM_WAITING
                        bullets.clear(); enemies.clear()
                    
                    elif player.pos.y > room_h - 40:
                        if current_map_idx == -1: 
                            current_map_idx = 0
                            cols, rows = MAP_DATA[0]['cols'], MAP_DATA[0]['rows']
                            room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                            player.pos.x, player.pos.y = room_w // 2, room_h - 90 
                            room_state = ROOM_CLEARED if cleared_rooms[0] else ROOM_WAITING
                            bullets.clear(); enemies.clear()
                            
                        elif current_map_idx > 0:
                            current_map_idx -= 1
                            cols, rows = MAP_DATA[current_map_idx]['cols'], MAP_DATA[current_map_idx]['rows']
                            room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                            player.pos.x, player.pos.y = room_w // 2, 90
                            room_state = ROOM_CLEARED if cleared_rooms[current_map_idx] else ROOM_WAITING
                            bullets.clear(); enemies.clear()

        # ==================== 렌더링 (그리기) ====================
        display_surface.fill((0, 0, 0)) 

        if app_state == APP_MAIN_MENU:
            display_surface.blit(title_font.render("단죄의 시간", True, (255, 255, 255)), (150, 150))
            display_surface.blit(font.render("Time of Condemnation", True, (150, 150, 150)), (160, 280))
            menu_btn_start.draw(display_surface, center_x, scaled_mouse_pos)
            menu_btn_continue.draw(display_surface, center_x, scaled_mouse_pos)
            menu_btn_settings.draw(display_surface, center_x, scaled_mouse_pos)
            menu_btn_quit.draw(display_surface, center_x, scaled_mouse_pos)

        elif app_state == APP_PLAYING:
            view_surface.fill((0, 0, 0))
            pygame.draw.rect(view_surface, ROOM_COLOR, (-camera_x, -camera_y, room_w, room_h))
            
            if current_map_idx >= 0:
                for i in range(cols + 1):
                    x_pos = i * TILE_SIZE - camera_x
                    pygame.draw.line(view_surface, GRID_COLOR, (x_pos, -camera_y), (x_pos, room_h - camera_y), 1)
                for i in range(rows + 1):
                    y_pos = i * TILE_SIZE - camera_y
                    pygame.draw.line(view_surface, GRID_COLOR, (-camera_x, y_pos), (room_w - camera_x, y_pos), 1)

                door_color = DOOR_OPEN_COLOR if room_state in [ROOM_WAITING, ROOM_CLEARED] else DOOR_LOCKED_COLOR
                door_w = TILE_SIZE * 2
                door_half_w = door_w // 2
                
                if current_map_idx < len(MAP_DATA) - 1:
                    pygame.draw.rect(view_surface, door_color, (room_w//2 - door_half_w - camera_x, -camera_y, door_w, 30))
                if current_map_idx > 0:
                    pygame.draw.rect(view_surface, door_color, (room_w//2 - door_half_w - camera_x, room_h - 30 - camera_y, door_w, 30))
                    
            else:
                if 'naye_home_bg' in IMAGES:
                    view_surface.blit(IMAGES['naye_home_bg'], (-camera_x, -camera_y))

            if room_state == ROOM_COMBAT:
                for enemy in enemies: enemy.draw(view_surface, camera_x, camera_y)
            for bullet in bullets: bullet.draw(view_surface, camera_x, camera_y)
            player.draw(view_surface, camera_x, camera_y)

            display_surface.blit(view_surface, (VIEW_MARGIN_X, VIEW_MARGIN_Y))

            display_surface.blit(font.render(f"진행 시간: {format_time(current_play_time)} | [ESC] 설정 | [Q] 저장", True, (200, 200, 200)), (40, 30))
            
            map_name_str = "나예 집" if current_map_idx == -1 else MAP_DATA[current_map_idx]['name']
            map_name_surf = large_font.render(f"- {map_name_str} -", True, (255, 255, 255))
            display_surface.blit(map_name_surf, (LOGICAL_WIDTH - map_name_surf.get_width() - 40, 20))

            if 'naye_base' in IMAGES:
                illust_x = VIEW_MARGIN_X // 2
                illust_y = LOGICAL_HEIGHT - 550
                ui_rect = IMAGES['naye_base'].get_rect(center=(illust_x, illust_y))
                display_surface.blit(IMAGES['naye_base'], ui_rect)
                
                name_tag = font.render("나예", True, (255, 255, 255))
                name_rect = name_tag.get_rect(center=(illust_x, ui_rect.bottom + 30))
                
                bg_rect = pygame.Rect(0, 0, 90, 40)
                bg_rect.center = name_rect.center
                pygame.draw.rect(display_surface, (50, 50, 60), bg_rect, border_radius=5)
                display_surface.blit(name_tag, name_rect)

            if current_map_idx >= 0:
                minimap_room_size = 24  
                minimap_margin = 8      
                minimap_start_x = LOGICAL_WIDTH - 80 
                minimap_start_y = 90    

                for i in range(len(MAP_DATA)):
                    draw_idx = (len(MAP_DATA) - 1) - i
                    rect_x = minimap_start_x
                    rect_y = minimap_start_y + i * (minimap_room_size + minimap_margin)

                    is_cleared = cleared_rooms[draw_idx]
                    is_current = (draw_idx == current_map_idx)
                    is_adjacent = abs(draw_idx - current_map_idx) == 1 
                    
                    if not (is_cleared or is_current or is_adjacent): continue

                    if i < len(MAP_DATA) - 1:
                        next_draw_idx = draw_idx - 1
                        next_is_visible = cleared_rooms[next_draw_idx] or (next_draw_idx == current_map_idx) or (abs(next_draw_idx - current_map_idx) == 1)
                        if next_is_visible:
                            pygame.draw.rect(display_surface, (100, 100, 100), 
                                             (rect_x + minimap_room_size//2 - 2, rect_y + minimap_room_size, 4, minimap_margin))

                    if is_current:
                        bg_color = (200, 200, 200)
                        border_color = (255, 255, 255)
                    elif is_cleared:
                        bg_color = (70, 70, 70)
                        border_color = (130, 130, 130)
                    else: 
                        bg_color = (30, 30, 30)
                        border_color = (80, 80, 80)

                    pygame.draw.rect(display_surface, bg_color, (rect_x, rect_y, minimap_room_size, minimap_room_size), border_radius=3)
                    pygame.draw.rect(display_surface, border_color, (rect_x, rect_y, minimap_room_size, minimap_room_size), 2, border_radius=3)

                    if is_current:
                        pygame.draw.circle(display_surface, PLAYER_COLOR, (rect_x + minimap_room_size//2, rect_y + minimap_room_size//2), 5)

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
                    txt1 = font.render(f"마스터 볼륨: {config['volume']}%", True, (255, 255, 255))
                    display_surface.blit(txt1, (center_x - txt1.get_width()//2, 275))
                    btn_vol_down.draw(display_surface, center_x, scaled_mouse_pos); btn_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
                    
                    txt2 = font.render(f"전투 볼륨: {config['combat_volume']}%", True, (255, 255, 255))
                    display_surface.blit(txt2, (center_x - txt2.get_width()//2, 405))
                    btn_combat_vol_down.draw(display_surface, center_x, scaled_mouse_pos); btn_combat_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
                    
                    txt3 = font.render(f"음성 볼륨: {config['voice_volume']}%", True, (255, 255, 255))
                    display_surface.blit(txt3, (center_x - txt3.get_width()//2, 535))
                    btn_voice_vol_down.draw(display_surface, center_x, scaled_mouse_pos); btn_voice_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
                elif current_tab == "KEYS":
                    for action, btn in key_buttons.items():
                        if btn.is_clicked(event, scaled_mouse_pos): waiting_for_key = action

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
                    if btn_close_overlay.is_clicked(event, scaled_mouse_pos): 
                        current_overlay = None
                    else:
                        ts = large_font.render("진행상황 저장" if current_overlay == 'SAVE' else "게임 불러오기", True, (255, 255, 255))
                        display_surface.blit(ts, (center_x - ts.get_width()//2, 170))
                        for i in range(3): 
                            slot_buttons[i].draw(display_surface, center_x, scaled_mouse_pos)
                            if saves_data[f"slot_{i+1}"]: delete_buttons[i].draw(display_surface, center_x, scaled_mouse_pos)
                        btn_close_overlay.draw(display_surface, center_x, scaled_mouse_pos)

        screen.blit(pygame.transform.scale(display_surface, (current_width, current_height)), (0, 0))
        pygame.display.flip()
    pygame.quit(); sys.exit()

if __name__ == "__main__": main()