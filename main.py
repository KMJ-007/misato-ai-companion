import openai
import soundfile as sf
import sounddevice as sd
import speech_recognition as sr
from elevenlabs import generate, save, set_api_key
from dotenv import load_dotenv
from os import getenv, path
from json import load, dump, JSONDecodeError
from gtts import gTTS


class Misato:
    def __init__(self):
        load_dotenv()
        self.recogniser = sr.Recognizer()
        self.user_input_service = "whisper"
        self.stt_duration = 0.5
        self.chat_service = "openai"
        self.chat_model = "gpt-3.5-turbo"
        self.chat_temperature = 0.5
        self.personality_file = "personality.txt"
        self.tts_service = "google"
        self.tts_voice = "Elli"
        self.tts_model = "eleven_monolingual_v1"
        self.message_history = []
        self.context = []
        openai.api_key = getenv("OPENAI_API_KEY")
        set_api_key(getenv("ELEVENLABS_API_KEY"))

    def initialize(
        self,
        audio_input=None,
        output_device=None,
        chat_service="openai",
        chat_model="gpt-3.5-turbo",
        tts_service="google",
        tts_voice="Elli",
        tts_model="eleven_monolingual_v1",
    ):
        self.mic = sr.Microphone(device_index=audio_input)
        self.setup_output_device(output_device)
        self.load_chat_data()

        self.chat_service = chat_service
        self.chat_model = chat_model
        self.tts_service = tts_service
        self.tts_voice = tts_voice
        self.tts_model = tts_model

        openai.api_key = getenv("OPENAI_API_KEY")
        set_api_key(getenv("ELEVENLABS_API_KEY"))

    def setup_output_device(self, output_device):
        try:
            if output_device is not None:
                sd.check_output_settings(output_device)
                sd.default.samplerate = 44100
                sd.default.device = output_device
        except sd.PortAudioError:
            print("Invalid output device. Please choose one from the list below:")
            print(sd.query_devices())
            raise

    def load_chat_data(self):
        with open(self.personality_file, "r") as f:
            personality = f.read()
        self.context = [{"role": "system", "content": personality}]

        if path.isfile("message_history.txt"):
            try:
                with open("message_history.txt", "r") as f:
                    self.message_history = load(f)
            except JSONDecodeError:
                pass

    def conversation_cycle(self):
        user_input = self.get_user_input()
        response = self.get_chat_response(user_input)
        self.tts_say(response)
        return {"user": user_input, "assistant": response}

    def get_user_input(self):
        print("Starting listening")
        with self.mic as source:
            self.recogniser.adjust_for_ambient_noise(source, duration=self.stt_duration)
            audio = self.recogniser.listen(source)
        print("Stopped listening")

        if self.user_input_service == "whisper":
            return self.whisper_sr(audio)
        elif self.user_input_service == "google":
            return self.recogniser.recognize_google(audio)
        else:
            return input("User: ")

    def whisper_sr(self, audio):
        with open("speech.wav", "wb") as f:
            f.write(audio.get_wav_data())
        with open("speech.wav", "rb") as audio_file:
            transcript = openai.Audio.transcribe(model="whisper-1", file=audio_file)
        return transcript["text"]

    def get_chat_response(self, prompt):
        self.add_message("user", prompt)
        messages = self.context + self.message_history

        response = openai.ChatCompletion.create(
            model=self.chat_model, messages=messages, temperature=self.chat_temperature
        )
        response_text = response.choices[0].message["content"]
        self.add_message("assistant", response_text)
        self.update_message_history()
        return response_text

    def add_message(self, role, content):
        self.message_history.append({"role": role, "content": content})

    def update_message_history(self):
        with open("message_history.txt", "w") as f:
            dump(self.message_history, f)

    def tts_say(self, text):
        if self.tts_service == "google":
            gTTS(text=text, lang="en", slow=False).save("output.mp3")
        elif self.tts_service == "elevenlabs":
            audio = generate(text=text, voice=self.tts_voice, model=self.tts_model)
            save(audio, "output.mp3")
        else:
            print(f"Waifu: {text}")
            return

        data, fs = sf.read("output.mp3")
        sd.play(data, fs)
        sd.wait()


def main():
    m = Misato()
    m.initialize(
        audio_input=None,
        output_device=1,
        chat_service="openai",
        chat_model="gpt-3.5-turbo",
        tts_service="elevenlabs",
        tts_voice="Emily",
        tts_model="eleven_monolingual_v1",
    )
    conversation = m.conversation_cycle()
    print(conversation)


if __name__ == "__main__":
    main()
