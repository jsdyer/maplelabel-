import json
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build import BASE, ROOT, build, validate
from check_sources import checked, inspect


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.urls, self.canonicals, self.descriptions = [], [], []
        self.feed(path.read_text())

    def handle_starttag(self,t,attrs):
        a=dict(attrs)
        if t=='a' and 'href' in a:self.urls.append(a['href'])
        if t=='link' and a.get('rel')=='canonical':self.canonicals.append(a['href'])
        if t=='meta' and a.get('name')=='description':self.descriptions.append(a['content'])


class Records(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'web',self.root/'web')
        shutil.copyfile(ROOT/'tool.json',self.root/'tool.json')
        self.data=json.loads((self.root/'web/data/catalogue.json').read_text())
        self.status=json.loads((self.root/'web/data/status.json').read_text())

    def test_full_build_has_one_canonical_and_discoverable_sources(self):
        build(self.root)
        site=self.root/'dist';urls={e[0].text for e in ET.parse(site/'sitemap.xml').getroot()}
        self.assertIn(BASE+'records/',urls)
        self.assertEqual(len(urls),len(self.data['products'])+3)
        visited=set();queue=[BASE+'records/']
        while queue:
            u=queue.pop()
            if u in visited:continue
            page=Page(site/u[len(BASE):]/'index.html');visited.add(u)
            self.assertEqual(page.canonicals,[u]);self.assertEqual(len(page.descriptions),1)
            for href in page.urls:
                parsed=urlsplit(urljoin(u,href))
                clean=parsed._replace(query='',fragment='').geturl()
                if clean in urls:queue.append(clean)
                if clean.startswith(BASE):
                    target=site/clean[len(BASE):]
                    self.assertTrue(target.exists(),(u,href))
        self.assertEqual(visited,urls)
        self.assertEqual(Page(site/'index.html').canonicals,[BASE])
        comparison=(site/'records/quebec-cheese-and-coffee/index.html').read_text()
        self.assertIn('Aliments préparés au Québec',comparison)
        self.assertIn('roast',comparison.lower())
        self.assertIn('https://alimentsduquebec.com/',comparison)

    def test_new_product_flows_into_live_choices_and_static_records(self):
        new=deepcopy(self.data['products'][0])
        new.update(id='future-item',name='Future <item>',related=['oka-original'])
        self.data['products'].append(new)
        self.status['product_count']+=1
        for filename,data in [('catalogue.json',self.data),('status.json',self.status)]:
            (self.root/'web/data'/filename).write_text(json.dumps(data))
        build(self.root)
        self.assertIn('Future &lt;item&gt;', (self.root/'dist/records/future-item/index.html').read_text())
        self.assertIn('future-item/', (self.root/'dist/sitemap.xml').read_text())

    def test_bad_related_link_and_untrusted_url_rejected(self):
        self.data['products'][0]['related']=['not-a-real-product']
        with self.assertRaises(ValueError):validate(self.data,self.status)
        self.data['sources'][0]['url']='javascript:alert(1)'
        with self.assertRaisesRegex(ValueError,'source'):validate(self.data,self.status)


class SourceChecks(unittest.TestCase):
    def test_failed_or_changed_source_never_advances_success_date(self):
        data={'reviewed_at':'2026-10-01','products':[{}],'sources':[
            {'id':'site','mode':'scheduled','url':'A','anchors':['grown in Québec']},
            {'id':'manual','mode':'editorial','url':'B','anchors':['ignored']}]}
        def failed(url):raise OSError('offline')
        for getter in [failed,lambda u:'<script>grown in Québec</script>']:
            status=checked(data,{'checked_at':'2026-10-09'},'2026-11-10',get=getter)
            self.assertEqual(status['checked_at'],'2026-10-09')
            self.assertEqual(status['needs_review'],['site'])
        restored=checked(data,status,'2026-11-12',get=lambda u:'<p>Grown in <b>Québec</b></p>')
        self.assertEqual(restored['checked_at'],'2026-11-12')
        self.assertEqual(restored['reviewed_at'],'2026-10-01')
        self.assertEqual(restored['editorial_sources'],1)
        self.assertTrue(inspect({'url':'A','anchors':['Made in Canada']},lambda u:'<img alt="Made in Canada">'))
