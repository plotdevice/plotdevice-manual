#!./env/bin/python
# encoding: utf-8
"""
build.py

Generate the PlotDevice Manual. 

Created by Christian Swinehart on 2014/01/14.
Copyright (c) 2014 Samizdat Drafting Co. All rights reserved.
"""

from __future__ import with_statement, division
from os.path import basename, abspath, dirname, join, relpath, exists
py_root = dirname(abspath(__file__))
import sys, os, re
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
  global file_urls
  file_urls = static
  etc()
  ref()
  tut()
  lib()
  toc()

### utilities ###

_mkdir = lambda pth: os.path.exists(pth) or os.makedirs(pth)

def parse(fn):
  return BeautifulSoup(file(fn).read().decode('utf-8'), "html5lib")

def tidy(html):
  HTMLTIDY = '/usr/bin/tidy -q -i -w 100 -utf8 -omit -f /dev/null'.split()
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
  html = re.sub(r'<pre><',r'<pre>\n<', html)
  # html = re.sub(r'\n</pre>',r'</pre>\n', html)
  html = re.sub(r'( +)<pre>',r'<pre>', html)
  html = re.sub(r'<body><',r'<body>\n  <', html)
  return html
  # return BeautifulSoup(html.decode('utf-8'), "html5lib")

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
  """
  A Python lexer recognizing PlotDevice builtins, classes, and constants.
  """

  name = 'PlotDevice'
  aliases = ['plotdevice']

  # override the mimetypes to not inherit them from python
  mimetypes = []
  filenames = []

  EXTRA_CLASSES = set("adict|odict|ddict|BezierPath|ClippingPath|Color|Context|Family|Font|Stylesheet|Grob|Image|NodeBoxError|Oval|PathElement|Point|Rect|Text|Transform|TransformContext|Variable".split("|"))
  EXTRA_BUILTINS = set("plot|measure|stylesheet|order|ordered|shuffled|addvar|align|arrow|autoclosepath|autotext|background|beginclip|beginpath|bezier|canvas|capstyle|choice|clip|closepath|color|colormode|colorrange|colors|curveto|drawpath|ellipse|endclip|endpath|export|files|fill|findpath|findvar|font|fonts|fontsize|grid|image|imagesize|joinstyle|line|lineheight|lineto|moveto|pen|plotstyle|nofill|nostroke|outputmode|oval|pop|push|random|rect|reset|rotate|save|scale|size|skew|speed|star|state_vars|stroke|strokewidth|text|textheight|textmetrics|textpath|textwidth|transform|translate|var|ximport".split('|'))
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



### handlers each section of the site ###

tmpls = Environment(loader=FileSystemLoader('%s/tmpl'%py_root))

def etc():
  # hardlink all the media files so we're not shuffling around megs
  # of images on every run (yes i know, whole MEGAbytes)
  for sect in ('ref','tut','lib'):
    _mkdir('doc/etc/%s'%sect)
    os.system('ln -f src/etc/%s/* doc/etc/%s'%(sect,sect))
    os.system('ln -f tmpl/manual.css doc/etc/manual.css')
    os.system('ln -f src/etc/zepto.min.js doc/etc/zepto.min.js')

def ref():
  print "\nReference"
  _mkdir('doc/ref')

  for page in glob('src/ref/*'):
    cmd, typ, old = [map(get_sect, glob('%s/%s/*'%(page,s))) for s in ('commands','types','compat')]
    sect = basename(page)
    # print sect, map(len, (cmd, typ, old))
    print "-", sect

    html = tmpls.get_template('reference.html')
    fname = 'doc/ref/%s.html' % sect
    siblings = ["Setup", "Primitives", "Drawing", "Line+Color", "Typography", "Utility"]
    info = dict(name=sect, commands=cmd, types=typ, compat=old, siblings=siblings)
    markup = html.render(info)
    with file(fname, 'w') as f:
      f.write(tidy(markup).encode('utf-8'))

def tut():
  print "\nTutorials"
  _mkdir('doc/tut')

  html = tmpls.get_template('article.html')
  for tut in sorted(glob('src/tut/*.html')):
    soup = BeautifulSoup(file(tut).read().decode('utf-8'), "html5lib")
    article = soup.find('div', class_='article')
    api = namify(tut)
    tut_name = basename(tut)[:-5]
    print "-", api

    fname = 'doc/tut/%s.html'%tut_name
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
    _mkdir(dirname(fname))

    pg_name = basename(fname).replace('.html','')
    subdir = dirname(fname)!='doc/lib'
    if subdir:
      if not in_sub:
        print "...",
      print pg_name.split('.',1)[-1],
      in_sub = True
    else:
      if in_sub:
        print
        in_sub = False
      print "-", pg_name

    soup = BeautifulSoup(file(lib).read().decode('utf-8'), "html5lib")
    article = soup.find('div', class_='article')
    api = namify(fname)

    info = dict(name=api, doc=article, sect='lib', root='../' if subdir else '')
    markup = html.render(info)
    with file(fname, 'w') as f:
      f.write(tidy(markup).encode('utf-8'))

def toc():

  # dump out the contents of the src/ref folders for a first pass at setting up the `ref` dict
  # 
  # ref_sects = {}
  # for page in glob('src/ref/*'):
  #   cmd, typ, old = [map(lambda x:basename(x)[:-5], glob('%s/%s/*'%(page,s))) for s in ('commands','types','compat')]
  #   sect = basename(page)
  #   ref_sects[sect] = (cmd, typ, old)
  # ref = {}
  # for sect in 'Setup','Line+Color','Typography','Transform','Primitives','Drawing','Utility':
  #   print sect, ":", dict(zip(('commands','types','compat'),ref_sects[sect]))
  #   ref[sect] = dict(zip(('commands','types','compat'),ref_sects[sect]))
  # print ref

  ref=odict()
  ref['Setup'] = {
      'commands': ['canvas()', 'speed()', 'export()', 'background()'], 
      'types': ['Constants'],
      'compat': ['outputmode()', 'size()'] }
  ref['Primitives'] = {
      'commands': ['image()', 'rect()',  'oval()', 'line()', 'arrow()', 'star()'], 
      'types': ['Image'],
      'compat': ['imagesize()'] }
  ref['Drawing'] = {
      'commands': ['plot()', 'bezier()', 'moveto()', 'lineto()', 'curveto()', 'clip()', ], 
      'types': ['BezierPath', 'PathElement'],
      'compat': ['autoclosepath()', 'beginclip()', 'beginpath()', 'drawpath()', 'endclip()', 'endpath()', 'findpath()'] }
  ref['Line+Color'] = {
      'commands': ['plotstyle()', 'color()', 'pen()', 'fill()', 'stroke()', 'shadow()'], 
      'types': ['Color', 'Gradient'],
      'compat': ['capstyle()', 'colormode()', 'joinstyle()', 'nofill()', 'nostroke()', 'strokewidth()'] }
  ref['Typography'] = {
      'commands': ['font()', 'text()', 'align()', 'stylesheet()'], 
      'types': ['Family', 'Font', 'Stylesheet', 'Text'],
      'compat': ['fontsize()', 'lineheight()', 'textheight()', 'textmetrics()', 'textpath()', 'textwidth()'] }
  ref['Transform'] = {
      'commands': ['transform()', 'translate()', 'rotate()', 'scale()', 'skew()', 'reset()', ], 
      'types': ['Transform'],
      'compat': ['pop()', 'push()'] }
  ref['Utility'] = {
      'commands': ['read()', 'grid()', 'measure()', 'random()', ('choice()', 'shuffled()'), ('order()', 'ordered()'), ('files()', 'fonts()')], 
      'types': ['dictionaries'],
      'compat': ['autotext()', 'open()'] }

  tut=odict()
  tut['Basics']=["Introduction", "Environment", "Primitives", "Graphics_State",]
  tut['Data']=["Variables", "Lists", "Strings",]
  tut['Strategy']=["Repetition", "Commands", "Libraries", "Classes",]
  tut['Specifics']=["Animation", "Interaction", "Paths", "Color", "Math",]
  tut['Advanced']=["Extending", "Scripting", "plotdevice",]

  lib=odict()
  lib['Design']=["Colors", "Grid", "Pixie", "Fatpath",]
  lib['Pixels']=["PhotoBot", "Core Image", "iSight", "Quicktime",]
  lib['Paths']=["Cornu", "SVG", "Supershape", "Bezier Editor",]
  lib['Bytes']=["Database", "Web", ]
  lib['Words']=["WordNet", "Keywords", "Graph", "Linguistics", "Perception",]
  lib['Systems']=["Boids", "Ants", "L-system", "Noise",]
  lib['Tangible']=["WiiNode", "TUIO", "OSC ",]

  html = tmpls.get_template('manual.html')
  info = dict(ref=ref, tut=tut, lib=lib, isinstance=isinstance, tuple=tuple, len=len)
  markup = html.render(info)

  with file('doc/manual.html', 'w') as f:
    f.write(tidy(markup).encode('utf-8'))

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
  build(static=not sys.argv[1:] or sys.argv[1]!='site')
  check_media()
  check_links()
  # code_blocks()