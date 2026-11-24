from pathlib import Path

VERSION = 'ice-stock/1'
EXAMPLES = Path(__file__).resolve().parent.parent / 'sample_data'
PARTS = ('moves', 'slots', 'doors', 'temperatures', 'lots', 'window')
TEMP_MAX_AGE = 600
MIN_DOOR_PULSE = 30
