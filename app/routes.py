from flask import Blueprint, render_template, jsonify, request, send_file, Response, stream_with_context
from datetime import datetime, timedelta
import pytz
import speech_recognition as sr
import tempfile
import os
import logging
import subprocess
import shutil
import requests
from config import Config
from gtts import gTTS
import io
import base64
from werkzeug.utils import secure_filename
import nagisa
import threading
import time
import random

# Raspberry Pi環境でのみRPi.GPIOをインポート
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("RPi.GPIO is not available. Running in development mode.")
    GPIO = None

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

# 認識したテキストを保存するグローバル変数
Text_Data = ""

# タッチセンサーが接続されているGPIOピン
TOUCH_PIN = 17

# タッチセンサーの状態を保持するグローバル変数
touch_detected = False

if GPIO:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def touch_callback(channel):
    global touch_detected
    touch_detected = True
    logger.info("タッチセンサーが検出されました")

if GPIO:
    try:
        GPIO.add_event_detect(TOUCH_PIN, GPIO.RISING, callback=touch_callback, bouncetime=300)
    except RuntimeError as e:
        logger.error(f"GPIOの設定中にエラーが発生しました: {str(e)}")

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/api/time')
def get_time():
    japan_tz = pytz.timezone('Asia/Tokyo')
    japan_time = datetime.now(japan_tz)
    return jsonify({'time': japan_time.strftime('%H:%M:%S')})

@bp.route('/events')
def sse():
    def event_stream():
        global touch_detected
        while True:
            if check_for_touch_event():
                yield f"data: touch_detected\n\n"
                touch_detected = False  # イベントを送信したらフラグをリセット
            time.sleep(0.1)  # 100ミリ秒ごとにチェック

    return Response(stream_with_context(event_stream()), content_type='text/event-stream')

def check_for_touch_event():
    global touch_detected
    if GPIO:
        return touch_detected
    else:
        # 開発環境では、ランダムにタッチイベントをシミュレート
        return random.random() < 0.01  # 1%の確率でTrueを返す

@bp.route('/api/touch-detected', methods=['POST'])
def touch_detected_api():
    global touch_detected
    touch_detected = True
    logger.info("タッチセンサーが検出されました (API経由)")
    return jsonify({'message': 'タッチ検出確認'}), 200

# 以下、既存の関数は変更なし

def start_voice_input():
    global Text_Data
    logger.info("音声認識処理を開始")

    try:
        # 音声録音の処理（5秒間録音）
        audio_file = "temp_audio.wav"
        duration = 5  # 録音時間（秒）を5秒に変更
        sample_rate = 44100
        channels = 1

        command = [
            'arecord',
            '-d', str(duration),
            '-f', 'S16_LE',
            '-c', str(channels),
            '-r', str(sample_rate),
            audio_file
        ]
        
        logger.info("音声録音を開始します（5秒間）")
        subprocess.run(command, check=True)
        logger.info("音声録音が完了しました")

        # 音声認識の実行
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_file) as source:
            logger.info("音声データを読み込み中...")
            audio_data = recognizer.record(source)
            logger.info("音声認識を実行中...")
            
            text = recognizer.recognize_google(audio_data, language='ja-JP')
            # 認識したテキストをグローバル変数に保存
            Text_Data = text
            logger.info(f"認識結果を保存: {Text_Data}")

            return jsonify({'text': text, 'success': True})

    except Exception as e:
        logger.error(f"音声認識エラー: {str(e)}")
        return jsonify({'error': str(e), 'success': False})
    finally:
        # 一時ファイルの削除
        if os.path.exists(audio_file):
            os.remove(audio_file)

@bp.route('/api/start-voice-input', methods=['POST'])
def api_start_voice_input():
    logger.info("api_start_voice_input関数が呼び出されました")
    return start_voice_input()

@bp.route('/api/speech-to-text', methods=['POST'])
def speech_to_text():
    global Text_Data
    logger.info("音声認識処理を開始")

    if 'audio' not in request.files:
        logger.error("音声ファイルが見つかりません")
        return jsonify({'error': '音声ファイルが見つかりません'}), 400

    audio_file = request.files['audio']
    if not audio_file.filename:
        logger.error("ファイル名が空です")
        return jsonify({'error': '無効な音声ファイルです'}), 400

    filename = secure_filename(audio_file.filename)
    file_path = os.path.join(tempfile.gettempdir(), filename)
    audio_file.save(file_path)

    try:
        # WebMファイルをWAVに変換
        wav_path = os.path.join(tempfile.gettempdir(), "converted.wav")
        command = [
            'ffmpeg',
            '-i', file_path,
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            wav_path
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg変換エラー: {result.stderr}")
            return jsonify({'error': 'FFmpeg変換エラー'}), 500

        # 音声認識の実行
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            logger.info("音声データを読み込み中...")
            audio_data = recognizer.record(source)
            logger.info("音声認識を実行中...")
            
            text = recognizer.recognize_google(audio_data, language='ja-JP')
            # 認識したテキストをグローバル変数に保存
            Text_Data = text
            logger.info(f"認識結果を保存: {Text_Data}")
            
            return jsonify({
                'text': text,
                'stored': True  # テキストが保存されたことを示すフラグ
            })

    except sr.UnknownValueError as e:
        logger.error(f"音声認識エラー: {str(e)}")
        return jsonify({'error': '音声を認識できませんでした'}), 400
    except sr.RequestError as e:
        logger.error(f"音声認識サービスエラー: {str(e)}")
        return jsonify({'error': '音声認識サービスに接続できませんでした'}), 500
    except Exception as e:
        logger.error(f"予期せぬエラー: {str(e)}")
        return jsonify({'error': f'予期せぬエラーが発生しました: {str(e)}'}), 500
    finally:
        # 一時ファイルの削除
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(wav_path):
                os.remove(wav_path)
        except Exception as e:
            logger.error(f"一時ファイルの削除中にエラー: {str(e)}")

@bp.route('/api/get-text', methods=['GET'])
def get_text():
    global Text_Data
    return jsonify({'text': Text_Data})

def is_positive_news(title, description):
    # ポジティブな単語のリスト
    positive_words = ['成功', '進展', '改善', '回復', '成長', '発展', '好調', '前進', '達成', '解決']
    
    # タイトルと概要を結合してテキストを作成
    text = title + ' ' + description
    
    # nagisaを使用してテキストを形態素解析
    words = nagisa.tagging(text)
    
    # ポジティブな単語の出現回数をカウント
    positive_count = sum(1 for word in words.words if word in positive_words)
    
    # ポジティブな単語が1つ以上含まれていればTrue、そうでなければFalse
    return positive_count > 0

@bp.route('/api/get-news', methods=['GET'])
def get_news():
    global Text_Data
    logger.info(f"ニュース取得開始: 検索ワード '{Text_Data}'")

    api_key = Config.NEWS_API_KEY
    if not api_key:
        logger.error("NewsAPI keyが設定されていません")
        return jsonify({'error': 'NewsAPI keyが設定されていません'}), 500

    url = 'https://newsapi.org/v2/everything'
    
    params = {
        'q': Text_Data or '日本',  # 検索ワードが空の場合は'日本'をデフォルトとする
        'sortBy': 'publishedAt',  # 公開日時で並び替え
        'apiKey': api_key,
        'domains': 'asahi.com',  # 朝日新聞のドメインを指定
        'pageSize': 20  # 20件を取得（フィルタリング前）
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        news_data = response.json()

        if news_data['status'] == 'ok':
            articles = news_data['articles']
            filtered_articles = filter_asahi_articles(articles)
            positive_articles = [
                article for article in filtered_articles
                if is_positive_news(article['title'], article['description'])
            ]
            formatted_articles = format_articles(positive_articles[:3])  # 最大3件に制限
            
            logger.info(f"{len(formatted_articles)}件のポジティブな朝日新聞記事を取得しました")

            # 音声データの生成
            titles = [article['title'] for article in formatted_articles]
            audio_data = generate_audio(titles)

            return jsonify({
                'articles': formatted_articles,
                'audio': audio_data
            })
        else:
            logger.error(f"NewsAPI エラー: {news_data['message']}")
            return jsonify({'error': 'ニュースの取得に失敗しました'}), 500

    except requests.RequestException as e:
        logger.error(f"NewsAPI リクエストエラー: {str(e)}")
        return jsonify({'error': 'ニュースの取得中にエラーが発生しました'}), 500

def filter_asahi_articles(articles):
    # 朝日新聞の記事のみをフィルタリング
    return [article for article in articles if 'asahi.com' in article.get('url', '')]

def format_articles(articles):
    return [{
        'title': article['title'],
        'description': article['description'],
        'url': article['url'],
        'publishedAt': article['publishedAt']
    } for article in articles]

def generate_audio(titles):
    try:
        if not titles:
            text = "ポジティブなニュースはありませんでした。"
        else:
            # 最大3つのタイトルを使用
            titles = titles[:3]
            # タイトルを結合して1つの文章にする
            text = "以下のポジティブなニュースをお伝えします。" + "。次に、".join(titles) + "。以上です。"
        
        # 音声ファイルを生成
        tts = gTTS(text=text, lang='ja')
        
        # 音声をバイトストリームとして保存
        audio_stream = io.BytesIO()
        tts.write_to_fp(audio_stream)
        audio_stream.seek(0)
        
        # 音声データをBase64エンコード
        audio_base64 = base64.b64encode(audio_stream.getvalue()).decode('utf-8')
        
        return audio_base64
    
    except Exception as e:
        logger.error(f"音声合成エラー: {str(e)}")
        return None

