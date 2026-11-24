from collections import defaultdict
from fractions import Fraction
from .utc import iso


def minutes(seconds):
    return str(Fraction(seconds, 60))


def lanes(stages):
    start, end = stages['window']['start'], stages['window']['end']
    span = end - start
    grouped = defaultdict(list)
    for row in stages['exposure']['rows']:
        grouped[row['lot']].append(row)
    markers = defaultdict(list)
    for event in stages['custody']['rows']:
        if start <= event['time'] < end:
            point = round((event['time'] - start) * 100 / span, 6)
            markers[event['lot']].append(dict(event, point=point))
    tracks = []
    for lot, rows in sorted(grouped.items()):
        blocks = []
        for row in sorted(rows, key=lambda value: value['start']):
            left = (row['start'] - start) * 100 / span
            width = row['seconds'] * 100 / span
            blocks.append(dict(row, rel=round(left, 6), width=round(width, 6)))
        tracks.append(dict(lot=lot, blocks=blocks, markers=markers[lot],
                           description=stages['registry']['lots'][lot]['description']))
    ticks = [dict(left=index*20, label=iso(start + index*span//5)[11:19]) for index in range(6)]
    return tracks, ticks
