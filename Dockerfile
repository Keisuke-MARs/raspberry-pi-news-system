FROM python:3.9-slim-buster

WORKDIR /app

# システムパッケージのインストール（FFmpeg、MeCab、FLACを含む）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    python3-pyaudio \
    ffmpeg \
    mecab \
    libmecab-dev \
    mecab-ipadic-utf8 \
    flac \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコピー
COPY . .

# FFmpegとFLACの存在確認
RUN ffmpeg -version && flac --version

# アプリケーションの実行
CMD ["python", "run.py"]

