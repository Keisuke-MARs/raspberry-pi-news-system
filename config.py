import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
    
    # ネガティブワードのリストを追加
    NEGATIVE_WORDS = [
        '事故', '災害', '犯罪', '死亡', '殺人', '自殺', '詐欺', '失敗', '破産', '倒産',
        '感染', '病気', '疫病', '汚染', '不況', '紛争', '戦争', '暴力', '差別', '争い',
        '貧困', '飢餓', '失業', '倒壊', '崩壊', '破壊', '悪化', '低下', '下落', '減少'
    ]

