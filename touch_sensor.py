import time
import requests
import logging

# Raspberry Pi環境でのみRPi.GPIOをインポート
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("RPi.GPIO is not available. Running in development mode.")
    GPIO = None

# ログ設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# タッチセンサーが接続されているGPIOピン
TOUCH_PIN = 17

# FlaskサーバーのURL
SERVER_URL = "http://localhost:5000/api/touch-detected"

if GPIO:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TOUCH_PIN, GPIO.IN)

def touch_detected():
    logger.info("タッチセンサーが触れられました。サーバーに通知します。")
    try:
        response = requests.post(SERVER_URL)
        if response.status_code == 200:
            logger.info("サーバーに正常に通知しました。")
        else:
            logger.error(f"サーバーへの通知に失敗しました。ステータスコード: {response.status_code}")
    except Exception as e:
        logger.error(f"サーバーへの通知中にエラーが発生しました: {str(e)}")

if GPIO:
    GPIO.add_event_detect(TOUCH_PIN, GPIO.RISING, callback=lambda x: touch_detected(), bouncetime=300)

try:
    logger.info("タッチセンサーの入力待機中...")
    while True:
        if not GPIO:
            # 開発環境でのテスト用
            user_input = input("タッチセンサーをシミュレートするには Enter キーを押してください（終了するには 'q' を入力）: ")
            if user_input.lower() == 'q':
                break
            touch_detected()
        time.sleep(0.1)
except KeyboardInterrupt:
    logger.info("プログラムを終了します。")
finally:
    if GPIO:
        GPIO.cleanup()

