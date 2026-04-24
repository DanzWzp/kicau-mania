import cv2
import numpy as np
import os
import sys

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("[WARNING] pygame tidak ditemukan. Install: pip install pygame")

# Tidak ada spasi — karakter paling gelap tetap terlihat (.)
ASCII_CHARS = ".,;:i1lfLCG08@#"
ASCII_LEN   = len(ASCII_CHARS)

CANVAS_W     = 1280
CANVAS_H     = 720
NEON_GREEN   = (0, 255, 0)
TITLE_COLOR  = (0, 255, 255)   # Kuning neon (BGR)
SHADOW_COLOR = (0, 0, 0)
TITLE_TEXT   = "KICAU MANIA GACOR!!!"
FONT_ASCII   = cv2.FONT_HERSHEY_SIMPLEX
FONT_TITLE   = cv2.FONT_HERSHEY_DUPLEX
FONT_SCALE   = 0.30
FONT_THICK   = 1
TITLE_SCALE  = 1.15
TITLE_THICK  = 3
TITLE_AREA_H = 58

PIP_W     = 320
PIP_H     = 180
PIP_PAD   = 10
PIP_COLOR = (0, 200, 255)
PIP_LABEL = "[ KUCING CAM ]"


# ─── Audio ────────────────────────────────────────────────────────────────────
def init_audio(base_dir):
    if not PYGAME_AVAILABLE:
        return False
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        path = os.path.join(base_dir, "kicau.mp3")
        if not os.path.exists(path):
            print("[WARNING] kicau.mp3 tidak ditemukan")
            return False
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(0.8)
        pygame.mixer.music.play(-1)
        print("[OK] Audio berjalan.")
        return True
    except Exception as e:
        print(f"[WARNING] Audio gagal: {e}")
        return False


def stop_audio(audio_ok):
    if audio_ok and PYGAME_AVAILABLE:
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception:
            pass


# ─── Pre-render bitmap monospace ─────────────────────────────────────────────
def measure_cell():
    """Ukur sel karakter berdasarkan huruf terlebar ('W')."""
    (cw, ch), baseline = cv2.getTextSize("W", FONT_ASCII, FONT_SCALE, FONT_THICK)
    cell_w = cw + 1          # +1 agar ada jarak sedikit
    cell_h = ch + baseline + 1
    return cell_w, cell_h, ch  # ch = ascent (tinggi di atas baseline)


def build_char_table(cell_w, cell_h, ascent):
    """
    Pre-render setiap karakter ASCII ke bitmap (cell_h x cell_w x 3).
    Hasilnya: array (ASCII_LEN, cell_h, cell_w, 3).
    Dipanggil SEKALI di awal — tidak di dalam loop frame.
    """
    table = np.zeros((ASCII_LEN, cell_h, cell_w, 3), dtype=np.uint8)
    pad   = 4
    for i, c in enumerate(ASCII_CHARS):
        bmp = np.zeros((cell_h + pad, cell_w + pad, 3), dtype=np.uint8)
        (gw, _), _ = cv2.getTextSize(c, FONT_ASCII, FONT_SCALE, FONT_THICK)
        x_off = max(0, (cell_w - gw) // 2)   # center horizontal dalam sel
        cv2.putText(bmp, c, (x_off, ascent), FONT_ASCII, FONT_SCALE,
                    NEON_GREEN, FONT_THICK, cv2.LINE_AA)
        table[i] = bmp[:cell_h, :cell_w]
    return table


# ─── Grid ASCII ───────────────────────────────────────────────────────────────
def compute_grid(cell_w, cell_h):
    avail_h  = CANVAS_H - TITLE_AREA_H
    ascii_w  = CANVAS_W  // cell_w
    ascii_h  = avail_h   // cell_h
    # Sisa piksel → dipusatkan
    offset_x = (CANVAS_W - ascii_w * cell_w) // 2
    offset_y = TITLE_AREA_H + (avail_h - ascii_h * cell_h) // 2
    return ascii_w, ascii_h, offset_x, offset_y


# ─── Render ASCII via numpy tiling (tanpa Python loop) ───────────────────────
def render_ascii(indices, char_table, cell_h, cell_w):
    """
    indices: (ascii_h, ascii_w) uint8
    char_table: (ASCII_LEN, cell_h, cell_w, 3) uint8

    Hasilnya: gambar 2D (ascii_h*cell_h, ascii_w*cell_w, 3) — monospace sempurna.
    Teknik: numpy fancy indexing + transpose + reshape, tanpa loop Python.
    """
    ascii_h, ascii_w = indices.shape
    # (ascii_h, ascii_w, cell_h, cell_w, 3)
    tiles = char_table[indices]
    # Transpose ke (ascii_h, cell_h, ascii_w, cell_w, 3) lalu reshape
    section = tiles.transpose(0, 2, 1, 3, 4).reshape(
        ascii_h * cell_h, ascii_w * cell_w, 3
    )
    return section


# ─── Overlay ─────────────────────────────────────────────────────────────────
def draw_title(canvas, tx, ty):
    cv2.putText(canvas, TITLE_TEXT, (tx + 2, ty + 2),
                FONT_TITLE, TITLE_SCALE, SHADOW_COLOR, TITLE_THICK + 2, cv2.LINE_AA)
    cv2.putText(canvas, TITLE_TEXT, (tx, ty),
                FONT_TITLE, TITLE_SCALE, TITLE_COLOR, TITLE_THICK, cv2.LINE_AA)


def draw_pip(canvas, vframe):
    ox = CANVAS_W - PIP_W - PIP_PAD
    oy = CANVAS_H - PIP_H - PIP_PAD
    resized = cv2.resize(vframe, (PIP_W, PIP_H), interpolation=cv2.INTER_LINEAR)
    canvas[oy:oy + PIP_H, ox:ox + PIP_W] = resized
    # Bingkai + label
    cv2.rectangle(canvas, (ox - 2, oy - 22), (ox + PIP_W + 2, oy + PIP_H + 2), PIP_COLOR, 2)
    cv2.putText(canvas, PIP_LABEL, (ox, oy - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, PIP_COLOR, 1, cv2.LINE_AA)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    audio_ok = init_audio(base_dir)

    # Webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Tidak bisa membuka webcam!")
        stop_audio(audio_ok)
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    for _ in range(5):      # flush buffer awal
        cap.read()

    # Video kucing.mp4
    vid      = None
    vid_path = os.path.join(base_dir, "kucing.mp4")
    if os.path.exists(vid_path):
        vid = cv2.VideoCapture(vid_path)
        if vid.isOpened():
            print("[OK] kucing.mp4 dimuat (loop).")
        else:
            vid = None
    else:
        print("[WARNING] kucing.mp4 tidak ditemukan.")

    # Layout & pre-render
    cell_w, cell_h, ascent = measure_cell()
    char_table              = build_char_table(cell_w, cell_h, ascent)
    ascii_w, ascii_h, off_x, off_y = compute_grid(cell_w, cell_h)
    sec_h = ascii_h * cell_h
    sec_w = ascii_w * cell_w

    (tw, th), _ = cv2.getTextSize(TITLE_TEXT, FONT_TITLE, TITLE_SCALE, TITLE_THICK)
    title_x = (CANVAS_W - tw) // 2
    title_y = th + 8

    canvas = np.zeros((CANVAS_H, CANVAS_W, 3), dtype=np.uint8)

    print(f"[INFO] Grid ASCII: {ascii_w}x{ascii_h} karakter, sel: {cell_w}x{cell_h}px")
    print("Tekan 'q' untuk keluar.")

    cv2.namedWindow(TITLE_TEXT, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(TITLE_TEXT, CANVAS_W, CANVAS_H)

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        frame = cv2.flip(frame, 1)   # mirror selfie

        # Resize webcam frame ke ukuran ASCII grid
        small   = cv2.resize(frame, (ascii_w, ascii_h), interpolation=cv2.INTER_LINEAR)
        gray    = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        indices = (gray.astype(np.float32) * ((ASCII_LEN - 1) / 255.0)).astype(np.uint8)

        # Render ASCII (numpy tiling — monospace penuh, tanpa loop)
        section = render_ascii(indices, char_table, cell_h, cell_w)

        # Update canvas
        canvas[:] = 0
        canvas[off_y:off_y + sec_h, off_x:off_x + sec_w] = section

        draw_title(canvas, title_x, title_y)

        # Overlay kucing.mp4
        if vid is not None:
            ret_v, vframe = vid.read()
            if not ret_v:                       # habis → ulangi dari awal
                vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret_v, vframe = vid.read()
            if ret_v:
                draw_pip(canvas, vframe)

        cv2.imshow(TITLE_TEXT, canvas)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    stop_audio(audio_ok)
    if vid is not None:
        vid.release()
    cap.release()
    cv2.destroyAllWindows()
    print("Sampai jumpa dari KICAU MANIA GACOR!!!")


if __name__ == "__main__":
    main()
