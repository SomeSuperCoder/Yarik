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
import math

def filter(result):
    with open("remove_words.json", "r", encoding='utf-8') as file:
        data = json.loads(file.read())
        print(data)

    filtered_str = json.loads(result)["text"]
    for i in data:
        filtered_str = filtered_str.replace(i, "")

    return filtered_str.strip()

playing_now = False

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
xls.close()
print(dataset)
print(type(dataset["A"]))

last_index = None

model, _ = torch.hub.load(repo_or_dir="snakers4/silero-models",
                          model='silero_tts',
                          language=lang,
                          speaker=model_id)

model.to(device)


def respond(text):
    audio = model.apply_tts(text=text,
                            speaker=speaker,
                            sample_rate=sample_rate,
                            put_accent=put_accent,
                            put_yo=put_yo)
    sd.play(audio, sample_rate * 1.2)
    time.sleep((len(audio) / sample_rate) + 1)
    sd.stop()

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
            result: str = rec.Result()
            if json.loads(result)["text"] == "":
                continue
            if fuzz.partial_ratio(result, "ярик") < 80:
                continue
            print(result)
            matches = []

            if json.loads(result)["text"] != "ярик":
                for i in range(len(dataset["A"])):
                    name = dataset["A"][i]

                    filtered_str = filter(result)
                    matches.append(fuzz.partial_ratio(filtered_str, name))

                    print(result)
                    print(f"Filtered: {filtered_str}")
                    print(matches)

                    print(f"The index is: {matches.index(max(matches))}")

                # if not "ярик" in result:
                #     continue

                if max(matches) < 70:
                    respond("... В мо+ей базе данных пока нет ответа на данный вопрос ...")
                else:
                    info = dataset["B"][matches.index(max(matches))]
                    name = dataset["A"][matches.index(max(matches))]
                    current_text = f"{info}."
                    respond(f"... ... {current_text} ... ...")
