# ASCII Converter

Converter for photos and videos to ASCII art. Save the result as an image, a text file, a video (with the original sound) or a GIF.

| Version      | Source                                  | Build script | Output                     |
| ------------ | --------------------------------------- | ------------ | -------------------------- |
| GUI (window) | `ascii_converter.py`, `ascii_core.py`   | `build.bat`  | `dist\ASCII-Converter.exe` |

The resulting `.exe` is fully standalone: ffmpeg is bundled inside, and the person running it does not need Python.

## Features

- Open photos (PNG, JPG, BMP, WebP, GIF) and videos (MP4, AVI, MOV, MKV, WebM)
- Live preview, video playback with pause
- Width, symbol size, contrast, 5 character sets, invert, color mode, light background
- Save a photo or a video frame as PNG, JPG, BMP or WebP
- Save as a text file (`.txt`)
- Save a video as MP4 or AVI **with the original sound**, or as GIF (GIF has no sound)

## Requirements

- Windows 10 or 11 (64-bit)
- Python 3.9 or newer
- An internet connection (only during the build, to download the libraries)

## Step 1. Install Python

1. Download Python from <https://www.python.org/downloads/>.
2. Run the installer and **tick "Add python.exe to PATH"** on the first screen.
3. Click "Install Now".
4. Verify: open Command Prompt and run `python --version`. You should see a version number.

## Step 2. Prepare the folder

Put these files together in one folder, for example `C:\ASCII-Converter`:

```
C:\ASCII-Converter\
    ascii_converter.py
    ascii_core.py
    requirements.txt
    build.bat
```

ffmpeg is not needed here: it comes with the `imageio-ffmpeg` package and is downloaded during the build.

## Step 3. Build

Double-click `build.bat`.

The script installs the libraries and PyInstaller, then packages the program. This takes a few minutes. The window stays open at the end so you can read the result.

When it finishes, your file is here:

```
C:\ASCII-Converter\dist\ASCII-Converter.exe
```

Copy it anywhere you like. You can delete the `build`, `dist` and `.spec` leftovers afterwards.

## Run without building

```
python -m pip install -r requirements.txt
python ascii_converter.py
```

## Manual build (without the .bat file)

Open Command Prompt in the project folder and run:

```
python -m pip install --upgrade -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --collect-all imageio_ffmpeg --name ASCII-Converter ascii_converter.py
```

Use `--console` instead of `--windowed` if you want to see error messages.

## Troubleshooting

| Message                          | Fix                                                                                                                   |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `Python not found`               | Reinstall Python and tick "Add python.exe to PATH", or try `py -3` instead of `python`.                               |
| `Could not install dependencies` | Check your internet connection, proxy or VPN.                                                                         |
| Antivirus flags the .exe         | This is a common false positive for PyInstaller programs. Add an exception, or build it yourself and keep the source. |
| The .exe does not start          | Rebuild with `--console` instead of `--windowed` to see error messages in a console.                                  |
| Window closes instantly          | Open Command Prompt in the folder and run `build.bat` from there to see the output.                                   |
| Video has no sound               | Make sure you save as MP4 or AVI, not GIF. Check that the source video has an audio track.                            |
| Export is slow                   | Lower the width or the symbol size. Each video frame is rendered as a full image.                                     |
