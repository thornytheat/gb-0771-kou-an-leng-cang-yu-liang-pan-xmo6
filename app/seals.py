from hashlib import sha256
import json


def compact(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def sha(text):
    return sha256(text.encode()).hexdigest()


def input_seals(files):
    return {source: sha(text) for source, text in files.items()}
