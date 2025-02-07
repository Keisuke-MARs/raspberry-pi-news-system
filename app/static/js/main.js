document.addEventListener("DOMContentLoaded", () => {
  let eventSource
  const voiceInputBtn = document.getElementById("voice-input-btn")
  const clockSection = document.getElementById("clock-section")
  const voiceInputSection = document.getElementById("voice-input-section")
  const newsSection = document.getElementById("news-section")
  const voiceInputStatus = document.getElementById("voice-input-status")
  const recognitionResult = document.getElementById("recognition-result")

  let isRecording = false
  const audioPlaybackPromise = null

  function initEventSource() {
    if (eventSource) {
      eventSource.close()
    }
    eventSource = new EventSource("/events")
    eventSource.onmessage = (event) => {
      if (event.data === "touch_detected") {
        console.log("タッチ検出：音声入力を開始/停止します")
        toggleVoiceInput()
      }
    }
    eventSource.onerror = (error) => {
      console.error("SSE エラー:", error)
      eventSource.close()
      setTimeout(() => {
        console.log("SSE 再接続を試みます...")
        initEventSource()
      }, 5000)
    }
  }

  // 初期化時にSSE接続を開始
  initEventSource()

  voiceInputBtn.addEventListener("click", toggleVoiceInput)

  function toggleVoiceInput() {
    if (isRecording) {
      stopVoiceInput()
    } else {
      startVoiceInput()
    }
  }

  function startVoiceInput() {
    showSection(voiceInputSection)
    voiceInputStatus.textContent = "音声入力を開始します..."
    recognitionResult.textContent = ""
    isRecording = true
    voiceInputBtn.textContent = "音声入力停止"

    fetch("/api/start-voice-input", { method: "POST" })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          voiceInputStatus.textContent = "音声入力中..."
        } else {
          voiceInputStatus.textContent = "音声入力エラー"
          recognitionResult.textContent = `エラー: ${data.error}`
          isRecording = false
          voiceInputBtn.textContent = "音声入力開始"
        }
      })
      .catch((error) => {
        console.error("音声入力エラー:", error)
        voiceInputStatus.textContent = "音声入力エラー"
        recognitionResult.textContent = `エラー: ${error.message}`
        isRecording = false
        voiceInputBtn.textContent = "音声入力開始"
      })
  }

  function stopVoiceInput() {
    isRecording = false
    voiceInputBtn.textContent = "音声入力開始"
    voiceInputStatus.textContent = "音声認識処理中..."

    fetch("/api/stop-voice-input", { method: "POST" })
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
              .then(() => {
                console.log("音声再生が完了しました")
                returnToClockAfterDelay(0)
              })
              .catch((error) => {
                console.error("音声再生エラー:", error)
                returnToClockAfterDelay(5000)
              })
          } else {
            returnToClockAfterDelay(5000)
          }
        } else {
          newsStatus.textContent = "ニュースが見つかりませんでした"
          returnToClockAfterDelay(5000)
        }
      })
      .catch((error) => {
        console.error("ニュース取得エラー:", error)
        newsStatus.textContent = `ニュース取得エラー: ${error.message}`
        returnToClockAfterDelay(5000)
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
    return new Promise((resolve, reject) => {
      const audio = new Audio(`data:audio/mp3;base64,${audioBase64}`)
      audio.onended = () => {
        console.log("音声再生が終了しました")
        resolve()
      }
      audio.onerror = (error) => {
        console.error("音声の再生に失敗しました:", error)
        reject(error)
      }
      // 自動再生を試みる
      audio.play().catch((error) => {
        console.error("自動再生に失敗しました:", error)
        // 自動再生に失敗した場合、ユーザーインタラクションを待つ
        document.body.addEventListener(
          "click",
          function playHandler() {
            audio.play().catch(reject)
            document.body.removeEventListener("click", playHandler)
          },
          { once: true },
        )
        console.log("音声の再生準備完了。ユーザーの操作を待っています...")
      })
    })
  }

  function returnToClockAfterDelay(delay) {
    setTimeout(() => {
      console.log("時計表示に戻ります")
      showSection(clockSection)
    }, delay)
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

