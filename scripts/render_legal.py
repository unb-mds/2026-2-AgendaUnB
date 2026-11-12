"""Render project legal documents. Requires Markdown==3.11.3.

Default output is a local draft preview; --publish refuses unresolved drafts.
"""
import argparse
import html
from pathlib import Path
import re

import markdown

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = {
    'politica-de-privacidade.md': ('privacidade.html', 'Política de Privacidade'),
    'termos-de-uso.md': ('termos.html', 'Termos de Uso'),
}
STYLE = '''
body{margin:0;background:#10151c;color:#e8edf4;font:17px/1.7 system-ui,sans-serif}
main{max-width:900px;margin:auto;padding:32px 24px 80px}a{color:#71baff}
h1,h2{line-height:1.3}h1{font-size:2.2rem}h2{margin-top:2rem}
nav{display:flex;flex-wrap:wrap;gap:20px;margin-bottom:36px}
.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{border:1px solid #445064;padding:12px;text-align:left;vertical-align:top}
.draft{border:2px solid #ffc26e;padding:16px;color:#ffc26e}
:focus-visible{outline:3px solid #71baff;outline-offset:4px}
'''


def render(publish=False):
    documents = []
    for source, (filename, title) in DOCUMENTS.items():
        text = (ROOT / 'docs/produto' / source).read_text(encoding='utf-8')
        unresolved = '[DEFINIR]' in text or 'proposta para revisão' in text.lower()
        if publish and unresolved:
            raise ValueError(f'{source}: revisão e decisões pendentes impedem a publicação.')
        text = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, count=1, flags=re.S)
        for original, (target, _) in DOCUMENTS.items():
            text = text.replace(f']({original})', f'](/{target})')
        content = markdown.markdown(text, extensions=['tables'])
        content = content.replace('<table>', '<div class="table-scroll"><table>').replace('</table>', '</table></div>')
        warning = '' if publish else '<aside class="draft">Prévia local — documento em revisão, não publicado.</aside>'
        robots = '' if publish else '<meta name="robots" content="noindex,nofollow">'
        page = f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">{robots}
<title>{html.escape(title)} | Agenda UnB</title><style>{STYLE}</style></head>
<body><main><nav aria-label="Navegação"><a href="/">Agenda UnB</a>
<a href="/privacidade.html">Privacidade</a><a href="/termos.html">Termos de Uso</a></nav>
{warning}{content}</main></body></html>'''
        documents.append((filename, page))
    output = ROOT / ('frontend/public' if publish else 'output/legal-preview')
    output.mkdir(parents=True, exist_ok=True)
    for filename, page in documents:
        (output / filename).write_text(page, encoding='utf-8')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    print(render(args.publish))
