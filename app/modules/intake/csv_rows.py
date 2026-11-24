import csv
from io import StringIO
from app.faults import DockFault


def rows(text, fields, source, optional=()):
    """解析 CSV 原件。

    `fields` 为必备表头，`optional` 为可选的附加表头。附加表头可以整列
    缺席（老原件照常采信），也可以任意子集出现；备列不得缺席或重复。
    每行缺省的附加字段补空串，交由后续契约判定。
    """
    stream = csv.reader(StringIO(text.removeprefix('﻿'), newline=''), strict=True)
    accepted, isolated = [], []
    blanks, headers, total = 0, 0, 0
    required, extra = set(fields), set(optional)
    try:
        header = next(stream, None)
        if header is None:
            raise DockFault('EMPTY', f'{source} 原件为空')
        if (len(header) != len(set(header)) or not required <= set(header) or
                not set(header) <= required | extra):
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
                record = dict(line=line, source=source, raw=raw,
                              **dict(zip(header, (v.strip() for v in raw))))
                for name in optional:
                    record.setdefault(name, '')
                accepted.append(record)
    except csv.Error as exc:
        raise DockFault('CSV', f'{source} 原件第 {stream.line_num} 行损坏') from exc
    return accepted, isolated, dict(total=total, blanks=blanks, repeated_headers=headers)
