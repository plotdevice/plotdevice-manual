#!./env/bin/python
# encoding: utf-8
"""
build.py

Generate the PlotDevice Manual.

Created by Christian Swinehart on 2014/01/14.
Copyright (c) 2014 Samizdat Drafting Co. All rights reserved.
"""

from __future__ import with_statement, division
from os.path import basename, abspath, dirname, join, relpath, exists, getmtime
py_root = dirname(abspath(__file__))
import sys, os, re
from SocketServer import TCPServer, ThreadingMixIn
from SimpleHTTPServer import SimpleHTTPRequestHandler as Handler
from collections import defaultdict as ddict, OrderedDict as odict
from glob import glob
from pprint import pprint
from subprocess import Popen, PIPE
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer
from pygments.token import Punctuation, Keyword, Name, Number, Text
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup, NavigableString

### the big red button ###

def build(static=True):
  # if True, will make sure every link points to a valid .html file path
  # if False, hrefs are shortened: Line+Color.html#fill() -> Line+Color#fill()
  print "Building %s...\n" %('manual' if static else 'website')
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
        print "Live version of the manual at http://127.0.0.1:%i/doc/manual.html"%PORT
        TCPServer.__init__(self, (host, port), PlotDoxHandler)

class PlotDoxHandler(Handler):
  def do_GET(self):
    # run the build script before every pageload
    if self.path.endswith('.html'):
      print "regen for", self.path
      sys.stdout, _out = file('/dev/null','w'), sys.stdout
      build()
      sys.stdout = _out
    Handler.do_GET(self)

### utilities ###

_mkdir = lambda pth: os.path.exists(pth) or os.makedirs(pth)

def parse(fn):
  return BeautifulSoup(file(fn).read().decode('utf-8'), "html5lib")

def tidy(html):
  HTMLTIDY = '/usr/bin/tidy -q -i -w 100 --doctype "html" -utf8 -omit -f /dev/null'.split()
  tidy = Popen(HTMLTIDY, stdin=PIPE, stdout=PIPE)
  (out, err) = tidy.communicate(html.encode('utf-8'))
  markup = u"\n".join(out.decode('utf-8').split(u"\n"))
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
          child.replace_with(child.replace(u'\n\n',u'\n'))

  # smarten up quotes
  for tag in soup.find_all(recursive=True):
    for child in tag.children:
      rents = [p.name for p in child.parents]
      if type(child) is NavigableString and 'pre' not in rents and 'script' not in rents:
        if "'" in child or '"' in child:
          # child.replace_with(child.replace(u"'",u"’").replace(u' "',u" “").replace(u'"',u'”'))
          child.replace_with(child.replace(u"'",u"’").replace(u' "',u" ‘").replace(u'"',u'’'))

  # run all of the python blocks through pygments
  for pre in soup.find_all('pre'):
    if 'shell' in pre.get('class',()):
      continue
    pre.replace_with(syntax_color(pre.text))

  # close <p> and </pre> at the end of the line rather than on a new one
  html = re.sub(r'\n( +)</p><',r'</p>\n\1<', unicode(soup))
  html = re.sub(r'\n( +)</li><',r'</li>\n\1<', html)
  html = re.sub(r'<pre><',r'<pre>\n<', html)
  # html = re.sub(r'\n</pre>',r'</pre>\n', html)
  html = re.sub(r'( +)<pre>',r'<pre>', html)
  html = re.sub(r'<body><',r'<body>\n  <', html)
  return html

def is_stale(dst, src, deps=[], quiet=False):
  if isinstance(src, basestring):
    src = (src,)

  # print src, deps
  # print getmtime(src), [getmtime(dst), tuple([getmtime(d) for d in deps])]
  newest = max(max(getmtime(s) for s in src), max(getmtime(d) for d in deps))
  stale = not exists(dst) or getmtime(dst) < newest
  if stale or not quiet:
    print ">" if stale else '-', namify(dst)
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

  EXTRA_CLASSES = set("adict|odict|ddict|BezierPath|ClippingPath|Color|Context|Family|Font|Stylesheet|Grob|Image|NodeBoxError|Oval|PathElement|Point|Rect|Text|Transform|TransformContext|Variable".split("|"))
  EXTRA_BUILTINS = set("clear|plot|measure|stylesheet|order|ordered|shuffled|addvar|align|arrow|autoclosepath|autotext|background|beginclip|beginpath|bezier|canvas|capstyle|choice|clip|closepath|color|colormode|colorrange|colors|curveto|drawpath|ellipse|endclip|endpath|export|files|fill|findpath|findvar|font|fonts|fontsize|grid|image|imagesize|joinstyle|line|lineheight|lineto|moveto|pen|plotstyle|nofill|nostroke|outputmode|oval|pop|push|random|rect|reset|rotate|save|scale|size|skew|speed|star|state_vars|stroke|strokewidth|text|textheight|textmetrics|textpath|textwidth|transform|translate|var|ximport".split('|'))
  EXTRA_CONSTS = set("DEFAULT|FRAME|PAGE|BEVEL|BOOLEAN|BUTT|BUTTON|CENTER|CLOSE|CMYK|CORNER|CURVETO|DEFAULT_HEIGHT|DEFAULT_WIDTH|FORTYFIVE|HEIGHT|HSB|JUSTIFY|KEY_BACKSPACE|KEY_DOWN|KEY_ESC|KEY_LEFT|KEY_RIGHT|KEY_TAB|KEY_UP|LEFT|LINETO|MITER|MOVETO|NORMAL|NUMBER|RGB|GREY|RIGHT|ROUND|SQUARE|TEXT|WIDTH|DEGREES|RADIANS|PERCENT|cm|inch|mm|pi|tau".split('|'))

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

### handlers for each section of the site ###

tmpls = Environment(loader=FileSystemLoader('%s/tmpl'%py_root))

def etc():
  # hardlink all the media files so we're not shuffling around megs
  # of images on every run (yes i know, whole MEGAbytes)
  if not exists('doc/etc/ref'):
    _mkdir('doc/etc/type')
    os.system('ln -f src/etc/type/* doc/etc/type')
    os.system('ln -f tmpl/manual.css doc/etc/manual.css')
    os.system('ln -f tmpl/typography.css doc/etc/type/typography.css')
    os.system('ln -f src/etc/zepto.min.js doc/etc/zepto.min.js')
    for sect in ('ref','tut','lib'):
      _mkdir('doc/etc/%s'%sect)
      os.system('ln -f src/etc/%s/* doc/etc/%s'%(sect,sect))

def toc():
  print "Table of Contents"
  print "- Reference"
  ref=odict()
  ref['Canvas'] = {
      'commands': ['canvas()', 'speed()', 'background()', 'export()', 'clear()', 'plot()',],
      'types': ['Constants'],
      'compat': ['outputmode()', 'size()'] }
  ref['Primitives'] = {
      'commands': ['image()', 'rect()',  'oval()', 'poly()', 'line()', ],
      'types': ['Image'],
      'compat': ['arrow()', 'star()'] }
  ref['Drawing'] = {
      'commands': ['bezier()', 'moveto()', 'lineto()', 'arcto()', 'curveto()', ],
      'types': ['Bezier', 'Curve'],
      'compat': ['autoclosepath()', 'beginclip()', 'beginpath()', 'drawpath()', 'endclip()', 'endpath()', 'findpath()'] }
  ref['Line+Color'] = {
      'commands': ['plotstyle()', 'stroke()', 'fill()', 'pen()', 'color()'],
      'types': ['Color', 'Gradient', 'Pattern'],
      'compat': ['capstyle()', 'colormode()', 'joinstyle()', 'nofill()', 'nostroke()', 'strokewidth()'] }
  ref['Transform'] = {
      'commands': ['transform()', 'translate()', 'rotate()', 'scale()', 'skew()', 'reset()', ],
      'types': ['Transform'],
      'compat': ['pop()', 'push()'] }
  ref['Compositing'] = {
      'commands': ['effects()','alpha()', 'blend()', 'shadow()', 'clip()', ],
      'types': ['Shadow', ],
      'compat': ['noshadow()',] }
  ref['Typography'] = {
      'commands': ['font()', 'text()', 'align()', 'stylesheet()'],
      'types': ['Family', 'Font', 'Stylesheet', 'Text'],
      'compat': ['fontsize()', 'lineheight()', 'textheight()', 'textmetrics()', 'textpath()', 'textwidth()'] }
  ref['Utility'] = {
      'commands': ['read()', 'grid()', 'measure()', ('files()', 'fonts()'), ('random()', 'choice()'), ('shuffled()', 'ordered()')],
      'types': ['Point', 'Size', 'Region', None, 'dictionaries', ],
      'compat': ['imagesize()', 'autotext()', 'open()'] }

  print "- Tutorials"
  tut=odict()
  tut['Basics']=["Introduction", "Environment", "Primitives", "Graphics_State",]
  tut['Specifics']=["Animation", u"Bezier_Paths", "Color", "Math",]
  tut['Data']=["Variables", "Lists", "Strings", "Serialization"]
  tut['Structure']=["Repetition", "Commands", "Libraries", "Classes",]
  tut['Advanced']=["Interaction", "Extending", "Scripting", "plotdevice",]

  print "- Libraries"
  lib=odict()
  lib['Design']=["Colors", "Grid", "Pixie", "Fatpath",]
  lib['Pixels']=["PhotoBot", "Core Image", "iSight", "Quicktime",]
  lib['Paths']=["Cornu", "SVG", "Supershape", "Bezier Editor",]
  lib['Bytes']=["Database", "Web", ]
  lib['Words']=["WordNet", "Keywords", "Graph", "Linguistics", "Perception",]
  lib['Systems']=["Boids", "Ants", "L-system", "Noise",]
  lib['Tangible']=["WiiNode", "TUIO", "OSC ",]

  html = tmpls.get_template('manual.html')
  local = dict(isinstance=isinstance, tuple=tuple, len=len)
  info = dict(ref=ref, tut=tut, lib=lib, **local)
  markup = html.render(info)

  _mkdir('doc')
  with file('doc/manual.html', 'w') as f:
    f.write(tidy(markup).encode('utf-8'))

def ref():
  print "\nReference"
  _mkdir('doc/ref')

  for page in glob('src/ref/*'):
    sect = basename(page)
    fname = 'doc/ref/%s.html' % sect
    if is_stale(fname, glob('%s/*/*.html'%page), deps=['tmpl/nav.html','tmpl/reference.html']):
      cmd, typ, old = [map(get_sect, glob('%s/%s/*'%(page,s))) for s in ('commands','types','compat')]
      html = tmpls.get_template('reference.html')
      info = dict(name=sect, commands=cmd, types=typ, compat=old)
      markup = html.render(info)
      with file(fname, 'w') as f:
        f.write(tidy(markup).encode('utf-8'))

def tut():
  print "\nTutorials"
  _mkdir('doc/tut')

  html = tmpls.get_template('article.html')
  for tut in sorted(glob('src/tut/*.html')):
    api = namify(tut)
    tut_name = basename(tut)[:-5]
    fname = 'doc/tut/%s.html'%tut_name
    if is_stale(fname, tut, deps=['tmpl/nav.html','tmpl/article.html']):
      soup = BeautifulSoup(file(tut).read().decode('utf-8'), "html5lib")
      article = soup.find('div', class_='article')
      info = dict(name=api, doc=article, sect='tut', tutorial=tut_name)
      markup = html.render(info)
      with file(fname, 'w') as f:
        f.write(tidy(markup).encode('utf-8'))

def lib():
  print "\nLibraries"
  _mkdir('doc/lib')

  in_sub = False
  html = tmpls.get_template('article.html')
  for lib in sorted(glob('src/lib/*.html') + glob('src/lib/*/*.html')):
    fname = 'doc/lib/' + lib.replace('src/lib/','')
    pg_name = basename(fname).replace('.html','')
    subdir = dirname(fname)!='doc/lib'

    if is_stale(fname, lib, quiet=subdir, deps=['tmpl/nav.html','tmpl/article.html']):
      _mkdir(dirname(fname))
      soup = BeautifulSoup(file(lib).read().decode('utf-8'), "html5lib")
      article = soup.find('div', class_='article')
      api = namify(fname)

      info = dict(name=api, doc=article, sect='lib', root='../' if subdir else '')
      markup = html.render(info)
      with file(fname, 'w') as f:
        f.write(tidy(markup).encode('utf-8'))

### first-pass toc generator ###

def scan_toc():
  # dump out the contents of the src/ref folders for a first pass at setting up the `ref` dict
  ref_sects = {}
  for page in glob('src/ref/*'):
    cmd, typ, old = [map(lambda x:basename(x)[:-5], glob('%s/%s/*'%(page,s))) for s in ('commands','types','compat')]
    sect = basename(page)
    ref_sects[sect] = (cmd, typ, old)
  ref = {}
  for sect in 'Canvas','Line+Color','Typography','Transform','Primitives','Drawing','Utility':
    print sect, ":", dict(zip(('commands','types','compat'),ref_sects[sect]))
    ref[sect] = dict(zip(('commands','types','compat'),ref_sects[sect]))
  print ref

### post-build validation ###

def check_media():
  print "\nMissing Images"
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
  for fn,info in media.items():
    if not os.path.exists(fn):
      print "!",fn,'<-',info

def check_links():
  print "\nMissing Links"
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
  refs = {k:dict((kind, sorted(lst)) for kind, lst in v.items()) for k,v in refs.items()}

  # broken links
  for fn,info in sorted(refs.items()):
    if not os.path.exists(fn):
      print "!",fn,'<-',info['refrs']

def code_blocks():
  lexx = PlotDeviceLexer()
  yack = HtmlFormatter()
  render = lambda src: highlight(src, lexx, yack)
  reload(__main__)
  classes = set()
  for fn in glob('doc/*/*.html') + glob('doc/*/*/*.html'):
    soup = parse(fn)
    print fn
    for pre in soup.find_all('pre'):
      # print pre.text
      # print render(pre.text)
      out = render(pre.text)
      classes.update(re.findall(r'class="(.*?)"', out))
      # print out.encode('utf-8'),
      print pre.attrs
      print '-----------------------------'
      # print '.',
    # print
  print classes

  print yack.get_style_defs()


if __name__=='__main__':
  if 'live' in sys.argv:
    HOST, PORT = "", 9099
    httpd = PlotDoxServer(HOST, PORT)
    try:
      httpd.serve_forever(.1)
    except KeyboardInterrupt:
      sys.exit(0)

  else:
    build(static=not sys.argv[1:] or sys.argv[1]!='site')

  # check_media()
  # check_links()
  # code_blocks()