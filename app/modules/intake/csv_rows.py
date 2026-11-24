import csv
from io import StringIO
from app.faults import DockFault


def rows(text, fields, source):
    stream = csv.reader(StringIO(text.removeprefix('\ufeff'), newline=''), strict=True)
    accepted, isolated = [], []
    blanks, headers, total = 0, 0, 0
    try:
        header = next(stream, None)
        if header is None:
            raise DockFault('EMPTY', f'{source} 原件为空')
        if len(header) != len(fields) or set(header) != set(fields):
            raise DockFault('HEADER', f'{source} 表头不符')
        while True:
            line = stream.line_num + 1
            raw = next(stream, None)
            if raw is None:
                break
            total += 1
            if not any(cell.strip() for cell in raw):
                blanks += 1
            elif raw == header:
                headers += 1
            elif len(raw) != len(header):
                isolated.append(dict(line=line, source=source, raw=raw, code='WIDTH'))
            else:
                accepted.append(dict(line=line, source=source, raw=raw, **dict(zip(header, (v.strip() for v in raw)))))
    except csv.Error as exc:
        raise DockFault('CSV', f'{source} 原件第 {stream.line_num} 行损坏') from exc
    return accepted, isolated, dict(total=total, blanks=blanks, repeated_headers=headers)
