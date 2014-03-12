#!./env/bin/python
# encoding: utf-8
"""
build.py

Created by Christian Swinehart on 2014/01/14.
Copyright (c) 2014 Samizdat Drafting Co All rights reserved.
"""

from __future__ import with_statement, division
import sys
import os
import re
from pdb import set_trace as tron
from collections import defaultdict as ddict
from collections import OrderedDict as odict
py_root = os.path.dirname(os.path.abspath(__file__))
_mkdir = lambda pth: os.path.exists(pth) or os.makedirs(pth)

from urllib2 import quote, unquote
from os.path import basename, dirname, join, relpath, exists
from glob import glob
from bs4 import BeautifulSoup, NavigableString
from pprint import pprint
from subprocess import Popen, PIPE

HTMLTIDY = '/usr/bin/tidy -q -i -w 100 -utf8 -omit -f /dev/null'.split()


from jinja2 import Environment, FileSystemLoader
tmpls = Environment(loader=FileSystemLoader('%s/tmpl'%py_root))

def parse(fn):
  return BeautifulSoup(file(fn).read().decode('utf-8'), "html5lib")

def tidy(html):
  tidy = Popen(HTMLTIDY, stdin=PIPE, stdout=PIPE)
  (out, err) = tidy.communicate(html.encode('utf-8'))
  markup = u"\n".join(out.decode('utf-8').split(u"\n"))
  soup = BeautifulSoup(markup, "html5lib")
  for spam in soup.find_all('meta'):
    if spam.get('name')=='generator':
      spam.extract()

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

def get_sect(fn):
  soup = parse(fn)
  sect = soup.find('div', class_='section')
  return namify(fn), sect

def ref():
  print "\nReference"
  _mkdir('build/ref')

  for page in glob('src/ref/*'):
    cmd, typ, old = [map(get_sect, glob('%s/%s/*'%(page,s))) for s in ('commands','types','compat')]
    sect = basename(page)
    # print sect, map(len, (cmd, typ, old))
    print "-", sect

    html = tmpls.get_template('reference.html')
    fname = 'build/ref/%s.html' % sect
    siblings = ["Setup", "Primitives", "Drawing", "Line+Color", "Typography", "Utility"]
    info = dict(name=sect, commands=cmd, types=typ, compat=old, siblings=siblings)
    markup = html.render(info)
    with file(fname, 'w') as f:
      f.write(tidy(markup).encode('utf-8'))

def tut():
  print "\nTutorials"
  _mkdir('build/tut')

  html = tmpls.get_template('article.html')
  for tut in sorted(glob('src/tut/*.html')):
    soup = BeautifulSoup(file(tut).read().decode('utf-8'), "html5lib")
    article = soup.find('div', class_='article')
    api = namify(tut)
    tut_name = basename(tut)[:-5]
    print "-", api

    fname = 'build/tut/%s.html'%tut_name
    info = dict(name=api, doc=article, sect='tut', tutorial=tut_name)
    markup = html.render(info)
    with file(fname, 'w') as f:
      f.write(tidy(markup).encode('utf-8'))

def lib():
  print "\nLibraries"
  _mkdir('build/lib')

  in_sub = False
  html = tmpls.get_template('article.html')
  for lib in sorted(glob('src/lib/*.html') + glob('src/lib/*/*.html')): 
    fname = 'build/lib/' + lib.replace('src/lib/','')
    _mkdir(dirname(fname))

    pg_name = basename(fname).replace('.html','')
    subdir = dirname(fname)!='build/lib'
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
  ref=odict()

  # ref_sects = {}
  # for page in glob('src/ref/*'):
  #   cmd, typ, old = [map(lambda x:basename(x)[:-5], glob('%s/%s/*'%(page,s))) for s in ('commands','types','compat')]
  #   sect = basename(page)
  #   ref_sects[sect] = (cmd, typ, old)
  # for sect in 'Setup','Line+Color','Typography','Transform','Primitives','Drawing','Utility':
  #   print sect, ":", dict(zip(('commands','types','compat'),ref_sects[sect]))
  #   ref[sect] = dict(zip(('commands','types','compat'),ref_sects[sect]))
  # print ref

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

  with file('build/manual.html', 'w') as f:
    f.write(tidy(markup).encode('utf-8'))

def etc():
  for sect in ('ref','tut','lib'):
    _mkdir('build/etc/%s'%sect)
    os.system('ln -f src/etc/%s/* build/etc/%s'%(sect,sect))
    os.system('ln -f tmpl/manual.css build/etc/manual.css')
    os.system('ln -f src/etc/zepto.min.js build/etc/zepto.min.js')

if __name__=='__main__':
  etc()
  ref()
  tut()
  lib()
  toc()
