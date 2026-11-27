"""Render the catalogue, comparison pages and scoped sitemap offline."""
from datetime import date
from html import escape
import json
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from search_metadata import add_search_metadata

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://coolcode.ca/maplelabel/'
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
FIELDS = [('inputs', 'Ingredients or materials'), ('processing', 'Processing or manufacturing'), ('ownership', 'Company ownership')]


def e(value):
    return escape(str(value), quote=True)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def a(href, label, cls=''):
    return f'<a href="{e(href)}" class="{e(cls)}">{e(label)}</a>'


def by_id(rows):
    items = {row['id']: row for row in rows}
    if len(items) != len(rows) or not all(SLUG.fullmatch(k) for k in items):
        raise ValueError('Source, rule and product IDs must be unique URL-safe names')
    return items


def validate(data, status):
    products = by_id(data['products'])
    if {'label-guide','quebec-cheese-and-coffee'} & set(products):
        raise ValueError('Product ID collides with an editorial route')
    rules = by_id(data['rules'])
    sources = by_id(data['sources'])
    date.fromisoformat(data['reviewed_at'])
    if not products or len(products) != status['product_count'] or data['reviewed_at'] != status['reviewed_at']:
        raise ValueError('Catalogue and status disagree. Run the source check after editorial changes.')
    for field in ['last_attempt','checked_at']:
        if status.get(field):
            date.fromisoformat(status[field])
    for source in sources.values():
        url = urlsplit(source['url'])
        if not url.hostname or url.scheme != 'https' or url.username or not source['anchors'] or source['mode'] not in ('scheduled','editorial'):
            raise ValueError('Invalid source record')
    if not set(status['needs_review']).issubset(sources):
        raise ValueError('Unknown source check result')
    for rule in rules.values():
        if rule['source'] and rule['source'] not in sources:
            raise ValueError('A rule has no supporting source')
    for r in products.values():
        if not all(str(r.get(key) or '').strip() for key in ('name','brand','category','claim','summary')):
            raise ValueError('Incomplete product identification')
        if r['rule'] not in rules or not r['sources'] or not set(r['sources']).issubset(sources):
            raise ValueError('Unresolved product evidence')
        if not r['related'] or not set(r['related']).issubset(products) or r['id'] in r['related'] or len(set(r['related'])) != len(r['related']):
            raise ValueError('Unresolved related product')
    return products,rules,sources


def profile_url(r): return 'records/' + r['id'] + '/'


def info(label, value):
    return f'<div><dt>{e(label)}</dt><dd>{e(value or "Not specified in the cited sources.")}</dd></div>'


def card(r, root):
    location = r['province'] or 'Canada · province unspecified'
    return f'''<article class="card"><div class="card-meta">{e(r["category"])} · {e(location)}</div>
<h3>{a(root+profile_url(r),r["name"])}</h3><p class="maker">{e(r["brand"])}</p>
<p><strong>{e(r["claim"])}</strong></p><p>{e(r["summary"])}</p></article>'''


def links(r, sources, status):
    result=[]
    for key in r['sources']:
        s = sources[key]
        mode = 'Editorial review' if s['mode']=='editorial' else 'Scheduled text check'
        if key in status['needs_review']:
            mode += ' · needs review'
        result.append(f'<li>{a(s["url"],s["name"])} <small>{e(mode)}</small></li>')
    return '<ul class="sources">' + ''.join(result) + '</ul>'


def build(root=ROOT):
    tool = read(root/'tool.json')
    if tool['url'] != '/maplelabel/' or tool['result_directory']['path'] != 'records/':
        raise ValueError('Expected native Maple Label routes')
    data = read(root/'web/data/catalogue.json')
    status = read(root/'web/data/status.json')
    products,rules,sources = validate(data,status)
    first = products['oka-original']
    second = products['balanced-espresso']
    with TemporaryDirectory() as scratch:
        stage=Path(scratch)/'dist'
        web = root/'web'
        if web.is_symlink() or any(p.is_symlink() for p in web.rglob('*')):
            raise ValueError('Unexpected symlink in web assets')
        shutil.copytree(web,stage)
        template=(stage/'index.html').read_text()
        paths=[]

        def publish(path,title,heading,desc,body,home=False):
            prefix='../'*path.count('/') if path else './'
            nav=a(prefix,'Maple Label','brand') + '<div>'+a(prefix+'records/','Browse records')+a(prefix+'records/label-guide/','Label guide')+'</div>'
            footer=a('https://coolcode.ca/','CoolCode.ca')+a(prefix+'data/catalogue.json','Download the data')+a('https://coolcode.ca/labelcompare/','Compare nutrition labels')+a('https://coolcode.ca/report/?tool=maplelabel','Report a correction')
            head = '' if home else f'<link rel="canonical" href="{BASE+path}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">'
            values={'TITLE':e(title)+' · Maple Label','DESC':e(desc),'PREFIX':prefix,'NAV':nav,'FOOTER':footer,'BODY':body,'HEADING':e(heading),'META':head,'INTRO':e(desc),'SCRIPT':'<script type="module" src="./app.mjs"></script>' if home else ''}
            html=template
            for k,v in values.items():html=html.replace('{{'+k+'}}',v)
            if home:
                dataset={'@type':'Dataset','@id':BASE+'#products','name':tool['dataset']['title'],'description':tool['data_info']['detail'],'isBasedOn':[sources[k]['url'] for k in ('cfia','bureau')],'distribution':{'@type':'DataDownload','contentUrl':BASE+tool['dataset']['file'],'encodingFormat':'application/json'}}
                html=add_search_metadata(html,tool,category='ReferenceApplication',datasets=[dataset])
            else:
                paths.append(path)
            folder=stage/path
            folder.mkdir(exist_ok=True,parents=True)
            (folder/'index.html').write_text(html,encoding='utf-8')

        def field_list(r):
            return '<dl class="facts">'+''.join(info(label,r[key]) for key,label in FIELDS)+'</dl>'

        dataset_date=e(data['reviewed_at'])
        summary=f'{len(products)} product records · Evidence reviewed {dataset_date}'
        checked=e(status['checked_at']) if status.get('checked_at') else 'awaiting a complete check'
        context=f'<p class="date">Evidence reviewed {dataset_date}. Last successful automated check of monitored wording: {checked}. Sources marked editorial are revisited separately.</p>'
        if status['needs_review']:
            context+=f'<p class="notice">{len(status["needs_review"])} monitored source(s) need review after the {e(status["last_attempt"])} check. The previous reviewed records remain available.</p>'
        feature='<section class="comparison" id="starting-example"><h2>Two Québec labels, two different promises</h2><div class="pair">'+''.join(card(p,'./') for p in (first,second))+'</div>'+a('records/quebec-cheese-and-coffee/','Read the side-by-side findings','action')+'</section>'
        filters='''<section id="finder" hidden><h2>Find a product</h2><form id="filters" hidden><label class="search">Product or brand<input type="search" id="query" placeholder="Try apple juice, maple or Rogers"></label><label>Province<select id="province"></select></label><label>Category<select id="category"></select></label><label>Claim or program<select id="rule"></select></label><button type="reset">Clear filters</button></form><div id="results" hidden><p id="count" role="status"></p><ul id="matches"></ul></div></section>
<section id="comparison" hidden><h2>Compare origin evidence</h2><div id="pickers"><label>First product<select id="product"></select></label><label>Compare with<select id="compare"></select></label></div><div class="pair" id="comparison-cards"></div></section>'''
        intro='Find out where a product’s ingredients came from, where it was made and what its origin claim actually covers.'
        opening='<p class="opening-links">'+a('./records/quebec-cheese-and-coffee/','Compare OKA cheese and Laval-roasted coffee','action')+' '+a('./records/','Browse all '+str(len(products))+' records')+'</p>'
        publish('',tool['task_label'],'Made in Canada finder',intro,opening+filters+feature+f'<p class="date">{summary}.</p>'+context,True)
        groupings={}
        for r in products.values():groupings.setdefault(r['category'],[]).append(r)
        body='<p>'+a('../','Search and compare products','action')+'</p>'+a('label-guide/','Read the label definitions')
        body+=' · '+a('quebec-cheese-and-coffee/','Québec cheese and coffee compared')
        for category,rows in sorted(groupings.items()):
            body+=f'<section><h2>{e(category)}</h2><div class="cards">'+''.join(card(row,'../') for row in rows)+'</div></section>'
        publish('records/','Canadian product-origin records by category','Product-origin records',f'Browse {len(products)} named products by category. Each record links to the producer or program that published the claim.',body+context)
        compare_body='<div class="pair">'
        for item in (first,second):
            p=products[item['id']]
            compare_body+='<article class="card"><h2>'+a('../'+p['id']+'/',p['name'])+'</h2><p class="origin-label">'+e(p['claim'])+'</p>'+field_list(p)+links(p,sources,status)+'</article>'
        compare_body+='</div><p>'+a('../../?product='+first['id']+'&compare='+second['id']+'#comparison','Compare these or choose other products','action')+'</p>'+context
        compare_body += ('<section><h2>How does green coffee reach Canada?</h2><p>'
                         + a('https://coolcode.ca/importtrail/records/hs-090111/', 'Explore Canadian imports of unroasted coffee')
                         + ' to see which companies appear in the federal trade data. The figures cover the Canadian market as a whole. '
                         + 'The espresso’s product record identifies where the beans were roasted.</p></section>')
        publish('records/quebec-cheese-and-coffee/','OKA cheese and Laval-roasted espresso compared','What is local in cheese and coffee?','OKA Original’s Québec certification covers its main ingredients. Hortus espresso’s certification covers processing, and its listing identifies the roasting location as Laval.',compare_body)
        definitions=''
        for rule in rules.values():
            linked=[p for p in products.values() if p['rule']==rule['id']]
            definitions+=f'<section id="{rule["id"]}"><h2>{e(rule["name"])}</h2><p>{e(rule["description"])}</p>'
            if rule['source']:
                s=sources[rule['source']]
                definitions+='<p>'+a(s['url'],s['name'])+'</p>'
            if linked:
                definitions+='<p>Product records · '+ ' · '.join(a('../../'+profile_url(p),p['name']) for p in linked)+'</p>'
            definitions+='</section>'
        definitions+='<section><h2>Does a barcode identify the country?</h2><p>A GS1 prefix identifies the organisation that allocated the number. The product can be made elsewhere. Use a barcode to identify an item, then look for a product-specific origin source.</p>'+a(sources['gs1']['url'],sources['gs1']['name'])+'</section>'
        publish('records/label-guide/','Product of Canada and Made in Canada label definitions','What Canadian origin labels mean','Food rules and non-food guidance use different tests. Provincial programs also set their own requirements.',definitions+context)
        for r in products.values():
            rule=rules[r['rule']]
            body=f'<p class="origin-label">{e(r["claim"])}</p><p class="meta">{e(r["brand"])} · {e(r["category"])} · {e(r["province"] or "Canada · province unspecified")}</p>'
            body+='<section><h2>What the sources establish</h2>'+field_list(r)+'</section>'
            body+=f'<section><h2>{e(rule["name"])}</h2><p>{e(rule["description"])}</p>{a("../label-guide/#"+rule["id"],"See how this label compares with other claims")}</section>'
            body+='<section><h2>Read the source evidence</h2>'+links(r,sources,status)+context+'</section>'
            body+='<section><h2>Compare related records</h2><ul class="related">'
            for key in r['related']:
                p=products[key]
                body+=f'<li>{a("../"+key+"/",p["name"])}<span>{e(p["claim"])}</span>{a("../../?product="+r["id"]+"&compare="+key+"#comparison","Compare their evidence")}</li>'
            body+='</ul>'
            if r in (first,second):
                body+='<p>'+a('../quebec-cheese-and-coffee/','Read both Québec labels side by side')+'</p>'
            body+='</section><p>'+a('../../?product='+r['id']+'#comparison','Open this product in the finder')+' · '+a('../','All product records')+'</p>'
            publish(profile_url(r),r['name']+' · '+r['claim'],r['name'],r['summary'],body)
        sitemap=ET.Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
        for path in sorted(paths):
            ET.SubElement(ET.SubElement(sitemap,'url'),'loc').text=BASE+path
        ET.ElementTree(sitemap).write(stage/'sitemap.xml',encoding='utf-8',xml_declaration=True)
        (stage/'.nojekyll').touch()
        dest=root/'dist'
        if dest.is_symlink():raise ValueError('Unexpected dist symlink')
        if dest.exists():shutil.rmtree(dest)
        shutil.copytree(stage,dest)
    print(f'{len(products)} curated products, {len(paths)} sitemap records')


if __name__=='__main__':build()
