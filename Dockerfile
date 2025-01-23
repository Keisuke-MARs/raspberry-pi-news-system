FROM python:3.9-slim-buster

WORKDIR /app

# システムパッケージのインストール（apt-utilsを追加）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    apt-utils \
    build-essential \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    python3-pyaudio \
    ffmpeg \
    alsa-utils \
    flac \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ファイル記述子の制限を増やす
RUN ulimit -n 65536

# 仮想環境の作成と有効化
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# pipとwheelの更新
RUN pip install --upgrade pip wheel setuptools

# Raspberry Pi環境でのみRPi.GPIOをインストール
RUN if [ "$(uname -m)" = "armv7l" ]; then \
    pip install RPi.GPIO==0.7.0; \
    fi

# Pythonパッケージのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコピー
COPY . .

# FFmpegとFLACの存在確認
RUN ffmpeg -version && flac --version

# アプリケーションの実行
CMD ["python", "run.py"]

