import streamlit as st
import cv2
import numpy as np
import os
import base64
import av
from streamlit_webrtc import webrtc_streamer
import streamlit.components.v1 as components

ASCII_CHARS = ".,;:i1lfLCG08@#"
ASCII_LEN = len(ASCII_CHARS)
PIP_W, PIP_H = 160, 90

@st.cache_data
def get_char_table():
    cell_w, cell_h = 8, 12
    table = np.zeros((ASCII_LEN, cell_h, cell_w, 3), dtype=np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    for i, c in enumerate(ASCII_CHARS):
        bmp = np.zeros((cell_h, cell_w, 3), dtype=np.uint8)
        cv2.putText(bmp, c, (0, 10), font, 0.3, (0, 255, 0), 1, cv2.LINE_AA)
        table[i] = bmp
    return table, cell_w, cell_h

class VideoProcessor:
    def __init__(self):
        self.char_table, self.cell_w, self.cell_h = get_char_table()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.vid_path = os.path.join(base_dir, "kucing.mp4")
        self.vid = cv2.VideoCapture(self.vid_path) if os.path.exists(self.vid_path) else None

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        h, w = img.shape[:2]

        ascii_w = w // self.cell_w
        ascii_h = h // self.cell_h

        small = cv2.resize(img, (ascii_w, ascii_h), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        indices = (gray.astype(np.float32) * ((ASCII_LEN - 1) / 255.0)).astype(np.uint8)

        tiles = self.char_table[indices]
        section = tiles.transpose(0, 2, 1, 3, 4).reshape(
            ascii_h * self.cell_h, ascii_w * self.cell_w, 3
        )

        canvas = np.zeros_like(img)
        canvas[0:section.shape[0], 0:section.shape[1]] = section

        cv2.putText(canvas, "KICAU MANIA GACOR!!!", (20, 40),
                    cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 255), 2, cv2.LINE_AA)

        if self.vid is not None:
            ret, vframe = self.vid.read()
            if not ret:
                self.vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, vframe = self.vid.read()

            if ret:
                resized_cat = cv2.resize(vframe, (PIP_W, PIP_H))
                oy, ox = h - PIP_H - 10, w - PIP_W - 10
                canvas[oy:oy+PIP_H, ox:ox+PIP_W] = resized_cat
                cv2.rectangle(canvas, (ox, oy), (ox+PIP_W, oy+PIP_H), (0, 200, 255), 2)
                cv2.putText(canvas, "[ KUCING CAM ]", (ox, oy - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1)

        return av.VideoFrame.from_ndarray(canvas, format="bgr24")

st.set_page_config(page_title="Kicau Mania", page_icon="🐦", layout="centered")

st.title("🐦 Kamera Kicau Mania Gacor")
st.markdown("Nyalakan kamera di bawah untuk melihat efek ASCII. Pastikan browser kamu memberikan izin akses kamera.")

def play_background_audio():
    audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kicau.mp3")
    if os.path.exists(audio_path):
        with open(audio_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            html_code = f"""
            <div style="display: flex; justify-content: center; align-items: center; flex-direction: column;">
                <audio id="suara-burung" loop>
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mpeg">
                </audio>
                <button onclick="document.getElementById('suara-burung').play()" 
                        style="padding: 12px 20px; background-color: #00CC66; color: white; 
                               border: none; border-radius: 8px; font-size: 16px; cursor: pointer;
                               font-family: sans-serif; font-weight: bold; width: 100%;">
                    🔊 KLIK DI SINI UNTUK MENYALAKAN SUARA 🔊
                </button>
                <span style="font-family: sans-serif; font-size: 12px; color: #888; margin-top: 8px;">
                    *Aturan Browser: Suara tidak bisa berputar otomatis tanpa diklik
                </span>
            </div>
            """
            components.html(html_code, height=100)

play_background_audio()

webrtc_streamer(
    key="kicau-cam",
    video_processor_factory=VideoProcessor,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)