import os
import pygame
import sys
import json
import csv
import math 
import random 
import heapq
import threading

# ==================== 마법의 절대 경로 함수 ====================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
# ===============================================================

# Pygame 및 Mixer 초기화
pygame.init()
pygame.mixer.init()

# ==================== 한글 폰트 자동 탐색 함수 ====================
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

# 👇 노트북 등 작은 화면 대응: 화면 크기의 80%로 초기 창 설정
if DESKTOP_W < 1600 or DESKTOP_H < 900:
    current_width, current_height = max(1024, int(DESKTOP_W * 0.8)), max(576, int(DESKTOP_H * 0.8))
else:
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
APP_MAIN_MENU = 0; APP_STORY = 1; APP_PLAYING = 2; APP_DEATH_ANIMATION = 3; APP_GAME_OVER = 4; APP_ENDING = 5; APP_CREDITS = 6

current_difficulty = 'normal'
DIFF = {
    'easy':   {'dmg_mode': 'flat', 'dmg_value': 2, 'boss_ult_dmg': 20, 'hp_mult': 1.0, 'proj_speed_mult': 0.8, 'warn_mult': 1.3},
    'normal': {'dmg_mode': 'normal', 'dmg_value': 0, 'boss_ult_dmg': 50, 'hp_mult': 1.0, 'proj_speed_mult': 1.0, 'warn_mult': 1.0},
    'hard':   {'dmg_mode': 'add',   'dmg_value': 2, 'boss_ult_dmg': 99, 'hp_mult': 1.5, 'proj_speed_mult': 1.2, 'warn_mult': 0.7}
}

TILE_SIZE = 32 

MAP_DATA = [
    {"name": "교실", "cols": 30, "rows": 28},
    {"name": "화장실", "cols": 30, "rows": 20}, 
    {"name": "보건실", "cols": 20, "rows": 30},
    {"name": "체육관", "cols": 60, "rows": 60},
    {"name": "급식실", "cols": 50, "rows": 60},
    {"name": "컴퓨터실", "cols": 40, "rows": 28},
    {"name": "도서관", "cols": 60, "rows": 50},
    {"name": "교장실", "cols": 80, "rows": 60} 
]

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
                            if row_idx >= default_rows or col_idx >= default_cols: continue
                            raw_val = int(val_str)
                            real_val = raw_val & 0x0FFFFFFF
                            if real_val == 2: combined_map[row_idx][col_idx] = 2
                            elif real_val == 3: combined_map[row_idx][col_idx] = 3
                            elif real_val == 4: combined_map[row_idx][col_idx] = 4
                            elif real_val != -1 and real_val != 0: combined_map[row_idx][col_idx] = 1
            except Exception as e: print(f"맵 로딩 오류 ({filepath}): {e}")

    if not loaded_any:
        combined_map = [[0 for _ in range(default_cols)] for _ in range(default_rows)]
        for i in range(default_cols): combined_map[0][i] = 1; combined_map[default_rows-1][i] = 1
        for i in range(default_rows): combined_map[i][0] = 1; combined_map[i][default_cols-1] = 1
        mid = default_cols // 2
        combined_map[default_rows-1][mid-1] = 0; combined_map[default_rows-1][mid] = 0

    return combined_map

# 맵 파일 로드
layer_files_home = [resource_path("assets/naye_home/나예집_충돌.csv")]
NAYE_HOME_MAP = load_tiled_map(layer_files_home, 26, 15)

layer_files_class = [resource_path("assets/school_class/교실__충돌_최종수정.csv"), resource_path("assets/school_class/교실_충돌.csv")]
CLASSROOM_MAP = load_tiled_map(layer_files_class, MAP_DATA[0]['cols'], MAP_DATA[0]['rows'])

layer_files_toilet = [resource_path("assets/school_toilet/화장실_충돌_4_수정.csv"), resource_path("assets/school_toilet/화장실_충돌.csv")]
TOILET_MAP = load_tiled_map(layer_files_toilet, MAP_DATA[1]['cols'], MAP_DATA[1]['rows'])

layer_files_health = [resource_path("assets/school_health office/보건실_충돌_수정.csv"), resource_path("assets/school_health office/보건실_충돌.csv")]
HEALTH_MAP = load_tiled_map(layer_files_health, MAP_DATA[2]['cols'], MAP_DATA[2]['rows'])

layer_files_gym = [resource_path("assets/school_gym/체육관_충돌_수정.csv"), resource_path("assets/school_gym/체육관_충돌.csv")]
GYM_MAP = load_tiled_map(layer_files_gym, MAP_DATA[3]['cols'], MAP_DATA[3]['rows'])

layer_files_cafeteria = [resource_path("assets/school_cafeteria/급식실_충돌_수정.csv"), resource_path("assets/school_cafeteria/급식실_충돌.csv")]
CAFETERIA_MAP = load_tiled_map(layer_files_cafeteria, MAP_DATA[4]['cols'], MAP_DATA[4]['rows'])

layer_files_computer = [resource_path("assets/school_computer room/컴퓨터실_충돌_수정.csv"), resource_path("assets/school_computer room/컴퓨터실_충돌.csv")]
COMPUTER_MAP = load_tiled_map(layer_files_computer, MAP_DATA[5]['cols'], MAP_DATA[5]['rows'])

layer_files_library = [resource_path("assets/school_library/도서관_충돌_수정.csv"), resource_path("assets/school_library/도서관_충돌.csv")]
LIBRARY_MAP = load_tiled_map(layer_files_library, MAP_DATA[6]['cols'], MAP_DATA[6]['rows'])

layer_files_principal = [resource_path("assets/school_principal office/교장실_충돌_수정.csv"), resource_path("assets/school_principal office/교장실_충돌.csv")]
PRINCIPAL_MAP = load_tiled_map(layer_files_principal, MAP_DATA[7]['cols'], MAP_DATA[7]['rows'])

# ==================== 이미지 자원 관리 ====================
IMAGES = {}

def load_images():
    try: IMAGES['title_bg'] = pygame.transform.scale(pygame.image.load(resource_path("assets/image/시작배경.png")).convert(), (LOGICAL_WIDTH, LOGICAL_HEIGHT))
    except: pass
    try: IMAGES['naye_home_bg'] = pygame.transform.scale(pygame.image.load(resource_path("assets/naye_home/나예집_배경.png")).convert_alpha(), (26 * TILE_SIZE, 15 * TILE_SIZE))
    except: pass
    try: IMAGES['class_bg'] = pygame.transform.scale(pygame.image.load(resource_path("assets/school_class/학교_교실.png")).convert_alpha(), (MAP_DATA[0]['cols'] * TILE_SIZE, MAP_DATA[0]['rows'] * TILE_SIZE))
    except: pass
    try: IMAGES['toilet_bg'] = pygame.transform.scale(pygame.image.load(resource_path("assets/school_toilet/학교_화장실.png")).convert_alpha(), (MAP_DATA[1]['cols'] * TILE_SIZE, MAP_DATA[1]['rows'] * TILE_SIZE))
    except: pass
    try: IMAGES['health_bg'] = pygame.transform.scale(pygame.image.load(resource_path("assets/school_health office/학교_보건실.png")).convert_alpha(), (MAP_DATA[2]['cols'] * TILE_SIZE, MAP_DATA[2]['rows'] * TILE_SIZE))
    except: pass
    try: IMAGES['gym_bg'] = pygame.transform.scale(pygame.image.load(resource_path("assets/school_gym/학교_체육관.png")).convert_alpha(), (MAP_DATA[3]['cols'] * TILE_SIZE, MAP_DATA[3]['rows'] * TILE_SIZE))
    except: pass
    try: IMAGES['cafeteria_bg'] = pygame.transform.scale(pygame.image.load(resource_path("assets/school_cafeteria/학교_급식실.png")).convert_alpha(), (MAP_DATA[4]['cols'] * TILE_SIZE, MAP_DATA[4]['rows'] * TILE_SIZE))
    except: pass
    try: IMAGES['computer_bg'] = pygame.transform.scale(pygame.image.load(resource_path("assets/school_computer room/학교_컴퓨터실.png")).convert_alpha(), (MAP_DATA[5]['cols'] * TILE_SIZE, MAP_DATA[5]['rows'] * TILE_SIZE))
    except: pass
    try: IMAGES['library_bg'] = pygame.transform.scale(pygame.image.load(resource_path("assets/school_library/학교_도서관.png")).convert_alpha(), (MAP_DATA[6]['cols'] * TILE_SIZE, MAP_DATA[6]['rows'] * TILE_SIZE))
    except: pass
    try:
        IMAGES['principal_bg1'] = pygame.transform.scale(pygame.image.load(resource_path("assets/school_principal office/학교_교장실1.png")).convert_alpha(), (MAP_DATA[7]['cols'] * TILE_SIZE, MAP_DATA[7]['rows'] * TILE_SIZE))
        IMAGES['principal_bg2'] = pygame.transform.scale(pygame.image.load(resource_path("assets/school_principal office/학교_교장실2.png")).convert_alpha(), (MAP_DATA[7]['cols'] * TILE_SIZE, MAP_DATA[7]['rows'] * TILE_SIZE))
    except: pass
    try:
        # 치약 탄막(큰 버블)용 이미지 로드
        bubble_raw = pygame.image.load(resource_path("assets/school_toilet/버블_1.png")).convert_alpha()
        IMAGES['bubble_large'] = pygame.transform.scale(bubble_raw, (88, 88))
        # 터진 탄막(작은 버블)용 이미지 로드
        IMAGES['bubble_small'] = pygame.transform.scale(bubble_raw, (50, 50))
    except: pass
        
    try:
        # 1. 이미지 원본 로드
        pencil_tip_raw = pygame.image.load(resource_path("assets/school_class/심_1.png")).convert_alpha()
        
        # 2. 원본 크기 가져오기
        w, h = pencil_tip_raw.get_size()
        
        # 3. 원하는 배율 설정 (예: 2.0은 2배, 1.5는 1.5배)
        scale_factor = 0.35
        
        # 4. 비율을 유지하며 스케일 조정 (int로 감싸서 정수로 변환)
        new_w = int(w * scale_factor)
        new_h = int(h * scale_factor)
        
        IMAGES['pencil_tip'] = pygame.transform.scale(pencil_tip_raw, (new_w, new_h))
        # 심_1 이미지 크기에 맞는 충돌 판정 반지름 저장 (이미지의 짧은 변의 절반)
        IMAGES['pencil_tip_radius'] = min(new_w, new_h) // 2
        
    except: pass
        
    for m_type, k_name in [('eraser', '칠판지우개'), ('chalk', '분필'), ('pencil', '연필')]:
        size = (63, 63) if m_type == 'eraser' else (126, 126)
        for i in range(1, 4):
            try: 
                IMAGES[f'{m_type}_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_class/{k_name}_{i}.png")).convert_alpha(), size)
            except: pass
            # 👇 화장실 몬스터 이미지 로딩 추가
    for m_type, k_name in [('soap', '비누'), ('toothpaste', '치약'), ('toothbrush', '칫솔')]:
        size = (80, 80)  # 필요에 따라 크기 조절
        for i in range(1, 5):
            try:
                IMAGES[f'{m_type}_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_toilet/{k_name}_{i}.png")).convert_alpha(), size)
            except: pass

            # 👇 보건실 몬스터 이미지 로딩 추가 (붕대, 주사기, 알약)
    for m_type, k_name in [('bandage', '붕대'), ('syringe', '주사기')]:
        size = (110, 110)
        for i in range(1, 4):
            try:
                IMAGES[f'{m_type}_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_health office/{k_name}_{i}.png")).convert_alpha(), size)
            except: pass
    
    # 알약 보스 이미지 로딩
    for i in range(1, 3):
        try:
            IMAGES[f'pill_boss_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_health office/알약_{i}.png")).convert_alpha(), (100, 100))
        except: pass
    
    # 붕대끈 탄막 이미지 로딩
    try:
        IMAGES['bandage_rope'] = pygame.transform.scale(pygame.image.load(resource_path("assets/school_health office/붕대끈_1.png")).convert_alpha(), (130, 130))
    except: pass
    
    # 빨간 알약 이미지 로딩 (pill_bullet_red)
    try:
        IMAGES['pill_bullet_red'] = pygame.transform.scale(pygame.image.load(resource_path("assets/school_health office/빨간알약_1.png")).convert_alpha(), (100, 100))
    except: pass
    
    # 파란 알약 이미지 로딩 (pill_bullet_blue)
    try:
        IMAGES['pill_bullet_blue'] = pygame.transform.scale(pygame.image.load(resource_path("assets/school_health office/파란알약_1.png")).convert_alpha(), (100, 100))
    except: pass
    
    # 👇 체육관 몬스터 이미지 로딩 (꼬깔콘, 축구공, 배드민턴채)
    gym_monster_configs = [
        ('corn_cone', '꼬깔콘', 12, (120, 120)),
        ('soccer_ball', '축구공', 10, (80, 80)),
        ('badminton_racket', '배드민턴채', 7, (80, 80)),
    ]
    for m_type, k_name, max_frames, size in gym_monster_configs:
        for i in range(1, max_frames + 1):
            try:
                IMAGES[f'{m_type}_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_gym/{k_name}_{i}.png")).convert_alpha(), size)
            except: pass
    # 배드민턴공 투사체 이미지 로딩
    for i in range(1, 3):
        try:
            IMAGES[f'badminton_shuttle_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_gym/배드민턴공_{i}.png")).convert_alpha(), (130, 130))
        except: pass

    # 급식실 몬스터 이미지 로딩
    for i in range(1, 7):
        try:
            IMAGES[f'food_tray_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_cafeteria/다중급식판_{i}.png")).convert_alpha(), (80, 80))
        except: pass
    for i in range(1, 2):
        try:
            IMAGES[f'single_tray_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_cafeteria/단일급식판_{i}.png")).convert_alpha(), (80, 80))
        except: pass
    for i in range(1, 5):
        try:
            IMAGES[f'side_dish_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_cafeteria/반찬_{i}.png")).convert_alpha(), (80, 80))
        except: pass
    for m_type, k_name, max_f in [('steel_scrubber', '철수세미', 14), ('spoon_chopsticks', '숟가락', 5)]:
        size = (100, 100)
        for i in range(1, max_f + 1):
            try:
                IMAGES[f'{m_type}_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_cafeteria/{k_name}_{i}.png")).convert_alpha(), size)
            except: pass
    for i in range(1, 2):
        try:
            IMAGES[f'chopstick_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_cafeteria/젓가락_{i}.png")).convert_alpha(), (130, 80))
        except: pass

    # 컴퓨터실 몬스터 이미지 로딩 (키보드, 공유기, 마우스)
    for i in range(1, 4):
        try:
            IMAGES[f'keyboard_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_computer room/키보드_{i}.png")).convert_alpha(), (80, 80))
        except: pass
    for i in range(1, 2):
        try:
            IMAGES[f'router_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_computer room/공유기_{i}.png")).convert_alpha(), (80, 80))
        except: pass
    for i in range(1, 4):
        try:
            IMAGES[f'computer_mouse_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_computer room/마우스_{i}.png")).convert_alpha(), (80, 80))
        except: pass
    for i in range(1, 9):
        try:
            IMAGES[f'laser_beam_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_computer room/레이저_{i}.png")).convert_alpha(), (340, 1400))
        except: pass

    for m_type, k_name, max_f, size in [('mine_book', '지뢰책', 4, (70, 70)), ('gravity_book', '중력책', 4, (90, 90)), ('forbidden_book', '금지책', 4, (90, 90)), ('gamble_book', '도박책', 4, (90, 90))]:
        for i in range(1, max_f + 1):
            try:
                IMAGES[f'{m_type}_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_library/{k_name}_{i}.png")).convert_alpha(), size)
            except: pass
    for i in range(1, 3):
        try:
            IMAGES[f'library_mine_{i}'] = pygame.transform.scale(pygame.image.load(resource_path(f"assets/school_library/지뢰_{i}.png")).convert_alpha(), (112, 112))
        except: pass
    
    for i in range(1, 21):
        try:
            path = resource_path(f"assets/image/스토리_{i}.png")
            if os.path.exists(path):
                # 1920x1080 (LOGICAL_WIDTH, LOGICAL_HEIGHT) 크기로 꽉 차게 변환하여 저장
                IMAGES[f'story_{i}'] = pygame.transform.scale(
                    pygame.image.load(path).convert_alpha(), 
                    (LOGICAL_WIDTH, LOGICAL_HEIGHT)
                )
        except: pass
        
    try: IMAGES['naye_base'] = pygame.transform.scale(pygame.image.load(resource_path("assets/image/나예 기본.png")).convert_alpha(), (1700, 900))
    except: pass
    try: IMAGES['naye_surprised'] = pygame.transform.scale(pygame.image.load(resource_path("assets/image/나예 놀람.png")).convert_alpha(), (1700, 900))
    except: pass

    # 👈 고양이 이미지 로딩 코드를 추가합니다.
    # 고양이 초상화
    try:
        # 오직 assets/image/고양이.png 파일만 사용합니다.
        # 해당 파일이 지정된 경로에 반드시 존재해야 합니다.
        cat_path = resource_path("assets/image/고양이.png")
        IMAGES['cat_portrait'] = pygame.transform.scale(pygame.image.load(cat_path).convert_alpha(), (350, 430))
    except Exception as e:
        # 파일이 없을 경우 에러 메시지를 출력하고 게임은 계속 진행되도록 예외 처리합니다.
        print(f"고양이 이미지를 불러오지 못했습니다 (path: assets/image/고양이.png): {e}")
    try:
        _jh_raw = pygame.image.load(resource_path("assets/image/주현 기본.png")).convert_alpha()
        _jh_w, _jh_h = _jh_raw.get_size()
        _jh_scale = 300 / _jh_h
        IMAGES['주현_기본'] = pygame.transform.smoothscale(_jh_raw, (int(_jh_w * _jh_scale), int(_jh_h * _jh_scale)))
    except: pass
        # 👇 노아 표정 이미지를 나예 기본처럼 (1700, 900) 고해상도로 크게 늘려서 로딩합니다!
    emotions = ['기본', '놀람', '두려움', '슬픔', '행복', '화남']
    for emo in emotions:
        try:
            path = resource_path(f"assets/image/노아 {emo}.png")
            # 나예 이미지와 똑같이 1700x900 크기로 변환하여 저장합니다.
            IMAGES[f'noah_{emo}'] = pygame.transform.scale(pygame.image.load(path).convert_alpha(), (1700, 900))
        except: pass
        # 👇 [수정] 나예 보스전 감정 일러스트들을 고해상도(1700, 900) 비율 유지 상태로 로딩 (깨짐 방지)
        naye_emotions = ['기본', '혐오', '화남', '행복']
        for emo in naye_emotions:
            try:
                path = resource_path(f"assets/image/나예 {emo}.png")
                IMAGES[f'naye_face_{emo}'] = pygame.transform.scale(pygame.image.load(path).convert_alpha(), (1700, 900))
            except: pass

    try:
        IMAGES['cursor_normal'] = pygame.transform.scale(pygame.image.load(resource_path("assets/image/마우스_기본.png")).convert_alpha(), (32, 32))
        IMAGES['cursor_click'] = pygame.transform.scale(pygame.image.load(resource_path("assets/image/마우스_클릭.png")).convert_alpha(), (32, 32))
    except: pass

    # 엔딩 이미지 로딩 (1~4)
    for i in range(1, 5):
        try:
            path = resource_path(f"assets/image/엔딩_{i}.png")
            if os.path.exists(path):
                raw = pygame.image.load(path).convert_alpha()
                rw, rh = raw.get_size()
                IMAGES[f'ending_{i}'] = pygame.transform.scale(raw, (int(rw * 0.9), int(rh * 0.7)))
        except: pass

    IMAGES['slash_effect'] = []
    for i in range(1, 20): 
        path = resource_path(f"assets/image/베기_이펙트_{i}.png")
        if os.path.exists(path):
            try: IMAGES['slash_effect'].append(pygame.transform.scale(pygame.image.load(path).convert_alpha(), (150, 150))) 
            except: pass
        else: break 
    if not IMAGES['slash_effect'] and os.path.exists(resource_path("assets/image/베기_이펙트.png")):
        try: IMAGES['slash_effect'].append(pygame.transform.scale(pygame.image.load(resource_path("assets/image/베기_이펙트.png")).convert_alpha(), (130, 130)))
        except: pass

    try:
        idle_1 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/대기 모션_1.png")).convert_alpha(), (65, 65))
        idle_2 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/대기 모션_2.png")).convert_alpha(), (65, 65))
        idle_3 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/대기 모션_3.png")).convert_alpha(), (65, 65))
        IMAGES['player_idle'] = [idle_1, idle_2, idle_2, idle_3, idle_3, idle_2, idle_2, idle_1]
    except: pass

    try:
        run_1 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/걷기 모션_1.png")).convert_alpha(), (60, 60))
        run_2 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/걷기 모션_2.png")).convert_alpha(), (60, 60))
        run_3 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/걷기 모션_3.png")).convert_alpha(), (60, 60))
        run_4 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/걷기 모션_4.png")).convert_alpha(), (60, 60))
        run_5 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/걷기 모션_5.png")).convert_alpha(), (60, 60))
        run_6 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/걷기 모션_6.png")).convert_alpha(), (60, 60))
        IMAGES['player_run_right'] = [run_1, run_2, run_2, run_1, run_1, run_3, run_3, run_1, run_1, run_4, run_4, run_1, run_1, run_5, run_5, run_1, run_1, run_6, run_6, run_1]
        IMAGES['player_run_left'] = [pygame.transform.flip(img, True, False) for img in IMAGES['player_run_right']]
    except: pass

    try:
        up_1 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/뒷면 걷기_1.png")).convert_alpha(), (60, 60))
        up_2 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/뒷면 걷기_2.png")).convert_alpha(), (60, 60))
        up_3 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/뒷면 걷기_3.png")).convert_alpha(), (60, 60))
        IMAGES['player_run_up'] = [up_1, up_2, up_2, up_3, up_3, up_2, up_2, up_1] 
    except: pass

    try:
        down_1 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/정면 걷기_1.png")).convert_alpha(), (60, 60))
        down_2 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/정면 걷기_2.png")).convert_alpha(), (60, 60))
        down_3 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/정면 걷기_3.png")).convert_alpha(), (60, 60))
        down_4 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/정면 걷기_4.png")).convert_alpha(), (55, 55))
        down_5 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/정면 걷기_5.png")).convert_alpha(), (55, 55))
        IMAGES['player_run_down'] = [down_1, down_2, down_2, down_3, down_3, down_4, down_4, down_5, down_5, down_1] 
    except: pass

    try:
        att1_1 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/공격 오_왼_1.png")).convert_alpha(), (180, 180))
        att1_2 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/공격 오_왼_2.png")).convert_alpha(), (180, 180))
        att1_3 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/공격 오_왼_3.png")).convert_alpha(), (180, 180))
        att1_4 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/공격 오_왼_4.png")).convert_alpha(), (180, 180))
        IMAGES['attack_1_right'] = [att1_1, att1_2, att1_3, att1_4]
        IMAGES['attack_1_left'] = [pygame.transform.flip(img, True, False) for img in IMAGES['attack_1_right']]
        IMAGES['attack_1_up'] = [pygame.transform.rotate(img, 90) for img in IMAGES['attack_1_right']]
        IMAGES['attack_1_down'] = [pygame.transform.rotate(img, -90) for img in IMAGES['attack_1_right']]

        att2_1 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/공격 왼_오_1.png")).convert_alpha(), (180, 180))
        att2_2 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/공격 왼_오_2.png")).convert_alpha(), (180, 180))
        att2_3 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/공격 왼_오_3.png")).convert_alpha(), (180, 180))
        att2_4 = pygame.transform.scale(pygame.image.load(resource_path("assets/image/공격 왼_오_4.png")).convert_alpha(), (180, 180))
        IMAGES['attack_2_right'] = [att2_1, att2_2, att2_3, att2_4]
        IMAGES['attack_2_left'] = [pygame.transform.flip(img, True, False) for img in IMAGES['attack_2_right']]
        IMAGES['attack_2_up'] = [pygame.transform.rotate(img, 90) for img in IMAGES['attack_2_right']]
        IMAGES['attack_2_down'] = [pygame.transform.rotate(img, -90) for img in IMAGES['attack_2_right']]
    except: pass

    try:
        IMAGES['potion'] = pygame.transform.scale(pygame.image.load(resource_path("assets/image/회복물약.png")).convert_alpha(), (24, 24))
    except: pass

    # 방어막 및 애니메이션
    IMAGES['shield_anim'] = []
    for i in range(1, 9):
        try:
            img = pygame.transform.scale(pygame.image.load(resource_path(f"assets/image/방어막_{i}.png")).convert_alpha(), (110, 110))
            IMAGES['shield_anim'].append(img)
        except: pass
    
    if IMAGES['shield_anim']:
        IMAGES['shield'] = pygame.transform.scale(IMAGES['shield_anim'][0], (24, 24))
        IMAGES['shield_large'] = pygame.transform.scale(IMAGES['shield_anim'][0], (120, 120))
    else:
        try:
            raw_sh = pygame.image.load(resource_path("assets/image/방어막_1.png")).convert_alpha()
            IMAGES['shield'] = pygame.transform.scale(raw_sh, (24, 24))
            IMAGES['shield_large'] = pygame.transform.scale(raw_sh, (120, 120))
        except: pass

    # 배낭
    try:
        raw_bag = pygame.image.load(resource_path("assets/image/배낭.png")).convert_alpha()
        IMAGES['backpack'] = pygame.transform.scale(raw_bag, (TILE_SIZE, TILE_SIZE))
        IMAGES['backpack_large'] = pygame.transform.scale(raw_bag, (120, 120))
    except: pass

    IMAGES['boss_dialogue'] = []
    for i in range(1, 11):
        try:
            path = resource_path(f"assets/school_principal office/대화_{i}.png")
            raw = pygame.image.load(path).convert_alpha()
            IMAGES['boss_dialogue'].append(pygame.transform.scale(raw, (100, 100)))
        except: pass

    IMAGES['boss_phase1'] = []
    for i in range(1, 11):
        try:
            path = resource_path(f"assets/school_principal office/1페_{i}.png")
            raw = pygame.image.load(path).convert_alpha()
            IMAGES['boss_phase1'].append(pygame.transform.scale(raw, (100, 100)))
        except: pass

    IMAGES['boss_meteor'] = []
    for i in range(1, 11):
        try:
            path = resource_path(f"assets/school_principal office/운석_{i}.png")
            raw = pygame.image.load(path).convert_alpha()
            rw, rh = raw.get_size()
            IMAGES['boss_meteor'].append(pygame.transform.scale(raw, (230, 500)))
        except: pass

    IMAGES['boss_phase2'] = []
    for i in range(1, 13):
        try:
            path = resource_path(f"assets/school_principal office/2페_{i}.png")
            IMAGES['boss_phase2'].append(pygame.transform.scale(pygame.image.load(path).convert_alpha(), (100, 100)))
        except: pass

    try:
        raw = pygame.image.load(resource_path("assets/school_principal office/다운_1.png")).convert_alpha()
        IMAGES['boss_down'] = pygame.transform.scale(raw, (100, 100))
        IMAGES['boss_down_flip'] = pygame.transform.flip(IMAGES['boss_down'], True, False)
    except: pass

# ==================== 설정(Config) 및 세이브 ====================
# 마우스 버튼 특수 키 코드 (pygame 키보드 코드와 충돌 방지를 위해 음수 사용)
MOUSE_LEFT = -1
MOUSE_MIDDLE = -2
MOUSE_RIGHT = -3
mouse_buttons_held = {1: False, 2: False, 3: False}

CONFIG_FILE = "settings.json"
config = {
    'display_mode': 'WINDOW', 'volume': 50, 'bgm_volume': 50, 'voice_volume': 50,
    'keys': {
        'UP': pygame.K_w, 'DOWN': pygame.K_s, 'LEFT': pygame.K_a, 'RIGHT': pygame.K_d,
        'INTERACT': pygame.K_e, 'DASH': pygame.K_SPACE, 'ATTACK': MOUSE_LEFT
    }
}

def is_action_pressed(action):
    """config의 키 설정에 따라 키보드 또는 마우스 버튼이 눌려있는지 확인"""
    key_val = config['keys'].get(action)
    if key_val is None: return False
    if key_val == MOUSE_LEFT: return mouse_buttons_held.get(1, False)
    elif key_val == MOUSE_MIDDLE: return mouse_buttons_held.get(2, False)
    elif key_val == MOUSE_RIGHT: return mouse_buttons_held.get(3, False)
    else:
        try: return pygame.key.get_pressed()[key_val]
        except (IndexError, TypeError): return False

def get_key_display_name(key_val):
    """키 값을 화면에 표시할 문자열로 변환"""
    if key_val is None: return "?"
    if key_val == MOUSE_LEFT: return "L-마우스"
    elif key_val == MOUSE_MIDDLE: return "M-마우스"
    elif key_val == MOUSE_RIGHT: return "R-마우스"
    else:
        try: return pygame.key.name(key_val).upper()
        except: return "?"

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
        # 👇 버튼 클릭 판정과 동시에 클릭음을 재생하도록 개조합니다!
        clicked = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(scaled_mouse_pos)
        if clicked and 'click' in SOUNDS: 
            SOUNDS['click'].play()
        return clicked
        
SOUNDS = {}
CURRENT_BGM = None  

def load_sounds():
    def load_snd(name, filename):
        path = resource_path(f"assets/sound/{filename}")
        if os.path.exists(path):
            try: SOUNDS[name] = pygame.mixer.Sound(path)
            except: pass
    load_snd('attack', '칼공격.mp3')
    load_snd('hit', '칼피격.mp3')
    load_snd('dash', '대쉬.mp3')
    load_snd('interact', '상호작용.mp3')
    load_snd('player_hit', '플레이어피격.mp3')
    load_snd('door_open', '문열림.mp3')
    load_snd('door_close', '문닫힘.mp3')
    load_snd('meow_1', '먀옹1.mp3')
    load_snd('meow_2', '먀옹2.mp3')
    load_snd('meow_3', '먀옹3.mp3')
    load_snd('click', '클릭.mp3')
    load_snd('discord_alarm', '디코알람.mp3')
    load_snd('dialog_next', '대화넘기기.mp3')
    load_snd('closet_open', '옷장열림.mp3')
    load_snd('walk', '걷기.mp3')
    load_snd('sword_draw', '칼들음.mp3')
    load_snd('stun', '스턴.mp3')
    load_snd('enter_press', '엔터침.mp3')
    load_snd('explosion', '폭발소리.mp3')
    load_snd('sigh', '한숨소리.mp3')
    load_snd('laugh', '웃음소리.mp3')
    load_snd('fall', '쓰러진소리.mp3')
    voice_dir = resource_path("assets/voice")
    if os.path.exists(voice_dir):
        for i in range(1, 24):
            num_str = f'{i:02d}'
            for fname in os.listdir(voice_dir):
                if fname.startswith(num_str + '_') and fname.lower().endswith('.mp3'):
                    try: SOUNDS[f'voice_{num_str}'] = pygame.mixer.Sound(os.path.join(voice_dir, fname))
                    except: pass
                    break
    update_sound_volumes()

def update_sound_volumes():
    master_vol = config.get('volume', 50) / 100.0
    bgm_vol = config.get('bgm_volume', 50) / 100.0 
    if 'attack' in SOUNDS: SOUNDS['attack'].set_volume(master_vol)
    if 'hit' in SOUNDS: SOUNDS['hit'].set_volume(master_vol)
    if 'dash' in SOUNDS: SOUNDS['dash'].set_volume(master_vol)
    if 'interact' in SOUNDS: SOUNDS['interact'].set_volume(master_vol)
    if 'player_hit' in SOUNDS: SOUNDS['player_hit'].set_volume(master_vol)
    if 'door_open' in SOUNDS: SOUNDS['door_open'].set_volume(master_vol)
    if 'door_close' in SOUNDS: SOUNDS['door_close'].set_volume(master_vol)
    if 'click' in SOUNDS: SOUNDS['click'].set_volume(master_vol)
    if 'discord_alarm' in SOUNDS: SOUNDS['discord_alarm'].set_volume(master_vol)
    if 'dialog_next' in SOUNDS: SOUNDS['dialog_next'].set_volume(master_vol)
    if 'closet_open' in SOUNDS: SOUNDS['closet_open'].set_volume(master_vol)
    if 'walk' in SOUNDS: SOUNDS['walk'].set_volume(master_vol)
    if 'sword_draw' in SOUNDS: SOUNDS['sword_draw'].set_volume(master_vol)
    if 'stun' in SOUNDS: SOUNDS['stun'].set_volume(master_vol)
    if 'enter_press' in SOUNDS: SOUNDS['enter_press'].set_volume(master_vol)
    for i in range(1, 4):
        if f'meow_{i}' in SOUNDS: SOUNDS[f'meow_{i}'].set_volume(master_vol)
    voice_vol = config.get('voice_volume', 50) / 100.0
    for i in range(1, 24):
        key = f'voice_{i:02d}'
        if key in SOUNDS: SOUNDS[key].set_volume(master_vol * voice_vol)
    if 'sigh' in SOUNDS: SOUNDS['sigh'].set_volume(master_vol * 0.2)
    if 'laugh' in SOUNDS: SOUNDS['laugh'].set_volume(master_vol * 0.2)
    if 'explosion' in SOUNDS: SOUNDS['explosion'].set_volume(master_vol * 0.5)
    pygame.mixer.music.set_volume(master_vol * bgm_vol)

def play_bgm(bgm_key):
    global CURRENT_BGM
    if CURRENT_BGM == bgm_key: return
    CURRENT_BGM = bgm_key
    update_sound_volumes() 
    if bgm_key == 'title': path = resource_path("assets/sound/시작배경.mp3")
    elif bgm_key == 'game': path = resource_path("assets/sound/게임배경.mp3")
    elif bgm_key == 'waiting': path = resource_path("assets/sound/대기배경.mp3")
    elif bgm_key == 'boss_phase1': path = resource_path("assets/sound/보스1페.mp3")
    elif bgm_key == 'boss_phase2': path = resource_path("assets/sound/보스2페.mp3")
    elif bgm_key == 'credits': path = resource_path("assets/sound/엔딩크레딧배경.mp3")
    else: pygame.mixer.music.stop(); return
    
    if os.path.exists(path):
        try:
            pygame.mixer.music.load(path); pygame.mixer.music.play(-1)
            if bgm_key == 'boss_phase1':
                pygame.mixer.music.set_volume(min(1.0, (config.get('volume', 50) / 100.0) * (config.get('bgm_volume', 50) / 100.0) * 2.0))
            elif bgm_key == 'boss_phase2':
                pygame.mixer.music.set_volume(min(1.0, (config.get('volume', 50) / 100.0) * (config.get('bgm_volume', 50) / 100.0) * 1.5))
        except: pass

# ==================== 이펙트 & 객체 클래스 ====================
class DustParticle:
    def __init__(self, x, y):
        self.x = x; self.y = y
        self.vx = random.uniform(-20, 20); self.vy = random.uniform(-80, -30) 
        self.max_lifetime = random.uniform(0.5, 1.5); self.lifetime = self.max_lifetime
        self.size = random.randint(2, 5)
        self.color = random.choice([(150, 150, 150), (100, 100, 100), (200, 200, 200)])
    def update(self, dt):
        self.x += self.vx * dt; self.y += self.vy * dt; self.lifetime -= dt
    def draw(self, surface, cam_x, cam_y):
        if self.lifetime > 0:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            s.fill((self.color[0], self.color[1], self.color[2], alpha))
            surface.blit(s, (int(self.x - cam_x), int(self.y - cam_y)))

class DroppedItem:
    def __init__(self, x, y, item_type="회복물약"):
        self.pos = pygame.math.Vector2(x, y)
        self.item_type = item_type
        self.radius = 6 
        self.float_offset = random.uniform(0, math.pi * 2) 

    def draw(self, surface, cam_x, cam_y):
        draw_x = int(self.pos.x - cam_x)
        draw_y = int(self.pos.y - cam_y + math.sin(pygame.time.get_ticks() * 0.005 + self.float_offset) * 3)
        
        img_key = 'potion' if self.item_type == "회복물약" else 'shield'
        if img_key in IMAGES:
            img = IMAGES[img_key]
            surface.blit(img, img.get_rect(center=(draw_x, draw_y)))
        else:
            color = (255, 50, 50) if self.item_type == "회복물약" else (50, 100, 255)
            pygame.draw.circle(surface, color, (draw_x, draw_y), self.radius)

class MonsterSpawn:
    def __init__(self, x, y, enemy_type='normal'):
        self.pos = pygame.math.Vector2(x, y)
        self.enemy_type = enemy_type
        self.timer = 0.0
        self.max_time = 0.8  
        self.delay = 1.0     
        self.warning_radius = 45 if enemy_type in ['boss', 'pill_boss'] else 25
        self.extra_attrs = {}

    def update(self, dt):
        if self.delay > 0:
            self.delay -= dt; return False 
        self.timer += dt
        return self.timer >= self.max_time

    def draw(self, surface, cam_x, cam_y):
        if self.delay > 0: return 
        draw_x = int(self.pos.x - cam_x); draw_y = int(self.pos.y - cam_y)
        progress = min(1.0, self.timer / self.max_time)
        alpha_surf = pygame.Surface((self.warning_radius * 2, self.warning_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(alpha_surf, (200, 30, 30, 40), (self.warning_radius, self.warning_radius), self.warning_radius)
        curr_radius = int(self.warning_radius * progress)
        curr_alpha = int(40 + 200 * progress) 
        if curr_radius > 0: pygame.draw.circle(alpha_surf, (220, 20, 20, curr_alpha), (self.warning_radius, self.warning_radius), curr_radius)
        pygame.draw.circle(alpha_surf, (255, 50, 50, 150), (self.warning_radius, self.warning_radius), self.warning_radius, 2)
        scaled_surf = pygame.transform.scale(alpha_surf, (self.warning_radius * 2, int(self.warning_radius * 1.4)))
        surface.blit(scaled_surf, (draw_x - self.warning_radius, draw_y - int(self.warning_radius * 0.7)))

class SpawnEffect:
    def __init__(self, x, y):
        self.pos = pygame.math.Vector2(x, y); self.max_timer = 0.4; self.timer = 0.4; self.radius = 25 
    def update(self, dt): self.timer -= dt
    def draw(self, surface, cam_x, cam_y):
        if self.timer <= 0: return
        progress = 1.0 - (self.timer / self.max_timer) 
        current_radius = int(self.radius * (1.0 + progress * 0.5)); hole_radius = int(current_radius * progress); thickness = current_radius - hole_radius
        alpha = max(0, int(255 * (1.0 - progress)))
        draw_x = int(self.pos.x - cam_x); draw_y = int(self.pos.y - cam_y)
        temp_surf = pygame.Surface((current_radius * 2, current_radius * 2), pygame.SRCALPHA)
        if thickness > 0:
            pygame.draw.circle(temp_surf, (255, 255, 200, alpha), (current_radius, current_radius), current_radius, thickness)
            if thickness > 2: pygame.draw.circle(temp_surf, (255, 255, 255, alpha), (current_radius, current_radius), current_radius, max(1, thickness // 2))
        scaled_surf = pygame.transform.scale(temp_surf, (current_radius * 2, int(current_radius * 1.2)))
        surface.blit(scaled_surf, (draw_x - current_radius, draw_y - int(current_radius * 0.6)))

class SoapPuddle:
    def __init__(self, x, y):
        self.pos = pygame.math.Vector2(x, y)
        self.timer = 5.0      
        self.max_timer = 5.0
        self.radius = 20      

    def update(self, dt): 
        self.timer -= dt

    def draw(self, surface, cam_x, cam_y):
        if self.timer > 0:
            # 시간이 지날수록 서서히 투명해지게 처리
            alpha = min(150, int(150 * (self.timer / self.max_timer)))
            s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (200, 240, 255, alpha), (self.radius, self.radius), self.radius)
            surface.blit(s, (int(self.pos.x - cam_x - self.radius), int(self.pos.y - cam_y - self.radius)))

class LibraryMine:
    def __init__(self, x, y, damage=1):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = 30
        self.damage = damage
        self.anim_timer = 0.0
        self.alive = True
        self.chain_delay = 0.0
        self.chain_triggered = False

    def update(self, dt):
        self.anim_timer += dt
        if self.chain_triggered:
            self.chain_delay -= dt

    def draw(self, surface, cam_x, cam_y):
        if not self.alive: return
        draw_x = int(self.pos.x - cam_x)
        draw_y = int(self.pos.y - cam_y)
        if self.chain_triggered and self.chain_delay > 0:
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.02))
            warn_r = self.radius * 3
            warn_surf = pygame.Surface((warn_r * 2, warn_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(warn_surf, (255, 100, 0, int(120 * pulse)), (warn_r, warn_r), warn_r)
            pygame.draw.circle(warn_surf, (255, 60, 0, int(200 * pulse)), (warn_r, warn_r), warn_r, 3)
            surface.blit(warn_surf, (draw_x - warn_r, draw_y - warn_r))
        frame_idx = int(self.anim_timer / 1.0) % 2 + 1
        img_key = f'library_mine_{frame_idx}'
        if img_key in IMAGES:
            surface.blit(IMAGES[img_key], IMAGES[img_key].get_rect(center=(draw_x, draw_y)))
        else:
            pygame.draw.circle(surface, (200, 50, 50), (draw_x, draw_y), self.radius)
            pygame.draw.circle(surface, (255, 100, 100), (draw_x, draw_y), self.radius, 2)

class StaticWave:
    def __init__(self, x, y, max_radius=3000):
        self.pos = pygame.math.Vector2(x, y)
        self.current_radius = 0.0
        self.speed = 500
        self.max_radius = max_radius
        self.dead = False
    def update(self, dt):
        self.current_radius += self.speed * dt
        if self.current_radius >= self.max_radius:
            self.dead = True
    def draw(self, surface, cam_x, cam_y):
        if self.dead or self.current_radius <= 0: return
        cx = int(self.pos.x - cam_x)
        cy = int(self.pos.y - cam_y)
        r = int(self.current_radius)
        fade = max(0.1, 1.0 - self.current_radius / self.max_radius)
        thickness = max(3, int(20 * fade))
        alpha = int(180 * fade)
        vw, vh = surface.get_size()
        left = max(0, cx - r); top = max(0, cy - r)
        right = min(vw, cx + r); bottom = min(vh, cy + r)
        sw, sh = right - left, bottom - top
        if sw <= 0 or sh <= 0: return
        local_cx, local_cy = cx - left, cy - top
        wave_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.circle(wave_surf, (80, 120, 255, min(255, max(0, alpha))), (local_cx, local_cy), r, thickness)
        pygame.draw.circle(wave_surf, (120, 160, 255, min(255, max(0, alpha // 2))), (local_cx, local_cy), max(1, r - thickness), max(1, thickness // 2))
        surface.blit(wave_surf, (left, top))

class BossShockwaveParticle:
    def __init__(self, x, y, angle):
        self.x = x; self.y = y
        speed = random.uniform(200, 500)
        self.vx = math.cos(angle) * speed; self.vy = math.sin(angle) * speed
        self.max_lifetime = random.uniform(0.4, 0.9); self.lifetime = self.max_lifetime
        self.size = random.randint(3, 8)
        self.color = random.choice([
            (255, 220, 50), (255, 180, 0), (255, 150, 0), (255, 255, 100),
            (255, 100, 0), (200, 150, 0), (255, 200, 80)
        ])
    def update(self, dt):
        self.x += self.vx * dt; self.y += self.vy * dt
        self.vx *= 0.96; self.vy *= 0.96
        self.lifetime -= dt
    def draw(self, surface, cam_x, cam_y):
        if self.lifetime <= 0: return
        ratio = self.lifetime / self.max_lifetime
        alpha = int(255 * ratio)
        s = max(1, int(self.size * ratio))
        dx, dy = int(self.x - cam_x), int(self.y - cam_y)
        temp = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
        pygame.draw.circle(temp, (*self.color, alpha), (s, s), s)
        surface.blit(temp, (dx - s, dy - s))

class BossShockwave:
    def __init__(self, x, y, max_radius=3000):
        self.pos = pygame.math.Vector2(x, y)
        self.current_radius = 0.0
        self.speed = 600
        self.max_radius = max_radius
        self.dead = False
        self.ring_particles = []
        self.particle_timer = 0.0
        self.rings = []
        self.next_ring_at = 0.0
    def update(self, dt):
        self.current_radius += self.speed * dt
        if self.current_radius >= self.max_radius:
            self.dead = True
        self.particle_timer += dt
        if self.particle_timer >= 0.03:
            self.particle_timer = 0.0
            for _ in range(4):
                angle = random.uniform(0, 2 * math.pi)
                px = self.pos.x + math.cos(angle) * self.current_radius
                py = self.pos.y + math.sin(angle) * self.current_radius
                self.ring_particles.append(BossShockwaveParticle(px, py, angle))
        if self.current_radius >= self.next_ring_at and self.next_ring_at < self.max_radius:
            self.rings.append({'radius': self.current_radius, 'alpha': 255.0, 'thickness': random.randint(6, 14)})
            self.next_ring_at += 120
        for p in self.ring_particles[:]:
            p.update(dt)
            if p.lifetime <= 0: self.ring_particles.remove(p)
        for ring in self.rings:
            ring['alpha'] -= 200 * dt
        self.rings = [r for r in self.rings if r['alpha'] > 0]
    def draw(self, surface, cam_x, cam_y):
        if self.dead and not self.rings and not self.ring_particles: return
        cx = int(self.pos.x - cam_x)
        cy = int(self.pos.y - cam_y)
        r = int(self.current_radius)
        fade = max(0.1, 1.0 - self.current_radius / self.max_radius)
        vw, vh = surface.get_size()
        left = max(0, cx - r - 20); top = max(0, cy - r - 20)
        right = min(vw, cx + r + 20); bottom = min(vh, cy + r + 20)
        sw, sh = right - left, bottom - top
        if sw <= 0 or sh <= 0: return
        local_cx, local_cy = cx - left, cy - top
        wave_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        main_alpha = int(200 * fade)
        main_thickness = max(4, int(25 * fade))
        pygame.draw.circle(wave_surf, (255, 200, 0, min(255, max(0, main_alpha))), (local_cx, local_cy), max(1, r), main_thickness)
        inner_alpha = int(100 * fade)
        pygame.draw.circle(wave_surf, (255, 255, 100, min(255, max(0, inner_alpha))), (local_cx, local_cy), max(1, r - main_thickness), max(1, main_thickness // 2))
        glow_alpha = int(40 * fade)
        if glow_alpha > 0 and r > main_thickness * 2:
            pygame.draw.circle(wave_surf, (255, 180, 0, min(255, max(0, glow_alpha))), (local_cx, local_cy), max(1, r + main_thickness), max(1, main_thickness))
        for ring in self.rings:
            rr = int(ring['radius'])
            ra = int(min(255, max(0, ring['alpha'])))
            if ra > 0 and rr > 0:
                pygame.draw.circle(wave_surf, (255, 255, 150, ra), (local_cx, local_cy), rr, max(1, int(ring['thickness'] * (ra / 255.0))))
        surface.blit(wave_surf, (left, top))
        for p in self.ring_particles:
            p.draw(surface, cam_x, cam_y)

class Particle:
    def __init__(self, x, y):
        self.x = x; self.y = y; angle = random.uniform(0, 2 * math.pi); speed = random.uniform(100, 250) 
        self.vx = math.cos(angle) * speed; self.vy = math.sin(angle) * speed
        self.max_lifetime = random.uniform(0.2, 0.4); self.lifetime = self.max_lifetime
        self.size = random.randint(4, 9)
        self.color = random.choice([(255, 40, 40), (200, 10, 10), (130, 0, 0), (80, 0, 0)])
    def update(self, dt):
        self.x += self.vx * dt; self.y += self.vy * dt; self.vy += 1000 * dt 
        self.vy *= 0.95 ** (dt * 60); self.vx *= 0.98 ** (dt * 60); self.lifetime -= dt
    def draw(self, surface, cam_x, cam_y):
        if self.lifetime > 0:
            ratio = self.lifetime / self.max_lifetime; current_size = max(1, int(self.size * ratio))
            rect = pygame.Rect(0, 0, current_size, current_size); rect.center = (int(self.x - cam_x), int(self.y - cam_y))
            pygame.draw.rect(surface, self.color, rect)

class ExplosionParticle:
    def __init__(self, x, y):
        self.x = x; self.y = y
        angle = random.uniform(-math.pi * 0.85, -math.pi * 0.15)
        speed = random.uniform(200, 600)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.max_lifetime = random.uniform(0.5, 1.2)
        self.lifetime = self.max_lifetime
        self.size = random.randint(8, 22)
        self.color = random.choice([
            (255, 200, 50), (255, 160, 30), (255, 120, 20), (255, 80, 10),
            (200, 180, 150), (150, 140, 130), (100, 95, 90), (80, 75, 70),
            (255, 255, 200), (255, 230, 100), (220, 100, 20)
        ])
    def update(self, dt):
        self.x += self.vx * dt; self.y += self.vy * dt
        self.vy += 800 * dt
        self.vx *= 0.97 ** (dt * 60); self.vy *= 0.97 ** (dt * 60)
        self.lifetime -= dt
    def draw(self, surface, cam_x, cam_y):
        if self.lifetime > 0:
            ratio = self.lifetime / self.max_lifetime
            alpha = int(255 * ratio)
            current_size = max(1, int(self.size * (0.3 + 0.7 * ratio)))
            s = pygame.Surface((current_size, current_size), pygame.SRCALPHA)
            s.fill((*self.color, alpha))
            surface.blit(s, s.get_rect(center=(int(self.x - cam_x), int(self.y - cam_y))))

class ShieldBreakParticle:
    """하늘색 보호막이 깨지는 파티클 - 삼각형 모양 파편으로 퍼지며 투명해짐"""
    def __init__(self, x, y):
        self.x = x; self.y = y
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(80, 350)
        self.vx = math.cos(angle) * speed; self.vy = math.sin(angle) * speed
        self.max_lifetime = random.uniform(0.4, 0.9); self.lifetime = self.max_lifetime
        self.size = random.randint(5, 14)
        self.color = random.choice([
            (130, 200, 255), (80, 170, 255), (50, 140, 230),
            (180, 225, 255), (100, 190, 250), (40, 120, 200)
        ])
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-400, 400)
    def update(self, dt):
        self.x += self.vx * dt; self.y += self.vy * dt
        self.vy += 300 * dt  # 약한 중력
        self.vx *= 0.97 ** (dt * 60); self.vy *= 0.97 ** (dt * 60)
        self.rotation += self.rot_speed * dt
        self.lifetime -= dt
    def draw(self, surface, cam_x, cam_y):
        if self.lifetime <= 0: return
        ratio = self.lifetime / self.max_lifetime
        alpha = max(0, int(255 * ratio))
        current_size = max(2, int(self.size * ratio))
        dx = int(self.x - cam_x); dy = int(self.y - cam_y)
        # 삼각형 파편 모양으로 그리기
        pts = [
            (dx, dy - current_size),
            (dx - int(current_size * 0.7), dy + int(current_size * 0.5)),
            (dx + int(current_size * 0.7), dy + int(current_size * 0.5))
        ]
        surf = pygame.Surface((current_size * 3, current_size * 3), pygame.SRCALPHA)
        offset_pts = [(p[0] - dx + current_size * 2, p[1] - dy + current_size * 2) for p in pts]
        # 바깥쪽 하늘색 삼각형
        pygame.draw.polygon(surf, (*self.color, alpha), offset_pts)
        # 안쪽 밝은 하이라이트
        inner_pts = [(int(p[0] * 0.6 + current_size * 2 * 0.4), int(p[1] * 0.6 + current_size * 2 * 0.4)) for p in offset_pts]
        bright = tuple(min(255, c + 80) for c in self.color)
        pygame.draw.polygon(surf, (*bright, int(alpha * 0.7)), inner_pts)
        # 회전 적용
        if abs(self.rotation % 360) > 1:
            surf = pygame.transform.rotate(surf, self.rotation)
        surface.blit(surf, surf.get_rect(center=(dx, dy)))

class DamageText:
    def __init__(self, x, y, amount):
        self.pos = pygame.math.Vector2(x, y); self.amount = amount; self.timer = 0.8; self.max_timer = 0.8
        angle = random.uniform(-math.pi/4, math.pi/4); speed = random.uniform(180, 260)              
        self.vel = pygame.math.Vector2(math.sin(angle) * speed, -math.cos(angle) * speed)
        self.font = get_korean_font(36, bold=True)
        if str(self.amount) == "무적": 
            self.inner_color = (200, 200, 255); self.outline_color = (50, 50, 150)  
        elif str(self.amount) == "보호": 
            self.inner_color = (150, 220, 255); self.outline_color = (0, 50, 255)  # 안쪽 하늘색, 테두리 파란색
        elif str(self.amount).startswith("-"): 
            self.inner_color = (255, 50, 50); self.outline_color = (150, 0, 0)
        elif str(self.amount) == "+5":
            self.inner_color = (150, 220, 255); self.outline_color = (30, 80, 180)
        elif str(self.amount) == "공격불가":
            self.inner_color = (200, 200, 200); self.outline_color = (80, 80, 80)
        else:
            self.inner_color = (255, 255, 255); self.outline_color = (150, 0, 0)
        self.text_surf_inner = self.font.render(str(self.amount), True, self.inner_color)
        self.text_surf_out = self.font.render(str(self.amount), True, self.outline_color)
    def update(self, dt): self.pos += self.vel * dt; self.vel.y += 700 * dt; self.timer -= dt
    def draw(self, surface, cam_x, cam_y):
        if self.timer <= 0: return
        alpha = min(255, int((self.timer / self.max_timer) * 255 * 1.5)) 
        draw_x = int(self.pos.x - cam_x - self.text_surf_inner.get_width()//2)
        draw_y = int(self.pos.y - cam_y - self.text_surf_inner.get_height()//2)
        temp_surf = pygame.Surface((self.text_surf_inner.get_width() + 4, self.text_surf_inner.get_height() + 4), pygame.SRCALPHA)
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (1,-1), (-1,1), (1,1)]: temp_surf.blit(self.text_surf_out, (dx + 2, dy + 2))
        temp_surf.blit(self.text_surf_inner, (2, 2)); temp_surf.set_alpha(alpha); surface.blit(temp_surf, (draw_x - 2, draw_y - 2))

class SlashEffect:
    def __init__(self, x, y):
        self.pos = pygame.math.Vector2(x, y); slash_list = IMAGES.get('slash_effect', [])
        self.image = random.choice(slash_list) if slash_list else None
        self.max_timer = 0.3; self.timer = 0.3; self.angle = random.randint(0, 360) 
    def update(self, dt): self.timer -= dt
    def draw(self, surface, cam_x, cam_y):
        if self.timer <= 0 or not self.image: return
        img = pygame.transform.rotate(self.image.copy(), self.angle)
        img.set_alpha(min(255, int((self.timer / self.max_timer) * 255)))
        surface.blit(img, img.get_rect(center=(int(self.pos.x - cam_x), int(self.pos.y - cam_y))))

class Player:
    def __init__(self, room_w, room_h):
        self.pos = pygame.math.Vector2(room_w // 2, room_h - 90)
        self.normal_speed = 350; self.speed = self.normal_speed; self.radius = 12 
        
        self.hp = 100 
        self.max_hp = 100
        self.inv_timer = 0.0 
        self.dust_progress = 0.0 
        
        self.has_bag = False
        self.has_shield = False
        self.shield_anim_timer = 0.0
        self.controls_reversed = False
        self.attack_disabled = False
        self.inventory = [None] * 12 
        self.quick_slots = [None, None, None, None]
        self.item_cooldown = 0.0
        self.seen_items = [] 
        
        self.is_dashing = False; self.dash_speed = 700; self.dash_duration = 0.19; self.dash_cooldown = 1.0
        self.dash_time_left = 0; self.dash_cooldown_left = 0; self.dash_direction = pygame.math.Vector2(0, 0)
        self.stun_timer = 0.0  # 붕대 스턴(이동 불가) 타이머
        self.push_vel = pygame.math.Vector2(0, 0)
        self.push_timer = 0.0
        
        self.is_attacking = False; self.attack_step = 0; self.attack_timer = 0.0; self.combo_window = 0.0
        self.move_lock_timer = 0.0; self.attack_cooldown_timer = 0.0; self.pose_hold_timer = 0.0
        self.frame_index = 0.0; self.animation_speed = 6.0; self.facing = 'right'; self.afterimages = []
        self.frozen = False  # 보스 사망 페이드아웃 등에서 애니메이션을 대기 모션으로 고정
        self.last_damage_taken = 0

    def take_damage(self, amount, is_boss_ultimate=False):
        if self.hp <= 0: return False
        if self.inv_timer <= 0 and not self.is_dashing:
            if self.has_shield:
                self.has_shield = False
                self.inv_timer = 0.5
                return "BLOCKED"
            diff = DIFF[current_difficulty]
            if is_boss_ultimate:
                actual = diff['boss_ult_dmg']
            elif diff['dmg_mode'] == 'flat':
                actual = diff['dmg_value']
            elif diff['dmg_mode'] == 'add':
                actual = amount + diff['dmg_value']
            else:
                actual = amount
            self.hp = max(0, self.hp - actual)
            self.last_damage_taken = actual
            self.inv_timer = 0.5
            if 'player_hit' in SOUNDS: SOUNDS['player_hit'].play()
            if self.hp <= 0: self.is_attacking = False
            return True
        return False

    def use_item(self, slot_idx, is_quick_slot=True):
        item = self.quick_slots[slot_idx] if is_quick_slot else self.inventory[slot_idx]
        if not item: return False, "슬롯이 비어있어!"
        if self.item_cooldown > 0: return False, f"아직 사용할 수 없어! ({self.item_cooldown:.1f}초)"
        
        if item["name"] == "회복물약":
            self.hp = min(self.max_hp, self.hp + 10)
        elif item["name"] == "방어막":
            if self.has_shield: return False, "이미 방어막이 활성화되어 있어!"
            self.has_shield = True
            
        item["count"] -= 1
        msg = f"{item['name']} 사용!"
        if item["count"] <= 0:
            if is_quick_slot: self.quick_slots[slot_idx] = None
            else: self.inventory[slot_idx] = None
        self.item_cooldown = 5.0
        return True, msg

    def add_item(self, name, count):
        for i in range(4):
            if self.quick_slots[i] is not None and self.quick_slots[i]["name"] == name:
                self.quick_slots[i]["count"] += count; return True
        for i in range(12):
            if self.inventory[i] is not None and self.inventory[i]["name"] == name:
                self.inventory[i]["count"] += count; return True
        new_item = {"name": name, "count": count}
        for i in range(4):
            if self.quick_slots[i] is None: self.quick_slots[i] = new_item; return True
        for i in range(12):
            if self.inventory[i] is None: self.inventory[i] = new_item; return True
        return False

    def trigger_attack(self):
        if self.attack_disabled: return "DISABLED"
        if self.push_timer > 0: return False
        if self.is_dashing or self.attack_cooldown_timer > 0: return False
        if not self.is_attacking and self.combo_window <= 0:
            self.is_attacking = True; self.attack_step = 1; self.attack_timer = 0.3; self.combo_window = 0.8; self.frame_index = 0.0; self.move_lock_timer = 0.15; return True
        elif self.combo_window > 0 and self.attack_step == 1:
            if self.attack_timer < 0.15: 
                self.is_attacking = True; self.attack_step = 2; self.attack_timer = 0.3; self.combo_window = 0.0; self.frame_index = 0.0; self.move_lock_timer = 0.15; self.attack_cooldown_timer = 0.3; return True
        return False

    def move(self, dt, room_w, room_h, target_x, target_y, current_map_idx=0, tile_map=None):
        if self.stun_timer > 0: self.stun_timer -= dt  # 스턴 타이머 감소
        if self.dash_cooldown_left > 0: self.dash_cooldown_left -= dt
        if self.move_lock_timer > 0: self.move_lock_timer -= dt
        if self.attack_cooldown_timer > 0: self.attack_cooldown_timer -= dt
        if self.pose_hold_timer > 0: self.pose_hold_timer -= dt
        if self.inv_timer > 0: self.inv_timer -= dt
        self.shield_anim_timer += dt * 10.0  # 👈 방어막 애니메이션 타이머
            
        for ghost in self.afterimages: ghost['timer'] -= dt
        self.afterimages = [g for g in self.afterimages if g['timer'] > 0]
        
        if self.attack_timer > 0:
            self.attack_timer -= dt
            if self.attack_timer <= 0: self.is_attacking = False; self.pose_hold_timer = 0.5 
                
        if self.combo_window > 0: self.combo_window -= dt

        if not self.is_attacking and self.pose_hold_timer <= 0:
            dx = target_x - self.pos.x; dy = target_y - self.pos.y
            if abs(dx) > abs(dy): self.facing = 'right' if dx > 0 else 'left'
            else: self.facing = 'down' if dy > 0 else 'up'

        direction = pygame.math.Vector2(0, 0)
        
        if self.push_timer > 0:
            move_x, move_y = 0, 0
        elif self.frozen:
            move_x, move_y = 0, 0
        else:
            if self.move_lock_timer <= 0 and not self.is_dashing and self.stun_timer <= 0:
                if is_action_pressed('UP'): direction.y -= 1
                if is_action_pressed('DOWN'): direction.y += 1
                if is_action_pressed('LEFT'): direction.x -= 1
                if is_action_pressed('RIGHT'): direction.x += 1
                if self.controls_reversed:
                    direction = -direction

            if direction.length() > 0: direction = direction.normalize(); self.pose_hold_timer = 0.0

            move_x, move_y = 0, 0

            if is_action_pressed('DASH') and self.dash_cooldown_left <= 0 and direction.length() > 0 and self.move_lock_timer <= 0 and not self.is_dashing:
                self.is_dashing = True; self.dash_time_left = self.dash_duration; self.dash_cooldown_left = self.dash_cooldown; self.speed = self.dash_speed; self.dash_direction = direction
                if 'dash' in SOUNDS: SOUNDS['dash'].play()

            if self.is_dashing:
                self.dash_time_left -= dt
                if self.dash_time_left <= 0:
                    self.is_dashing = False; self.speed = self.normal_speed
                else: move_x = self.dash_direction.x * self.speed * dt; move_y = self.dash_direction.y * self.speed * dt
            else:
                move_x = direction.x * self.speed * dt; move_y = direction.y * self.speed * dt

        can_move_x, can_move_y = True, True
        can_move_x, can_move_y = True, True
        if tile_map:
            # 👈 0번(바닥)만 지나갈 수 있게 설정 (3번은 자동으로 벽이 됨)
            passable_tiles = [0]
            
            # X축 이동 검사
            check_x = self.pos.x + move_x + (self.radius if move_x > 0 else -self.radius)
            c_x, r_cur = int(check_x // TILE_SIZE), int(self.pos.y // TILE_SIZE)
            if move_x != 0 and 0 <= c_x < len(tile_map[0]) and 0 <= r_cur < len(tile_map):
                # 👈 [수정] tile_map[r_cur][c_x] != 0 이면 못 지나가게 막음
                if tile_map[r_cur][c_x] not in passable_tiles: 
                    can_move_x = False
            
            # Y축 이동 검사
            check_y = self.pos.y + move_y + (self.radius if move_y > 0 else -self.radius)
            r_y, c_cur = int(check_y // TILE_SIZE), int(self.pos.x // TILE_SIZE)
            if move_y != 0 and 0 <= r_y < len(tile_map) and 0 <= c_cur < len(tile_map[0]):
                # 👈 [수정] 0번 타일이 아니면 무조건 벽 취급
                if tile_map[r_y][c_cur] not in passable_tiles: 
                    can_move_y = False

        if can_move_x: self.pos.x += move_x
        if can_move_y: self.pos.y += move_y

        if self.push_timer > 0:
            self.push_timer -= dt
            px = self.push_vel.x * dt
            py = self.push_vel.y * dt
            hit_wall = False
            p_can_x, p_can_y = True, True
            if tile_map:
                c_x_p = int((self.pos.x + px + (self.radius if px > 0 else -self.radius)) // TILE_SIZE)
                r_cur_p = int(self.pos.y // TILE_SIZE)
                if 0 <= c_x_p < len(tile_map[0]) and 0 <= r_cur_p < len(tile_map):
                    if tile_map[r_cur_p][c_x_p] not in [0]: p_can_x = False; hit_wall = True
                else: p_can_x = False; hit_wall = True
                r_y_p = int((self.pos.y + py + (self.radius if py > 0 else -self.radius)) // TILE_SIZE)
                c_cur_p = int(self.pos.x // TILE_SIZE)
                if 0 <= r_y_p < len(tile_map) and 0 <= c_cur_p < len(tile_map[0]):
                    if tile_map[r_y_p][c_cur_p] not in [0]: p_can_y = False; hit_wall = True
                else: p_can_y = False; hit_wall = True
            if p_can_x: self.pos.x += px
            if p_can_y: self.pos.y += py
            if hit_wall:
                self.push_timer = 0
                self.push_vel = pygame.math.Vector2(0, 0)
            
        if not getattr(self, 'frozen', False):
            if direction.length() == 0 and not self.is_dashing: self.frame_index += self.animation_speed * dt
            else: self.frame_index += (self.animation_speed * 1.5) * dt

        self.pos.x = max(self.radius, min(room_w - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(room_h - self.radius, self.pos.y))

    def draw(self, surface, cam_x, cam_y):
        draw_x = int(self.pos.x - cam_x); draw_y = int(self.pos.y - cam_y)
        is_moving = (is_action_pressed('UP') or is_action_pressed('DOWN') or is_action_pressed('LEFT') or is_action_pressed('RIGHT'))
        if self.move_lock_timer > 0: is_moving = False
        if getattr(self, 'is_auto_walking', False): is_moving = True
        if getattr(self, 'frozen', False): is_moving = False  # 👈 보스 사망 페이드아웃 등에서 강제로 대기 모션

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
            if len(run_anim) > 0: base_anim_list = [run_anim[0]] 
            else: base_anim_list = IMAGES.get('player_idle', [])
        else: base_anim_list = IMAGES.get('player_idle', [])
            
        if len(base_anim_list) == 0: base_anim_list = IMAGES.get('player_idle', [])

        if len(base_anim_list) > 0:
            current_frame = int(self.frame_index) % len(base_anim_list)
            base_img = base_anim_list[current_frame]
            if base_anim_list == IMAGES.get('player_idle', []) and self.facing == 'left': base_img = pygame.transform.flip(base_img, True, False)
            if self.is_dashing: self.afterimages.append({'pos': pygame.math.Vector2(self.pos.x, self.pos.y), 'img': base_img, 'timer': 0.2})
            for ghost in self.afterimages:
                alpha = max(0, min(255, int(120 * (ghost['timer'] / 0.2))))
                ghost_img = ghost['img'].copy()
                ghost_img.set_alpha(alpha)
                surface.blit(ghost_img, ghost_img.get_rect(center=(int(ghost['pos'].x - cam_x), int(ghost['pos'].y - cam_y))))
            
            if self.dust_progress > 0:
                h = base_img.get_height()
                w = base_img.get_width()
                dust_h = int(h * self.dust_progress)
                if dust_h < h:
                    crop_rect = pygame.Rect(0, dust_h, w, h - dust_h)
                    surface.blit(base_img, (draw_x - w//2, draw_y - h//2 + dust_h), crop_rect)
            else:
                if self.inv_timer > 0:
                    if int(pygame.time.get_ticks() / 100) % 2 == 0:
                        pass
                    else:
                        surface.blit(base_img, base_img.get_rect(center=(draw_x, draw_y)))
                else:
                    surface.blit(base_img, base_img.get_rect(center=(draw_x, draw_y)))
                
        elif 'player' in IMAGES: surface.blit(IMAGES['player'], (draw_x - self.radius, draw_y - self.radius))
        else: pygame.draw.circle(surface, PLAYER_COLOR, (draw_x, draw_y), self.radius)

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
                att_frame = min(int(progress * len(attack_anim_list)), len(attack_anim_list) - 1)
                attack_img = attack_anim_list[att_frame]
                offset_x, offset_y = 45, 60  
                ax, ay = draw_x, draw_y
                if self.facing == 'right': ax += offset_x
                elif self.facing == 'left': ax -= offset_x
                elif self.facing == 'up': ay -= offset_y
                elif self.facing == 'down': ay += offset_y
                surface.blit(attack_img, attack_img.get_rect(center=(ax, ay)))

        # 👈 방어막 렌더링 추가
        if self.has_shield:
            shield_anim = IMAGES.get('shield_anim', [])
            if shield_anim:
                # 원본 이미지를 복사한 뒤 투명도를 적용합니다
                frame = shield_anim[int(self.shield_anim_timer) % len(shield_anim)].copy()
                frame.set_alpha(160)  # 👈 투명도 조절 (0: 완전 투명 ~ 255: 완전 불투명)
                surface.blit(frame, frame.get_rect(center=(draw_x, draw_y)))
            else:
                pygame.draw.circle(surface, (100, 200, 255, 150), (draw_x, draw_y), self.radius + 15, 3)

        # 👈 스턴 상태 시각 효과 (노란색 원형 + 텍스트)
        if self.stun_timer > 0:
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.015))
            stun_radius = int(18 + 6 * pulse)
            pygame.draw.circle(surface, (255, 255, 50), (draw_x, draw_y), stun_radius, 3)
            pygame.draw.circle(surface, (200, 200, 0), (draw_x, draw_y), stun_radius + 4, 2)

        if self.controls_reversed:
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.008))
            aura_r = int(self.radius + 20 + 8 * pulse)
            aura_surf = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (120, 40, 200, int(80 + 60 * pulse)), (aura_r, aura_r), aura_r)
            pygame.draw.circle(aura_surf, (180, 80, 255, int(150 + 80 * pulse)), (aura_r, aura_r), aura_r, 3)
            surface.blit(aura_surf, (draw_x - aura_r, draw_y - aura_r))

class Bullet:
    def __init__(self, x, y, target_x, target_y):
        self.pos = pygame.math.Vector2(x, y); self.speed = 1200; self.radius = 9
        direction = pygame.math.Vector2(target_x - x, target_y - y)
        self.direction = direction.normalize() if direction.length() > 0 else pygame.math.Vector2(1, 0)
    def update(self, dt): self.pos += self.direction * self.speed * dt
    def draw(self, surface, cam_x, cam_y): pygame.draw.circle(surface, BULLET_COLOR, (int(self.pos.x - cam_x), int(self.pos.y - cam_y)), self.radius)

class EnemyBullet:
    def __init__(self, x, y, target_x, target_y, damage=1):
        self.pos = pygame.math.Vector2(x, y)
        self.speed = int(400 * DIFF[current_difficulty]['proj_speed_mult'])
        self.radius = 45
        self.damage = damage
        # 연필탄인지 확인하기 위한 구분값 (나중에 필요시)
        self.is_pencil_tip = False
        # 버블탄인지 확인하기 위한 구분값
        self.is_bubble = False
        # 붕대탄인지 확인하기 위한 구분값
        self.is_bandage = False
        # 알약 보스 탄막인지 확인하   위한 구분값
        self.is_pill_bullet = False
        # 파란 알약 탄막인지 (체력 회복)
        self.is_healing_pill = False
        # 배드민턴공 탄막인지 (플레이어가 쳐낼 수 있음)
        self.is_shuttle = False
        self.is_reflected = False
        self.is_side_dish = False
        self.side_dish_type = 1
        self.is_wire_scraps = False
        self.is_text_bullet = False
        self.text_content = ""
        self.is_boss_soccer = False
        self.boss_soccer_bounces = 0
        self.boss_soccer_max_bounces = 3
        self.boss_soccer_tile_map = None
        # 배드민턴공 발사한 몬스터 참조 (역공 시 데미지용)
        self.owner_racket = None
        # 배드민턴공 이동 거리 누적
        self.travel_distance = 0.0
        # 배드민턴공 최대 사거리
        self.max_travel_distance = 500
        # 보스 중앙 좌표 (탄막이 조여오는 목표점)
        self.boss_center = None
        # 중앙 도달 판정 거리
        self.arrive_threshold = 20
        # 알파 마스크 기반 충돌 판정용
        self.rotated_img = None
        self.mask = None
        
        direction = pygame.math.Vector2(target_x - x, target_y - y)
        self.direction = direction.normalize() if direction.length() > 0 else pygame.math.Vector2(1, 0)

    def update(self, dt):
        # pill 탄막이 이미 도달했으면 더 이상 이동하지 않음
        if self.is_pill_bullet and getattr(self, 'dead', False):
            return
        # 배드민턴공이 이미 변신/파훼 처리되었으면 이동하지 않음
        if self.is_shuttle and getattr(self, 'dead', False):
            return

        self.pos += self.direction * self.speed * dt
        
        if self.is_boss_soccer:
            if self.boss_soccer_tile_map is not None:
                tm = self.boss_soccer_tile_map
                room_w = len(tm[0]) * TILE_SIZE
                room_h = len(tm) * TILE_SIZE
                old_pos = self.pos.copy()
                self.pos += self.direction * self.speed * dt
                hit_wall = False
                c, r = int(self.pos.x // TILE_SIZE), int(self.pos.y // TILE_SIZE)
                if 0 <= r < len(tm) and 0 <= c < len(tm[0]) and tm[r][c] in [1, 2, 3]:
                    hit_wall = True
                elif self.pos.x < self.radius or self.pos.x > room_w - self.radius:
                    hit_wall = True
                elif self.pos.y < self.radius or self.pos.y > room_h - self.radius:
                    hit_wall = True
                elif c < 0 or c >= len(tm[0]) or r < 0 or r >= len(tm):
                    hit_wall = True
                if hit_wall:
                    self.boss_soccer_bounces += 1
                    if self.boss_soccer_bounces >= self.boss_soccer_max_bounces:
                        self.dead = True
                        self.pos = pygame.math.Vector2(-10000, -10000)
                        return
                    x_hit = False; y_hit = False
                    nx = old_pos.x + self.direction.x * self.speed * dt
                    ny = old_pos.y + self.direction.y * self.speed * dt
                    if nx < self.radius or nx > room_w - self.radius:
                        x_hit = True
                    else:
                        xc, xr = int(nx // TILE_SIZE), int(old_pos.y // TILE_SIZE)
                        if 0 <= xr < len(tm) and 0 <= xc < len(tm[0]) and tm[xr][xc] in [1, 2, 3]:
                            x_hit = True
                    if ny < self.radius or ny > room_h - self.radius:
                        y_hit = True
                    else:
                        yc, yr = int(old_pos.x // TILE_SIZE), int(ny // TILE_SIZE)
                        if 0 <= yr < len(tm) and 0 <= yc < len(tm[0]) and tm[yr][yc] in [1, 2, 3]:
                            y_hit = True
                    if x_hit: self.direction.x = -self.direction.x
                    if y_hit: self.direction.y = -self.direction.y
                    if not x_hit and not y_hit:
                        self.direction.x = -self.direction.x
                        self.direction.y = -self.direction.y
                    self.pos = old_pos
            else:
                self.pos += self.direction * self.speed * dt
            return
        
        # 배드민턴공 이동 거리 누적
        if self.is_shuttle and not self.is_reflected:
            self.travel_distance += self.speed * dt
            # 사거리 도달 시 공몬스터로 변신 플래그
            if self.travel_distance >= self.max_travel_distance:
                self.dead = True
                return
        
        # pill 탄막이 중앙에 도달하면 사라짐 처리
        if self.is_pill_bullet and self.boss_center is not None:
            if self.pos.distance_to(self.boss_center) < self.arrive_threshold:
                self.dead = True  # 도달 플래그 설정
                self.pos = pygame.math.Vector2(-10000, -10000)

    def _prepare_mask(self):
        """이미지 회전 및 마스크를 미리 준비합니다."""
        if self.is_bubble and 'bubble_small' in IMAGES:
            self.rotated_img = IMAGES['bubble_small']
            self.mask = pygame.mask.from_surface(self.rotated_img)
        elif self.is_pencil_tip and 'pencil_tip' in IMAGES:
            angle = math.degrees(math.atan2(-self.direction.y, self.direction.x)) - 90
            self.rotated_img = pygame.transform.rotate(IMAGES['pencil_tip'], angle)
            self.mask = pygame.mask.from_surface(self.rotated_img)

    def collides_with_mask(self, player):
        """알파 마스크 기반 충돌 판정을 수행합니다. 투명한 부분은 충돌하지 않습니다."""
        if self.mask is None:
            # 마스크가 없으면 기존 원형 판정 사용
            return self.pos.distance_to(player.pos) < self.radius + player.radius
        
        # 1단계: 거리 기반 빠른 사전 검사 (마스크 연산 비용 줄이기)
        img_w, img_h = self.rotated_img.get_size()
        img_radius = math.sqrt(img_w * img_w + img_h * img_h) / 2
        if self.pos.distance_to(player.pos) > img_radius + player.radius:
            return False
        
        # 2단계: 플레이어의 마스크 생성
        player_mask_size = int(player.radius * 2)
        player_surface = pygame.Surface((player_mask_size, player_mask_size), pygame.SRCALPHA)
        pygame.draw.circle(player_surface, (255, 255, 255, 255), (int(player.radius), int(player.radius)), int(player.radius))
        player_mask = pygame.mask.from_surface(player_surface)
        
        # 3단계: 마스크 겹침 검사
        img_rect = self.rotated_img.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        offset_x = int(player.pos.x - player.radius - img_rect.x)
        offset_y = int(player.pos.y - player.radius - img_rect.y)
        
        overlap = self.mask.overlap(player_mask, (offset_x, offset_y))
        return overlap is not None

    def draw(self, surface, cam_x, cam_y):
        draw_x, draw_y = int(self.pos.x - cam_x), int(self.pos.y - cam_y)
        
        if self.is_bubble and 'bubble_small' in IMAGES:
            surface.blit(IMAGES['bubble_small'], IMAGES['bubble_small'].get_rect(center=(draw_x, draw_y)))
        elif self.is_pencil_tip and 'pencil_tip' in IMAGES:
            # 1. 이동 방향(self.direction)을 각도로 변환
            # atan2는 라디안 값을 주므로 degrees로 변환
            angle = math.degrees(math.atan2(-self.direction.y, self.direction.x)) - 90
            
            # 2. 이미지 회전
            rotated_img = pygame.transform.rotate(IMAGES['pencil_tip'], angle)
            surface.blit(rotated_img, rotated_img.get_rect(center=(draw_x, draw_y)))
        elif self.is_bandage:
            # 👈 붕  끈 투사체: 이미지가 있으면 사용, 없으면 원형
            if 'bandage_rope' in IMAGES:
                # 이동 방향에 따라 회전
                angle = math.degrees(math.atan2(-self.direction.y, self.direction.x))
                rot_img = pygame.transform.rotate(IMAGES['bandage_rope'], angle)
                surface.blit(rot_img, rot_img.get_rect(center=(draw_x, draw_y)))
            else:
                pygame.draw.circle(surface, (240, 240, 220), (draw_x, draw_y), self.radius)
                pygame.draw.circle(surface, (200, 200, 160), (draw_x, draw_y), self.radius, 2)
        elif self.is_pill_bullet:
            # 👈 빙글빙글 회전하는 알약 탄막 + 발광 테두리
            rotation_speed = pygame.time.get_ticks() * 0.3  # 회전 속도
            glow_radius = 24

            if self.is_healing_pill:
                if 'pill_bullet_blue' in IMAGES:
                    rot_img = pygame.transform.rotate(IMAGES['pill_bullet_blue'], rotation_speed)
                    surface.blit(rot_img, rot_img.get_rect(center=(draw_x, draw_y)))
                    # 파란색 발광 테두리
                    glow_surf = pygame.Surface((glow_radius * 2 + 8, glow_radius * 2 + 8), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, (80, 160, 255, 100), (glow_radius + 4, glow_radius + 4), glow_radius + 4)
                    surface.blit(glow_surf, (draw_x - glow_radius - 4, draw_y - glow_radius - 4))
                    pygame.draw.circle(surface, (100, 180, 255), (draw_x, draw_y), glow_radius, 2)
                else:
                    pygame.draw.circle(surface, (30, 100, 255), (draw_x, draw_y), 12)
                    pygame.draw.circle(surface, (100, 180, 255), (draw_x, draw_y), 8)
            else:
                if 'pill_bullet_red' in IMAGES:
                    rot_img = pygame.transform.rotate(IMAGES['pill_bullet_red'], rotation_speed)
                    surface.blit(rot_img, rot_img.get_rect(center=(draw_x, draw_y)))
                    # 빨간색 발광 테두리
                    glow_surf = pygame.Surface((glow_radius * 2 + 8, glow_radius * 2 + 8), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, (255, 60, 60, 100), (glow_radius + 4, glow_radius + 4), glow_radius + 4)
                    surface.blit(glow_surf, (draw_x - glow_radius - 4, draw_y - glow_radius - 4))
                    pygame.draw.circle(surface, (255, 80, 80), (draw_x, draw_y), glow_radius, 2)
                else:
                    pygame.draw.circle(surface, (220, 40, 40), (draw_x, draw_y), 12)
                    pygame.draw.circle(surface, (255, 100, 80), (draw_x, draw_y), 8)
        elif self.is_shuttle:
            # 배드민턴공 투사체
            if self.is_reflected:
                # 반사된 공: 빨간색 발광
                glow_surf = pygame.Surface((90, 90), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (255, 100, 50, 120), (45, 45), 45)
                surface.blit(glow_surf, (draw_x - 45, draw_y - 45))
            if 'badminton_shuttle_2' in IMAGES:
                angle = math.degrees(math.atan2(-self.direction.y, self.direction.x))
                rot_img = pygame.transform.rotate(IMAGES['badminton_shuttle_2'], angle)
                surface.blit(rot_img, rot_img.get_rect(center=(draw_x, draw_y)))
            else:
                pygame.draw.circle(surface, (200, 200, 255), (draw_x, draw_y), 20)
                pygame.draw.circle(surface, (255, 255, 255), (draw_x, draw_y), 14)
        elif self.is_side_dish:
            img_key = f'side_dish_{self.side_dish_type}'
            if img_key in IMAGES:
                angle = math.degrees(math.atan2(-self.direction.y, self.direction.x))
                rot_img = pygame.transform.rotate(IMAGES[img_key], angle)
                glow_r = int(rot_img.get_width() * 0.15)
                glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (255, 200, 80, 60), (glow_r, glow_r), glow_r)
                surface.blit(glow_surf, glow_surf.get_rect(center=(draw_x, draw_y)))
                surface.blit(rot_img, rot_img.get_rect(center=(draw_x, draw_y)))
            else:
                pygame.draw.circle(surface, (200, 150, 50), (draw_x, draw_y), self.radius)
        elif self.is_wire_scraps:
            angle = math.atan2(-self.direction.y, self.direction.x)
            dx = math.cos(angle); dy = -math.sin(angle)
            px = math.cos(angle + math.pi / 2); py = -math.sin(angle + math.pi / 2)
            bx = draw_x - dx * 12; by = draw_y - dy * 12
            bl = (bx + px * 2, by + py * 2); br = (bx - px * 2, by - py * 2)
            fl = (draw_x + px * 2, draw_y + py * 2); fr = (draw_x - px * 2, draw_y - py * 2)
            tip = (draw_x + dx * 8, draw_y + dy * 8)
            pygame.draw.polygon(surface, (30, 30, 30), [bl, br, fr, fl])
            pygame.draw.polygon(surface, (30, 30, 30), [fl, fr, tip])
        elif getattr(self, 'is_boss_syringe', False):
            if 'syringe_3' in IMAGES:
                angle = math.degrees(math.atan2(-self.direction.y, self.direction.x))
                rot_img = pygame.transform.rotate(IMAGES['syringe_3'], angle)
                surface.blit(rot_img, rot_img.get_rect(center=(draw_x, draw_y)))
            else:
                pygame.draw.polygon(surface, (200, 200, 200), [(draw_x, draw_y - 12), (draw_x - 5, draw_y + 8), (draw_x + 5, draw_y + 8)])
                pygame.draw.rect(surface, (180, 180, 180), (draw_x - 3, draw_y + 8, 6, 10))
        elif self.is_text_bullet and self.text_content:
            try:
                font_size = max(22, min(34, 18 + len(self.text_content) * 2))
                font = get_korean_font(font_size, bold=True)
                outline_surf = font.render(self.text_content, True, (0, 0, 0))
                text_surf = font.render(self.text_content, True, (255, 255, 255))
                half_w = text_surf.get_width() // 2
                half_h = text_surf.get_height() // 2
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
                    surface.blit(outline_surf, (draw_x - half_w + dx, draw_y - half_h + dy))
                surface.blit(text_surf, (draw_x - half_w, draw_y - half_h))
            except: pass
        elif self.is_boss_soccer:
            if 'soccer_ball_7' in IMAGES:
                angle = math.degrees(math.atan2(-self.direction.y, self.direction.x))
                rot_img = pygame.transform.rotate(IMAGES['soccer_ball_7'], angle)
                surface.blit(rot_img, rot_img.get_rect(center=(draw_x, draw_y)))
            else:
                pygame.draw.circle(surface, (255, 255, 255), (draw_x, draw_y), self.radius)
                pygame.draw.circle(surface, (50, 50, 50), (draw_x, draw_y), self.radius, 3)
                for a in range(0, 360, 60):
                    px = draw_x + int(math.cos(math.radians(a)) * self.radius * 0.5)
                    py = draw_y + int(math.sin(math.radians(a)) * self.radius * 0.5)
                    pygame.draw.circle(surface, (50, 50, 50), (px, py), 4)
        else:
            front = self.pos + self.direction * (self.radius * 1.8)
            back_left = self.pos - self.direction * self.radius + pygame.math.Vector2(-self.direction.y, self.direction.x) * (self.radius * 0.6)
            back_right = self.pos - self.direction * self.radius + pygame.math.Vector2(self.direction.y, -self.direction.x) * (self.radius * 0.6)
            points = [(int(front.x - cam_x), int(front.y - cam_y)), (int(back_left.x - cam_x), int(back_left.y - cam_y)), (int(back_right.x - cam_x), int(back_right.y - cam_y))]
            pygame.draw.polygon(surface, (40, 40, 40), points)
            pygame.draw.polygon(surface, (180, 20, 20), points, 1)

class DiceBullet:
    def __init__(self, x, y, target_x, target_y, damage=1, room_w=9999, room_h=9999):
        self.pos = pygame.math.Vector2(x, y)
        self.start_pos = pygame.math.Vector2(x, y)
        self.speed = int(350 * DIFF[current_difficulty]['proj_speed_mult'])
        self.damage = damage
        self.radius = 18
        self.rotation = 0.0
        self.rotation_speed = 720.0
        self.arrived = False
        self.number_phase = False
        self.number_timer = 0.0
        self.number_duration = 1.2
        self.spin_interval = 0.15
        self.spin_timer = 0.0
        self.display_number = 1
        self.final_number = 0
        self.alive = True
        self.number_confirmed = False
        self.mini_dices_spawned = False
        self.gold_text_timer = 0.0
        self.gold_text_duration = 0.8
        self.room_w = room_w
        self.room_h = room_h
        self.total_distance = self.start_pos.distance_to(pygame.math.Vector2(target_x, target_y))
        self.traveled = 0.0
        direction = pygame.math.Vector2(target_x - x, target_y - y)
        self.direction = direction.normalize() if direction.length() > 0 else pygame.math.Vector2(1, 0)

    def update(self, dt):
        if not self.alive:
            return
        if self.number_phase:
            self.number_timer += dt
            self.rotation += self.rotation_speed * dt
            if self.gold_text_timer > 0:
                self.gold_text_timer -= dt
            if self.number_timer >= self.number_duration:
                if not self.number_confirmed:
                    self.number_confirmed = True
                    self.final_number = random.randint(1, 6)
                    self.display_number = self.final_number
                    self.gold_text_timer = self.gold_text_duration
                    self.mini_dices_spawned = True
            else:
                self.spin_timer += dt
                if self.spin_timer >= self.spin_interval:
                    self.spin_timer = 0.0
                    self.display_number = random.randint(1, 6)
            return
        move_dist = self.speed * dt
        self.traveled += move_dist
        self.pos += self.direction * move_dist
        self.rotation += self.rotation_speed * dt
        if self.traveled >= self.total_distance:
            self.pos.x = max(self.radius, min(self.room_w - self.radius, self.pos.x))
            self.pos.y = max(self.radius, min(self.room_h - self.radius, self.pos.y))
            self.number_phase = True
            self.number_timer = 0.0
        elif self.pos.x - self.radius <= 0 or self.pos.x + self.radius >= self.room_w or self.pos.y - self.radius <= 0 or self.pos.y + self.radius >= self.room_h:
            self.pos.x = max(self.radius, min(self.room_w - self.radius, self.pos.x))
            self.pos.y = max(self.radius, min(self.room_h - self.radius, self.pos.y))
            self.number_phase = True
            self.number_timer = 0.0

    def _draw_dice(self, surface, cx, cy, size, rotation, num_dots=None):
        dice_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        corners = []
        for angle_offset in [math.pi / 4, 3 * math.pi / 4, 5 * math.pi / 4, 7 * math.pi / 4]:
            rx = size * 0.85 * math.cos(angle_offset)
            ry = size * 0.85 * math.sin(angle_offset)
            corners.append((size + rx, size + ry))
        pygame.draw.polygon(dice_surf, (255, 255, 255), corners)
        pygame.draw.polygon(dice_surf, (60, 60, 60), corners, 2)
        dot_r = max(2, size // 5)
        dot_positions = {
            1: [(0, 0)],
            2: [(-0.35, -0.35), (0.35, 0.35)],
            3: [(-0.35, -0.35), (0, 0), (0.35, 0.35)],
            4: [(-0.35, -0.35), (0.35, -0.35), (-0.35, 0.35), (0.35, 0.35)],
            5: [(-0.35, -0.35), (0.35, -0.35), (0, 0), (-0.35, 0.35), (0.35, 0.35)],
            6: [(-0.35, -0.35), (0.35, -0.35), (-0.35, 0), (0.35, 0), (-0.35, 0.35), (0.35, 0.35)]
        }
        dots = num_dots if num_dots else random.randint(1, 6)
        for dx, dy in dot_positions.get(dots, [(0, 0)]):
            pygame.draw.circle(dice_surf, (20, 20, 20), (int(size + dx * size), int(size + dy * size)), dot_r)
        rotated = pygame.transform.rotate(dice_surf, rotation)
        surface.blit(rotated, rotated.get_rect(center=(cx, cy)))

    def draw(self, surface, cam_x, cam_y):
        if not self.alive:
            return
        draw_x = int(self.pos.x - cam_x)
        draw_y = int(self.pos.y - cam_y)
        if self.number_phase and self.number_confirmed and self.gold_text_timer <= 0 and self.mini_dices_spawned:
            return
        if self.number_phase:
            try:
                font = get_korean_font(40, bold=True)
                if self.number_confirmed and self.gold_text_timer > 0:
                    alpha = int(255 * min(1.0, self.gold_text_timer / (self.gold_text_duration * 0.5)))
                    num_str = str(self.display_number)
                    txt_surf = font.render(num_str, True, (255, 215, 50))
                    out_surf = font.render(num_str, True, (120, 90, 0))
                    float_offset = int((1.0 - self.gold_text_timer / self.gold_text_duration) * 80)
                    tx = draw_x - txt_surf.get_width() // 2
                    ty = draw_y - 40 - float_offset
                    gold_alpha_surf = pygame.Surface(txt_surf.get_size(), pygame.SRCALPHA)
                    gold_alpha_surf.blit(txt_surf, (0, 0))
                    gold_alpha_surf.set_alpha(alpha)
                    out_alpha_surf = pygame.Surface(out_surf.get_size(), pygame.SRCALPHA)
                    out_alpha_surf.blit(out_surf, (0, 0))
                    out_alpha_surf.set_alpha(alpha)
                    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                        surface.blit(out_alpha_surf, (tx + dx, ty + dy))
                    surface.blit(gold_alpha_surf, (tx, ty))
                elif not self.number_confirmed:
                    num_str = str(self.display_number)
                    txt_surf = font.render(num_str, True, (255, 50, 50))
                    out_surf = font.render(num_str, True, (80, 0, 0))
                    tx = draw_x - txt_surf.get_width() // 2
                    ty = draw_y - txt_surf.get_height() // 2
                    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                        surface.blit(out_surf, (tx + dx, ty + dy))
                    surface.blit(txt_surf, (tx, ty))
            except: pass
        else:
            self._draw_dice(surface, draw_x, draw_y, self.radius, self.rotation)


class MiniDice:
    def __init__(self, x, y, damage=1, room_w=2000, room_h=2000):
        self.pos = pygame.math.Vector2(x, y)
        self.speed = random.uniform(250, 450) * DIFF[current_difficulty]['proj_speed_mult']
        self.damage = damage
        self.radius = 12
        self.rotation = random.uniform(0, 360)
        self.rotation_speed = random.uniform(400, 900)
        self.bounce_count = 0
        self.max_bounces = 2
        self.alive = True
        self.lifetime = 12.0
        self.room_w = room_w
        self.room_h = room_h
        angle = random.uniform(0, 2 * math.pi)
        self.direction = pygame.math.Vector2(math.cos(angle), math.sin(angle)).normalize()
        self.dot_face = random.randint(1, 6)

    def update(self, dt):
        if not self.alive:
            return
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            return
        self.pos += self.direction * self.speed * dt
        self.rotation += self.rotation_speed * dt
        self.speed = max(150, self.speed - 30 * dt)
        bounced = False
        if self.pos.x - self.radius <= 0:
            self.pos.x = self.radius
            self.direction.x = abs(self.direction.x)
            bounced = True
        elif self.pos.x + self.radius >= self.room_w:
            self.pos.x = self.room_w - self.radius
            self.direction.x = -abs(self.direction.x)
            bounced = True
        if self.pos.y - self.radius <= 0:
            self.pos.y = self.radius
            self.direction.y = abs(self.direction.y)
            bounced = True
        elif self.pos.y + self.radius >= self.room_h:
            self.pos.y = self.room_h - self.radius
            self.direction.y = -abs(self.direction.y)
            bounced = True
        if bounced:
            self.bounce_count += 1
            if self.bounce_count >= self.max_bounces:
                self.alive = False

    def draw(self, surface, cam_x, cam_y):
        if not self.alive:
            return
        draw_x = int(self.pos.x - cam_x)
        draw_y = int(self.pos.y - cam_y)
        size = self.radius
        dice_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        corners = []
        for angle_offset in [math.pi / 4, 3 * math.pi / 4, 5 * math.pi / 4, 7 * math.pi / 4]:
            rx = size * 0.85 * math.cos(angle_offset)
            ry = size * 0.85 * math.sin(angle_offset)
            corners.append((size + rx, size + ry))
        pygame.draw.polygon(dice_surf, (255, 255, 240), corners)
        pygame.draw.polygon(dice_surf, (80, 80, 80), corners, 1)
        dot_r = max(1, size // 4)
        dot_positions = {
            1: [(0, 0)],
            2: [(-0.35, -0.35), (0.35, 0.35)],
            3: [(-0.35, -0.35), (0, 0), (0.35, 0.35)],
            4: [(-0.35, -0.35), (0.35, -0.35), (-0.35, 0.35), (0.35, 0.35)],
            5: [(-0.35, -0.35), (0.35, -0.35), (0, 0), (-0.35, 0.35), (0.35, 0.35)],
            6: [(-0.35, -0.35), (0.35, -0.35), (-0.35, 0), (0.35, 0), (-0.35, 0.35), (0.35, 0.35)]
        }
        for dx, dy in dot_positions.get(self.dot_face, [(0, 0)]):
            pygame.draw.circle(dice_surf, (20, 20, 20), (int(size + dx * size), int(size + dy * size)), dot_r)
        rotated = pygame.transform.rotate(dice_surf, self.rotation)
        surface.blit(rotated, rotated.get_rect(center=(draw_x, draw_y)))
        
class BoomerangProjectile:
    def __init__(self, start_x, start_y, target_x, target_y, damage=1, room_w=9999, room_h=9999):
        self.pos = pygame.math.Vector2(start_x, start_y)
        self.start_pos = pygame.math.Vector2(start_x, start_y)
        self.damage = damage
        self.radius = 30
        self.t = 0.0
        self.total_time = 4.0
        self.rotation = 0.0
        self.rotation_speed = 720.0
        self.scatter_timer = 0.0
        self.scatter_interval = 0.25
        self.returned = False
        self.owner = None
        self.room_w = room_w
        self.room_h = room_h
        dir_vec = pygame.math.Vector2(target_x - start_x, target_y - start_y)
        dist = dir_vec.length() if dir_vec.length() > 0 else 1
        self.angle = math.atan2(dir_vec.y, dir_vec.x)
        margin = 80
        max_a = min(start_x - margin, room_w - start_x - margin, start_y - margin, room_h - start_y - margin, dist * 1.2)
        self.a = max(200, max_a)
        self.b = max(120, self.a * 0.5)
        cos_a = math.cos(self.angle); sin_a = math.sin(self.angle)
        self.center = pygame.math.Vector2(start_x + cos_a * self.a, start_y + sin_a * self.a)

    def update(self, dt, enemy_bullets_list=None):
        if self.returned: return
        self.t += dt / self.total_time
        self.rotation += self.rotation_speed * dt
        theta = self.t * 2 * math.pi + math.pi
        cos_a = math.cos(self.angle); sin_a = math.sin(self.angle)
        lx = self.a * math.cos(theta)
        ly = self.b * math.sin(theta)
        nx = self.center.x + lx * cos_a - ly * sin_a
        ny = self.center.y + lx * sin_a + ly * cos_a
        margin = 20
        self.pos.x = max(margin, min(self.room_w - margin, nx))
        self.pos.y = max(margin, min(self.room_h - margin, ny))

        self.scatter_timer += dt
        if self.scatter_timer >= self.scatter_interval and enemy_bullets_list is not None:
            self.scatter_timer = 0.0
            side_dish_type = random.randint(1, 4)
            angle = random.uniform(0, 2 * math.pi)
            tx = self.pos.x + math.cos(angle) * 10
            ty = self.pos.y + math.sin(angle) * 10
            eb = EnemyBullet(self.pos.x, self.pos.y, tx, ty, damage=self.damage)
            eb.is_side_dish = True
            eb.side_dish_type = side_dish_type
            eb.speed = int(280 * DIFF[current_difficulty]['proj_speed_mult'])
            eb.radius = 35
            enemy_bullets_list.append(eb)

        if self.t >= 1.0:
            self.returned = True

    def draw(self, surface, cam_x, cam_y):
        if self.returned: return
        draw_x = int(self.pos.x - cam_x)
        draw_y = int(self.pos.y - cam_y)
        if 'single_tray_1' in IMAGES:
            rot_img = pygame.transform.rotate(IMAGES['single_tray_1'], self.rotation)
            surface.blit(rot_img, rot_img.get_rect(center=(draw_x, draw_y)))
        else:
            pygame.draw.circle(surface, (180, 140, 100), (draw_x, draw_y), self.radius)

class DustBurst:
    def __init__(self, x, y):
        self.pos = pygame.math.Vector2(x, y)
        self.puffs = []
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(100, 350)
            self.puffs.append({
                'x': x, 'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed - random.uniform(50, 200),
                'size': random.uniform(8, 25),
                'lifetime': random.uniform(0.4, 1.0),
                'max_lifetime': random.uniform(0.4, 1.0),
                'color': random.choice([(180, 160, 130), (150, 130, 100), (200, 180, 150), (120, 100, 80)])
            })
        self.ring_radius = 0.0
        self.ring_max = 80
        self.ring_lifetime = 0.5
        self.ring_max_lifetime = 0.5

    def update(self, dt):
        self.ring_lifetime -= dt
        self.ring_radius += 300 * dt
        for p in self.puffs:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += 400 * dt
            p['vx'] *= 0.95
            p['lifetime'] -= dt
        self.puffs = [p for p in self.puffs if p['lifetime'] > 0]

    def is_done(self):
        return self.ring_lifetime <= 0 and len(self.puffs) == 0

    def draw(self, surface, cam_x, cam_y):
        if self.ring_lifetime > 0:
            ratio = self.ring_lifetime / self.ring_max_lifetime
            alpha = int(200 * ratio)
            r = int(self.ring_radius)
            if r > 0:
                ring_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                thickness = max(2, int(6 * ratio))
                pygame.draw.circle(ring_surf, (200, 180, 140, alpha), (r, r), r, thickness)
                surface.blit(ring_surf, (int(self.pos.x - cam_x - r), int(self.pos.y - cam_y - r)))
        for p in self.puffs:
            ratio = p['lifetime'] / p['max_lifetime']
            alpha = max(0, int(200 * ratio))
            size = max(1, int(p['size'] * (0.5 + 0.5 * ratio)))
            puff_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(puff_surf, (*p['color'], min(255, alpha)), (size, size), size)
            surface.blit(puff_surf, (int(p['x'] - cam_x - size), int(p['y'] - cam_y - size)))

class ChopstickRain:
    def __init__(self, target_x, target_y, damage=1):
        self.target_pos = pygame.math.Vector2(target_x, target_y)
        self.pos = pygame.math.Vector2(target_x, target_y - 800)
        self.damage = damage
        self.radius = 35
        self.fall_speed = 0.0
        self.gravity = 1200
        self.warning_duration = 0.0
        self.warning_timer = 0.0
        self.phase = 'FALLING'
        self.done = False
        self.fall_speed = 150

    def update(self, dt, player=None, damage_texts=None, particles=None):
        if self.done: return
        if self.phase == 'FALLING':
            self.fall_speed += 900 * dt
            self.pos.y += self.fall_speed * dt
            if self.pos.y >= self.target_pos.y:
                self.pos.y = self.target_pos.y
                self.phase = 'DONE'
                if player and not (player.is_dashing or player.inv_timer > 0):
                    if self.pos.distance_to(player.pos) < self.radius + player.radius:
                        res = player.take_damage(self.damage)
                        if res == "BLOCKED" and damage_texts is not None:
                            damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                        elif res == True:
                            if damage_texts is not None:
                                damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                            if particles is not None:
                                for _ in range(10): particles.append(Particle(self.pos.x, self.pos.y))
                self.done = True

    def draw(self, surface, cam_x, cam_y):
        if self.done: return
        if self.phase == 'FALLING':
            progress = min(1.0, (self.target_pos.y - self.pos.y) / 800)
            alpha = int(40 + 180 * progress)
            tx = int(self.target_pos.x - cam_x)
            ty = int(self.target_pos.y - cam_y)
            warn_r = 15
            warn_surf = pygame.Surface((warn_r * 2, warn_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(warn_surf, (255, 0, 0, alpha), (warn_r, warn_r), warn_r)
            surface.blit(warn_surf, (tx - warn_r, ty - warn_r))
            draw_x = int(self.pos.x - cam_x)
            draw_y = int(self.pos.y - cam_y)
            if 'chopstick_1' in IMAGES:
                rot_img = IMAGES['chopstick_1']
                surface.blit(rot_img, rot_img.get_rect(center=(draw_x, draw_y)))
            else:
                pygame.draw.polygon(surface, (200, 180, 140), [(draw_x, draw_y + 25), (draw_x - 6, draw_y - 15), (draw_x + 6, draw_y - 15)])

class FloatingBullet:
    def __init__(self, x, y, room_w, room_h, damage=1): # 👈 맵의 가로, 세로 크기를 인수로 받습니다.
        self.pos = pygame.math.Vector2(x, y)
        self.speed = random.uniform(140, 200) * DIFF[current_difficulty]['proj_speed_mult']
        self.radius = 44
        self.damage = damage
        self.lifetime = 10.0
        self.room_w = max(100, room_w)
        self.room_h = max(100, room_h)
        
        angle = random.uniform(0, 2 * math.pi)
        self.direction = pygame.math.Vector2(math.cos(angle), math.sin(angle))
        self.change_dir_timer = random.uniform(1.0, 2.0)
        self.exploded = False
        # 알파 마스크 기반 충돌 판정용
        self.mask = None
        self.rotated_img = None
        if 'bubble_large' in IMAGES:
            self.rotated_img = IMAGES['bubble_large']
            self.mask = pygame.mask.from_surface(self.rotated_img)

    def update(self, dt):
        if self.exploded: return
        
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.exploded = True 
            return
            
        self.change_dir_timer -= dt
        if self.change_dir_timer <= 0:
            angle = random.uniform(0, 2 * math.pi)
            target_dir = pygame.math.Vector2(math.cos(angle), math.sin(angle))
            self.direction = self.direction.lerp(target_dir, 0.3).normalize()
            self.change_dir_timer = random.uniform(1.0, 2.0)
            
        self.pos += self.direction * self.speed * dt

        # 👇 [새로 추가] 맵 좌우/상하 테두리에 닿으면 반사하는 로직 (맵 밖 이탈 방지)
        margin = self.radius + 12 # 벽에서 살짝 떨어질 여백
        
        # 좌우 벽 충돌 검사
        if self.pos.x < margin:
            self.pos.x = margin
            self.direction.x *= -1 # X축 이동 방향 반전
        elif self.pos.x > self.room_w - margin:
            self.pos.x = self.room_w - margin
            self.direction.x *= -1
            
        # 상하 벽 충돌 검사
        if self.pos.y < margin:
            self.pos.y = margin
            self.direction.y *= -1 # Y축 이동 방향 반전
        elif self.pos.y > self.room_h - margin:
            self.pos.y = self.room_h - margin
            self.direction.y *= -1

    def collides_with_mask(self, player):
        """알파 마스크 기반 충돌 판정을 수행합니다. 투명한 부분은 충돌하지 않습니다."""
        if self.mask is None:
            return self.pos.distance_to(player.pos) < self.radius + player.radius
        
        img_w, img_h = self.rotated_img.get_size()
        img_radius = math.sqrt(img_w * img_w + img_h * img_h) / 2
        if self.pos.distance_to(player.pos) > img_radius + player.radius:
            return False
        
        player_mask_size = int(player.radius * 2)
        player_surface = pygame.Surface((player_mask_size, player_mask_size), pygame.SRCALPHA)
        pygame.draw.circle(player_surface, (255, 255, 255, 255), (int(player.radius), int(player.radius)), int(player.radius))
        player_mask = pygame.mask.from_surface(player_surface)
        
        img_rect = self.rotated_img.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        offset_x = int(player.pos.x - player.radius - img_rect.x)
        offset_y = int(player.pos.y - player.radius - img_rect.y)
        
        overlap = self.mask.overlap(player_mask, (offset_x, offset_y))
        return overlap is not None

    def explode(self, enemy_bullets_list):
        for i in range(16):
            angle = i * (math.pi / 8)
            target_x = self.pos.x + math.cos(angle) * 10
            target_y = self.pos.y + math.sin(angle) * 10
            eb = EnemyBullet(self.pos.x, self.pos.y, target_x, target_y, damage=self.damage)
            eb.is_bubble = True
            eb._prepare_mask()
            enemy_bullets_list.append(eb)
        self.pos.x = -10000
        
    def draw(self, surface, cam_x, cam_y):
        draw_x = int(self.pos.x - cam_x)
        draw_y = int(self.pos.y - cam_y + math.sin(pygame.time.get_ticks() * 0.005) * 4)
        
        if 'bubble_large' in IMAGES:
            img = IMAGES['bubble_large']
            if self.lifetime < 1.5 and int(self.lifetime * 8) % 2 == 0:
                red_overlay = pygame.Surface(img.get_size(), pygame.SRCALPHA)
                red_overlay.fill((255, 0, 0, 120))
                img = img.copy()
                img.blit(red_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(img, img.get_rect(center=(draw_x, draw_y)))
        else:
            pygame.draw.circle(surface, (150, 255, 200), (draw_x, draw_y), self.radius)

class WifiWave:
    def __init__(self, x, y, damage=1, max_radius=1500):
        self.pos = pygame.math.Vector2(x, y)
        self.current_radius = 0.0
        self.speed = 250 * DIFF[current_difficulty]['proj_speed_mult']
        self.damage = damage
        self.ring_thickness = 20
        self.max_radius = max_radius
        self.lifetime = 0.0
        self.dead = False
        self.is_wifi_wave = True
        self.radius = 0
        self._hit_player_ids = set()

    def update(self, dt):
        self.current_radius += self.speed * dt
        self.lifetime += dt
        if self.current_radius >= self.max_radius:
            self.dead = True

    def collides_with_mask(self, player):
        if self.dead: return False
        pid = id(player)
        if pid in self._hit_player_ids: return False
        dist = self.pos.distance_to(player.pos)
        half_t = self.ring_thickness / 2
        if (self.current_radius - half_t - player.radius) < dist < (self.current_radius + half_t + player.radius):
            self._hit_player_ids.add(pid)
            return True
        return False

    def draw(self, surface, cam_x, cam_y):
        if self.current_radius <= 0 or self.dead: return
        cx = int(self.pos.x - cam_x)
        cy = int(self.pos.y - cam_y)
        fade = max(0.2, 1.0 - (self.current_radius / self.max_radius) * 0.5)
        if fade <= 0.15: return
        pulse = (math.sin(self.lifetime * 6.0) + 1.0) / 2.0
        vw, vh = surface.get_size()
        r_outer = int(self.current_radius) + 20
        left = max(0, cx - r_outer)
        top = max(0, cy - r_outer)
        right = min(vw, cx + r_outer)
        bottom = min(vh, cy + r_outer)
        sw = right - left
        sh = bottom - top
        if sw <= 0 or sh <= 0: return
        local_cx = cx - left
        local_cy = cy - top
        wave_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        num_rings = 5
        for i in range(num_rings):
            ring_r = int(self.current_radius) - i * 8
            if ring_r <= 0: continue
            if i % 2 == 0:
                color = (int(30 + 70 * pulse), int(80 + 100 * pulse), int(200 + 55 * pulse))
            else:
                color = (int(100 - 70 * pulse), int(200 - 100 * pulse), int(255 - 55 * pulse))
            alpha = int(230 * fade * (1.0 - i * 0.08))
            thickness = max(3, int(10 * fade))
            pygame.draw.circle(wave_surf, (*color, min(255, max(0, alpha))), (local_cx, local_cy), ring_r, thickness)
        surface.blit(wave_surf, (left, top))

class Enemy:
    def __init__(self, x, y, enemy_type='normal'):
        self.pos = pygame.math.Vector2(x, y)
        self.type = enemy_type
        self.is_boss = (enemy_type in ['boss', 'pill_boss'])
        self.flash_timer = 0.0
        self.path = []
        self.path_calc_timer = 0.0
        
        if self.type == 'boss':
            self.speed = 0; self.radius = 50
            self.phase1_max_hp = 600; self.phase1_hp = 600
            self.phase2_max_hp = 400; self.phase2_hp = 400
            self.hp = self.phase1_hp; self.max_hp = self.phase1_max_hp
            self.boss_phase = 1; self.damage = 1; self.color = BOSS_COLOR; self.state = 'IDLE'
            self.dialogue_anim_active = False
            self.dialogue_anim_frame = 0.0
            self.dialogue_anim_cycle = 0
            self.dialogue_anim_speed = 8.0
            self.phase1_anim_frame = 0.0
            self.phase1_anim_speed = 8.0
            self.phase2_anim_frame = 0.0
            self.phase2_anim_cycle = 0
            self.phase2_anim_speed = 8.0
            self.death_fly_active = False
            self.death_fly_dir = pygame.math.Vector2(1, 0)
            self.death_fly_speed = 800
            self.death_fly_hit_wall = False
            self.death_fly_facing_right = True
            self.death_afterimages = []
            self.shockwave_after_dialogue_done = False
            self.phase1_transition_done = False
            self.spawn_pos = pygame.math.Vector2(x, y)
            self.next_attack_offset = random.uniform(0, math.pi / 4)
            self.attack_warning_duration = 0.5
            self._warning_ready = False
            self.attack_pattern = 0
            self.attack_order = [0, 1, 2, 0, 3, 4]
            self.attack_order_idx = 0
            self.spike_state = 'none'
            self.spike_timer = 0.0
            self.spike_radius = 140
            self.spike_positions_v = []
            self.spike_positions_h = []
            self.spike_damage_dealt = False
            self.spike_fall_progress = 0.0
            self.spike_fall_speed = 0.0
            self.spike_impact_timer = 0.0
            self.summon_used = False
            self.summon_shield = False
            self.summon_minion_ids = []
            self.summon_shield_timer = 0.0
            self.summon_shield_break = False
            self.bubble_state = 'none'
            self.bubble_wave = 0
            self.bubble_timer = 0.0
            self.bubble_angle_offset = 0.0
            self.aim_state = 'none'
            self.aim_timer = 0.0
            self.aim_wave = 0
            self.aim_base_angle = 0.0
            self.brush_state = 'none'
            self.brush_timer = 0.0
            self.brush_count = 0
            self.brush_side = 1
            self.brushes = []
            self.boss_chopstick_rain_timer = 0.0
            self.boss_chopstick_rain_interval = 0.25
            self.boss_spawn_chopstick = False
            self.boss_bandage_timer = 0.0
            self.boss_bandage_interval = 2.5
            self.boss_spawn_bandage = False
            self.boss_reverse_applied = False
            self.boss_laser_active = False
            self.boss_laser_angle = 0.0
            self.boss_laser_rotate_speed = 40.0
            self.boss_laser_dir = pygame.math.Vector2(1, 0)
            self.boss_laser_wall_hit = None
            self.boss_laser_frame_timer = 0.0
            self.boss_laser_frame_index = 0
            self.boss_laser_damage_cd = 0.0
            self.boss_laser_width = 16
        elif self.type == 'eraser':
            self.speed, self.radius, self.hp, self.max_hp = 250, 21, 100, 100 
            self.damage = 3; self.color = (139, 69, 19) 
            self.state = 'CHASE'; self.timer = 0.0; self.attack_target = None
        elif self.type == 'chalk':
            self.speed, self.radius, self.hp, self.max_hp = 200, 18, 100, 100 
            self.damage = 3; self.color = (240, 240, 240) 
            self.state = 'CHASE'; self.timer = 0.0; self.dash_dir = pygame.math.Vector2()
            self.dash_distance = 0.0
            self.dash_max_distance = 270
        
            # 👇 화장실 몬스터 3종 스탯 세팅
        elif self.type == 'soap':
            self.speed, self.radius, self.hp, self.max_hp = 180, 20, 100, 100 
            self.damage = 2; self.color = (150, 200, 255)
            self.state = 'RANDOM_WALK'
            self.puddle_timer = 0.2
            self.timer = random.uniform(2.5, 4.0)
            
            # 처음 태어날 때 멈춰있지 않도록 360도 중 무작위 방향 벡터 주입
            angle = random.uniform(0, 2 * math.pi)
            self.move_dir = pygame.math.Vector2(math.cos(angle), math.sin(angle))
            if self.move_dir.length() > 0:
                self.move_dir = self.move_dir.normalize()
                
            self.puddle_timer = 0.2  # 0.2초마다 액체를 떨어뜨릴 타이머
            
        elif self.type == 'toothpaste':
            self.speed, self.radius, self.hp, self.max_hp = 0, 22, 120, 120  
            self.damage = 2; self.color = (100, 255, 100) 
            self.state = 'IDLE'; self.timer = 2.0
        elif self.type == 'toothbrush':
            # 플레이어(350)보다 약간 느린 속도인 280으로 설정
            self.speed, self.radius, self.hp, self.max_hp = 280, 18, 80, 80 
            self.damage = 5; self.color = (255, 100, 100)
            self.state = 'FLEE'; self.flee_timer = 3.0
            
            self.dash_dir = pygame.math.Vector2()
            self.ortho_dir = pygame.math.Vector2()
            self.base_pos = pygame.math.Vector2()
            self.dash_distance = 0.0
            self.dash_max_distance = 3000     
            self.zigzag_width = 35
        elif self.type == 'pencil':
            self.speed, self.radius, self.hp, self.max_hp = 140, 21, 60, 60 
            self.damage = 2; self.color = (255, 215, 0) 
            self.state = 'CHASE'; self.timer = 0.0
            self.attack_cooldown = 1.5  # 필수 변수 복구

            # 👇 보건실 몬스터 3종 스탯 세팅
        elif self.type == 'bandage':
            # 붕대: 제자리 고정, 플레이어를 향해 투사체만 발사
            self.speed, self.radius, self.hp, self.max_hp = 0, 22, 120, 120
            self.damage = 3; self.color = (240, 240, 220)
            self.state = 'IDLE'; self.timer = 2.0  # 2초 후 첫 공격
        elif self.type == 'pill':
            # 알약: 느리지만 원거리 투사체 발사 (임시 - IDLE/FIRE)
            self.speed, self.radius, self.hp, self.max_hp = 100, 20, 80, 80
            self.damage = 4; self.color = (255, 100, 100)
            self.state = 'IDLE'; self.timer = 2.0
        elif self.type == 'syringe':
            # 주사기: 빠른 돌진형 (임시 - CHASE)
            self.speed, self.radius, self.hp, self.max_hp = 250, 18, 60, 60
            self.damage = 2; self.color = (100, 200, 255)
            self.state = 'CHASE'; self.timer = 0.0
            self.dash_dir = pygame.math.Vector2()
            self.dash_distance = 0.0
            self.dash_max_distance = 350  # 시각적 표시 범위에 맞춤

            # 👇 알약 보스 & 기믹 알약 스탯 세팅
        elif self.type == 'pill_boss':
            # 알약 보스: 맵 중앙에 고정, 주변 몬스터(bandage, syringe)가 다 죽을 때까지 무적
            self.speed, self.radius, self.hp, self.max_hp = 0, 35, 200, 200  # radius 줄임
            self.damage = 1; self.color = (200, 50, 200)
            self.state = 'IDLE'; self.timer = 0.0
            self.bullet_timer = 5.0       # 첫 탄막 발사까지 5초 대기
            self.is_invincible = True     # 주변 bandage, syringe가 살아있으면 무적
            self.last_blue_index = -1     # 이전 공격에서 파란알약이 나온 위치 (다음 공격에서 제외)

            # 👇 체육관 몬스터 3종 스탯 세팅
        elif self.type == 'corn_cone':
            # 꼬깔콘: 스파이크 낙하 공격형 - PRECAST→RISE→HOVER→FALL→IMPACT→STUCK
            self.speed, self.radius, self.hp, self.max_hp = 150, 22, 200, 200
            self.damage = 5; self.color = (255, 160, 50)
            self.state = 'IDLE'; self.timer = 2.0
            self.attack_cooldown = 3.0
            self.visual_offset_y = 0.0       # Y축 시각 오프셋 (음수=위로)
            self.rise_speed = 0.0            # 상승 속도
            self.fall_speed = 0.0            # 낙하 속도
            self.target_landing_pos = None   # 낙하 목표 위치
            self.spike_radius = 140          # 스파이크 공격 범위 (넓음)
            self.anim_frame = 0.0            # 애니메이션 프레임 누적
            self.hover_timer = 0.0           # 예고 범위 타이머
            self.hover_duration = 1.5        # 예고 범위 지속시간
            self.impact_timer = 0.0          # 폭발 상태 타이머
            self.stuck_timer = 0.0           # 처박힘 상태 타이머
            self.shake_offset = 0.0          # 흔들림 오프셋
            
        elif self.type == 'soccer_ball':
            # 축구공: 조준→스핀→돌진→도탄(3번)→기절(파훼 타이밍)
            self.speed, self.radius, self.hp, self.max_hp = 0, 30, 100, 100
            self.damage = 4; self.color = (50, 50, 50)
            self.state = 'IDLE'; self.timer = 2.0
            self.aim_dir = pygame.math.Vector2(1, 0)  # 조준 방향
            self.dash_dir = pygame.math.Vector2()       # 돌진 방향
            self.dash_speed = 1200                       # 돌진 속도 (매우 빠름)
            self.bounce_count = 0                        # 도탄 횟수
            self.max_bounces = 5                         # 최대 도탄 후 기절
            self.charge_time = 2.5                       # PRECAST(스핀) 지속시간
            self.spin_frame = 0.0                        # 애니메이션 프레임 누적
            self.stun_time = 7.5                         # 기절 지속시간
            self.stun_flash_timer = 0.0                  # 기절 진입 시 폭발 이펙트 타이머
            self.dash_ready_timer = 0.0                  # 돌진 직전 멈춤 시간
            self.warning_range = 800                     # 예고 범위 (벽까지 거리로 갱신)
            
        elif self.type == 'badminton_racket':
            # 배드민턴채: 원거리 공 발사형 - 이동하면서 조준→스윙→공 발사→공몬스터 변신
            self.speed, self.radius, self.hp, self.max_hp = 120, 24, 90, 90
            self.damage = 3; self.color = (100, 200, 100)
            self.state = 'IDLE'; self.timer = 2.0  # 2초 후 첫 조준
            self.swing_speed = 14.0  # 스윙 애니메이션 속도
            self.aim_dir = pygame.math.Vector2(1, 0)  # 조준 방향
            self.shuttle_range = 700  # 공 최대 사거리 (증가)
            self.attack_cooldown = 3.0  # 공격 쿨타임
            self.has_active_shuttle = False  # 현재 날아가는 공이 있는지

        elif self.type == 'badminton_shuttle':
            # 배드민턴공(공몬스터): 몸통박치기 추적형
            self.speed, self.radius, self.hp, self.max_hp = 250, 35, 30, 30
            self.damage = 1; self.color = (200, 200, 255)
            self.state = 'CHASE'; self.timer = 0.0

        elif self.type == 'food_tray':
            self.speed, self.radius, self.hp, self.max_hp = 0, 24, 120, 120
            self.damage = 3; self.color = (180, 140, 100)
            self.state = 'IDLE'; self.timer = 2.0
            self.has_active_boomerang = False
            self._boomerang_launched = False
            self.wash_timer = 0.0
            self.wash_duration = 5.0
        elif self.type == 'steel_scrubber':
            self.speed, self.radius, self.hp, self.max_hp = 0, 28, 80, 80
            self.damage = 3; self.color = (160, 160, 170)
            self.state = 'IDLE'; self.timer = 2.0
            self.anim_frame = 0.0
            self.scatter_timer = 0.0
            self.scatter_interval = 0.15
        elif self.type == 'spoon_chopsticks':
            self.speed, self.radius, self.hp, self.max_hp = 380, 26, 100, 100
            self.damage = 5; self.color = (200, 200, 210)
            self.state = 'CHASE'; self.timer = 0.0
            self.chase_speed = 380; self.flee_speed = 175
            self.slam_radius = 120
            self.slam_offset = 0
            self.anim_frame = 0.0
            self.shake_duration = 5.0
            self.chopstick_timer = 0.0
            self.chopstick_interval = 0.3
            self.trigger_shake = False
            self.trigger_slam_particles = False
            self.spawn_chopstick = False

        elif self.type == 'keyboard':
            self.speed, self.radius, self.hp, self.max_hp = 0, 20, 100, 100
            self.damage = 3; self.color = (60, 60, 70)
            self.state = 'IDLE'; self.timer = 2.0
            self.word_pool = ['과제','영원히','독점욕','사랑해','교수님','나만봐','독점키스','너의전부','절대감금','너를원해','영원소유','줄여주세요','숨통을조여','날위해죽어','피묻은사랑','너는내꺼야']
            self.words_to_type = []
            self.current_word_idx = 0
            self.typed_chars = 0
            self.char_timer = 0.0
            self.char_speed = 0.3
            self.max_attacks = 3
            self.active_word_len = 0
        elif self.type == 'router':
            self.speed, self.radius, self.hp, self.max_hp = 0, 22, 120, 120
            self.damage = 2; self.color = (100, 100, 200)
            self.state = 'IDLE'; self.timer = 2.0
            self.attack_cooldown = 3.0
            self.trigger_glitch = False
        elif self.type == 'computer_mouse':
            self.speed, self.radius, self.hp, self.max_hp = 150, 18, 80, 80
            self.damage = 4; self.color = (180, 180, 180)
            self.state = 'PATROL'; self.timer = 0.0
            self.patrol_index = 0
            self.wall_margin = TILE_SIZE * 2
            self.facing_angle = 0.0
            self.laser_dir = pygame.math.Vector2(0, -1)
            self.laser_angle_deg = 0.0
            self.laser_rotate_speed = 20.0
            self.laser_hold_timer = 0.0
            self.laser_initial_angle_deg = 0.0
            self.mouse_direction = 1
            self.laser_active = False
            self.laser_frame_timer = 0.0
            self.laser_frame_index = 0
            self.laser_wall_hit = None
            self.laser_width = 16
            self.laser_damage_cd = 0.0
            self.room_w = 0
            self.room_h = 0
            self._mouse_initialized = False

        elif self.type == 'mine_book':
            self.speed, self.radius, self.hp, self.max_hp = 170, 18, 100, 100
            self.damage = 5; self.color = (200, 80, 80)
            self.state = 'RANDOM_WALK'; self.timer = 10.0
            angle = random.uniform(0, 2 * math.pi)
            self.move_dir = pygame.math.Vector2(math.cos(angle), math.sin(angle))
            if self.move_dir.length() > 0:
                self.move_dir = self.move_dir.normalize()
            self.mine_place_timer = 0.0
            self.mine_retry = False
            self.mine_pre_place = False
        elif self.type == 'gravity_book':
            self.speed, self.radius, self.hp, self.max_hp = 0, 22, 120, 120
            self.damage = 1; self.color = (100, 80, 200)
            self.state = 'IDLE'; self.timer = 1.0
            self.anim_frame = 0.0
            self.float_timer = 0.0
        elif self.type == 'forbidden_book':
            self.speed, self.radius, self.hp, self.max_hp = 0, 22, 100, 100
            self.damage = 1; self.color = (180, 50, 180)
            self.state = 'IDLE'; self.timer = 1.0
            self.is_real = False
            self.float_timer = 0.0
            self.anim_frame = 0.0
        elif self.type == 'gamble_book':
            self.speed, self.radius, self.hp, self.max_hp = 175, 20, 80, 80
            self.damage = random.randint(1, 6); self.color = (220, 180, 50)
            self.state = 'CHASE'; self.timer = 3.0
            self.dice_throw_range = 400
            self.dice_bullets = []
            self.mini_dices = []
            self.room_w = 0; self.room_h = 0
            self.spin_angle = 0.0

        else:
            self.speed, self.radius, self.hp, self.max_hp = 200, 14, 100, 100
            self.damage = 1            # 👈 누락된 데미지 속성 추가
            self.state = 'CHASE'       # 👈 누락된 상태 속성 추가
            self.color = (255, 60, 60) # 👈 누락된 색상 속성 추가

        diff = DIFF[current_difficulty]
        if diff['hp_mult'] != 1.0:
            self.hp = int(self.hp * diff['hp_mult'])
            self.max_hp = int(self.max_hp * diff['hp_mult'])
            if self.type == 'boss':
                self.phase1_hp = int(self.phase1_hp * diff['hp_mult'])
                self.phase1_max_hp = int(self.phase1_max_hp * diff['hp_mult'])
                self.phase2_hp = int(self.phase2_hp * diff['hp_mult'])
                self.phase2_max_hp = int(self.phase2_max_hp * diff['hp_mult'])
        if self.type == 'boss':
            self.attack_warning_duration = 0.5 * diff['warn_mult']

    def get_path(self, target_pos, tile_map):
        start_c, start_r = int(self.pos.x // TILE_SIZE), int(self.pos.y // TILE_SIZE)
        tgt_c, tgt_r = int(target_pos.x // TILE_SIZE), int(target_pos.y // TILE_SIZE)
        if start_c == tgt_c and start_r == tgt_r: return []
        open_set = []; heapq.heappush(open_set, (0, start_c, start_r))
        came_from = {}; g_score = {(start_c, start_r): 0}; search_limit = 300 
        while open_set and search_limit > 0:
            search_limit -= 1; _, curr_c, curr_r = heapq.heappop(open_set)
            if curr_c == tgt_c and curr_r == tgt_r:
                path = []
                while (curr_c, curr_r) in came_from: path.append((curr_c, curr_r)); curr_c, curr_r = came_from[(curr_c, curr_r)]
                path.reverse(); return path
            for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
                nc, nr = curr_c + dc, curr_r + dr
                if 0 <= nr < len(tile_map) and 0 <= nc < len(tile_map[0]):
                    if tile_map[nr][nc] in [1, 2, 3]: continue
                    if dc != 0 and dr != 0:
                        if tile_map[curr_r][nc] in [1, 2, 3] or tile_map[nr][curr_c] in [1, 2, 3]: continue
                    tentative_g = g_score[(curr_c, curr_r)] + (1.414 if dc != 0 and dr != 0 else 1)
                    if (nc, nr) not in g_score or tentative_g < g_score[(nc, nr)]:
                        came_from[(nc, nr)] = (curr_c, curr_r); g_score[(nc, nr)] = tentative_g
                        f_score = tentative_g + (abs(nc - tgt_c) + abs(nr - tgt_r))
                        heapq.heappush(open_set, (f_score, nc, nr))
        return []

    def update(self, dt, target_pos, tile_map, enemy_bullets=None, player=None, damage_texts=None, particles=None, puddles=None, enemies_list=None, spawners_list=None):
        if self.flash_timer > 0: self.flash_timer -= dt
        
        if self.type == 'soap':
            # 1. 탱탱볼 같은 반사가 아닌, 일정 시간마다 자기 마음대로 랜덤하게 방향을 꺾으며 계속 직진함
            self.timer -= dt
            if self.timer <= 0:
                self.timer = random.uniform(0.4, 1.2)  # 0.4 ~ 1.2초마다 방향 바꿈
                angle = random.uniform(0, 2 * math.pi)
                self.move_dir = pygame.math.Vector2(math.cos(angle), math.sin(angle)).normalize()
            
            # 이동 속도 연산
            move_x = self.move_dir.x * self.speed * dt
            move_y = self.move_dir.y * self.speed * dt
            
            can_move_x, can_move_y = True, True
            if tile_map:
                c_x, r_cur = int((self.pos.x + move_x + (self.radius if move_x > 0 else -self.radius)) // TILE_SIZE), int(self.pos.y // TILE_SIZE)
                if move_x != 0:
                    if 0 <= c_x < len(tile_map[0]) and 0 <= r_cur < len(tile_map):
                        if tile_map[r_cur][c_x] in [1, 2, 3]: can_move_x = False
                    else:
                        can_move_x = False  # 맵 바깥 범위는 무조건 벽으로 처리
                
                c_y, c_cur = int((self.pos.y + move_y + (self.radius if move_y > 0 else -self.radius)) // TILE_SIZE), int(self.pos.x // TILE_SIZE)
                if move_y != 0:
                    if 0 <= c_y < len(tile_map) and 0 <= c_cur < len(tile_map[0]):
                        if tile_map[c_y][c_cur] in [1, 2, 3]: can_move_y = False
                    else:
                        can_move_y = False  # 맵 바깥 범위는 무조건 벽으로 처리
            
            # 2. 벽에 닿았을 때 정직하게 튕기지 않고, 무작위로 빠져나갈 새로운 방향을 바로 찾아냄
            if can_move_x: 
                self.pos.x += move_x
            else: 
                self.move_dir.x *= -1
                # 거울 반사가 아니라, 반대쪽으로 무작위 각도를 비틀어서 생물처럼 빠져나옴
                new_angle = math.atan2(self.move_dir.y, self.move_dir.x) + random.uniform(-0.6, 0.6)
                self.move_dir = pygame.math.Vector2(math.cos(new_angle), math.sin(new_angle)).normalize()
                self.pos.x += self.move_dir.x * self.speed * dt
                self.timer = random.uniform(0.4, 1.2) # 벽에 부딪히면 타이머 리셋
            
            if can_move_y: 
                self.pos.y += move_y
            else: 
                self.move_dir.y *= -1
                new_angle = math.atan2(self.move_dir.y, self.move_dir.x) + random.uniform(-0.6, 0.6)
                self.move_dir = pygame.math.Vector2(math.cos(new_angle), math.sin(new_angle)).normalize()
                self.pos.y += self.move_dir.y * self.speed * dt
                self.timer = random.uniform(0.4, 1.2)

            # 3. 바닥에 끈적한 액체 생성
            if hasattr(self, 'puddle_timer'):
                self.puddle_timer -= dt
                if self.puddle_timer <= 0:
                    self.puddle_timer = 0.2  
                    if puddles is not None:
                        puddles.append(SoapPuddle(self.pos.x, self.pos.y))
            
            # 4. 플레이어 충돌 처리
            if player and self.pos.distance_to(player.pos) < self.radius + player.radius:
                if not (player.is_dashing or player.inv_timer > 0):
                    res = player.take_damage(self.damage)
                    if res == "BLOCKED" and damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                    elif res == True:
                        if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                        for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))

        elif self.type == 'toothpaste':
            self.timer -= dt
            
            if self.state == 'IDLE':
                if self.timer <= 0:
                    self.state = 'PRECAST'; self.timer = 0.7 
                    
            elif self.state == 'PRECAST':
                if self.timer <= 0:
                    # 👈 tile_map 체크 로직 강화
                    if enemy_bullets is not None and tile_map is not None and len(tile_map) > 0:
                        room_w = len(tile_map[0]) * TILE_SIZE
                        room_h = len(tile_map) * TILE_SIZE
                        enemy_bullets.append(FloatingBullet(self.pos.x, self.pos.y, room_w, room_h, damage=self.damage))
                    
                    self.state = 'FIRE'; self.timer = 0.3
                    
            elif self.state == 'FIRE':
                if self.timer <= 0:
                    self.state = 'IDLE'
                    self.timer = 2.0    

            # 플레이어가 와서 닿으면 데미지를 주는 로직 (그대로 유지)
            if player and self.pos.distance_to(player.pos) < self.radius + player.radius:
                if not (player.is_dashing or player.inv_timer > 0):
                    res = player.take_damage(self.damage)
                    if res == "BLOCKED" and damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                    elif res == True:
                        if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                        for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))

        elif self.type == 'eraser':
            if self.state == 'CHASE':
                if self.pos.distance_to(target_pos) < 90:
                    self.state = 'PRECAST'; self.timer = 0.7; self.attack_target = target_pos.copy()
                else: self.move_towards(dt, target_pos, tile_map)
            elif self.state == 'PRECAST':
                self.timer -= dt
                if self.timer <= 0:
                    self.pos = self.attack_target.copy()
                    if player and self.pos.distance_to(player.pos) < 96: 
                        if player.is_dashing or player.inv_timer > 0: pass
                        else:
                            res = player.take_damage(self.damage)
                            if res == "BLOCKED":
                                if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                            elif res == True:
                                if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                                for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
                    self.state = 'COOLDOWN'; self.timer = 1.5 
            elif self.state == 'COOLDOWN':
                self.timer -= dt
                if self.timer <= 0: self.state = 'CHASE'

        elif self.type == 'chalk':
            if self.state == 'CHASE':
                if self.pos.distance_to(target_pos) < 270:
                    self.state = 'PRECAST'; self.timer = 0.5
                    dir_vec = target_pos - self.pos
                    self.dash_dir = dir_vec.normalize() if dir_vec.length() > 0 else pygame.math.Vector2(1,0)
                else: 
                    self.move_towards(dt, target_pos, tile_map)
                    
            elif self.state == 'PRECAST':
                self.timer -= dt
                if self.timer <= 0: 
                    self.state = 'DASH'
                    self.dash_distance = 0.0  # 돌진 시작 시 거리 리셋
                    
            elif self.state == 'DASH':
                dash_speed = 960
                move_step = self.dash_dir * dash_speed * dt
                self.pos += move_step
                self.dash_distance += dash_speed * dt  # 돌진한 거리 누적
                
                # 플레이어 충돌(데미지) 검사
                if player and self.pos.distance_to(player.pos) < self.radius + player.radius + 15: 
                    if not (player.is_dashing or player.inv_timer > 0):
                        res = player.take_damage(self.damage)
                        if res == "BLOCKED" and damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                        elif res == True:
                            if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                            for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
                
                # 벽에 닿았는지 타일맵 검사
                hit_wall = False
                if tile_map:
                    c, r = int(self.pos.x//TILE_SIZE), int(self.pos.y//TILE_SIZE)
                    if 0 <= r < len(tile_map) and 0 <= c < len(tile_map[0]) and tile_map[r][c] in [1, 2, 3]: 
                        hit_wall = True
                
                # 🎯 [렉 해결 핵심] 돌진 거리를 다 채웠거나 벽에 박으면 쿨타임(COOLDOWN) 상태로 확실하게 탈출!
                if self.dash_distance >= self.dash_max_distance or hit_wall: 
                    self.state = 'COOLDOWN'
                    self.timer = 1.5 
                    
            elif self.state == 'COOLDOWN':
                self.timer -= dt
                if self.timer <= 0: 
                    self.state = 'CHASE'

        elif self.type == 'pencil':
            if self.state == 'CHASE':
                dist = self.pos.distance_to(target_pos)
                if dist < 225: 
                    retreat_pos = self.pos + (self.pos - target_pos).normalize() * 100
                    self.move_towards(dt, retreat_pos, tile_map)
                elif dist > 375: 
                    self.move_towards(dt, target_pos, tile_map)
                
                self.attack_cooldown -= dt
                if self.attack_cooldown <= 0: 
                    self.state = 'PRECAST'; self.timer = 0.5 # 경고 시간

            elif self.state == 'PRECAST':
                self.timer -= dt
                if self.timer <= 0:
                    self.state = 'FIRE' # 👈 발사 상태 추가
                    
            elif self.state == 'FIRE': # 👈 여기서 딱 한 번만 발사
                if enemy_bullets is not None:
                    dir_vec = target_pos - self.pos
                    base_angle = math.atan2(dir_vec.y, dir_vec.x)
                    
                    # 원하는 각도로 단 3발만 발사
                    for offset in [-0.45, 0, 0.45]:
                        a = base_angle + offset
                        eb = EnemyBullet(self.pos.x, self.pos.y, self.pos.x + math.cos(a)*10, self.pos.y + math.sin(a)*10, damage=self.damage)
                        eb.is_pencil_tip = True
                        eb._prepare_mask()
                        enemy_bullets.append(eb)
                
                self.state = 'CHASE'; self.attack_cooldown = 1.5 # 👈 발사 후 다시 CHASE로 돌아가며 쿨타임 시작
                    
        # (Enemy 클래스의 update 내부, elif self.type == 'toothbrush': 부분을 찾아 아래 코드로 교체해주세요)
        elif self.type == 'toothbrush':
            if self.state == 'FLEE':
                # 플레이어의 반대 방향으로 도망치기
                if self.pos.distance_to(target_pos) > 0:
                    retreat_pos = self.pos + (self.pos - target_pos).normalize() * 100
                    self.move_towards(dt, retreat_pos, tile_map)
                
                # 5초 타이머 감소
                self.flee_timer -= dt
                if self.flee_timer <= 0:
                    self.state = 'PRECAST'; self.timer = 0.8
                    dir_vec = target_pos - self.pos
                    self.dash_dir = dir_vec.normalize() if dir_vec.length() > 0 else pygame.math.Vector2(1,0)
                    self.ortho_dir = pygame.math.Vector2(-self.dash_dir.y, self.dash_dir.x)
                    
            elif self.state == 'PRECAST':
                self.timer -= dt
                if self.timer <= 0:
                    self.state = 'DASH'; self.dash_distance = 0.0
                    self.base_pos = self.pos.copy()
                    self.dash_timer = 0.0
                    
            elif self.state == 'DASH':
                self.dash_timer += dt  
                dash_speed = 700
                self.dash_distance += dash_speed * dt
                
                freq = 0.07 
                offset = math.sin(self.dash_distance * freq) * self.zigzag_width
                
                # 1. 캔슬이나 이동 불가 판정 없이 기준점(base_pos)을 무조건 앞으로 밀고 나갑니다.
                self.base_pos += self.dash_dir * dash_speed * dt
                
                # 2. 실제 위치는 기준점 + 지그재그 오프셋으로 바로 꽂아버립니다.
                self.pos = self.base_pos + self.ortho_dir * offset
                
                margin = TILE_SIZE + self.radius
                hit_wall = False
                
                # 3. 맵 바깥으로 나가지 않게 좌표를 맵 테두리 안쪽으로 강제로 가둡니다.
                if tile_map:
                    room_w = len(tile_map[0]) * TILE_SIZE
                    room_h = len(tile_map) * TILE_SIZE
                    
                    self.pos.x = max(margin, min(room_w - margin, self.pos.x))
                    self.pos.y = max(margin, min(room_h - margin, self.pos.y))
                    
                    # 4. '지그재그'가 아닌 '돌진 방향의 기준점(base_pos)'이 벽에 닿았을 때만 종료 판정
                    if self.base_pos.x <= margin and self.dash_dir.x < 0: hit_wall = True
                    elif self.base_pos.x >= room_w - margin and self.dash_dir.x > 0: hit_wall = True
                    if self.base_pos.y <= margin and self.dash_dir.y < 0: hit_wall = True
                    elif self.base_pos.y >= room_h - margin and self.dash_dir.y > 0: hit_wall = True

                if player and self.pos.distance_to(player.pos) < self.radius + player.radius + 15: 
                    if not (player.is_dashing or player.inv_timer > 0):
                        res = player.take_damage(self.damage)
                        if res == "BLOCKED" and damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                        elif res == True:
                            if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                            for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
                
                if self.dash_distance >= self.dash_max_distance or (self.dash_timer > 0.5 and hit_wall):
                    self.state = 'FLEE'; self.flee_timer = 3.0

        # 👇 보건실 붕대 몬스터: 제자리에서 IDLE → PRECAST(반짝임) → 발사 → IDLE
        elif self.type == 'bandage':
            self.timer -= dt
            if self.state == 'IDLE':
                if self.timer <= 0:
                    self.state = 'PRECAST'; self.timer = 0.6  # 0.6초간 반짝임 경고
            elif self.state == 'PRECAST':
                if self.timer <= 0:
                    # 투사체 발사
                    if enemy_bullets is not None and player is not None:
                        eb = EnemyBullet(self.pos.x, self.pos.y, target_pos.x, target_pos.y, damage=1)
                        eb.is_bandage = True
                        eb.speed = int(300 * DIFF[current_difficulty]['proj_speed_mult'])
                        eb.radius = 20
                        enemy_bullets.append(eb)
                    self.state = 'IDLE'; self.timer = 3.0  # 3초 후 다시 공격

        elif self.type == 'pill':
            # 알약: 제자리에서 주기적으로 투사체 발사
            self.timer -= dt
            if self.state == 'IDLE':
                if self.timer <= 0:
                    self.state = 'PRECAST'; self.timer = 0.5
            elif self.state == 'PRECAST':
                if self.timer <= 0:
                    if enemy_bullets is not None and tile_map is not None and len(tile_map) > 0:
                        room_w = len(tile_map[0]) * TILE_SIZE
                        room_h = len(tile_map) * TILE_SIZE
                        # 3방향 투사체 발사
                        dir_vec = target_pos - self.pos
                        base_angle = math.atan2(dir_vec.y, dir_vec.x)
                        for offset in [-0.5, 0, 0.5]:
                            a = base_angle + offset
                            eb = EnemyBullet(self.pos.x, self.pos.y, self.pos.x + math.cos(a)*10, self.pos.y + math.sin(a)*10, damage=self.damage)
                            eb._prepare_mask()
                            enemy_bullets.append(eb)
                    self.state = 'FIRE'; self.timer = 0.3
            elif self.state == 'FIRE':
                if self.timer <= 0:
                    self.state = 'IDLE'; self.timer = 2.5

            # 플레이어 접촉 데미지
            if player and self.pos.distance_to(player.pos) < self.radius + player.radius:
                if not (player.is_dashing or player.inv_timer > 0):
                    res = player.take_damage(self.damage)
                    if res == "BLOCKED" and damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                    elif res == True:
                        if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                        for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))

        elif self.type == 'syringe':
            # 주사기: 제자리 대기 → 플레이어에게 돌진 (이동 안 함)
            if self.state == 'CHASE':
                # 맵 끝까지 인식 범위 설정
                if tile_map:
                    room_w_local = len(tile_map[0]) * TILE_SIZE
                    room_h_local = len(tile_map) * TILE_SIZE
                    detect_range = math.sqrt(room_w_local ** 2 + room_h_local ** 2)
                    self.dash_max_distance = detect_range  # PRECAST 표시용으로 미리 설정
                else:
                    detect_range = 1000
                if self.pos.distance_to(target_pos) < detect_range:
                    self.state = 'PRECAST'; self.timer = 0.5
                    dir_vec = target_pos - self.pos
                    self.dash_dir = dir_vec.normalize() if dir_vec.length() > 0 else pygame.math.Vector2(1, 0)
            elif self.state == 'PRECAST':
                self.timer -= dt
                if self.timer <= 0:
                    self.state = 'DASH'; self.dash_distance = 0.0
                    # 맵 끝에서 끝까지 돌진 거리 설정
                    if tile_map:
                        room_w_local = len(tile_map[0]) * TILE_SIZE
                        room_h_local = len(tile_map) * TILE_SIZE
                        self.dash_max_distance = math.sqrt(room_w_local ** 2 + room_h_local ** 2)
            elif self.state == 'DASH':
                dash_speed = 1500
                move_step = self.dash_dir * dash_speed * dt
                self.pos += move_step
                self.dash_distance += dash_speed * dt

                # 플레이어 충돌 (돌진 중에도 데미지)
                if player and self.pos.distance_to(player.pos) < self.radius + player.radius + 15:
                    if not (player.is_dashing or player.inv_timer > 0):
                        res = player.take_damage(self.damage)
                        if res == "BLOCKED" and damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                        elif res == True:
                            if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                            for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))

                # 맵 경계 밖으로 나가면 멈춤 (타일 벽은 관통)
                hit_wall = False
                if tile_map:
                    room_w = len(tile_map[0]) * TILE_SIZE
                    room_h = len(tile_map) * TILE_SIZE
                    margin = self.radius + 20  # 마진 증가
                    if self.pos.x < margin or self.pos.x > room_w - margin or self.pos.y < margin or self.pos.y > room_h - margin:
                        self.pos.x = max(margin, min(room_w - margin, self.pos.x))
                        self.pos.y = max(margin, min(room_h - margin, self.pos.y))
                        hit_wall = True

                if self.dash_distance >= self.dash_max_distance or hit_wall:
                    self.state = 'COOLDOWN'; self.timer = 1.0
            elif self.state == 'COOLDOWN':
                self.timer -= dt
                if self.timer <= 0: self.state = 'CHASE'
        
        # 👇 체육관 몬스터 3종 AI
        elif self.type == 'corn_cone':
            # 꼬깔콘: IDLE → PRECAST(2초, _1~_4) → RISE(_5~_6, 위로 올라감) →
            #          HOVER(예고범위) → FALL(_7~_10, 내려옴) → IMPACT(_11, 폭발) → STUCK(_12, 5초 흔들)
            self.anim_frame += dt
            
            if self.state == 'IDLE':
                self.attack_cooldown -= dt
                if self.attack_cooldown <= 0:
                    self.state = 'PRECAST'
                    self.timer = 2.0
                    self.anim_frame = 0.0
            
            elif self.state == 'PRECAST':
                # 공격 대기: 테두리 빛남, _1~_4 순차 (각 0.5초)
                self.timer -= dt
                if self.timer <= 0:
                    self.state = 'RISE'
                    self.rise_speed = 300.0
                    self.anim_frame = 0.0
                    self.visual_offset_y = 0.0
            
            elif self.state == 'RISE':
                # Y축으로 위로 올라감, 속도 점점 빨라짐
                self.rise_speed += 600 * dt
                self.visual_offset_y -= self.rise_speed * dt
                # _5: 0.5초, _6: 그 후 화면 밖까지
                if self.visual_offset_y < -700:
                    self.state = 'HOVER'
                    self.hover_timer = 0.0
                    self.target_landing_pos = target_pos.copy() if target_pos else self.pos.copy()
                    self.anim_frame = 0.0
            
            elif self.state == 'HOVER':
                # 화면 밖에서 플레이어 위치 추적 + 예고 범위
                # 마지막 0.5초는 위치 고정 (플레이어 회피 기회)
                self.hover_timer += dt
                track_cutoff = self.hover_duration - 0.5
                if target_pos and self.hover_timer < track_cutoff:
                    self.target_landing_pos = target_pos.copy()
                if self.hover_timer >= self.hover_duration:
                    self.state = 'FALL'
                    self.fall_speed = 200.0
                    self.visual_offset_y = -700
                    self.anim_frame = 0.0
                    if self.target_landing_pos:
                        self.pos.x = self.target_landing_pos.x
                        self.pos.y = self.target_landing_pos.y
            
            elif self.state == 'FALL':
                # Y축으로 내려옴, 속도 점점 빨라짐
                self.fall_speed += 1500 * dt
                self.visual_offset_y += self.fall_speed * dt
                if self.visual_offset_y >= 0:
                    self.visual_offset_y = 0
                    self.state = 'IMPACT'
                    self.impact_timer = 0.6
                    self.anim_frame = 0.0
                    # 스파이크 데미지 (넓은 범위)
                    if player and self.pos.distance_to(player.pos) < self.spike_radius:
                        if not (player.is_dashing or player.inv_timer > 0):
                            res = player.take_damage(self.damage)
                            if res == "BLOCKED" and damage_texts is not None:
                                damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                            elif res == True:
                                if damage_texts is not None:
                                    damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                                for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
                    if particles is not None:
                        for _ in range(30): particles.append(ExplosionParticle(self.pos.x, self.pos.y))
            
            elif self.state == 'IMPACT':
                # 폭발 상태: 짧은 시간
                self.impact_timer -= dt
                if self.impact_timer <= 0:
                    self.state = 'STUCK'
                    self.stuck_timer = 5.0
                    self.anim_frame = 0.0
            
            elif self.state == 'STUCK':
                # 5초간 흔들흔들 (파훼 타이밍 - 무방비)
                self.stuck_timer -= dt
                self.shake_offset = math.sin(pygame.time.get_ticks() * 0.03) * 6
                if self.stuck_timer <= 0:
                    self.state = 'IDLE'
                    self.attack_cooldown = 3.0
                    self.anim_frame = 0.0
                    self.shake_offset = 0
                    self.visual_offset_y = 0
                    
            # 접촉 데미지 (IDLE/PRECAST 상태에서만, 공중/박힘 상태에서는 없음)
            if self.state in ('IDLE', 'PRECAST') and player and self.pos.distance_to(player.pos) < self.radius + player.radius:
                if not (player.is_dashing or player.inv_timer > 0):
                    res = player.take_damage(self.damage)
                    if res == "BLOCKED" and damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                    elif res == True:
                        if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                        for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
                        
        elif self.type == 'soccer_ball':
            # 축구공: IDLE → PRECAST(스핀/조준, 2.5초) → DASH(돌진+도탄) → STUNNED(기절, 9초) → IDLE
            self.timer -= dt
            
            if self.state == 'IDLE':
                # 기본 상태: 대기 후 PRECAST 진입
                if self.timer <= 0:
                    self.state = 'PRECAST'
                    self.timer = self.charge_time  # 2.5초 스핀
                    self.spin_frame = 0.0
            
            elif self.state == 'PRECAST':
                # 스핀 애니메이션 진행 + 실시간 플레이어 조준
                self.spin_frame += dt
                if target_pos:
                    dir_vec = target_pos - self.pos
                    if dir_vec.length() > 0:
                        self.aim_dir = dir_vec.normalize()
                # 예고 범위: 조준 방향으로 벽까지 레이캐스팅
                if tile_map:
                    self.warning_range = 0
                    step = 4
                    max_range = 2000
                    for d in range(0, max_range, step):
                        test_x = self.pos.x + self.aim_dir.x * d
                        test_y = self.pos.y + self.aim_dir.y * d
                        c, r = int(test_x // TILE_SIZE), int(test_y // TILE_SIZE)
                        if 0 <= r < len(tile_map) and 0 <= c < len(tile_map[0]):
                            if tile_map[r][c] in [1, 2, 3]:
                                self.warning_range = d
                                break
                        else:
                            self.warning_range = d
                            break
                    else:
                        self.warning_range = max_range
                else:
                    self.warning_range = 800
                if self.timer <= 0:
                    # 돌진 시작 (잠시 멈춤 후 출발)
                    self.state = 'DASH'
                    self.dash_dir = self.aim_dir.copy()
                    self.bounce_count = 0
                    self.dash_ready_timer = 0.3  # 축구공_7에서 0.3초 멈춤
            
            elif self.state == 'DASH':
                # 돌진 직전 잠시 멈춤
                if self.dash_ready_timer > 0:
                    self.dash_ready_timer -= dt
                else:
                    # 매우 빠른 속도로 직선 돌진
                    old_pos = self.pos.copy()
                    self.pos += self.dash_dir * self.dash_speed * dt
                    
                    # 플레이어 충돌 데미지
                    if player and self.pos.distance_to(player.pos) < self.radius + player.radius:
                        if not (player.is_dashing or player.inv_timer > 0):
                            res = player.take_damage(self.damage)
                            if res == "BLOCKED" and damage_texts is not None:
                                damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                            elif res == True:
                                if damage_texts is not None:
                                    damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                                for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
                    
                    # 벽 충돌 체크
                    hit_wall = False
                    if tile_map:
                        c, r = int(self.pos.x // TILE_SIZE), int(self.pos.y // TILE_SIZE)
                        if 0 <= r < len(tile_map) and 0 <= c < len(tile_map[0]) and tile_map[r][c] in [1, 2, 3]:
                            hit_wall = True
                    
                    if hit_wall:
                        self.bounce_count += 1
                        
                        if self.bounce_count >= self.max_bounces:
                            # 3번 도탄 후 기절 → 파훼 타이밍
                            self.pos = old_pos
                            self.state = 'STUNNED'
                            self.timer = self.stun_time
                            self.spin_frame = 0.0
                            self.stun_flash_timer = 0.5
                            # 터지는 이펙트
                            if particles is not None:
                                for _ in range(30): particles.append(Particle(self.pos.x, self.pos.y))
                        else:
                            # 도탄 반사: X/Y 각각 테스트
                            if tile_map:
                                # X 이동만 테스트
                                x_test = pygame.math.Vector2(old_pos.x + self.dash_dir.x * self.dash_speed * dt, old_pos.y)
                                xc, xr = int(x_test.x // TILE_SIZE), int(x_test.y // TILE_SIZE)
                                x_wall = (0 <= xr < len(tile_map) and 0 <= xc < len(tile_map[0]) and tile_map[xr][xc] in [1, 2, 3])
                                # Y 이동만 테스트
                                y_test = pygame.math.Vector2(old_pos.x, old_pos.y + self.dash_dir.y * self.dash_speed * dt)
                                yc, yr = int(y_test.x // TILE_SIZE), int(y_test.y // TILE_SIZE)
                                y_wall = (0 <= yr < len(tile_map) and 0 <= yc < len(tile_map[0]) and tile_map[yr][yc] in [1, 2, 3])
                                
                                if x_wall: self.dash_dir.x = -self.dash_dir.x
                                if y_wall: self.dash_dir.y = -self.dash_dir.y
                                if not x_wall and not y_wall:
                                    self.dash_dir.x = -self.dash_dir.x
                                    self.dash_dir.y = -self.dash_dir.y
                            
                            self.pos = old_pos  # 이전 위치로 복귀
            
            elif self.state == 'STUNNED':
                # 기절 상태: 9초간 이동/공격 불가 (파훼 타이밍)
                self.spin_frame += dt
                if self.stun_flash_timer > 0:
                    self.stun_flash_timer -= dt
                if self.timer <= 0:
                    self.state = 'IDLE'
                    self.timer = 2.0
                        
        elif self.type == 'badminton_racket':
            # 배드민턴채: IDLE(이동) → AIM(조준, 예고범위) → SWING(스윙 애니메이션) → FIRE(공 발사) → COOLDOWN
            self.attack_cooldown -= dt
            
            if self.state == 'IDLE':
                # IDLE 중에는 플레이어 반대 방향으로 천천히 이동 (거리 유지)
                if target_pos.distance_to(self.pos) < 300:
                    retreat_pos = self.pos + (self.pos - target_pos).normalize() * 100
                    self.move_towards(dt, retreat_pos, tile_map)
                elif target_pos.distance_to(self.pos) > 500:
                    self.move_towards(dt, target_pos, tile_map)
                self.attack_cooldown -= dt
                if self.attack_cooldown <= 0:
                    self.state = 'AIM'; self.timer = 1.5  # 1.5초간 조준
                    dir_vec = target_pos - self.pos
                    self.aim_dir = dir_vec.normalize() if dir_vec.length() > 0 else pygame.math.Vector2(1, 0)
                    
            elif self.state == 'AIM':
                # 조준 중: 플레이어 방향 추적 (이동은 하지 않음)
                dir_vec = target_pos - self.pos
                if dir_vec.length() > 0:
                    self.aim_dir = dir_vec.normalize()
                self.timer -= dt
                if self.timer <= 0:
                    self.state = 'SWING'; self.swing_frame = 0.0
                    
            elif self.state == 'SWING':
                # 스윙 애니메이션: 배드민턴채_2~7 빠르게 재생
                self.swing_frame += self.swing_speed * dt
                if self.swing_frame >= 6.0:  # 프레임 2~7 (6프레임)
                    self.state = 'FIRE'
                    # 공 발사
                    if enemy_bullets is not None:
                        target_x = self.pos.x + self.aim_dir.x * 10
                        target_y = self.pos.y + self.aim_dir.y * 10
                        shuttle_dmg = 1 if current_difficulty == 'easy' else self.damage
                        eb = EnemyBullet(self.pos.x, self.pos.y, target_x, target_y, damage=shuttle_dmg)
                        eb.is_shuttle = True
                        eb.speed = int(650 * DIFF[current_difficulty]['proj_speed_mult'])
                        eb.radius = 35
                        eb.max_travel_distance = self.shuttle_range
                        eb.owner_racket = self
                        enemy_bullets.append(eb)
                        self.has_active_shuttle = True
                    self.state = 'COOLDOWN'; self.timer = 1.0
                    
            elif self.state == 'COOLDOWN':
                self.timer -= dt
                if self.timer <= 0:
                    self.state = 'IDLE'
                    self.attack_cooldown = 3.0
                    
            # 접촉 데미지
            if player and self.pos.distance_to(player.pos) < self.radius + player.radius:
                if not (player.is_dashing or player.inv_timer > 0):
                    res = player.take_damage(self.damage)
                    if res == "BLOCKED" and damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                    elif res == True:
                        if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                        for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
                        
        elif self.type == 'badminton_shuttle':
            # 배드민턴공(공몬스터): 플레이어에게 몸통박치기 추적
            self.move_towards(dt, target_pos, tile_map)
            # 접촉 데미지
            if player and self.pos.distance_to(player.pos) < self.radius + player.radius:
                if not (player.is_dashing or player.inv_timer > 0):
                    res = player.take_damage(self.damage)
                    if res == "BLOCKED" and damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                    elif res == True:
                        if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                        for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))

        elif self.type == 'food_tray':
            self.timer -= dt
            if self.state == 'IDLE':
                if self.timer <= 0:
                    self.state = 'PRECAST'; self.timer = 0.7
            elif self.state == 'PRECAST':
                if self.timer <= 0:
                    self.state = 'THROW'
                    self.has_active_boomerang = True
            elif self.state == 'THROW':
                if not self.has_active_boomerang:
                    self.state = 'WASHING'; self.wash_timer = self.wash_duration
            elif self.state == 'WASHING':
                self.wash_timer -= dt
                if self.wash_timer <= 0:
                    self.state = 'IDLE'; self.timer = 1.5

        elif self.type == 'steel_scrubber':
            self.timer -= dt
            if self.state == 'IDLE':
                if self.timer <= 0:
                    self.state = 'PRECAST'; self.timer = 0.7
            elif self.state == 'PRECAST':
                if self.timer <= 0:
                    self.state = 'SPIN'; self.anim_frame = 0.0; self.scatter_timer = 0.0
            elif self.state == 'SPIN':
                self.anim_frame += dt
                self.scatter_timer += dt
                if self.scatter_timer >= self.scatter_interval and enemy_bullets is not None:
                    self.scatter_timer = 0.0
                    for _ in range(3):
                        angle = random.uniform(0, 2 * math.pi)
                        speed_var = random.uniform(200, 450)
                        tx = self.pos.x + math.cos(angle) * 10
                        ty = self.pos.y + math.sin(angle) * 10
                        eb = EnemyBullet(self.pos.x, self.pos.y, tx, ty, damage=self.damage)
                        eb.is_wire_scraps = True
                        eb.speed = speed_var
                        eb.radius = 6
                        enemy_bullets.append(eb)
                if self.anim_frame >= 3.0:
                    self.state = 'RECOVER'; self.anim_frame = 0.0
            elif self.state == 'RECOVER':
                self.anim_frame += dt
                if self.anim_frame >= 4.5:
                    self.state = 'IDLE'; self.timer = 1.5

        elif self.type == 'spoon_chopsticks':
            if self.state == 'CHASE':
                self.speed = self.chase_speed
                self.move_towards(dt, target_pos, tile_map)
                if self.pos.distance_to(target_pos) < 80:
                    self.state = 'PRECAST'; self.timer = 0.3
            elif self.state == 'PRECAST':
                self.timer -= dt
                if self.timer <= 0:
                    self.state = 'SLAM'; self.anim_frame = 0.0
            elif self.state == 'SLAM':
                self.anim_frame += dt
                if self.anim_frame >= 0.5:
                    self.state = 'IMPACT'; self.anim_frame = 0.0
                    self.trigger_slam_particles = True
                    if player:
                        if self.pos.distance_to(player.pos) < self.slam_radius:
                            if not (player.is_dashing or player.inv_timer > 0):
                                res = player.take_damage(self.damage)
                                if res == "BLOCKED" and damage_texts is not None:
                                    damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                                elif res == True:
                                    if damage_texts is not None:
                                        damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                                    if particles is not None:
                                        for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
            elif self.state == 'IMPACT':
                self.anim_frame += dt
                if self.anim_frame >= 0.08:
                    self.state = 'IMPACT_HOLD'; self.anim_frame = 0.0
            elif self.state == 'IMPACT_HOLD':
                self.anim_frame += dt
                if self.anim_frame >= 0.15:
                    self.state = 'SHAKING'; self.anim_frame = 0.0
                    self.trigger_shake = True; self.chopstick_timer = 0.0
            elif self.state == 'SHAKING':
                self.anim_frame += dt
                self.speed = self.flee_speed
                if self.pos.distance_to(target_pos) > 0:
                    retreat_pos = self.pos + (self.pos - target_pos).normalize() * 100
                    self.move_towards(dt, retreat_pos, tile_map)
                self.chopstick_timer += dt
                if self.chopstick_timer >= self.chopstick_interval:
                    self.chopstick_timer = 0.0; self.spawn_chopstick = True
                if self.anim_frame >= self.shake_duration:
                    self.state = 'FLEE'; self.timer = 3.0
            elif self.state == 'FLEE':
                self.speed = self.flee_speed
                if self.pos.distance_to(target_pos) > 0:
                    retreat_pos = self.pos + (self.pos - target_pos).normalize() * 100
                    self.move_towards(dt, retreat_pos, tile_map)
                self.timer -= dt
                if self.timer <= 0:
                    self.state = 'CHASE'

        elif self.type == 'boss':
            if getattr(self, 'death_fly_active', False) and not getattr(self, 'death_fly_hit_wall', False):
                self.pos += self.death_fly_dir * self.death_fly_speed * dt
                return
            if getattr(self, 'death_fly_hit_wall', False):
                return
            if hasattr(self, 'spawn_pos'):
                self.pos.x = self.spawn_pos.x
                self.pos.y = self.spawn_pos.y
            if not hasattr(self, 'attack_timer'):
                self.attack_timer = 1.0
            if not getattr(self, 'dialogue_anim_active', False):
                if self.boss_phase == 2 and len(IMAGES.get('boss_phase2', [])) >= 12:
                    self.phase2_anim_frame += self.phase2_anim_speed * dt
                    max_f = 12 if self.phase2_anim_cycle == 0 else 9
                    if int(self.phase2_anim_frame) >= max_f:
                        self.phase2_anim_frame = 0.0
                        if self.phase2_anim_cycle == 0:
                            self.phase2_anim_cycle = 1
                        elif self.phase2_anim_cycle == 1:
                            self.phase2_anim_cycle = 2
                        else:
                            self.phase2_anim_cycle = 1
                else:
                    self.phase1_anim_frame += self.phase1_anim_speed * dt
                    if self.phase1_anim_frame >= 10:
                        self.phase1_anim_frame -= 10
            
            if self.boss_phase == 2:
                if not self.boss_reverse_applied and player is not None:
                    self.boss_reverse_applied = True
                    player.controls_reversed = True
                    self.boss_laser_active = True
                self.boss_chopstick_rain_timer += dt
                if self.boss_chopstick_rain_timer >= self.boss_chopstick_rain_interval:
                    self.boss_chopstick_rain_timer = 0.0
                    self.boss_spawn_chopstick = True
                self.boss_bandage_timer += dt
                if self.boss_bandage_timer >= self.boss_bandage_interval:
                    self.boss_bandage_timer = 0.0
                    self.boss_spawn_bandage = True
            
            if self.boss_phase == 2 and self.boss_laser_active:
                self.boss_laser_angle -= self.boss_laser_rotate_speed * dt
                self.boss_laser_dir = pygame.math.Vector2(
                    math.cos(math.radians(self.boss_laser_angle)),
                    math.sin(math.radians(self.boss_laser_angle))
                )
                if self.boss_laser_dir.length() > 0:
                    self.boss_laser_dir = self.boss_laser_dir.normalize()
                laser_end = self.pos.copy()
                if tile_map is not None and len(tile_map) > 0:
                    room_w_l = len(tile_map[0]) * TILE_SIZE
                    room_h_l = len(tile_map) * TILE_SIZE
                    max_t = 9999
                    if abs(self.boss_laser_dir.x) > 0.0001:
                        t_left = (0 - self.pos.x) / self.boss_laser_dir.x
                        t_right = (room_w_l - self.pos.x) / self.boss_laser_dir.x
                        if t_left > 0: max_t = min(max_t, t_left)
                        if t_right > 0: max_t = min(max_t, t_right)
                    if abs(self.boss_laser_dir.y) > 0.0001:
                        t_top = (0 - self.pos.y) / self.boss_laser_dir.y
                        t_bottom = (room_h_l - self.pos.y) / self.boss_laser_dir.y
                        if t_top > 0: max_t = min(max_t, t_top)
                        if t_bottom > 0: max_t = min(max_t, t_bottom)
                    laser_end = self.pos + self.boss_laser_dir * max_t
                self.boss_laser_wall_hit = laser_end
                self.boss_laser_frame_timer += dt * 10.0
                if self.boss_laser_frame_timer >= 1.0:
                    self.boss_laser_frame_timer -= 1.0
                    self.boss_laser_frame_index = (self.boss_laser_frame_index + 1) % 8
                self.boss_laser_damage_cd -= dt
                if player and self.boss_laser_wall_hit and self.boss_laser_damage_cd <= 0:
                    seg = self.boss_laser_wall_hit - self.pos
                    seg_len_sq = seg.length_squared()
                    if seg_len_sq > 0:
                        t = max(0, min(1, (player.pos - self.pos).dot(seg) / seg_len_sq))
                        proj = self.pos + t * seg
                        dist_to_beam = player.pos.distance_to(proj)
                        if dist_to_beam < self.boss_laser_width + player.radius and 0 < t <= 1:
                            if not (player.is_dashing or player.inv_timer > 0):
                                res = player.take_damage(3)
                                self.boss_laser_damage_cd = 0.4
                                if res == "BLOCKED" and damage_texts is not None:
                                    damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                                elif res and damage_texts is not None:
                                    damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                                    if particles is not None:
                                        for _ in range(5): particles.append(Particle(player.pos.x, player.pos.y))
            
            if self.spike_state != 'none':
                self.spike_timer -= dt
                if self.spike_state == 'vertical_warn' and self.spike_timer <= 0:
                    self.spike_state = 'vertical_fall'
                    self.spike_fall_progress = 0.0
                    self.spike_fall_speed = 0.0
                    self.spike_damage_dealt = False
                elif self.spike_state == 'vertical_fall':
                    self.spike_fall_speed += 2500 * dt
                    self.spike_fall_progress += self.spike_fall_speed * dt
                    if self.spike_fall_progress >= 400:
                        self.spike_state = 'vertical_impact'
                        self.spike_impact_timer = 0.5
                        if particles is not None:
                            for sp in self.spike_positions_v:
                                for _ in range(30): particles.append(ExplosionParticle(sp.x, sp.y))
                        if player and not self.spike_damage_dealt:
                            for sp in self.spike_positions_v:
                                if sp.distance_to(player.pos) < self.spike_radius + player.radius:
                                    if not (player.is_dashing or player.inv_timer > 0):
                                        res = player.take_damage(4)
                                        if res == "BLOCKED" and damage_texts is not None:
                                            damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                                        elif res == True:
                                            if damage_texts is not None:
                                                damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                                            if particles is not None:
                                                for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
                                    self.spike_damage_dealt = True
                                    break
                elif self.spike_state == 'vertical_impact':
                    self.spike_impact_timer -= dt
                    if self.spike_impact_timer <= 0:
                        self.spike_state = 'gap'
                        self.spike_timer = 0.15
                elif self.spike_state == 'gap' and self.spike_timer <= 0:
                    self.spike_state = 'horizontal_warn'
                    self.spike_timer = 0.6 * DIFF[current_difficulty]['warn_mult']
                elif self.spike_state == 'horizontal_warn' and self.spike_timer <= 0:
                    self.spike_state = 'horizontal_fall'
                    self.spike_fall_progress = 0.0
                    self.spike_fall_speed = 0.0
                    self.spike_damage_dealt = False
                elif self.spike_state == 'horizontal_fall':
                    self.spike_fall_speed += 2500 * dt
                    self.spike_fall_progress += self.spike_fall_speed * dt
                    if self.spike_fall_progress >= 400:
                        self.spike_state = 'horizontal_impact'
                        self.spike_impact_timer = 0.5
                        if particles is not None:
                            for sp in self.spike_positions_h:
                                for _ in range(30): particles.append(ExplosionParticle(sp.x, sp.y))
                        if player and not self.spike_damage_dealt:
                            for sp in self.spike_positions_h:
                                if sp.distance_to(player.pos) < self.spike_radius + player.radius:
                                    if not (player.is_dashing or player.inv_timer > 0):
                                        res = player.take_damage(4)
                                        if res == "BLOCKED" and damage_texts is not None:
                                            damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                                        elif res == True:
                                            if damage_texts is not None:
                                                damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                                            if particles is not None:
                                                for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
                                    self.spike_damage_dealt = True
                                    break
                elif self.spike_state == 'horizontal_impact':
                    self.spike_impact_timer -= dt
                    if self.spike_impact_timer <= 0:
                        if getattr(self, 'spike_round', 0) == 0:
                            self.spike_round = 1
                            self._generate_spike_positions(tile_map, inverse=True)
                            self.spike_state = 'vertical_warn'
                            self.spike_timer = 0.6 * DIFF[current_difficulty]['warn_mult']
                        else:
                            self.spike_round = 0
                            self.spike_state = 'none'
                            self.attack_timer = 1.5
                            self.attack_order_idx = (self.attack_order_idx + 1) % len(self.attack_order)
                            self.attack_pattern = self.attack_order[self.attack_order_idx]
                            self._warning_ready = False
            
            if self.boss_phase == 1 and not self.summon_used and self.phase1_hp <= self.phase1_max_hp * 0.5:
                self.summon_used = True
                self.summon_shield = True
                self.summon_minion_ids = []
                summon_pool = ['chalk', 'pencil', 'badminton_racket', 'food_tray', 'steel_scrubber', 'keyboard', 'mine_book', 'gamble_book']
                chosen = random.sample(summon_pool, 3)
                if tile_map and len(tile_map) > 0:
                    room_w_local = len(tile_map[0]) * TILE_SIZE
                    room_h_local = len(tile_map) * TILE_SIZE
                else:
                    room_w_local = 2000; room_h_local = 2000
                summon_positions = []
                for mtype in chosen:
                    for _ in range(100):
                        sx = random.randint(int(TILE_SIZE * 3), room_w_local - int(TILE_SIZE * 3))
                        sy = random.randint(int(TILE_SIZE * 3), room_h_local - int(TILE_SIZE * 3))
                        if tile_map:
                            c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                            if 0 <= c_y < len(tile_map) and 0 <= c_x < len(tile_map[0]):
                                if tile_map[c_y][c_x] in [1, 2, 3]: continue
                        if pygame.math.Vector2(sx, sy).distance_to(self.pos) < 300: continue
                        too_close = False
                        for px, py in summon_positions:
                            if pygame.math.Vector2(sx, sy).distance_to(pygame.math.Vector2(px, py)) < 120:
                                too_close = True; break
                        if too_close: continue
                        summon_positions.append((sx, sy))
                        break
                for idx, mtype in enumerate(chosen):
                    if idx < len(summon_positions):
                        sx, sy = summon_positions[idx]
                        sp = MonsterSpawn(sx, sy, enemy_type=mtype)
                        sp.extra_attrs['_boss_minion'] = True
                        if spawners_list is not None:
                            spawners_list.append(sp)
            
            if self.summon_shield and self.summon_minion_ids is not None:
                self.summon_shield_timer += dt
                still_alive = False
                if enemies_list is not None:
                    for e in enemies_list:
                        if getattr(e, '_boss_minion', False) and e.hp > 0:
                            still_alive = True; break
                if not still_alive and not any(getattr(sp, 'extra_attrs', {}).get('_boss_minion', False) for sp in (spawners_list or [])):
                    self.summon_shield = False
                    self.summon_minion_ids = []
                    self.summon_shield_break = True
            
            if self.bubble_state == 'ACTIVE':
                self.bubble_timer -= dt
                if self.bubble_timer <= 0 and enemy_bullets is not None:
                    num_sectors = 32
                    is_attack = (self.bubble_wave % 2 == 0)
                    for i in range(num_sectors):
                        sector_attack = (i % 2 == 0) == is_attack
                        if sector_attack:
                            angle = (2 * math.pi / num_sectors) * i + self.bubble_angle_offset
                            tx = self.pos.x + math.cos(angle) * 10
                            ty = self.pos.y + math.sin(angle) * 10
                            eb = EnemyBullet(self.pos.x, self.pos.y, tx, ty, damage=2)
                            eb.is_bubble = True
                            eb.speed = int(450 * DIFF[current_difficulty]['proj_speed_mult'])
                            eb.radius = 18
                            enemy_bullets.append(eb)
                    self.bubble_wave += 1
                    if self.bubble_wave >= 10:
                        self.bubble_state = 'none'
                        self.bubble_wave = 0
                        self.attack_order_idx = (self.attack_order_idx + 1) % len(self.attack_order)
                        self.attack_pattern = self.attack_order[self.attack_order_idx]
                        self.attack_timer = 1.0
                        self._warning_ready = False
                    else:
                        self.bubble_timer = 0.3
            
            if self.aim_state == 'WARN':
                self.aim_timer -= dt
                if self.aim_timer <= 0:
                    self.aim_state = 'FIRE'
                    self.aim_timer = 0.0
            elif self.aim_state == 'FIRE' and enemy_bullets is not None:
                spread = math.pi * 0.8 if self.aim_wave == 0 else math.pi * 0.4
                if not hasattr(self, 'aim_fire_index') or self.aim_fire_index < 0:
                    num = 18 if self.aim_wave == 0 else 12
                    self.aim_fire_index = 0
                    self.aim_fire_num = num
                    self.aim_fire_spread = spread
                if self.aim_fire_index < self.aim_fire_num:
                    idx = self.aim_fire_num - 1 - self.aim_fire_index if self.aim_wave == 1 else self.aim_fire_index
                    offset_angle = -self.aim_fire_spread / 2 + (self.aim_fire_spread / (self.aim_fire_num - 1)) * idx if self.aim_fire_num > 1 else 0
                    fire_angle = self.aim_base_angle + offset_angle
                    tx = self.pos.x + math.cos(fire_angle) * 10
                    ty = self.pos.y + math.sin(fire_angle) * 10
                    eb = EnemyBullet(self.pos.x, self.pos.y, tx, ty, damage=3)
                    eb.is_boss_syringe = True
                    eb.speed = int(800 * DIFF[current_difficulty]['proj_speed_mult'])
                    eb.radius = 25
                    enemy_bullets.append(eb)
                    self.aim_fire_index += 1
                    self.aim_timer = 0.06
                else:
                    self.aim_wave += 1
                    self.aim_fire_index = -1
                    if self.aim_wave >= 2:
                        self.aim_state = 'none'
                        self.aim_wave = 0
                        self.attack_order_idx = (self.attack_order_idx + 1) % len(self.attack_order)
                        self.attack_pattern = self.attack_order[self.attack_order_idx]
                        self.attack_timer = 1.0
                        self._warning_ready = False
                    else:
                        self.aim_state = 'WARN'
                        self.aim_timer = 0.6
            
            if self.brush_state != 'none':
                self.brush_timer -= dt
                if self.brush_state == 'WARN':
                    if self.brush_timer <= 0:
                        self.brush_state = 'WARN_LINE'
                        self.brush_timer = 0.25
                elif self.brush_state == 'WARN_LINE':
                    if self.brush_timer <= 0:
                        self.brush_state = 'ATTACK'
                        for b in self.brushes:
                            b['base_pos'] = b['pos'].copy()
                            b['travel_dist'] = 0.0
                            b['damage_dealt'] = False
                            b['active'] = True
                elif self.brush_state == 'ATTACK':
                    dash_speed = 1350
                    all_done = True
                    for b in self.brushes:
                        if not b['active']: continue
                        b['travel_dist'] += dash_speed * dt
                        freq = 0.07
                        zigzag_width = 35
                        zigzag_offset = math.sin(b['travel_dist'] * freq) * zigzag_width
                        b['base_pos'] = b['base_pos'] + b['move_dir'] * dash_speed * dt
                        b['pos'] = b['base_pos'] + b['ortho_dir'] * zigzag_offset
                        brush_radius = 22
                        if player and not b['damage_dealt']:
                            if b['pos'].distance_to(player.pos) < brush_radius + player.radius:
                                if not (player.is_dashing or player.inv_timer > 0):
                                    res = player.take_damage(3)
                                    if res == "BLOCKED" and damage_texts is not None:
                                        damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                                    elif res == True:
                                        if damage_texts is not None:
                                            damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                                        if particles is not None:
                                            for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
                                b['damage_dealt'] = True
                        if b['travel_dist'] >= b['total_dist']:
                            b['active'] = False
                        else:
                            all_done = False
                    if all_done:
                        self.brush_state = 'DISAPPEAR'
                        self.brush_timer = 0.08
                elif self.brush_state == 'DISAPPEAR':
                    if self.brush_timer <= 0:
                        self.brush_count += 1
                        self.brush_side *= -1
                        if self.brush_count >= 3:
                            self.brush_state = 'none'
                            self.brush_count = 0
                            self.brushes = []
                            self.attack_order_idx = (self.attack_order_idx + 1) % len(self.attack_order)
                            self.attack_pattern = self.attack_order[self.attack_order_idx]
                            self.attack_timer = 1.5
                            self._warning_ready = False
                        else:
                            self._brush_start_next(tile_map, player)
            
            if self.spike_state == 'none' and self.bubble_state == 'none' and self.aim_state == 'none' and self.brush_state == 'none' and not (self.boss_phase == 1 and self.phase1_hp <= 0):
                self.attack_timer -= dt
                if not self._warning_ready and self.attack_timer <= self.attack_warning_duration and self.attack_timer > 0:
                    self._warning_ready = True
                    if self.attack_pattern == 0:
                        self.next_attack_offset = random.uniform(0, math.pi / 4)
                
                if self.attack_timer <= 0 and enemy_bullets is not None:
                    self._warning_ready = False
                    
                    if self.attack_pattern == 0:
                        offset = self.next_attack_offset
                        for i in range(8):
                            angle = (2 * math.pi / 8) * i + offset
                            tx = self.pos.x + math.cos(angle) * 10
                            ty = self.pos.y + math.sin(angle) * 10
                            eb = EnemyBullet(self.pos.x, self.pos.y, tx, ty, damage=3)
                            eb.is_boss_soccer = True
                            eb.speed = int(450 * DIFF[current_difficulty]['proj_speed_mult'])
                            eb.radius = 30
                            eb.boss_soccer_tile_map = tile_map
                            enemy_bullets.append(eb)
                        self.attack_order_idx = (self.attack_order_idx + 1) % len(self.attack_order)
                        self.attack_pattern = self.attack_order[self.attack_order_idx]
                        self.attack_timer = 1.5
                    elif self.attack_pattern == 1:
                        if tile_map is not None and len(tile_map) > 0:
                            self.spike_round = 0
                            self._generate_spike_positions(tile_map)
                            self.spike_state = 'vertical_warn'
                            self.spike_timer = 0.3 * DIFF[current_difficulty]['warn_mult']
                            self.spike_damage_dealt = False
                        else:
                            self.attack_order_idx = (self.attack_order_idx + 1) % len(self.attack_order)
                            self.attack_pattern = self.attack_order[self.attack_order_idx]
                            self.attack_timer = 3.0
                    elif self.attack_pattern == 2:
                        self.bubble_state = 'ACTIVE'
                        self.bubble_wave = 0
                        self.bubble_angle_offset = random.uniform(0, math.pi / 8)
                        self.bubble_timer = 0.3
                    elif self.attack_pattern == 3:
                        if player is not None:
                            self.aim_state = 'WARN'
                            self.aim_timer = 0.8
                            self.aim_wave = 0
                            dir_to_player = player.pos - self.pos
                            self.aim_base_angle = math.atan2(dir_to_player.y, dir_to_player.x) if dir_to_player.length() > 0 else 0
                        else:
                            self.attack_order_idx = (self.attack_order_idx + 1) % len(self.attack_order)
                            self.attack_pattern = self.attack_order[self.attack_order_idx]
                            self.attack_timer = 1.5
                    elif self.attack_pattern == 4:
                        if player is not None and tile_map is not None and len(tile_map) > 0:
                            self.brush_count = 0
                            self.brush_side = random.choice([-1, 1])
                            self._brush_start_next(tile_map, player)
                        else:
                            self.attack_order_idx = (self.attack_order_idx + 1) % len(self.attack_order)
                            self.attack_pattern = self.attack_order[self.attack_order_idx]
                            self.attack_timer = 1.5

        elif self.type == 'pill_boss':
            # 알약 보스: 맵 중앙에 고정, 주변 몬스터(bandage, syringe)가 모두 죽으면 무적 해제
            # 무적이 한번 해제되면 다시 복구 불가
            if not getattr(self, 'invincible_permanently_lost', False):
                prev_invincible = self.is_invincible
                helper_found = False
                # enemies_list에서 bandage/syringe가 살아있는지 확인
                if enemies_list is not None:
                    for e in enemies_list:
                        if e is not self and e.type in ['bandage', 'syringe'] and e.hp > 0:
                            helper_found = True; break
                # spawner에 bandage/syringe가 아직 남아있어도 무적 유지
                if not helper_found and spawners_list is not None:
                    for sp in spawners_list:
                        if sp.enemy_type in ['bandage', 'syringe']:
                            helper_found = True; break
                self.is_invincible = helper_found
                if not helper_found:
                    self.invincible_permanently_lost = True
                # 무적 해제 순간 감지 플래그 (메인 루프에서 파티클 생성에 사용)
                if prev_invincible and not self.is_invincible:
                    self.shield_break = True

            # 탄막 패턴: 5초마다 맵 밖에서 16개 탄막 생성 (15 빨간 + 1 파란), 중앙으로 조여옴
            self.bullet_timer -= dt
            if self.bullet_timer <= 0:
                if enemy_bullets is not None and tile_map is not None and len(tile_map) > 0:
                    room_w = len(tile_map[0]) * TILE_SIZE
                    room_h = len(tile_map) * TILE_SIZE
                    cx = room_w // 2
                    cy = room_h // 2
                    
                    num_bullets = 16
                    spawn_radius = max(room_w, room_h) * 0.8  # 맵 밖 반경
                    # 16개 중 1개를 랜덤으로 파란 알약으로 설정 (이전 위치 제외)
                    available_indices = [i for i in range(num_bullets) if i != self.last_blue_index]
                    blue_index = random.choice(available_indices)
                    
                    for i in range(num_bullets):
                        angle = (2 * math.pi / num_bullets) * i
                        sx = cx + math.cos(angle) * spawn_radius
                        sy = cy + math.sin(angle) * spawn_radius
                        # 보스 쪽(중앙)으로 향하는 방향
                        dir_to_center = pygame.math.Vector2(cx - sx, cy - sy)
                        if dir_to_center.length() > 0:
                            dir_to_center = dir_to_center.normalize()
                        target_x = sx + dir_to_center.x * 10
                        target_y = sy + dir_to_center.y * 10
                        
                        if i == blue_index:
                            # 파란 알약 탄막: 체력 회복
                            eb = EnemyBullet(sx, sy, target_x, target_y, damage=0)
                            eb.is_pill_bullet = True
                            eb.is_healing_pill = True  # 파란 알약 표시
                            eb.radius = 30  # 충돌 판정 크기 감소
                        else:
                            # 빨간 알약 탄막: 데미지
                            eb = EnemyBullet(sx, sy, target_x, target_y, damage=4)
                            eb.is_pill_bullet = True
                            eb.is_healing_pill = False
                            eb.radius = 30  # 충돌 판정 크기 감소
                        
                        eb.speed = int(250 * DIFF[current_difficulty]['proj_speed_mult'])
                        eb.boss_center = pygame.math.Vector2(cx, cy)  # 중앙 좌표 저장
                        eb.arrive_threshold = 20  # 중앙 도달 판정 거리
                        enemy_bullets.append(eb)
                    self.last_blue_index = blue_index  # 다음 공격에서 이 위치 제외
                 
                self.bullet_timer = 5.0  # 5초마다 발사

            # 플레이어 접촉 데미지 (무적 상태일 때도 접촉 데미지 적용)
            if player and self.pos.distance_to(player.pos) < self.radius + player.radius:
                if not (player.is_dashing or player.inv_timer > 0):
                    res = player.take_damage(self.damage)
                    if res == "BLOCKED" and damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                    elif res == True:
                        if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                        for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
        
        elif self.type == 'keyboard':
            self.timer -= dt
            
            if self.state == 'IDLE':
                if self.timer <= 0:
                    self.state = 'PRECAST'; self.timer = 1.0
            
            elif self.state == 'PRECAST':
                if self.timer <= 0:
                    self.state = 'TYPING'
                    banned_len = 0
                    if enemies_list is not None:
                        for other in enemies_list:
                            if other is not self and other.type == 'keyboard' and getattr(other, 'active_word_len', 0) > 0:
                                banned_len = other.active_word_len
                    self.words_to_type = []
                    for _ in range(self.max_attacks):
                        pool = [w for w in self.word_pool if len(w) != banned_len] if banned_len else self.word_pool
                        if not pool: pool = self.word_pool
                        self.words_to_type.append(random.choice(pool))
                    self.current_word_idx = 0
                    self.typed_chars = 0
                    self.char_timer = self.char_speed
                    self.active_word_len = len(self.words_to_type[0])
            
            elif self.state == 'TYPING':
                self.char_timer -= dt
                if self.char_timer <= 0 and self.current_word_idx < len(self.words_to_type):
                    self.typed_chars += 1
                    self.char_timer = self.char_speed
                    
                    current_word = self.words_to_type[self.current_word_idx]
                    if self.typed_chars >= len(current_word):
                        if enemy_bullets is not None:
                            dir_vec = target_pos - self.pos
                            if dir_vec.length() > 0:
                                nd = dir_vec.normalize()
                                tx = self.pos.x + nd.x * 10
                                ty = self.pos.y + nd.y * 10
                            else:
                                tx, ty = self.pos.x + 10, self.pos.y
                            eb = EnemyBullet(self.pos.x, self.pos.y, tx, ty, damage=self.damage)
                            eb.is_text_bullet = True
                            eb.text_content = current_word
                            eb.speed = max(200, 500 - len(current_word) * 30)
                            try:
                                fs = max(22, min(34, 18 + len(current_word) * 2))
                                tmp_font = get_korean_font(fs, bold=True)
                                tmp_surf = tmp_font.render(current_word, True, (255,255,255))
                                eb.radius = max(tmp_surf.get_width(), tmp_surf.get_height()) // 2 + 4
                            except:
                                eb.radius = max(15, len(current_word) * 8)
                            enemy_bullets.append(eb)
                        
                        self.current_word_idx += 1
                        if self.current_word_idx >= len(self.words_to_type):
                            self.state = 'REST'; self.timer = 5.0; self.active_word_len = 0
                        else:
                            self.typed_chars = 0; self.char_timer = 0.5
                            self.active_word_len = len(self.words_to_type[self.current_word_idx])
            
            elif self.state == 'REST':
                if self.timer <= 0:
                    self.state = 'IDLE'; self.timer = 2.0

        elif self.type == 'router':
            self.timer -= dt
            
            if self.state == 'IDLE':
                if self.timer <= 0:
                    self.state = 'PRECAST'; self.timer = 1.0
            
            elif self.state == 'PRECAST':
                if self.timer <= 0:
                    self.state = 'FIRE'
            
            elif self.state == 'FIRE':
                if enemy_bullets is not None:
                    if tile_map and len(tile_map) > 0:
                        room_w_local = len(tile_map[0]) * TILE_SIZE
                        room_h_local = len(tile_map) * TILE_SIZE
                        max_r = math.sqrt(room_w_local ** 2 + room_h_local ** 2) / 2 + 200
                    else:
                        max_r = 1500
                    wave = WifiWave(self.pos.x, self.pos.y, damage=self.damage, max_radius=max_r)
                    enemy_bullets.append(wave)
                self.trigger_glitch = True
                self.state = 'COOLDOWN'; self.timer = 2.0
            
            elif self.state == 'COOLDOWN':
                if self.timer <= 0:
                    self.state = 'PRECAST'; self.timer = 1.0

        elif self.type == 'computer_mouse':
            if tile_map and len(tile_map) > 0:
                self.room_w = len(tile_map[0]) * TILE_SIZE
                self.room_h = len(tile_map) * TILE_SIZE
            
            if not self._mouse_initialized and self.room_w > 0 and self.room_h > 0:
                self._mouse_initialized = True
                margin = self.wall_margin
                corners = [
                    pygame.math.Vector2(margin, margin),
                    pygame.math.Vector2(margin, self.room_h - margin),
                    pygame.math.Vector2(self.room_w - margin, self.room_h - margin),
                    pygame.math.Vector2(self.room_w - margin, margin)
                ]
                best_dist = float('inf')
                for ci, cp in enumerate(corners):
                    d = self.pos.distance_to(cp)
                    if d < best_dist:
                        best_dist = d
                        self.patrol_index = ci
            
            margin = self.wall_margin
            
            if self.room_w > 0 and self.room_h > 0:
                if self.patrol_index == 0: corner_pos = pygame.math.Vector2(margin, margin)
                elif self.patrol_index == 1: corner_pos = pygame.math.Vector2(margin, self.room_h - margin)
                elif self.patrol_index == 2: corner_pos = pygame.math.Vector2(self.room_w - margin, self.room_h - margin)
                else: corner_pos = pygame.math.Vector2(self.room_w - margin, margin)
            else:
                corner_pos = self.pos.copy()
            
            if self.laser_damage_cd > 0:
                self.laser_damage_cd -= dt
            
            if self.state == 'PATROL':
                if self.room_w <= 0 or self.room_h <= 0:
                    pass
                else:
                    dir_to_corner = corner_pos - self.pos
                    dist_to_corner = dir_to_corner.length()
                    if dist_to_corner > self.speed * dt * 2:
                        if dist_to_corner > 0:
                            self.facing_angle = -math.degrees(math.atan2(dir_to_corner.y, dir_to_corner.x)) - 90
                            move_dir = dir_to_corner.normalize()
                            self.pos += move_dir * self.speed * dt
                    else:
                        self.pos = corner_pos.copy()
                        self.state = 'AT_CORNER'
                        self.timer = 1.0
            
            elif self.state == 'AT_CORNER':
                self.timer -= dt
                if self.timer <= 0:
                    center = pygame.math.Vector2(self.room_w / 2, self.room_h / 2)
                    to_center = center - self.pos
                    if to_center.length() > 0:
                        self.laser_dir = to_center.normalize()
                    self.laser_angle_deg = math.degrees(math.atan2(self.laser_dir.y, self.laser_dir.x))
                    self.laser_initial_angle_deg = self.laser_angle_deg
                    self.facing_angle = -self.laser_angle_deg - 90
                    self.state = 'LASER'
                    self.laser_active = True
                    self.laser_frame_timer = 0.0
                    self.laser_frame_index = 0
                    self.laser_damage_cd = 0.0
                    self.laser_hold_timer = 1.5
                    self.laser_fire_timer = 3.0
            
            elif self.state == 'LASER':
                if self.laser_hold_timer > 0:
                    self.laser_hold_timer -= dt
                else:
                    self.laser_angle_deg += self.laser_rotate_speed * dt * self.mouse_direction
                    self.laser_dir = pygame.math.Vector2(
                        math.cos(math.radians(self.laser_angle_deg)),
                        math.sin(math.radians(self.laser_angle_deg))
                    )
                    if self.laser_dir.length() > 0:
                        self.laser_dir = self.laser_dir.normalize()
                    self.facing_angle = -self.laser_angle_deg - 90
                    self.laser_fire_timer -= dt
                
                laser_end = self.pos.copy()
                if self.laser_dir.length() > 0 and self.room_w > 0 and self.room_h > 0:
                    max_t = 9999
                    if abs(self.laser_dir.x) > 0.0001:
                        t_left = (0 - self.pos.x) / self.laser_dir.x
                        t_right = (self.room_w - self.pos.x) / self.laser_dir.x
                        if t_left > 0: max_t = min(max_t, t_left)
                        if t_right > 0: max_t = min(max_t, t_right)
                    if abs(self.laser_dir.y) > 0.0001:
                        t_top = (0 - self.pos.y) / self.laser_dir.y
                        t_bottom = (self.room_h - self.pos.y) / self.laser_dir.y
                        if t_top > 0: max_t = min(max_t, t_top)
                        if t_bottom > 0: max_t = min(max_t, t_bottom)
                    laser_end = self.pos + self.laser_dir * max_t
                self.laser_wall_hit = laser_end
                
                self.laser_frame_timer += dt * 10.0
                if self.laser_frame_timer >= 1.0:
                    self.laser_frame_timer -= 1.0
                    self.laser_frame_index = (self.laser_frame_index + 1) % 8
                
                if player and self.laser_wall_hit and self.laser_damage_cd <= 0:
                    seg = self.laser_wall_hit - self.pos
                    seg_len_sq = seg.length_squared()
                    if seg_len_sq > 0:
                        t = max(0, min(1, (player.pos - self.pos).dot(seg) / seg_len_sq))
                        proj = self.pos + t * seg
                        dist_to_beam = player.pos.distance_to(proj)
                        if dist_to_beam < self.laser_width + player.radius and 0 < t <= 1:
                            if not (player.is_dashing or player.inv_timer > 0):
                                res = player.take_damage(self.damage)
                                self.laser_damage_cd = 0.4
                                if res == "BLOCKED" and damage_texts is not None:
                                    damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                                elif res and damage_texts is not None:
                                    damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                                    for _ in range(5): particles.append(Particle(player.pos.x, player.pos.y))
                
                if self.laser_fire_timer <= 0:
                    self.laser_active = False
                    self.laser_wall_hit = None
                    self.state = 'COOLDOWN'
                    self.timer = 1.0
            
            elif self.state == 'COOLDOWN':
                self.timer -= dt
                if self.timer <= 0:
                    self.patrol_index = (self.patrol_index + self.mouse_direction) % 4
                    self.state = 'PATROL'

        elif self.type == 'mine_book':
            self.timer -= dt
            if self.timer <= 0:
                self.timer = random.uniform(0.4, 1.2)
                angle = random.uniform(0, 2 * math.pi)
                self.move_dir = pygame.math.Vector2(math.cos(angle), math.sin(angle)).normalize()

            move_x = self.move_dir.x * self.speed * dt
            move_y = self.move_dir.y * self.speed * dt
            can_move_x, can_move_y = True, True
            if tile_map:
                c_x, r_cur = int((self.pos.x + move_x + (self.radius if move_x > 0 else -self.radius)) // TILE_SIZE), int(self.pos.y // TILE_SIZE)
                if move_x != 0:
                    if 0 <= c_x < len(tile_map[0]) and 0 <= r_cur < len(tile_map):
                        if tile_map[r_cur][c_x] in [1, 2, 3]: can_move_x = False
                    else: can_move_x = False
                c_y, c_cur = int((self.pos.y + move_y + (self.radius if move_y > 0 else -self.radius)) // TILE_SIZE), int(self.pos.x // TILE_SIZE)
                if move_y != 0:
                    if 0 <= c_y < len(tile_map) and 0 <= c_cur < len(tile_map[0]):
                        if tile_map[c_y][c_cur] in [1, 2, 3]: can_move_y = False
                    else: can_move_y = False

            if can_move_x:
                self.pos.x += move_x
            else:
                self.move_dir.x *= -1
                new_angle = math.atan2(self.move_dir.y, self.move_dir.x) + random.uniform(-0.6, 0.6)
                self.move_dir = pygame.math.Vector2(math.cos(new_angle), math.sin(new_angle)).normalize()
                self.timer = random.uniform(0.4, 1.2)
            if can_move_y:
                self.pos.y += move_y
            else:
                self.move_dir.y *= -1
                new_angle = math.atan2(self.move_dir.y, self.move_dir.x) + random.uniform(-0.6, 0.6)
                self.move_dir = pygame.math.Vector2(math.cos(new_angle), math.sin(new_angle)).normalize()
                self.timer = random.uniform(0.4, 1.2)

            self.mine_place_timer -= dt
            self.mine_pre_place = (0 < self.mine_place_timer <= 0.4)
            if self.mine_place_timer <= 0:
                mine_pos = pygame.math.Vector2(self.pos.x, self.pos.y)
                too_close = False
                if hasattr(self, '_mines_list') and self._mines_list is not None:
                    for m in self._mines_list:
                        if m.alive and m.pos.distance_to(mine_pos) < TILE_SIZE:
                            too_close = True
                            break
                if too_close:
                    self.mine_place_timer = 0.5
                    self.mine_retry = True
                else:
                    if hasattr(self, '_mines_list') and self._mines_list is not None:
                        self._mines_list.append(LibraryMine(self.pos.x, self.pos.y, damage=self.damage))
                    self.mine_place_timer = 4.5
                    self.mine_retry = False

        elif self.type == 'gravity_book':
            self.float_timer += dt
            if self.state == 'IDLE':
                self.timer -= dt
                if self.timer <= 0:
                    self.state = 'PRECAST'; self.timer = 1.0; self.anim_frame = 0.0
            elif self.state == 'PRECAST':
                self.timer -= dt
                self.anim_frame += dt
                if self.timer <= 0:
                    self.state = 'ACTIVE'
                    if player is not None:
                        player.controls_reversed = True
            elif self.state == 'ACTIVE':
                pass

        elif self.type == 'forbidden_book':
            self.float_timer += dt
            if self.state == 'IDLE':
                self.timer -= dt
                if self.timer <= 0:
                    self.state = 'PRECAST'; self.timer = 1.0; self.anim_frame = 0.0
            elif self.state == 'PRECAST':
                self.timer -= dt
                self.anim_frame += dt
                if self.timer <= 0:
                    self.state = 'ACTIVE'
            elif self.state == 'ACTIVE':
                pass

        elif self.type == 'gamble_book':
            self.timer -= dt
            self.spin_angle += 360 * dt
            if tile_map and len(tile_map) > 0:
                self.room_w = len(tile_map[0]) * TILE_SIZE
                self.room_h = len(tile_map) * TILE_SIZE
            for db in self.dice_bullets[:]:
                db.update(dt)
                if not db.alive:
                    self.dice_bullets.remove(db)
            for md in self.mini_dices[:]:
                md.update(dt)
                if not md.alive:
                    self.mini_dices.remove(md)
            if not hasattr(self, '_gb_prev_player_pos'):
                self._gb_prev_player_pos = pygame.math.Vector2(target_pos)
            player_vel = target_pos - self._gb_prev_player_pos
            if dt > 0:
                player_vel_per_sec = player_vel / dt
            else:
                player_vel_per_sec = pygame.math.Vector2(0, 0)
            self._gb_prev_player_pos = pygame.math.Vector2(target_pos)

            if self.state == 'CHASE':
                dist_to_player = self.pos.distance_to(target_pos)
                if dist_to_player > 305:
                    self.move_towards(dt, target_pos, tile_map)
                elif dist_to_player < 295:
                    away_dir = self.pos - target_pos
                    if away_dir.length() > 0:
                        self.move_towards(dt, self.pos + away_dir.normalize() * 200, tile_map)
                if self.timer <= 0:
                    self.state = 'PRECAST'; self.timer = 0.8

            elif self.state == 'PRECAST':
                if self.timer <= 0:
                    self.state = 'THROW'
                    self.timer = 3.5
                    predict_time = self.dice_throw_range / 350
                    predicted_pos = target_pos + player_vel_per_sec * predict_time * 0.5
                    for i in range(2):
                        spread_x = random.uniform(-60, 60)
                        spread_y = random.uniform(-60, 60)
                        offset_x = random.uniform(-15, 15)
                        offset_y = random.uniform(-15, 15)
                        target_x = predicted_pos.x + spread_x
                        target_y = predicted_pos.y + spread_y
                        dice = DiceBullet(self.pos.x + offset_x, self.pos.y + offset_y, target_x, target_y, damage=self.damage, room_w=max(200, self.room_w), room_h=max(200, self.room_h))
                        dist = self.pos.distance_to(pygame.math.Vector2(target_x, target_y))
                        dice.total_distance = max(100, dist)
                        self.dice_bullets.append(dice)

            elif self.state == 'THROW':
                dist_to_player = self.pos.distance_to(target_pos)
                if dist_to_player > 305:
                    self.move_towards(dt, target_pos, tile_map)
                elif dist_to_player < 295:
                    away_dir = self.pos - target_pos
                    if away_dir.length() > 0:
                        self.move_towards(dt, self.pos + away_dir.normalize() * 200, tile_map)
                all_done = True
                for db in self.dice_bullets:
                    if db.alive and db.number_phase and not db.number_confirmed:
                        all_done = False
                    elif db.alive and not db.number_phase:
                        all_done = False
                    elif db.alive and db.gold_text_timer > 0:
                        all_done = False
                if all_done:
                    for db in self.dice_bullets[:]:
                        if db.mini_dices_spawned and db.alive:
                            num = db.final_number
                            for _ in range(num * 3):
                                md = MiniDice(db.pos.x, db.pos.y, damage=self.damage, room_w=max(200, self.room_w), room_h=max(200, self.room_h))
                                self.mini_dices.append(md)
                            db.alive = False
                    self.state = 'COOLDOWN'; self.timer = 2.0

            elif self.state == 'COOLDOWN':
                dist_to_player = self.pos.distance_to(target_pos)
                if dist_to_player > 305:
                    self.move_towards(dt, target_pos, tile_map)
                elif dist_to_player < 295:
                    away_dir = self.pos - target_pos
                    if away_dir.length() > 0:
                        self.move_towards(dt, self.pos + away_dir.normalize() * 200, tile_map)
                if self.timer <= 0:
                    self.state = 'CHASE'; self.timer = 2.0
        else:
            self.move_towards(dt, target_pos, tile_map)

        # 👈 일반 몬스터 및 기타 적의 기본 몸통 박치기 공격 로직 추가 (상태 무관)
        if self.type in ['normal', 'boss', 'pencil', 'toothbrush', 'bandage', 'syringe', 'keyboard', 'router', 'gravity_book', 'forbidden_book', 'gamble_book']:
            if player and self.pos.distance_to(player.pos) < self.radius + player.radius:
                if not (player.is_dashing or player.inv_timer > 0):
                    res = player.take_damage(self.damage)
                    if res == "BLOCKED":
                        if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                    elif res == True:
                        if damage_texts is not None: damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                        for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))

    def move_towards(self, dt, target_pos, tile_map):
        self.path_calc_timer -= dt
        if self.path_calc_timer <= 0:
            self.path_calc_timer = 0.2
            self.path = self.get_path(target_pos, tile_map) if tile_map else []

        direction = pygame.math.Vector2(0, 0)
        if self.path and len(self.path) > 0:
            next_node = self.path[0]; node_target = pygame.math.Vector2(next_node[0] * TILE_SIZE + TILE_SIZE / 2, next_node[1] * TILE_SIZE + TILE_SIZE / 2)
            if self.pos.distance_to(node_target) < self.speed * dt * 2:
                self.path.pop(0)
                if not self.path: direction = target_pos - self.pos
                else: next_node = self.path[0]; node_target = pygame.math.Vector2(next_node[0] * TILE_SIZE + TILE_SIZE / 2, next_node[1] * TILE_SIZE + TILE_SIZE / 2); direction = node_target - self.pos
            else: direction = node_target - self.pos
        else: direction = target_pos - self.pos
            
        if direction.length() > 0: direction = direction.normalize()
        move_x, move_y = direction.x * self.speed * dt, direction.y * self.speed * dt
        
        can_move_x, can_move_y = True, True
        if tile_map:
            c_x, r_cur = int((self.pos.x + move_x + (self.radius if move_x > 0 else -self.radius)) // TILE_SIZE), int(self.pos.y // TILE_SIZE)
            if move_x != 0:
                if 0 <= c_x < len(tile_map[0]) and 0 <= r_cur < len(tile_map):
                    if tile_map[r_cur][c_x] in [1, 2, 3]: can_move_x = False
                else:
                    can_move_x = False  # 맵 밖은 무조건 벽
            
            c_y, c_cur = int((self.pos.y + move_y + (self.radius if move_y > 0 else -self.radius)) // TILE_SIZE), int(self.pos.x // TILE_SIZE)
            if move_y != 0:
                if 0 <= c_y < len(tile_map) and 0 <= c_cur < len(tile_map[0]):
                    if tile_map[c_y][c_cur] in [1, 2, 3]: can_move_y = False
                else:
                    can_move_y = False  # 맵 밖은 무조건 벽

        if can_move_x: self.pos.x += move_x
        if can_move_y: self.pos.y += move_y
        
    def _brush_start_next(self, tile_map, player):
        if player is None: return
        view_left = player.pos.x - VIEW_W / 2
        view_right = player.pos.x + VIEW_W / 2
        margin = 150
        num_total = 15
        num_aimed = 3
        safe_direction = random.choice([-1, 1])
        safe_y = player.pos.y + safe_direction * random.uniform(90, 150)
        safe_half = 85
        if self.brush_side == 1:
            spawn_x = view_left - margin
        else:
            spawn_x = view_right + margin
        self.brushes = []
        for i in range(num_total):
            is_aimed = i < num_aimed
            if is_aimed:
                target_y = player.pos.y + random.uniform(-15, 15)
            else:
                target_y = player.pos.y + random.uniform(-400, 400)
                for _ in range(20):
                    if abs(target_y - safe_y) < safe_half:
                        target_y = player.pos.y + random.uniform(-400, 400)
                    else:
                        break
                if abs(target_y - safe_y) < safe_half:
                    target_y = safe_y + safe_half * (1 if target_y < safe_y else -1)
            target_x = player.pos.x + random.uniform(-30, 30)
            spawn_y = target_y + random.uniform(-10, 10)
            raw_dir = pygame.math.Vector2(target_x - spawn_x, target_y - spawn_y)
            if raw_dir.length() > 0: raw_dir = raw_dir.normalize()
            else: raw_dir = pygame.math.Vector2(1 if self.brush_side == 1 else -1, 0)
            angle_offset = random.uniform(-0.08, 0.08)
            cos_a = math.cos(angle_offset); sin_a = math.sin(angle_offset)
            move_dir = pygame.math.Vector2(
                raw_dir.x * cos_a - raw_dir.y * sin_a,
                raw_dir.x * sin_a + raw_dir.y * cos_a
            )
            if move_dir.length() > 0: move_dir = move_dir.normalize()
            ortho_dir = pygame.math.Vector2(-move_dir.y, move_dir.x)
            start_pos = pygame.math.Vector2(spawn_x, spawn_y)
            dist_to_target = start_pos.distance_to(pygame.math.Vector2(target_x, target_y))
            total_dist = dist_to_target + VIEW_W * 0.7
            self.brushes.append({
                'start_pos': start_pos.copy(),
                'pos': start_pos.copy(),
                'base_pos': start_pos.copy(),
                'move_dir': move_dir,
                'ortho_dir': ortho_dir,
                'travel_dist': 0.0,
                'total_dist': total_dist,
                'damage_dealt': False,
                'is_aimed': is_aimed,
                'active': True,
            })
        self.brush_state = 'WARN'
        self.brush_timer = 0.15

    def _generate_spike_positions(self, tile_map, inverse=False):
        if tile_map is None or len(tile_map) == 0: return
        room_w = len(tile_map[0]) * TILE_SIZE
        room_h = len(tile_map) * TILE_SIZE
        strip_w = self.spike_radius * 2
        
        self.spike_positions_v = []
        is_attack = not inverse
        for x_start in range(0, room_w, strip_w):
            if is_attack:
                cx = x_start + self.spike_radius
                y = self.spike_radius
                while y < room_h:
                    c = int(cx // TILE_SIZE)
                    r = int(y // TILE_SIZE)
                    if 0 <= r < len(tile_map) and 0 <= c < len(tile_map[0]) and tile_map[r][c] not in [1, 2, 3]:
                        self.spike_positions_v.append(pygame.math.Vector2(cx, y))
                    y += int(strip_w * 0.85)
            is_attack = not is_attack
        
        self.spike_positions_h = []
        is_attack = not inverse
        for y_start in range(0, room_h, strip_w):
            if is_attack:
                cy = y_start + self.spike_radius
                x = self.spike_radius
                while x < room_w:
                    c = int(x // TILE_SIZE)
                    r = int(cy // TILE_SIZE)
                    if 0 <= r < len(tile_map) and 0 <= c < len(tile_map[0]) and tile_map[r][c] not in [1, 2, 3]:
                        self.spike_positions_h.append(pygame.math.Vector2(x, cy))
                    x += int(strip_w * 0.85)
            is_attack = not is_attack
    
    def _get_phase2_frame(self):
        cycle = self.phase2_anim_cycle
        f = int(self.phase2_anim_frame)
        if cycle == 0:
            return min(f, 11)
        elif cycle == 1:
            seq = [10, 9, 8, 7, 6, 5, 4, 3, 2]
            return seq[min(f, len(seq) - 1)]
        else:
            seq = [2, 3, 4, 5, 6, 7, 8, 9, 10]
            return seq[min(f, len(seq) - 1)]
    
    def draw(self, surface, cam_x, cam_y, player_pos=None):
        draw_x, draw_y = int(self.pos.x - cam_x), int(self.pos.y - cam_y)
        # 꼬깔콘 시각적 Y 오프셋 + 흔들림 적용
        if self.type == 'corn_cone':
            draw_y += int(getattr(self, 'visual_offset_y', 0))
            if self.state == 'STUCK':
                draw_x += int(getattr(self, 'shake_offset', 0))
        if self.type == 'gravity_book' and hasattr(self, 'float_timer'):
            draw_y += int(math.sin(self.float_timer * 2.0) * 10)
        if self.type == 'forbidden_book' and hasattr(self, 'float_timer'):
            draw_y += int(math.sin(self.float_timer * 2.0) * 10)
        
        if self.type == 'boss' and not getattr(self, 'death_fly_active', False) and self.boss_phase == 2 and getattr(self, 'boss_laser_active', False) and getattr(self, 'boss_laser_wall_hit', None) and getattr(self, 'boss_laser_dir', pygame.math.Vector2(0,0)).length() > 0:
            laser_key = f'laser_beam_{self.boss_laser_frame_index + 1}'
            laser_img_template = IMAGES.get(laser_key)
            laser_dir_norm = self.boss_laser_dir.normalize()
            laser_dist = self.pos.distance_to(self.boss_laser_wall_hit)
            
            glow_surf = pygame.Surface((int(laser_dist) + 20, self.boss_laser_width * 2 + 10), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (255, 30, 30, 90), (0, self.boss_laser_width - 15, int(laser_dist) + 20, 30))
            pygame.draw.rect(glow_surf, (255, 100, 50, 50), (0, self.boss_laser_width - 30, int(laser_dist) + 20, 60))
            glow_angle = math.degrees(math.atan2(-self.boss_laser_dir.y, self.boss_laser_dir.x))
            rot_glow = pygame.transform.rotate(glow_surf, glow_angle)
            glow_cx = int((self.pos.x + self.boss_laser_dir.x * laser_dist / 2) - cam_x)
            glow_cy = int((self.pos.y + self.boss_laser_dir.y * laser_dist / 2) - cam_y)
            surface.blit(rot_glow, rot_glow.get_rect(center=(glow_cx, glow_cy)))
            
            if laser_img_template:
                img_h = laser_img_template.get_height()
                if img_h > 0:
                    num_tiles = int(laser_dist / img_h) + 1
                    laser_rot = -self.boss_laser_angle - 90
                    start_offset = self.radius
                    for ti in range(num_tiles):
                        tile_center = self.pos + laser_dir_norm * (start_offset + ti * img_h + img_h / 2)
                        if tile_center.distance_to(self.pos) > laser_dist + img_h:
                            break
                        tdx = int(tile_center.x - cam_x)
                        tdy = int(tile_center.y - cam_y)
                        rot_laser = pygame.transform.rotate(laser_img_template, laser_rot)
                        surface.blit(rot_laser, rot_laser.get_rect(center=(tdx, tdy)))

        if self.type == 'boss' and not getattr(self, 'death_fly_active', False) and self._warning_ready and self.attack_pattern == 0 and hasattr(self, 'next_attack_offset'):
            progress = 1.0 - (max(0, getattr(self, 'attack_timer', 5.0)) / self.attack_warning_duration)
            alpha = int(40 + 200 * progress)
            for i in range(8):
                angle = (2 * math.pi / 8) * i + self.next_attack_offset
                line_len = 1200
                line_w = 54
                line_surf = pygame.Surface((line_len, line_w), pygame.SRCALPHA)
                for seg in range(0, line_len, 6):
                    seg_ratio = seg / max(1, line_len)
                    seg_alpha = int(alpha * (1.0 - seg_ratio * 0.7))
                    pygame.draw.rect(line_surf, (255, 50, 50, seg_alpha), (seg, line_w // 2 - line_w // 4, 6, line_w // 2))
                rot_angle = math.degrees(math.atan2(math.sin(angle), math.cos(angle)))
                rot_surf = pygame.transform.rotate(line_surf, -rot_angle)
                start_x = self.pos.x + math.cos(angle) * 40
                start_y = self.pos.y + math.sin(angle) * 40
                center_pos = pygame.math.Vector2(start_x + math.cos(angle) * line_len / 2, start_y + math.sin(angle) * line_len / 2)
                draw_cx = int(center_pos.x - cam_x)
                draw_cy = int(center_pos.y - cam_y)
                rot_rect = rot_surf.get_rect(center=(draw_cx, draw_cy))
                surface.blit(rot_surf, rot_rect)

        if self.type == 'boss' and not getattr(self, 'death_fly_active', False) and self.spike_state != 'none':
            spike_r = self.spike_radius
            if self.spike_state == 'vertical_warn':
                progress = max(0.0, min(1.0, 1.0 - self.spike_timer / 0.6))
                warn_alpha = int(30 + 200 * progress)
                for sp in self.spike_positions_v:
                    sx = int(sp.x - cam_x); sy = int(sp.y - cam_y)
                    warn_surf = pygame.Surface((spike_r * 2, spike_r * 2), pygame.SRCALPHA)
                    for ring_r in range(spike_r, 0, -4):
                        r_ratio = 1.0 - (ring_r / spike_r)
                        ring_alpha = int(warn_alpha * (0.3 + 0.7 * r_ratio))
                        pygame.draw.circle(warn_surf, (255, 0, 0, min(255, ring_alpha)), (spike_r, spike_r), ring_r)
                    surface.blit(warn_surf, (sx - spike_r, sy - spike_r))
            elif self.spike_state == 'vertical_fall':
                fall_ratio = min(1.0, self.spike_fall_progress / 400)
                frame_idx = min(int(fall_ratio * 4) + 7, 10)
                corn_key = f'corn_cone_{frame_idx}'
                fall_offset = int(-400 + self.spike_fall_progress)
                for sp in self.spike_positions_v:
                    sx = int(sp.x - cam_x); sy = int(sp.y - cam_y)
                    if corn_key in IMAGES:
                        surface.blit(IMAGES[corn_key], IMAGES[corn_key].get_rect(center=(sx, sy + fall_offset)))
            elif self.spike_state == 'vertical_impact':
                impact_progress = 1.0 - (self.spike_impact_timer / 0.5)
                for sp in self.spike_positions_v:
                    sx = int(sp.x - cam_x); sy = int(sp.y - cam_y)
                    if 'corn_cone_11' in IMAGES:
                        surface.blit(IMAGES['corn_cone_11'], IMAGES['corn_cone_11'].get_rect(center=(sx, sy)))
                    shockwave_r = int(spike_r * (0.5 + 1.0 * impact_progress))
                    shockwave_alpha = int(200 * (1.0 - impact_progress))
                    if shockwave_alpha > 0:
                        shock_surf = pygame.Surface((shockwave_r * 2, shockwave_r * 2), pygame.SRCALPHA)
                        pygame.draw.circle(shock_surf, (255, 200, 50, min(255, shockwave_alpha)), (shockwave_r, shockwave_r), shockwave_r, max(2, int(8 * (1.0 - impact_progress))))
                        inner_r = int(shockwave_r * 0.5)
                        inner_alpha = int(150 * (1.0 - impact_progress))
                        pygame.draw.circle(shock_surf, (255, 255, 200, min(255, inner_alpha)), (shockwave_r, shockwave_r), inner_r)
                        surface.blit(shock_surf, (sx - shockwave_r, sy - shockwave_r))
            elif self.spike_state == 'horizontal_warn':
                progress = max(0.0, min(1.0, 1.0 - self.spike_timer / 0.6))
                warn_alpha = int(30 + 200 * progress)
                for sp in self.spike_positions_h:
                    sx = int(sp.x - cam_x); sy = int(sp.y - cam_y)
                    warn_surf = pygame.Surface((spike_r * 2, spike_r * 2), pygame.SRCALPHA)
                    for ring_r in range(spike_r, 0, -4):
                        r_ratio = 1.0 - (ring_r / spike_r)
                        ring_alpha = int(warn_alpha * (0.3 + 0.7 * r_ratio))
                        pygame.draw.circle(warn_surf, (255, 0, 0, min(255, ring_alpha)), (spike_r, spike_r), ring_r)
                    surface.blit(warn_surf, (sx - spike_r, sy - spike_r))
            elif self.spike_state == 'horizontal_fall':
                fall_ratio = min(1.0, self.spike_fall_progress / 400)
                frame_idx = min(int(fall_ratio * 4) + 7, 10)
                corn_key = f'corn_cone_{frame_idx}'
                fall_offset = int(-400 + self.spike_fall_progress)
                for sp in self.spike_positions_h:
                    sx = int(sp.x - cam_x); sy = int(sp.y - cam_y)
                    if corn_key in IMAGES:
                        surface.blit(IMAGES[corn_key], IMAGES[corn_key].get_rect(center=(sx, sy + fall_offset)))
            elif self.spike_state == 'horizontal_impact':
                impact_progress = 1.0 - (self.spike_impact_timer / 0.5)
                for sp in self.spike_positions_h:
                    sx = int(sp.x - cam_x); sy = int(sp.y - cam_y)
                    if 'corn_cone_11' in IMAGES:
                        surface.blit(IMAGES['corn_cone_11'], IMAGES['corn_cone_11'].get_rect(center=(sx, sy)))
                    shockwave_r = int(spike_r * (0.5 + 1.0 * impact_progress))
                    shockwave_alpha = int(200 * (1.0 - impact_progress))
                    if shockwave_alpha > 0:
                        shock_surf = pygame.Surface((shockwave_r * 2, shockwave_r * 2), pygame.SRCALPHA)
                        pygame.draw.circle(shock_surf, (255, 200, 50, min(255, shockwave_alpha)), (shockwave_r, shockwave_r), shockwave_r, max(2, int(8 * (1.0 - impact_progress))))
                        inner_r = int(shockwave_r * 0.5)
                        inner_alpha = int(150 * (1.0 - impact_progress))
                        pygame.draw.circle(shock_surf, (255, 255, 200, min(255, inner_alpha)), (shockwave_r, shockwave_r), inner_r)
                        surface.blit(shock_surf, (sx - shockwave_r, sy - shockwave_r))

        if self.type == 'boss' and not getattr(self, 'death_fly_active', False) and self.brush_state != 'none':
            for b in self.brushes:
                bpos = b['pos']
                mdir = b['move_dir']
                spos = b['start_pos']
                tdist = b['total_dist']
                draw_bx = int(bpos.x - cam_x)
                draw_by = int(bpos.y - cam_y)
                if self.brush_state == 'WARN':
                    alpha = max(0, min(120, int(120 * (1.0 - self.brush_timer / 0.15))))
                    rect_len = int(tdist)
                    rect_w = 36
                    rect_surf = pygame.Surface((rect_len, rect_w), pygame.SRCALPHA)
                    rect_surf.fill((255, 0, 0, alpha))
                    angle = math.degrees(math.atan2(-mdir.y, mdir.x))
                    rot_surf = pygame.transform.rotate(rect_surf, angle)
                    center_pos = spos + mdir * (rect_len / 2)
                    rcx = int(center_pos.x - cam_x)
                    rcy = int(center_pos.y - cam_y)
                    surface.blit(rot_surf, rot_surf.get_rect(center=(rcx, rcy)))
                elif self.brush_state == 'WARN_LINE':
                    alpha = max(0, min(255, int(255 * (1.0 - self.brush_timer / 0.25))))
                    rect_len = int(tdist)
                    rect_w = 36
                    rect_surf = pygame.Surface((rect_len, rect_w), pygame.SRCALPHA)
                    rect_surf.fill((255, 0, 0, alpha))
                    angle = math.degrees(math.atan2(-mdir.y, mdir.x))
                    rot_surf = pygame.transform.rotate(rect_surf, angle)
                    center_pos = spos + mdir * (rect_len / 2)
                    rcx = int(center_pos.x - cam_x)
                    rcy = int(center_pos.y - cam_y)
                    surface.blit(rot_surf, rot_surf.get_rect(center=(rcx, rcy)))
                elif self.brush_state == 'ATTACK':
                    if b['active']:
                        if 'toothbrush_4' in IMAGES:
                            img = IMAGES['toothbrush_4']
                            angle = math.degrees(math.atan2(-mdir.y, mdir.x))
                            rot_img = pygame.transform.rotate(img, angle)
                            surface.blit(rot_img, rot_img.get_rect(center=(draw_bx, draw_by)))
                        else:
                            pygame.draw.circle(surface, (200, 200, 200), (draw_bx, draw_by), 18)
                            pygame.draw.circle(surface, (150, 150, 150), (draw_bx, draw_by), 18, 3)
                elif self.brush_state == 'DISAPPEAR':
                    alpha = max(0, min(255, int(255 * (self.brush_timer / 0.08))))
                    if 'toothbrush_4' in IMAGES:
                        img = IMAGES['toothbrush_4'].copy()
                        img.set_alpha(alpha)
                        angle = math.degrees(math.atan2(-mdir.y, mdir.x))
                        rot_img = pygame.transform.rotate(img, angle)
                        surface.blit(rot_img, rot_img.get_rect(center=(draw_bx, draw_by)))

        if self.type == 'eraser' and self.state == 'PRECAST' and self.attack_target:
            tx, ty = int(self.attack_target.x - cam_x), int(self.attack_target.y - cam_y)
            # 기준 시간을 0.8로 맞추고, 투명도 값이 0~255를 벗어나지 않게 안전하게 제한합니다.
            alpha = max(0, min(255, int(255 * (1.0 - self.timer / 0.7))))
            rect_surf = pygame.Surface((96, 96), pygame.SRCALPHA)
            rect_surf.fill((255, 0, 0, alpha))
            surface.blit(rect_surf, (tx - 48, ty - 48))
            
        elif self.type == 'chalk' and self.state == 'PRECAST':
            alpha = max(0, min(255, int(255 * (1.0 - self.timer / 0.5))))
            # 분필 사거리(270)와 두께(두께는 취향에 맞게 조정 가능, 여기선 48) 설정
            rect_len = self.dash_max_distance if hasattr(self, 'dash_max_distance') else 270
            rect_surf = pygame.Surface((rect_len, 48), pygame.SRCALPHA)
            rect_surf.fill((255, 0, 0, alpha))
            
            angle = math.degrees(math.atan2(-self.dash_dir.y, self.dash_dir.x))
            rot_surf = pygame.transform.rotate(rect_surf, angle)
            
            # 분필은 제자리에서 앞으로 뻗어나가므로 중심점을 앞으로 이동 계산
            center_pos = self.pos + self.dash_dir * (rect_len / 2)
            draw_cx = int(center_pos.x - cam_x)
            draw_cy = int(center_pos.y - cam_y)
            rot_rect = rot_surf.get_rect(center=(draw_cx, draw_cy))
            surface.blit(rot_surf, rot_rect)
            
        elif self.type == 'syringe' and self.state == 'PRECAST':
            # 주사기 돌진 경고: 빨간 범위 표시
            alpha = max(0, min(255, int(255 * (1.0 - self.timer / 0.5))))
            rect_len = self.dash_max_distance  # 맵 끝까지 동적으로 표시
            rect_surf = pygame.Surface((rect_len, 24), pygame.SRCALPHA)
            rect_surf.fill((255, 0, 0, alpha))
            
            if self.dash_dir.length() > 0:
                angle = math.degrees(math.atan2(-self.dash_dir.y, self.dash_dir.x))
            else:
                angle = 0
            rot_surf = pygame.transform.rotate(rect_surf, angle)
            
            center_pos = self.pos + self.dash_dir * (rect_len / 2)
            draw_cx = int(center_pos.x - cam_x)
            draw_cy = int(center_pos.y - cam_y)
            rot_rect = rot_surf.get_rect(center=(draw_cx, draw_cy))
            surface.blit(rot_surf, rot_rect)

        elif self.type == 'router' and self.state == 'PRECAST':
            if self.timer < 0.3:
                progress = 1.0 - (self.timer / 0.3)
                num_circles = 3
                for i in range(num_circles):
                    r = int(20 + (i + 1) * 12 * progress)
                    alpha = int(180 * progress * (1.0 - i * 0.25))
                    circ_surf_size = r * 2 + 4
                    circ_surf = pygame.Surface((circ_surf_size, circ_surf_size), pygame.SRCALPHA)
                    pygame.draw.circle(circ_surf, (60, 140, 255, min(255, max(0, alpha))), (circ_surf_size // 2, circ_surf_size // 2), r, max(2, int(5 * progress)))
                    surface.blit(circ_surf, (draw_x - circ_surf_size // 2, draw_y - circ_surf_size // 2))

        elif self.type == 'corn_cone' and self.state == 'HOVER':
            # 꼬깔콘 낙하 예고: 연한 빨강 → 중앙부터 진해짐 → 전체 진해짐
            if self.target_landing_pos:
                progress = min(1.0, self.hover_timer / self.hover_duration)
                tx = int(self.target_landing_pos.x - cam_x)
                ty = int(self.target_landing_pos.y - cam_y)
                spike_r = self.spike_radius
                warn_surf = pygame.Surface((spike_r * 2, spike_r * 2), pygame.SRCALPHA)
                for r in range(spike_r, 0, -3):
                    r_ratio = 1.0 - (r / spike_r)  # 중앙=1, 바깥=0
                    alpha = int(30 + 200 * progress * r_ratio)
                    pygame.draw.circle(warn_surf, (255, 0, 0, min(255, alpha)), (spike_r, spike_r), r)
                surface.blit(warn_surf, (tx - spike_r, ty - spike_r))

        elif self.type == 'corn_cone' and self.state == 'IMPACT':
            # 꼬깔콘 착지 충격파: 확장되는 원형 이펙트
            impact_progress = 1.0 - (self.impact_timer / 0.6)  # 0→1
            shockwave_r = int(self.spike_radius * (0.5 + 1.0 * impact_progress))
            shockwave_alpha = int(200 * (1.0 - impact_progress))
            if shockwave_alpha > 0:
                shock_surf = pygame.Surface((shockwave_r * 2, shockwave_r * 2), pygame.SRCALPHA)
                # 바깥쪽 링
                pygame.draw.circle(shock_surf, (255, 200, 50, min(255, shockwave_alpha)), (shockwave_r, shockwave_r), shockwave_r, max(2, int(8 * (1.0 - impact_progress))))
                # 내부 빛
                inner_r = int(shockwave_r * 0.5)
                inner_alpha = int(150 * (1.0 - impact_progress))
                pygame.draw.circle(shock_surf, (255, 255, 200, min(255, inner_alpha)), (shockwave_r, shockwave_r), inner_r)
                surface.blit(shock_surf, (draw_x - shockwave_r, draw_y - shockwave_r))

        elif self.type == 'toothbrush' and self.state == 'PRECAST':
            # 투명도 조절
            alpha = max(0, min(255, int(255 * (1.0 - self.timer / 0.8))))
            
            # 빨간 범위의 길이와 너비(지그재그 폭 + 몬스터 크기)
            rect_len = self.dash_max_distance
            rect_wid = self.zigzag_width * 2 + self.radius * 2 
            
            rect_surf = pygame.Surface((rect_len, rect_wid), pygame.SRCALPHA)
            rect_surf.fill((255, 0, 0, alpha))
            
            # 몬스터가 바라보는 방향으로 직사각형 회전
            angle = math.degrees(math.atan2(-self.dash_dir.y, self.dash_dir.x))
            rot_surf = pygame.transform.rotate(rect_surf, angle)
            
            # 사각형의 중심점 맞추기 (몬스터 앞쪽으로 길게 뻗어나가게)
            center_pos = self.pos + self.dash_dir * (rect_len / 2)
            draw_cx = int(center_pos.x - cam_x)
            draw_cy = int(center_pos.y - cam_y)
            rot_rect = rot_surf.get_rect(center=(draw_cx, draw_cy))
            
            surface.blit(rot_surf, rot_rect)

        # 👇 체육관 몬스터 경고 효과
        elif self.type == 'corn_cone' and self.state == 'PRECAST':
            # 꼬깔콘 낙하 준비: 머리 위에 "!" 표시 (반짝임)
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.008))
            ex_alpha = int(180 + 75 * pulse)
            ex_font = get_korean_font(36, bold=True)
            ex_surf = ex_font.render("!", True, (255, 60, 60))
            ex_surf.set_alpha(ex_alpha)
            ex_rect = ex_surf.get_rect(center=(draw_x, draw_y - 50))
            surface.blit(ex_surf, ex_rect)

        elif self.type == 'soccer_ball' and self.state == 'PRECAST':
            # 축구공 조준 경고: 진한 빨간색 직선 (벽까지 거리, 도탄 범위는 표시 안함)
            progress = 1.0 - (self.timer / self.charge_time)
            aim_len = max(10, getattr(self, 'warning_range', 800))
            alpha = int(80 + 175 * progress)
            line_w = self.radius * 2  # 이미지 판정에 맞춤
            line_surf = pygame.Surface((aim_len, line_w), pygame.SRCALPHA)
            for seg in range(0, aim_len, 4):
                seg_progress = seg / max(1, aim_len)
                seg_alpha = int(alpha * (0.5 + 0.5 * seg_progress))
                pygame.draw.rect(line_surf, (255, 0, 0, seg_alpha), (seg, 0, 4, line_w))
            angle = math.degrees(math.atan2(-self.aim_dir.y, self.aim_dir.x))
            rot_surf = pygame.transform.rotate(line_surf, angle)
            center_pos = self.pos + self.aim_dir * (aim_len / 2)
            draw_cx = int(center_pos.x - cam_x)
            draw_cy = int(center_pos.y - cam_y)
            rot_rect = rot_surf.get_rect(center=(draw_cx, draw_cy))
            surface.blit(rot_surf, rot_rect)

        elif self.type == 'badminton_racket' and self.state == 'AIM':
            # 배드민턴채 조준 경고: 처음부터 최대 사거리 표시, 연한 빨강→진한 빨강으로 점차 진해짐
            progress = 1.0 - (self.timer / 1.5)  # 0→1로 진행
            shuttle_range = getattr(self, 'shuttle_range', 700)
            aim_dir = getattr(self, 'aim_dir', pygame.math.Vector2(1, 0))
            # 처음부터 최대 사거리로 표시
            current_len = shuttle_range
            # 전체 alpha가 progress에 따라 진해짐 (연한→진한)
            alpha = int(30 + 200 * progress)
            line_surf = pygame.Surface((current_len, 30), pygame.SRCALPHA)
            # 그라데이션 효과: 가까운 곳은 연하게, 먼 곳은 진하게
            for seg in range(0, current_len, 4):
                seg_progress = seg / max(1, current_len)
                seg_alpha = int(alpha * (0.3 + 0.7 * seg_progress))
                pygame.draw.rect(line_surf, (255, 0, 0, seg_alpha), (seg, 0, 4, 30))
            angle = math.degrees(math.atan2(-aim_dir.y, aim_dir.x))
            rot_surf = pygame.transform.rotate(line_surf, angle)
            center_pos = self.pos + aim_dir * (current_len / 2)
            draw_cx = int(center_pos.x - cam_x)
            draw_cy = int(center_pos.y - cam_y)
            rot_rect = rot_surf.get_rect(center=(draw_cx, draw_cy))
            surface.blit(rot_surf, rot_rect)

        # (Enemy 클래스의 draw 내부)
        img_key = None
        if self.type in ['eraser', 'chalk', 'pencil', 'soap', 'toothpaste', 'toothbrush', 'bandage', 'pill', 'syringe', 'pill_boss', 'red_pill', 'blue_pill', 'corn_cone', 'soccer_ball', 'badminton_racket', 'badminton_shuttle', 'food_tray', 'steel_scrubber', 'spoon_chopsticks', 'keyboard', 'router', 'computer_mouse', 'mine_book', 'gravity_book', 'forbidden_book', 'gamble_book']:
            if self.state == 'PRECAST' and self.type not in ('soccer_ball', 'corn_cone', 'router', 'keyboard', 'gamble_book'):
                img_key = f"{self.type}_2"
            elif self.type == 'keyboard' and self.state == 'TYPING':
                img_key = f"{self.type}_2"
            elif self.type == 'keyboard' and self.state == 'REST':
                img_key = f"{self.type}_3"
            elif self.type == 'toothpaste' and self.state == 'FIRE':
                img_key = f"{self.type}_3"
            elif self.type == 'chalk' and self.state == 'DASH':
                img_key = f"{self.type}_3"
            elif self.type == 'toothbrush' and self.state == 'DASH':
                img_key = f"{self.type}_4"
            elif self.type == 'eraser' and self.state == 'COOLDOWN' and self.timer > 1.0:
                img_key = f"{self.type}_3"
            elif self.type == 'pencil' and getattr(self, 'attack_cooldown', 0) > 1.0:
                img_key = f"{self.type}_3"
            elif self.type == 'pill' and self.state == 'FIRE':
                img_key = f"{self.type}_3"
            elif self.type == 'syringe' and self.state == 'DASH':
                img_key = f"{self.type}_3"
            # 👇 체육관 몬스터 상태별 이미지
            elif self.type == 'corn_cone' and self.state == 'PRECAST':
                # PRECAST: 2초 동안 _1~_4 순차 (각 0.5초)
                frame_idx = min(int(self.anim_frame / 0.5) + 1, 4)
                img_key = f"{self.type}_{frame_idx}"
            elif self.type == 'corn_cone' and self.state == 'RISE':
                # RISE: _5 0.7초, _6 그 후 화면 밖까지
                if self.anim_frame < 0.7:
                    img_key = f"{self.type}_5"
                else:
                    img_key = f"{self.type}_6"
            elif self.type == 'corn_cone' and self.state == 'HOVER':
                img_key = None  # 화면 밖에 있으므로 그리지 않음
            elif self.type == 'corn_cone' and self.state == 'FALL':
                # FALL: _7~_10을 낙하 진행도에 따라 분배
                progress = max(0, min(1, (self.visual_offset_y + 700) / 700))
                frame_idx = min(int(progress * 4) + 7, 10)
                img_key = f"{self.type}_{frame_idx}"
            elif self.type == 'corn_cone' and self.state == 'IMPACT':
                img_key = f"{self.type}_11"
            elif self.type == 'corn_cone' and self.state == 'STUCK':
                img_key = f"{self.type}_12"
            elif self.type == 'soccer_ball' and self.state == 'PRECAST':
                # PRECAST: 2.5초 동안 _2~_6 순차 (각 0.5초)
                frame_idx = min(int(self.spin_frame / 0.5) + 2, 6)
                img_key = f"{self.type}_{frame_idx}"
            elif self.type == 'soccer_ball' and self.state == 'DASH':
                img_key = f"{self.type}_7"
            elif self.type == 'soccer_ball' and self.state == 'STUNNED':
                # STUNNED: 7.5초 동안 _8~_10 순차 (각 2.5초)
                frame_idx = min(int(self.spin_frame / 2.5) + 8, 10)
                img_key = f"{self.type}_{frame_idx}"
            elif self.type == 'badminton_racket' and self.state == 'AIM':
                img_key = f"{self.type}_1"  # 조준 중: 기본 이미지
            elif self.type == 'spoon_chopsticks' and self.state == 'SLAM':
                progress = min(1.0, self.anim_frame / 0.5)
                alpha = int(40 + 215 * progress)
                slam_r = self.slam_radius
                dir_to_player = pygame.math.Vector2(1, 0)
                if player_pos:
                    dp = player_pos - self.pos
                    if dp.length() > 0: dir_to_player = dp.normalize()
                slam_cx = int(self.pos.x + dir_to_player.x * self.slam_offset - cam_x)
                slam_cy = int(self.pos.y + dir_to_player.y * self.slam_offset - cam_y)
                warn_surf = pygame.Surface((slam_r * 2, slam_r * 2), pygame.SRCALPHA)
                fill_r = int(slam_r * progress)
                if fill_r > 0:
                    pygame.draw.circle(warn_surf, (255, 0, 0, alpha), (slam_r, slam_r), fill_r)
                pygame.draw.circle(warn_surf, (255, 0, 0, 100), (slam_r, slam_r), slam_r, 2)
                surface.blit(warn_surf, (slam_cx - slam_r, slam_cy - slam_r))
                frame_idx = min(int(self.anim_frame / 0.17) + 2, 4)
                img_key = f"{self.type}_{frame_idx}"
            elif self.type == 'badminton_racket' and self.state == 'SWING':
                # 스윙 애니메이션: _2 ~ _7 순차 재생
                swing_idx = min(int(self.swing_frame) + 2, 7)
                img_key = f"{self.type}_{swing_idx}"
            elif self.type == 'badminton_racket' and self.state == 'FIRE':
                img_key = f"{self.type}_7"  # 발사 순간: 마지막 프레임
            elif self.type == 'badminton_racket' and self.state == 'COOLDOWN':
                img_key = f"{self.type}_1"  # 쿨타임: 기본
            elif self.type == 'food_tray' and self.state == 'WASHING':
                wash_elapsed = self.wash_duration - self.wash_timer
                frame_idx = min(int(wash_elapsed / 1.0) + 2, 6)
                img_key = f"{self.type}_{frame_idx}"
            elif self.type == 'steel_scrubber' and self.state == 'SPIN':
                frame_idx = min(int(self.anim_frame / 0.3) + 2, 11)
                img_key = f"{self.type}_{frame_idx}"
            elif self.type == 'steel_scrubber' and self.state == 'RECOVER':
                frame_idx = min(int(self.anim_frame / 1.5) + 12, 14)
                img_key = f"{self.type}_{frame_idx}"
            elif self.type == 'spoon_chopsticks' and self.state == 'IMPACT':
                img_key = f"{self.type}_4"
            elif self.type == 'spoon_chopsticks' and self.state == 'IMPACT_HOLD':
                img_key = f"{self.type}_5"
            elif self.type == 'gravity_book':
                if self.state == 'IDLE':
                    img_key = f"{self.type}_1"
                elif self.state == 'PRECAST':
                    frame_idx = min(int(self.anim_frame / 0.5) + 2, 3)
                    img_key = f"{self.type}_{frame_idx}"
                else:
                    img_key = f"{self.type}_4"
            elif self.type == 'forbidden_book':
                if self.state == 'IDLE':
                    img_key = f"{self.type}_1"
                elif self.state == 'PRECAST':
                    frame_idx = min(int(self.anim_frame / 0.5) + 2, 3)
                    img_key = f"{self.type}_{frame_idx}"
                else:
                    img_key = f"{self.type}_4"
            elif self.type == 'bandage' and self.state == 'PRECAST':
                img_key = f"{self.type}_2"  # 붕대_2: 공격 준비 (반짝임)
            elif self.type == 'pill_boss':
                if getattr(self, 'is_invincible', False):
                    img_key = 'pill_boss_1'  # 무적 상태: 알약_1
                else:
                    img_key = 'pill_boss_2'  # 무적 해제: 알약_2
                
            elif self.type == 'toothbrush' and getattr(self, 'state', '') == 'FLEE':
                if getattr(self, 'flee_timer', 0) <= 1.0:
                    img_key = f"{self.type}_3"  # 👈 칫솔_2 대신 칫솔_3을 사용하도록 수정!
                else:
                    img_key = f"{self.type}_1"
                    
            else:
                img_key = f"{self.type}_1"
        
        if img_key and img_key in IMAGES:
            img = IMAGES[img_key]
            
            if player_pos:
                # 배드민턴공 몬스터는 이미지를 상하 반전
                if self.type == 'badminton_shuttle':
                    img = pygame.transform.flip(img, True, False)
                
                is_fleeing = getattr(self, 'state', '') == 'FLEE'
                flee_time_left = getattr(self, 'flee_timer', 0)
                
                if self.type == 'corn_cone':
                    pass
                elif self.type == 'router':
                    pass
                elif self.type == 'keyboard':
                    pass
                elif self.type == 'computer_mouse':
                    pass
                elif self.type == 'gravity_book':
                    pass
                elif self.type == 'forbidden_book':
                    pass
                elif self.type == 'syringe' and self.state == 'DASH':
                    pass
                elif self.type == 'soccer_ball' and self.state == 'DASH':
                    pass
                elif self.type == 'food_tray':
                    if player_pos.x >= self.pos.x:
                        img = pygame.transform.flip(img, True, False)
                elif self.type == 'spoon_chopsticks' and self.state in ('FLEE', 'SHAKING'):
                    if player_pos.x > self.pos.x:
                        img = pygame.transform.flip(img, True, False)
                elif self.type == 'mine_book':
                    if hasattr(self, 'move_dir') and self.move_dir.x < 0:
                        img = pygame.transform.flip(img, True, False)
                elif is_fleeing and flee_time_left > 1.0:
                    if player_pos.x >= self.pos.x:
                        img = pygame.transform.flip(img, True, False)
                else:
                    if player_pos.x < self.pos.x:
                        img = pygame.transform.flip(img, True, False)
            
            if self.type == 'computer_mouse':
                img = pygame.transform.rotate(img, self.facing_angle)
            elif self.type == 'gamble_book':
                img = pygame.transform.rotate(img, self.spin_angle)
            elif self.type == 'syringe' and self.state == 'DASH' and hasattr(self, 'dash_dir') and self.dash_dir.length() > 0:
                angle = math.degrees(math.atan2(-self.dash_dir.y, self.dash_dir.x))
                img = pygame.transform.rotate(img, angle)
            elif self.type == 'soccer_ball' and self.state == 'DASH' and hasattr(self, 'dash_dir') and self.dash_dir.length() > 0:
                angle = math.degrees(math.atan2(-self.dash_dir.y, self.dash_dir.x))
                img = pygame.transform.rotate(img, angle)
            
            img_rect = img.get_rect(center=(draw_x, draw_y))
            
            # 👈 마스크 기반 충돌 판정용 마스크 캐싱
            self._cached_img = img
            self._cached_mask = pygame.mask.from_surface(img)
            
            # 👇 [수정됨] 하얀색 반짝임 조건을 묶어서 처리합니다.
            show_outline = False
            if getattr(self, 'state', '') == 'PRECAST':
                show_outline = True
            # 칫솔이 도망 중이고 남은 시간이 1초 이하일 때도 반짝이도록 추가
            elif self.type == 'toothbrush' and getattr(self, 'state', '') == 'FLEE' and getattr(self, 'flee_timer', 0) <= 1.0:
                show_outline = True
            # 배드민턴채 조준(AIM) 상태일 때도 반짝임
            elif self.type == 'badminton_racket' and getattr(self, 'state', '') == 'AIM':
                show_outline = True
            # 꼬깔콘 PRECAST 상태일 때도 반짝임
            elif self.type == 'corn_cone' and getattr(self, 'state', '') == 'PRECAST':
                show_outline = True
            # 축구공 PRECAST(스핀) 상태일 때도 반짝임
            elif self.type == 'soccer_ball' and getattr(self, 'state', '') == 'PRECAST':
                show_outline = True
            elif self.type == 'steel_scrubber' and getattr(self, 'state', '') == 'PRECAST':
                show_outline = True
            elif self.type == 'spoon_chopsticks' and getattr(self, 'state', '') == 'PRECAST':
                show_outline = True
            elif self.type == 'keyboard' and getattr(self, 'state', '') == 'PRECAST':
                show_outline = True
            elif self.type == 'gravity_book' and getattr(self, 'state', '') == 'PRECAST':
                show_outline = True
            elif self.type == 'forbidden_book' and getattr(self, 'state', '') == 'PRECAST':
                show_outline = True
            elif self.type == 'mine_book' and getattr(self, 'mine_pre_place', False):
                show_outline = True
            elif self.type == 'gamble_book' and getattr(self, 'state', '') == 'PRECAST':
                show_outline = True

            if show_outline:
                pulse = abs(math.sin(pygame.time.get_ticks() * 0.025))
                alpha = int(180 * pulse)
                mask = pygame.mask.from_surface(img)
                mask_surf = mask.to_surface(setcolor=(255, 255, 255, alpha), unsetcolor=(0, 0, 0, 0))
                for dx, dy in [(-3,0), (3,0), (0,-3), (0,3), (-2,0), (2,0), (0,-2), (0,2), (-1,-1), (1,-1), (-1,1), (1,1), (-2,-2), (2,-2), (-2,2), (2,2)]:
                    surface.blit(mask_surf, (img_rect.x + dx, img_rect.y + dy))
            
            if self.flash_timer > 0:
                flash = img.copy()
                flash.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_ADD)
                surface.blit(flash, img_rect)
            else:
                surface.blit(img, img_rect)
            
            # 👇 컴퓨터실 마우스 레이저 빔 그리기
            if self.type == 'computer_mouse' and self.laser_active and self.laser_wall_hit and self.laser_dir.length() > 0:
                laser_key = f'laser_beam_{self.laser_frame_index + 1}'
                laser_img_template = IMAGES.get(laser_key)
                laser_dir_norm = self.laser_dir.normalize()
                laser_dist = self.pos.distance_to(self.laser_wall_hit)
                
                glow_surf = pygame.Surface((int(laser_dist) + 20, self.laser_width * 2 + 10), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (255, 30, 30, 90), (0, self.laser_width - 15, int(laser_dist) + 20, 30))
                pygame.draw.rect(glow_surf, (255, 100, 50, 50), (0, self.laser_width - 30, int(laser_dist) + 20, 60))
                glow_angle = math.degrees(math.atan2(-self.laser_dir.y, self.laser_dir.x))
                rot_glow = pygame.transform.rotate(glow_surf, glow_angle)
                glow_cx = int((self.pos.x + self.laser_dir.x * laser_dist / 2) - cam_x)
                glow_cy = int((self.pos.y + self.laser_dir.y * laser_dist / 2) - cam_y)
                surface.blit(rot_glow, rot_glow.get_rect(center=(glow_cx, glow_cy)))
                
                if laser_img_template:
                    img_h = laser_img_template.get_height()
                    if img_h > 0:
                        num_tiles = int(laser_dist / img_h) + 1
                        laser_rot = self.facing_angle
                        start_offset = self.radius
                        for ti in range(num_tiles):
                            tile_center = self.pos + laser_dir_norm * (start_offset + ti * img_h + img_h / 2)
                            if tile_center.distance_to(self.pos) > laser_dist + img_h:
                                break
                            tdx = int(tile_center.x - cam_x)
                            tdy = int(tile_center.y - cam_y)
                            rot_laser = pygame.transform.rotate(laser_img_template, laser_rot)
                            surface.blit(rot_laser, rot_laser.get_rect(center=(tdx, tdy)))
            
            if self.type == 'forbidden_book' and getattr(self, 'is_real', False) and self.state == 'ACTIVE' and hasattr(self, '_fb_blue_alpha') and self._fb_blue_alpha > 0.3:
                pulse = abs(math.sin(pygame.time.get_ticks() * 0.01))
                if img_key and img_key in IMAGES:
                    gold_img = IMAGES[img_key].copy()
                    gold_img.fill((80, 60, 0, 255), special_flags=pygame.BLEND_RGB_ADD)
                    surface.blit(gold_img, gold_img.get_rect(center=(draw_x, draw_y)))

            # 축구공 기절 진입 시 폭발 이펙트 (이미지 위에 하얀 원 오버레이)
            if self.type == 'soccer_ball' and self.state == 'STUNNED' and getattr(self, 'stun_flash_timer', 0) > 0:
                ratio = self.stun_flash_timer / 0.5
                exp_radius = int(80 * ratio)
                exp_alpha = int(220 * ratio)
                exp_surf = pygame.Surface((exp_radius * 2, exp_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(exp_surf, (255, 255, 255, exp_alpha), (exp_radius, exp_radius), exp_radius)
                surface.blit(exp_surf, (draw_x - exp_radius, draw_y - exp_radius))
            
            # ✨ [새로 추가됨] 칫솔 1초 경고 시 느낌표(!) 띄우기
            if self.type == 'toothbrush' and getattr(self, 'state', '') == 'FLEE' and getattr(self, 'flee_timer', 0) <= 1.0:
                excl_font = get_korean_font(40, bold=True)
                in_surf = excl_font.render("!", True, (255, 50, 50))  # 빨간색 느낌표
                out_surf = excl_font.render("!", True, (255, 255, 255)) # 하얀색 테두리
                
                # 위아래로 통통 튀는 애니메이션 효과
                bounce = math.sin(pygame.time.get_ticks() * 0.02) * 5
                excl_y = draw_y - self.radius - 40 + bounce
                
                # 하얀 테두리를 먼저 깔고 위에 빨간 느낌표 덮기
                for dx, dy in [(-1,-1), (1,-1), (-1,1), (1,1)]:
                    surface.blit(out_surf, out_surf.get_rect(center=(draw_x + dx, excl_y + dy)))
                surface.blit(in_surf, in_surf.get_rect(center=(draw_x, excl_y)))

            if self.type == 'spoon_chopsticks' and self.state == 'CHASE':
                excl_font = get_korean_font(40, bold=True)
                in_surf = excl_font.render("!", True, (255, 50, 50))
                out_surf = excl_font.render("!", True, (255, 255, 255))
                bounce = math.sin(pygame.time.get_ticks() * 0.02) * 5
                excl_y = draw_y - self.radius - 40 + bounce
                for dx, dy in [(-1,-1), (1,-1), (-1,1), (1,1)]:
                    surface.blit(out_surf, out_surf.get_rect(center=(draw_x + dx, excl_y + dy)))
                surface.blit(in_surf, in_surf.get_rect(center=(draw_x, excl_y)))

            if self.type == 'keyboard' and self.state == 'TYPING' and self.current_word_idx < len(self.words_to_type):
                word = self.words_to_type[self.current_word_idx]
                typed_part = word[:self.typed_chars]
                remaining_part = word[self.typed_chars:]
                try:
                    kb_font = get_korean_font(22, bold=True) # 변수명 변경
                    if typed_part:
                        typed_surf = kb_font.render(typed_part, True, (255, 255, 255))
                    else:
                        typed_surf = pygame.Surface((0, kb_font.get_height()), pygame.SRCALPHA)
                    remain_surf = kb_font.render(remaining_part, True, (100, 100, 100)) if remaining_part else pygame.Surface((0, kb_font.get_height()), pygame.SRCALPHA)
                    total_w = typed_surf.get_width() + remain_surf.get_width()
                    text_x = draw_x - total_w // 2
                    text_y = draw_y - self.radius - 50
                    surface.blit(typed_surf, (text_x, text_y))
                    surface.blit(remain_surf, (text_x + typed_surf.get_width(), text_y))
                except: pass

            if self.type == 'keyboard' and self.state == 'REST':
                try:
                    kb_font = get_korean_font(20, bold=True) # 변수명 변경
                    shake = random.randint(-2, 2)
                    err_surf = kb_font.render("뭐 쓰지", True, (255, 80, 80))
                    err_out = kb_font.render("뭐 쓰지", True, (80, 0, 0))
                    err_y = draw_y - self.radius - 28
                    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                        surface.blit(err_out, err_out.get_rect(center=(draw_x + dx + shake, err_y + dy)))
                    surface.blit(err_surf, err_surf.get_rect(center=(draw_x + shake, err_y)))
                except: pass

            if self.type == 'gamble_book':
                for db in self.dice_bullets:
                    db.draw(surface, cam_x, cam_y)
                for md in self.mini_dices:
                    md.draw(surface, cam_x, cam_y)

        # 🎯 여기서부터 중요! 맨 위 if와 정확히 줄을 맞춥니다.
        # 이미지가 없는 경우 기본 원형으로 그리기 (보건실 몬스터 포함)
        elif self.type in ['normal', 'boss', 'bandage', 'pill', 'syringe', 'pill_boss', 'red_pill', 'blue_pill', 'badminton_shuttle']:
            boss_dlg_imgs = IMAGES.get('boss_dialogue', [])
            boss_p1_imgs = IMAGES.get('boss_phase1', [])
            if self.type == 'boss' and getattr(self, 'death_fly_hit_wall', False):
                down_img = IMAGES.get('boss_down_flip' if not self.death_fly_facing_right else 'boss_down')
                if down_img:
                    for ghost in self.death_afterimages:
                        ghost['timer'] -= 1.0/60.0
                    self.death_afterimages = [g for g in self.death_afterimages if g['timer'] > 0]
                    for ghost in self.death_afterimages:
                        alpha = max(0, min(120, int(120 * (ghost['timer'] / 0.3))))
                        ghost_img = ghost['img'].copy()
                        ghost_img.set_alpha(alpha)
                        surface.blit(ghost_img, ghost_img.get_rect(center=(int(ghost['pos'].x - cam_x), int(ghost['pos'].y - cam_y))))
                    surface.blit(down_img, down_img.get_rect(center=(draw_x, draw_y)))
                else:
                    pygame.draw.circle(surface, getattr(self, 'color', (255, 60, 60)), (draw_x, draw_y), self.radius)
            elif self.type == 'boss' and getattr(self, 'death_fly_active', False) and not getattr(self, 'death_fly_hit_wall', False):
                p2_imgs = IMAGES.get('boss_phase2', [])
                fly_img = None
                if len(p2_imgs) >= 12:
                    img_idx = self._get_phase2_frame()
                    fly_img = p2_imgs[img_idx]
                elif len(boss_p1_imgs) >= 10:
                    fly_img = boss_p1_imgs[int(self.phase1_anim_frame) % 10]
                if fly_img:
                    self.death_afterimages.append({'pos': pygame.math.Vector2(self.pos.x, self.pos.y), 'img': fly_img.copy(), 'timer': 0.3})
                    for ghost in self.death_afterimages:
                        ghost['timer'] -= 1.0/60.0
                    self.death_afterimages = [g for g in self.death_afterimages if g['timer'] > 0]
                    for ghost in self.death_afterimages:
                        alpha = max(0, min(120, int(120 * (ghost['timer'] / 0.3))))
                        ghost_img = ghost['img'].copy()
                        ghost_img.set_alpha(alpha)
                        surface.blit(ghost_img, ghost_img.get_rect(center=(int(ghost['pos'].x - cam_x), int(ghost['pos'].y - cam_y))))
                    surface.blit(fly_img, fly_img.get_rect(center=(draw_x, draw_y)))
                else:
                    pygame.draw.circle(surface, getattr(self, 'color', (255, 60, 60)), (draw_x, draw_y), self.radius)
            elif self.type == 'boss' and getattr(self, 'dialogue_anim_active', False) and len(boss_dlg_imgs) >= 10:
                max_frame = 10 if self.dialogue_anim_cycle == 0 else 8
                frame_idx = min(int(self.dialogue_anim_frame), max_frame - 1)
                surface.blit(boss_dlg_imgs[frame_idx], boss_dlg_imgs[frame_idx].get_rect(center=(draw_x, draw_y)))
            elif self.type == 'boss' and not getattr(self, 'dialogue_anim_active', False) and self.boss_phase == 2 and len(IMAGES.get('boss_phase2', [])) >= 12:
                img_idx = self._get_phase2_frame()
                surface.blit(IMAGES['boss_phase2'][img_idx], IMAGES['boss_phase2'][img_idx].get_rect(center=(draw_x, draw_y)))
            elif self.type == 'boss' and not getattr(self, 'dialogue_anim_active', False) and len(boss_p1_imgs) >= 10:
                frame_idx = int(self.phase1_anim_frame) % 10
                surface.blit(boss_p1_imgs[frame_idx], boss_p1_imgs[frame_idx].get_rect(center=(draw_x, draw_y)))
            else:
                pygame.draw.circle(surface, getattr(self, 'color', (255, 60, 60)), (draw_x, draw_y), self.radius)
            # 👈 pill_boss 무적 상태 표시 (하늘색 보호막)
            if self.type == 'pill_boss' and getattr(self, 'is_invincible', False):
                pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
                glow_radius = int(self.radius + 15 + 10 * pulse)
                pygame.draw.circle(surface, (100, 180, 255, 150), (draw_x, draw_y), glow_radius, 4)
                pygame.draw.circle(surface, (150, 210, 255, 100), (draw_x, draw_y), int(glow_radius * 0.7), 2)
            # 👈 보스 소환 보호막 표시 (금색 보호막)
            if self.is_boss and getattr(self, 'summon_shield', False):
                t = getattr(self, 'summon_shield_timer', 0.0)
                pulse = abs(math.sin(t * 3.0))
                base_r = self.radius + 18
                glow_r = int(base_r + 8 * pulse)
                shield_size = glow_r * 2 + 20
                shield_surf = pygame.Surface((shield_size, shield_size), pygame.SRCALPHA)
                cx_s, cy_s = shield_size // 2, shield_size // 2
                for layer in range(3):
                    r_layer = glow_r + 6 - layer * 3
                    a_layer = int((40 + 30 * pulse) * (1.0 - layer * 0.3))
                    pygame.draw.circle(shield_surf, (60, 140, 255, min(255, max(0, a_layer))), (cx_s, cy_s), r_layer)
                hex_count = 6
                rot_offset = t * 40.0
                for i in range(hex_count):
                    angle = math.radians(60 * i + rot_offset)
                    hx = cx_s + math.cos(angle) * (glow_r - 4)
                    hy = cy_s + math.sin(angle) * (glow_r - 4)
                    node_alpha = int(180 + 60 * pulse)
                    pygame.draw.circle(shield_surf, (140, 210, 255, min(255, node_alpha)), (int(hx), int(hy)), 4)
                for i in range(hex_count):
                    a1 = math.radians(60 * i + rot_offset)
                    a2 = math.radians(60 * ((i + 1) % hex_count) + rot_offset)
                    x1 = cx_s + math.cos(a1) * (glow_r - 4)
                    y1 = cy_s + math.sin(a1) * (glow_r - 4)
                    x2 = cx_s + math.cos(a2) * (glow_r - 4)
                    y2 = cy_s + math.sin(a2) * (glow_r - 4)
                    line_a = int(120 + 80 * pulse)
                    pygame.draw.line(shield_surf, (100, 190, 255, min(255, line_a)), (int(x1), int(y1)), (int(x2), int(y2)), 2)
                inner_hex_count = 6
                inner_rot = -t * 25.0
                for i in range(inner_hex_count):
                    a1 = math.radians(60 * i + inner_rot)
                    a2 = math.radians(60 * ((i + 1) % inner_hex_count) + inner_rot)
                    ir = glow_r * 0.55
                    x1 = cx_s + math.cos(a1) * ir
                    y1 = cy_s + math.sin(a1) * ir
                    x2 = cx_s + math.cos(a2) * ir
                    y2 = cy_s + math.sin(a2) * ir
                    pygame.draw.line(shield_surf, (160, 220, 255, int(80 + 40 * pulse)), (int(x1), int(y1)), (int(x2), int(y2)), 1)
                for i in range(inner_hex_count):
                    a1 = math.radians(60 * i + inner_rot)
                    a2 = math.radians(60 * i + rot_offset)
                    pygame.draw.line(shield_surf, (120, 200, 255, int(60 + 30 * pulse)), (int(cx_s + math.cos(a1) * glow_r * 0.55), int(cy_s + math.sin(a1) * glow_r * 0.55)), (int(cx_s + math.cos(a2) * (glow_r - 4)), int(cy_s + math.sin(a2) * (glow_r - 4))), 1)
                ring_a = int(160 + 60 * pulse)
                pygame.draw.circle(shield_surf, (80, 170, 255, min(255, ring_a)), (cx_s, cy_s), glow_r + 2, 2)
                surface.blit(shield_surf, (draw_x - shield_size // 2, draw_y - shield_size // 2))

            if self.is_boss and not getattr(self, 'death_fly_active', False) and getattr(self, 'aim_state', 'none') == 'WARN':
                progress = 1.0 - (max(0, getattr(self, 'aim_timer', 0)) / 0.8)
                aim_alpha = int(30 + 180 * progress)
                aim_angle = getattr(self, 'aim_base_angle', 0)
                cone_len = 1200
                spread = math.pi * 0.8 if getattr(self, 'aim_wave', 0) == 0 else math.pi * 0.4
                cone_surf = pygame.Surface((cone_len * 2, cone_len * 2), pygame.SRCALPHA)
                cone_cx, cone_cy = cone_len, cone_len
                points = [(cone_cx, cone_cy)]
                steps = 30
                for s in range(steps + 1):
                    a = aim_angle - spread / 2 + (spread / steps) * s
                    px = cone_cx + math.cos(a) * cone_len
                    py = cone_cy + math.sin(a) * cone_len
                    points.append((int(px), int(py)))
                points.append((cone_cx, cone_cy))
                if len(points) >= 3:
                    pygame.draw.polygon(cone_surf, (255, 50, 50, min(255, aim_alpha)), points)
                    pygame.draw.line(cone_surf, (255, 100, 100, min(255, aim_alpha)), (cone_cx, cone_cy), (int(cone_cx + math.cos(aim_angle - spread/2) * cone_len), int(cone_cy + math.sin(aim_angle - spread/2) * cone_len)), 2)
                    pygame.draw.line(cone_surf, (255, 100, 100, min(255, aim_alpha)), (cone_cx, cone_cy), (int(cone_cx + math.cos(aim_angle + spread/2) * cone_len), int(cone_cy + math.sin(aim_angle + spread/2) * cone_len)), 2)
                surface.blit(cone_surf, (draw_x - cone_len, draw_y - cone_len))

        # 🎯 체력바는 if~elif 구문이 전부 끝난 뒤에 작동해야 합니다.
        if not (self.is_boss and (getattr(self, 'dialogue_anim_active', False) or getattr(self, 'death_fly_active', False))):
            bar_w = 60 if self.is_boss else 36
            bar_offset = 35 if self.is_boss else 15
            pygame.draw.rect(surface, (255, 255, 255), (draw_x - bar_w//2, draw_y - self.radius - bar_offset, bar_w, 6))
            pygame.draw.rect(surface, (255,50,50), (draw_x - bar_w//2, draw_y - self.radius - bar_offset, max(0, bar_w * (self.hp/self.max_hp)), 6))

def update_display(mode):
    global screen, current_width, current_height
    config['display_mode'] = mode; save_config(); screen.fill((0, 0, 0)); pygame.display.flip()
    if mode == 'FULLSCREEN': screen = pygame.display.set_mode((DESKTOP_W, DESKTOP_H), pygame.FULLSCREEN)
    elif mode == 'BORDERLESS': os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"; screen = pygame.display.set_mode((DESKTOP_W, DESKTOP_H), pygame.NOFRAME)
    else: os.environ['SDL_VIDEO_CENTERED'] = '1'; screen = pygame.display.set_mode((1600, 900) if DESKTOP_W >= 1600 and DESKTOP_H >= 900 else (current_width, current_height))
    current_width, current_height = screen.get_width(), screen.get_height()

def main():
    global current_width, current_height, screen, NAYE_HOME_MAP, CLASSROOM_MAP, TOILET_MAP, HEALTH_MAP, GYM_MAP, CAFETERIA_MAP, COMPUTER_MAP, LIBRARY_MAP, PRINCIPAL_MAP, current_difficulty
    
    load_config(); update_display(config['display_mode']); screen.fill((20, 20, 25))
    
    # 1. 백그라운드에서 실행할 로딩 작업 정의
    def load_assets_task():
        load_images()
        load_sounds()

    # 2. 로딩 스레드 생성 및 시작
    loading_thread = threading.Thread(target=load_assets_task)
    loading_thread.start()

    # 3. 로딩 애니메이션용 변수 세팅
    fnt = get_korean_font(40, bold=True)
    dot_count = 0
    dot_timer = 0.0

    # 4. 로딩 스레드가 끝날 때까지 부드러운 애니메이션 루프 실행
    while loading_thread.is_alive():
        dt = clock.tick(60) / 1000.0
        dot_timer += dt

        # 0.4초마다 점 개수 변경 (0 -> 1 -> 2 -> 3 -> 0)
        if dot_timer > 0.4:
            dot_timer = 0.0
            dot_count = (dot_count + 1) % 4

        # 로딩 중 창 닫기 이벤트 처리
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

        # 화면 렌더링
        screen.fill((20, 20, 25))
        try:
            loading_text = f"로딩 중입니다{' .' * dot_count}"
            txt = fnt.render(loading_text, True, (255, 255, 255))
            screen.blit(txt, (current_width // 2 - txt.get_width() // 2, current_height // 2))
        except: pass
        pygame.display.flip()

    # 스레드가 안전하게 종료되었는지 확인
    loading_thread.join()
    
    app_state = APP_MAIN_MENU; current_map_idx = -1; cleared_rooms = [False] * len(MAP_DATA)
    story_step = 1; story_timer = 0.0; story_alpha = 0.0; story_state = 'VIEW'
    cols, rows = 26, 15; room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
    
    player = Player(room_w, room_h)
    
    bullets = []; enemy_bullets = []; enemies = []; spawners = []; boomerangs = []; chopstick_rains = []; dust_bursts = []; room_state = ROOM_WAITING
    saves_data = get_save_data(); current_play_time = 0.0; camera_x, camera_y = 0, 0
    
    context_menu_active = False; context_menu_pos = (0, 0); context_selected_inv_idx = -1; context_selected_qs_idx = -1; assigning_quick_slot = False
    damage_texts = []; slash_effects = []; particles = []; dust_particles = []; dropped_items = []; shield_particles = []
    _kill_count_since_potion = 0
    soap_puddles = []
    library_mines = []
    static_waves = []
    forbidden_wave_phase = 'IDLE'
    forbidden_wave_timer = 0.0
    blue_overlay_alpha = 0.0
    forbidden_fake_death = False
    forbidden_fake_death_timer = 0.0
    forbidden_respawn_flash = 0.0
    screen_shake_timer = 0.0; screen_shake_duration = 5.0; screen_shake_intensity = 0.0
    glitch_timer = 0.0
    
    def _handle_interact_action():
        """상호작용 키/마우스 버튼이 눌렸을 때 실행되는 공통 로직"""
        nonlocal popup_msg, popup_timer, current_overlay, viewing_item
        picked_up = False
        for item in dropped_items[:]:
            if item.pos.distance_to(player.pos) < player.radius + item.radius + 15:
                picked_up = True
                if item.item_type not in player.seen_items:
                    player.seen_items.append(item.item_type)
                    current_overlay = 'ITEM_INFO'; viewing_item = item.item_type
                    player.add_item(item.item_type, 1); dropped_items.remove(item)
                    if 'interact' in SOUNDS: SOUNDS['interact'].play()
                else:
                    if player.add_item(item.item_type, 1):
                        dropped_items.remove(item); popup_msg = f"{item.item_type} 획득!"; popup_timer = 2.0
                        if 'interact' in SOUNDS: SOUNDS['interact'].play()
                    else: popup_msg = "배낭이 꽉 찼습니다!"; popup_timer = 2.0
                break
        if picked_up: return
        p_col, p_row = int(player.pos.x // TILE_SIZE), int(player.pos.y // TILE_SIZE)
        if current_map_idx == -1:
            for r in range(max(0, p_row-1), min(len(NAYE_HOME_MAP), p_row+2)):
                for c in range(max(0, p_col-1), min(len(NAYE_HOME_MAP[0]), p_col+2)):
                    tc_x = c * TILE_SIZE + TILE_SIZE / 2; tc_y = r * TILE_SIZE + TILE_SIZE / 2
                    if NAYE_HOME_MAP[r][c] == 2:
                        if pygame.math.Vector2(tc_x, tc_y).distance_to(player.pos) < 55:
                            if 'interact' in SOUNDS: SOUNDS['interact'].play()
                            current_overlay = 'SAVE'; return
                    if NAYE_HOME_MAP[r][c] == 3 and not player.has_bag:
                        if pygame.math.Vector2(tc_x, tc_y).distance_to(player.pos) < 55:
                            if 'interact' in SOUNDS: SOUNDS['interact'].play()
                            player.has_bag = True
                            current_overlay = 'ITEM_INFO'; viewing_item = "배낭"; return
        elif current_map_idx == 5:
            if "방어막" in player.seen_items: return
            for r in range(max(0, p_row-1), min(len(COMPUTER_MAP), p_row+2)):
                for c in range(max(0, p_col-1), min(len(COMPUTER_MAP[0]), p_col+2)):
                    if COMPUTER_MAP[r][c] == 3:
                        tc_x = c * TILE_SIZE + TILE_SIZE / 2; tc_y = r * TILE_SIZE + TILE_SIZE / 2
                        if pygame.math.Vector2(tc_x, tc_y).distance_to(player.pos) < 55:
                            if 'interact' in SOUNDS: SOUNDS['interact'].play()
                            if "방어막" not in player.seen_items:
                                player.seen_items.append("방어막")
                                current_overlay = 'ITEM_INFO'; viewing_item = "방어막"
                            player.add_item("방어막", 1); return
        elif current_map_idx in [0, 1, 2, 3, 4, 5, 6, 7]:
            target_map = [CLASSROOM_MAP, TOILET_MAP, HEALTH_MAP, GYM_MAP, CAFETERIA_MAP, COMPUTER_MAP, LIBRARY_MAP, PRINCIPAL_MAP][current_map_idx]
            for r in range(max(0, p_row-1), min(len(target_map), p_row+2)):
                for c in range(max(0, p_col-1), min(len(target_map[0]), p_col+2)):
                    tc_x = c * TILE_SIZE + TILE_SIZE / 2; tc_y = r * TILE_SIZE + TILE_SIZE / 2
                    if target_map[r][c] == 2:
                        if pygame.math.Vector2(tc_x, tc_y).distance_to(player.pos) < 55:
                            if room_state == ROOM_CLEARED:
                                if 'interact' in SOUNDS: SOUNDS['interact'].play()
                                current_overlay = 'SAVE'
                            else: popup_msg = "주변의 몬스터를 모두 처치해야해!"; popup_timer = 2.0
                            return
    
    def _handle_attack_action(target_x, target_y):
        """공격 키/마우스 버튼이 눌렸을 때 실행되는 공통 로직"""
        if player.frozen: return
        nonlocal boss_defeated, boss_death_fade_alpha, forbidden_fake_death, forbidden_fake_death_timer, forbidden_wave_phase, blue_overlay_alpha, _kill_count_since_potion
        dx = target_x - player.pos.x; dy = target_y - player.pos.y
        if abs(dx) > abs(dy): player.facing = 'right' if dx > 0 else 'left'
        else: player.facing = 'down' if dy > 0 else 'up'
        
        atk_result = player.trigger_attack()
        if atk_result == "DISABLED":
            damage_texts.append(DamageText(player.pos.x, player.pos.y - 40, "공격불가"))
            return
        if atk_result == True:
            if 'attack' in SOUNDS: SOUNDS['attack'].play()
            offset_x, offset_y = 45, 60; hx, hy = player.pos.x, player.pos.y
            if player.facing == 'right': hx += offset_x
            elif player.facing == 'left': hx -= offset_x
            elif player.facing == 'up': hy -= offset_y
            elif player.facing == 'down': hy += offset_y
            hitbox_pos = pygame.math.Vector2(hx, hy); hitbox_radius = 75; hit_something = False
            
            for enemy in enemies[:]:
                if hitbox_pos.distance_to(enemy.pos) < hitbox_radius + enemy.radius:
                    hit_something = True
                    if enemy.is_boss and (boss_transition_state in ['WIDE_SHOT', 'METEOR_FALL'] or boss_bubble_state == 'ACTIVE'):
                        damage_texts.append(DamageText(enemy.pos.x, enemy.pos.y - 40, "무적"))
                    elif enemy.type == 'pill_boss' and getattr(enemy, 'is_invincible', False):
                        damage_texts.append(DamageText(enemy.pos.x, enemy.pos.y - 40, "무적"))
                    elif enemy.is_boss and getattr(enemy, 'summon_shield', False):
                        damage_texts.append(DamageText(enemy.pos.x, enemy.pos.y - 40, "무적"))
                    else:
                        individual_dmg = random.randint(20, 25) if player.attack_step == 2 else random.randint(15, 19)
                        # 꼬깔콘 상태별 피해 배율
                        if enemy.type == 'corn_cone':
                            if getattr(enemy, 'state', '') == 'STUCK':
                                individual_dmg = int(individual_dmg * 2.0)  # 파훼 보너스 2배
                            elif getattr(enemy, 'state', '') == 'PRECAST':
                                individual_dmg = max(1, int(individual_dmg * 0.5))  # PRECAST 중 0.5배
                        enemy.hp -= individual_dmg; enemy.flash_timer = 0.1
                        if enemy.type == 'boss':
                            if enemy.boss_phase == 1:
                                enemy.phase1_hp = max(0, enemy.phase1_hp - individual_dmg)
                                enemy.hp = enemy.phase1_hp
                            else:
                                enemy.phase2_hp = max(0, enemy.phase2_hp - individual_dmg)
                                enemy.hp = enemy.phase2_hp
                        damage_texts.append(DamageText(enemy.pos.x, enemy.pos.y - 20, individual_dmg))
                        slash_effects.append(SlashEffect(enemy.pos.x, enemy.pos.y))
                        for _ in range(random.randint(15, 25)): particles.append(Particle(enemy.pos.x, enemy.pos.y - 10))
                        if enemy.hp <= 0:
                            dead_type = enemy.type
                            if dead_type == 'boss' and enemy.boss_phase == 1:
                                enemy.phase1_hp = 0; enemy.hp = 0
                                continue
                            if dead_type == 'boss' and enemy.boss_phase == 2 and not getattr(enemy, 'death_fly_active', False):
                                fly_dir = enemy.pos - player.pos
                                if fly_dir.length() > 0: fly_dir = fly_dir.normalize()
                                else: fly_dir = pygame.math.Vector2(1, 0)
                                enemy.death_fly_dir = fly_dir
                                enemy.death_fly_facing_right = fly_dir.x >= 0
                                enemy.death_fly_active = True
                                enemy.hp = 0
                                continue
                            dead_was_real = getattr(enemy, 'is_real', False)
                            enemies.remove(enemy)
                            if dead_type == 'boss':
                                boss_defeated = True
                                player.frozen = True
                                boss_death_fade_alpha = 0.1
                                pygame.mixer.music.stop()
                            if dead_type == 'pill_boss':
                                for eb in enemy_bullets[:]:
                                    if hasattr(eb, 'is_pill_bullet') and eb.is_pill_bullet:
                                        enemy_bullets.remove(eb)
                            if dead_type == 'gravity_book':
                                player.controls_reversed = False
                            if dead_type == 'forbidden_book':
                                for fb in enemies[:]:
                                    if fb.type == 'forbidden_book': enemies.remove(fb)
                                if not dead_was_real:
                                    forbidden_fake_death = True
                                    forbidden_fake_death_timer = 2.5
                                else:
                                    forbidden_wave_phase = 'IDLE'; blue_overlay_alpha = 0.0
                            if dead_type == 'gamble_book':
                                for d in enemy.dice_bullets: d.alive = False
                                for d in enemy.mini_dices: d.alive = False
                            if dead_type not in ['badminton_shuttle', 'forbidden_book']:
                                _kill_count_since_potion += 1
                                if _kill_count_since_potion >= 6 or random.random() < 0.15:
                                    dropped_items.append(DroppedItem(enemy.pos.x, enemy.pos.y, "회복물약")); _kill_count_since_potion = 0
                            
            for eb in enemy_bullets[:]:
                # 👇 배드민턴공 파훼: 플레이어 공격이 공에 닿으면 반사
                if hasattr(eb, 'is_shuttle') and eb.is_shuttle and not getattr(eb, 'is_reflected', False):
                    if hitbox_pos.distance_to(eb.pos) < hitbox_radius + eb.radius:
                        hit_something = True
                        # 공을 반사시킴: 방향을 반대로 (라켓을 향해)
                        eb.is_reflected = True
                        eb.direction = -eb.direction  # 역방향
                        eb.speed = 600  # 반사 시 속도 증가
                        eb.travel_distance = 0
                        eb.max_travel_distance = 800  # 반사 후 사거리
                        slash_effects.append(SlashEffect(eb.pos.x, eb.pos.y))
                        for _ in range(15): particles.append(Particle(eb.pos.x, eb.pos.y))
                        continue
                
                if hasattr(eb, 'exploded') and hitbox_pos.distance_to(eb.pos) < hitbox_radius + eb.radius:
                    hit_something = True
                    eb.explode(enemy_bullets)
                    if eb in enemy_bullets: enemy_bullets.remove(eb)
                    slash_effects.append(SlashEffect(eb.pos.x, eb.pos.y))
                    for _ in range(10): particles.append(Particle(eb.pos.x, eb.pos.y - 10))
            
            current_tile_map = None
            if current_map_idx == -1: current_tile_map = NAYE_HOME_MAP
            elif current_map_idx in [0,1,2,3,4,5,6,7]: current_tile_map = [CLASSROOM_MAP, TOILET_MAP, HEALTH_MAP, GYM_MAP, CAFETERIA_MAP, COMPUTER_MAP, LIBRARY_MAP, PRINCIPAL_MAP][current_map_idx]
            
            if current_tile_map:
                hit_4_tiles = []
                start_c = max(0, int((hitbox_pos.x - hitbox_radius) // TILE_SIZE)); end_c = min(len(current_tile_map[0]), int((hitbox_pos.x + hitbox_radius) // TILE_SIZE) + 1)
                start_r = max(0, int((hitbox_pos.y - hitbox_radius) // TILE_SIZE)); end_r = min(len(current_tile_map), int((hitbox_pos.y + hitbox_radius) // TILE_SIZE) + 1)
                for r in range(start_r, end_r):
                    for c in range(start_c, end_c):
                        if current_tile_map[r][c] == 4:
                            tc_x = c * TILE_SIZE + TILE_SIZE / 2; tc_y = r * TILE_SIZE + TILE_SIZE / 2
                            if hitbox_pos.distance_to(pygame.math.Vector2(tc_x, tc_y)) < hitbox_radius + TILE_SIZE / 2: hit_4_tiles.append((tc_x, tc_y))
                if hit_4_tiles:
                    hit_something = True
                    avg_x = sum(t[0] for t in hit_4_tiles) / len(hit_4_tiles); min_y = min(t[1] for t in hit_4_tiles) - TILE_SIZE / 2
                    sandbag_dmg = random.randint(20, 25) if player.attack_step == 2 else random.randint(15, 19)
                    damage_texts.append(DamageText(avg_x, min_y, sandbag_dmg)); slash_effects.append(SlashEffect(avg_x, min_y + TILE_SIZE//2))
                    for _ in range(random.randint(15, 25)): particles.append(Particle(avg_x, min_y + TILE_SIZE//2))
            if hit_something and 'hit' in SOUNDS: SOUNDS['hit'].play()
    
    boss_phase = 1; boss_transition_state = None; boss_transition_timer = 0.0; boss_ref = None
    boss_phase2_attack_name_timer = 0.0
    meteor_frame = 0.0; meteor_frame_speed = 15.0
    meteor_pos = pygame.math.Vector2(0, 0); explosion_radius = 0.0; explosion_alpha = 255.0
    # 👇 보스 컷씬 및 고급 대화 데이터
    boss_talk_state = 'NONE' # 'APPROACH'(걸어가는 중), 'TALKING', 'DONE'
    boss_talk_step = 0; boss_char_idx = 0.0; boss_dialogue_played = False
    _boss_state_file = "boss_state.json"
    if os.path.exists(_boss_state_file):
        try:
            with open(_boss_state_file, "r", encoding="utf-8") as _bsf:
                boss_intro_completed_once = json.load(_bsf).get("intro_completed", False)
        except:
            boss_intro_completed_once = False
    else:
        boss_intro_completed_once = False
    boss_defeated = False  # 보스가 사망하면 True로 전환 → 페이드아웃 후 엔딩 시퀀스 진입
    boss_death_fade_alpha = 0.0  # 보스 사망 후 화면 어두워짐 (0=투명, 255=완전검정)
    boss_death_snapshot = None   # 보스 사망 순간의 화면 스냅샷 (게임 완전 정지용)
    boss_messages = [
        {"speaker": "노아", "emo": "기본", "text": "학교가 왜이리 소란스러운가 했더니\n역시나 너군아."},
        {"speaker": "노아", "emo": "기본", "text": "나예.", "speed": "very_slow", "size": "large"},
        {"speaker": "나예", "emo": "혐오", "text": "내 남친을 홀린 애가 너지?"},
        {"speaker": "노아", "emo": "행복", "text": "맞아. 바로 나야.\n애교랑 앙탈을 부리니 금방 넘어 오던데?"},
        {"speaker": "나예", "emo": "화남", "text": "개새끼...저딴 단순한거에 넘어가고..", "style": "mumble"},
        {"speaker": "노아", "emo": "행복", "text": "니 남친 쩔더라고.\n다정하고 귀여워죽겠어~"},
        {"speaker": "노아", "emo": "행복", "text": "확! 내꺼로 만들어야겠어!"},
        {"speaker": "나예", "emo": "혐오", "text": "..."},
        {"speaker": "노아", "emo": "기본", "text": "그러니까 말이야......\n넌 이 자리에서..."},
        {"speaker": "노아", "emo": "화남", "text": "죽어줘야겠어", "style": "blood"}
    ]
    boss_emotions = ["기본", "슬픔", "화남"] # 대사 순서에 맞춰 노아의 표정을 지정
    # 👇 보스 말풍선 (2페 전환 전)
    boss_bubble_state = 'NONE'  # 'NONE', 'ACTIVE', 'DONE'
    boss_bubble_lines = ["끝난 줄 알았지....?", "이제부터", "시 작 이 다"]
    boss_bubble_step = 0
    boss_bubble_char_idx = 0.0
    boss_bubble_speed = 25.0  # 마지막 줄은 더 느리게
    # 👇 엔딩 스토리 데이터
    ending_messages = [
        {"speaker": "노아", "text": "크윽….", "style": "normal", "noah_emo": "슬픔"},
        {"speaker": "노아", "text": "내가 잘못했어!! 한 번만 더 기회를 줘....\n더 이상 니 남친 앞에 나타나지 않을게..!!!", "style": "normal", "noah_emo": "두려움"},
        {"speaker": "나예", "text": "더 할 말은…?", "style": "normal", "naye_emo": "혐오"},
        {"speaker": "노아", "text": "정말 미안해! 없던 일로 할까?\n쇼핑 좋아해? 우리 쇼핑하러가ㄹ…", "style": "normal", "noah_emo": "행복"},
        {"speaker": "노아", "text": "커ㅡ억..ㄴ..너….", "style": "normal", "noah_emo": "두려움", "naye_emo": "혐오"},
        {"speaker": "나예", "text": "미안하지만 난 너를", "style": "normal", "naye_emo": "혐오"},
        {"speaker": "나예", "text": "용 서 해 줄 수 없 어.", "style": "ending_blood", "naye_emo": "혐오"},
        {"speaker": "나예", "text": "잘가.", "style": "normal", "naye_emo": "행복"},
    ]
    
    # 엔딩 step에 따른 이미지 키 반환 (전역에서 접근 가능하도록)
    def _get_ending_img_key(step):
        if step < 0:  # INTRO 전용 (step=-1처럼 취급)
            return 'ending_1'
        elif step >= 4:
            return 'ending_4'
        elif step >= 1:
            return 'ending_3'
        elif step >= 0:
            return 'ending_2'
        return None
    
    ending_state = 'NONE'  # 'NONE', 'INTRO', 'PLAYING', 'DELAY', 'FADE_OUT', 'FADE_IN', 'BLACK_FADE', 'BLACK_WAIT', 'DONE'
    ending_step = 0
    ending_char_idx = 0.0
    ending_shake_timer = 0.0
    ending_delay_timer = 0.0
    ending_fade_alpha = 255.0  # 이미지 페이드용 알파값 (255=완전표시, 0=완전투명)
    ending_target_step = 0  # 페이드 완료 후 이동할 step
    ending_black_alpha = 0.0  # 엔딩 종료 후 검은 화면 페이드용 (0=투명, 255=완전검정)
    ending_black_wait = 0.0  # 검은 화면 대기 타이머
    ending_last_noah_emo = "기본"  # 마지막으로 표시된 노아 감정 기억 (투명해질 때 유지)
    ending_last_naye_emo = "기본"  # 마지막으로 표시된 나예 감정 기억 (투명해질 때 유지)
    death_anim_timer = 0.0
    room_clear_timer = 0.5
    
    viewing_item = None
    
    tutorial_state = 'DONE'; tutorial_timer = 0.0; tutorial_step = 0; tutorial_char_idx = 0.0; current_zoom = 1.0 
    monologue_step = 0
    _voice_played_monologue_step = -1
    _voice_played_boss_talk_step = -1
    _voice_played_boss_bubble_step = -1
    _voice_played_ending_step = -1
    boss_talk_voice_map = {0: 4, 1: 5, 2: 6, 3: 7, 4: 8, 5: 9, 6: 10, 8: 11, 9: 12}
    def _stop_all_voices():
        for vi in range(1, 24):
            vk = f'voice_{vi:02d}'
            if vk in SOUNDS: SOUNDS[vk].stop()
    monologue_messages = [
        "이 쓰레기새끼....\n날 두고 딴 년이랑...",
        "죽여버릴거야",
        "일단 학교로 가볼까...."
    ] 
    tutorial_messages = [
        "먀~앙", 
        "안냥?! 내가 널 도와주겠다냥!", 
        "이동은 WASD로 할 수 있고 좌클릭은 공격이다냥!!", 
        "스페이스바로 대쉬해서 공격을 피할 수 있다냐!\n타이밍이 넉넉하지 않으니 조심하라냥!", 
        "왼쪽에 꽃병이 보이냥? 저기에서 저장을 할 수 있다냐!\n맵 곳곳에 숨어있으니 잘 찾아보라냥!",
        "저장을 하지 않으면\n처음부터 해야 할 수 있으니 조심하라냥!",
        "아래에 공으로 공격을 한번 테스트 해보라냥", 
        "준비가 되면 책상 위에\n가방을 챙겨서 학교로 출발하자냥!!!"
    ]
    cat_pos = pygame.math.Vector2(23 * 32, 5 * 32); vase_pos = pygame.math.Vector2(4 * 32, 7 * 32); ball_pos = pygame.math.Vector2(22.5 * 32, 11.5 * 32)
    
    is_mouse_down = False; popup_msg = ""; popup_timer = 0.0
    
    title_font = get_korean_font(100, bold=True); huge_font = get_korean_font(60, bold=True); font = get_korean_font(30)
    large_font = get_korean_font(40); small_font = get_korean_font(20); mini_font = get_korean_font(16)
    credits_font_title = get_korean_font(55, bold=True); credits_font_body = get_korean_font(35); credits_font_last = get_korean_font(45, bold=True)

    credits_scroll_y = 0.0
    credits_scroll_speed = 50.0
    credits_started = False
    credits_paused = False
    credits_pause_timer = 0.0
    credits_can_enter = False
    credits_img_group_idx = 0
    credits_img_alpha = 255.0
    credits_img_timer = 0.0
    credits_img_fading_out = False
    credits_img_fading_in = False
    _credits_char_imgs = ['naye_face_행복', 'noah_행복', '주현_기본', 'cat_portrait']
    _credits_bg_imgs = ['naye_home_bg', 'class_bg', 'toilet_bg', 'health_bg', 'gym_bg', 'cafeteria_bg', 'computer_bg', 'library_bg', 'principal_bg1', 'principal_bg2']
    _credits_mon_imgs = ['eraser_1', 'chalk_1', 'pencil_1', 'pencil_tip', 'soap_1', 'toothbrush_2', 'toothpaste_1', 'bubble_large', 'bandage_1', 'syringe_1', 'pill_boss_2', 'pill_bullet_red', 'pill_bullet_blue', 'corn_cone_1', 'badminton_racket_1', 'badminton_shuttle_1', 'soccer_ball_1', 'food_tray_1', 'single_tray_1', 'side_dish_1', 'side_dish_2', 'side_dish_3', 'side_dish_4', 'spoon_chopsticks_1', 'steel_scrubber_1', 'router_1', 'keyboard_2', 'computer_mouse_1', 'laser_beam_1', 'mine_book_1', 'library_mine_1', 'forbidden_book_1', 'gravity_book_1', 'gamble_book_1']
    credits_image_groups = []
    credits_image_groups.append(_credits_char_imgs[:])
    for i in range(0, len(_credits_bg_imgs), 4):
        credits_image_groups.append(_credits_bg_imgs[i:i+4])
    credits_monster_start_idx = len(credits_image_groups)
    for i in range(0, len(_credits_mon_imgs), 4):
        credits_image_groups.append(_credits_mon_imgs[i:i+4])
    credits_lines = [
        ("title", "[엔딩크레딧]"),
        ("normal", ""),
        ("normal", ""),
        ("normal", "배경: 학교"),
        ("normal", "스토리 : 바람피는 남친과 그의 여자들을 단죄"),
        ("normal", "그 중 1명을 단죄하는 이야기"),
        ("normal", ""),
        ("normal", ""),
        ("normal", "호서대학교 게임소프트웨어 학과 1학년"),
        ("normal", "창의프로그래밍 Ai 활용"),
        ("normal", "pygame 1인 게임개발"),
        ("normal", ""),
        ("normal", ""),
        ("normal", "기획 : 나예"),
        ("normal", "디자인 : 나예"),
        ("normal", "개발 : 나예"),
        ("normal", "제작기간 : 30일"),
        ("normal", ""),
        ("normal", ""),
        ("normal", ""),
        ("normal", ""),
        ("normal", ""),
        ("normal", ""),
        ("normal", ""),
        ("normal", ""),
        ("normal", ""),
        ("normal", ""),
        ("normal", ""),
        ("normal", ""),
        ("normal", ""),
        ("last", "저 얀데레 아니니까 오해하지 말아주세요."),
    ]
    
    minimap_positions = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2), (0, 1)]

    current_overlay = None; current_tab = "VIDEO"; waiting_for_key = None; confirm_delete_slot = None; confirm_save_slot = None; continue_enabled = any(saves_data.get(f"slot_{i+1}") is not None for i in range(3))

    menu_btn_start = Button(-840, 700, 200, 60, "새로 시작")
    menu_btn_continue = Button(-840, 780, 200, 60, "이어하기")
    menu_btn_settings = Button(-840, 860, 200, 60, "설정")
    menu_btn_quit = Button(-840, 940, 200, 60, "게임 종료", base_col=(180, 50, 50), hover_col=(220, 80, 80))

    btn_go_restart = Button(0, 450, 240, 70, "새로 시작")
    btn_go_continue = Button(0, 540, 240, 70, "이어하기")
    btn_go_quit = Button(0, 630, 240, 70, "게임 종료", base_col=(180, 50, 50), hover_col=(220, 80, 80))

    btn_video = Button(-200, 200, 180, 60, "화면 설정")
    btn_audio = Button(0, 200, 180, 60, "음향 설정")
    btn_keys = Button(200, 200, 180, 60, "단축키")
    
    btn_window = Button(0, 330, 320, 60, "창 모드")
    btn_borderless = Button(0, 400, 320, 60, "테두리 없는 전체화면")
    btn_fullscreen = Button(0, 470, 320, 60, "전체화면")
    
    btn_vol_down = Button(-100, 310, 60, 60, "-", 40); btn_vol_up = Button(100, 310, 60, 60, "+", 40)
    btn_bgm_vol_down = Button(-100, 440, 60, 60, "-", 40); btn_bgm_vol_up = Button(100, 440, 60, 60, "+", 40)
    btn_voice_vol_down = Button(-100, 570, 60, 60, "-", 40); btn_voice_vol_up = Button(100, 570, 60, 60, "+", 40)
    
    key_buttons = {'UP': Button(-225, 340, 130, 45, "", 20), 'DOWN': Button(-75,  340, 130, 45, "", 20), 'LEFT': Button(75,   340, 130, 45, "", 20), 'RIGHT': Button(225,  340, 130, 45, "", 20), 'INTERACT': Button(-150, 450, 130, 45, "", 20), 'DASH': Button(0,   450, 130, 45, "", 20), 'ATTACK': Button(150, 450, 130, 45, "", 20)}
    key_labels_kr = {'UP': "위 이동", 'DOWN': "아래 이동", 'LEFT': "왼쪽 이동", 'RIGHT': "오른쪽 이동", 'INTERACT': "상호작용", 'DASH': "대시 (회피)", 'ATTACK': "공격"}

    btn_reset_defaults = Button(305, 715, 70, 25, "기본값", 14, (100, 60, 60), (140, 80, 80))
    btn_reset_confirm_yes = Button(120, 470, 200, 70, "확인", base_col=(60, 150, 60), hover_col=(80, 200, 80)); btn_reset_confirm_no = Button(-120, 470, 200, 70, "뒤로", base_col=(80, 80, 90))
    confirm_reset_tab = None
    btn_close_overlay = Button(0, 650, 260, 70, "닫기", base_col=(80, 80, 90)); btn_return_main = Button(-140, 650, 260, 70, "나가기", base_col=(180, 50, 50)); btn_close_settings_game = Button(140, 650, 260, 70, "설정 닫기", base_col=(80, 80, 90))
    slot_buttons = [Button(-50, 250, 320, 80, "슬롯 1", 26), Button(-50, 380, 320, 80, "슬롯 2", 26), Button(-50, 510, 320, 80, "슬롯 3", 26)]
    delete_buttons = [Button(160, 250, 80, 80, "삭제", 24, (180, 50, 50)), Button(160, 380, 80, 80, "삭제", 24, (180, 50, 50)), Button(160, 510, 80, 80, "삭제", 24, (180, 50, 50))]
    btn_confirm_yes_del = Button(-120, 450, 200, 70, "예 (삭제)", base_col=(180, 50, 50)); btn_confirm_yes_save = Button(-120, 450, 200, 70, "예 (저장)", base_col=(60, 150, 60)); btn_confirm_no = Button(120, 450, 200, 70, "아니오", base_col=(80, 80, 90))

    difficulty_sub = 'SELECT'; selected_difficulty = None
    difficulty_data = {
        'easy':   {"name": "쉬움",   "desc_lines": [
            [("모든 입는 데미지 2", (200, 200, 200))],
            [("몬스터 공격 준비시간 조금 ", (200, 200, 200)), ("증가", (255, 140, 140))],
            [("탄막 속도 조금 ", (200, 200, 200)), ("감소", (140, 180, 255))]
        ]},
        'normal': {"name": "보통",   "desc_lines": [
            [("기본 난이도", (200, 200, 200))]
        ]},
        'hard':   {"name": "어려움", "desc_lines": [
            [("기본 데미지에 +2", (200, 200, 200))],
            [("몬스터 공격 준비시간 조금 ", (200, 200, 200)), ("감소", (140, 180, 255))],
            [("탄막 속도 조금 ", (200, 200, 200)), ("증가", (255, 140, 140))],
            [("보스 및 몬스터 체력 x1.5", (200, 200, 200))]
        ]}
    }
    btn_diff_easy   = Button(0, 350, 300, 70, "쉬움",   base_col=(60, 150, 60),  hover_col=(80, 200, 80))
    btn_diff_normal = Button(0, 440, 300, 70, "보통",   base_col=(60, 60, 180),  hover_col=(80, 80, 220))
    btn_diff_hard   = Button(0, 530, 300, 70, "어려움", base_col=(180, 50, 50),  hover_col=(220, 80, 80))
    btn_diff_x      = Button(270, 175, 60, 60, "X", 30, base_col=(180, 50, 50), hover_col=(220, 80, 80))
    btn_diff_back   = Button(-120, 580, 200, 70, "뒤로", base_col=(80, 80, 90),  hover_col=(120, 120, 130))
    btn_diff_confirm= Button(120,  580, 200, 70, "확인", base_col=(60, 150, 60),  hover_col=(80, 200, 80))
    btn_leave_yes = Button(-120, 480, 200, 70, "가자!", base_col=(60, 150, 60), hover_col=(80, 180, 80)); btn_leave_no = Button(120, 480, 200, 70, "아직이야..", base_col=(80, 80, 90), hover_col=(100, 100, 110))

    running = True
    while running:
        real_dt = clock.tick(60) / 1000.0
        dt = real_dt
        scaled_mouse_pos = get_scaled_mouse_pos(); center_x = LOGICAL_WIDTH // 2

        if app_state == APP_MAIN_MENU: play_bgm('title')
        elif app_state == APP_STORY: play_bgm(None)
        elif app_state == APP_PLAYING:
            if current_map_idx == -1: 
                # 고양이와 대화가 끝난 상태(DONE)일 때만 대기배경 재생! 그 전엔 정적 유지.
                if tutorial_state in ('WAITING_INPUT', 'EXCLAMATION', 'PANNING', 'TALKING', 'DONE'): play_bgm('waiting')
                else: play_bgm(None)
            elif current_map_idx == 7:
                if boss_defeated or boss_talk_state in ['APPROACH', 'TALKING']:
                    play_bgm(None)
                elif boss_phase == 2:
                    play_bgm('boss_phase2')
                elif boss_talk_state == 'DONE':
                    play_bgm('boss_phase1')
                else:
                    play_bgm(None)
            else: 
                # 0~6번 일반 학교 맵에서는 평소대로 전투 배경음악 재생
                play_bgm('game') 

        for i in range(3):
            slot_key = f"slot_{i+1}"
            if saves_data[slot_key]: slot_buttons[i].text = f"슬롯 {i+1} [{format_time(saves_data[slot_key].get('play_time', 0.0))}]"; slot_buttons[i].base_color = (60, 120, 60)
            else: slot_buttons[i].text = f"슬롯 {i+1} [비어있음]"; slot_buttons[i].base_color = (80, 80, 90)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2: mouse_buttons_held[2] = True
                elif event.button == 3: mouse_buttons_held[3] = True
                if event.button == 1:
                    is_mouse_down = True; mouse_buttons_held[1] = True
                    if current_overlay: pass
                    elif app_state == APP_GAME_OVER:
                        if btn_go_restart.is_clicked(event, scaled_mouse_pos):
                            # 1. 맵 및 플레이어 리셋
                            current_map_idx = -1; cleared_rooms = [False] * len(MAP_DATA); cols, rows = 26, 15; room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                            player = Player(room_w, room_h); player.pos.x = room_w // 2; player.pos.y = 250
                            
                            # 2. 모든 맵 데이터 원본 복구
                            NAYE_HOME_MAP = load_tiled_map(layer_files_home, 26, 15)
                            CLASSROOM_MAP = load_tiled_map(layer_files_class, MAP_DATA[0]['cols'], MAP_DATA[0]['rows'])
                            TOILET_MAP = load_tiled_map(layer_files_toilet, MAP_DATA[1]['cols'], MAP_DATA[1]['rows'])
                            HEALTH_MAP = load_tiled_map(layer_files_health, MAP_DATA[2]['cols'], MAP_DATA[2]['rows'])
                            GYM_MAP = load_tiled_map(layer_files_gym, MAP_DATA[3]['cols'], MAP_DATA[3]['rows'])
                            CAFETERIA_MAP = load_tiled_map(layer_files_cafeteria, MAP_DATA[4]['cols'], MAP_DATA[4]['rows'])
                            COMPUTER_MAP = load_tiled_map(layer_files_computer, MAP_DATA[5]['cols'], MAP_DATA[5]['rows'])
                            LIBRARY_MAP = load_tiled_map(layer_files_library, MAP_DATA[6]['cols'], MAP_DATA[6]['rows'])
                            PRINCIPAL_MAP = load_tiled_map(layer_files_principal, MAP_DATA[7]['cols'], MAP_DATA[7]['rows'])
                            
                            # 3. 투사체, 이펙트 및 방 상태 완전 리셋
                            bullets.clear(); enemy_bullets.clear(); enemies.clear(); spawners.clear(); boomerangs.clear(); chopstick_rains.clear(); dust_bursts.clear(); damage_texts.clear(); slash_effects.clear(); particles.clear(); dust_particles.clear(); dropped_items.clear(); soap_puddles.clear(); library_mines.clear(); static_waves.clear()
                            room_state = ROOM_WAITING; current_play_time = 0.0; app_state = APP_STORY
                            story_step = 1; story_timer = 0.0; story_alpha = 0.0; story_state = 'VIEW'; walk_played = False; sword_draw_played = False
                            is_mouse_down = False; context_menu_active = False; assigning_quick_slot = False
                            # 4. 👑 보스 컷씬 및 페이즈 데이터 완전 리셋
                            boss_phase = 1; boss_transition_state = None; boss_ref = None; boss_phase2_attack_name_timer = 0.0
                            boss_talk_state = 'NONE'; boss_talk_step = 0; boss_char_idx = 0.0; boss_dialogue_played = False
                            boss_intro_completed_once = False
                            if os.path.exists("boss_state.json"): os.remove("boss_state.json")
                            boss_bubble_state = 'NONE'; boss_bubble_step = 0; boss_bubble_char_idx = 0.0
                            boss_defeated = False
                            boss_death_fade_alpha = 0.0
                            player.frozen = False
                            forbidden_wave_phase = 'IDLE'; blue_overlay_alpha = 0.0; forbidden_fake_death = False; forbidden_fake_death_timer = 0.0; forbidden_respawn_flash = 0.0
                            ending_state = 'NONE'; ending_step = 0; ending_char_idx = 0.0; ending_shake_timer = 0.0; ending_delay_timer = 0.0; ending_intro_timer = 0.0; ending_black_alpha = 0.0; ending_black_wait = 0.0; ending_last_noah_emo = "기본"; ending_last_naye_emo = "기본"
                            
                            # 5. 튜토리얼 및 독백 초기화
                            tutorial_state = 'MONOLOGUE'; monologue_step = 0; tutorial_step = 0; tutorial_char_idx = 0.0; current_zoom = 1.0; camera_x = player.pos.x - VIEW_W / 2; camera_y = player.pos.y - VIEW_H / 2
                            _stop_all_voices(); _voice_played_monologue_step = -1; _voice_played_boss_talk_step = -1; _voice_played_boss_bubble_step = -1; _voice_played_ending_step = -1
                        elif btn_go_continue.is_clicked(event, scaled_mouse_pos) and continue_enabled: current_overlay = 'LOAD'
                        elif btn_go_quit.is_clicked(event, scaled_mouse_pos): running = False
                        
                    elif context_menu_active and app_state == APP_PLAYING:
                        cm_x, cm_y = context_menu_pos
                        if cm_x + 120 > LOGICAL_WIDTH: cm_x = LOGICAL_WIDTH - 120
                        if cm_y + 70 > LOGICAL_HEIGHT: cm_y = LOGICAL_HEIGHT - 70
                        use_rect = pygame.Rect(cm_x, cm_y, 120, 35); action2_rect = pygame.Rect(cm_x, cm_y + 35, 120, 35)
                        mx, my = scaled_mouse_pos
                        
                        if use_rect.collidepoint((mx, my)): 
                            succ, msg = False, ""
                            if context_selected_inv_idx != -1:
                                succ, msg = player.use_item(context_selected_inv_idx, False)
                            elif context_selected_qs_idx != -1:
                                succ, msg = player.use_item(context_selected_qs_idx, True)
                            
                            popup_msg = msg; popup_timer = 2.0
                            if succ:
                                if 'interact' in SOUNDS: SOUNDS['interact'].play()
                            context_menu_active = False
                            
                        elif action2_rect.collidepoint((mx, my)): 
                            if context_selected_inv_idx != -1:
                                assigning_quick_slot = True; context_menu_active = False; popup_msg = "퀵슬롯(1~4)을 지정해주세요."; popup_timer = 3.0
                            elif context_selected_qs_idx != -1:
                                moved = False
                                for i in range(12):
                                    if player.inventory[i] is None:
                                        player.inventory[i] = player.quick_slots[context_selected_qs_idx]; player.quick_slots[context_selected_qs_idx] = None; moved = True; break
                                if moved: popup_msg = "배낭으로 이동 완료!"
                                else: popup_msg = "배낭이 꽉 찼습니다!"
                                popup_timer = 2.0; context_menu_active = False
                        else: context_menu_active = False; assigning_quick_slot = False
                            
                elif event.button == 3 and player.has_bag and tutorial_state == 'DONE' and app_state == APP_PLAYING:
                    inv_cols = 3; inv_rows = 4; slot_size = 65; slot_margin = 10
                    inv_w = (slot_size * inv_cols) + (slot_margin * (inv_cols + 1)); inv_h = (slot_size * inv_rows) + (slot_margin * (inv_rows + 1)) + 50
                    inv_x = LOGICAL_WIDTH - inv_w - 40; inv_y = 330 
                    qs_w = (slot_size * 4) + (slot_margin * 5); qs_h = slot_size + (slot_margin * 2)
                    qs_x = inv_x + (inv_w - qs_w) // 2; qs_y = inv_y + inv_h + 20
                    
                    mx, my = scaled_mouse_pos; clicked_something = False
                    for r in range(inv_rows):
                        for c in range(inv_cols):
                            sx = inv_x + slot_margin + c * (slot_size + slot_margin); sy = inv_y + 50 + slot_margin + r * (slot_size + slot_margin)
                            if sx <= mx <= sx + slot_size and sy <= my <= sy + slot_size:
                                idx = r * inv_cols + c
                                if player.inventory[idx] is not None:
                                    context_menu_active = True; context_menu_pos = (mx, my); context_selected_inv_idx = idx; context_selected_qs_idx = -1; assigning_quick_slot = False; clicked_something = True; break
                        if clicked_something: break
                        
                    if not clicked_something:
                        for i in range(4):
                            bx = qs_x + slot_margin + i * (slot_size + slot_margin); by = qs_y + slot_margin
                            if bx <= mx <= bx + slot_size and by <= my <= by + slot_size:
                                if player.quick_slots[i] is not None:
                                    context_menu_active = True; context_menu_pos = (mx, my); context_selected_qs_idx = i; context_selected_inv_idx = -1; assigning_quick_slot = False; break
                                    
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1: is_mouse_down = False; mouse_buttons_held[1] = False
                elif event.button == 2: mouse_buttons_held[2] = False
                elif event.button == 3: mouse_buttons_held[3] = False
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: is_mouse_down = True; mouse_buttons_held[1] = True
                if event.button == 2: mouse_buttons_held[2] = True
                elif event.button == 3: mouse_buttons_held[3] = True
                
                # 👇 독백 종료 후 대기 상태에서 마우스 클릭 시 !로 전환
                if app_state == APP_PLAYING and tutorial_state == 'WAITING_INPUT':
                    tutorial_state = 'EXCLAMATION'; tutorial_timer = 1.0
                    if 'interact' in SOUNDS: SOUNDS['interact'].play()
                    continue
                
                # 마우스 버튼으로 INTERACT가 설정된 경우 처리
            if event.type == pygame.MOUSEBUTTONDOWN and config['keys']['INTERACT'] in [MOUSE_LEFT, MOUSE_MIDDLE, MOUSE_RIGHT]:
                btn_match = (config['keys']['INTERACT'] == MOUSE_LEFT and event.button == 1) or \
                            (config['keys']['INTERACT'] == MOUSE_MIDDLE and event.button == 2) or \
                            (config['keys']['INTERACT'] == MOUSE_RIGHT and event.button == 3)
                if btn_match and app_state == APP_PLAYING and not current_overlay and tutorial_state == 'DONE':
                    if not (boss_transition_state and boss_transition_state != 'DONE'):
                        _handle_interact_action()

            if event.type == pygame.KEYDOWN:
                
                # 👇 독백 종료 후 대기 상태에서 아무 키 입력 시 !로 전환
                if app_state == APP_PLAYING and tutorial_state == 'WAITING_INPUT':
                    tutorial_state = 'EXCLAMATION'; tutorial_timer = 1.0
                    if 'interact' in SOUNDS: SOUNDS['interact'].play()
                    continue
                
                if event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                    if current_overlay == 'ITEM_INFO':
                        current_overlay = None; viewing_item = None; popup_msg = "아이템을 확인했습니다."; popup_timer = 2.0
                        if 'enter_press' in SOUNDS: SOUNDS['enter_press'].play()
                    elif app_state == APP_CREDITS and credits_started and credits_paused and credits_can_enter:
                        credits_started = False; credits_paused = False; credits_can_enter = False
                        credits_img_group_idx = 0; credits_img_alpha = 0.0; credits_img_timer = 0.0
                        credits_img_fading_out = False; credits_img_fading_in = False
                        app_state = APP_MAIN_MENU
                        continue_enabled = False
                        play_bgm('title')
                        saves_data = {"slot_1": None, "slot_2": None, "slot_3": None}
                        write_save_data(saves_data)
                        cleared_rooms = [False] * len(MAP_DATA)
                        cols, rows = 26, 15; room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                        player = Player(room_w, room_h); player.pos.x = room_w // 2; player.pos.y = 250
                        NAYE_HOME_MAP = load_tiled_map(layer_files_home, 26, 15)
                        CLASSROOM_MAP = load_tiled_map(layer_files_class, MAP_DATA[0]['cols'], MAP_DATA[0]['rows'])
                        TOILET_MAP = load_tiled_map(layer_files_toilet, MAP_DATA[1]['cols'], MAP_DATA[1]['rows'])
                        HEALTH_MAP = load_tiled_map(layer_files_health, MAP_DATA[2]['cols'], MAP_DATA[2]['rows'])
                        GYM_MAP = load_tiled_map(layer_files_gym, MAP_DATA[3]['cols'], MAP_DATA[3]['rows'])
                        CAFETERIA_MAP = load_tiled_map(layer_files_cafeteria, MAP_DATA[4]['cols'], MAP_DATA[4]['rows'])
                        COMPUTER_MAP = load_tiled_map(layer_files_computer, MAP_DATA[5]['cols'], MAP_DATA[5]['rows'])
                        LIBRARY_MAP = load_tiled_map(layer_files_library, MAP_DATA[6]['cols'], MAP_DATA[6]['rows'])
                        PRINCIPAL_MAP = load_tiled_map(layer_files_principal, MAP_DATA[7]['cols'], MAP_DATA[7]['rows'])
                        bullets.clear(); enemy_bullets.clear(); enemies.clear(); spawners.clear(); boomerangs.clear(); chopstick_rains.clear(); dust_bursts.clear()
                        damage_texts.clear(); slash_effects.clear(); particles.clear(); dust_particles.clear()
                        dropped_items.clear(); soap_puddles.clear(); library_mines.clear(); static_waves.clear()
                        room_state = ROOM_WAITING; current_play_time = 0.0; is_mouse_down = False
                        context_menu_active = False; assigning_quick_slot = False
                        boss_phase = 1; boss_transition_state = None; boss_ref = None; boss_phase2_attack_name_timer = 0.0
                        boss_talk_state = 'NONE'; boss_talk_step = 0; boss_char_idx = 0.0
                        boss_dialogue_played = False; boss_bubble_state = 'NONE'; boss_bubble_step = 0; boss_bubble_char_idx = 0.0; boss_defeated = False; boss_death_fade_alpha = 0.0; boss_death_snapshot = None
                        player.frozen = False
                        ending_state = 'NONE'; ending_step = 0; ending_char_idx = 0.0; ending_shake_timer = 0.0; ending_delay_timer = 0.0; ending_intro_timer = 0.0; ending_fade_alpha = 255.0; ending_target_step = 0; ending_black_alpha = 0.0; ending_black_wait = 0.0; ending_last_noah_emo = "기본"; ending_last_naye_emo = "기본"
                        current_naye_emo = "기본"
                        story_step = 1; story_timer = 0.0; story_alpha = 0.0; story_state = 'VIEW'; walk_played = False; sword_draw_played = False
                        forbidden_wave_phase = 'IDLE'; blue_overlay_alpha = 0.0; forbidden_fake_death = False; forbidden_fake_death_timer = 0.0; forbidden_respawn_flash = 0.0
                        screen_shake_timer = 0.0; screen_shake_intensity = 0.0; glitch_timer = 0.0
                        death_anim_timer = 0.0; room_clear_timer = 0.5
                        tutorial_state = 'MONOLOGUE'; monologue_step = 0; tutorial_step = 0; tutorial_char_idx = 0.0
                        _stop_all_voices(); _voice_played_monologue_step = -1; _voice_played_boss_talk_step = -1; _voice_played_boss_bubble_step = -1; _voice_played_ending_step = -1
                        current_zoom = 1.0; camera_x = player.pos.x - VIEW_W / 2; camera_y = player.pos.y - VIEW_H / 2
                        
                    # 👇 나예 혼잣말 넘기기 로직
                    elif app_state == APP_PLAYING and tutorial_state == 'MONOLOGUE':
                        current_msg = monologue_messages[monologue_step]
                        if int(tutorial_char_idx) < len(current_msg): tutorial_char_idx = len(current_msg) 
                        else:
                            _stop_all_voices(); monologue_step += 1; tutorial_char_idx = 0.0
                            if 'enter_press' in SOUNDS: SOUNDS['enter_press'].play()
                            if monologue_step >= len(monologue_messages):
                                tutorial_state = 'WAITING_INPUT'
                                
                    # 👇 보스 대화 넘기기 로직 (스킵 불가)
                    elif app_state == APP_PLAYING and boss_talk_state == 'TALKING':
                        msg_data = boss_messages[boss_talk_step]
                        current_msg = msg_data["text"]
                        
                        # 글자가 모두 출력되었을 때만 엔터키가 작동합니다.
                        if int(boss_char_idx) >= len(current_msg):
                            _stop_all_voices(); boss_talk_step += 1; boss_char_idx = 0.0
                            if 'enter_press' in SOUNDS: SOUNDS['enter_press'].play()
                            if boss_talk_step >= len(boss_messages):
                                boss_talk_state = 'DONE'; boss_dialogue_played = True; boss_intro_completed_once = True
                                with open("boss_state.json", "w", encoding="utf-8") as _bsf: json.dump({"intro_completed": True}, _bsf)
                                for e in enemies:
                                    if e.type == 'boss' and not e.shockwave_after_dialogue_done:
                                        e.shockwave_after_dialogue_done = True
                                        e.dialogue_anim_active = False
                                        e.attack_timer = 999.0
                                        static_waves.append(BossShockwave(e.pos.x, e.pos.y))
                                        push_dir = player.pos - e.pos
                                        if push_dir.length() > 0: push_dir = push_dir.normalize()
                                        else: push_dir = pygame.math.Vector2(0, 1)
                                        player.push_vel = push_dir * 450
                                        max_push_dist = math.sqrt((room_w / 2) ** 2 + (room_h / 2) ** 2)
                                        player.push_timer = max_push_dist / 450 + 0.5
                                        player.inv_timer = 1.5
                                        break

                    elif app_state == APP_PLAYING and tutorial_state == 'TALKING':
                        current_msg = tutorial_messages[tutorial_step]
                        if int(tutorial_char_idx) < len(current_msg): tutorial_char_idx = len(current_msg) 
                        else:
                            tutorial_step += 1; tutorial_char_idx = 0.0
                            if 'enter_press' in SOUNDS: SOUNDS['enter_press'].play()
                            for i in range(1, 4):
                                if f'meow_{i}' in SOUNDS: SOUNDS[f'meow_{i}'].stop()
                            if tutorial_step >= len(tutorial_messages): tutorial_state = 'DONE' 
                            else:
                                next_meow = f"meow_{(tutorial_step % 3) + 1}"
                                if next_meow in SOUNDS: SOUNDS[next_meow].play()
                if event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                    
                    # ====================================================
                    # [스토리 엔터 로직 - 마지막 이미지(20)에서만 Enter로 게임 시작]
                    if app_state == APP_STORY:
                        if story_step == 20:
                            app_state = APP_PLAYING
                            current_play_time = 0.0
                            bullets.clear(); enemy_bullets.clear(); enemies.clear(); spawners.clear(); boomerangs.clear(); chopstick_rains.clear(); dust_bursts.clear()
                            dropped_items.clear(); damage_texts.clear(); slash_effects.clear(); particles.clear()
                            soap_puddles.clear(); library_mines.clear(); static_waves.clear()
                    # ====================================================

                    # 👇 엔딩 스토리 Enter 진행 (INTRO)
                    elif app_state == APP_ENDING and ending_state == 'INTRO':
                        if 'enter_press' in SOUNDS: SOUNDS['enter_press'].play()
                        if 'walk' in SOUNDS: SOUNDS['walk'].play()
                        # 이미지가 같으면 페이드 없이 바로 진행
                        if _get_ending_img_key(-1) == _get_ending_img_key(0):
                            ending_step = 0
                            ending_char_idx = 0.0
                            ending_shake_timer = 0.0
                            ending_state = 'PLAYING'
                        else:
                            ending_state = 'FADE_OUT'
                            ending_target_step = 0
                            ending_step = -1  # INTRO 이미지(ending_1)가 이전 이미지로 페이드아웃 되도록

                    # 👇 엔딩 스토리 Enter 진행 (PLAYING)
                    elif app_state == APP_ENDING and ending_state == 'PLAYING':
                        msg_data = ending_messages[ending_step]
                        current_msg = msg_data["text"]
                        if int(ending_char_idx) >= len(current_msg):
                            _stop_all_voices()
                            if 'enter_press' in SOUNDS: SOUNDS['enter_press'].play()
                            if ending_step + 1 >= len(ending_messages):
                                ending_state = 'BLACK_FADE'
                                ending_black_alpha = 0.0
                            # 👇 step 3(쇼핑하러가ㄹ…) 이후에 칼피격 사운드 재생 및 딜레이
                            elif ending_step == 3:
                                if 'hit' in SOUNDS:
                                    # 느린 속도로 재생 (pygame.mixer.Sound는 재생 속도를 직접 조절할 수 없으므로,
                                    # 볼륨을 낮추고 딜레이를 길게 줘서 느리게 들리는 효과)
                                    SOUNDS['hit'].play()
                                ending_state = 'DELAY'
                                ending_delay_timer = 2.5  # 2.5초 딜레이
                            else:
                                # 이미지가 같으면 페이드 없이 바로 진행
                                if _get_ending_img_key(ending_step) == _get_ending_img_key(ending_step + 1):
                                    ending_step += 1
                                    ending_char_idx = 0.0
                                    ending_shake_timer = 0.0
                                    ending_state = 'PLAYING'
                                else:
                                    ending_state = 'FADE_OUT'
                                    ending_target_step = ending_step + 1
                                    boss_talk_step = 0
                                    boss_char_idx = 0.0
                                    boss_dialogue_played = False
                                    if os.path.exists("boss_state.json"): os.remove("boss_state.json")
                                    boss_bubble_state = 'NONE'; boss_bubble_step = 0; boss_bubble_char_idx = 0.0
                                    boss_defeated = False
                                    boss_death_fade_alpha = 0.0
                                    player.frozen = False
                                    tutorial_state = 'MONOLOGUE'
                                    monologue_step = 0
                                    tutorial_step = 0
                                    tutorial_char_idx = 0.0
                                    current_zoom = 1.0
                                    camera_x = player.pos.x - VIEW_W / 2
                                    camera_y = player.pos.y - VIEW_H / 2

                    # 👇 기존 코드는 if를 elif로 바꿔서 그대로 둡니다.
                    elif current_overlay == 'ITEM_INFO':
                        current_overlay = None; viewing_item = None; popup_msg = "아이템을 확인했습니다."; popup_timer = 2.0
                        if 'enter_press' in SOUNDS: SOUNDS['enter_press'].play()
                        
                    # 👇 나예 혼잣말 넘기기 로직
                    elif app_state == APP_PLAYING and tutorial_state == 'MONOLOGUE' and current_map_idx != 7:
                        current_msg = monologue_messages[monologue_step]
                        if int(tutorial_char_idx) < len(current_msg): tutorial_char_idx = len(current_msg) 
                        else:
                            _stop_all_voices(); monologue_step += 1; tutorial_char_idx = 0.0
                            if 'enter_press' in SOUNDS: SOUNDS['enter_press'].play()
                            if monologue_step >= len(monologue_messages):
                                tutorial_state = 'WAITING_INPUT'
                                
                    # 👇 보스 대화 넘기기 로직 (오직 7번 보스방일 때만 엔터 입력이 작동하도록 분리)
                    elif app_state == APP_PLAYING and boss_talk_state == 'TALKING' and current_map_idx == 7:
                        msg_data = boss_messages[boss_talk_step]
                        current_msg = msg_data["text"]
                        
                        # 글자가 모두 출력되었을 때만 엔터키가 작동합니다.
                        if int(boss_char_idx) >= len(current_msg):
                            _stop_all_voices(); boss_talk_step += 1; boss_char_idx = 0.0
                            if 'enter_press' in SOUNDS: SOUNDS['enter_press'].play()
                            if boss_talk_step >= len(boss_messages):
                                boss_talk_state = 'DONE'; boss_dialogue_played = True; boss_intro_completed_once = True
                                with open("boss_state.json", "w", encoding="utf-8") as _bsf: json.dump({"intro_completed": True}, _bsf)
                                for e in enemies:
                                    if e.type == 'boss' and not e.shockwave_after_dialogue_done:
                                        e.shockwave_after_dialogue_done = True
                                        e.dialogue_anim_active = False
                                        e.attack_timer = 999.0
                                        static_waves.append(BossShockwave(e.pos.x, e.pos.y))
                                        push_dir = player.pos - e.pos
                                        if push_dir.length() > 0: push_dir = push_dir.normalize()
                                        else: push_dir = pygame.math.Vector2(0, 1)
                                        player.push_vel = push_dir * 450
                                        max_push_dist = math.sqrt((room_w / 2) ** 2 + (room_h / 2) ** 2)
                                        player.push_timer = max_push_dist / 450 + 0.5
                                        player.inv_timer = 1.5
                                        break

                    elif app_state == APP_PLAYING and boss_bubble_state == 'ACTIVE':
                        current_line = boss_bubble_lines[boss_bubble_step]
                        if int(boss_bubble_char_idx) >= len(current_line):
                            _stop_all_voices()
                            if 'enter_press' in SOUNDS: SOUNDS['enter_press'].play()
                            boss_bubble_step += 1; boss_bubble_char_idx = 0.0
                            if boss_bubble_step >= len(boss_bubble_lines):
                                boss_bubble_state = 'DONE'
                                player.frozen = False
                                for enemy in enemies:
                                    if enemy.type == 'boss':
                                        boss_transition_state = 'WIDE_SHOT'; boss_transition_timer = 2.5; boss_ref = enemy
                                        break

                    elif app_state == APP_PLAYING and tutorial_state == 'TALKING' and current_map_idx != 7:
                        current_msg = tutorial_messages[tutorial_step]
                        if int(tutorial_char_idx) < len(current_msg): tutorial_char_idx = len(current_msg) 
                        else:
                            tutorial_step += 1; tutorial_char_idx = 0.0
                            if 'enter_press' in SOUNDS: SOUNDS['enter_press'].play()
                            for i in range(1, 4):
                                if f'meow_{i}' in SOUNDS: SOUNDS[f'meow_{i}'].stop()
                            if tutorial_step >= len(tutorial_messages): tutorial_state = 'DONE' 
                            else:
                                next_meow = f"meow_{(tutorial_step % 3) + 1}"
                                if next_meow in SOUNDS: SOUNDS[next_meow].play()

                elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4] and app_state == APP_PLAYING and not current_overlay and tutorial_state == 'DONE':
                    # 👇 컷씬 중에는 퀵슬롯 무시!
                    if getattr(player, 'is_auto_walking', False) or (boss_talk_state in ['APPROACH', 'TALKING'] and current_map_idx == 7): continue
                    
                    slot_idx = event.key - pygame.K_1
                    if assigning_quick_slot: 
                        temp = player.quick_slots[slot_idx]
                        player.quick_slots[slot_idx] = player.inventory[context_selected_inv_idx]
                        player.inventory[context_selected_inv_idx] = temp
                        assigning_quick_slot = False; popup_msg = f"{slot_idx+1}번 퀵슬롯에 지정 완료!"; popup_timer = 2.0
                    else: 
                        succ, msg = player.use_item(slot_idx, True)
                        popup_msg = msg; popup_timer = 2.0
                        if succ:
                            if 'interact' in SOUNDS: SOUNDS['interact'].play()

                elif event.key == pygame.K_ESCAPE:
                    context_menu_active = False; assigning_quick_slot = False
                    if confirm_delete_slot: confirm_delete_slot = None
                    elif confirm_save_slot: confirm_save_slot = None
                    elif current_overlay: current_overlay = None; viewing_item = None; waiting_for_key = None
                    elif app_state in [APP_PLAYING, APP_GAME_OVER, APP_STORY, APP_ENDING, APP_CREDITS]: current_overlay = 'SETTINGS'
                    
                
                # 👇 키보드로 INTERACT가 설정된 경우 처리
                elif event.key == config['keys']['INTERACT'] and config['keys']['INTERACT'] not in [MOUSE_LEFT, MOUSE_MIDDLE, MOUSE_RIGHT] and app_state == APP_PLAYING and not current_overlay and tutorial_state == 'DONE':
                    if not (boss_transition_state and boss_transition_state != 'DONE') and boss_death_fade_alpha <= 0:
                        _handle_interact_action()
                
                # 👇 키보드로 ATTACK이 설정된 경우 처리 (마우스 커서 방향으로 공격)
                elif event.key == config['keys']['ATTACK'] and config['keys']['ATTACK'] not in [MOUSE_LEFT, MOUSE_MIDDLE, MOUSE_RIGHT] and app_state == APP_PLAYING and room_state in [ROOM_COMBAT, ROOM_CLEARED] and not current_overlay and tutorial_state == 'DONE':
                    if not (boss_transition_state and boss_transition_state != 'DONE') and not getattr(player, 'is_auto_walking', False) and boss_talk_state not in ['APPROACH', 'TALKING'] and boss_bubble_state != 'ACTIVE' and boss_death_fade_alpha <= 0:
                        mx, my = scaled_mouse_pos
                        target_x = mx - VIEW_MARGIN_X + camera_x; target_y = my - VIEW_MARGIN_Y + camera_y
                        _handle_attack_action(target_x, target_y)

            if current_overlay:
                if current_overlay == 'ITEM_INFO':
                    overlay_bg = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA); overlay_bg.fill((0, 0, 0, 180)); display_surface.blit(overlay_bg, (0, 0))
                    popup_rect = pygame.Rect(center_x - 350, 150, 700, 600)
                    pygame.draw.rect(display_surface, (40, 40, 45), popup_rect, border_radius=15); pygame.draw.rect(display_surface, (200, 200, 200), popup_rect, 3, border_radius=15)
                    
                    item_name = viewing_item if viewing_item else "아이템"
                    
                    desc = "아이템 설명이 없습니다."
                    if item_name == "회복물약": desc = "사용 시 체력을 10 회복 합니다."
                    elif item_name == "방어막": desc = "강력한 공격을 막을 때 유용할지도..?\n단 하나 뿐이니 신중하게 쓰자."
                    elif item_name == "배낭": desc = "배낭안에 아이템을 우클릭하여 조정할 수 있다."
                    
                    img_rect = pygame.Rect(center_x - 280, 200, 200, 200) 
                    pygame.draw.rect(display_surface, (60, 60, 70), img_rect, border_radius=10)
                    
                    if item_name == "회복물약" and 'potion' in IMAGES:
                        big_img = pygame.transform.scale(IMAGES['potion'], (120, 120))
                        display_surface.blit(big_img, big_img.get_rect(center=img_rect.center))
                    elif item_name == "방어막" and 'shield' in IMAGES:
                        big_img = pygame.transform.scale(IMAGES['shield'], (120, 120))
                        display_surface.blit(big_img, big_img.get_rect(center=img_rect.center))
                    elif item_name == "배낭":
                        # 배낭은 따로 이미지가 없으니 갈색 가방 모양으로 심플하게 그려줍니다
                        pygame.draw.rect(display_surface, (180, 100, 50), (img_rect.centerx - 40, img_rect.centery - 40, 80, 80), border_radius=10)
                        pygame.draw.rect(display_surface, (120, 60, 30), (img_rect.centerx - 40, img_rect.centery - 40, 80, 80), 5, border_radius=10)
                        pygame.draw.arc(display_surface, (120, 60, 30), (img_rect.centerx - 20, img_rect.centery - 60, 40, 40), 0, 3.1415, 5)
                    else:
                        pygame.draw.circle(display_surface, (255, 50, 50), img_rect.center, 50); pygame.draw.circle(display_surface, (255, 150, 150), img_rect.center, 50, 5)
                    
                    name_inner = huge_font.render(item_name, True, (255, 255, 255))
                    name_out = huge_font.render(item_name, True, (0, 0, 0))
                    name_rect = name_inner.get_rect(midleft=(center_x - 30, img_rect.centery))
                    
                    offsets = [(-1,-1), (0,-1), (1,-1), (-1,0), (1,0), (-1,1), (0,1), (1,1)]
                    for dx, dy in offsets:
                        display_surface.blit(name_out, (name_rect.x + dx, name_rect.y + dy))
                    display_surface.blit(name_inner, name_rect)
                    
                    enter_text = "enter를 눌러 확인" if item_name == "배낭" else "enter를 눌러 배낭에 넣기"
                    enter_surf = small_font.render(enter_text, True, (150, 150, 150))
                    enter_rect = enter_surf.get_rect(center=(center_x, 700))
                    display_surface.blit(enter_surf, enter_rect)
                    
                    lines = []
                    for paragraph in desc.splitlines():
                        current_line = ""
                        for char in paragraph:
                            test_line = current_line + char
                            if font.size(test_line)[0] > 600:
                                lines.append(current_line)
                                current_line = char
                            else: 
                                current_line = test_line
                        if current_line:
                            lines.append(current_line)
                
                    desc_start_y = img_rect.bottom + 40
                    for i, line in enumerate(lines):
                        line_surf = font.render(line.strip(), True, (200, 200, 200))
                        display_surface.blit(line_surf, (center_x - 300, desc_start_y + i * 40))
                    
                elif current_overlay == 'DIFFICULTY':
                    if difficulty_sub == 'SELECT':
                        if btn_diff_easy.is_clicked(event, scaled_mouse_pos):
                            selected_difficulty = 'easy'; difficulty_sub = 'DESC'
                        elif btn_diff_normal.is_clicked(event, scaled_mouse_pos):
                            selected_difficulty = 'normal'; difficulty_sub = 'DESC'
                        elif btn_diff_hard.is_clicked(event, scaled_mouse_pos):
                            selected_difficulty = 'hard'; difficulty_sub = 'DESC'
                        elif btn_diff_x.is_clicked(event, scaled_mouse_pos):
                            current_overlay = None
                    elif difficulty_sub == 'DESC' and selected_difficulty:
                        if btn_diff_back.is_clicked(event, scaled_mouse_pos):
                            difficulty_sub = 'SELECT'
                        elif btn_diff_confirm.is_clicked(event, scaled_mouse_pos):
                            current_overlay = None
                            current_difficulty = selected_difficulty
                            current_map_idx = -1; cleared_rooms = [False] * len(MAP_DATA); cols, rows = 26, 15; room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                            player = Player(room_w, room_h); player.pos.x = room_w // 2; player.pos.y = 250
                            NAYE_HOME_MAP = load_tiled_map(layer_files_home, 26, 15)
                            CLASSROOM_MAP = load_tiled_map(layer_files_class, MAP_DATA[0]['cols'], MAP_DATA[0]['rows'])
                            TOILET_MAP = load_tiled_map(layer_files_toilet, MAP_DATA[1]['cols'], MAP_DATA[1]['rows'])
                            HEALTH_MAP = load_tiled_map(layer_files_health, MAP_DATA[2]['cols'], MAP_DATA[2]['rows'])
                            GYM_MAP = load_tiled_map(layer_files_gym, MAP_DATA[3]['cols'], MAP_DATA[3]['rows'])
                            CAFETERIA_MAP = load_tiled_map(layer_files_cafeteria, MAP_DATA[4]['cols'], MAP_DATA[4]['rows'])
                            COMPUTER_MAP = load_tiled_map(layer_files_computer, MAP_DATA[5]['cols'], MAP_DATA[5]['rows'])
                            LIBRARY_MAP = load_tiled_map(layer_files_library, MAP_DATA[6]['cols'], MAP_DATA[6]['rows'])
                            PRINCIPAL_MAP = load_tiled_map(layer_files_principal, MAP_DATA[7]['cols'], MAP_DATA[7]['rows'])
                            bullets.clear(); enemy_bullets.clear(); enemies.clear(); spawners.clear(); boomerangs.clear(); chopstick_rains.clear(); dust_bursts.clear(); damage_texts.clear(); slash_effects.clear(); particles.clear(); dust_particles.clear(); dropped_items.clear(); soap_puddles.clear(); library_mines.clear(); static_waves.clear()
                            room_state = ROOM_WAITING; current_play_time = 0.0; app_state = APP_STORY
                            story_step = 1; story_timer = 0.0; story_alpha = 0.0; story_state = 'VIEW'; walk_played = False; sword_draw_played = False
                            is_mouse_down = False; context_menu_active = False; assigning_quick_slot = False
                            boss_phase = 1; boss_transition_state = None; boss_ref = None
                            boss_talk_state = 'NONE'; boss_talk_step = 0; boss_char_idx = 0.0; boss_dialogue_played = False
                            boss_intro_completed_once = False
                            if os.path.exists("boss_state.json"): os.remove("boss_state.json")
                            boss_bubble_state = 'NONE'; boss_bubble_step = 0; boss_bubble_char_idx = 0.0
                            boss_defeated = False; boss_death_fade_alpha = 0.0; player.frozen = False
                            ending_state = 'NONE'; ending_step = 0; ending_char_idx = 0.0; ending_shake_timer = 0.0; ending_delay_timer = 0.0; ending_intro_timer = 0.0; ending_black_alpha = 0.0; ending_black_wait = 0.0; ending_last_noah_emo = "기본"; ending_last_naye_emo = "기본"
                            current_naye_emo = "기본"
                            tutorial_state = 'MONOLOGUE'; monologue_step = 0; tutorial_step = 0; tutorial_char_idx = 0.0; current_zoom = 1.0; camera_x = player.pos.x - VIEW_W / 2; camera_y = player.pos.y - VIEW_H / 2
                            _stop_all_voices(); _voice_played_monologue_step = -1; _voice_played_boss_talk_step = -1; _voice_played_boss_bubble_step = -1; _voice_played_ending_step = -1
                            difficulty_sub = 'SELECT'
                elif current_overlay == 'SETTINGS':
                    if waiting_for_key:
                        if event.type == pygame.KEYDOWN:
                            if event.key != pygame.K_ESCAPE:
                                for _a, _v in config['keys'].items():
                                    if _a != waiting_for_key and _v == event.key: config['keys'][_a] = None
                                config['keys'][waiting_for_key] = event.key; save_config()
                            waiting_for_key = None
                        elif event.type == pygame.MOUSEBUTTONDOWN:
                            _mv = {1: MOUSE_LEFT, 2: MOUSE_MIDDLE, 3: MOUSE_RIGHT}.get(event.button)
                            if _mv is not None:
                                for _a, _v in config['keys'].items():
                                    if _a != waiting_for_key and _v == _mv: config['keys'][_a] = None
                                config['keys'][waiting_for_key] = _mv; save_config(); waiting_for_key = None
                    elif not waiting_for_key:
                        if btn_video.is_clicked(event, scaled_mouse_pos): current_tab = "VIDEO"
                        elif btn_audio.is_clicked(event, scaled_mouse_pos): current_tab = "AUDIO"
                        elif btn_keys.is_clicked(event, scaled_mouse_pos): current_tab = "KEYS"
                        if app_state == APP_MAIN_MENU and btn_close_overlay.is_clicked(event, scaled_mouse_pos): current_overlay = None
                        elif app_state in [APP_PLAYING, APP_GAME_OVER, APP_STORY, APP_ENDING, APP_CREDITS]:
                            if btn_close_settings_game.is_clicked(event, scaled_mouse_pos): current_overlay = None
                            if btn_return_main.is_clicked(event, scaled_mouse_pos):
                                app_state = APP_MAIN_MENU; current_overlay = None; current_map_idx = -1
                                saves_data = get_save_data()
                                continue_enabled = any(saves_data.get(f"slot_{i+1}") is not None for i in range(3))
                                cols, rows = 26, 15; room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                                player = Player(room_w, room_h); bullets.clear(); enemy_bullets.clear(); enemies.clear(); spawners.clear(); boomerangs.clear(); chopstick_rains.clear(); dust_bursts.clear()
                                room_state = ROOM_WAITING; current_play_time = 0.0; cleared_rooms = [False] * len(MAP_DATA) 
                                damage_texts.clear(); slash_effects.clear(); particles.clear(); dust_particles.clear(); dropped_items.clear(); soap_puddles.clear(); library_mines.clear(); static_waves.clear()
                                context_menu_active = False; assigning_quick_slot = False

                        if confirm_reset_tab:
                            if btn_reset_confirm_yes.is_clicked(event, scaled_mouse_pos):
                                if confirm_reset_tab == "VIDEO": update_display('WINDOW'); config['display_mode'] = 'WINDOW'; save_config()
                                elif confirm_reset_tab == "AUDIO": config['volume'] = 50; config['bgm_volume'] = 50; config['voice_volume'] = 50; update_sound_volumes(); save_config()
                                elif confirm_reset_tab == "KEYS": config['keys'] = {'UP': pygame.K_w, 'DOWN': pygame.K_s, 'LEFT': pygame.K_a, 'RIGHT': pygame.K_d, 'INTERACT': pygame.K_e, 'DASH': pygame.K_SPACE, 'ATTACK': MOUSE_LEFT}; save_config()
                                confirm_reset_tab = None
                            elif btn_reset_confirm_no.is_clicked(event, scaled_mouse_pos): confirm_reset_tab = None
                        elif current_tab == "VIDEO":
                            if btn_window.is_clicked(event, scaled_mouse_pos): update_display('WINDOW')
                            if btn_borderless.is_clicked(event, scaled_mouse_pos): update_display('BORDERLESS')
                            if btn_fullscreen.is_clicked(event, scaled_mouse_pos): update_display('FULLSCREEN')
                            if btn_reset_defaults.is_clicked(event, scaled_mouse_pos): confirm_reset_tab = "VIDEO"
                        elif current_tab == "AUDIO":
                            if btn_vol_down.is_clicked(event, scaled_mouse_pos): config['volume'] = max(0, config['volume'] - 10); update_sound_volumes(); save_config()
                            if btn_vol_up.is_clicked(event, scaled_mouse_pos): config['volume'] = min(100, config['volume'] + 10); update_sound_volumes(); save_config()
                            if btn_bgm_vol_down.is_clicked(event, scaled_mouse_pos): config['bgm_volume'] = max(0, config.get('bgm_volume', 50) - 10); update_sound_volumes(); save_config()
                            if btn_bgm_vol_up.is_clicked(event, scaled_mouse_pos): config['bgm_volume'] = min(100, config.get('bgm_volume', 50) + 10); update_sound_volumes(); save_config()
                            if btn_voice_vol_down.is_clicked(event, scaled_mouse_pos): config['voice_volume'] = max(0, config['voice_volume'] - 10); update_sound_volumes(); save_config()
                            if btn_voice_vol_up.is_clicked(event, scaled_mouse_pos): config['voice_volume'] = min(100, config['voice_volume'] + 10); update_sound_volumes(); save_config()
                            if btn_reset_defaults.is_clicked(event, scaled_mouse_pos): confirm_reset_tab = "AUDIO"
                        elif current_tab == "KEYS":
                            for action, btn in key_buttons.items():
                                if btn.is_clicked(event, scaled_mouse_pos):
                                    waiting_for_key = action; break
                            if btn_reset_defaults.is_clicked(event, scaled_mouse_pos): confirm_reset_tab = "KEYS"
                            
                elif current_overlay in ['SAVE', 'LOAD']:
                    if confirm_delete_slot:
                        if btn_confirm_yes_del.is_clicked(event, scaled_mouse_pos): saves_data[f"slot_{confirm_delete_slot}"] = None; write_save_data(saves_data); confirm_delete_slot = None 
                        elif btn_confirm_no.is_clicked(event, scaled_mouse_pos): confirm_delete_slot = None 
                    elif confirm_save_slot:
                        if btn_confirm_yes_save.is_clicked(event, scaled_mouse_pos):
                            saves_data[f"slot_{confirm_save_slot}"] = {
                                "map_idx": current_map_idx, "play_time": current_play_time, "player_x": player.pos.x, "player_y": player.pos.y, "room_state": room_state,
                                "cleared_rooms": cleared_rooms, "enemies": [{"x": e.pos.x, "y": e.pos.y, "hp": e.hp, "enemy_type": e.type} for e in enemies],
                                "has_bag": player.has_bag, "inventory": player.inventory, "quick_slots": player.quick_slots, "seen_items": player.seen_items,
                                "player_hp": player.hp, "player_max_hp": player.max_hp, "player_has_shield": player.has_shield,
                                "dropped_items": [{"x": d.pos.x, "y": d.pos.y, "type": d.item_type} for d in dropped_items],
                                "controls_reversed": player.controls_reversed, "attack_disabled": player.attack_disabled,
                                "boss_intro_completed_once": boss_intro_completed_once,
                                "difficulty": current_difficulty
                            }
                            write_save_data(saves_data); confirm_save_slot = None; current_overlay = None; continue_enabled = True
                        elif btn_confirm_no.is_clicked(event, scaled_mouse_pos): confirm_save_slot = None
                    else:
                        if btn_close_overlay.is_clicked(event, scaled_mouse_pos): current_overlay = None; continue
                        for i in range(3):
                            slot_key = f"slot_{i+1}"
                            if saves_data[slot_key] and delete_buttons[i].is_clicked(event, scaled_mouse_pos): confirm_delete_slot = i + 1; break 
                            if slot_buttons[i].is_clicked(event, scaled_mouse_pos):
                                if current_overlay == 'SAVE': confirm_save_slot = i + 1 
                                elif current_overlay == 'LOAD' and saves_data[slot_key]:
                                    sd = saves_data[slot_key]
                                    current_map_idx = sd.get("map_idx", -1)
                                    cleared_rooms = sd.get("cleared_rooms", [False] * len(MAP_DATA))
                                    if current_map_idx == -1: cols, rows = 26, 15 
                                    else: cols, rows = MAP_DATA[current_map_idx]['cols'], MAP_DATA[current_map_idx]['rows']
                                    room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                                    current_play_time = sd.get("play_time", 0.0); player.pos.x, player.pos.y = sd["player_x"], sd["player_y"]
                                    player.hp = sd.get("player_hp", 100); player.max_hp = sd.get("player_max_hp", 100); player.has_shield = sd.get("player_has_shield", False)
                                    player.inv_timer = 2.0
                                    player.has_bag = sd.get("has_bag", False); player.inventory = sd.get("inventory", [None]*12); player.quick_slots = sd.get("quick_slots", [None]*4)
                                    player.seen_items = sd.get("seen_items", [])
                                    room_state = sd["room_state"]
                                    current_difficulty = sd.get("difficulty", "normal")
                                    NAYE_HOME_MAP = load_tiled_map(layer_files_home, 26, 15)
                                    if player.has_bag:
                                        for r in range(len(NAYE_HOME_MAP)):
                                            for c in range(len(NAYE_HOME_MAP[0])):
                                                if NAYE_HOME_MAP[r][c] == 3: NAYE_HOME_MAP[r][c] = 0
                                    enemies.clear(); spawners.clear(); enemy_bullets.clear(); boomerangs.clear(); chopstick_rains.clear(); dust_bursts.clear(); dropped_items.clear()
                                    for e in sd["enemies"]:
                                        en = Enemy(e["x"], e["y"], enemy_type=e.get("enemy_type", "normal")); en.hp = e["hp"]; enemies.append(en)
                                    for d in sd.get("dropped_items", []):
                                        dropped_items.append(DroppedItem(d["x"], d["y"], d.get("type", "회복물약")))
                                    player.controls_reversed = sd.get("controls_reversed", False)
                                    player.attack_disabled = sd.get("attack_disabled", False)
                                    player.dust_progress = 0.0; player.frozen = False; player.stun_timer = 0.0; player.push_timer = 0.0
                                    bullets.clear(); damage_texts.clear(); slash_effects.clear(); particles.clear(); dust_particles.clear()
                                    soap_puddles.clear(); library_mines.clear(); static_waves.clear()
                                    boss_phase = 1; boss_transition_state = None; boss_ref = None; boss_phase2_attack_name_timer = 0.0
                                    boss_talk_state = 'NONE'; boss_talk_step = 0; boss_char_idx = 0.0; boss_dialogue_played = False
                                    boss_intro_completed_once = sd.get("boss_intro_completed_once", False)
                                    if boss_intro_completed_once and os.path.exists("boss_state.json"):
                                        pass
                                    elif os.path.exists("boss_state.json"):
                                        with open("boss_state.json", "r", encoding="utf-8") as _bsf:
                                            boss_intro_completed_once = json.load(_bsf).get("intro_completed", False)
                                    boss_bubble_state = 'NONE'; boss_bubble_step = 0; boss_bubble_char_idx = 0.0
                                    boss_defeated = False; boss_death_fade_alpha = 0.0; boss_death_snapshot = None
                                    forbidden_wave_phase = 'IDLE'; blue_overlay_alpha = 0.0; forbidden_fake_death = False; forbidden_fake_death_timer = 0.0; forbidden_respawn_flash = 0.0
                                    screen_shake_timer = 0.0; screen_shake_intensity = 0.0; glitch_timer = 0.0
                                    app_state = APP_PLAYING; current_overlay = None; break

                elif current_overlay == 'LEAVE_HOME':
                    if btn_leave_yes.is_clicked(event, scaled_mouse_pos):
                        current_map_idx = 0; cols, rows = MAP_DATA[current_map_idx]['cols'], MAP_DATA[current_map_idx]['rows']; room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                        player.pos.x, player.pos.y = 90, room_h // 2; room_state = ROOM_CLEARED if cleared_rooms[current_map_idx] else ROOM_WAITING
                        bullets.clear(); enemy_bullets.clear(); enemies.clear(); spawners.clear(); boomerangs.clear(); chopstick_rains.clear(); dust_bursts.clear(); damage_texts.clear(); slash_effects.clear(); particles.clear(); dropped_items.clear()
                        boss_phase = 1; boss_transition_state = None; current_overlay = None; boss_phase2_attack_name_timer = 0.0
                    elif btn_leave_no.is_clicked(event, scaled_mouse_pos): current_overlay = None

            elif app_state == APP_MAIN_MENU:
                if menu_btn_start.is_clicked(event, scaled_mouse_pos):
                    current_overlay = 'DIFFICULTY'; difficulty_sub = 'SELECT'; selected_difficulty = None
                elif menu_btn_continue.is_clicked(event, scaled_mouse_pos) and continue_enabled: current_overlay = 'LOAD'
                elif menu_btn_settings.is_clicked(event, scaled_mouse_pos): current_overlay = 'SETTINGS'
                elif menu_btn_quit.is_clicked(event, scaled_mouse_pos): running = False

            elif app_state == APP_PLAYING and room_state in [ROOM_COMBAT, ROOM_CLEARED] and tutorial_state == 'DONE':
                if boss_transition_state and boss_transition_state in ['EXPLOSION', 'FADE_OUT', 'RESTORE_CAMERA']: pass
                elif getattr(player, 'is_auto_walking', False) or boss_talk_state in ['APPROACH', 'TALKING']: pass
                elif boss_transition_state in ['WIDE_SHOT', 'METEOR_FALL']: pass
                elif boss_bubble_state == 'ACTIVE': pass
                elif boss_death_fade_alpha > 0: pass
                # 👇 ATTACK 키가 마우스 버튼인 경우 처리
                elif event.type == pygame.MOUSEBUTTONDOWN and not context_menu_active:
                    attack_key = config['keys'].get('ATTACK')
                    btn_match = (attack_key == MOUSE_LEFT and event.button == 1) or \
                                (attack_key == MOUSE_MIDDLE and event.button == 2) or \
                                (attack_key == MOUSE_RIGHT and event.button == 3)
                    if btn_match:
                        mx, my = scaled_mouse_pos
                        if VIEW_MARGIN_X <= mx <= VIEW_MARGIN_X + VIEW_W and VIEW_MARGIN_Y <= my <= VIEW_MARGIN_Y + VIEW_H:
                            target_x = mx - VIEW_MARGIN_X + camera_x; target_y = my - VIEW_MARGIN_Y + camera_y
                            _handle_attack_action(target_x, target_y)

        # ==================== 게임 로직 처리 ====================
        if not current_overlay and app_state in [APP_PLAYING, APP_DEATH_ANIMATION, APP_ENDING, APP_CREDITS]:
            is_game_paused = False
            if app_state == APP_ENDING: is_game_paused = True
            if app_state == APP_CREDITS: is_game_paused = True
            if boss_transition_state in ['EXPLOSION', 'FADE_OUT', 'RESTORE_CAMERA']: is_game_paused = True
            if app_state == APP_DEATH_ANIMATION: is_game_paused = True
            # 👇 컷씬 중에는 게임 시간을 멈춥니다.
            if boss_talk_state in ['APPROACH', 'TALKING']: is_game_paused = True
            if boss_death_fade_alpha > 0: is_game_paused = True  # 페이드아웃 중 게임 멈춤
            
            # 👇 보스 사망 후 화면 페이드아웃 처리 (천천히 어두워짐)
            if boss_death_fade_alpha > 0 and boss_death_fade_alpha < 255:
                boss_death_fade_alpha += dt * 50  # 천천히 어두워짐 (약 5초)
                if boss_death_fade_alpha >= 255:
                    boss_death_fade_alpha = 255
                    # 완전히 어두워지면 엔딩 시퀀스 진입
                    app_state = APP_ENDING
                    ending_state = 'INTRO'
                    ending_step = 0
                    ending_char_idx = 0.0
                    ending_shake_timer = 0.0
                    ending_delay_timer = 0.0
                    ending_fade_alpha = 255.0
                    ending_target_step = 0
                    ending_black_alpha = 0.0
                    ending_black_wait = 0.0
                    ending_last_noah_emo = "기본"
                    ending_last_naye_emo = "기본"
                    ending_intro_timer = 2.0
            
            # 👇 보스전 자동 걷기 연출 및 대화 속도 처리
            if boss_talk_state == 'APPROACH':
                player.is_auto_walking = True # 👈 자동 걷기 애니메이션 ON
                player.pos.y -= player.normal_speed * 0.4 * dt 
                player.facing = 'up'
                player.frame_index += player.animation_speed * dt
                
                _boss_e = next((e for e in enemies if e.type == 'boss'), None)
                if _boss_e and len(IMAGES.get('boss_dialogue', [])) >= 10:
                    _boss_e.dialogue_anim_active = True
                    _boss_e.dialogue_anim_frame += _boss_e.dialogue_anim_speed * dt
                    max_frame = 10 if _boss_e.dialogue_anim_cycle == 0 else 8
                    if int(_boss_e.dialogue_anim_frame) >= max_frame:
                        _boss_e.dialogue_anim_frame = 0.0
                        _boss_e.dialogue_anim_cycle = (_boss_e.dialogue_anim_cycle + 1) % 3
                
                if _boss_e and (_boss_e.pos.y - camera_y) >= VIEW_H * 0.3: # 화면 중앙~상단 사이
                    boss_talk_state = 'TALKING'; player.frame_index = 0
                    player.is_auto_walking = False # 👈 정지 시 애니메이션 OFF
            
            elif boss_talk_state == 'TALKING':
                msg_data = boss_messages[boss_talk_step]
                speed = 3.0 if msg_data.get("speed") == "very_slow" else (2.0 if msg_data.get("style") == "blood" else 30.0)
                boss_char_idx += dt * speed
                if boss_talk_step != _voice_played_boss_talk_step and boss_talk_step in boss_talk_voice_map:
                    _voice_played_boss_talk_step = boss_talk_step
                    _vk = f'voice_{boss_talk_voice_map[boss_talk_step]:02d}'
                    if _vk in SOUNDS: SOUNDS[_vk].play()
                _boss_e = next((e for e in enemies if e.type == 'boss'), None)
                if _boss_e and len(IMAGES.get('boss_dialogue', [])) >= 10:
                    _boss_e.dialogue_anim_active = True
                    _boss_e.dialogue_anim_frame += _boss_e.dialogue_anim_speed * dt
                    max_frame = 10 if _boss_e.dialogue_anim_cycle == 0 else 8
                    if int(_boss_e.dialogue_anim_frame) >= max_frame:
                        _boss_e.dialogue_anim_frame = 0.0
                        _boss_e.dialogue_anim_cycle = (_boss_e.dialogue_anim_cycle + 1) % 3

            # 👇 엔딩 스토리 순차 페이드 처리 (사라짐 → 등장)
            if app_state == APP_ENDING and ending_state == 'FADE_OUT':
                ending_fade_alpha -= dt * 150
                if ending_fade_alpha <= 0:
                    ending_fade_alpha = 0
                    ending_state = 'FADE_IN'
                    ending_step = ending_target_step
                    ending_char_idx = 0.0
                    ending_shake_timer = 0.0
                    if ending_step == 0 and 'walk' in SOUNDS: SOUNDS['walk'].stop()
            elif app_state == APP_ENDING and ending_state == 'FADE_IN':
                ending_fade_alpha += dt * 150
                if ending_fade_alpha >= 255:
                    ending_fade_alpha = 255
                    ending_state = 'PLAYING'

            # 👇 엔딩 스토리 텍스트 진행
            if app_state == APP_ENDING and ending_state == 'PLAYING':
                msg_data = ending_messages[ending_step]
                style = msg_data.get("style", "normal")
                if style == "ending_blood":
                    ending_char_idx += dt * 3.0  # 한 글자씩 천천히 (속도 향상)
                    ending_shake_timer += dt
                else:
                    ending_char_idx += dt * 20.0  # 일반 텍스트 속도 (빠르게)
                if ending_step != _voice_played_ending_step and 0 <= ending_step < len(ending_messages):
                    _voice_played_ending_step = ending_step
                    _vk = f'voice_{ending_step + 16:02d}'
                    if _vk in SOUNDS: SOUNDS[_vk].play()

            # 👇 엔딩 스토리 DELAY 상태 처리 (칼피격 사운드 재생 후 대기)
            if app_state == APP_ENDING and ending_state == 'DELAY':
                ending_delay_timer -= dt
                if ending_delay_timer <= 0:
                    # 다음 step이 마지막을 넘으면 검은 화면 페이드
                    if ending_step + 1 >= len(ending_messages):
                        ending_state = 'BLACK_FADE'
                        ending_black_alpha = 0.0
                    # 이미지가 같으면 페이드 없이 바로 진행, 다르면 페이드
                    elif _get_ending_img_key(ending_step) == _get_ending_img_key(ending_step + 1):
                        ending_state = 'PLAYING'
                        ending_step += 1
                        ending_char_idx = 0.0
                        ending_shake_timer = 0.0
                    else:
                        ending_state = 'FADE_OUT'
                        ending_target_step = ending_step + 1

            # 👇 엔딩 스토리 BLACK_FADE 상태 처리 (화면이 검은색으로 천천히 변함)
            if app_state == APP_ENDING and ending_state == 'BLACK_FADE':
                ending_black_alpha += dt * 60  # 천천히 자연스레 검정색으로
                if ending_black_alpha >= 255:
                    ending_black_alpha = 255
                    ending_state = 'BLACK_WAIT'
                    ending_black_wait = 3.0  # 3초 대기
            elif app_state == APP_ENDING and ending_state == 'BLACK_WAIT':
                ending_black_wait -= dt
                if ending_black_wait <= 0:
                    app_state = APP_CREDITS
                    ending_state = 'NONE'
                    credits_scroll_y = LOGICAL_HEIGHT + 50.0
                    credits_started = True
                    credits_paused = False
                    credits_pause_timer = 0.0
                    credits_can_enter = False
                    credits_img_group_idx = 0
                    credits_img_alpha = 0.0
                    credits_img_timer = 0.0
                    credits_img_fading_out = False
                    credits_img_fading_in = True
                    continue_enabled = False
                    play_bgm('credits')
                    saves_data = {"slot_1": None, "slot_2": None, "slot_3": None}
                    write_save_data(saves_data)
                    cleared_rooms = [False] * len(MAP_DATA)
                    cols, rows = 26, 15
                    room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                    player = Player(room_w, room_h)
                    player.pos.x = room_w // 2
                    player.pos.y = 250
                    NAYE_HOME_MAP = load_tiled_map(layer_files_home, 26, 15)
                    CLASSROOM_MAP = load_tiled_map(layer_files_class, MAP_DATA[0]['cols'], MAP_DATA[0]['rows'])
                    TOILET_MAP = load_tiled_map(layer_files_toilet, MAP_DATA[1]['cols'], MAP_DATA[1]['rows'])
                    HEALTH_MAP = load_tiled_map(layer_files_health, MAP_DATA[2]['cols'], MAP_DATA[2]['rows'])
                    GYM_MAP = load_tiled_map(layer_files_gym, MAP_DATA[3]['cols'], MAP_DATA[3]['rows'])
                    CAFETERIA_MAP = load_tiled_map(layer_files_cafeteria, MAP_DATA[4]['cols'], MAP_DATA[4]['rows'])
                    COMPUTER_MAP = load_tiled_map(layer_files_computer, MAP_DATA[5]['cols'], MAP_DATA[5]['rows'])
                    LIBRARY_MAP = load_tiled_map(layer_files_library, MAP_DATA[6]['cols'], MAP_DATA[6]['rows'])
                    PRINCIPAL_MAP = load_tiled_map(layer_files_principal, MAP_DATA[7]['cols'], MAP_DATA[7]['rows'])
                    bullets.clear(); enemy_bullets.clear(); enemies.clear(); spawners.clear(); boomerangs.clear(); chopstick_rains.clear(); dust_bursts.clear()
                    damage_texts.clear(); slash_effects.clear(); particles.clear(); dust_particles.clear()
                    dropped_items.clear(); soap_puddles.clear(); library_mines.clear(); static_waves.clear()
                    room_state = ROOM_WAITING
                    current_play_time = 0.0
                    is_mouse_down = False
                    context_menu_active = False
                    assigning_quick_slot = False
                    boss_phase = 1
                    boss_transition_state = None
                    boss_ref = None
                    boss_talk_state = 'NONE'
                    boss_talk_step = 0
                    boss_char_idx = 0.0
                    boss_dialogue_played = False
                    boss_bubble_state = 'NONE'; boss_bubble_step = 0; boss_bubble_char_idx = 0.0
                    boss_defeated = False
                    boss_death_fade_alpha = 0.0
                    player.frozen = False
                    tutorial_state = 'MONOLOGUE'
                    monologue_step = 0
                    _stop_all_voices(); _voice_played_monologue_step = -1; _voice_played_boss_talk_step = -1; _voice_played_boss_bubble_step = -1; _voice_played_ending_step = -1
                    tutorial_step = 0
                    tutorial_char_idx = 0.0
                    current_zoom = 1.0
                    camera_x = player.pos.x - VIEW_W / 2
                    camera_y = player.pos.y - VIEW_H / 2
            
            # 👇 엔딩 크레딧 스크롤 업데이트
            if app_state == APP_CREDITS and credits_started and not credits_paused:
                credits_scroll_y -= credits_scroll_speed * dt
                last_line_h = credits_font_last.get_height() + 30
                line_h = credits_font_body.get_height() + 25
                title_h = credits_font_title.get_height() + 40
                total_credits_height = 0
                for style, text in credits_lines:
                    if style == "title":
                        total_credits_height += title_h
                    elif style == "last":
                        total_credits_height += last_line_h
                    else:
                        total_credits_height += line_h
                target_y = LOGICAL_HEIGHT // 2 - last_line_h // 2
                last_line_top = credits_scroll_y + total_credits_height - last_line_h
                if last_line_top <= target_y:
                    credits_scroll_y += target_y - last_line_top
                    credits_paused = True
                    credits_pause_timer = 0.0
                    credits_can_enter = False
                num_groups = len(credits_image_groups)
                if num_groups > 0:
                    start_y = LOGICAL_HEIGHT + 50.0
                    total_dist = start_y + total_credits_height - last_line_h - target_y
                    total_time = total_dist / credits_scroll_speed if credits_scroll_speed > 0 else 1.0
                    time_per_group = total_time / num_groups
                    fade_dur = min(1.0, time_per_group * 0.3)
                    credits_img_timer += dt
                    if credits_img_fading_in:
                        credits_img_alpha += dt * (255.0 / max(0.01, fade_dur))
                        if credits_img_alpha >= 255.0:
                            credits_img_alpha = 255.0
                            credits_img_fading_in = False
                    elif not credits_img_fading_out:
                        if credits_img_timer >= time_per_group - fade_dur:
                            credits_img_fading_out = True
                    if credits_img_fading_out:
                        credits_img_alpha -= dt * (255.0 / max(0.01, fade_dur))
                        if credits_img_alpha <= 0:
                            credits_img_alpha = 0.0
                            credits_img_fading_out = False
                            credits_img_group_idx += 1
                            if credits_img_group_idx >= num_groups:
                                credits_img_group_idx = num_groups - 1
                            credits_img_timer = 0.0
                            credits_img_fading_in = True
            elif app_state == APP_CREDITS and credits_started and credits_paused:
                if not credits_can_enter:
                    credits_pause_timer += dt
                    if credits_pause_timer >= 3.0:
                        credits_can_enter = True
            
            if app_state == APP_DEATH_ANIMATION:
                death_anim_timer -= dt
                player.dust_progress = 1.0 - (max(0, death_anim_timer) / 3.0)
                if player.dust_progress < 1.0:
                    for _ in range(5):
                        wx = player.pos.x + random.uniform(-15, 15); wy = player.pos.y - 30 + (60 * player.dust_progress)
                        dust_particles.append(DustParticle(wx, wy))
                for dp in dust_particles[:]:
                    dp.update(dt)
                    if dp.lifetime <= 0: dust_particles.remove(dp)
                if death_anim_timer <= -1.0:
                    app_state = APP_GAME_OVER
                    continue_enabled = True

            if app_state == APP_PLAYING and player.hp <= 0:
                app_state = APP_DEATH_ANIMATION; death_anim_timer = 3.0; player.dust_progress = 0.0; dust_particles.clear()
                pygame.mixer.music.stop()
                
            if boss_transition_state and boss_transition_state != 'DONE':
                if boss_transition_state == 'WIDE_SHOT':
                    boss_transition_timer -= dt
                    if boss_transition_timer <= 0:
                        boss_transition_state = 'METEOR_FALL'; meteor_pos = pygame.math.Vector2(boss_ref.pos.x, boss_ref.pos.y - 1200) 
                elif boss_transition_state == 'METEOR_FALL':
                    meteor_pos.y += 400 * dt
                    meteor_frame += meteor_frame_speed * dt
                    if meteor_frame >= 10: meteor_frame -= 10
                    if meteor_pos.y >= boss_ref.pos.y:
                        boss_transition_state = 'EXPLOSION'; explosion_radius = 0.0
                        if 'explosion' in SOUNDS: SOUNDS['explosion'].play()
                        player.inv_timer = 0.0
                        result = player.take_damage(50, is_boss_ultimate=True)
                        if result == "BLOCKED":
                            damage_texts.append(DamageText(player.pos.x, player.pos.y - 30, "보호"))
                            for _ in range(20): shield_particles.append(ShieldBreakParticle(player.pos.x, player.pos.y))
                            screen_shake_timer = 0.3; screen_shake_intensity = 8; screen_shake_duration = 0.3
                        elif result:
                            damage_texts.append(DamageText(player.pos.x, player.pos.y - 30, player.last_damage_taken))
                            screen_shake_timer = 0.6; screen_shake_intensity = 15; screen_shake_duration = 0.6
                elif boss_transition_state == 'EXPLOSION':
                    explosion_radius += 3000 * dt 
                    if explosion_radius >= LOGICAL_WIDTH: boss_transition_state = 'FADE_OUT'; explosion_alpha = 255.0
                elif boss_transition_state == 'FADE_OUT':
                    explosion_alpha -= 200 * dt 
                    if explosion_alpha <= 0:
                        if boss_phase == 1 and boss_ref and boss_ref.type == 'boss':
                            boss_phase = 2; boss_ref.boss_phase = 2
                            boss_ref.hp = boss_ref.phase2_hp; boss_ref.max_hp = boss_ref.phase2_max_hp
                            boss_phase2_attack_name_timer = 3.0
                        boss_transition_state = 'RESTORE_CAMERA'; boss_transition_timer = 1.0
                elif boss_transition_state == 'RESTORE_CAMERA':
                    boss_transition_timer -= dt
                    if boss_transition_timer <= 0: boss_transition_state = 'DONE'
            
            if boss_phase2_attack_name_timer > 0:
                boss_phase2_attack_name_timer -= dt



            if tutorial_state == 'WAITING' and not is_game_paused:
                is_any_moving = is_action_pressed('UP') or is_action_pressed('DOWN') or is_action_pressed('LEFT') or is_action_pressed('RIGHT') or is_action_pressed('DASH')
                if is_any_moving or is_mouse_down: tutorial_state = 'MONOLOGUE'; tutorial_char_idx = 0.0
            elif tutorial_state == 'MONOLOGUE' and not is_game_paused:
                if monologue_step == 1: tutorial_char_idx += dt * 3.0  # 두 번째 대사는 핏빛으로 엄청 천천히
                else: tutorial_char_idx += dt * 30.0  # 기본 속도
                if monologue_step != _voice_played_monologue_step and 0 <= monologue_step < len(monologue_messages):
                    _voice_played_monologue_step = monologue_step
                    _vk = f'voice_{monologue_step + 1:02d}'
                    if _vk in SOUNDS: SOUNDS[_vk].play()
            
            # 👇 독백 텍스트 출력 속도 조절 (2번째 대사는 엄청 느리게)
            elif tutorial_state == 'MONOLOGUE' and not is_game_paused:
                if monologue_step == 1: tutorial_char_idx += dt * 3.0  # 엄청 천천히 등장
                else: tutorial_char_idx += dt * 30.0  # 기본 속도

            elif tutorial_state == 'WAITING_INPUT' and not is_game_paused:
                pass
            elif tutorial_state == 'EXCLAMATION' and not is_game_paused:
                tutorial_timer -= dt
                if tutorial_timer <= 0: tutorial_state = 'PANNING'; tutorial_timer = 1.2 
            elif tutorial_state == 'PANNING' and not is_game_paused:
                tutorial_timer -= dt
                if tutorial_timer <= 0: 
                    tutorial_state = 'TALKING'
                    if 'meow_1' in SOUNDS: SOUNDS['meow_1'].play()
            elif tutorial_state == 'TALKING' and not is_game_paused: tutorial_char_idx += dt * 30.0 
                
            mx, my = scaled_mouse_pos; world_mouse_x = mx - VIEW_MARGIN_X + camera_x; world_mouse_y = my - VIEW_MARGIN_Y + camera_y
            
            current_tile_map = None
            if current_map_idx == -1: current_tile_map = NAYE_HOME_MAP
            elif current_map_idx in [0,1,2,3,4,5,6,7]: current_tile_map = [CLASSROOM_MAP, TOILET_MAP, HEALTH_MAP, GYM_MAP, CAFETERIA_MAP, COMPUTER_MAP, LIBRARY_MAP, PRINCIPAL_MAP][current_map_idx]
            
            # 👇 금지책 가짜 죽음 타이머 (무조건 항상 실행)
            if forbidden_fake_death:
                forbidden_fake_death_timer -= dt
                if forbidden_fake_death_timer <= 0:
                    forbidden_fake_death = False
                    forbidden_wave_phase = 'IDLE'
                    blue_overlay_alpha = 0.0
                    player.attack_disabled = False
                    forbidden_respawn_flash = 0.4
                    if current_map_idx == 6:
                        fb_margin = TILE_SIZE * 4
                        fb_corners = [(fb_margin, fb_margin), (room_w - fb_margin, fb_margin), (fb_margin, room_h - fb_margin), (room_w - fb_margin, room_h - fb_margin)]
                        random.shuffle(fb_corners)
                        fb_real = random.randint(0, 3)
                        for fi, (fx, fy) in enumerate(fb_corners):
                            fb = Enemy(fx, fy, enemy_type='forbidden_book')
                            fb.is_real = (fi == fb_real)
                            enemies.append(fb)
            if forbidden_respawn_flash > 0:
                forbidden_respawn_flash -= dt
            
            if tutorial_state == 'DONE' and not is_game_paused and not forbidden_fake_death:
                # 👇 [여기에 추가] 장판 수명 업데이트 및 밟았는지 체크 로직
                is_on_puddle = False
                for puddle in soap_puddles[:]:
                    puddle.update(dt)
                    if puddle.timer <= 0:
                        soap_puddles.remove(puddle)
                    elif puddle.pos.distance_to(player.pos) < puddle.radius + player.radius:
                        is_on_puddle = True

                # 플레이어가 장판 위에 있으면 속도 절반으로 감소 (대시 중에는 영향 안받음)
                if is_on_puddle and not player.is_dashing: 
                    player.speed = player.normal_speed * 0.5
                elif not player.is_dashing: 
                    player.speed = player.normal_speed

                # 👇 도서관 지뢰 업데이트 및 폭발 로직
                for mine in library_mines[:]:
                    mine.update(dt)
                for mine in library_mines[:]:
                    if not mine.alive: continue
                    if mine.chain_triggered and mine.chain_delay <= 0:
                        mine.alive = False
                        library_mines.remove(mine)
                        blast_radius = mine.radius * 3
                        if player.pos.distance_to(mine.pos) < blast_radius and not (player.is_dashing or player.inv_timer > 0):
                            res = player.take_damage(mine.damage)
                            if res == "BLOCKED" and damage_texts is not None:
                                damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                            elif res and damage_texts is not None:
                                damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                        for _ in range(60):
                            particles.append(ExplosionParticle(mine.pos.x, mine.pos.y))
                        screen_shake_timer = 0.6; screen_shake_duration = 0.6; screen_shake_intensity = 30.0
                        explosion_radius = TILE_SIZE * 5
                        for other in library_mines[:]:
                            if not other.alive or other.chain_triggered: continue
                            if other.pos.distance_to(mine.pos) <= explosion_radius:
                                other.chain_triggered = True
                                other.chain_delay = random.uniform(0.8, 1.5)
                        continue
                    if mine.chain_triggered: continue
                    if mine.pos.distance_to(player.pos) < mine.radius + player.radius:
                        if not (player.is_dashing or player.inv_timer > 0):
                            mine.chain_triggered = True
                            mine.chain_delay = random.uniform(0.5, 0.8)
                if boss_transition_state in ['WIDE_SHOT', 'METEOR_FALL']:
                    if player.is_dashing: player.is_dashing = False; player.speed = player.normal_speed
                else:
                    player.move(dt, room_w, room_h, world_mouse_x, world_mouse_y, current_map_idx, current_tile_map)
                current_play_time += dt
                if player.item_cooldown > 0: player.item_cooldown -= dt
                
                for d_txt in damage_texts[:]: d_txt.update(dt); d_txt.timer <= 0 and damage_texts.remove(d_txt)
                for s_eff in slash_effects[:]: s_eff.update(dt); s_eff.timer <= 0 and slash_effects.remove(s_eff)
                for p in particles[:]: p.update(dt); p.lifetime <= 0 and particles.remove(p)
                for sp in shield_particles[:]: sp.update(dt); sp.lifetime <= 0 and shield_particles.remove(sp)
                for eb in enemy_bullets[:]:
                    eb.update(dt)
                    
                    # pill 탄막이 중앙에 도달(dead)했으면 즉시 제거
                    if hasattr(eb, 'dead') and eb.dead:
                        # 👇 배드민턴공이 사거리/벽에 도달하면 공몬스터로 변신
                        if hasattr(eb, 'is_shuttle') and eb.is_shuttle and not getattr(eb, 'is_reflected', False):
                            shuttle_enemy = Enemy(eb.pos.x, eb.pos.y, enemy_type='badminton_shuttle')
                            enemies.append(shuttle_enemy)
                            # 라켓의 활성 공 플래그 해제
                            if hasattr(eb, 'owner_racket') and eb.owner_racket is not None:
                                eb.owner_racket.has_active_shuttle = False
                        enemy_bullets.remove(eb); continue
                    
                    # 👇 반사된 배드민턴공이 라켓에 닿으면 라켓에 데미지
                    if hasattr(eb, 'is_shuttle') and eb.is_shuttle and getattr(eb, 'is_reflected', False):
                        for enemy in enemies[:]:
                            if enemy.type == 'badminton_racket' and enemy.pos.distance_to(eb.pos) < enemy.radius + eb.radius:
                                enemy.hp -= 30
                                enemy.flash_timer = 0.2
                                damage_texts.append(DamageText(enemy.pos.x, enemy.pos.y - 20, 30))
                                slash_effects.append(SlashEffect(enemy.pos.x, enemy.pos.y))
                                for _ in range(15): particles.append(Particle(enemy.pos.x, enemy.pos.y))
                                if enemy.hp <= 0:
                                    if enemy.type == 'gravity_book':
                                        player.controls_reversed = False
                                    if enemy.type == 'forbidden_book':
                                        fb_was_real = getattr(enemy, 'is_real', False)
                                        for fb in enemies[:]:
                                            if fb.type == 'forbidden_book' and fb is not enemy: enemies.remove(fb)
                                        enemies.remove(enemy)
                                        if not fb_was_real:
                                            forbidden_fake_death = True
                                            forbidden_fake_death_timer = 2.5
                                        else:
                                            forbidden_wave_phase = 'IDLE'; blue_overlay_alpha = 0.0
                                    else:
                                        enemies.remove(enemy)
                                    if enemy.type not in ['badminton_shuttle', 'forbidden_book']:
                                        _kill_count_since_potion += 1
                                        if _kill_count_since_potion >= 6 or random.random() < 0.15:
                                            dropped_items.append(DroppedItem(enemy.pos.x, enemy.pos.y, "회복물약")); _kill_count_since_potion = 0
                                if eb in enemy_bullets: enemy_bullets.remove(eb)
                                break
                        else:
                            # 반사된 공이 맵 밖으로 나가면 제거
                            if not (0 <= eb.pos.x <= room_w and 0 <= eb.pos.y <= room_h):
                                if eb in enemy_bullets: enemy_bullets.remove(eb)
                        continue

                    # 1. 수명이 다해 터지는 로직 (대쉬와 상관없음)
                    if hasattr(eb, 'exploded') and eb.exploded and eb.pos.x != -10000:
                        eb.explode(enemy_bullets)
                        if eb in enemy_bullets: enemy_bullets.remove(eb)
                        continue
                        
                    # pill 탄막은 맵 밖에서 시작하므로 맵 경계 검사를 건너뜀
                    if not (0 <= eb.pos.x <= room_w and 0 <= eb.pos.y <= room_h):
                        if hasattr(eb, 'is_pill_bullet') and eb.is_pill_bullet:
                            pass  # pill 탄막은 맵 경계 무시
                        elif hasattr(eb, 'is_shuttle') and eb.is_shuttle and not getattr(eb, 'is_reflected', False):
                            # 배드민턴공이 맵 경계에 닿으면 공몬스터로 변신
                            spawn_x = max(0, min(eb.pos.x, room_w))
                            spawn_y = max(0, min(eb.pos.y, room_h))
                            shuttle_enemy = Enemy(spawn_x, spawn_y, enemy_type='badminton_shuttle')
                            enemies.append(shuttle_enemy)
                            if hasattr(eb, 'owner_racket') and eb.owner_racket is not None:
                                eb.owner_racket.has_active_shuttle = False
                            if eb in enemy_bullets: enemy_bullets.remove(eb)
                            continue
                        else:
                            enemy_bullets.remove(eb); continue
                    
                    # 2. 플레이어와 충돌 판정 (알파 마스크 기반)
                    if eb.collides_with_mask(player):
                        
                        # 👇 [핵심 수정] 대쉬 중이면 아무 일도 일어나지 않고 통과합니다.
                        if player.is_dashing or player.inv_timer > 0:
                            continue
                        
                        # 👇 와이파이 파동: 데미지만 주고 투사체는 제거하지 않음
                        if hasattr(eb, 'is_wifi_wave') and eb.is_wifi_wave:
                            res = player.take_damage(eb.damage)
                            if res == "BLOCKED":
                                damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                            elif res == True:
                                damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                                for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
                            continue
                        
                        # 👇 반사된 배드민턴공은 플레이어에게 데미지 없이 통과
                        if hasattr(eb, 'is_shuttle') and eb.is_shuttle and getattr(eb, 'is_reflected', False):
                            continue
                            
                        # 👇 붕대 투사체 충돌 시 스턴 적용
                        if hasattr(eb, 'is_bandage') and eb.is_bandage:
                            player.stun_timer = 1.0
                            if 'stun' in SOUNDS: SOUNDS['stun'].play()
                            damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "스턴"))
                            for _ in range(5): particles.append(Particle(player.pos.x, player.pos.y))
                            if eb in enemy_bullets: enemy_bullets.remove(eb)
                            continue

                        # 👇 파란 알약 탄막 충돌 시 체력 회복
                        if hasattr(eb, 'is_healing_pill') and eb.is_healing_pill:
                            player.hp = min(player.max_hp, player.hp + 5)
                            damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "+5"))
                            for _ in range(5): particles.append(Particle(player.pos.x, player.pos.y))
                            if eb in enemy_bullets: enemy_bullets.remove(eb)
                            continue

                        # 대쉬 중이 아닐 때만 폭발하고 데미지를 입음
                        if hasattr(eb, 'exploded'):
                            eb.explode(enemy_bullets)
                            
                        res = player.take_damage(eb.damage)
                        if res == "BLOCKED":
                            damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                        elif res == True:
                            damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                            for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))
                            
                        if eb in enemy_bullets: enemy_bullets.remove(eb)

                for boom in boomerangs[:]:
                    boom.update(dt, enemy_bullets)
                    if boom.returned:
                        if boom.owner and boom.owner.hp > 0:
                            boom.owner.has_active_boomerang = False
                            boom.owner._boomerang_launched = False
                        boomerangs.remove(boom)
                        continue
                    if not (player.is_dashing or player.inv_timer > 0):
                        if boom.pos.distance_to(player.pos) < boom.radius + player.radius:
                            res = player.take_damage(boom.damage)
                            if res == "BLOCKED":
                                damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                            elif res == True:
                                damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                                for _ in range(10): particles.append(Particle(player.pos.x, player.pos.y))

                for cr in chopstick_rains[:]:
                    cr.update(dt, player, damage_texts, particles)
                    if cr.done: chopstick_rains.remove(cr)
                for db in dust_bursts[:]:
                    db.update(dt)
                    if db.is_done(): dust_bursts.remove(db)

            cam_speed = 5.0; target_zoom = 1.0
            
            if app_state == APP_DEATH_ANIMATION:
                target_zoom = 3.0; target_x = player.pos.x - VIEW_W / 2; target_y = player.pos.y - VIEW_H / 2
            elif tutorial_state in ['PANNING', 'TALKING']:
                target_zoom = 2.5 
                if tutorial_step in [4, 5]: target_x = vase_pos.x - VIEW_W / 2; target_y = vase_pos.y - VIEW_H / 2
                elif tutorial_step == 6: target_x = ball_pos.x - VIEW_W / 2; target_y = ball_pos.y - VIEW_H / 2
                else: target_x = cat_pos.x - VIEW_W / 2; target_y = cat_pos.y - VIEW_H / 2
            elif boss_transition_state in ['WIDE_SHOT', 'METEOR_FALL', 'EXPLOSION', 'FADE_OUT']:
                if current_map_idx == 7 and boss_ref:
                    fit_zoom = min(VIEW_W / room_w, VIEW_H / room_h) * 0.92
                    target_zoom = fit_zoom
                    vis_w, vis_h = VIEW_W / fit_zoom, VIEW_H / fit_zoom
                    target_x = room_w / 2 - vis_w / 2; target_y = room_h / 2 - vis_h / 2
                else:
                    target_zoom = 1.0 
                    if boss_ref: target_x = boss_ref.pos.x - VIEW_W / 2; target_y = boss_ref.pos.y - VIEW_H / 2
            elif boss_transition_state == 'RESTORE_CAMERA':
                target_zoom = 1.0; target_x = player.pos.x - VIEW_W / 2; target_y = player.pos.y - VIEW_H / 2
            elif boss_bubble_state == 'ACTIVE':
                target_zoom = 1.0
                boss_obj_cam = next((e for e in enemies if e.type == 'boss'), None)
                if boss_obj_cam: target_x = boss_obj_cam.pos.x - VIEW_W / 2; target_y = boss_obj_cam.pos.y - VIEW_H / 2
            else:
                _dfly_boss = next((e for e in enemies if e.type == 'boss' and getattr(e, 'death_fly_active', False)), None)
                if _dfly_boss:
                    target_x = _dfly_boss.pos.x - VIEW_W / 2; target_y = _dfly_boss.pos.y - VIEW_H / 2
                else:
                    target_x = player.pos.x - VIEW_W / 2; target_y = player.pos.y - VIEW_H / 2
                
            if boss_transition_state not in ['WIDE_SHOT', 'METEOR_FALL', 'EXPLOSION', 'FADE_OUT']:
                target_x = max(0, min(target_x, room_w - VIEW_W)) if room_w >= VIEW_W else -(VIEW_W - room_w) // 2
                target_y = max(0, min(target_y, room_h - VIEW_H)) if room_h >= VIEW_H else -(VIEW_H - room_h) // 2
            
            if tutorial_state == 'WAITING' and camera_x == 0 and camera_y == 0: camera_x, camera_y = target_x, target_y
                
            if tutorial_state in ['PANNING', 'TALKING'] or boss_transition_state in ['WIDE_SHOT', 'METEOR_FALL', 'EXPLOSION', 'FADE_OUT', 'RESTORE_CAMERA'] or (tutorial_state == 'DONE' and current_map_idx == -1 and abs(target_x - camera_x) > 5) or app_state == APP_DEATH_ANIMATION or any(getattr(e, 'death_fly_active', False) for e in enemies if e.type == 'boss') or boss_defeated:
                camera_x += (target_x - camera_x) * cam_speed * dt; camera_y += (target_y - camera_y) * cam_speed * dt
            else: camera_x, camera_y = target_x, target_y

            if screen_shake_timer > 0:
                screen_shake_timer -= dt
                shake_i = screen_shake_intensity * min(1.0, screen_shake_timer / screen_shake_duration)
                camera_x += random.uniform(-shake_i, shake_i)
                camera_y += random.uniform(-shake_i, shake_i)

            if current_map_idx == 7 and boss_bubble_state == 'ACTIVE':
                speed = 2.5 if boss_bubble_step == len(boss_bubble_lines) - 1 else boss_bubble_speed
                boss_bubble_char_idx += dt * speed
                if boss_bubble_step != _voice_played_boss_bubble_step:
                    _voice_played_boss_bubble_step = boss_bubble_step
                    _vk = f'voice_{boss_bubble_step + 13:02d}'
                    if _vk in SOUNDS: SOUNDS[_vk].play()

            if room_state == ROOM_WAITING and not is_game_paused:
                if forbidden_fake_death:
                    pass
                elif current_map_idx == -1: room_state = ROOM_CLEARED
                elif not cleared_rooms[current_map_idx]: 
                    room_state = ROOM_COMBAT; spawners.clear(); boomerangs.clear(); chopstick_rains.clear(); dust_bursts.clear()
                    player.room_wave = 1
                    if current_map_idx == 7: enemies.append(Enemy(room_w // 2, room_h // 2, enemy_type='boss'))
                    elif current_map_idx == 0:
                        types_to_spawn = ['eraser', 'chalk', 'pencil']
                        for e_type in types_to_spawn:
                            for _ in range(50):
                                sx, sy = random.randint(TILE_SIZE * 2, room_w - TILE_SIZE * 2), random.randint(TILE_SIZE * 2, room_h - TILE_SIZE * 2)
                                valid = True
                                if current_tile_map:
                                    c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                    if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                        if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                    else: valid = False
                                if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100: break
                            spawners.append(MonsterSpawn(sx, sy, enemy_type=e_type))
                            # 👇 화장실 맵(1) 전용 스폰 로직 추가
                    elif current_map_idx == 1:
                        types_to_spawn = ['soap', 'soap', 'toothpaste', 'toothbrush']
                        for e_type in types_to_spawn:
                            for _ in range(50):
                                sx, sy = random.randint(TILE_SIZE * 2, room_w - TILE_SIZE * 2), random.randint(TILE_SIZE * 2, room_h - TILE_SIZE * 2)
                                valid = True
                                if current_tile_map:
                                    c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                    if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                        if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                    else: valid = False
                                if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100: break
                            spawners.append(MonsterSpawn(sx, sy, enemy_type=e_type))
                    elif current_map_idx == 2:
                        # 👈 보건실: pill_boss(맵 중앙) + bandage(1) + syringe(1)
                        # pill_boss도 spawner로 소환 (맵 중앙)
                        sp = MonsterSpawn(room_w // 2, room_h // 2, enemy_type='pill_boss')
                        sp.warning_radius = 35
                        sp.delay = 0.0
                        spawners.append(sp)
                        # bandage + syringe×2 스폰 (맵 중앙에서 적당히 떨어진 곳)
                        for e_type in ['bandage', 'syringe', 'syringe']:
                            for _ in range(50):
                                sx, sy = random.randint(TILE_SIZE * 3, room_w - TILE_SIZE * 3), random.randint(TILE_SIZE * 3, room_h - TILE_SIZE * 3)
                                valid = True
                                if current_tile_map:
                                    c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                    if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                        if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                    else: valid = False
                                if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100: break
                            spawners.append(MonsterSpawn(sx, sy, enemy_type=e_type))
                    elif current_map_idx == 3:
                        # 👈 체육관: 꼬깔콘(2, 순차스폰) + 축구공(2) + 배드민턴채(2)
                        types_to_spawn = ['corn_cone', 'corn_cone', 'soccer_ball', 'soccer_ball', 'badminton_racket', 'badminton_racket']
                        corn_cone_count = 0
                        for e_type in types_to_spawn:
                            for _ in range(50):
                                sx, sy = random.randint(TILE_SIZE * 2, room_w - TILE_SIZE * 2), random.randint(TILE_SIZE * 2, room_h - TILE_SIZE * 2)
                                valid = True
                                if current_tile_map:
                                    c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                    if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                        if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                    else: valid = False
                                if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100: break
                            sp = MonsterSpawn(sx, sy, enemy_type=e_type)
                            # 두 번째 꼬깔콘은 0.5초 뒤에 스폰
                            if e_type == 'corn_cone':
                                corn_cone_count += 1
                                if corn_cone_count == 2:
                                    sp.delay = 2.0  # 첫 번째(1.0초)보다 1초 뒤 스폰
                            spawners.append(sp)
                    elif current_map_idx == 4:
                        # 급식실: 식판(2) + 철수세미(2) + 수저와젓가락(2)
                        types_to_spawn = ['food_tray', 'food_tray', 'steel_scrubber', 'spoon_chopsticks']
                        for e_type in types_to_spawn:
                            for _ in range(50):
                                sx, sy = random.randint(TILE_SIZE * 2, room_w - TILE_SIZE * 2), random.randint(TILE_SIZE * 2, room_h - TILE_SIZE * 2)
                                valid = True
                                if current_tile_map:
                                    c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                    if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                        if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                    else: valid = False
                                if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100: break
                            spawners.append(MonsterSpawn(sx, sy, enemy_type=e_type))
                    elif current_map_idx == 5:
                        # 컴퓨터실: 키보드(2, 최소 50px 거리) + 공유기(위쪽) + 마우스(2, 대각선 구석)
                        mouse_margin = TILE_SIZE * 2
                        corners_spawn = [
                            (mouse_margin, mouse_margin),
                            (room_w - mouse_margin, room_h - mouse_margin)
                        ]
                        for mi, (mx, my) in enumerate(corners_spawn):
                            sp = MonsterSpawn(mx, my, enemy_type='computer_mouse')
                            sp.delay = 0.5
                            spawners.append(sp)
                        kb_positions = []
                        for _ in range(2):
                            found = False
                            for _ in range(100):
                                sx, sy = random.randint(TILE_SIZE * 2, room_w - TILE_SIZE * 2), random.randint(TILE_SIZE * 2, room_h - TILE_SIZE * 2)
                                valid = True
                                if current_tile_map:
                                    c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                    if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                        if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                    else: valid = False
                                if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100:
                                    for px, py in kb_positions:
                                        if pygame.math.Vector2(sx, sy).distance_to(pygame.math.Vector2(px, py)) < 150:
                                            valid = False; break
                                if valid: found = True; break
                            if not found and kb_positions:
                                sx, sy = kb_positions[-1]
                                sx += 200
                                sx = min(sx, room_w - TILE_SIZE * 2)
                            kb_positions.append((sx, sy))
                            spawners.append(MonsterSpawn(sx, sy, enemy_type='keyboard'))
                        sp_router = MonsterSpawn(room_w // 2, int(room_h * 0.2), enemy_type='router')
                        sp_router.delay = 0.0
                        spawners.append(sp_router)
                    elif current_map_idx == 6:
                        for e_type in ['mine_book', 'gravity_book', 'gamble_book']:
                            for _ in range(50):
                                sx, sy = random.randint(TILE_SIZE * 2, room_w - TILE_SIZE * 2), random.randint(TILE_SIZE * 2, room_h - TILE_SIZE * 2)
                                valid = True
                                if current_tile_map:
                                    c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                    if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                        if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                    else: valid = False
                                if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100: break
                            spawners.append(MonsterSpawn(sx, sy, enemy_type=e_type))
                        fb_margin = TILE_SIZE * 4
                        fb_corners = [(fb_margin, fb_margin), (room_w - fb_margin, fb_margin), (fb_margin, room_h - fb_margin), (room_w - fb_margin, room_h - fb_margin)]
                        fb_real = random.randint(0, 3)
                        for fi, (fx, fy) in enumerate(fb_corners):
                            sp = MonsterSpawn(fx, fy, enemy_type='forbidden_book')
                            sp.extra_attrs['is_real'] = (fi == fb_real)
                            spawners.append(sp)
                    else:
                        for _ in range(3):
                            for _ in range(50):
                                sx, sy = random.randint(TILE_SIZE * 2, room_w - TILE_SIZE * 2), random.randint(TILE_SIZE * 2, room_h - TILE_SIZE * 2)
                                valid = True
                                if current_tile_map:
                                    c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                    if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                        if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                    else: valid = False
                                if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100: break
                            spawners.append(MonsterSpawn(sx, sy, enemy_type='normal'))
                        
            elif room_state == ROOM_COMBAT and not is_game_paused and not forbidden_fake_death:
                for enemy in enemies:
                    if enemy.type == 'mine_book':
                        enemy._mines_list = library_mines
                    if enemy.is_boss and enemy.type != 'pill_boss' and not getattr(enemy, 'death_fly_active', False) and (boss_transition_state in ['WIDE_SHOT', 'METEOR_FALL'] or boss_bubble_state == 'ACTIVE'):
                        if hasattr(enemy, 'spawn_pos'):
                            enemy.pos.x = enemy.spawn_pos.x
                            enemy.pos.y = enemy.spawn_pos.y
                        if not getattr(enemy, 'dialogue_anim_active', False):
                            if enemy.boss_phase == 2 and len(IMAGES.get('boss_phase2', [])) >= 12:
                                enemy.phase2_anim_frame += enemy.phase2_anim_speed * dt
                                max_f = 12 if enemy.phase2_anim_cycle == 0 else 9
                                if int(enemy.phase2_anim_frame) >= max_f:
                                    enemy.phase2_anim_frame = 0.0
                                    if enemy.phase2_anim_cycle == 0: enemy.phase2_anim_cycle = 1
                                    elif enemy.phase2_anim_cycle == 1: enemy.phase2_anim_cycle = 2
                                    else: enemy.phase2_anim_cycle = 1
                            elif len(IMAGES.get('boss_phase1', [])) >= 10:
                                enemy.phase1_anim_frame += enemy.phase1_anim_speed * dt
                                if enemy.phase1_anim_frame >= 10: enemy.phase1_anim_frame -= 10
                    else: enemy.update(dt, player.pos, current_tile_map, enemy_bullets, player, damage_texts, particles, soap_puddles, enemies_list=enemies, spawners_list=spawners)
                    if enemy.type == 'boss' and getattr(enemy, 'death_fly_active', False) and not getattr(enemy, 'death_fly_hit_wall', False):
                        hit_wall = False
                        if enemy.pos.x - enemy.radius < 0 or enemy.pos.x + enemy.radius > room_w:
                            hit_wall = True
                        if enemy.pos.y - enemy.radius < 0 or enemy.pos.y + enemy.radius > room_h:
                            hit_wall = True
                        if not hit_wall and current_tile_map:
                            cx = int(enemy.pos.x // TILE_SIZE)
                            cy = int(enemy.pos.y // TILE_SIZE)
                            if 0 <= cy < len(current_tile_map) and 0 <= cx < len(current_tile_map[0]):
                                if current_tile_map[cy][cx] in [1, 2, 3]:
                                    hit_wall = True
                        if hit_wall:
                            enemy.death_fly_hit_wall = True
                            enemy.pos.x = max(enemy.radius, min(room_w - enemy.radius, enemy.pos.x))
                            enemy.pos.y = max(enemy.radius, min(room_h - enemy.radius, enemy.pos.y))
                            boss_defeated = True
                            player.frozen = True
                            boss_death_fade_alpha = 0.1
                            pygame.mixer.music.stop()
                            if 'fall' in SOUNDS: SOUNDS['fall'].play()
                    if enemy.type == 'food_tray' and enemy.state == 'THROW' and enemy.has_active_boomerang and not enemy._boomerang_launched:
                        boom = BoomerangProjectile(enemy.pos.x, enemy.pos.y, player.pos.x, player.pos.y, damage=enemy.damage, room_w=room_w, room_h=room_h)
                        boom.owner = enemy
                        boomerangs.append(boom)
                        enemy._boomerang_launched = True
                    if enemy.type == 'spoon_chopsticks':
                        if getattr(enemy, 'trigger_shake', False):
                            enemy.trigger_shake = False
                            screen_shake_timer = 5.0; screen_shake_duration = 5.0; screen_shake_intensity = 12.0
                        if getattr(enemy, 'trigger_slam_particles', False):
                            enemy.trigger_slam_particles = False
                            dust_bursts.append(DustBurst(enemy.pos.x, enemy.pos.y))
                        if getattr(enemy, 'spawn_chopstick', False):
                            enemy.spawn_chopstick = False
                            view_left = camera_x
                            view_top = camera_y
                            view_right = camera_x + VIEW_W
                            view_bottom = camera_y + VIEW_H
                            margin = 60
                            sx = random.randint(max(int(view_left + margin), TILE_SIZE * 2), min(int(view_right - margin), room_w - TILE_SIZE * 2))
                            sy = random.randint(max(int(view_top + margin), TILE_SIZE * 2), min(int(view_bottom - margin), room_h - TILE_SIZE * 2))
                            if current_tile_map:
                                c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                    if current_tile_map[c_y][c_x] in [1, 2, 3]:
                                        sx = int(player.pos.x + random.uniform(-200, 200))
                                        sy = int(player.pos.y + random.uniform(-200, 200))
                            chopstick_rains.append(ChopstickRain(sx, sy, damage=enemy.damage))

                    if enemy.type == 'boss' and enemy.boss_phase == 2 and getattr(enemy, 'boss_spawn_chopstick', False):
                        enemy.boss_spawn_chopstick = False
                        view_left = camera_x
                        view_top = camera_y
                        view_right = camera_x + VIEW_W
                        view_bottom = camera_y + VIEW_H
                        margin = 80
                        for _ in range(2):
                            sx = random.randint(max(int(view_left + margin), TILE_SIZE * 2), min(int(view_right - margin), room_w - TILE_SIZE * 2))
                            sy = random.randint(max(int(view_top + margin), TILE_SIZE * 2), min(int(view_bottom - margin), room_h - TILE_SIZE * 2))
                            if current_tile_map:
                                c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                    if current_tile_map[c_y][c_x] in [1, 2, 3]:
                                        sx = int(player.pos.x + random.uniform(-300, 300))
                                        sy = int(player.pos.y + random.uniform(-300, 300))
                            chopstick_rains.append(ChopstickRain(sx, sy, damage=2))

                    if enemy.type == 'boss' and enemy.boss_phase == 2 and getattr(enemy, 'boss_spawn_bandage', False):
                        enemy.boss_spawn_bandage = False
                        num_ropes = random.randint(2, 4)
                        for _ in range(num_ropes):
                            from_left = random.choice([True, False])
                            if from_left:
                                bx = camera_x - 50
                            else:
                                bx = camera_x + VIEW_W + 50
                            by = random.randint(int(camera_y + 60), int(camera_y + VIEW_H - 60))
                            target_y = by + random.uniform(-150, 150)
                            target_x = player.pos.x + random.uniform(-100, 100)
                            eb = EnemyBullet(bx, by, target_x, target_y, damage=1)
                            eb.is_bandage = True
                            eb.speed = random.uniform(300, 450)
                            eb.radius = 20
                            enemy_bullets.append(eb)

                    # 👈 적이 맵 밖으로 나가지 않도록 경계 클램핑 (안전장치)
                    if current_tile_map:
                        m = enemy.radius
                        room_w_local = len(current_tile_map[0]) * TILE_SIZE
                        room_h_local = len(current_tile_map) * TILE_SIZE
                        door_half = 200
                        door_block = TILE_SIZE * 3
                        cx_local = room_w_local // 2
                        cy_local = room_h_local // 2
                        if current_map_idx == -1:
                            if abs(enemy.pos.x - cx_local) < door_half:
                                enemy.pos.y = max(m + door_block, min(room_h_local - m, enemy.pos.y))
                        elif current_map_idx >= 0:
                            has_top = False
                            has_bottom = False
                            pos_curr = minimap_positions[current_map_idx]
                            has_left = has_right = False
                            if current_map_idx > 0:
                                pos_prev = minimap_positions[current_map_idx - 1]
                                dx_p, dy_p = pos_prev[0] - pos_curr[0], pos_prev[1] - pos_curr[1]
                                if dx_p == 1: has_right = True
                                elif dx_p == -1: has_left = True
                                elif dy_p == 1: has_bottom = True
                                elif dy_p == -1: has_top = True
                            if current_map_idx < len(MAP_DATA) - 1:
                                pos_next = minimap_positions[current_map_idx + 1]
                                dx_n, dy_n = pos_next[0] - pos_curr[0], pos_next[1] - pos_curr[1]
                                if dx_n == 1: has_right = True
                                elif dx_n == -1: has_left = True
                                elif dy_n == 1: has_bottom = True
                                elif dy_n == -1: has_top = True
                            tb_block = TILE_SIZE * 2
                            lr_block = TILE_SIZE
                            if current_map_idx != 7:
                                if has_top and abs(enemy.pos.x - cx_local) < 600:
                                    enemy.pos.y = max(m + tb_block, enemy.pos.y)
                                if has_bottom and abs(enemy.pos.x - cx_local) < 600:
                                    enemy.pos.y = min(room_h_local - m - tb_block, enemy.pos.y)
                                if has_left and abs(enemy.pos.y - cy_local) < 200:
                                    enemy.pos.x = max(m + lr_block, enemy.pos.x)
                                if has_right and abs(enemy.pos.y - cy_local) < 200:
                                    enemy.pos.x = min(room_w_local - m - lr_block, enemy.pos.x)
                        enemy.pos.x = max(m, min(room_w_local - m, enemy.pos.x))
                        enemy.pos.y = max(m, min(room_h_local - m, enemy.pos.y))
                
                for enemy in enemies:
                    if enemy.type == 'gamble_book':
                        for md in enemy.mini_dices[:]:
                            if md.alive and not (player.is_dashing or player.inv_timer > 0):
                                if md.pos.distance_to(player.pos) < md.radius + player.radius:
                                    res = player.take_damage(md.damage)
                                    if res == "BLOCKED":
                                        damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, "보호"))
                                    elif res:
                                        damage_texts.append(DamageText(player.pos.x, player.pos.y - 20, f"-{player.last_damage_taken}"))
                                        for _ in range(5): particles.append(Particle(player.pos.x, player.pos.y))
                                    md.alive = False
                
                # spawner 업데이트를 enemy 업데이트 뒤로 이동 (pill_boss 무적 확인을 위해)
                for sp in spawners[:]:
                    if sp.update(dt):
                        new_enemy = Enemy(sp.pos.x, sp.pos.y, enemy_type=sp.enemy_type)
                        for k, v in sp.extra_attrs.items():
                            setattr(new_enemy, k, v)
                        enemies.append(new_enemy)
                        slash_effects.append(SpawnEffect(sp.pos.x, sp.pos.y)); spawners.remove(sp)
                
                # 👇 공유기 파동 발사 시 글리치 이펙트 트리거
                for enemy in enemies:
                    if getattr(enemy, 'trigger_glitch', False):
                        glitch_timer = 0.5
                        enemy.trigger_glitch = False
                
                # 👇 금지책 파동 사이클 + 가짜 죽음 처리
                has_active_fb = any(e.type == 'forbidden_book' and e.state == 'ACTIVE' for e in enemies)
                if has_active_fb and not forbidden_fake_death:
                    for e in enemies:
                        if e.type == 'forbidden_book':
                            e._fb_wave_phase = forbidden_wave_phase
                            e._fb_blue_alpha = blue_overlay_alpha
                    if forbidden_wave_phase == 'IDLE':
                        forbidden_wave_phase = 'EXPANDING'
                        forbidden_wave_timer = 2.0
                        for e in enemies:
                            if e.type == 'forbidden_book':
                                static_waves.append(StaticWave(e.pos.x, e.pos.y))
                    elif forbidden_wave_phase == 'EXPANDING':
                        forbidden_wave_timer -= dt
                        blue_overlay_alpha = min(1.0, blue_overlay_alpha + dt * 0.5)
                        if forbidden_wave_timer <= 0:
                            forbidden_wave_phase = 'STATIC'
                            forbidden_wave_timer = 4.0
                    elif forbidden_wave_phase == 'STATIC':
                        forbidden_wave_timer -= dt
                        if forbidden_wave_timer <= 0:
                            forbidden_wave_phase = 'FADING'
                            forbidden_wave_timer = 3.0
                    elif forbidden_wave_phase == 'FADING':
                        forbidden_wave_timer -= dt
                        blue_overlay_alpha = max(0.0, blue_overlay_alpha - dt * 0.35)
                        if forbidden_wave_timer <= 0:
                            forbidden_wave_phase = 'COOLDOWN'
                            forbidden_wave_timer = 3.0
                            blue_overlay_alpha = 0.0
                    elif forbidden_wave_phase == 'COOLDOWN':
                        forbidden_wave_timer -= dt
                        if forbidden_wave_timer <= 0:
                            forbidden_wave_phase = 'EXPANDING'
                            forbidden_wave_timer = 2.0
                            for e in enemies:
                                if e.type == 'forbidden_book':
                                    static_waves.append(StaticWave(e.pos.x, e.pos.y))
                player.attack_disabled = (blue_overlay_alpha > 0.3)
                for sw in static_waves[:]:
                    sw.update(dt)
                    if sw.dead: static_waves.remove(sw)
                
                # 👈 보스 파장 종료 후 첫 공격 시작
                for enemy in enemies:
                    if enemy.type == 'boss' and getattr(enemy, 'shockwave_after_dialogue_done', False) and getattr(enemy, 'attack_timer', 0) > 100:
                        if player.push_timer <= 0:
                            enemy.attack_timer = 0.3
                
                # 👈 pill_boss 무적 해제 시 하늘색 보호막 깨지는 이  트
                for enemy in enemies:
                    if enemy.type == 'pill_boss' and getattr(enemy, 'shield_break', False):
                        for _ in range(50):
                            shield_particles.append(ShieldBreakParticle(enemy.pos.x, enemy.pos.y))
                        enemy.shield_break = False
                
                # 👈 보스 소환 보호막 깨짐 이펙트
                for enemy in enemies:
                    if enemy.is_boss and getattr(enemy, 'summon_shield_break', False):
                        shield_r = enemy.radius + 25
                        for ring in range(3):
                            ring_r = shield_r + ring * 5
                            for i in range(24):
                                a = (2 * math.pi / 24) * i + ring * 0.3
                                px = enemy.pos.x + math.cos(a) * ring_r
                                py = enemy.pos.y + math.sin(a) * ring_r
                                shield_particles.append(ShieldBreakParticle(px, py))
                        for _ in range(30):
                            shield_particles.append(ShieldBreakParticle(enemy.pos.x, enemy.pos.y))
                        enemy.summon_shield_break = False
                
                if current_map_idx == 7:
                    for enemy in enemies:
                        if enemy.type == 'boss' and boss_phase == 1 and getattr(enemy, 'phase1_transition_done', False) == False and enemy.phase1_hp <= 0:
                            enemy.phase1_transition_done = True
                            enemy.spike_state = 'none'
                            enemy.bubble_state = 'none'
                            enemy.aim_state = 'none'
                            enemy.brush_state = 'none'
                            enemy_bullets.clear()
                            enemy.spike_positions_v.clear()
                            enemy.spike_positions_h.clear()
                            enemy.brushes.clear()
                            enemy.attack_order_idx = (enemy.attack_order_idx + 1) % len(enemy.attack_order)
                            enemy.attack_pattern = enemy.attack_order[enemy.attack_order_idx]
                            enemy.attack_timer = 1.5
                            enemy._warning_ready = False
                            static_waves.append(BossShockwave(enemy.pos.x, enemy.pos.y))
                            push_dir = player.pos - enemy.pos
                            if push_dir.length() > 0: push_dir = push_dir.normalize()
                            else: push_dir = pygame.math.Vector2(0, 1)
                            player.push_vel = push_dir * 450
                            max_push_dist = math.sqrt((room_w / 2) ** 2 + (room_h / 2) ** 2)
                            player.push_timer = max_push_dist / 450 + 0.5
                            player.inv_timer = 1.5
                            boss_bubble_state = 'ACTIVE'
                            boss_bubble_step = 0
                            boss_bubble_char_idx = 0.0
                            player.frozen = True
                            break
                            
                for bullet in bullets[:]:
                    bullet.update(dt)
                    if not (0 <= bullet.pos.x <= room_w and 0 <= bullet.pos.y <= room_h): bullets.remove(bullet); continue
                    for enemy in enemies[:]:
                        # 충돌 판정 (마스크 기반 또는 원형 거리 기반)
                        hit = False
                        try:
                            cached_mask = getattr(enemy, '_cached_mask', None)
                            cached_img = getattr(enemy, '_cached_img', None)
                            if cached_mask and cached_img:
                                img_rect = cached_img.get_rect(center=(int(enemy.pos.x), int(enemy.pos.y)))
                                bullet_mask_size = int(bullet.radius * 2)
                                bullet_surf = pygame.Surface((bullet_mask_size, bullet_mask_size), pygame.SRCALPHA)
                                pygame.draw.circle(bullet_surf, (255, 255, 255, 255), (int(bullet.radius), int(bullet.radius)), int(bullet.radius))
                                bullet_mask = pygame.mask.from_surface(bullet_surf)
                                offset_x = int(bullet.pos.x - bullet.radius - img_rect.x)
                                offset_y = int(bullet.pos.y - bullet.radius - img_rect.y)
                                hit = cached_mask.overlap(bullet_mask, (offset_x, offset_y)) is not None
                            else:
                                hit = bullet.pos.distance_to(enemy.pos) < bullet.radius + enemy.radius
                        except:
                            hit = bullet.pos.distance_to(enemy.pos) < bullet.radius + enemy.radius
                        
                        if hit:
                            if enemy.type == 'boss' and (boss_transition_state in ['WIDE_SHOT', 'METEOR_FALL'] or boss_bubble_state == 'ACTIVE'):
                                damage_texts.append(DamageText(enemy.pos.x, enemy.pos.y - 40, "무적"))
                            elif enemy.type == 'pill_boss' and getattr(enemy, 'is_invincible', False):
                                damage_texts.append(DamageText(enemy.pos.x, enemy.pos.y - 40, "무적"))
                            else:
                                enemy.hp -= 1; enemy.flash_timer = 0.1
                                if enemy.type == 'boss':
                                    if enemy.boss_phase == 1:
                                        enemy.phase1_hp = max(0, enemy.phase1_hp - 1)
                                        enemy.hp = enemy.phase1_hp
                                    else:
                                        enemy.phase2_hp = max(0, enemy.phase2_hp - 1)
                                        enemy.hp = enemy.phase2_hp
                                damage_texts.append(DamageText(enemy.pos.x, enemy.pos.y - 20, 1))
                                slash_effects.append(SlashEffect(enemy.pos.x, enemy.pos.y))
                                for _ in range(random.randint(10, 15)): particles.append(Particle(enemy.pos.x, enemy.pos.y - 10))
                                if enemy.hp <= 0:
                                    dead_type = enemy.type
                                    if dead_type == 'boss' and enemy.boss_phase == 1:
                                        enemy.phase1_hp = 0; enemy.hp = 0
                                        continue
                                    if dead_type == 'boss' and enemy.boss_phase == 2 and not getattr(enemy, 'death_fly_active', False):
                                        fly_dir = enemy.pos - player.pos
                                        if fly_dir.length() > 0: fly_dir = fly_dir.normalize()
                                        else: fly_dir = pygame.math.Vector2(1, 0)
                                        enemy.death_fly_dir = fly_dir
                                        enemy.death_fly_facing_right = fly_dir.x >= 0
                                        enemy.death_fly_active = True
                                        enemy.hp = 0
                                        continue
                                    dead_pos = enemy.pos.copy()
                                    dead_was_real = getattr(enemy, 'is_real', False)
                                    enemies.remove(enemy)
                                    # 👇 보스 사망 시 엔딩 플래그 (즉시 게임 동결)
                                    if dead_type == 'boss':
                                        boss_defeated = True
                                        player.frozen = True
                                        player.controls_reversed = False
                                        enemy.boss_laser_active = False
                                        boss_death_fade_alpha = 0.1
                                        pygame.mixer.music.stop()
                                    # pill_boss가 죽으면 모든 pill 탄막 제거
                                    if dead_type == 'pill_boss':
                                        for eb in enemy_bullets[:]:
                                            if hasattr(eb, 'is_pill_bullet') and eb.is_pill_bullet:
                                                enemy_bullets.remove(eb)
                                    # gravity_book이 죽으면 조작 반전 해제
                                    if dead_type == 'gravity_book':
                                        player.controls_reversed = False
                                    if dead_type == 'forbidden_book':
                                        for fb in enemies[:]:
                                            if fb.type == 'forbidden_book': enemies.remove(fb)
                                        if not dead_was_real:
                                            forbidden_fake_death = True
                                            forbidden_fake_death_timer = 2.5
                                        else:
                                            forbidden_wave_phase = 'IDLE'; blue_overlay_alpha = 0.0
                                    if dead_type == 'gamble_book':
                                        for d in enemy.dice_bullets: d.alive = False
                                        for d in enemy.mini_dices: d.alive = False
                                    # 👈 파란 알약을 죽이면 체력 5 회복
                                    if dead_type == 'blue_pill':
                                        player.hp = min(player.max_hp, player.hp + 5)
                                        damage_texts.append(DamageText(player.pos.x, player.pos.y - 40, "+5"))
                                    elif dead_type == 'red_pill':
                                        pass
                                    elif dead_type == 'badminton_shuttle':
                                        pass
                                    elif dead_type == 'forbidden_book':
                                        pass
                                    else:
                                        _kill_count_since_potion += 1
                                        if _kill_count_since_potion >= 6 or random.random() < 0.15:
                                            dropped_items.append(DroppedItem(dead_pos.x, dead_pos.y, "회복물약")); _kill_count_since_potion = 0

                            if bullet in bullets: bullets.remove(bullet)
                            break
                
                if not forbidden_fake_death and len(enemies) == 0 and len(spawners) == 0: 
                    if current_map_idx == 0 and getattr(player, 'room_wave', 1) == 1:
                        player.room_wave = 2 
                        types_pool = ['eraser', 'chalk', 'pencil']
                        spawn_counts = {'eraser': 0, 'chalk': 0, 'pencil': 0}
                        
                        for i in range(3):
                            e_type = random.choice(types_pool)
                            spawn_counts[e_type] += 1 
                            
                            if e_type == 'chalk' and 'chalk' in types_pool:
                                types_pool.remove('chalk')
                            elif spawn_counts[e_type] >= 2 and e_type in types_pool:
                                types_pool.remove(e_type)
                                
                            for _ in range(50):
                                sx, sy = random.randint(TILE_SIZE * 2, room_w - TILE_SIZE * 2), random.randint(TILE_SIZE * 2, room_h - TILE_SIZE * 2)
                                valid = True
                                if current_tile_map:
                                    c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                    if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                        if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                    else: valid = False
                                if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100: break
                            
                            sp = MonsterSpawn(sx, sy, enemy_type=e_type)
                            sp.delay = 1.0 + (i * 0.3) 
                            spawners.append(sp)
                    elif current_map_idx == 1 and getattr(player, 'room_wave', 1) == 1:
                        player.room_wave = 2
                        respawn_types = ['toothpaste', 'toothpaste', 'soap', 'toothbrush', 'toothbrush']
                        for i, e_type in enumerate(respawn_types):
                            for _ in range(50):
                                sx, sy = random.randint(TILE_SIZE * 2, room_w - TILE_SIZE * 2), random.randint(TILE_SIZE * 2, room_h - TILE_SIZE * 2)
                                valid = True
                                if current_tile_map:
                                    c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                    if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                        if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                    else: valid = False
                                if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100: break
                            sp = MonsterSpawn(sx, sy, enemy_type=e_type)
                            sp.delay = 1.0 + (i * 0.3)
                            spawners.append(sp)
                    elif current_map_idx == 2 and getattr(player, 'room_wave', 1) == 1:
                        player.room_wave = 2
                        respawn_types = ['bandage', 'syringe', 'syringe']
                        for i, e_type in enumerate(respawn_types):
                            for _ in range(50):
                                sx, sy = random.randint(TILE_SIZE * 2, room_w - TILE_SIZE * 2), random.randint(TILE_SIZE * 2, room_h - TILE_SIZE * 2)
                                valid = True
                                if current_tile_map:
                                    c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                    if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                        if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                    else: valid = False
                                if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100: break
                            sp = MonsterSpawn(sx, sy, enemy_type=e_type)
                            sp.delay = 1.0 + (i * 0.3)
                            spawners.append(sp)
                    elif current_map_idx == 3 and getattr(player, 'room_wave', 1) == 1:
                        player.room_wave = 2
                        respawn_types = ['corn_cone', 'corn_cone', 'soccer_ball', 'badminton_racket']
                        for i, e_type in enumerate(respawn_types):
                            for _ in range(50):
                                sx, sy = random.randint(TILE_SIZE * 2, room_w - TILE_SIZE * 2), random.randint(TILE_SIZE * 2, room_h - TILE_SIZE * 2)
                                valid = True
                                if current_tile_map:
                                    c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                    if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                        if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                    else: valid = False
                                if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100: break
                            sp = MonsterSpawn(sx, sy, enemy_type=e_type)
                            sp.delay = 1.0 + (i * 0.3)
                            spawners.append(sp)
                    elif current_map_idx == 4 and getattr(player, 'room_wave', 1) == 1:
                        player.room_wave = 2
                        respawn_types = ['food_tray', 'steel_scrubber', 'steel_scrubber', 'spoon_chopsticks']
                        min_dist = 30 * TILE_SIZE
                        spawned_positions = []
                        for i, e_type in enumerate(respawn_types):
                            for _ in range(50):
                                sx, sy = random.randint(TILE_SIZE * 2, room_w - TILE_SIZE * 2), random.randint(TILE_SIZE * 2, room_h - TILE_SIZE * 2)
                                valid = True
                                if current_tile_map:
                                    c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                    if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                        if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                    else: valid = False
                                if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100:
                                    if e_type == 'steel_scrubber':
                                        too_close = False
                                        for px, py in spawned_positions:
                                            if pygame.math.Vector2(sx, sy).distance_to(pygame.math.Vector2(px, py)) < min_dist:
                                                too_close = True; break
                                        if too_close: valid = False
                                if valid: break
                            spawned_positions.append((sx, sy))
                            sp = MonsterSpawn(sx, sy, enemy_type=e_type)
                            sp.delay = 1.0 + (i * 0.3)
                            spawners.append(sp)
                    elif current_map_idx == 5 and getattr(player, 'room_wave', 1) == 1:
                        player.room_wave = 2
                        mouse_margin2 = TILE_SIZE * 2
                        corners_spawn2 = [
                            (mouse_margin2, room_h - mouse_margin2),
                            (room_w - mouse_margin2, mouse_margin2)
                        ]
                        for mi, (mx, my) in enumerate(corners_spawn2):
                            sp = MonsterSpawn(mx, my, enemy_type='computer_mouse')
                            sp.delay = 0.5
                            sp.extra_attrs['mouse_direction'] = -1
                            spawners.append(sp)
                        for _ in range(100):
                            sx, sy = random.randint(TILE_SIZE * 2, room_w - TILE_SIZE * 2), random.randint(TILE_SIZE * 2, room_h - TILE_SIZE * 2)
                            valid = True
                            if current_tile_map:
                                c_x, c_y = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
                                if 0 <= c_y < len(current_tile_map) and 0 <= c_x < len(current_tile_map[0]):
                                    if current_tile_map[c_y][c_x] in [1, 2, 3]: valid = False
                                else: valid = False
                            if valid and pygame.math.Vector2(sx, sy).distance_to(player.pos) > 100: break
                        sp = MonsterSpawn(sx, sy, enemy_type='keyboard')
                        sp.delay = 1.0
                        spawners.append(sp)
                        sp_router2 = MonsterSpawn(room_w // 2, int(room_h * 0.8), enemy_type='router')
                        sp_router2.delay = 1.0
                        spawners.append(sp_router2)
                    else:
                        if not forbidden_fake_death:
                            room_clear_timer -= dt
                            if room_clear_timer <= 0:
                                room_state = ROOM_CLEARED
                                if 'door_open' in SOUNDS and not (boss_defeated and current_map_idx == 7):
                                    SOUNDS['door_open'].play()
                                if current_map_idx >= 0: cleared_rooms[current_map_idx] = True
                                if boss_defeated and current_map_idx == 7:
                                    boss_death_fade_alpha = 0.1
                                    player.frozen = True
                                    pygame.mixer.music.stop()
                        else:
                            room_clear_timer = 0.5
                
            elif room_state in [ROOM_WAITING, ROOM_CLEARED] and not is_game_paused:
                for bullet in bullets[:]: bullet.update(dt)
                transitioned = False
                
                if current_map_idx == -1:
                    if (room_w//2 - 100 < player.pos.x < room_w//2 + 100) and player.pos.y > room_h - 45:
                        if player.has_bag: current_overlay = 'LEAVE_HOME'; player.pos.y = room_h - 60 
                        else: popup_msg = "가방을 깜빡했어!"; popup_timer = 2.0; player.pos.y = room_h - 60

                if not transitioned and current_map_idx >= 0:
                    pos_curr = minimap_positions[current_map_idx]; doors = []
                    if current_map_idx > 0:
                        pos_prev = minimap_positions[current_map_idx - 1]
                        dx, dy = pos_prev[0] - pos_curr[0], pos_prev[1] - pos_curr[1]
                        if dx == 1: doors.append({'dir': 'RIGHT', 'target': current_map_idx - 1})
                        elif dx == -1: doors.append({'dir': 'LEFT', 'target': current_map_idx - 1})
                        elif dy == 1: doors.append({'dir': 'BOTTOM', 'target': current_map_idx - 1})
                        elif dy == -1: doors.append({'dir': 'TOP', 'target': current_map_idx - 1})
                    if current_map_idx < len(MAP_DATA) - 1:
                        pos_next = minimap_positions[current_map_idx + 1]
                        dx, dy = pos_next[0] - pos_curr[0], pos_next[1] - pos_curr[1]
                        if dx == 1: doors.append({'dir': 'RIGHT', 'target': current_map_idx + 1})
                        elif dx == -1: doors.append({'dir': 'LEFT', 'target': current_map_idx + 1})
                        elif dy == 1: doors.append({'dir': 'BOTTOM', 'target': current_map_idx + 1})
                        elif dy == -1: doors.append({'dir': 'TOP', 'target': current_map_idx + 1})
                        
                    for door in doors:
                        d_dir, tgt, trig, sp_dir = door['dir'], door['target'], False, ''
                        if d_dir == 'TOP' and player.pos.y < 45 and (room_w//2 - 100 < player.pos.x < room_w//2 + 100): trig, sp_dir = True, 'BOTTOM'
                        elif d_dir == 'BOTTOM' and player.pos.y > room_h - 45 and (room_w//2 - 100 < player.pos.x < room_w//2 + 100): trig, sp_dir = True, 'TOP'
                        elif d_dir == 'LEFT' and player.pos.x < 45 and (room_h//2 - 100 < player.pos.y < room_h//2 + 100): trig, sp_dir = True, 'RIGHT'
                        elif d_dir == 'RIGHT' and player.pos.x > room_w - 45 and (room_h//2 - 100 < player.pos.y < room_h//2 + 100): trig, sp_dir = True, 'LEFT'
                            
                        if trig:
                            current_map_idx = tgt; cols, rows = MAP_DATA[current_map_idx]['cols'], MAP_DATA[current_map_idx]['rows']; room_w, room_h = cols * TILE_SIZE, rows * TILE_SIZE
                            if sp_dir == 'BOTTOM': player.pos.x, player.pos.y = room_w // 2, room_h - 90
                            elif sp_dir == 'TOP': player.pos.x, player.pos.y = room_w // 2, 90
                            elif sp_dir == 'RIGHT': player.pos.x, player.pos.y = room_w - 90, room_h // 2
                            elif sp_dir == 'LEFT': player.pos.x, player.pos.y = 90, room_h // 2
                            transitioned = True; camera_x, camera_y = player.pos.x - VIEW_W/2, player.pos.y - VIEW_H/2
                            
                            # 👇 보스방 진입 시 자동으로 보스를 향해 걸어감
                            if current_map_idx == 7 and not boss_dialogue_played and not boss_intro_completed_once:
                                boss_talk_state = 'APPROACH'; boss_talk_step = 0; boss_char_idx = 0.0
                            elif current_map_idx == 7 and boss_intro_completed_once:
                                boss_dialogue_played = True
                                boss_talk_state = 'DONE'
                                for e in enemies:
                                    if e.type == 'boss' and not e.shockwave_after_dialogue_done:
                                        e.shockwave_after_dialogue_done = True
                                        e.dialogue_anim_active = False
                                        e.attack_timer = 999.0
                                        static_waves.append(BossShockwave(e.pos.x, e.pos.y))
                                        push_dir = player.pos - e.pos
                                        if push_dir.length() > 0: push_dir = push_dir.normalize()
                                        else: push_dir = pygame.math.Vector2(0, 1)
                                        player.push_vel = push_dir * 450
                                        max_push_dist = math.sqrt((room_w / 2) ** 2 + (room_h / 2) ** 2)
                                        player.push_timer = max_push_dist / 450 + 0.5
                                        player.inv_timer = 1.5
                                        break
                            break
                            
                if transitioned:
                    # 👇 방을 넘어갈 때 문 닫힘 사운드 재생!
                    if 'door_close' in SOUNDS: SOUNDS['door_close'].play() 
                    
                    if not forbidden_fake_death:
                        if current_map_idx == -1: room_state = ROOM_CLEARED
                        else: room_state = ROOM_CLEARED if cleared_rooms[current_map_idx] else ROOM_WAITING
                    bullets.clear(); enemy_bullets.clear(); enemies.clear(); spawners.clear(); boomerangs.clear(); chopstick_rains.clear(); dust_bursts.clear(); damage_texts.clear(); slash_effects.clear(); particles.clear(); dropped_items.clear(); soap_puddles.clear(); library_mines.clear(); static_waves.clear()
                    player.controls_reversed = False
                    player.attack_disabled = False
                    forbidden_wave_phase = 'IDLE'; blue_overlay_alpha = 0.0; forbidden_fake_death = False
                    # 👇 보스방(7) 진입 시 타이머를 무시하고 보스를 즉시 소환합니다!
                    if current_map_idx == 7 and not cleared_rooms[7]:
                        room_state = ROOM_COMBAT
                        enemies.append(Enemy(room_w // 2, room_h // 2, enemy_type='boss'))

        # ==================== 렌더링 (그리기) ====================
        display_surface.fill((0, 0, 0)) 

        if app_state == APP_MAIN_MENU:
            if 'title_bg' in IMAGES: display_surface.blit(IMAGES['title_bg'], (0, 0))
            else: display_surface.blit(title_font.render("단죄의 시간", True, (255, 255, 255)), (150, 150)); display_surface.blit(font.render("Time of Condemnation", True, (150, 150, 150)), (160, 280))
            if continue_enabled:
                menu_btn_start.y = 700; menu_btn_start.rect.y = 700
                menu_btn_start.draw(display_surface, center_x, scaled_mouse_pos)
                menu_btn_continue.y = 780; menu_btn_continue.rect.y = 780
                menu_btn_continue.draw(display_surface, center_x, scaled_mouse_pos)
                menu_btn_settings.y = 860; menu_btn_settings.rect.y = 860
                menu_btn_quit.y = 940; menu_btn_quit.rect.y = 940
            else:
                menu_btn_start.y = 780; menu_btn_start.rect.y = 780
                menu_btn_start.draw(display_surface, center_x, scaled_mouse_pos)
                menu_btn_settings.y = 860; menu_btn_settings.rect.y = 860
                menu_btn_quit.y = 940; menu_btn_quit.rect.y = 940
            menu_btn_settings.draw(display_surface, center_x, scaled_mouse_pos)
            menu_btn_quit.draw(display_surface, center_x, scaled_mouse_pos)
        
        elif app_state == APP_STORY:
            if not current_overlay:
                story_timer += dt
                
                if story_state == 'VIEW':
                    if story_step == 19:
                        if not walk_played:
                            if 'walk' in SOUNDS:
                                SOUNDS['walk'].play()
                            walk_played = True
                            story_timer = 0.0
                        walk_sound = SOUNDS.get('walk')
                        walk_len = walk_sound.get_length() if walk_sound else 2.5
                        if story_timer >= walk_len:
                            story_step = 20
                            story_timer = 0.0
                            walk_played = False
                    elif story_step < 20 and story_timer >= 2.5:
                        story_step += 1
                        story_timer = 0.0
                        walk_played = False
                        if story_step == 2 and 'discord_alarm' in SOUNDS:
                            SOUNDS['discord_alarm'].play()
                        if story_step == 12 and 'sigh' in SOUNDS:
                            SOUNDS['sigh'].play()
                        if story_step == 16 and 'laugh' in SOUNDS:
                            SOUNDS['laugh'].play()
                        if story_step == 18 and 'closet_open' in SOUNDS:
                            SOUNDS['closet_open'].play()
                        if story_step in (5, 6, 7, 8, 9) and 'dialog_next' in SOUNDS:
                            SOUNDS['dialog_next'].play()
                    # 이미지 20(마지막): Enter를 누를 때까지 대기 (자동 전환 없음)

            img_key = f'story_{story_step}'
            if img_key in IMAGES:
                display_surface.blit(IMAGES[img_key], (0, 0))
            
            # 👇 마지막 이미지(20)에서 칼들음 사운드 재생 후 Enter 안내 문구 표시
            if story_state == 'VIEW' and story_step == 20 and not current_overlay:
                if not sword_draw_played:
                    if 'sword_draw' in SOUNDS:
                        SOUNDS['sword_draw'].play()
                    sword_draw_played = True
                    story_timer = 0.0
                sword_sound = SOUNDS.get('sword_draw')
                sword_len = sword_sound.get_length() if sword_sound else 2.0
                if story_timer >= sword_len:
                    skip_txt = small_font.render("Enter를 눌러 시작하기", True, (200, 200, 200))
                    skip_txt.set_alpha(abs(int(math.sin(pygame.time.get_ticks() * 0.005) * 255)))
                    display_surface.blit(skip_txt, (LOGICAL_WIDTH - skip_txt.get_width() - 50, LOGICAL_HEIGHT - 60))
                
        elif app_state in [APP_PLAYING, APP_DEATH_ANIMATION]:
            view_surface.fill((0, 0, 0))
            pygame.draw.rect(view_surface, ROOM_COLOR, (-camera_x, -camera_y, room_w, room_h))
            
            if current_map_idx >= 0:
                bg_key_map = {0:'class_bg', 1:'toilet_bg', 2:'health_bg', 3:'gym_bg', 4:'cafeteria_bg', 5:'computer_bg', 6:'library_bg'}
                if current_map_idx in bg_key_map and bg_key_map[current_map_idx] in IMAGES: view_surface.blit(IMAGES[bg_key_map[current_map_idx]], (-camera_x, -camera_y))
                elif current_map_idx == 7:
                    if boss_phase == 2 or boss_transition_state in ['FADE_OUT', 'RESTORE_CAMERA', 'DONE']:
                        if 'principal_bg2' in IMAGES: view_surface.blit(IMAGES['principal_bg2'], (-camera_x, -camera_y))
                    else:
                        if 'principal_bg1' in IMAGES: view_surface.blit(IMAGES['principal_bg1'], (-camera_x, -camera_y))
                    
                if current_map_idx in [0, 1, 2, 3, 4, 5, 6, 7]:
                    target_map = [CLASSROOM_MAP, TOILET_MAP, HEALTH_MAP, GYM_MAP, CAFETERIA_MAP, COMPUTER_MAP, LIBRARY_MAP, PRINCIPAL_MAP][current_map_idx]
                    start_col = max(0, int(camera_x // TILE_SIZE)); end_col = min(len(target_map[0]), int((camera_x + VIEW_W) // TILE_SIZE) + 1)
                    start_row = max(0, int(camera_y // TILE_SIZE)); end_row = min(len(target_map), int((camera_y + VIEW_H) // TILE_SIZE) + 1)
                    for row_idx in range(start_row, end_row):
                        for col_idx in range(start_col, end_col):
                            if target_map[row_idx][col_idx] == 2:
                                if room_state == ROOM_CLEARED:
                                    x, y = col_idx * TILE_SIZE - camera_x, row_idx * TILE_SIZE - camera_y
                                    floating_offset = math.sin(pygame.time.get_ticks() * 0.005) * 3; cx = x + TILE_SIZE / 2
                                    p1, p2, p3 = (cx - 6, y - 10 + floating_offset), (cx + 6, y - 10 + floating_offset), (cx, y - 2 + floating_offset)
                                    pygame.draw.polygon(view_surface, (255, 255, 100), [p1, p2, p3]); pygame.draw.polygon(view_surface, (150, 150, 50), [p1, p2, p3], 1)
                            
                            # 👇 [여기에 추가!] 컴퓨터실(5번 맵) 방어막 아이템 눈에 띄는 반짝임 효과
                            elif target_map[row_idx][col_idx] == 3 and current_map_idx == 5:
                                if "방어막" not in player.seen_items:
                                    cx = col_idx * TILE_SIZE - camera_x + TILE_SIZE / 2
                                    cy = row_idx * TILE_SIZE - camera_y + TILE_SIZE / 2
                                    
                                    # 시간에 따라 커졌다 작아지는(맥박) 값 계산
                                    pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
                                    glow_radius = int(12 + 8 * pulse)
                                    
                                    # 은은하게 퍼지는 파란색 원형 후광 효과
                                    pygame.draw.circle(view_surface, (50, 150, 255), (cx, cy), glow_radius + 5, 2)
                                    pygame.draw.circle(view_surface, (100, 200, 255), (cx, cy), glow_radius, 4)
                                    
                                    # 강렬한 하얀색 십자가(별) 반짝임
                                    star_size = 10 + 10 * pulse
                                    pygame.draw.line(view_surface, (255, 255, 255), (cx - star_size, cy), (cx + star_size, cy), 3)
                                    pygame.draw.line(view_surface, (255, 255, 255), (cx, cy - star_size), (cx, cy + star_size), 3)
                                    pygame.draw.circle(view_surface, (255, 255, 255), (cx, cy), 5)
                                
                            
            else:
                if 'naye_home_bg' in IMAGES: view_surface.blit(IMAGES['naye_home_bg'], (-camera_x, -camera_y))
                start_col = max(0, int(camera_x // TILE_SIZE)); end_col = min(len(NAYE_HOME_MAP[0]), int((camera_x + VIEW_W) // TILE_SIZE) + 1)
                start_row = max(0, int(camera_y // TILE_SIZE)); end_row = min(len(NAYE_HOME_MAP), int((camera_y + VIEW_H) // TILE_SIZE) + 1)
                for row_idx in range(start_row, end_row):
                    for col_idx in range(start_col, end_col):
                        tile_val = NAYE_HOME_MAP[row_idx][col_idx]
                        x, y = col_idx * TILE_SIZE - camera_x, row_idx * TILE_SIZE - camera_y
                        if tile_val == 3 and not player.has_bag:
                            if 'backpack' in IMAGES: view_surface.blit(IMAGES['backpack'], (x, y))
                            else:
                                bag_rect = pygame.Rect(x + 6, y + 8, TILE_SIZE - 12, TILE_SIZE - 16)
                                pygame.draw.rect(view_surface, (230, 60, 60), bag_rect, border_radius=4); pygame.draw.rect(view_surface, (180, 40, 40), bag_rect, 2, border_radius=4)
                                pygame.draw.arc(view_surface, (180, 40, 40), (x + 10, y + 2, TILE_SIZE - 20, 12), 0, 3.1415, 2)
                        
                        is_show_mark = False
                        if tile_val == 2: is_show_mark = True
                        elif tile_val == 3 and not player.has_bag: is_show_mark = True

                        if is_show_mark:
                            floating_offset = math.sin(pygame.time.get_ticks() * 0.005) * 3; cx = x + TILE_SIZE / 2
                            p1, p2, p3 = (cx - 6, y - 10 + floating_offset), (cx + 6, y - 10 + floating_offset), (cx, y - 2 + floating_offset)
                            pygame.draw.polygon(view_surface, (255, 255, 100), [p1, p2, p3]); pygame.draw.polygon(view_surface, (150, 150, 50), [p1, p2, p3], 1)

            for sp in spawners: sp.draw(view_surface, camera_x, camera_y)
            for item in dropped_items: item.draw(view_surface, camera_x, camera_y)
            for puddle in soap_puddles: puddle.draw(view_surface, camera_x, camera_y)
            for mine in library_mines: mine.draw(view_surface, camera_x, camera_y)

            if boss_transition_state in ['WIDE_SHOT', 'METEOR_FALL']:
                warn_pulse = (math.sin(pygame.time.get_ticks() * 0.008) + 1.0) / 2.0
                warn_alpha = int(30 + 60 * warn_pulse)
                warn_surf = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
                warn_surf.fill((255, 30, 30, warn_alpha))
                for border_thick in range(3):
                    border_alpha = int(80 + 120 * warn_pulse) - border_thick * 30
                    if border_alpha > 0:
                        pygame.draw.rect(warn_surf, (255, 80, 80, min(255, border_alpha)),
                                         (border_thick, border_thick, VIEW_W - border_thick * 2, VIEW_H - border_thick * 2), 3)
                warn_font = get_korean_font(36, bold=True)
                warn_text_alpha = int(120 + 135 * warn_pulse)
                warn_text_surf = warn_font.render("⚠ 전체 공격 예고 ⚠", True, (255, 255, 80))
                warn_text_surf.set_alpha(warn_text_alpha)
                warn_surf.blit(warn_text_surf, (VIEW_W // 2 - warn_text_surf.get_width() // 2, 30))
                shield_hint = get_korean_font(22)
                shield_hint_surf = shield_hint.render("방어막 아이템으로 방어 가능!", True, (100, 200, 255))
                shield_hint_surf.set_alpha(warn_text_alpha)
                warn_surf.blit(shield_hint_surf, (VIEW_W // 2 - shield_hint_surf.get_width() // 2, 75))
                view_surface.blit(warn_surf, (0, 0))

            if boss_transition_state in ['METEOR_FALL', 'EXPLOSION']:
                mx, my = int(meteor_pos.x - camera_x), int(meteor_pos.y - camera_y)
                if boss_transition_state == 'METEOR_FALL':
                    meteor_imgs = IMAGES.get('boss_meteor', [])
                    if len(meteor_imgs) >= 10:
                        frame_idx = int(meteor_frame) % 10
                        view_surface.blit(meteor_imgs[frame_idx], meteor_imgs[frame_idx].get_rect(center=(mx, my)))
                    else:
                        pygame.draw.polygon(view_surface, (255, 100, 0), [(mx-60, my), (mx+60, my), (mx, my-400)])
                        pygame.draw.polygon(view_surface, (255, 200, 50), [(mx-30, my), (mx+30, my), (mx, my-300)])
                        pygame.draw.circle(view_surface, (255, 50, 0), (mx, my), 90); pygame.draw.circle(view_surface, (255, 200, 50), (mx, my), 50)
                else:
                    pygame.draw.circle(view_surface, (255, 50, 0), (mx, my), 90); pygame.draw.circle(view_surface, (255, 200, 50), (mx, my), 50)

            if room_state == ROOM_COMBAT:
                for enemy in enemies: enemy.draw(view_surface, camera_x, camera_y, player.pos)
            for bullet in bullets: bullet.draw(view_surface, camera_x, camera_y)
            for e_bullet in enemy_bullets: e_bullet.draw(view_surface, camera_x, camera_y)
            for boom in boomerangs: boom.draw(view_surface, camera_x, camera_y)
            for cr in chopstick_rains: cr.draw(view_surface, camera_x, camera_y)
            for db in dust_bursts: db.draw(view_surface, camera_x, camera_y)
            
            # 🛑 [플레이어 고정] 보스 대화 중일 때는 강제로 뒷모습으로 정지
            if boss_talk_state == 'TALKING':
                up_anims = IMAGES.get('player_run_up', [])
                if up_anims:
                    up_1_img = up_anims[0]
                    draw_x = int(player.pos.x - camera_x)
                    draw_y = int(player.pos.y - camera_y)
                    view_surface.blit(up_1_img, up_1_img.get_rect(center=(draw_x, draw_y)))
                else:
                    player.draw(view_surface, camera_x, camera_y)
            else:
                player.draw(view_surface, camera_x, camera_y)
            
            for dp in dust_particles: dp.draw(view_surface, camera_x, camera_y) 
            for p in particles: p.draw(view_surface, camera_x, camera_y)
            for sp in shield_particles: sp.draw(view_surface, camera_x, camera_y)
            for s_eff in slash_effects: s_eff.draw(view_surface, camera_x, camera_y)
            for sw in static_waves: sw.draw(view_surface, camera_x, camera_y)
            if blue_overlay_alpha > 0:
                blue_s = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
                blue_s.fill((30, 60, 200, int(blue_overlay_alpha * 100)))
                view_surface.blit(blue_s, (0, 0))
            for d_txt in damage_texts: d_txt.draw(view_surface, camera_x, camera_y)

            # ==================== 문 방향 화살표 표시 ====================
            arrow_color = (255, 255, 0)  # 밝은 노란색
            arrow_distance = 60  # 플레이어 중심으로부터의 거리
            arrow_pulse = math.sin(pygame.time.get_ticks() * 0.004) * 10  # 부드러운 펄스 효과
            show_arrow = False
            door_positions = []  # 문의 월드 좌표 리스트

            if current_map_idx == -1:
                # 나예 집: 가방을 주운 후에만 출구(아래쪽 중앙) 화살표 표시
                if player.has_bag:
                    door_positions.append((room_w // 2, room_h - 22))
                    show_arrow = True
            elif current_map_idx >= 0 and room_state == ROOM_CLEARED and not boss_defeated:
                # 미니맵 위치 기반으로 문 방향 계산 (보스 사망 후에는 표시 안 함)
                pos_curr = minimap_positions[current_map_idx]
                if current_map_idx > 0:
                    pos_prev = minimap_positions[current_map_idx - 1]
                    dx, dy = pos_prev[0] - pos_curr[0], pos_prev[1] - pos_curr[1]
                    if dx == 1: door_positions.append((room_w - 22, room_h // 2))    # RIGHT
                    elif dx == -1: door_positions.append((22, room_h // 2))           # LEFT
                    elif dy == 1: door_positions.append((room_w // 2, room_h - 22))   # BOTTOM
                    elif dy == -1: door_positions.append((room_w // 2, 22))            # TOP
                if current_map_idx < len(MAP_DATA) - 1:
                    pos_next = minimap_positions[current_map_idx + 1]
                    dx, dy = pos_next[0] - pos_curr[0], pos_next[1] - pos_curr[1]
                    if dx == 1: door_positions.append((room_w - 22, room_h // 2))    # RIGHT
                    elif dx == -1: door_positions.append((22, room_h // 2))           # LEFT
                    elif dy == 1: door_positions.append((room_w // 2, room_h - 22))   # BOTTOM
                    elif dy == -1: door_positions.append((room_w // 2, 22))            # TOP
                if door_positions:
                    show_arrow = True

            if show_arrow and door_positions:
                for door_x, door_y in door_positions:
                    # 플레이어에서 문까지의 방향 벡터
                    dir_x = door_x - player.pos.x
                    dir_y = door_y - player.pos.y
                    dist = math.sqrt(dir_x * dir_x + dir_y * dir_y)
                    if dist < 1: continue
                    
                    # 정규화된 방향 벡터
                    nx, ny = dir_x / dist, dir_y / dist
                    
                    # 화살표 중심 위치 (플레이어 주변)
                    arr_cx = player.pos.x + nx * (arrow_distance + arrow_pulse) - camera_x
                    arr_cy = player.pos.y + ny * (arrow_distance + arrow_pulse) - camera_y
                    
                    # 화살표 각도 (라디안)
                    angle = math.atan2(ny, nx)
                    
                    # 화살표 삼각형 꼭짓점 계산
                    tip_x = arr_cx + math.cos(angle) * 14
                    tip_y = arr_cy + math.sin(angle) * 14
                    left_x = arr_cx + math.cos(angle + 2.5) * 10
                    left_y = arr_cy + math.sin(angle + 2.5) * 10
                    right_x = arr_cx + math.cos(angle - 2.5) * 10
                    right_y = arr_cy + math.sin(angle - 2.5) * 10
                    
                    arrow_points = [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)]
                    pygame.draw.polygon(view_surface, arrow_color, arrow_points)
                    pygame.draw.polygon(view_surface, (200, 200, 0), arrow_points, 2)
            # ============================================================

            # 👇 공유기 파동 발사 시 글리치 이펙트
            if glitch_timer > 0:
                glitch_timer -= dt
                gp = glitch_timer / 0.5
                vw_safe, vh_safe = VIEW_W, VIEW_H
                for _ in range(random.randint(3, 6)):
                    gh = random.randint(2, 12)
                    gy = random.randint(0, max(0, vh_safe - gh))
                    gw = random.randint(vw_safe // 3, vw_safe)
                    gx = random.randint(0, max(0, vw_safe - gw))
                    offset = random.randint(-60, 60)
                    rx = max(0, min(gx + offset, vw_safe - gw))
                    ry = max(0, min(gy, vh_safe - gh))
                    try:
                        glitch_slice = view_surface.subsurface(pygame.Rect(gx, gy, gw, gh)).copy()
                        view_surface.blit(glitch_slice, (rx, ry))
                    except: pass
                if random.random() < 0.5 and gp > 0:
                    tw = min(random.randint(40, 100), vw_safe)
                    th = min(random.randint(10, 40), vh_safe)
                    if tw > 0 and th > 0:
                        tx = random.randint(0, vw_safe - tw)
                        ty = random.randint(0, vh_safe - th)
                        tint = pygame.Surface((tw, th), pygame.SRCALPHA)
                        tint.fill((0, random.randint(150, 255), random.randint(200, 255), max(0, min(255, int(35 * gp)))))
                        view_surface.blit(tint, (tx, ty))

            current_zoom += (target_zoom - current_zoom) * 4 * dt

            boss_wide_active = (boss_transition_state in ['WIDE_SHOT', 'METEOR_FALL', 'EXPLOSION', 'FADE_OUT'] and current_map_idx == 7 and current_zoom < 0.99)

            if current_zoom > 1.01 or current_zoom < 0.99:
                if boss_wide_active:
                    full_w, full_h = room_w, room_h
                    full_surf = pygame.Surface((full_w, full_h))
                    full_surf.fill((0, 0, 0))
                    pygame.draw.rect(full_surf, ROOM_COLOR, (0, 0, full_w, full_h))
                    if boss_phase == 2 or boss_transition_state in ['FADE_OUT', 'RESTORE_CAMERA']:
                        if 'principal_bg2' in IMAGES: full_surf.blit(IMAGES['principal_bg2'], (0, 0))
                    else:
                        if 'principal_bg1' in IMAGES: full_surf.blit(IMAGES['principal_bg1'], (0, 0))
                    target_map = PRINCIPAL_MAP
                    for row_idx in range(len(target_map)):
                        for col_idx in range(len(target_map[0])):
                            if target_map[row_idx][col_idx] == 2:
                                pass
                            elif target_map[row_idx][col_idx] == 3:
                                if 'shield' in IMAGES:
                                    full_surf.blit(IMAGES['shield'], (col_idx * TILE_SIZE + TILE_SIZE // 2 - 12, row_idx * TILE_SIZE + TILE_SIZE // 2 - 12))
                            elif target_map[row_idx][col_idx] == 4:
                                if 'backpack' in IMAGES:
                                    full_surf.blit(IMAGES['backpack'], (col_idx * TILE_SIZE, row_idx * TILE_SIZE))
                    if room_state == ROOM_COMBAT:
                        for enemy in enemies: enemy.draw(full_surf, 0, 0, player.pos)
                    if boss_transition_state in ['METEOR_FALL']:
                        mmx, mmy = int(meteor_pos.x), int(meteor_pos.y)
                        meteor_imgs = IMAGES.get('boss_meteor', [])
                        if len(meteor_imgs) >= 10:
                            frame_idx = int(meteor_frame) % 10
                            full_surf.blit(meteor_imgs[frame_idx], meteor_imgs[frame_idx].get_rect(center=(mmx, mmy)))
                        else:
                            pygame.draw.polygon(full_surf, (255, 100, 0), [(mmx-60, mmy), (mmx+60, mmy), (mmx, mmy-400)])
                            pygame.draw.polygon(full_surf, (255, 200, 50), [(mmx-30, mmy), (mmx+30, mmy), (mmx, mmy-300)])
                            pygame.draw.circle(full_surf, (255, 50, 0), (mmx, mmy), 90)
                            pygame.draw.circle(full_surf, (255, 200, 50), (mmx, mmy), 50)
                    if boss_transition_state in ['WIDE_SHOT', 'METEOR_FALL']:
                        warn_pulse = (math.sin(pygame.time.get_ticks() * 0.008) + 1.0) / 2.0
                        warn_alpha = int(30 + 60 * warn_pulse)
                        warn_full = pygame.Surface((full_w, full_h), pygame.SRCALPHA)
                        warn_full.fill((255, 30, 30, warn_alpha))
                        for border_thick in range(3):
                            ba = int(80 + 120 * warn_pulse) - border_thick * 30
                            if ba > 0:
                                pygame.draw.rect(warn_full, (255, 80, 80, min(255, ba)), (border_thick, border_thick, full_w - border_thick * 2, full_h - border_thick * 2), max(3, 12 - border_thick * 3))
                        full_surf.blit(warn_full, (0, 0))
                        warn_text_alpha = int(120 + 135 * warn_pulse)
                        wf_big = get_korean_font(48, bold=True)
                        wt1 = wf_big.render("⚠ 전체 공격 예고 ⚠", True, (255, 255, 80))
                        wt1.set_alpha(warn_text_alpha)
                        full_surf.blit(wt1, (full_w // 2 - wt1.get_width() // 2, 40))
                        wf_sm = get_korean_font(30)
                        wt2 = wf_sm.render("방어막 아이템으로 방어 가능!", True, (100, 200, 255))
                        wt2.set_alpha(warn_text_alpha)
                        full_surf.blit(wt2, (full_w // 2 - wt2.get_width() // 2, 100))
                    player.draw(full_surf, 0, 0)
                    for p in particles: p.draw(full_surf, 0, 0)
                    for sp in shield_particles: sp.draw(full_surf, 0, 0)
                    for d_txt in damage_texts: d_txt.draw(full_surf, 0, 0)
                    fit_scale = min(VIEW_W / full_w, VIEW_H / full_h)
                    scaled_w, scaled_h = int(full_w * fit_scale), int(full_h * fit_scale)
                    scaled_full = pygame.transform.smoothscale(full_surf, (scaled_w, scaled_h))
                    blit_x = VIEW_MARGIN_X + (VIEW_W - scaled_w) // 2
                    blit_y = VIEW_MARGIN_Y + (VIEW_H - scaled_h) // 2
                    display_surface.blit(scaled_full, (blit_x, blit_y))
                else:
                    if app_state == APP_DEATH_ANIMATION: zoom_cx, zoom_cy = player.pos.x - camera_x, player.pos.y - camera_y
                    elif tutorial_state in ['PANNING', 'TALKING'] and tutorial_step in [4, 5]: zoom_cx, zoom_cy = vase_pos.x - camera_x, vase_pos.y - camera_y
                    elif tutorial_state in ['PANNING', 'TALKING'] and tutorial_step == 6: zoom_cx, zoom_cy = ball_pos.x - camera_x, ball_pos.y - camera_y
                    elif tutorial_state in ['PANNING', 'TALKING']: zoom_cx, zoom_cy = cat_pos.x - camera_x, cat_pos.y - camera_y
                    elif boss_transition_state in ['WIDE_SHOT', 'METEOR_FALL', 'EXPLOSION', 'FADE_OUT', 'RESTORE_CAMERA'] and boss_ref: zoom_cx, zoom_cy = boss_ref.pos.x - camera_x, boss_ref.pos.y - camera_y
                    else: zoom_cx, zoom_cy = player.pos.x - camera_x, player.pos.y - camera_y
                        
                    sub_w, sub_h = max(1, int(VIEW_W / current_zoom)), max(1, int(VIEW_H / current_zoom))
                    sub_x, sub_y = zoom_cx - sub_w / 2, zoom_cy - sub_h / 2
                    sub_x, sub_y = max(0, min(sub_x, VIEW_W - sub_w)), max(0, min(sub_y, VIEW_H - sub_h))
                    
                    try:
                        sub_surf = view_surface.subsurface(pygame.Rect(int(sub_x), int(sub_y), sub_w, sub_h))
                        display_surface.blit(pygame.transform.scale(sub_surf, (VIEW_W, VIEW_H)), (VIEW_MARGIN_X, VIEW_MARGIN_Y))
                    except ValueError: display_surface.blit(view_surface, (VIEW_MARGIN_X, VIEW_MARGIN_Y))
            else: display_surface.blit(view_surface, (VIEW_MARGIN_X, VIEW_MARGIN_Y))
            
            if forbidden_fake_death:
                black_s = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
                progress = 1.0 - (forbidden_fake_death_timer / 2.5) if forbidden_fake_death_timer > 0 else 1.0
                if progress < 0.3:
                    black_alpha = int(255 * (progress / 0.3))
                else:
                    black_alpha = 255
                black_s.fill((0, 0, 0, min(255, black_alpha)))
                display_surface.blit(black_s, (0, 0))
                if black_alpha > 100:
                    glitch_s = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
                    for y in range(0, LOGICAL_HEIGHT, 2):
                        if random.random() < 0.5:
                            c = random.choice([(0, 255, 0), (255, 0, 0), (0, 200, 255)])
                            a = random.randint(20, 80)
                            offset_x = random.randint(-20, 20)
                            pygame.draw.line(glitch_s, (*c, a), (offset_x, y), (LOGICAL_WIDTH + offset_x, y))
                    for _ in range(40):
                        bx = random.randint(0, LOGICAL_WIDTH)
                        by = random.randint(0, LOGICAL_HEIGHT)
                        bw = random.randint(80, LOGICAL_WIDTH)
                        bh = random.randint(3, 20)
                        c = random.choice([(255, 0, 0), (0, 255, 0), (0, 100, 255), (255, 255, 0)])
                        pygame.draw.rect(glitch_s, (*c, random.randint(40, 120)), (bx, by, bw, bh))
                    for _ in range(8):
                        sy = random.randint(0, LOGICAL_HEIGHT)
                        sh = random.randint(20, 120)
                        sx = random.randint(-30, 30)
                        try:
                            strip = display_surface.subsurface(pygame.Rect(0, min(sy, LOGICAL_HEIGHT - sh), LOGICAL_WIDTH, min(sh, LOGICAL_HEIGHT - sy)))
                            glitch_s.blit(strip, (sx, sy))
                        except: pass
                    display_surface.blit(glitch_s, (0, 0))
                if progress > 0.15:
                    fake_font = get_korean_font(80, bold=True)
                    jx, jy = random.randint(-12, 12), random.randint(-12, 12)
                    txt = fake_font.render("가짜야..", True, (255, 30, 30))
                    out = fake_font.render("가짜야..", True, (80, 0, 0))
                    tx = LOGICAL_WIDTH // 2 - txt.get_width() // 2 + jx
                    ty = LOGICAL_HEIGHT // 2 - txt.get_height() // 2 + jy
                    for dx, dy in [(-3,0),(3,0),(0,-3),(0,3),(-2,-2),(2,-2),(-2,2),(2,2)]:
                        display_surface.blit(out, (tx + dx, ty + dy))
                    display_surface.blit(txt, (tx, ty))
            
            if forbidden_respawn_flash > 0:
                flash_alpha = int(255 * (forbidden_respawn_flash / 0.4))
                flash_surf = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
                flash_surf.fill((255, 255, 255, min(255, flash_alpha)))
                display_surface.blit(flash_surf, (0, 0))

            if boss_transition_state in ['EXPLOSION', 'FADE_OUT']:
                overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
                if boss_transition_state == 'EXPLOSION': pygame.draw.circle(overlay, (255, 240, 200, 255), (LOGICAL_WIDTH//2, LOGICAL_HEIGHT//2), int(explosion_radius))
                elif boss_transition_state == 'FADE_OUT': overlay.fill((255, 240, 200, max(0, min(255, int(explosion_alpha)))))
                display_surface.blit(overlay, (0, 0))

            if boss_bubble_state == 'ACTIVE':
                boss_obj = next((e for e in enemies if e.type == 'boss'), None)
                if boss_obj:
                    bx = int(boss_obj.pos.x - camera_x + VIEW_MARGIN_X)
                    by = int(boss_obj.pos.y - camera_y + VIEW_MARGIN_Y)
                    bubble_font = get_korean_font(28)
                    current_line = boss_bubble_lines[boss_bubble_step]
                    is_last_line = boss_bubble_step == len(boss_bubble_lines) - 1
                    visible_text = current_line[:int(boss_bubble_char_idx)]
                    if is_last_line:
                        bubble_font = get_korean_font(48, bold=True)
                        text_color = (255, 30, 30)
                        char_w = bubble_font.render("시", True, text_color).get_width()
                        char_h = bubble_font.render("시", True, text_color).get_height()
                        char_gap = 8
                        visible_count = len(visible_text)
                        text_w = visible_count * char_w + max(0, visible_count - 1) * char_gap
                        text_h = char_h
                    else:
                        text_color = (255, 255, 255)
                    if not is_last_line:
                        text_surf = bubble_font.render(visible_text, True, text_color)
                        text_w = text_surf.get_width()
                        text_h = text_surf.get_height()
                    shake_ox, shake_oy = 0, 0
                    if is_last_line and int(boss_bubble_char_idx) >= len(current_line):
                        shake_ox = random.randint(-4, 4)
                        shake_oy = random.randint(-3, 3)
                    pad_x, pad_y = 25, 18
                    bubble_w = text_w + pad_x * 2
                    bubble_h = text_h + pad_y * 2
                    bubble_x = bx + 20
                    bubble_y = by - boss_obj.radius - bubble_h - 50
                    if bubble_x + bubble_w > LOGICAL_WIDTH - 10: bubble_x = bx - bubble_w - 20
                    if bubble_y < 10: bubble_y = by + boss_obj.radius + 15
                    bubble_surf = pygame.Surface((bubble_w, bubble_h), pygame.SRCALPHA)
                    if is_last_line:
                        pygame.draw.rect(bubble_surf, (40, 0, 0, 230), bubble_surf.get_rect(), border_radius=12)
                        pygame.draw.rect(bubble_surf, (200, 30, 30), bubble_surf.get_rect(), 3, border_radius=12)
                    else:
                        pygame.draw.rect(bubble_surf, (0, 0, 0, 220), bubble_surf.get_rect(), border_radius=12)
                        pygame.draw.rect(bubble_surf, (255, 200, 50), bubble_surf.get_rect(), 3, border_radius=12)
                    display_surface.blit(bubble_surf, (bubble_x + shake_ox, bubble_y + shake_oy))
                    if is_last_line:
                        for ci in range(len(visible_text)):
                            ch_surf = bubble_font.render(visible_text[ci], True, text_color)
                            ch_x = bubble_x + pad_x + ci * (char_w + char_gap) + shake_ox
                            ch_y = bubble_y + pad_y + shake_oy
                            display_surface.blit(ch_surf, (ch_x, ch_y))
                    else:
                        display_surface.blit(text_surf, (bubble_x + pad_x + shake_ox, bubble_y + pad_y + shake_oy))
                    tail_pts = [
                        (bubble_x + 20 + shake_ox, bubble_y + bubble_h - 2 + shake_oy),
                        (bubble_x + 35 + shake_ox, bubble_y + bubble_h + 14 + shake_oy),
                        (bubble_x + 50 + shake_ox, bubble_y + bubble_h - 2 + shake_oy)
                    ]
                    if bubble_y > by: tail_pts = [
                        (bubble_x + 20 + shake_ox, bubble_y + 2 + shake_oy),
                        (bubble_x + 35 + shake_ox, bubble_y - 14 + shake_oy),
                        (bubble_x + 50 + shake_ox, bubble_y + 2 + shake_oy)
                    ]
                    pygame.draw.polygon(display_surface, (0, 0, 0), tail_pts)
                    if is_last_line:
                        pygame.draw.lines(display_surface, (200, 30, 30), False, tail_pts, 3)
                    else:
                        pygame.draw.lines(display_surface, (255, 200, 50), False, tail_pts, 3)
                    if int(boss_bubble_char_idx) >= len(current_line):
                        tri_x = bubble_x + bubble_w - 22
                        tri_y = bubble_y + bubble_h - 18
                        pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
                        tri_alpha = int(100 + 155 * pulse)
                        tri_surf = pygame.Surface((16, 14), pygame.SRCALPHA)
                        pygame.draw.polygon(tri_surf, (255, 200, 50, tri_alpha), [(0, 0), (16, 0), (8, 12)])
                        display_surface.blit(tri_surf, (tri_x, tri_y))

            # 👇 보스 사망 후 화면 페이드아웃 오버레이 (전체 화면이 검게 어두워짐)
            if boss_death_fade_alpha > 0:
                fade_overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
                fade_overlay.fill((0, 0, 0, min(255, int(boss_death_fade_alpha))))
                display_surface.blit(fade_overlay, (0, 0))

            # UI 렌더링 파트
            if app_state == APP_PLAYING:
                is_talking = (tutorial_state in ['TALKING', 'MONOLOGUE'] or boss_talk_state in ['APPROACH', 'TALKING'])
                
                # 👇 나예 독백 대화창 렌더링
                if tutorial_state == 'MONOLOGUE':
                    box_w, box_h = 800, 160; box_x, box_y = center_x - box_w // 2, LOGICAL_HEIGHT - box_h - 40
                    tut_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
                    pygame.draw.rect(tut_surf, (0, 0, 0, 230), tut_surf.get_rect(), border_radius=15)
                    border_color = (150, 0, 0) if monologue_step == 1 else (200, 200, 200)
                    pygame.draw.rect(tut_surf, border_color, tut_surf.get_rect(), 3, border_radius=15)
                    display_surface.blit(tut_surf, (box_x, box_y))
                    
                    name_tag = font.render("나예", True, (255, 100, 100))
                    tag_bg = pygame.Rect(box_x + 30, box_y - 25, 120, 45)
                    pygame.draw.rect(display_surface, (50, 20, 20), tag_bg, border_radius=8)
                    display_surface.blit(name_tag, (tag_bg.centerx - name_tag.get_width()//2, tag_bg.centery - name_tag.get_height()//2))
                    
                    current_msg = monologue_messages[monologue_step]
                    max_idx = min(int(tutorial_char_idx), len(current_msg))
                    
                    if monologue_step == 1:
                        x_offset = box_x + 40
                        for char in current_msg[:max_idx]:
                            char_surf = huge_font.render(char, True, (180, 0, 0))
                            shake_x = random.randint(-4, 4); shake_y = random.randint(-4, 4)
                            display_surface.blit(char_surf, (x_offset + shake_x, box_y + 45 + shake_y))
                            x_offset += huge_font.size(char)[0] + 5
                    else:
                        for i, line in enumerate(current_msg[:max_idx].split('\n')):
                            display_surface.blit(font.render(line, True, (200, 200, 200)), (box_x + 40, box_y + 45 + i * 45))
                            
                    if max_idx >= len(current_msg) and int(pygame.time.get_ticks() / 500) % 2 == 0:
                        enter_surf = small_font.render("enter", True, (200, 200, 200))
                        display_surface.blit(enter_surf, (box_x + box_w - enter_surf.get_width() - 25, box_y + box_h - enter_surf.get_height() - 15))

                if tutorial_state == 'TALKING':
                    if 'cat_portrait' in IMAGES:
                        cat_img = IMAGES['cat_portrait']
                        cat_rect = cat_img.get_rect(bottomright=(LOGICAL_WIDTH + 10, LOGICAL_HEIGHT - 100))
                        display_surface.blit(cat_img, cat_rect)
                        
                        cat_name_tag = font.render("고양이", True, (255, 255, 255))
                        cat_name_rect = cat_name_tag.get_rect(center=(cat_rect.centerx - 10, cat_rect.bottom + 30))
                        cat_bg_rect = pygame.Rect(0, 0, 90, 40)
                        cat_bg_rect.center = cat_name_rect.center
                        pygame.draw.rect(display_surface, (50, 50, 60), cat_bg_rect, border_radius=5)
                        display_surface.blit(cat_name_tag, cat_name_rect)

                if tutorial_state == 'EXCLAMATION':
                    exc_surf = huge_font.render("!", True, (255, 50, 50))
                    draw_px = int(player.pos.x - camera_x) + VIEW_MARGIN_X; draw_py = int(player.pos.y - camera_y) + VIEW_MARGIN_Y - 80 + math.sin(pygame.time.get_ticks() * 0.02) * 5
                    display_surface.blit(exc_surf, exc_surf.get_rect(center=(draw_px, draw_py)))

                # 🎒 [나예 상시 상태창 인벤토리 가방 일러스트 파트]
                draw_base = True
                if player.inv_timer > 0 and not player.has_shield and 'naye_surprised' in IMAGES: base_img_key = 'naye_surprised'
                elif 'naye_base' in IMAGES: base_img_key = 'naye_base'
                else: draw_base = False
                    
                if draw_base:
                    illust_x = VIEW_MARGIN_X // 2
                    illust_y = LOGICAL_HEIGHT - 550
                    raw_base_img = IMAGES[base_img_key].copy()
                    ui_rect = raw_base_img.get_rect(center=(illust_x, illust_y))
                    
                    # 👑 보스 대화 진행 중일 때는 하단 레이어에 강제로 덮어씌워지는 예전 상태창을 무조건 증발(투명화)시킵니다.
                    if boss_talk_state == 'TALKING':
                        img = pygame.Surface(ui_rect.size, pygame.SRCALPHA)
                        img.fill((0, 0, 0, 0)) 
                    else:
                        img = raw_base_img
                    
                    display_surface.blit(img, ui_rect)
                    
                    # 상태창 텍스트 및 UI 레이아웃 정렬 유지
                    name_tag = font.render("나예", True, (255, 255, 255))
                    name_rect = name_tag.get_rect(center=(illust_x, ui_rect.bottom + 30))
                    bg_rect = pygame.Rect(0, 0, 90, 40)
                    bg_rect.center = name_rect.center
                    pygame.draw.rect(display_surface, (50, 50, 60), bg_rect, border_radius=5)
                    display_surface.blit(name_tag, name_rect)
                    hp_top_y = ui_rect.top + 10
                else:
                    illust_x = VIEW_MARGIN_X // 2; hp_top_y = 100
                    
                hp_w = 200; hp_h = 26; hp_x = illust_x - hp_w // 2
                pygame.draw.rect(display_surface, (50, 50, 50), (hp_x, hp_top_y, hp_w, hp_h), border_radius=8)
                pygame.draw.rect(display_surface, (255, 50, 50), (hp_x, hp_top_y, max(0, hp_w * (player.hp/player.max_hp)), hp_h), border_radius=8)
                hp_txt = small_font.render(f"{player.hp} / {player.max_hp}", True, (255, 255, 255))
                display_surface.blit(hp_txt, hp_txt.get_rect(center=(hp_x + hp_w // 2, hp_top_y + hp_h // 2)))

                display_surface.blit(font.render(f"진행 시간: {format_time(current_play_time)} | [ESC] 설정", True, (200, 200, 200)), (40, 30))
                
                if tutorial_state == 'TALKING':
                    box_w, box_h = 800, 160; box_x, box_y = center_x - box_w // 2, LOGICAL_HEIGHT - box_h - 40
                    tut_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
                    pygame.draw.rect(tut_surf, (0, 0, 0, 255), tut_surf.get_rect(), border_radius=15); pygame.draw.rect(tut_surf, (200, 200, 200, 255), tut_surf.get_rect(), 3, border_radius=15)
                    display_surface.blit(tut_surf, (box_x, box_y))
                    name_tag = font.render("고양이", True, (255, 255, 100)); tag_bg = pygame.Rect(box_x + 30, box_y - 25, 120, 45)
                    pygame.draw.rect(display_surface, (50, 50, 60), tag_bg, border_radius=8); display_surface.blit(name_tag, (tag_bg.centerx - name_tag.get_width()//2, tag_bg.centery - name_tag.get_height()//2))
                    current_msg = tutorial_messages[tutorial_step]; max_idx = min(int(tutorial_char_idx), len(current_msg))
                    for i, line in enumerate(current_msg[:max_idx].split('\n')): display_surface.blit(font.render(line, True, (255, 255, 255)), (box_x + 40, box_y + 45 + i * 45))
                    if max_idx >= len(current_msg) and int(pygame.time.get_ticks() / 500) % 2 == 0:
                        enter_surf = small_font.render("enter", True, (200, 200, 200)); display_surface.blit(enter_surf, (box_x + box_w - enter_surf.get_width() - 25, box_y + box_h - enter_surf.get_height() - 15))

                # 👇 보스 컷씬 전용 대화창 및 컷씬 초상화 렌더링 구역
                if boss_talk_state == 'TALKING':
                    box_w, box_h = 800, 160; box_x, box_y = center_x - box_w // 2, LOGICAL_HEIGHT - box_h - 40
                    tut_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
                    
                    msg_data = boss_messages[boss_talk_step]
                    speaker = msg_data["speaker"]; emo = msg_data["emo"]
                    text = msg_data["text"]; style = msg_data.get("style", ""); size_style = msg_data.get("size", "")
                    is_right = (speaker == "노아")
                    
                    pygame.draw.rect(tut_surf, (0, 0, 0, 255), tut_surf.get_rect(), border_radius=15)
                    pygame.draw.rect(tut_surf, (200, 200, 200, 255), tut_surf.get_rect(), 3, border_radius=15)
                    display_surface.blit(tut_surf, (box_x, box_y))
                    
                    name_tag = font.render(speaker, True, (255, 255, 100))
                    tag_bg = pygame.Rect(box_x + 30, box_y - 25, 120, 45)
                    pygame.draw.rect(display_surface, (50, 50, 60), tag_bg, border_radius=8)
                    display_surface.blit(name_tag, (tag_bg.centerx - name_tag.get_width()//2, tag_bg.centery - name_tag.get_height()//2))

                    current_noah_emo = "기본"
                    current_naye_emo = "기본"
                    for i in range(boss_talk_step + 1):
                        m = boss_messages[i]
                        if m["speaker"] == "노아": current_noah_emo = m["emo"]
                        elif m["speaker"] == "나예": current_naye_emo = m["emo"]

                    # ==========================================
                    # 👑 [우측 초상화 - 노아 캐싱 최적화 + 투명도 유지]
                    # ==========================================
                    noah_key = f'noah_{current_noah_emo}'
                    
                    if noah_key in IMAGES and tutorial_state == 'DONE' and current_map_idx == 7:
                        if boss_talk_step < len(boss_messages) and (speaker == "노아" or boss_talk_step > 0):
                            # [최적화 패치] 매 프레임 연산하지 않도록 완성본을 캐싱하여 저장합니다.
                            proc_noah_key = f"proc_{noah_key}"
                            if proc_noah_key not in IMAGES:
                                noah_img_raw = IMAGES[noah_key]
                                noah_visible_rect = noah_img_raw.get_bounding_rect()
                                if noah_visible_rect.width > 0 and noah_visible_rect.height > 0:
                                    noah_sub = noah_img_raw.subsurface(noah_visible_rect)
                                    temp_img = pygame.Surface(noah_sub.get_size(), pygame.SRCALPHA)
                                    temp_img.fill((0, 0, 0, 0))
                                    temp_img.blit(noah_sub, (0, 0))
                                else:
                                    temp_img = noah_img_raw
                                IMAGES[proc_noah_key] = pygame.transform.smoothscale(temp_img, (300, 790))
                                
                            noah_img = IMAGES[proc_noah_key].copy()
                            noah_center_x = LOGICAL_WIDTH - 165
                            noah_center_y = LOGICAL_HEIGHT - 460
                            noah_rect = noah_img.get_rect(center=(noah_center_x, noah_center_y))
                            
                            # ✨ 노아가 말하지 않을 때는 반투명 처리
                            if not is_right: 
                                alpha_surf = pygame.Surface(noah_img.get_size(), pygame.SRCALPHA)
                                alpha_surf.fill((255, 255, 255, 100))
                                noah_img.blit(alpha_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                                
                            display_surface.blit(noah_img, noah_rect)

                            noah_name_tag = font.render("노아", True, (255, 255, 255))
                            noah_name_rect = noah_name_tag.get_rect(center=(noah_center_x + 50, noah_rect.bottom + 30))
                            noah_bg_rect = pygame.Rect(0, 0, 90, 40)
                            noah_bg_rect.center = noah_name_rect.center
                            pygame.draw.rect(display_surface, (50, 50, 60), noah_bg_rect, border_radius=5)
                            display_surface.blit(noah_name_tag, noah_name_rect)

                    # ==========================================
                    # 👑 [좌측 초상화 - 나예 (원본 naye_base 완벽 동기화!)]
                    # ==========================================
                    boss_naye_key = f'naye_face_{current_naye_emo}'
                    
                    if boss_naye_key not in IMAGES and 'naye_base' in IMAGES:
                        boss_naye_key = 'naye_base'

                    if boss_naye_key in IMAGES and tutorial_state == 'DONE' and current_map_idx == 7:
                        # 💡 크기 조절/자르기 없이 원본 이미지(1700x900)를 그대로 복사합니다! (연산량 0)
                        cutscene_img = IMAGES[boss_naye_key].copy()
                        
                        # ✨ 나예가 말하지 않을 때는 반투명 처리
                        if is_right: 
                            alpha_surf = pygame.Surface(cutscene_img.get_size(), pygame.SRCALPHA)
                            alpha_surf.fill((255, 255, 255, 100))
                            cutscene_img.blit(alpha_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                            
                        # 자르지 않았으므로 원래 naye_base가 있던 (ui_rect) 좌표 그대로 블릿! 
                        # 1픽셀도 안 틀어지고 상태창 가방 나예 위치와 100% 동일하게 나타납니다.
                        display_surface.blit(cutscene_img, ui_rect)
                        
                    # 4. 글자 특수 효과 렌더링
                    max_idx = min(int(boss_char_idx), len(text))
                    disp_text = text[:max_idx]
                    x_offset = box_x + 40; y_offset = box_y + 45
                    
                    if style == "blood":
                        trigger_word = "죽어줘야겠어"
                        if trigger_word in text and text != trigger_word:
                            curr_char_count = 0
                            for char in disp_text:
                                if char == '\n':
                                    x_offset = box_x + 40; y_offset += 45; continue
                                if curr_char_count >= text.find(trigger_word):
                                    char_surf = huge_font.render(char, True, (180, 0, 0))
                                    shake_x = random.randint(-4, 4); shake_y = random.randint(-4, 4)
                                    display_surface.blit(char_surf, (x_offset + shake_x, y_offset + shake_y - 15))
                                    x_offset += huge_font.size(char)[0] + 5
                                else:
                                    char_surf = font.render(char, True, (255, 255, 255))
                                    display_surface.blit(char_surf, (x_offset, y_offset))
                                    x_offset += font.size(char)[0] + 2
                                curr_char_count += 1
                        else:
                            for char in disp_text:
                                if char == '\n': 
                                    x_offset = box_x + 40; y_offset += 60; continue
                                char_surf = huge_font.render(char, True, (180, 0, 0))
                                shake_x = random.randint(-4, 4); shake_y = random.randint(-4, 4)
                                display_surface.blit(char_surf, (x_offset + shake_x, y_offset + shake_y - 15))
                                x_offset += huge_font.size(char)[0] + 5
                                
                    elif size_style == "large":
                        for i, line in enumerate(disp_text.split('\n')):
                            display_surface.blit(huge_font.render(line, True, (255, 255, 255)), (x_offset, y_offset - 10 + i * 60))
                            
                    elif style == "mumble":
                        for i, line in enumerate(disp_text.split('\n')):
                            # ✨ [글자 키우기] small_font 에서 font 로 변경, 줄 간격 45로 넓힘!
                            surf = font.render(line, True, (160, 160, 160))
                            surf.set_alpha(140)
                            display_surface.blit(surf, (x_offset, y_offset + i * 45))
                    else:
                        for i, line in enumerate(disp_text.split('\n')): 
                            display_surface.blit(font.render(line, True, (255, 255, 255)), (x_offset, y_offset + i * 45))
                            
                    if max_idx >= len(text) and int(pygame.time.get_ticks() / 500) % 2 == 0:
                        enter_surf = small_font.render("enter", True, (200, 200, 200))
                        display_surface.blit(enter_surf, (box_x + box_w - enter_surf.get_width() - 25, box_y + box_h - enter_surf.get_height() - 15))

                if not current_overlay and tutorial_state == 'DONE':
                    p_col, p_row = int(player.pos.x // TILE_SIZE), int(player.pos.y // TILE_SIZE); is_near_interact = False
                    if current_map_idx == -1:
                        for r in range(max(0, p_row-1), min(len(NAYE_HOME_MAP), p_row+2)):
                            for c in range(max(0, p_col-1), min(len(NAYE_HOME_MAP[0]), p_col+2)):
                                tile_v = NAYE_HOME_MAP[r][c]
                                dist = pygame.math.Vector2(c*TILE_SIZE+TILE_SIZE/2, r*TILE_SIZE+TILE_SIZE/2).distance_to(player.pos)
                                if dist < 55:
                                    if tile_v == 2: 
                                        is_near_interact = True; break
                                    elif tile_v == 3 and not player.has_bag: 
                                        is_near_interact = True; break
                    elif current_map_idx == 5:
                        if "방어막" not in player.seen_items:
                            for r in range(max(0, p_row-1), min(len(COMPUTER_MAP), p_row+2)):
                                for c in range(max(0, p_col-1), min(len(COMPUTER_MAP[0]), p_col+2)):
                                    if COMPUTER_MAP[r][c] == 3 and pygame.math.Vector2(c*TILE_SIZE+TILE_SIZE/2, r*TILE_SIZE+TILE_SIZE/2).distance_to(player.pos) < 55: 
                                        is_near_interact = True; break
                    elif current_map_idx in [0, 1, 2, 3, 4, 5, 6, 7]: 
                        target_map = [CLASSROOM_MAP, TOILET_MAP, HEALTH_MAP, GYM_MAP, CAFETERIA_MAP, COMPUTER_MAP, LIBRARY_MAP, PRINCIPAL_MAP][current_map_idx]
                        for r in range(max(0, p_row-1), min(len(target_map), p_row+2)):
                            for c in range(max(0, p_col-1), min(len(target_map[0]), p_col+2)):
                                if target_map[r][c] == 2 and pygame.math.Vector2(c*TILE_SIZE+TILE_SIZE/2, r*TILE_SIZE+TILE_SIZE/2).distance_to(player.pos) < 55:
                                    if room_state == ROOM_CLEARED: is_near_interact = True
                                    break
                    if not is_near_interact:
                        for item in dropped_items:
                            if item.pos.distance_to(player.pos) < player.radius + item.radius + 15: is_near_interact = True; break
                                
                    if is_near_interact:
                        prompt_surf = small_font.render(f"[{get_key_display_name(config['keys']['INTERACT'])}] 상호작용", True, (255, 255, 100))
                        draw_px = int(player.pos.x - camera_x) + VIEW_MARGIN_X; draw_py = int(player.pos.y - camera_y) + VIEW_MARGIN_Y - 70 
                        bg_rect = prompt_surf.get_rect(center=(draw_px, draw_py)); bg_rect.inflate_ip(10, 10)
                        alpha_surf = pygame.Surface(bg_rect.size, pygame.SRCALPHA); pygame.draw.rect(alpha_surf, (40, 40, 45, 180), alpha_surf.get_rect(), border_radius=5)
                        display_surface.blit(alpha_surf, bg_rect); display_surface.blit(prompt_surf, prompt_surf.get_rect(center=(draw_px, draw_py)))
                
                if popup_timer > 0:
                    popup_timer -= dt; popup_surf = mini_font.render(popup_msg, True, (255, 200, 200))
                    if boss_wide_active:
                        room_w_local = room_w; room_h_local = room_h
                        fs = min(VIEW_W / room_w_local, VIEW_H / room_h_local)
                        sw, sh = int(room_w_local * fs), int(room_h_local * fs)
                        bx = VIEW_MARGIN_X + (VIEW_W - sw) // 2
                        by = VIEW_MARGIN_Y + (VIEW_H - sh) // 2
                        draw_px = int(bx + player.pos.x * fs); draw_py = int(by + player.pos.y * fs) - 40
                    else:
                        draw_px = int(player.pos.x - camera_x) + VIEW_MARGIN_X; draw_py = int(player.pos.y - camera_y) + VIEW_MARGIN_Y - 55
                    bg_rect = popup_surf.get_rect(center=(draw_px, draw_py)); bg_rect.inflate_ip(12, 8)
                    alpha_surf = pygame.Surface(bg_rect.size, pygame.SRCALPHA); pygame.draw.rect(alpha_surf, (30, 30, 35, 200), alpha_surf.get_rect(), border_radius=5)
                    display_surface.blit(alpha_surf, bg_rect); display_surface.blit(popup_surf, popup_surf.get_rect(center=(draw_px, draw_py)))

                if player.has_bag and not is_talking:
                    inv_cols = 3; inv_rows = 4; slot_size = 65; slot_margin = 10
                    inv_w = (slot_size * inv_cols) + (slot_margin * (inv_cols + 1)); inv_h = (slot_size * inv_rows) + (slot_margin * (inv_rows + 1)) + 50
                    inv_x = LOGICAL_WIDTH - inv_w - 40; inv_y = 330 
                    
                    inv_surf = pygame.Surface((inv_w, inv_h), pygame.SRCALPHA); pygame.draw.rect(inv_surf, (30, 30, 35, 220), inv_surf.get_rect(), border_radius=15); pygame.draw.rect(inv_surf, (150, 150, 160, 255), inv_surf.get_rect(), 3, border_radius=15)
                    display_surface.blit(inv_surf, (inv_x, inv_y)); inv_title = font.render("- 인벤토리 -", True, (255, 255, 255)); display_surface.blit(inv_title, (inv_x + inv_w//2 - inv_title.get_width()//2, inv_y + 15))
                    
                    hover_tooltip = None

                    for r in range(inv_rows):
                        for c in range(inv_cols):
                            idx = r * inv_cols + c; sx = inv_x + slot_margin + c * (slot_size + slot_margin); sy = inv_y + 50 + slot_margin + r * (slot_size + slot_margin)
                            pygame.draw.rect(display_surface, (50, 50, 60), (sx, sy, slot_size, slot_size), border_radius=8); pygame.draw.rect(display_surface, (80, 80, 90), (sx, sy, slot_size, slot_size), 2, border_radius=8)
                            item = player.inventory[idx]
                            if item:
                                if item["name"] == "회복물약" and 'potion' in IMAGES:
                                    inv_potion = pygame.transform.scale(IMAGES['potion'], (40, 40))
                                    display_surface.blit(inv_potion, inv_potion.get_rect(center=(sx + slot_size//2, sy + slot_size//2)))
                                elif item["name"] == "방어막" and 'shield' in IMAGES:
                                    inv_shield = pygame.transform.scale(IMAGES['shield'], (40, 40))
                                    display_surface.blit(inv_shield, inv_shield.get_rect(center=(sx + slot_size//2, sy + slot_size//2)))
                                else:
                                    display_surface.blit(mini_font.render(item["name"][:3], True, (255, 150, 150)), (sx + 8, sy + 20))
                                
                                display_surface.blit(mini_font.render(str(item["count"]), True, (255, 255, 255)), (sx + slot_size - 18, sy + slot_size - 22))
                                
                                if sx <= scaled_mouse_pos[0] <= sx + slot_size and sy <= scaled_mouse_pos[1] <= sy + slot_size:
                                    hover_tooltip = item["name"]

                    qs_w = (slot_size * 4) + (slot_margin * 5); qs_h = slot_size + (slot_margin * 2)
                    qs_x = inv_x + (inv_w - qs_w) // 2; qs_y = inv_y + inv_h + 20
                    qs_surf = pygame.Surface((qs_w, qs_h), pygame.SRCALPHA); pygame.draw.rect(qs_surf, (30, 30, 35, 220), qs_surf.get_rect(), border_radius=15); pygame.draw.rect(qs_surf, (150, 150, 160, 255), qs_surf.get_rect(), 3, border_radius=15)
                    display_surface.blit(qs_surf, (qs_x, qs_y))
                    
                    for i in range(4):
                        bx = qs_x + slot_margin + i * (slot_size + slot_margin); by = qs_y + slot_margin
                        pygame.draw.rect(display_surface, (50, 50, 60), (bx, by, slot_size, slot_size), border_radius=8); pygame.draw.rect(display_surface, (80, 80, 90), (bx, by, slot_size, slot_size), 2, border_radius=8)
                        display_surface.blit(mini_font.render(str(i+1), True, (255, 255, 100)), (bx + 6, by + 4))
                        item = player.quick_slots[i]
                        if item:
                            if item["name"] == "회복물약" and 'potion' in IMAGES:
                                qs_potion = pygame.transform.scale(IMAGES['potion'], (40, 40))
                                display_surface.blit(qs_potion, qs_potion.get_rect(center=(bx + slot_size//2, by + slot_size//2)))
                            elif item["name"] == "방어막" and 'shield' in IMAGES:
                                qs_shield = pygame.transform.scale(IMAGES['shield'], (40, 40))
                                display_surface.blit(qs_shield, qs_shield.get_rect(center=(bx + slot_size//2, by + slot_size//2)))
                            else:
                                display_surface.blit(mini_font.render(item["name"][:3], True, (255, 150, 150)), (bx + 8, by + 20))
                            
                            display_surface.blit(mini_font.render(str(item["count"]), True, (255, 255, 255)), (bx + slot_size - 18, by + slot_size - 22))
                            
                            if bx <= scaled_mouse_pos[0] <= bx + slot_size and by <= scaled_mouse_pos[1] <= by + slot_size:
                                hover_tooltip = item["name"]

                        if player.item_cooldown > 0:
                            cd_h = int(slot_size * (player.item_cooldown / 5.0)); cd_surf = pygame.Surface((slot_size, cd_h), pygame.SRCALPHA); cd_surf.fill((0, 0, 0, 180)); display_surface.blit(cd_surf, (bx, by + (slot_size - cd_h)))

                    if context_menu_active:
                        cm_x, cm_y = context_menu_pos
                        if cm_x + 120 > LOGICAL_WIDTH: cm_x = LOGICAL_WIDTH - 120
                        if cm_y + 70 > LOGICAL_HEIGHT: cm_y = LOGICAL_HEIGHT - 70
                        pygame.draw.rect(display_surface, (40, 40, 45), (cm_x, cm_y, 120, 70), border_radius=5); pygame.draw.rect(display_surface, (200, 200, 200), (cm_x, cm_y, 120, 70), 2, border_radius=5)
                        use_txt = small_font.render("사용", True, (255, 255, 255)); display_surface.blit(use_txt, use_txt.get_rect(center=(cm_x + 60, cm_y + 17)))
                        pygame.draw.line(display_surface, (100, 100, 100), (cm_x+5, cm_y+35), (cm_x+115, cm_y+35))
                        assign_txt = small_font.render("퀵슬롯 저장" if context_selected_inv_idx != -1 else "배낭에 넣기", True, (255, 255, 255))
                        display_surface.blit(assign_txt, assign_txt.get_rect(center=(cm_x + 60, cm_y + 52)))

                    if hover_tooltip and not context_menu_active:
                        tt_surf = small_font.render(hover_tooltip, True, (255, 255, 255))
                        tt_mx, tt_my = scaled_mouse_pos
                        tt_rect = tt_surf.get_rect(midbottom=(tt_mx, tt_my - 15))
                        if tt_rect.right > LOGICAL_WIDTH: tt_rect.right = LOGICAL_WIDTH - 5
                        if tt_rect.top < 0: tt_rect.top = 5
                        tt_bg = tt_rect.inflate(20, 12)
                        pygame.draw.rect(display_surface, (20, 20, 25), tt_bg, border_radius=6)
                        pygame.draw.rect(display_surface, (200, 200, 200), tt_bg, 1, border_radius=6)
                        display_surface.blit(tt_surf, tt_rect)

                if not is_talking:
                    map_name_str = "나예 집" if current_map_idx == -1 else MAP_DATA[current_map_idx]['name']
                    map_name_surf = large_font.render(f"- {map_name_str} -", True, (255, 255, 255)); display_surface.blit(map_name_surf, (LOGICAL_WIDTH - map_name_surf.get_width() - 40, 20))

                    if current_map_idx >= 0:
                        minimap_room_size = 24; minimap_margin = 16; minimap_start_x = 1710; minimap_start_y = 140  
                        for i in range(len(MAP_DATA) - 1):
                            curr_vis = cleared_rooms[i] or (i == current_map_idx) or (abs(i - current_map_idx) == 1)
                            next_vis = cleared_rooms[i+1] or (i+1 == current_map_idx) or (abs(i+1 - current_map_idx) == 1)
                            if curr_vis and next_vis:
                                x1 = minimap_start_x + minimap_positions[i][0] * (minimap_room_size + minimap_margin) + minimap_room_size // 2; y1 = minimap_start_y + minimap_positions[i][1] * (minimap_room_size + minimap_margin) + minimap_room_size // 2
                                x2 = minimap_start_x + minimap_positions[i+1][0] * (minimap_room_size + minimap_margin) + minimap_room_size // 2; y2 = minimap_start_y + minimap_positions[i+1][1] * (minimap_room_size + minimap_margin) + minimap_room_size // 2
                                pygame.draw.line(display_surface, (100, 100, 110), (x1, y1), (x2, y2), 4)

                        for i in range(len(MAP_DATA)):
                            if not (cleared_rooms[i] or i == current_map_idx or abs(i - current_map_idx) == 1): continue
                            rect_x = minimap_start_x + minimap_positions[i][0] * (minimap_room_size + minimap_margin); rect_y = minimap_start_y + minimap_positions[i][1] * (minimap_room_size + minimap_margin)
                            if i == current_map_idx: bg_color, border_color = (200, 200, 200), (255, 255, 255)
                            elif cleared_rooms[i]: bg_color, border_color = (70, 70, 70), (130, 130, 130)
                            else: bg_color, border_color = (30, 30, 30), (80, 80, 80)
                            pygame.draw.rect(display_surface, bg_color, (rect_x, rect_y, minimap_room_size, minimap_room_size), border_radius=4); pygame.draw.rect(display_surface, border_color, (rect_x, rect_y, minimap_room_size, minimap_room_size), 2, border_radius=4)
                            if i == current_map_idx: pygame.draw.circle(display_surface, PLAYER_COLOR, (rect_x + minimap_room_size//2, rect_y + minimap_room_size//2), 6)

        elif app_state == APP_GAME_OVER:
            display_surface.fill((15, 10, 10))
            go_title = huge_font.render("GAME OVER", True, (255, 50, 50))
            display_surface.blit(go_title, (center_x - go_title.get_width()//2, 250))
            btn_go_restart.draw(display_surface, center_x, scaled_mouse_pos)
            if continue_enabled:
                btn_go_continue.y = 540; btn_go_continue.rect.y = 540
                btn_go_continue.draw(display_surface, center_x, scaled_mouse_pos)
                btn_go_quit.y = 630; btn_go_quit.rect.y = 630
            else:
                btn_go_quit.y = 540; btn_go_quit.rect.y = 540
            btn_go_quit.draw(display_surface, center_x, scaled_mouse_pos)

        elif app_state == APP_ENDING:
            # 어두운 배경
            display_surface.fill((5, 0, 0))
            
            # 👇 엔딩 이미지 표시 (step에 따라 다른 이미지)
            def _draw_ending_img(img_key, alpha):
                if img_key and img_key in IMAGES:
                    img = IMAGES[img_key].copy()
                    img.set_alpha(max(0, min(255, int(alpha))))
                    img_w, img_h = img.get_size()
                    img_x = center_x - img_w // 2
                    img_y = (LOGICAL_HEIGHT - img_h) // 2 - 135
                    display_surface.blit(img, (img_x, img_y))
            
            if ending_state == 'FADE_OUT':
                # 이전 이미지가 서서히 사라짐
                old_key = _get_ending_img_key(ending_step)
                _draw_ending_img(old_key, ending_fade_alpha)
            elif ending_state == 'FADE_IN':
                # 다음 이미지가 서서히 등장
                new_key = _get_ending_img_key(ending_step)
                _draw_ending_img(new_key, ending_fade_alpha)
            else:
                ending_img_key = None
                if ending_state == 'INTRO':
                    ending_img_key = 'ending_1'
                elif ending_step >= 4:
                    ending_img_key = 'ending_4'
                elif ending_step >= 1:
                    ending_img_key = 'ending_3'
                elif ending_step >= 0:
                    ending_img_key = 'ending_2'
                
                if ending_img_key and ending_img_key in IMAGES:
                    ending_img = IMAGES[ending_img_key]
                    img_w, img_h = ending_img.get_size()
                    img_x = center_x - img_w // 2
                    img_y = (LOGICAL_HEIGHT - img_h) // 2 - 135
                    display_surface.blit(ending_img, (img_x, img_y))
            
            msg_data = ending_messages[ending_step] if ending_step >= 0 else ending_messages[0]
            speaker = msg_data["speaker"] if ending_step >= 0 else ""
            text = msg_data["text"]
            style = msg_data.get("style", "normal")
            
            # 대화창 배경
            box_w, box_h = 900, 200
            box_x, box_y = center_x - box_w // 2, LOGICAL_HEIGHT - box_h - 60
            tut_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            pygame.draw.rect(tut_surf, (0, 0, 0, 230), tut_surf.get_rect(), border_radius=15)
            
            base_border = (200, 200, 200)
            if style == "ending_blood":
                base_border = (150, 0, 0)
            pygame.draw.rect(tut_surf, base_border, tut_surf.get_rect(), 3, border_radius=15)
            display_surface.blit(tut_surf, (box_x, box_y))
            
            # 말하는 사람 이름 태그
            name_color = (255, 100, 100) if speaker == "나예" else (255, 255, 100)
            name_tag = font.render(speaker, True, name_color)
            tag_bg = pygame.Rect(box_x + 30, box_y - 25, 120, 45)
            tag_bg_color = (50, 20, 20) if speaker == "나예" else (50, 50, 60)
            pygame.draw.rect(display_surface, tag_bg_color, tag_bg, border_radius=8)
            display_surface.blit(name_tag, (tag_bg.centerx - name_tag.get_width()//2, tag_bg.centery - name_tag.get_height()//2))
            
            # 👇 엔딩 초상화 감정 결정 (현재 step의 메시지 데이터 기반)
            # step이 음수(FADE_OUT 중 INTRO)일 땐 초상화 감정을 기본으로
            if ending_step >= 0:
                msg_noah_emo = msg_data.get("noah_emo")
                msg_naye_emo = msg_data.get("naye_emo")
                # 감정이 명시되었으면 기억하고, 없으면 마지막 감정 유지
                if msg_noah_emo is not None:
                    ending_last_noah_emo = msg_noah_emo
                if msg_naye_emo is not None:
                    ending_last_naye_emo = msg_naye_emo
                noah_emo = ending_last_noah_emo
                naye_emo = ending_last_naye_emo
            else:
                noah_emo = ending_last_noah_emo
                naye_emo = ending_last_naye_emo
            
            # 초상화 표시
            # 노아 (오른쪽)
            noah_key = f'noah_{noah_emo}'
            draw_noah = noah_key in IMAGES
            if not draw_noah:
                noah_key = 'noah_기본'
                draw_noah = noah_key in IMAGES
            
            if draw_noah:
                proc_noah_key = f"proc_{noah_key}"
                if proc_noah_key not in IMAGES:
                    noah_img_raw = IMAGES[noah_key]
                    noah_visible_rect = noah_img_raw.get_bounding_rect()
                    if noah_visible_rect.width > 0 and noah_visible_rect.height > 0:
                        noah_sub = noah_img_raw.subsurface(noah_visible_rect)
                        temp_img = pygame.Surface(noah_sub.get_size(), pygame.SRCALPHA)
                        temp_img.fill((0, 0, 0, 0))
                        temp_img.blit(noah_sub, (0, 0))
                    else:
                        temp_img = noah_img_raw
                    IMAGES[proc_noah_key] = pygame.transform.smoothscale(temp_img, (300, 790))
                
                noah_img = IMAGES[proc_noah_key].copy()
                noah_center_x = LOGICAL_WIDTH - 165
                noah_center_y = LOGICAL_HEIGHT - 460
                noah_rect = noah_img.get_rect(center=(noah_center_x, noah_center_y))
                
                if speaker != "노아":
                    alpha_surf = pygame.Surface(noah_img.get_size(), pygame.SRCALPHA)
                    alpha_surf.fill((255, 255, 255, 100))
                    noah_img.blit(alpha_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                display_surface.blit(noah_img, noah_rect)
                
                noah_name_tag = font.render("노아", True, (255, 255, 255))
                noah_name_rect = noah_name_tag.get_rect(center=(noah_center_x + 40, noah_rect.bottom + 30))
                noah_bg_rect = pygame.Rect(0, 0, 90, 40)
                noah_bg_rect.center = noah_name_rect.center
                pygame.draw.rect(display_surface, (50, 50, 60), noah_bg_rect, border_radius=5)
                display_surface.blit(noah_name_tag, noah_name_rect)
            
            # 나예 (왼쪽) - 감정별 이미지 사용
            naye_face_key = f'naye_face_{naye_emo}'
            if naye_face_key in IMAGES:
                naye_img = IMAGES[naye_face_key].copy()
            elif 'naye_base' in IMAGES:
                naye_img = IMAGES['naye_base'].copy()
            else:
                naye_img = None
            
            if naye_img is not None:
                illust_x = VIEW_MARGIN_X // 2
                illust_y = LOGICAL_HEIGHT - 550
                ui_rect = naye_img.get_rect(center=(illust_x, illust_y))
                
                if speaker != "나예":
                    alpha_surf = pygame.Surface(naye_img.get_size(), pygame.SRCALPHA)
                    alpha_surf.fill((255, 255, 255, 100))
                    naye_img.blit(alpha_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                display_surface.blit(naye_img, ui_rect)
                
                naye_name_tag = font.render("나예", True, (255, 255, 255))
                naye_name_rect = naye_name_tag.get_rect(center=(illust_x, ui_rect.bottom + 30))
                naye_bg_rect = pygame.Rect(0, 0, 90, 40)
                naye_bg_rect.center = naye_name_rect.center
                pygame.draw.rect(display_surface, (50, 50, 60), naye_bg_rect, border_radius=5)
                display_surface.blit(naye_name_tag, naye_name_rect)
            
            # 텍스트 출력
            max_idx = min(int(ending_char_idx), len(text))
            disp_text = text[:max_idx]
            
            if style == "ending_blood":
                # 피 색상의 큰 글자, 한 글자씩 흔들리며 등장
                x_offset = box_x + 40
                y_offset = box_y + 20
                shake_x_base = math.sin(ending_shake_timer * 15) * 5
                shake_y_base = math.cos(ending_shake_timer * 13) * 4
                
                for i, char in enumerate(disp_text):
                    if char == '\n':
                        pass  # 줄바꿈은 무시 (단일 라인으로 처리)
                    else:
                        char_shake_x = shake_x_base + random.randint(-3, 3)
                        char_shake_y = shake_y_base + random.randint(-3, 3)
                        char_surf = huge_font.render(char, True, (180, 0, 0))
                        char_out = huge_font.render(char, True, (80, 0, 0))
                        # 테두리
                        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                            display_surface.blit(char_out, (x_offset + dx + char_shake_x, y_offset + dy + char_shake_y))
                        display_surface.blit(char_surf, (x_offset + char_shake_x, y_offset + char_shake_y))
                        x_offset += huge_font.size(char)[0] + 8
            else:
                # 일반 텍스트
                x_offset = box_x + 40
                y_offset = box_y + 50
                for line in disp_text.split('\n'):
                    display_surface.blit(font.render(line, True, (255, 255, 255)), (x_offset, y_offset))
                    y_offset += 45
            
            # Enter 표시
            show_enter = False
            if ending_state == 'INTRO':
                # INTRO 상태에서는 텍스트가 없어도 Enter 표시 깜빡임
                show_enter = True
            elif max_idx >= len(text):
                show_enter = True
            
            if show_enter and int(pygame.time.get_ticks() / 500) % 2 == 0:
                enter_surf = small_font.render("enter", True, (200, 200, 200))
                display_surface.blit(enter_surf, (box_x + box_w - enter_surf.get_width() - 25, box_y + box_h - enter_surf.get_height() - 15))
            
            # 👇 검은 화면 페이드 오버레이 (엔딩 종료 후)
            if ending_state in ('BLACK_FADE', 'BLACK_WAIT'):
                black_overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
                black_overlay.fill((0, 0, 0, int(ending_black_alpha)))
                display_surface.blit(black_overlay, (0, 0))

        elif app_state == APP_CREDITS:
            display_surface.fill((0, 0, 0))
            if credits_paused:
                if 'title_bg' in IMAGES:
                    img_area_w = LOGICAL_WIDTH // 2 - 40
                    img_area_h = LOGICAL_HEIGHT - 200
                    img_area_x = 20
                    img_area_y = 100
                    raw = IMAGES['title_bg']
                    iw, ih = raw.get_size()
                    scale = min(img_area_w / iw, img_area_h / ih)
                    nw, nh = int(iw * scale), int(ih * scale)
                    scaled = pygame.transform.smoothscale(raw, (nw, nh))
                    bx = img_area_x + (img_area_w - nw) // 2
                    by = img_area_y + (img_area_h - nh) // 2
                    display_surface.blit(scaled, (bx, by))
            else:
                credits_center_x = LOGICAL_WIDTH // 2
                img_area_w = LOGICAL_WIDTH // 2 - 40
                text_area_x = credits_center_x + 20
                text_area_w = LOGICAL_WIDTH // 2 - 60
                img_area_x = 20
                img_area_y = 100
                img_area_h = LOGICAL_HEIGHT - 200
                if credits_image_groups and credits_img_group_idx < len(credits_image_groups):
                    cur_group = credits_image_groups[credits_img_group_idx]
                    n_imgs = len(cur_group)
                    if n_imgs == 4:
                        cols_i, rows_i = 2, 2
                    elif n_imgs == 3:
                        cols_i, rows_i = 3, 1
                    elif n_imgs == 2:
                        cols_i, rows_i = 2, 1
                    else:
                        cols_i, rows_i = 1, 1
                    pad = 15
                    cell_w = (img_area_w - pad * (cols_i + 1)) // cols_i
                    cell_h = (img_area_h - pad * (rows_i + 1)) // rows_i
                    is_monster_group = credits_img_group_idx >= credits_monster_start_idx
                    for idx_i, img_key in enumerate(cur_group):
                        if img_key in IMAGES:
                            col_i = idx_i % cols_i
                            row_i = idx_i // cols_i
                            cx = img_area_x + pad + col_i * (cell_w + pad)
                            cy = img_area_y + pad + row_i * (cell_h + pad)
                            raw_img = IMAGES[img_key]
                            iw, ih = raw_img.get_size()
                            if is_monster_group:
                                scale = min(cell_w / iw, cell_h / ih, 160 / max(iw, ih))
                            elif img_key == '주현_기본':
                                scale = min(cell_w / iw, cell_h / ih)
                            else:
                                scale = min(cell_w / iw, cell_h / ih)
                            new_w, new_h = int(iw * scale), int(ih * scale)
                            if new_w > 0 and new_h > 0:
                                scaled = pygame.transform.smoothscale(raw_img, (new_w, new_h))
                                scaled.set_alpha(max(0, min(255, int(credits_img_alpha))))
                                blit_x = cx + (cell_w - new_w) // 2
                                blit_y = cy + (cell_h - new_h) // 2
                                display_surface.blit(scaled, (blit_x, blit_y))
            credits_center_x = LOGICAL_WIDTH // 2
            text_area_x = credits_center_x + 20
            text_area_w = LOGICAL_WIDTH // 2 - 60
            clip_rect = pygame.Rect(text_area_x - 10, 0, text_area_w + 20, LOGICAL_HEIGHT)
            display_surface.set_clip(clip_rect)
            y_pos = credits_scroll_y
            line_h = credits_font_body.get_height() + 25
            title_h = credits_font_title.get_height() + 40
            last_line_h = credits_font_last.get_height() + 30
            for style, text in credits_lines:
                if style == "title":
                    rendered = credits_font_title.render(text, True, (255, 255, 255))
                    text_x = text_area_x + (text_area_w - rendered.get_width()) // 2
                    if -rendered.get_height() < y_pos < LOGICAL_HEIGHT + rendered.get_height():
                        display_surface.blit(rendered, (text_x, y_pos))
                    y_pos += title_h
                elif style == "last":
                    rendered = credits_font_last.render(text, True, (255, 255, 255))
                    text_x = text_area_x + (text_area_w - rendered.get_width()) // 2
                    if -rendered.get_height() < y_pos < LOGICAL_HEIGHT + rendered.get_height():
                        display_surface.blit(rendered, (text_x, y_pos))
                    y_pos += last_line_h
                else:
                    if text == "":
                        y_pos += line_h
                        continue
                    rendered = credits_font_body.render(text, True, (255, 255, 255))
                    text_x = text_area_x + (text_area_w - rendered.get_width()) // 2
                    if -rendered.get_height() < y_pos < LOGICAL_HEIGHT + rendered.get_height():
                        display_surface.blit(rendered, (text_x, y_pos))
                    y_pos += line_h
            display_surface.set_clip(None)
            if credits_paused and credits_can_enter:
                if int(pygame.time.get_ticks() / 500) % 2 == 0:
                    enter_surf = font.render("Enter를 눌러 처음으로", True, (255, 255, 255))
                    display_surface.blit(enter_surf, (LOGICAL_WIDTH // 2 - enter_surf.get_width() // 2, LOGICAL_HEIGHT - 60))

        if current_overlay:
            if current_overlay == 'ITEM_INFO':
                overlay_bg = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA); overlay_bg.fill((0, 0, 0, 180)); display_surface.blit(overlay_bg, (0, 0))
                popup_rect = pygame.Rect(center_x - 350, 150, 700, 600)
                pygame.draw.rect(display_surface, (40, 40, 45), popup_rect, border_radius=15); pygame.draw.rect(display_surface, (200, 200, 200), popup_rect, 3, border_radius=15)
                
                item_name = viewing_item if viewing_item else "아이템"
                desc = "아이템 설명이 없습니다."
                if item_name == "회복물약": desc = "사용 시 체력을 10 회복 합니다."
                elif item_name == "방어막": desc = "강력한 공격을 막을 때 유용할지도..?\n단 하나 뿐이니 신중하게 쓰자."
                elif item_name == "배낭": desc = "배낭안에 아이템을 우클릭하여 조정할 수 있다."
                
                img_rect = pygame.Rect(center_x - 280, 200, 200, 200) 
                pygame.draw.rect(display_surface, (60, 60, 70), img_rect, border_radius=10)
                
                if item_name == "회복물약" and 'potion' in IMAGES:
                        big_img = pygame.transform.scale(IMAGES['potion'], (120, 120))
                        display_surface.blit(big_img, big_img.get_rect(center=img_rect.center))
                elif item_name == "방어막" and 'shield_large' in IMAGES:
                        display_surface.blit(IMAGES['shield_large'], IMAGES['shield_large'].get_rect(center=img_rect.center))
                elif item_name == "배낭" and 'backpack_large' in IMAGES:
                        display_surface.blit(IMAGES['backpack_large'], IMAGES['backpack_large'].get_rect(center=img_rect.center))
                elif item_name == "배낭":
                        pygame.draw.rect(display_surface, (180, 100, 50), (img_rect.centerx - 40, img_rect.centery - 40, 80, 80), border_radius=10)
                        pygame.draw.rect(display_surface, (120, 60, 30), (img_rect.centerx - 40, img_rect.centery - 40, 80, 80), 5, border_radius=10)
                        pygame.draw.arc(display_surface, (120, 60, 30), (img_rect.centerx - 20, img_rect.centery - 60, 40, 40), 0, 3.1415, 5)
                
                name_inner = huge_font.render(item_name, True, (255, 255, 255))
                name_out = huge_font.render(item_name, True, (0, 0, 0))
                name_rect = name_inner.get_rect(midleft=(center_x - 30, img_rect.centery))
                
                offsets = [(-1,-1), (0,-1), (1,-1), (-1,0), (1,0), (-1,1), (0,1), (1,1)]
                for dx, dy in offsets: display_surface.blit(name_out, (name_rect.x + dx, name_rect.y + dy))
                display_surface.blit(name_inner, name_rect)
                
                enter_text = "enter를 눌러 확인" if item_name == "배낭" else "enter를 눌러 배낭에 넣기"
                enter_surf = small_font.render(enter_text, True, (150, 150, 150))
                enter_rect = enter_surf.get_rect(center=(center_x, 700))
                display_surface.blit(enter_surf, enter_rect)
                
                lines = []
                for paragraph in desc.split('\n'):
                    current_line = ""
                    for char in paragraph:
                        test_line = current_line + char
                        if font.size(test_line)[0] > 600:
                            lines.append(current_line)
                            current_line = char
                        else: current_line = test_line
                    lines.append(current_line)
                
                desc_start_y = img_rect.bottom + 40
                for i, line in enumerate(lines):
                    line_surf = font.render(line.strip(), True, (200, 200, 200))
                    display_surface.blit(line_surf, (center_x - 300, desc_start_y + i * 40))
                
            elif current_overlay == 'LEAVE_HOME':
                overlay_bg = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA); overlay_bg.fill((0, 0, 0, 180)); display_surface.blit(overlay_bg, (0, 0))
                pygame.draw.rect(display_surface, (40, 40, 45), (center_x - 350, 150, 700, 600), border_radius=15); pygame.draw.rect(display_surface, (200, 200, 200), (center_x - 350, 150, 700, 600), 3, border_radius=15)
                l1 = huge_font.render("학교로 가시겠습니까?", True, (255, 255, 255)); display_surface.blit(l1, (center_x - l1.get_width()//2, 280)) 
                btn_leave_yes.draw(display_surface, center_x, scaled_mouse_pos); btn_leave_no.draw(display_surface, center_x, scaled_mouse_pos)
                warn_msg = small_font.render("전투가 시작되니 주의하세요!", True, (255, 150, 150)); display_surface.blit(warn_msg, (center_x - warn_msg.get_width()//2, 580))
            
            elif current_overlay == 'DIFFICULTY':
                overlay_bg = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA); overlay_bg.fill((0, 0, 0, 180)); display_surface.blit(overlay_bg, (0, 0))
                pygame.draw.rect(display_surface, (40, 40, 45), (center_x - 350, 150, 700, 600), border_radius=15); pygame.draw.rect(display_surface, (200, 200, 200), (center_x - 350, 150, 700, 600), 3, border_radius=15)
                if difficulty_sub == 'SELECT':
                    title_surf = large_font.render("난이도 선택", True, (255, 255, 255))
                    display_surface.blit(title_surf, (center_x - title_surf.get_width() // 2, 190))
                    btn_diff_easy.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_diff_normal.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_diff_hard.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_diff_x.draw(display_surface, center_x, scaled_mouse_pos)
                elif difficulty_sub == 'DESC' and selected_difficulty:
                    d = difficulty_data[selected_difficulty]
                    title_surf = large_font.render(f"난이도: {d['name']}", True, (255, 255, 255))
                    display_surface.blit(title_surf, (center_x - title_surf.get_width() // 2, 230))
                    for i, segments in enumerate(d['desc_lines']):
                        total_w = sum(font.size(text)[0] for text, _ in segments)
                        cur_x = center_x - total_w // 2
                        for text, color in segments:
                            surf = font.render(text, True, color)
                            display_surface.blit(surf, (cur_x, 350 + i * 50))
                            cur_x += surf.get_width()
                    btn_diff_back.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_diff_confirm.draw(display_surface, center_x, scaled_mouse_pos)
            
            elif current_overlay == 'SETTINGS':
                overlay_bg = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA); overlay_bg.fill((0, 0, 0, 180)); display_surface.blit(overlay_bg, (0, 0))
                pygame.draw.rect(display_surface, (40, 40, 45), (center_x - 350, 150, 700, 600), border_radius=15); pygame.draw.rect(display_surface, (200, 200, 200), (center_x - 350, 150, 700, 600), 3, border_radius=15)
                if current_tab == "KEYS":
                    for action, btn in key_buttons.items():
                        if waiting_for_key == action: btn.text, btn.base_color = "대기중", (150, 50, 50)
                        elif config['keys'][action] is None: btn.text, btn.base_color = "지정없음", (180, 50, 50)
                        else: btn.text, btn.base_color = get_key_display_name(config['keys'][action]), (80, 80, 90)
                        btn.draw(display_surface, center_x, scaled_mouse_pos)
                        lbl_surf = small_font.render(key_labels_kr[action], True, (255, 255, 255)); display_surface.blit(lbl_surf, (center_x + btn.rel_x - lbl_surf.get_width() // 2, btn.rect.y - lbl_surf.get_height() - 8))
                
                btn_video.draw(display_surface, center_x, scaled_mouse_pos)
                btn_audio.draw(display_surface, center_x, scaled_mouse_pos)
                btn_keys.draw(display_surface, center_x, scaled_mouse_pos)
                
                if app_state == APP_MAIN_MENU: btn_close_overlay.draw(display_surface, center_x, scaled_mouse_pos)
                elif app_state in [APP_PLAYING, APP_GAME_OVER, APP_STORY, APP_ENDING, APP_CREDITS]:
                    btn_return_main.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_close_settings_game.draw(display_surface, center_x, scaled_mouse_pos)
                btn_reset_defaults.draw(display_surface, center_x, scaled_mouse_pos)

                if current_tab == "VIDEO":
                    btn_window.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_borderless.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_fullscreen.draw(display_surface, center_x, scaled_mouse_pos)
                elif current_tab == "AUDIO":
                    t1 = font.render(f"마스터 볼륨: {config['volume']}%", True, (255, 255, 255)); display_surface.blit(t1, (center_x - t1.get_width()//2, 275))
                    btn_vol_down.draw(display_surface, center_x, scaled_mouse_pos); btn_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
                    t2 = font.render(f"배경 볼륨: {config.get('bgm_volume', 50)}%", True, (255, 255, 255)); display_surface.blit(t2, (center_x - t2.get_width()//2, 405))
                    btn_bgm_vol_down.draw(display_surface, center_x, scaled_mouse_pos); btn_bgm_vol_up.draw(display_surface, center_x, scaled_mouse_pos)
                    t3 = font.render(f"음성 볼륨: {config['voice_volume']}%", True, (255, 255, 255)); display_surface.blit(t3, (center_x - t3.get_width()//2, 535))
                    btn_voice_vol_down.draw(display_surface, center_x, scaled_mouse_pos); btn_voice_vol_up.draw(display_surface, center_x, scaled_mouse_pos)

                if confirm_reset_tab:
                    _cr_bg = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA); _cr_bg.fill((0, 0, 0, 120)); display_surface.blit(_cr_bg, (0, 0))
                    pygame.draw.rect(display_surface, (50, 50, 55), (center_x - 250, 350, 500, 250), border_radius=15); pygame.draw.rect(display_surface, (200, 200, 200), (center_x - 250, 350, 500, 250), 3, border_radius=15)
                    _cr_msg = large_font.render("현재 설정이 되돌아갑니다.", True, (255, 255, 255)); display_surface.blit(_cr_msg, (center_x - _cr_msg.get_width()//2, 400))
                    btn_reset_confirm_no.draw(display_surface, center_x, scaled_mouse_pos)
                    btn_reset_confirm_yes.draw(display_surface, center_x, scaled_mouse_pos)
                    
            elif current_overlay in ['SAVE', 'LOAD']:
                overlay_bg = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA); overlay_bg.fill((0, 0, 0, 180)); display_surface.blit(overlay_bg, (0, 0))
                pygame.draw.rect(display_surface, (40, 40, 45), (center_x - 350, 150, 700, 600), border_radius=15); pygame.draw.rect(display_surface, (200, 200, 200), (center_x - 350, 150, 700, 600), 3, border_radius=15)
                if confirm_delete_slot:
                    l1, l2 = large_font.render(f"슬롯 {confirm_delete_slot}의 데이터를 정말", True, (255, 100, 100)), large_font.render("삭제하시겠습니까?", True, (255, 100, 100))
                    display_surface.blit(l1, (center_x - l1.get_width()//2, 290)); display_surface.blit(l2, (center_x - l2.get_width()//2, 350))
                    btn_confirm_yes_del.draw(display_surface, center_x, scaled_mouse_pos); btn_confirm_no.draw(display_surface, center_x, scaled_mouse_pos)
                elif confirm_save_slot:
                    l1, l2 = large_font.render(f"슬롯 {confirm_save_slot}에 진행상황을", True, (100, 255, 100)), large_font.render("저장하시겠습니까?", True, (100, 255, 100))
                    display_surface.blit(l1, (center_x - l1.get_width()//2, 290)); display_surface.blit(l2, (center_x - l2.get_width()//2, 350))
                    btn_confirm_yes_save.draw(display_surface, center_x, scaled_mouse_pos); btn_confirm_no.draw(display_surface, center_x, scaled_mouse_pos)
                else:
                    ts = large_font.render("진행상황 저장" if current_overlay == 'SAVE' else "게임 불러오기", True, (255, 255, 255)); display_surface.blit(ts, (center_x - ts.get_width()//2, 170))
                    for i in range(3): 
                        slot_buttons[i].draw(display_surface, center_x, scaled_mouse_pos)
                        if saves_data[f"slot_{i+1}"]: delete_buttons[i].draw(display_surface, center_x, scaled_mouse_pos)
                    btn_close_overlay.draw(display_surface, center_x, scaled_mouse_pos)

        if 'cursor_normal' in IMAGES and 'cursor_click' in IMAGES:
            pygame.mouse.set_visible(False)
            display_surface.blit(IMAGES['cursor_click'] if is_mouse_down else IMAGES['cursor_normal'], scaled_mouse_pos)
        else: pygame.mouse.set_visible(True)

        screen.blit(pygame.transform.smoothscale(display_surface, (current_width, current_height)), (0, 0))
        pygame.display.flip()
    pygame.quit(); sys.exit()

if __name__ == "__main__": main()