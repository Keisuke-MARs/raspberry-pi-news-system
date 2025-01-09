from flask import Blueprint, render_template, jsonify, request, send_file
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

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

# 認識したテキストを保存するグローバル変数
Text_Data = ""

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/api/time')
def get_time():
    japan_tz = pytz.timezone('Asia/Tokyo')
    japan_time = datetime.now(japan_tz)
    return jsonify({'time': japan_time.strftime('%H:%M:%S')})

@bp.route('/api/speech-to-text', methods=['POST'])
def speech_to_text():
    global Text_Data
    logger.info("音声認識処理を開始")

    # FFmpegの存在確認
    ffmpeg_path = shutil.which('ffmpeg')
    if not ffmpeg_path:
        logger.error("FFmpegが見つかりません")
        return jsonify({'error': 'FFmpegが見つかりません'}), 500

    logger.info(f"FFmpegのパス: {ffmpeg_path}")

    if 'audio' not in request.files:
        logger.error("音声ファイルが見つかりません")
        return jsonify({'error': '音声ファイルが見つかりません'}), 400

    audio_file = request.files['audio']
    if not audio_file.filename:
        logger.error("ファイル名が空です")
        return jsonify({'error': '無効な音声ファイルです'}), 400

    webm_path = None
    wav_path = None

    try:
        # WebMファイルの保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as webm_temp:
            webm_path = webm_temp.name
            audio_file.save(webm_path)
            logger.info(f"WebMファイルを保存: {webm_path}")

        # WAVファイルへの変換
        wav_path = webm_path.replace('.webm', '.wav')
        logger.info(f"WAVファイルに変換開始: {wav_path}")

        # FFmpegコマンドの実行
        command = [
            'ffmpeg',
            '-y',
            '-i', webm_path,
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            wav_path
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"FFmpeg変換エラー: {result.stderr}")
            return jsonify({'error': '音声ファイルの変換に失敗しました'}), 500

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
            if webm_path and os.path.exists(webm_path):
                os.remove(webm_path)
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)
        except Exception as e:
            logger.error(f"一時ファイルの削除中にエラー: {str(e)}")

@bp.route('/api/get-text', methods=['GET'])
def get_text():
    global Text_Data
    return jsonify({'text': Text_Data})

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
        # 'language': 'ja',
        # 'sortBy': 'publishedAt',  # 公開日時で並び替え
        'apiKey': api_key,
        'domains': 'asahi.com',  # 朝日新聞のドメインを指定
        'pageSize': 3  # 最新の3件を取得
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        news_data = response.json()

        if news_data['status'] == 'ok':
            articles = news_data['articles']
            filtered_articles = filter_asahi_articles(articles)
            formatted_articles = format_articles(filtered_articles[:3])  # 最新の3件のみを取得
            
            logger.info(f"{len(formatted_articles)}件の朝日新聞記事を取得しました")

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
        # 最大3つのタイトルを使用
        titles = titles[:3]
        
        # タイトルを結合して1つの文章にする
        text = "以下のニュースをお伝えします。" + "。次に、".join(titles) + "。以上です。"
        
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

