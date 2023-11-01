"""
This script parses a token.xml file, collects the picURLs within, and replaces
the URLs to Scryfall cards with up-to-date URLs by querying Scryfall's API.
"""

from xml.sax import saxutils, make_parser, handler
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import itertools
import json
import sys
import time
import os
import tempfile
import pathlib
import shutil

SCRYFALL_MAX_LIST_SIZE = 75

def cards_collection(identifiers):
    """
    Get information about a set of cards using the Scryfall API.

    This simply returns a list of dictionaries representing the Card objects as
    returned by the /card/collection Scryfall API.

    If the list of identifiers is larger than Scryfall's API limit,
    cards_collection automatically splits the list into smaller chunks and
    makes multiple requests.
    """

    start_time = 0
    n = 0
    while n < len(identifiers):
        chunk = identifiers[n:n + SCRYFALL_MAX_LIST_SIZE]
        print("Requesting chunk {}-{}/{}...".format(n, n + len(chunk), len(identifiers)))
        n += SCRYFALL_MAX_LIST_SIZE

        payload = json.dumps({'identifiers': chunk}).encode('utf-8')
        req = Request('https://api.scryfall.com/cards/collection', payload,
                      headers={'Content-Type': 'application/json'})

        # Rate limiting
        cur_time = time.time()
        delta_time = cur_time - start_time
        if delta_time < 0.1:
            time.sleep(0.1 - delta_time)
        start_time = time.time()

        with urlopen(req) as f:
            list_obj = json.load(f)
            assert not list_obj.get('has_more', False)
            assert 'warnings' not in list_obj

            yield from list_obj['data']

def parse_picurl(picurl):
    """
    Parse a Scryfall picURL into its components.

    The Scryfall picURL must be in one of those forms:

        - https://c1.scryfall.com/file/scryfall-cards/<version>/<face>/*/*/<uuid>.jpg
        - https://cards.scryfall.io/<version>/<face>/*/*/<uuid>.jpg

    If it is, a dictionary with keys 'uuid', 'version' and 'face' is returned.
    Otherwise, an empty dictionary is returned.
    """

    obj = {}
    urlinfo = urlsplit(picurl)
    if urlinfo.netloc == 'c1.scryfall.com':
        parts = urlinfo.path.split('/')
        obj['version'] = parts[3]
        obj['face'] = parts[4]
        obj['uuid'] = parts[-1].rsplit('.')[0]
    elif urlinfo.netloc == 'cards.scryfall.io':
        parts = urlinfo.path.split('/')
        obj['version'] = parts[1]
        obj['face'] = parts[2]
        obj['uuid'] = parts[-1].rsplit('.')[0]
    return obj

class URLCollector(handler.ContentHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.urls = []

    def startElement(self, name, attrs):
        if name == 'set' and 'picURL' in attrs:
            obj = parse_picurl(attrs['picURL'])
            if obj:
                assert 'uuid' in obj
                self.urls.append(obj)

class URLRewriter(handler.LexicalHandler, saxutils.XMLGenerator):
    def __init__(self, images, **kwargs):
        super().__init__(**kwargs)

        self._images = images
        self.started = False

    def startElement(self, name, attrs):
        self.started = True

        if name == 'set' and 'picURL' in attrs:
            obj = parse_picurl(attrs['picURL'])
            if 'uuid' in obj and obj['uuid'] in self._images:
                new_url = self._images[obj['uuid']][obj['face']][obj['version']]
                if parse_picurl(new_url) != obj:
                    raise RuntimeError(
                        "URL `{}` was rewritten to `{}` that no longer resolves to the same card (hint: update parse_picurl).".format(
                            attrs['picURL'], new_url))
                attrs = dict(attrs, picURL=new_url)

        super().startElement(name, attrs)

    def endDocument(self):
        super().endDocument()
        self._write('\n')

    def comment(self, content):
        self.ignorableWhitespace('<!--{}-->{}'.format(content, '' if self.started else '\n'))

def collect_urls(fname):
    parser = make_parser()
    uc = URLCollector()
    parser.setContentHandler(uc)
    parser.parse(fname)
    return uc.urls

def rewrite_urls(fname, images, *, out=None):
    parser = make_parser()
    ur = URLRewriter(images, out=out, encoding='UTF-8')
    parser.setContentHandler(ur)
    parser.setProperty(handler.property_lexical_handler, ur)
    parser.parse(fname)

def main(fname, *, out=None):
    urls = collect_urls(fname)
    identifiers = {obj['uuid'] for obj in urls}
    identifiers = [{'id': uuid} for uuid in identifiers]

    images = {}
    for card in cards_collection(identifiers):
        assert card['id'] not in images

        if 'image_uris' in card:
            images[card['id']] = {'front': card['image_uris']}

        else:
            assert 'card_faces' in card and len(card['card_faces']) == 2
            images[card['id']] = {
                'front': card['card_faces'][0]['image_uris'],
                'back': card['card_faces'][1]['image_uris'],
            }

    rewrite_urls(fname, images, out=out)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Helper script to refresh scryfall image URLs')
    parser.add_argument('filename', nargs='?', default='tokens.xml')

    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument('--output', '-o')
    output_group.add_argument('--inplace', '-i', action='store_true')

    ns = parser.parse_args()

    if ns.inplace:
        outpath = pathlib.Path(ns.filename)
    else:
        outpath = pathlib.Path(ns.output)
    fd, temppath = tempfile.mkstemp(dir=outpath.parent)

    try:
        main(ns.filename, out=os.fdopen(fd, mode='w+b'))
        os.replace(temppath, outpath)
    except:
        os.unlink(temppath)
        raise
