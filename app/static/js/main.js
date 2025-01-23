document.addEventListener("DOMContentLoaded", () => {
    const eventSource = new EventSource("/events")
    const voiceInputBtn = document.getElementById("voice-input-btn")
    const clockSection = document.getElementById("clock-section")
    const voiceInputSection = document.getElementById("voice-input-section")
    const newsSection = document.getElementById("news-section")
    const voiceInputStatus = document.getElementById("voice-input-status")
    const recognitionResult = document.getElementById("recognition-result")

    eventSource.onmessage = (event) => {
        if (event.data === "touch_detected") {
            console.log("タッチ検出：音声入力を開始します")
            voiceInputStatus.textContent = "タッチ検出：音声入力を開始します"
            startVoiceInput()
        }
    }

    eventSource.onerror = (error) => {
        console.error("SSE エラー:", error)
        // エラー時に再接続を試みる
        setTimeout(() => {
            console.log("SSE 再接続を試みます...")
            eventSource.close()
            initEventSource()
        }, 5000)
    }

    function initEventSource() {
        const newEventSource = new EventSource("/events")
        newEventSource.onmessage = eventSource.onmessage
        newEventSource.onerror = eventSource.onerror
        eventSource = newEventSource
    }

    voiceInputBtn.addEventListener("click", startVoiceInput)

    function startVoiceInput() {
        showSection(voiceInputSection)
        voiceInputStatus.textContent = "音声入力を開始します..."
        recognitionResult.textContent = ""

        // 音声入力ボタンを無効化
        voiceInputBtn.disabled = true

        // 5秒間のカウントダウンを表示
        let countdown = 5
        const countdownInterval = setInterval(() => {
            voiceInputStatus.textContent = `音声を入力してください... (残り${countdown}秒)`
            countdown--
            if (countdown < 0) {
                clearInterval(countdownInterval)
                voiceInputStatus.textContent = "音声認識処理中..."
            }
        }, 1000)

        // 5秒後に音声認識を開始
        setTimeout(() => {
            fetch("/api/start-voice-input", { method: "POST" })
                .then((response) => response.json())
                .then((data) => {
                    if (data.success) {
                        voiceInputStatus.textContent = "音声認識完了"
                        recognitionResult.textContent = `認識結果: ${data.text}`
                        fetchNews()
                    } else {
                        voiceInputStatus.textContent = "音声認識エラー"
                        recognitionResult.textContent = `エラー: ${data.error}`
                    }
                })
                .catch((error) => {
                    console.error("音声入力エラー:", error)
                    voiceInputStatus.textContent = "音声入力エラー"
                    recognitionResult.textContent = `エラー: ${error.message}`
                })
                .finally(() => {
                    // 音声入力ボタンを再度有効化
                    voiceInputBtn.disabled = false
                })
        }, 5000)
    }

    function fetchNews() {
        showSection(newsSection)
        const newsContainer = document.getElementById("news-container")
        const newsStatus = document.getElementById("news-status")
        newsContainer.innerHTML = ""
        newsStatus.textContent = "ニュースを取得中..."

        fetch("/api/get-news")
            .then((response) => response.json())
            .then((data) => {
                if (data.articles) {
                    displayNews(data.articles)
                    newsStatus.textContent = "ニュース取得完了"
                    if (data.audio) {
                        playAudio(data.audio)
                    }
                } else {
                    newsStatus.textContent = "ニュースが見つかりませんでした"
                }
            })
            .catch((error) => {
                console.error("ニュース取得エラー:", error)
                newsStatus.textContent = `ニュース取得エラー: ${error.message}`
            })
    }

    function displayNews(articles) {
        const newsContainer = document.getElementById("news-container")
        newsContainer.innerHTML = ""

        if (articles.length === 0) {
            newsContainer.innerHTML = "<p>ポジティブなニュースはありませんでした。</p>"
            return
        }

        const newsList = document.createElement("ul")
        newsList.className = "news-list"

        articles.forEach((article) => {
            const listItem = document.createElement("li")
            listItem.className = "news-item"

            const title = document.createElement("h3")
            const link = document.createElement("a")
            link.href = article.url
            link.target = "_blank"
            link.textContent = article.title
            title.appendChild(link)

            const description = document.createElement("p")
            description.textContent = article.description

            const publishedAt = document.createElement("span")
            publishedAt.className = "news-date"
            publishedAt.textContent = new Date(article.publishedAt).toLocaleString("ja-JP")

            listItem.appendChild(title)
            listItem.appendChild(description)
            listItem.appendChild(publishedAt)

            newsList.appendChild(listItem)
        })

        newsContainer.appendChild(newsList)
    }

    function playAudio(audioBase64) {
        const audio = new Audio(`data:audio/mp3;base64,${audioBase64}`)
        audio.play().catch((error) => {
            console.error("音声の再生に失敗しました:", error)
        })
    }

    function showSection(section) {
        clockSection.classList.add("hidden")
        voiceInputSection.classList.add("hidden")
        newsSection.classList.add("hidden")
        section.classList.remove("hidden")
    }

    function updateClock() {
        const now = new Date()
        const hours = now.getHours()
        const minutes = now.getMinutes()
        const seconds = now.getSeconds()

        updateClockHands(hours, minutes, seconds)

        const digitalTime = `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`
        document.getElementById("digital-time").textContent = `日本時間: ${digitalTime}`
    }

    function updateClockHands(hours, minutes, seconds) {
        const hourHand = document.getElementById("hour-hand")
        const minuteHand = document.getElementById("minute-hand")
        const secondHand = document.getElementById("second-hand")

        const hourAngle = ((hours % 12) + minutes / 60) * 30
        const minuteAngle = (minutes + seconds / 60) * 6
        const secondAngle = seconds * 6

        hourHand.setAttribute("transform", `rotate(${hourAngle}, 100, 100)`)
        minuteHand.setAttribute("transform", `rotate(${minuteAngle}, 100, 100)`)
        secondHand.setAttribute("transform", `rotate(${secondAngle}, 100, 100)`)
    }

    setInterval(updateClock, 1000)
    updateClock()
    showSection(clockSection)
})

