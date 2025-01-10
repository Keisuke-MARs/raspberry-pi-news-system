import pyaudio
import wave
import requests
import json

def record_audio(filename, duration=5, sample_rate=44100, chunk=1024):
    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=sample_rate,
                        input=True,
                        frames_per_buffer=chunk)

    print("Recording...")

    frames = []

    for i in range(0, int(sample_rate / chunk * duration)):
        data = stream.read(chunk)
        frames.append(data)

    print("Finished recording.")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
    wf.setframerate(sample_rate)
    wf.writeframes(b''.join(frames))
    wf.close()

def send_audio_to_server(filename, url):
    with open(filename, 'rb') as audio_file:
        files = {'audio': audio_file}
        response = requests.post(url, files=files)
    
    if response.status_code == 200:
        result = json.loads(response.text)
        print(f"Recognized text: {result['text']}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    audio_file = "recorded_audio.wav"
    server_url = "http://localhost:5000/api/speech-to-text"

    record_audio(audio_file)
    send_audio_to_server(audio_file, server_url)

