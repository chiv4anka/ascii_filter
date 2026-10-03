"""ASCII Converter: фото и видео -> ASCII, с сохранением в PNG/JPG/TXT/MP4/AVI/GIF."""
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

import ascii_core as core

IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff", ".gif"}
VID_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".wmv", ".m4v"}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ASCII Converter")
        self.geometry("1150x720")
        self.minsize(820, 540)
        self.path = None
        self.kind = None
        self.cap = None
        self.frame = None
        self.playing = False
        self.fps = 25.0
        self.photo = None
        self._job = None
        self.busy = False
        self.q = queue.Queue()
        self._build_ui()
        self.after(100, self.poll)

    # ---------- интерфейс ----------
    def _scale(self, parent, text, lo, hi, val, dec=0):
        var = tk.DoubleVar(value=val)
        lab = ttk.Label(parent, text=f"{text}: {val:g}")
        lab.pack(anchor="w", pady=(8, 0))

        def on(v):
            x = round(float(v), dec) if dec else int(float(v))
            lab.config(text=f"{text}: {x:g}")
            self.refresh()

        ttk.Scale(parent, from_=lo, to=hi, variable=var, command=on).pack(fill="x")
        return var

    def _build_ui(self):
        side = ttk.Frame(self, padding=10)
        side.pack(side="left", fill="y")
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(side="right", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.show())

        ttk.Button(side, text="Открыть фото или видео…", command=self.open).pack(fill="x")
        self.info = ttk.Label(side, text="Файл не выбран", wraplength=240)
        self.info.pack(anchor="w", pady=(6, 0))

        self.cols = self._scale(side, "Ширина, символов", 20, 300, 100)
        self.fsize = self._scale(side, "Размер символа, px", 6, 28, 12)
        self.contrast = self._scale(side, "Контраст", 0.5, 3.0, 1.2, dec=1)

        ttk.Label(side, text="Набор символов").pack(anchor="w", pady=(8, 0))
        self.ramp = ttk.Combobox(side, values=list(core.RAMPS), state="readonly")
        self.ramp.current(0)
        self.ramp.pack(fill="x")
        self.ramp.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        self.invert = tk.BooleanVar()
        self.color = tk.BooleanVar()
        self.light = tk.BooleanVar()
        for text, var in (("Инвертировать", self.invert), ("Цветной режим", self.color), ("Светлый фон", self.light)):
            ttk.Checkbutton(side, text=text, variable=var, command=self.refresh).pack(anchor="w", pady=(6, 0))

        self.play_btn = ttk.Button(side, text="Пауза", command=self.toggle_play, state="disabled")
        self.play_btn.pack(fill="x", pady=(12, 0))

        ttk.Separator(side).pack(fill="x", pady=12)
        ttk.Button(side, text="Сохранить кадр как фото…", command=self.save_image).pack(fill="x")
        ttk.Button(side, text="Сохранить как текст (.txt)…", command=self.save_text).pack(fill="x", pady=(6, 0))
        ttk.Button(side, text="Сохранить видео / GIF…", command=self.save_video).pack(fill="x", pady=(6, 0))

        self.pb = ttk.Progressbar(side, maximum=1.0)
        self.pb.pack(fill="x", pady=(12, 0))
        self.status = ttk.Label(side, text="", wraplength=240)
        self.status.pack(anchor="w", pady=(6, 0))

    def settings(self):
        return dict(
            cols=int(self.cols.get()),
            font=int(self.fsize.get()),
            contrast=round(self.contrast.get(), 1),
            invert=self.invert.get(),
            color=self.color.get(),
            light_bg=self.light.get(),
            ramp=core.RAMPS[self.ramp.get()],
        )

    # ---------- открытие и показ ----------
    def open(self):
        pats = " ".join("*" + e for e in sorted(IMG_EXT | VID_EXT))
        p = filedialog.askopenfilename(filetypes=[("Фото и видео", pats), ("Все файлы", "*.*")])
        if not p:
            return
        self.playing = False
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        if self.cap:
            self.cap.release()
            self.cap = None
        ext = os.path.splitext(p)[1].lower()
        if ext in VID_EXT:
            cap = cv2.VideoCapture(p)
            ok, f = cap.read()
            if not ok:
                messagebox.showerror("Ошибка", "Не удалось открыть видео.")
                return
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            self.fps = fps if 1 <= fps <= 120 else 25.0
            self.cap, self.kind, self.frame, self.path = cap, "video", f, p
            self.play_btn.config(state="normal", text="Пауза")
            self.playing = True
            self.tick()
        else:
            try:
                arr = np.asarray(Image.open(p).convert("RGB"))[:, :, ::-1].copy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть изображение:\n{e}")
                return
            self.kind, self.frame, self.path = "image", arr, p
            self.play_btn.config(state="disabled")
            self.show()
        self.info.config(text=os.path.basename(p))

    def tick(self):
        self._job = None
        if not (self.playing and self.cap):
            return
        t0 = time.time()
        ok, f = self.cap.read()
        if not ok:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, f = self.cap.read()
        if ok:
            self.frame = f
            self.show()
        delay = max(1, int(1000 / self.fps - (time.time() - t0) * 1000))
        self._job = self.after(delay, self.tick)

    def toggle_play(self):
        if self.kind != "video":
            return
        if self.playing:
            self.playing = False
            if self._job:
                self.after_cancel(self._job)
                self._job = None
            self.play_btn.config(text="Продолжить")
        else:
            self.playing = True
            self.play_btn.config(text="Пауза")
            self.tick()

    def refresh(self):
        if self.frame is not None and not self.playing:
            self.show()

    def show(self):
        if self.frame is None:
            return
        img = core.render(self.frame, self.settings())
        w = max(50, self.canvas.winfo_width() - 4)
        h = max(50, self.canvas.winfo_height() - 4)
        sc = min(w / img.width, h / img.height)
        size = (max(1, int(img.width * sc)), max(1, int(img.height * sc)))
        img = img.resize(size, Image.BOX if sc < 1 else Image.NEAREST)
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(w // 2 + 2, h // 2 + 2, image=self.photo)

    # ---------- сохранение ----------
    def save_image(self):
        if self.frame is None:
            messagebox.showinfo("ASCII Converter", "Сначала откройте фото или видео.")
            return
        p = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp"), ("WebP", "*.webp")],
        )
        if not p:
            return
        try:
            core.render(self.frame, self.settings()).save(p, quality=95)
            self.status.config(text=f"Сохранено: {p}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def save_text(self):
        if self.frame is None:
            messagebox.showinfo("ASCII Converter", "Сначала откройте фото или видео.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Текст", "*.txt")])
        if not p:
            return
        with open(p, "w", encoding="utf-8") as f:
            f.write(core.render_text(self.frame, self.settings()))
        self.status.config(text=f"Сохранено: {p}")

    def save_video(self):
        if self.kind != "video":
            messagebox.showinfo("ASCII Converter", "Сначала откройте видео.")
            return
        if self.busy:
            return
        p = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4"), ("AVI", "*.avi"), ("GIF", "*.gif")],
        )
        if not p:
            return
        self.busy = True
        self.pb["value"] = 0
        self.status.config(text="Экспорт…")
        args = (self.path, p, self.settings())
        threading.Thread(target=self._export, args=args, daemon=True).start()

    def _export(self, src, out, s):
        try:
            msg = core.export_video(src, out, s, lambda v: self.q.put(("progress", v)))
            self.q.put(("done", msg))
        except Exception as e:
            self.q.put(("error", str(e)))

    def poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "progress":
                    self.pb["value"] = val
                elif kind == "done":
                    self.busy = False
                    self.pb["value"] = 0
                    self.status.config(text=val)
                elif kind == "error":
                    self.busy = False
                    self.pb["value"] = 0
                    self.status.config(text="Ошибка экспорта")
                    messagebox.showerror("Ошибка", val)
        except queue.Empty:
            pass
        self.after(100, self.poll)


if __name__ == "__main__":
    try:  # чёткий текст на экранах с масштабированием
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()
