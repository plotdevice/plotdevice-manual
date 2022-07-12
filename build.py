#!./env/bin/python3
# encoding: utf-8
"""
build.py

Generate the PlotDevice Manual.

Created by Christian Swinehart on 2014/01/14.
Copyright (c) 2014 Samizdat Drafting Co. All rights reserved.
"""


import sys, os, re
import json
from os.path import basename, abspath, dirname, join, relpath, exists, getmtime, splitext
import importlib
py_root = dirname(abspath(__file__))
from socketserver import TCPServer, ThreadingMixIn
from http.server import SimpleHTTPRequestHandler as Handler
from collections import defaultdict as ddict, OrderedDict as odict
from glob import glob
from pprint import pprint
from subprocess import Popen, PIPE
from shutil import rmtree
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer, PythonConsoleLexer
from pygments.token import Punctuation, Keyword, Name, Number, Text, Comment
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup, NavigableString
file_urls=None

# src/toc.py holds the manual's section/chapter structure
sys.path.append('%s/src'%py_root)
import toc as ToC

# analytics
# ga = "<script>(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o), m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m) })(window,document,'script','//www.google-analytics.com/analytics.js','ga'); ga('create', 'UA-631520-4', 'auto'); ga('send', 'pageview');</script>"

### the big red button ###

def build(static=True):
  # if True, will make sure every link points to a valid .html file path
  # if False, hrefs are shortened: Line+Color.html#fill() -> Line+Color#fill()
  print("Building %s...\n" %('manual' if static else 'website'))
  global file_urls
  file_urls = static
  toc()
  etc()
  ref()
  tut()
  lib()

### http server with live rebuilds ###

class PlotDoxServer(ThreadingMixIn, TCPServer):
    # Ctrl-C will cleanly kill all spawned threads
    daemon_threads = True
    # much faster rebinding
    allow_reuse_address = True

    def __init__(self, host, port):
        print("Live version of the manual at http://127.0.0.1:%i/doc/manual.html"%PORT)
        TCPServer.__init__(self, (host, port), PlotDoxHandler)

class PlotDoxHandler(Handler):
  def do_GET(self):
    # run the build script before every pageload
    if self.path.endswith('.html'):
      print("regen for", self.path)
      sys.stdout, _out = open('/dev/null','w'), sys.stdout
      build()
      # sys.stdout = _out
    Handler.do_GET(self)

### utilities ###

_mkdir = lambda pth: os.path.exists(pth) or os.makedirs(pth)

def parse(fn):
  return BeautifulSoup(open(fn, encoding='utf-8').read(), "html5lib")

def tidy(html):
  # swap our html5-isms for html2-isms (so htmltidy won't refuse to cooperate)
  # html = html.replace("<nav","<object").replace("</nav","</object")
  # html = html.replace("<footer","<embed").replace("</footer","</embed")
  # HTMLTIDY = '/usr/bin/tidy -q -i -w 1000 --doctype "html" -utf8 -omit -f /dev/null'.split()
  # tidy = Popen(HTMLTIDY, stdin=PIPE, stdout=PIPE)
  # (out, err) = tidy.communicate(html.encode('utf-8'))

  # # swap the fake tags back to their real nav/footer identities
  # markup = "\n".join(out.decode('utf-8').split("\n"))
  # markup = markup.replace("<object","<nav").replace("</object","</nav")
  # markup = markup.replace("<embed","<footer").replace("</embed","</footer")

  markup = html


  soup = BeautifulSoup(markup, "html5lib")
  for spam in soup.find_all('meta'):
    if spam.get('name')=='generator':
      spam.extract()

  # build cleaner '.html'-less urls if flagged
  if not file_urls:
    for a in soup.find_all('a'):
      href = a.get('href','')
      if not href: continue
      if '.html' in href and not href.startswith('http'):
        a['href'] = re.sub(r'\.html(?=#|$)', '', href)

  # htmltidy leaves things too loose for my taste. step though all the
  # elts and zap any double-newlines outside of <pre> tags
  for tag in soup.find_all(recursive=True):
    for child in tag.children:
      rents = [p.name for p in child.parents]
      if type(child) is NavigableString and 'pre' not in rents:
        if 'table' in rents or 'ul' in rents or 'p' in rents:
          child.replace_with(child.replace('\n\n','\n'))

  # smarten up quotes
  for tag in soup.find_all(recursive=True):
    for child in tag.children:
      rents = [p.name for p in child.parents]
      if type(child) is NavigableString and 'pre' not in rents and 'script' not in rents and 'code' not in rents:
        if "'" in child or '"' in child:
          # child.replace_with(child.replace(u"'",u"’").replace(u' "',u" “").replace(u'"',u'”'))
          child.replace_with(child.replace("'","’").replace(' "'," ‘").replace('"','’'))

  # run all of the python blocks through pygments
  for pre in soup.find_all('pre'):
    pre_class = pre.get('class',())
    if 'shell' in pre_class or 'manual' in pre_class:
      continue
    pre.replace_with(syntax_color(pre.text))

  # close <p> and </pre> at the end of the line rather than on a new one
  html = re.sub(r'\n( +)</p><',r'</p>\n\1<', str(soup))
  html = re.sub(r'\n( +)</li><',r'</li>\n\1<', html)
  # html = re.sub(r'<pre><',r'<pre>\n<', html)
  # html = re.sub(r'( +)<pre>',r'<pre>', html)
  # html = re.sub(r'\n</pre>',r'</pre>\n', html)
  html = re.sub(r'<body([^>]*)>',r'\n<body\1>\n', html)
  # if not file_urls:
  #   html = re.sub(r'</head>','  %s\n</head>'%ga, html)
  return html

def is_stale(dst, src, deps=[], quiet=False):
  if isinstance(src, str):
    src = (src,)

  # print src, deps
  # print getmtime(src), [getmtime(dst), tuple([getmtime(d) for d in deps])]
  newest = max(max(getmtime(s) for s in src), max(getmtime(d) for d in deps))
  stale = not exists(dst) or getmtime(dst) < newest
  if stale or not quiet:
    print(">" if stale else '-', namify(dst))
  return stale

def namify(fn):
  if fn.endswith('.html'):
    fn = fn[:-5]
  return basename(fn).replace('_',' ').replace('+',' & ')

def absify(rel, href):
  reldir, relfn = dirname(rel), basename(rel)
  if href.startswith('#'):
    return join(reldir, relfn+href)
  elif href.startswith('.'):
    return relpath(join(reldir,href), '.')
  elif href.startswith('http'):
    return href
  return relpath(join(reldir, href), '.')

def get_def(fn):
  soup = parse(fn)
  sect = soup.find('div', class_='definition')
  return namify(fn), sect

def get_sect(fn):
  soup = parse(fn)
  sect = soup.find('div', class_='section')
  return namify(fn), sect

def syntax_color(src):
  html = highlight(src, PlotDeviceLexer(), HtmlFormatter())
  soup = BeautifulSoup(html, 'html5lib')
  return soup.find_next('pre').extract()

class PlotDeviceLexer(PythonLexer):
  """A Python lexer recognizing PlotDevice builtins, classes, and constants."""

  name, aliases = 'PlotDevice', ['plotdevice']

  # override the mimetypes to not inherit them from python
  mimetypes = []
  filenames = []

  EXTRA_CLASSES = [
    'Bezier', 'BezierPath', 'Color', 'Curve', 'Effect', 'Family', 'Font',
    'Gradient', 'Grob', 'Image', 'Mask', 'PathElement', 'Pattern', 'Point',
    'Region', 'Shadow', 'Size', 'Stylesheet', 'Text', 'Transform', 'Variable',
    'halt', # not really a class, but should get extra-highlighted
    'adict', 'ddict', 'odict',
    ]
  EXTRA_CONSTS = [
    'BEVEL', 'BOOLEAN', 'BUTT', 'BUTTON', 'CENTER', 'CLOSE', 'CMYK', 'CORNER',
    'CURVETO', 'DEFAULT', 'DEGREES', 'FORTYFIVE', 'FRAME', 'GREY', 'HEIGHT', 'HSB', 'HSV',
    'JUSTIFY', 'KEY_BACKSPACE', 'KEY_DOWN', 'KEY_ESC', 'KEY_LEFT', 'KEY_RIGHT',
    'KEY_TAB', 'KEY_UP', 'LEFT', 'LINETO', 'MITER', 'MOUSEX', 'MOUSEY', 'mousedown',
    'MOVETO', 'NORMAL', 'NUMBER',
    'PAGENUM', 'PERCENT', 'RADIANS', 'RGB', 'RIGHT', 'ROUND', 'SQUARE', 'TEXT', 'WIDTH',
    'cm', 'inch', 'mm', 'pi', 'pica', 'px', 'tau']
  EXTRA_BUILTINS = [
    'align', 'alpha', 'arc', 'arcto', 'arrow', 'autoclosepath', 'autotext',
    'background', 'beginclip', 'beginpath', 'bezier', 'blend', 'canvas',
    'capstyle', 'choice', 'clear', 'clip', 'closepath', 'color', 'colormode',
    'colorrange', 'curveto', 'drawpath', 'ellipse', 'endclip', 'endpath',
    'export', 'files', 'fill', 'findpath', 'font', 'fonts', 'fontsize',
    'geometry', 'grid', 'image', 'imagesize', 'joinstyle', 'layout', 'line', 'lineheight',
    'lineto', 'mask', 'measure', 'moveto', 'nofill', 'noshadow', 'nostroke',
    'order', 'ordered', 'outputmode', 'oval', 'paginate', 'pen', 'plot', 'poly',
    'pop', 'push', 'random', 'read', 'rect', 'reset', 'rotate', 'scale', 'shadow',
    'shuffled', 'size', 'skew', 'speed', 'star', 'stroke', 'strokewidth',
    'stylesheet', 'text', 'textheight', 'textmetrics', 'textpath', 'textwidth',
    'transform', 'translate', "var", 'ximport']

  def get_tokens_unprocessed(self, text):
    for index, token, value in PythonLexer.get_tokens_unprocessed(self, text):
      if token is Name and value in self.EXTRA_CLASSES:
        yield index, Name.Class, value
      elif token is Name and value in self.EXTRA_BUILTINS:
        yield index, Name.Function, value
      elif token is Name and value in self.EXTRA_CONSTS:
        yield index, Keyword.Constant, value
      elif token in (Name,Punctuation):
        yield index, Text, value
      else:
        yield index, token, value
PlotDeviceLexer.tokens['root'].insert(0, (r'^>>>.*$', Comment),)


### handlers for each section of the site ###

tmpls = Environment(loader=FileSystemLoader('%s/tmpl'%py_root))

def etc():
  # hardlink all the media files so we're not shuffling around megs
  # of images on every run (yes i know, whole MEGAbytes)
  # if not exists('doc/etc/ref'):
  _mkdir('doc/etc/type')
  os.system('ln -f src/etc/type/* doc/etc/type')
  os.system('ln -f tmpl/manual.css doc/etc/manual.css')
  os.system('ln -f tmpl/toc.css doc/etc/toc.css')
  os.system('ln -f tmpl/typography.css doc/etc/type/typography.css')
  os.system('ln -f src/etc/cash.min.js doc/etc/cash.min.js')
  for sect in ('ref','tut','lib'):
    _mkdir('doc/etc/%s'%sect)
    os.system('ln -f src/etc/%s/* doc/etc/%s'%(sect,sect))

def toc():
  print("Table of Contents")
  toc = importlib.reload(ToC)
  html = tmpls.get_template('toc.html')
  local = dict(isinstance=isinstance, tuple=tuple, len=len, sorted=sorted)
  info = dict(ref=toc.ref, tut=toc.tut, lib=toc.lib, **local)
  markup = html.render(info)

  _mkdir('doc')
  with open('doc/manual.html', 'w', encoding='utf-8') as f:
    f.write(tidy(markup))

def ref():
  print("\nReference")
  _mkdir('doc/ref')

  # collapse the last two ToC categories into a single page
  siblings = list(list(importlib.reload(ToC).ref.keys()))[:-2] + ["Misc"]

  for page in glob('src/ref/*'):
    name = basename(page)
    fname = 'doc/ref/%s.html' % name

    if is_stale(fname, glob('%s/*/*.html'%page), deps=['tmpl/nav.html','tmpl/manpage.html']):
      cmd, typ, old = [list(map(get_def, sorted(glob('%s/%s/*'%(page,s))))) for s in ('commands','types','compat')]
      html = tmpls.get_template('manpage.html')
      info = dict(name=name, sect='ref', siblings=siblings, commands=cmd, types=typ, compat=old)

      push = '<a name="push()"></a>'
      pushpop = push + '<a name="pop()"></a>'
      markup = html.render(info).replace(push, pushpop)
      with open(fname, 'w', encoding='utf-8') as f:
        f.write(tidy(markup))

def tut():
  print("\nTutorials")
  _mkdir('doc/tut')

  siblings = sum(list(list(importlib.reload(ToC).tut.values())), [])

  html = tmpls.get_template('manpage.html')
  for tut in sorted(glob('src/tut/*.html')):
    api = namify(tut)
    tut_name = basename(tut)[:-5]
    fname = 'doc/tut/%s.html'%tut_name
    if is_stale(fname, tut, deps=['tmpl/nav.html','tmpl/manpage.html']):
      soup = BeautifulSoup(open(tut, encoding='utf-8').read(), "html5lib")
      article = soup.find('div', class_='article')
      article['class'] = 'tut article'
      info = dict(name=api, doc=article, sect='tut', siblings=siblings, tutorial=tut_name)
      markup = html.render(info)
      with open(fname, 'w', encoding='utf-8') as f:
        f.write(tidy(markup))


def lib():
  print("\nLibraries")
  _mkdir('doc/lib')

  in_sub = False
  html = tmpls.get_template('manpage.html')
  for lib in sorted(glob('src/lib/*.html') + glob('src/lib/*/*.html')):
    fname = 'doc/lib/' + lib.replace('src/lib/','')
    pg_name = basename(fname).replace('.html','')
    subdir = dirname(fname)!='doc/lib'

    if is_stale(fname, lib, quiet=subdir, deps=['tmpl/nav.html','tmpl/manpage.html']):
      _mkdir(dirname(fname))
      soup = BeautifulSoup(open(lib, encoding='utf-8').read(), "html5lib")
      article = soup.find('div', class_='article')
      article['class'] = 'lib article'
      api = namify(fname)

      info = dict(name=api, doc=article, sect='lib', root='../' if subdir else '')
      markup = html.render(info)
      with open(fname, 'w', encoding='utf-8') as f:
        f.write(tidy(markup))

def code():
  _mkdir('doc/etc/code')

  corpus = {}
  for example in glob('../plotdevice/examples/*/*.pv'):
    cat=basename(dirname(example))
    title=splitext(basename(example))[0]
    raw = open(example, encoding='utf-8').read()
    m = re.match(r'\s*"""(.*?)"""', raw, re.S)

    docstring = m.group(1).strip()
    src = raw[m.end():].strip()
    code = syntax_color(src).encode('utf-8')

    doc = [p.encode('utf-8') for p in m.group(1).strip().split('\n\n')]
    headline = doc.pop(0).rstrip('.')
    sidebar = '<p>'+ "</p><p>".join(doc) + "</p>"
    corpus[title] = dict(code=code, head=headline, doc=sidebar)

  with open('doc/etc/code/index.json','w') as f:
    json.dump(corpus, f)



### first-pass toc generator ###

def scan_toc():
  # dump out the contents of the src/ref folders for a first pass at setting up the `ref` dict
  ref_sects = {}
  for page in glob('src/ref/*'):
    cmd, typ, old = [[basename(x)[:-5] for x in glob('%s/%s/*'%(page,s))] for s in ('commands','types','compat')]
    sect = basename(page)
    ref_sects[sect] = (cmd, typ, old)
  ref = {}
  for sect in 'Canvas','Line+Color','Typography','Transform','Primitives','Drawing','Utility':
    print(sect, ":", dict(list(zip(('commands','types','compat'),ref_sects[sect]))))
    ref[sect] = dict(list(zip(('commands','types','compat'),ref_sects[sect])))
  print(ref)

### post-build validation ###

def check_media():
  print("\nMissing Images")
  outs = []
  media = ddict(list)
  for fn in glob('doc/*/*.html') + glob('doc/*/*/*.html'):
    # print fn
    soup = parse(fn)
    for elt in soup.select('[src]'):
      src = absify(fn, elt['src'])
      if src.startswith('http'):
        outs.append(src)
      elif src:
        media[src].append(fn)

  # broken images
  for fn,info in list(media.items()):
    if not os.path.exists(fn):
      print("!",fn,'<-',info)

  # unused images
  # css=["doc/etc/ref/transparency-grid.png","doc/etc/ref/blend-modes.png"]
  # used = [pth for pth in media.keys()+css if pth.startswith('doc')]
  # extant = [fn for fn in glob('doc/etc/*/*.*') if splitext(fn)[1] not in ['.css','.ttf','.json','.csv']]
  # stale = [fn for fn in extant if fn not in used]
  # pprint(sorted(stale))


def check_links():
  print("\nMissing Links")
  outs = []
  refs = ddict(lambda: ddict(set))

  for fn in glob('doc/*/*.html') + glob('doc/*/*/*.html'):
    # print fn
    soup = parse(fn)
    for link in soup.select('[href]'):
      href = link['href']
      url = absify(fn, href)
      if url.startswith('http'):
        outs.append(url)
      else:
        if '#' in url:
          pg, anchor = url.split('#')
          refs[pg]['anchors'].add('#'+anchor)
          url = pg
        refs[url]['refrs'].add(fn)
      # print "- %s :: <%s>" % (url, link['href'])
  refs = {k:dict((kind, sorted(lst)) for kind, lst in list(v.items())) for k,v in list(refs.items())}

  # broken links
  for fn,info in sorted(refs.items()):
    if not os.path.exists(fn):
      print("!",fn,'<-',info['refrs'])

def code_blocks():
  lexx = PlotDeviceLexer()
  yack = HtmlFormatter()
  render = lambda src: highlight(src, lexx, yack)
  importlib.reload(__main__)
  classes = set()
  for fn in glob('doc/*/*.html') + glob('doc/*/*/*.html'):
    soup = parse(fn)
    print(fn)
    for pre in soup.find_all('pre'):
      # print pre.text
      # print render(pre.text)
      out = render(pre.text)
      classes.update(re.findall(r'class="(.*?)"', out))
      # print out.encode('utf-8'),
      print(pre.attrs)
      print('-----------------------------')
      # print '.',
    # print
  print(classes)

  print(yack.get_style_defs())

def zap():
  os.system('rm -rf %s/doc/*'%py_root)

def ensite():
  """
  Creates the site-hosted version of the docs at <sitedir>/www/manual.html and zips up
  a static version at <sitedir>/www/extras/plotdevice-docs.zip
  """
  cwd = os.getcwd()
  os.chdir(py_root)
  code()

  # build & install hosted copy (with cleaner urls)
  zap()
  build(static=False)
  if exists('../plotdevice-site/www/etc'):
    for fn in glob('doc/etc/*'):
      print('sync', fn)
      os.system('rsync -avq %s ../plotdevice-site/www/etc/'%fn)

  if exists('../plotdevice-site'):
    for fn in 'ref','tut','lib','manual.html':
      print('sync', fn)
      os.system('rsync -avq doc/%s ../plotdevice-site/www/'%fn)

  landing = open('doc/manual.html', encoding='utf-8').read().replace('href="http://plotdevice.io"','href="/"',1)
  with open('../plotdevice-site/www/manual.html', 'w', encoding='utf-8') as f:
    f.write(landing)

  # build & install plotdevice-docs.zip
  if exists('../plotdevice-site/www/extras'):
    zap()
    build(static=True)
    os.rename('doc','plotdevice-docs')
    os.system('ditto -ck --keepParent plotdevice-docs plotdevice-docs.zip')
    rmtree('plotdevice-docs')
    os.system('mv plotdevice-docs.zip ../plotdevice-site/www/extras/plotdevice-docs.zip')

  os.chdir(cwd)

if __name__=='__main__':
  if 'live' in sys.argv:
    HOST, PORT = "", 9099
    httpd = PlotDoxServer(HOST, PORT)
    try:
      httpd.serve_forever(.1)
    except KeyboardInterrupt:
      sys.exit(0)
  elif 'clean' in sys.argv:
    zap()
  elif 'ensite' in sys.argv:
    ensite()
  else:
    build(static='site' not in sys.argv)

  if 'tests' in sys.argv:
    from detest import make_tests
    make_tests()


  # check_media()
  # check_links()
  # code_blocks()

