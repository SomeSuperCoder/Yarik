#!/usr/bin/python3

from pandas import *
import torch
import sounddevice as sd
import time
import vosk
import sys
import queue
from fuzzywuzzy import fuzz
import json

lang = "ru"
model_id = "ru_v3"
sample_rate = 48000
speaker = "aidar"
put_accent = True
put_yo = True
device = torch.device("cpu")

vosk_model = vosk.Model("model")
vosk_samplerate = 16000
vosk_device = 1
q = queue.Queue()

xls = ExcelFile('data.xlsx')
df = xls.parse(xls.sheet_names[0])
dataset = df.to_dict()
print(dataset)
print(type(dataset["A"]))

last_index = None

model, _ = torch.hub.load(repo_or_dir="snakers4/silero-models",
                          model='silero_tts',
                          language=lang,
                          speaker=model_id)

model.to(device)

def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

with sd.RawInputStream(samplerate=vosk_samplerate, blocksize=8000, device=vosk_device, dtype="int16",
                       channels=1, callback=callback):
    rec = vosk.KaldiRecognizer(vosk_model, vosk_samplerate)

    while True:
        data = q.get()

        if rec.AcceptWaveform(data):
            result = rec.Result()
            print(result)
            matches = []

            if json.loads(result)["text"] == "ярик":
                continue

            for i in range(len(dataset["A"])):
                name = dataset["A"][i]

                filtered_str = json.loads(result)["text"].replace("ярик", "").replace("расскажи", "").replace("мне", "").replace("про", "").replace("что", "").replace("такое", "").replace(" ", "").replace("как", "").replace("зовут", "").replace("кто", "").replace("такие", "").replace("сколько", "").replace("вот", "")
                matches.append(fuzz.ratio(filtered_str, name))

                print(result)
                print(f"Filtered: {filtered_str}")
                print(matches)

                print(f"The index is: {matches.index(max(matches))}")

            if not "ярик" in result:
                continue

            if max(matches) < 50:
                # audio = model.apply_tts(text="В мо+ей базе данных пока нет ответа на данный вопрос. Но я попрошу своего разработчика добавить информацию об этом",
                #                         speaker=speaker,
                #                         sample_rate=sample_rate,
                #                         put_accent=put_accent,
                #                         put_yo=put_yo)
                # sd.play(audio, sample_rate * 1.05)
                # time.sleep((len(audio) / sample_rate) + 0.5)
                # sd.stop()

                continue

            info = dataset["B"][matches.index(max(matches))]
            name = dataset["A"][matches.index(max(matches))]
            current_text = f"{info}."

            audio = model.apply_tts(text=current_text,
                                    speaker=speaker,
                                    sample_rate=sample_rate,
                                    put_accent=put_accent,
                                    put_yo=put_yo)
            sd.play(audio, sample_rate * 1.05)
            time.sleep((len(audio) / sample_rate) + 0.5)
            sd.stop()
