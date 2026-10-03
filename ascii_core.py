"""Ядро конвертера: кадр (BGR, numpy) -> ASCII в виде текста или картинки."""
import os
import shutil
import subprocess
import tempfile
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

# Символы от самого "пустого" к самому "плотному"
RAMPS = {
    "Классический": " .:-=+*#%@",
    "Подробный": ' .\'`^",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$',
    "Блоки": " ░▒▓█",
    "Простой": " .+#",
    "Двоичный": " 01",
}

_FONTS = [
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
]
_cache = {}


class Atlas:
    """Заранее отрисованные символы набора: быстрая сборка кадра через numpy."""

    def __init__(self, ramp, size):
        self.ramp = ramp
        font = None
        for p in _FONTS:
            if os.path.exists(p):
                try:
                    font = ImageFont.truetype(p, size)
                    break
                except Exception:
                    pass
        if font is None:
            font = ImageFont.load_default()
        try:
            self.cw = max(1, int(round(font.getlength("M"))))
        except AttributeError:
            self.cw = max(1, font.getsize("M")[0])
        try:
            asc, desc = font.getmetrics()
            self.ch = max(1, asc + desc)
        except AttributeError:
            self.ch = max(1, int(self.cw * 2))
        masks = []
        for c in ramp:
            im = Image.new("L", (self.cw, self.ch), 0)
            ImageDraw.Draw(im).text((0, 0), c, font=font, fill=255)
            masks.append(np.asarray(im))
        self.masks = np.stack(masks)


def get_atlas(ramp, size):
    key = (ramp, size)
    if key not in _cache:
        if len(_cache) > 8:
            _cache.clear()
        _cache[key] = Atlas(ramp, size)
    return _cache[key]


def grid(bgr, s, atlas):
    """Возвращает (индексы символов [rows, cols], уменьшенный кадр BGR)."""
    h, w = bgr.shape[:2]
    cols = s["cols"]
    rows = max(1, int(round(cols * h / w * atlas.cw / atlas.ch)))
    small = cv2.resize(bgr, (cols, rows), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    gray = np.clip((gray - 0.5) * s["contrast"] + 0.5, 0.0, 1.0)
    # На тёмном фоне "чернила" светлые: яркие пиксели = плотные символы.
    dense_bright = (not s["light_bg"]) != s["invert"]
    n = len(atlas.ramp) - 1
    idx = np.rint((gray if dense_bright else 1.0 - gray) * n).astype(np.intp)
    return idx, small


def to_text(idx, ramp):
    return "\n".join("".join(ramp[i] for i in row) for row in idx.tolist())


def to_image(idx, small, s, atlas):
    rows, cols = idx.shape
    glyph = atlas.masks[idx]  # rows, cols, ch, cw
    a = glyph.transpose(0, 2, 1, 3).reshape(rows * atlas.ch, cols * atlas.cw)
    a = a.astype(np.float32)[..., None] / 255.0
    light = s["light_bg"]
    bg = np.array([244, 242, 236] if light else [0, 0, 0], np.float32)
    if s["color"]:
        rgb = small[:, :, ::-1].astype(np.float32)
        fg = np.repeat(np.repeat(rgb, atlas.ch, axis=0), atlas.cw, axis=1)
    else:
        fg = np.array([25, 25, 25] if light else [235, 235, 235], np.float32)
    out = bg + (fg - bg) * a
    return Image.fromarray(out.astype(np.uint8))


def render(bgr, s):
    atlas = get_atlas(s["ramp"], s["font"])
    idx, small = grid(bgr, s, atlas)
    return to_image(idx, small, s, atlas)


def render_text(bgr, s):
    atlas = get_atlas(s["ramp"], s["font"])
    idx, _ = grid(bgr, s, atlas)
    return to_text(idx, s["ramp"])


def find_ffmpeg():
    """ffmpeg из пакета imageio-ffmpeg (вшит в .exe) или из PATH."""
    try:
        import imageio_ffmpeg
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if p and os.path.exists(p):
            return p
    except Exception:
        pass
    return shutil.which("ffmpeg")


def export_video(src, out, s, progress=None):
    """Сохраняет видео в ASCII (mp4/avi со звуком оригинала или gif). Возвращает сообщение."""
    cap = writer = None
    tmp = None
    try:
        cap = cv2.VideoCapture(src)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        atlas = get_atlas(s["ramp"], s["font"])
        ext = os.path.splitext(out)[1].lower()
        ff = find_ffmpeg() if ext in (".mp4", ".avi") else None
        target = out
        if ff:
            fd, tmp = tempfile.mkstemp(suffix=ext)
            os.close(fd)
            target = tmp
        gif_frames, step = [], max(1, round(fps / 15))
        i = 0
        while True:
            ok, f = cap.read()
            if not ok:
                break
            if ext == ".gif":
                if i % step == 0:
                    idx, small = grid(f, s, atlas)
                    im = to_image(idx, small, s, atlas)
                    gif_frames.append(im.convert("P", palette=Image.ADAPTIVE))
            else:
                idx, small = grid(f, s, atlas)
                arr = np.asarray(to_image(idx, small, s, atlas))
                H, W = arr.shape[0] // 2 * 2, arr.shape[1] // 2 * 2
                if writer is None:
                    code = "mp4v" if ext == ".mp4" else "XVID"
                    writer = cv2.VideoWriter(target, cv2.VideoWriter_fourcc(*code), fps, (W, H))
                    if not writer.isOpened():
                        raise RuntimeError("Не удалось создать видеофайл.")
                writer.write(np.ascontiguousarray(arr[:H, :W, ::-1]))
            i += 1
            if progress:
                progress(min(1.0, i / total))
        if writer:
            writer.release()
            writer = None
        if ext == ".gif":
            if not gif_frames:
                raise RuntimeError("В видео нет кадров.")
            gif_frames[0].save(out, save_all=True, append_images=gif_frames[1:],
                               duration=int(1000 * step / fps), loop=0)
            return f"Готово: {out} (GIF не поддерживает звук)"
        if not ff:
            return f"Готово без звука (ffmpeg не найден): {out}"
        cmd = [ff, "-y", "-i", tmp, "-i", src, "-map", "0:v:0", "-map", "1:a:0?",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
               "-c:a", "aac", "-b:a", "192k", "-shortest", out]
        flags = 0x08000000 if os.name == "nt" else 0
        r = subprocess.run(cmd, capture_output=True, creationflags=flags)
        if r.returncode != 0:
            shutil.copyfile(tmp, out)
            return f"Готово, но звук добавить не удалось: {out}"
        return f"Готово со звуком: {out}"
    finally:
        if writer:
            writer.release()
        if cap:
            cap.release()
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
