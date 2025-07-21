import pygame
import sys
import os
import json

# Settings
FPS = 60
DIRECTIONS = ['left', 'down', 'up', 'right']

KEY_MAPPING = {
    pygame.K_a: 'left',
    pygame.K_s: 'down',
    pygame.K_k: 'up',
    pygame.K_l: 'right'
}

HEALTH_MAX = 100
RECEPTOR_Y = 700  # y position of receptors (adjust to your screen height)
HIT_WINDOWS = {
    'sick': 30,
    'good': 60,
    'bad': 100,
    'trash': 130
}
FIRE_COMBO_THRESHOLD = 15
fire_colors = [
    (255, 50, 0),
    (255, 100, 0),
    (255, 150, 0),
    (255, 200, 0),
]

class Note:
    def __init__(self, direction, image, x):
        self.direction = direction
        self.image = image
        self.x = x
        self.y = -100 

    def update(self, speed):
        self.y += speed

    def draw(self, surface):
        rect = self.image.get_rect(center=(self.x, int(self.y)))
        surface.blit(self.image, rect)

def list_json_files():
    return [f for f in os.listdir('.') if f.endswith('.json')]

def get_song_title(json_file):
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
            if 'song' in data and data['song']:
                return os.path.splitext(os.path.basename(data['song']))[0]
            else:
                return os.path.splitext(os.path.basename(json_file))[0]
    except Exception:
        return os.path.splitext(os.path.basename(json_file))[0]

def load_images():
    receptors = {}
    notes = {}
    for direction in DIRECTIONS:
        receptors[direction] = pygame.image.load(f"graphics/{direction}Receptor.png").convert_alpha()
        notes[direction] = pygame.image.load(f"graphics/{direction}ReceptorD.png").convert_alpha()
    return receptors, notes

def get_centered_column_x(screen_width, num_columns, receptor_img_width):
    spacing = receptor_img_width + 20
    total_width = (num_columns - 1) * spacing
    start_x = (screen_width - total_width) // 2
    return {DIRECTIONS[i]: start_x + i * spacing for i in range(num_columns)}

def song_selection_menu(screen, font, big_font, json_files, song_titles):
    selected = 0
    clock = pygame.time.Clock()
    while True:
        screen.fill((0, 0, 0))
        title_text = big_font.render("Select a Song", True, (255, 255, 255))
        screen.blit(title_text, ((screen.get_width() - title_text.get_width()) // 2, 40))

        if not json_files:
            no_song_text = font.render("No songs found!", True, (255, 0, 0))
            screen.blit(no_song_text, ((screen.get_width() - no_song_text.get_width()) // 2, 150))
        else:
            for i, title in enumerate(song_titles):
                color = (255, 255, 0) if i == selected else (255, 255, 255)
                text = font.render(title, True, color)
                screen.blit(text, (100, 150 + i * 40))

        instr = font.render("Use UP/DOWN to navigate, ENTER to select", True, (180, 180, 180))
        screen.blit(instr, ((screen.get_width() - instr.get_width()) // 2, screen.get_height() - 60))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(json_files)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(json_files)
                elif event.key == pygame.K_RETURN and json_files:
                    return json_files[selected]

        clock.tick(FPS)

def get_judgment(distance):
    if distance <= HIT_WINDOWS['sick']:
        return 'sick'
    elif distance <= HIT_WINDOWS['good']:
        return 'good'
    elif distance <= HIT_WINDOWS['bad']:
        return 'bad'
    elif distance <= HIT_WINDOWS['trash']:
        return 'trash'
    return 'miss'

def main():
    pygame.init()
    pygame.mixer.init()

    screen_info = pygame.display.Info()
    global SCREEN_WIDTH, SCREEN_HEIGHT
    SCREEN_WIDTH, SCREEN_HEIGHT = screen_info.current_w, screen_info.current_h
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
    pygame.display.set_caption("Pysu!Mania")

    font = pygame.font.SysFont(None, 36)
    big_font = pygame.font.SysFont(None, 48)
    clock = pygame.time.Clock()

    # List JSON song files
    json_files = list_json_files()
    song_titles = [get_song_title(f) for f in json_files]

    selected_json_file = song_selection_menu(screen, font, big_font, json_files, song_titles)

    # Load song data from JSON
    with open(selected_json_file, 'r') as f:
        song_data = json.load(f)

    music_sheet_raw = song_data.get('musicSheet', [])
    song_path = song_data.get('song', None)
    bpm = song_data.get('bpm', 120)
    note_speed = song_data.get('noteSpeed', 15)

    receptors, note_images = load_images()
    receptor_img_width = receptors[DIRECTIONS[0]].get_width()
    COLUMN_X = get_centered_column_x(SCREEN_WIDTH, len(DIRECTIONS), receptor_img_width)

    # Precalculate note spawn times in ms based on bpm
    beat_interval_ms = 60000 / bpm
    music_sheet_raw = song_data.get('musicSheet', [])
    music_sheet = music_sheet_raw

    # Game variables
    notes = []
    next_note_index = 0
    score = 0
    combo = 0
    max_combo = 0
    multiplier = 1.0
    health = HEALTH_MAX
    hit_counts = {k: 0 for k in list(HIT_WINDOWS.keys()) + ['miss']}
    paused = False
    hit_display_text = ""
    hit_display_count = 0
    hit_display_timer = 0
    hit_display_alpha = 0
    fire_anim_frame = 0
    fire_text_glow = 0

    game_state = 'menu'
    song_start_time = 0

    def reset_rhythm_state():
        nonlocal notes, next_note_index, score, combo, max_combo, multiplier, health, hit_counts
        nonlocal paused, hit_display_text, hit_display_count, hit_display_timer, hit_display_alpha
        nonlocal fire_anim_frame, fire_text_glow, game_state, song_start_time

        notes = []
        next_note_index = 0
        score = 0
        combo = 0
        max_combo = 0
        multiplier = 1.0
        health = HEALTH_MAX
        hit_counts = {k: 0 for k in list(HIT_WINDOWS.keys()) + ['miss']}
        paused = False
        hit_display_text = ""
        hit_display_count = 0
        hit_display_timer = 0
        hit_display_alpha = 0
        fire_anim_frame = 0
        fire_text_glow = 0
        game_state = 'playing'
        song_start_time = pygame.time.get_ticks()

    def update_multiplier(combo):
        if combo >= 50:
            return 2.0
        elif combo >= 30:
            return 1.5
        elif combo >= 15:
            return 1.2
        else:
            return 1.0

    def spawn_note_from_line(line):
        parts = line.split()
        for i, char in enumerate(parts):
            if char == 'o':
                direction = DIRECTIONS[i]
                note = Note(direction, note_images[direction], COLUMN_X[direction])
                notes.append(note)

    def draw_text_centered(surface, text, font, color, y):
        text_surf = font.render(text, True, color)
        x = (SCREEN_WIDTH - text_surf.get_width()) // 2
        surface.blit(text_surf, (x, y))

    speed = note_speed

    running = True
    fire_active = False

    while running:
        clock.tick(FPS)

        # Update fire effect
        fire_active = combo >= FIRE_COMBO_THRESHOLD
        if fire_active:
            fire_anim_frame = (fire_anim_frame + 1) % len(fire_colors)
            fire_text_glow = min(255, fire_text_glow + 25)
        else:
            fire_text_glow = max(0, fire_text_glow - 25)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if game_state == 'menu':
                    if event.key == pygame.K_RETURN:
                        reset_rhythm_state()
                        # Load and play music
                        if song_path and os.path.isfile(song_path):
                            try:
                                pygame.mixer.music.load(song_path)
                                pygame.mixer.music.play()
                                song_start_time = pygame.time.get_ticks()
                            except Exception as e:
                                print(f"Error loading music: {e}")
                                song_start_time = pygame.time.get_ticks()
                        else:
                            song_start_time = pygame.time.get_ticks()
                        game_state = 'playing'

                    elif event.key == pygame.K_ESCAPE:
                        running = False

                elif game_state == 'playing':
                    if event.key == pygame.K_ESCAPE:
                        paused = not paused
                        if paused:
                            pygame.mixer.music.pause()
                        else:
                            pygame.mixer.music.unpause()

                    if not paused and event.key in KEY_MAPPING:
                        direction = KEY_MAPPING[event.key]
                        closest_note = None
                        closest_distance = float('inf')
                        for note in notes:
                            if note.direction == direction:
                                dist = abs(note.y - RECEPTOR_Y)
                                if dist < closest_distance and dist <= HIT_WINDOWS['trash']:
                                    closest_note = note
                                    closest_distance = dist

                        if closest_note:
                            judgment = get_judgment(closest_distance)
                            hit_counts[judgment] += 1

                            # Display hit text and count
                            if judgment == hit_display_text:
                                hit_display_count += 1
                            else:
                                hit_display_text = judgment
                                hit_display_count = 1
                            hit_display_timer = 30  # frames
                            if judgment == 'sick':
                                score += int(300 * multiplier)
                                combo += 1
                            elif judgment == 'good':
                                score += int(200 * multiplier)
                                combo += 1
                            elif judgment == 'bad':
                                score += int(100 * multiplier)
                                combo = 0
                            elif judgment == 'trash':
                                score += int(50 * multiplier)
                                combo = 0

                            if combo > max_combo:
                                max_combo = combo
                            multiplier = update_multiplier(combo)
                            health = min(HEALTH_MAX, health + 1)
                            notes.remove(closest_note)
                        else:
                            # Missed key press
                            hit_counts['miss'] += 1
                            combo = 0
                            health -= 10

                elif game_state == 'results':
                    if event.key == pygame.K_RETURN:
                        # Back to song selection menu
                        selected_json_file = song_selection_menu(screen, font, big_font, json_files, song_titles)
                        with open(selected_json_file, 'r') as f:
                            song_data = json.load(f)

                        music_sheet_raw = song_data.get('musicSheet', [])
                        song_path = song_data.get('song', None)
                        bpm = song_data.get('bpm', 120)
                        note_speed = song_data.get('noteSpeed', 15)

                        beat_interval_ms = 60000 / bpm
                        music_sheet.clear()
                        for i, line in enumerate(music_sheet_raw):
                            music_sheet.append({"time": int(i * beat_interval_ms), "line": line})

                        speed = note_speed

                        reset_rhythm_state()
                    elif event.key == pygame.K_ESCAPE:
                        running = False

        if game_state == 'playing' and not paused:
            now = pygame.time.get_ticks() - song_start_time
            # Spawn notes whose time has come
            while next_note_index < len(music_sheet) and music_sheet[next_note_index]['time'] <= now:
                spawn_note_from_line(music_sheet[next_note_index]['line'])
                next_note_index += 1

        # Update notes positions
        if game_state == 'playing' and not paused:
            for note in notes[:]:
                note.update(speed)
                if note.y > SCREEN_HEIGHT + 50:
                    notes.remove(note)
                    hit_counts['miss'] += 1
                    combo = 0
                    health -= 10

        # Check lose condition
        if health <= 0 and game_state == 'playing':
            game_state = 'results'
            pygame.mixer.music.stop()

        # Check end of song condition
        if game_state == 'playing':
            music_finished = not pygame.mixer.music.get_busy()
            no_notes_left = (next_note_index >= len(music_sheet) and not notes)
            if music_finished and no_notes_left:
                game_state = 'results'
                pygame.mixer.music.stop()

        # Drawing
        screen.fill((0, 0, 0))

        if game_state == 'menu':
            draw_text_centered(screen, "Pysu!Mania", big_font, (255, 255, 255), SCREEN_HEIGHT // 3)
            draw_text_centered(screen, "Press ENTER to Start", font, (255, 255, 0), SCREEN_HEIGHT // 2)
            draw_text_centered(screen, f"Selected Song: {get_song_title(selected_json_file)}", font, (255, 255, 255), SCREEN_HEIGHT // 2 + 50)

        elif game_state == 'playing':
            # Fire effect background if combo high enough
            if fire_active:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                color = fire_colors[fire_anim_frame]
                alpha = 60 + (fire_anim_frame * 20)
                overlay.fill((*color, alpha))
                screen.blit(overlay, (0, 0))

            # Draw receptors
            for direction in DIRECTIONS:
                receptor_img = receptors[direction]
                x = COLUMN_X[direction] - receptor_img.get_width() // 2
                y = RECEPTOR_Y - receptor_img.get_height() // 2
                screen.blit(receptor_img, (x, y))

            # Draw notes
            for note in notes:
                note.draw(screen)

            # Draw combo
            combo_color = (255, 255, 255)
            combo_scale = 1.0
            if fire_active:
                combo_color = fire_colors[fire_anim_frame]
                combo_scale = 1.2 + 0.1 * (fire_anim_frame % 2)
            combo_text_surface = font.render(f"Combo: {combo}", True, combo_color)
            if fire_active:
                glow = pygame.Surface((combo_text_surface.get_width()+8, combo_text_surface.get_height()+8), pygame.SRCALPHA)
                pygame.draw.ellipse(glow, (*combo_color, min(180, fire_text_glow)), glow.get_rect())
                screen.blit(glow, (6, 36))
            combo_rect = combo_text_surface.get_rect()
            combo_rect.topleft = (10, 40)
            if combo_scale != 1.0:
                combo_text_surface = pygame.transform.smoothscale(combo_text_surface, (int(combo_rect.width*combo_scale), int(combo_rect.height*combo_scale)))
            screen.blit(combo_text_surface, combo_rect.topleft)

            # Draw health bar
            health_bar_width = 400
            health_bar_height = 25
            health_ratio = health / HEALTH_MAX
            pygame.draw.rect(screen, (150, 0, 0), (SCREEN_WIDTH - health_bar_width - 20, 20, health_bar_width, health_bar_height))
            pygame.draw.rect(screen, (0, 200, 0), (SCREEN_WIDTH - health_bar_width - 20, 20, int(health_bar_width * health_ratio), health_bar_height))

            # Draw score and multiplier
            score_text = font.render(f"Score: {score}", True, (255, 255, 255))
            multiplier_text = font.render(f"Multiplier: x{multiplier:.1f}", True, (255, 255, 255))
            screen.blit(score_text, (10, 10))
            screen.blit(multiplier_text, (10, 70))

            # Fire label
            if fire_active:
                fire_label = big_font.render("FIRE!", True, fire_colors[fire_anim_frame])
                fire_label.set_alpha(200)
                fx = (SCREEN_WIDTH - fire_label.get_width()) // 2
                fy = 120
                screen.blit(fire_label, (fx, fy))

            # Pause hint
            pause_hint = font.render("Press ESC to Pause/Resume", True, (180, 180, 180))
            screen.blit(pause_hint, (SCREEN_WIDTH - pause_hint.get_width() - 20, SCREEN_HEIGHT - 40))

            # Hit display text
            if hit_display_timer > 0 and hit_display_text:
                display_text = hit_display_text.upper()
                if hit_display_count > 1:
                    display_text += f" x{hit_display_count}"
                hit_text = big_font.render(display_text, True, (255, 255, 255))
                hit_text.set_alpha(hit_display_alpha)
                hit_x = min(COLUMN_X.values()) - 180
                hit_y = RECEPTOR_Y - 50
                screen.blit(hit_text, (hit_x, hit_y))

                fade_duration = 7  # frames to fade
                if hit_display_timer > 30 - fade_duration:
                    hit_display_alpha = int(255 * (1 - (hit_display_timer - (30 - fade_duration)) / fade_duration))
                elif hit_display_timer < fade_duration:
                    hit_display_alpha = int(255 * (hit_display_timer / fade_duration))
                else:
                    hit_display_alpha = 255
                hit_display_timer -= 1
            else:
                hit_display_text = ""
                hit_display_count = 0
                hit_display_alpha = 0

            # Progress bar (optional)
            if pygame.mixer.music.get_busy():
                pos = pygame.mixer.music.get_pos() / 1000.0
                max_length = 120  # Max length of song in seconds (estimate)
                progress_ratio = min(pos / max_length, 1.0)
                bar_width = 400
                bar_height = 15
                x = (SCREEN_WIDTH - bar_width) // 2
                y = 10
                pygame.draw.rect(screen, (100, 100, 100), (x, y, bar_width, bar_height))
                pygame.draw.rect(screen, (50, 200, 50), (x, y, int(bar_width * progress_ratio), bar_height))

        elif game_state == 'results':
            draw_text_centered(screen, "Results", big_font, (255, 255, 255), SCREEN_HEIGHT // 4)
            acc = 0
            total_hits = sum(hit_counts[k] for k in ['sick', 'good', 'bad', 'trash'])
            if total_hits > 0:
                acc = (hit_counts['sick'] + 0.7 * hit_counts['good'] + 0.4 * hit_counts['bad'] + 0.1 * hit_counts['trash']) / total_hits * 100
            score_text = font.render(f"Score: {score}", True, (255, 255, 255))
            combo_text = font.render(f"Max Combo: {max_combo}", True, (255, 255, 255))
            acc_text = font.render(f"Accuracy: {acc:.2f}%", True, (255, 255, 255))
            retry_text = font.render("Press ENTER to return to menu, ESC to quit", True, (180, 180, 180))

            screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, SCREEN_HEIGHT // 2))
            screen.blit(combo_text, (SCREEN_WIDTH // 2 - combo_text.get_width() // 2, SCREEN_HEIGHT // 2 + 40))
            screen.blit(acc_text, (SCREEN_WIDTH // 2 - acc_text.get_width() // 2, SCREEN_HEIGHT // 2 + 80))
            screen.blit(retry_text, (SCREEN_WIDTH // 2 - retry_text.get_width() // 2, SCREEN_HEIGHT - 100))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
