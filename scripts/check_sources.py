"""Check selected text at the reviewed URLs. Product interpretation is editorial."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
import unicodedata
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'web/data'


def normal(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().replace('’', "'").split())


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.words = []
        self.excluded = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.excluded += 1
        if tag == 'img' and not self.excluded:
            self.words.append(dict(attrs).get('alt', '') or '')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.excluded = max(0, self.excluded - 1)

    def handle_data(self, value):
        if not self.excluded:
            self.words.append(value)


def fetch(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; CoolCode.ca source check / maplelabel)'})
    with urlopen(req, timeout=23) as response:
        body = response.read(4_000_001)
        if len(body) > 4_000_000 or response.status != 200:
            raise ValueError('Unexpected source response')
        return body.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')


def inspect(source, get):
    try:
        document = Text()
        document.feed(get(source['url']))
        text = normal(' '.join(document.words))
        return all(normal(s) in text for s in source['anchors'])
    except (OSError, TimeoutError, ValueError):
        return False


def checked(catalogue, previous, today, get=fetch):
    automated = [s for s in catalogue['sources'] if s['mode'] == 'scheduled']
    with ThreadPoolExecutor(max_workers=3) as pool:
        outcomes = list(pool.map(lambda s: inspect(s, get), automated))
    failed = [s['id'] for s, ok in zip(automated, outcomes) if not ok]
    return {'reviewed_at': catalogue['reviewed_at'], 'checked_at': previous.get('checked_at') if failed else today,
            'last_attempt': today, 'product_count': len(catalogue['products']), 'scheduled_sources': len(automated),
            'editorial_sources': len(catalogue['sources']) - len(automated), 'needs_review': failed}


def main():
    catalogue = json.loads((DATA / 'catalogue.json').read_text())
    path = DATA / 'status.json'
    previous = json.loads(path.read_text()) if path.exists() else {}
    status = checked(catalogue, previous, datetime.now(timezone.utc).date().isoformat())
    with NamedTemporaryFile('w', encoding='utf-8', dir=DATA, delete=False) as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
        f.write('\n')
    receipt = Path(f.name)
    receipt.chmod(0o644)
    receipt.replace(path)
    print(json.dumps(status))
    return int(bool(status['needs_review']))


if __name__ == '__main__':
    raise SystemExit(main())
