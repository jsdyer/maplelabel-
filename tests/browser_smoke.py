"""Check exact product selection, published evidence and script-free navigation."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json, os, threading, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*_):pass

def main():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp)/'maplelabel').symlink_to(ROOT/'dist',target_is_directory=True)
        handler=partial(Quiet,directory=tmp);server=ThreadingHTTPServer(('127.0.0.1',0),handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        data=json.loads((ROOT/'dist/data/catalogue.json').read_text())
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'))
                for width in (390,1280):
                    context=browser.new_context(viewport={'width':width,'height':844})
                    page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                    home=f'http://127.0.0.1:{server.server_port}/maplelabel/'
                    page.goto(home)
                    expect(page.locator('#count')).to_contain_text(str(len(data['products']))+' of')
                    assert page.locator('#query').bounding_box()['y'] < 844
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    page.locator('#query').fill('espresso')
                    page.locator('#province').select_option('Quebec')
                    expect(page.locator('#matches li')).to_have_count(1)
                    page.locator('#matches button').click()
                    expect(page.locator('#product')).to_have_value('balanced-espresso')
                    page.reload();expect(page.locator('#product')).to_have_value('balanced-espresso')
                    page.locator('#compare').select_option('oka-original')
                    expect(page.locator('#comparison-cards')).to_contain_text('Laval')
                    page.locator('#comparison-cards article').first.get_by_role('link',name='Sources and product record').click()
                    expect(page.locator('h1')).to_have_text('Balanced Espresso Coffee Beans')
                    page.get_by_role('link',name='Read both Québec labels side by side').click()
                    expect(page.locator('h1')).to_contain_text('cheese and coffee')
                    assert not errors,errors
                    out=ROOT/'browser-checks';out.mkdir(exist_ok=True)
                    page.screenshot(path=str(out/f'evidence-{width}.png'))
                    context.close()
                plain=browser.new_page(java_script_enabled=False,viewport={'width':390,'height':844})
                plain.goto(home);plain.get_by_role('link',name='Browse records',exact=True).click()
                plain.get_by_role('link',name='Fleur de Sel, 90 g',exact=True).click()
                expect(plain.locator('main')).to_contain_text('St. Margaret’s Bay')
                plain.get_by_role('link',name='Maple Syrup Leaf Bottle',exact=True).click()
                expect(plain.locator('main')).to_contain_text('Authentic Seacoast')
                assert plain.evaluate('document.documentElement.scrollWidth <= innerWidth')
                browser.close()
        finally:
            server.shutdown()
    print('Passed finder, filters, restored comparison, linked records, mobile and no-script browsing')

if __name__=='__main__':main()
