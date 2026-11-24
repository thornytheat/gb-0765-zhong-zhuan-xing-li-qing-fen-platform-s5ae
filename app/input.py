from .config import FILES, SAMPLES
from .errors import DeskError


def sample(name):
    if name not in ('dirty', 'clean'):
        raise DeskError('NO_SAMPLE', '样例不存在', 404)
    return {file: (SAMPLES / name / file).read_bytes().decode('utf-8') for file in FILES}


def submission(body):
    if isinstance(body, dict) and set(body) == {'sample'} and isinstance(body['sample'], str):
        return sample(body['sample'])
    if isinstance(body, dict) and set(body) == {'files'}:
        files = body['files']
        if isinstance(files, dict) and set(files) == set(FILES) and all(isinstance(text, str) for text in files.values()):
            return files
    raise DeskError('BAD_INPUT', '请选择样例或提交三份 CSV')
