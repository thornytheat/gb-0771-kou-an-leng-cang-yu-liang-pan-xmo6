from datetime import datetime, timezone
import re


def second(raw):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})', raw):
        raise ValueError('offset with seconds required')
    return int(datetime.fromisoformat(raw).timestamp())


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace('+00:00', 'Z')
