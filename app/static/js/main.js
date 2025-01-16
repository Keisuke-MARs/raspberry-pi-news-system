let isRecording = false;
let mediaRecorder;
let audioChunks = [];

function updateClock() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const seconds = now.getSeconds();

    // アナログ時計の針を更新
    updateClockHands(hours, minutes, seconds);

    // デジタル時計の表示を更新
    const digitalTime = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    document.getElementById('digital-time').textContent = `日本時間: ${digitalTime}`;
}

function updateClockHands(hours, minutes, seconds) {
    const hourHand = document.getElementById('hour-hand');
    const minuteHand = document.getElementById('minute-hand');
    const secondHand = document.getElementById('second-hand');

    const hourAngle = (hours % 12 + minutes / 60) * 30;
    const minuteAngle = (minutes + seconds / 60) * 6;
    const secondAngle = seconds * 6;

    hourHand.setAttribute('transform', `rotate(${hourAngle}, 100, 100)`);
    minuteHand.setAttribute('transform', `rotate(${minuteAngle}, 100, 100)`);
    secondHand.setAttribute('transform', `rotate(${secondAngle}, 100, 100)`);
}

function showClockSection() {
    document.getElementById('clock-section').classList.remove('hidden');
    document.getElementById('news-section').classList.add('hidden');
    // Clear status messages
    document.getElementById('voice-input-status').textContent = '';
    document.getElementById('recognition-result').textContent = '';
}

function showNewsSection() {
    document.getElementById('clock-section').classList.add('hidden');
    document.getElementById('news-section').classList.remove('hidden');
}

setInterval(updateClock, 1000);
updateClock();

document.getElementById('voice-input-btn').addEventListener('click', toggleRecording);

function toggleRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true
            }
        });

        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus',
            audioBitsPerSecond: 16000
        });

        isRecording = true;
        document.getElementById('voice-input-btn').textContent = '録音停止';
        document.getElementById('voice-input-status').textContent = '録音中...';

        audioChunks = [];
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = sendAudioToServer;
        mediaRecorder.onerror = (event) => {
            console.error('MediaRecorder エラー:', event.error);
            document.getElementById('voice-input-status').textContent = '録音エラー';
        };

        mediaRecorder.start(100);
        console.log('録音開始');
    } catch (error) {
        console.error('録音の開始に失敗しました:', error);
        document.getElementById('voice-input-status').textContent =
            'マイクへのアクセスに失敗しました。マイクの権限を確認してください。';
        document.getElementById('voice-input-btn').textContent = '音声入力';
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        document.getElementById('voice-input-btn').textContent = '音声入力';
        document.getElementById('voice-input-status').textContent = '音声を処理中...';
        console.log('録音停止');
    }
}

async function sendAudioToServer() {
    try {
        console.log('音声データの送信準備中...');
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm;codecs=opus' });
        console.log(`送信する音声データのサイズ: ${audioBlob.size} bytes`);

        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        console.log('サーバーへ音声データを送信中...');
        const response = await fetch('/api/speech-to-text', {
            method: 'POST',
            body: formData
        });

        console.log(`サーバーレスポンスステータス: ${response.status}`);
        const result = await response.json();
        console.log('サーバーレスポンス:', result);

        if (!response.ok) {
            throw new Error(result.error || `サーバーエラー: ${response.status}`);
        }

        document.getElementById('recognition-result').textContent = `認識結果: ${result.text}`;
        document.getElementById('voice-input-status').textContent =
            result.stored ? '音声認識完了（テキストを保存しました）' : '音声認識完了';

        // ニュースを取得
        await fetchNews();

    } catch (error) {
        console.error('音声認識エラー:', error);
        document.getElementById('recognition-result').textContent = `エラー: ${error.message}`;
        document.getElementById('voice-input-status').textContent = '音声認識エラー';
    } finally {
        audioChunks = [];
    }
}

async function fetchNews() {
    try {
        showNewsSection();
        // ニュースコンテナをクリア
        const newsContainer = document.getElementById('news-container');
        newsContainer.innerHTML = '';
        document.getElementById('news-status').textContent = 'ニュースを取得中...';

        const response = await fetch('/api/get-news');
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `ニュース取得エラー: ${response.status}`);
        }

        displayNews(data.articles);
        document.getElementById('news-status').textContent = data.articles.length > 0 ? 'ニュース取得完了' : '関連するニュースが見つかりませんでした';

        // 音声の再生
        if (data.audio) {
            await playAudio(data.audio);
            // 音声再生後、時計表示に戻る
            showClockSection();
        }
    } catch (error) {
        console.error('ニュース取得エラー:', error);
        document.getElementById('news-status').textContent = `ニュース取得エラー: ${error.message}`;
        // エラー発生時も時計表示に戻る
        showClockSection();
    }
}

function displayNews(articles) {
    const newsContainer = document.getElementById('news-container');
    newsContainer.innerHTML = '';

    if (articles.length === 0) {
        newsContainer.innerHTML = '<p>ポジティブなニュースはありませんでした。</p>';
        return;
    }

    const newsList = document.createElement('ul');
    newsList.className = 'news-list';

    articles.forEach((article) => {
        const listItem = document.createElement('li');
        listItem.className = 'news-item';

        const title = document.createElement('h3');
        const link = document.createElement('a');
        link.href = article.url;
        link.target = '_blank';
        link.textContent = article.title;
        title.appendChild(link);

        const description = document.createElement('p');
        description.textContent = article.description;

        const publishedAt = document.createElement('span');
        publishedAt.className = 'news-date';
        publishedAt.textContent = new Date(article.publishedAt).toLocaleString('ja-JP');

        listItem.appendChild(title);
        listItem.appendChild(description);
        listItem.appendChild(publishedAt);

        newsList.appendChild(listItem);
    });

    newsContainer.appendChild(newsList);
}

async function playAudio(audioBase64) {
    return new Promise((resolve, reject) => {
        const audio = new Audio(`data:audio/mp3;base64,${audioBase64}`);
        audio.onended = resolve;
        audio.onerror = reject;
        audio.play().catch(error => {
            console.error('音声の再生に失敗しました:', error);
            reject(error);
        });
    });
}

// 初期表示は時計セクション
showClockSection();

