import csv
from io import StringIO

from app.errors import DeskError


def read_table(text, columns, source):
    reader = csv.reader(StringIO(text.removeprefix('\ufeff'), newline=''), strict=True)
    counts = dict(source_rows=0, sections=1, blanks=0, rejected=0)
    records, rejected = [], []
    try:
        header = next(reader, None)
        if header is None:
            raise DeskError('EMPTY_FILE', f'{source} 无原件')
        if not any(header):
            raise DeskError('BLANK_FILE', f'{source} 首行为空')
        if len(header) != len(columns) or set(header) != set(columns):
            raise DeskError('BAD_HEADER', f'{source} 表头不符')
        while True:
            line = reader.line_num + 1
            cells = next(reader, None)
            if cells is None:
                break
            counts['source_rows'] += 1
            if not any(cell.strip() for cell in cells):
                counts['blanks'] += 1
            elif cells == header:
                counts['sections'] += 1
            elif len(cells) != len(header):
                rejected.append(dict(line=line, reason='WIDTH', raw=cells, source=source))
            else:
                records.append(dict(line=line, source=source, raw=cells, **dict(zip(header, cells))))
    except csv.Error as exc:
        raise DeskError('CSV_SYNTAX', f'{source} 第 {reader.line_num} 行 CSV 损坏') from exc
    if not counts['source_rows']:
        raise DeskError('HEADER_ONLY', f'{source} 仅含表头')
    if counts['source_rows'] == counts['blanks']:
        raise DeskError('BLANK_FILE', f'{source} 记录全为空')
    counts['rejected'] = len(rejected)
    return records, rejected, counts
