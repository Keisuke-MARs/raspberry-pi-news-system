FROM python:3.9-slim-buster

# 環境変数の設定
ENV DEBIAN_FRONTEND=noninteractive

# apt-utils と必要なパッケージをインストール
RUN apt-get update && apt-get install -y apt-utils dialog

# システムパッケージのインストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    python3-pyaudio \
    ffmpeg \
    alsa-utils \
    libasound2 \
    libasound2-plugins \
    pulseaudio \
    flac \
    python3-rpi.gpio \
    libsndfile1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

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

# pydubのインストール
RUN pip install pydub

# アプリケーションのコピー
COPY . .

# オーディオグループの確認と追加（存在しない場合のみ）
RUN getent group audio || groupadd -g 29 audio
RUN usermod -a -G audio root

# PulseAudioの設定
RUN mkdir -p /root/.config/pulse
RUN echo "default-server = unix:/run/user/1000/pulse/native" > /root/.config/pulse/client.conf

# 一時ファイル用ディレクトリの作成と権限設定
RUN mkdir -p /tmp/audio && chmod 777 /tmp/audio

# FFmpegとFLACの存在確認
RUN ffmpeg -version && flac --version

# オーディオデバイスの確認とテスト
RUN arecord -l || true

# アプリケーションの実行
CMD ["python", "run.py"]

