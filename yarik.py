#!/usr/bin/python3

import random

from pandas import *
import torch
import sounddevice as sd
import time
import vosk
import sys
import queue
from fuzzywuzzy import fuzz
import torchaudio
import json
import hashlib
import os

def filter(result_text):
    with open("remove_words.json", "r", encoding='utf-8') as file:
        data = json.loads(file.read())

    filtered_str = result_text
    for i in data:
        filtered_str = filtered_str.replace(i, "")

    return filtered_str.strip()

playing_now = False

# Names
robot_name = "ярик"
cache_dir = "./cache"

# Builtins
builtin = {
    "HELLO": "Зравствуйте!",
    "I_AM_LISTENING": f"{robot_name} слушает",
    "IDK": "... В мо+ей базе данных пока нет ответа на данный вопрос ...",
    "I_AM": f"Я р+обот-гид {robot_name}... Я могу рассказать вам о Чувашии! Жду вопросов!",
    "RELOAD_SUCCESS": "Перезагруска б+азы данных - успешно!"
}

# Silero config
lang = "ru"
model_id = "ru_v3"
sample_rate = 48000
speaker = "aidar"
put_accent = True
put_yo = True
device = torch.device("cpu")

# Vosk config
vosk_model = vosk.Model("model")
vosk_samplerate = 16000
vosk_device = 6
q = queue.Queue()


def load_db():
    print("Обновление БД...")

    global dataset
    global variants

    xls = ExcelFile('data.xlsx')
    df = xls.parse(xls.sheet_names[0])
    dataset = df.to_dict()
    xls.close()

    xls = ExcelFile('variants.xlsx')
    df = xls.parse(xls.sheet_names[0])
    variants = df.to_dict()
    xls.close()

    now_should_exist = []

    file_list = os.listdir(cache_dir)
    need_to_process = []
    done = 0

    for _, answer in dataset["B"].items():
        need_to_process.append(answer) if not answer.startswith("cmd_") else ...

    for _, answer in variants["answers"].items():
        [need_to_process.append(i) for i in answer.split(";")]

    for _, answer in builtin.items():
        need_to_process.append(answer)

    for answer in need_to_process:
        done += 1
        answer_hash = hashlib.sha256(answer.encode()).hexdigest()
        now_should_exist.append(answer_hash)

        print(answer)
        print(answer_hash)

        if os.path.isfile(os.path.join(cache_dir, answer_hash)):
            print("Already exists")
            continue

        audio = respond_logic(answer)

        with open(os.path.join(cache_dir, answer_hash), "w") as f:
            f.write(json.dumps(audio))

        print(f"{round(done/len(need_to_process) * 100, 2)}% done")

    for file in file_list:
        if file not in now_should_exist:
            os.remove(os.path.join(cache_dir, file))

last_index = None

model, _ = torch.hub.load(repo_or_dir="snakers4/silero-models",
                          model='silero_tts',
                          language=lang,
                          speaker=model_id)

model.to(device)

def respond(text):
    with open(os.path.join(cache_dir, hashlib.sha256(text.encode()).hexdigest()), "r") as f:
        audio = torch.Tensor(json.loads(f.read()))

    sd.play(audio, sample_rate * 1.2)
    time.sleep((len(audio) / sample_rate) + 1)
    sd.stop()

def respond_logic(text):
    """
    This function should not be called directly
    """

    return model.apply_tts(text=text,
                            speaker=speaker,
                            sample_rate=sample_rate,
                            put_accent=put_accent,
                            put_yo=put_yo).numpy().tolist()

def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))


# The program logic starts here

load_db()

respond(builtin["HELLO"])
respond(builtin["I_AM_LISTENING"])


with sd.RawInputStream(samplerate=vosk_samplerate, blocksize=8000, device=vosk_device, dtype="int16",
                       channels=1, callback=callback):
    rec = vosk.KaldiRecognizer(vosk_model, vosk_samplerate)

    while True:
        data = q.get()

        if rec.AcceptWaveform(data):
            result: str = rec.Result()
            result_text = json.loads(result)["text"]
            if result_text == "":
                continue
            if fuzz.partial_ratio(result, robot_name) < 75:
                continue
            if fuzz.partial_ratio(result, "обнови базу данных") > 80:
                load_db()
                respond(builtin["RELOAD_SUCCESS"])
                continue

            matches = []

            if result_text != robot_name:
                print(f"Слышу: {result_text}")
                for i in range(len(dataset["A"])):
                    name = dataset["A"][i]

                    filtered_str = filter(result_text)
                    matches.append(fuzz.partial_ratio(filtered_str, name))

                if max(matches) < 70:
                    respond(builtin["IDK"])
                elif dataset["B"][matches.index(max(matches))].startswith("cmd_"):
                    chosen = random.choice(list(variants["answers"].values())[list(variants["cmd_id"].values()).index(dataset["B"][matches.index(max(matches))])].split(";"))  
                    print(f"Говорю: {chosen}")
                    respond(chosen)
                else:
                    info = dataset["B"][matches.index(max(matches))]
                    name = dataset["A"][matches.index(max(matches))]
                    current_text = f"{info}"
                    print(f"Говорю: {current_text}")
                    respond(current_text) # TODO: add .... ... TEXT ... ...
            else:
                respond(builtin["I_AM"])
