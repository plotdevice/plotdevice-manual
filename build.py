#!./env/bin/python
# encoding: utf-8
"""
build.py

Generate the PlotDevice Manual.

Created by Christian Swinehart on 2014/01/14.
Copyright (c) 2014 Samizdat Drafting Co. All rights reserved.
"""

from __future__ import with_statement, division
import sys, os, re
from os.path import basename, abspath, dirname, join, relpath, exists, getmtime
py_root = dirname(abspath(__file__))
from SocketServer import TCPServer, ThreadingMixIn
from SimpleHTTPServer import SimpleHTTPRequestHandler as Handler
from collections import defaultdict as ddict, OrderedDict as odict
from glob import glob
from pprint import pprint
from subprocess import Popen, PIPE
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
      if type(child) is NavigableString and 'pre' not in rents and 'script' not in rents and 'code' not in rents:
        if "'" in child or '"' in child:
          # child.replace_with(child.replace(u"'",u"’").replace(u' "',u" “").replace(u'"',u'”'))
          child.replace_with(child.replace(u"'",u"’").replace(u' "',u" ‘").replace(u'"',u'’'))

  # run all of the python blocks through pygments
  for pre in soup.find_all('pre'):
    if 'shell' in pre.get('class',()) or 'manual' in pre.get('class',()):
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
    'geometry', 'grid', 'image', 'imagesize', 'joinstyle', 'line', 'lineheight',
    'lineto', 'mask', 'measure', 'moveto', 'nofill', 'noshadow', 'nostroke',
    'order', 'ordered', 'outputmode', 'oval', 'pen', 'plot', 'poly', 'pop',
    'push', 'random', 'read', 'rect', 'reset', 'rotate', 'scale', 'shadow',
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
  os.system('ln -f src/etc/zepto.min.js doc/etc/zepto.min.js')
  for sect in ('ref','tut','lib'):
    _mkdir('doc/etc/%s'%sect)
    os.system('ln -f src/etc/%s/* doc/etc/%s'%(sect,sect))

def toc():
  print "Table of Contents"
  toc = reload(ToC)
  html = tmpls.get_template('toc.html')
  local = dict(isinstance=isinstance, tuple=tuple, len=len)
  info = dict(ref=toc.ref, tut=toc.tut, lib=toc.lib, **local)
  markup = html.render(info)

  _mkdir('doc')
  with file('doc/manual.html', 'w') as f:
    f.write(tidy(markup).encode('utf-8'))

def ref():
  print "\nReference"
  _mkdir('doc/ref')

  # collapse the last two ToC categories into a single page
  siblings = reload(ToC).ref.keys()[:-2] + ["Misc"]

  for page in glob('src/ref/*'):
    name = basename(page)
    fname = 'doc/ref/%s.html' % name
    if is_stale(fname, glob('%s/*/*.html'%page), deps=['tmpl/nav.html','tmpl/manpage.html']):
      cmd, typ, old = [map(get_def, glob('%s/%s/*'%(page,s))) for s in ('commands','types','compat')]

      html = tmpls.get_template('manpage.html')
      info = dict(name=name, sect='ref', siblings=siblings, commands=cmd, types=typ, compat=old)

      push = '<a name="push()"></a>'
      pushpop = push + '<a name="pop()"></a>'
      markup = html.render(info).replace(push, pushpop)
      with file(fname, 'w') as f:
        f.write(tidy(markup).encode('utf-8'))

def tut():
  print "\nTutorials"
  _mkdir('doc/tut')

  siblings = sum(reload(ToC).tut.values(), [])

  html = tmpls.get_template('manpage.html')
  for tut in sorted(glob('src/tut/*.html')):
    api = namify(tut)
    tut_name = basename(tut)[:-5]
    fname = 'doc/tut/%s.html'%tut_name
    if is_stale(fname, tut, deps=['tmpl/nav.html','tmpl/manpage.html']):
      soup = BeautifulSoup(file(tut).read().decode('utf-8'), "html5lib")
      article = soup.find('div', class_='article')
      article['class'] = 'tut article'
      info = dict(name=api, doc=article, sect='tut', siblings=siblings, tutorial=tut_name)
      markup = html.render(info)
      with file(fname, 'w') as f:
        f.write(tidy(markup).encode('utf-8'))

def lib():
  print "\nLibraries"
  _mkdir('doc/lib')

  in_sub = False
  html = tmpls.get_template('manpage.html')
  for lib in sorted(glob('src/lib/*.html') + glob('src/lib/*/*.html')):
    fname = 'doc/lib/' + lib.replace('src/lib/','')
    pg_name = basename(fname).replace('.html','')
    subdir = dirname(fname)!='doc/lib'

    if is_stale(fname, lib, quiet=subdir, deps=['tmpl/nav.html','tmpl/manpage.html']):
      _mkdir(dirname(fname))
      soup = BeautifulSoup(file(lib).read().decode('utf-8'), "html5lib")
      article = soup.find('div', class_='article')
      article['class'] = 'lib article'
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
  elif 'clean' in sys.argv:
    os.system('rm -r %s/doc/*'%py_root)

  else:
    build(static=not sys.argv[1:] or sys.argv[1]!='site')

  # check_media()
  # check_links()
  # code_blocks()