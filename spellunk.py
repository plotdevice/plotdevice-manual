#!./env/bin/python
# encoding: utf-8
"""
spellunk.py

Created by Christian Swinehart on 2014/03/21.
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

def reorg():
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
      'types': ['Color', 'Gradient'],
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
      'commands': ['read()', 'grid()', 'measure()', 'files()', 'fonts()', 'random()', 'choice()', 'shuffled()', 'ordered()'],
      'types': ['Point', 'Size', 'Region', 'dictionaries', ],
      'compat': ['imagesize()', 'autotext()', 'open()'] }

  tut=odict()
  tut['Basics']=["Introduction", "Environment", "Primitives", "Graphics_State",]
  tut['Specifics']=["Animation", u"Bézier Paths", "Color", "Math",]
  tut['Data']=["Variables", "Lists", "Strings", "Serialization"]
  tut['Structure']=["Repetition", "Commands", "Libraries", "Classes",]
  tut['Advanced']=["Interaction", "Extending", "Scripting", "plotdevice",]

  extant = {}
  for pth in glob('src/ref/*/*/*.html'):
    sect, group, api = [re.sub(r'\.html$','', s) for s in pth.split('/')[-3:]]
    extant[api] = (sect, group)

  preferred = {}
  for sect, groups in ref.items():
    for group, calls in groups.items():
      for api in calls:
        preferred[api] = (sect, group)



  for api in preferred:
    try:
      old = extant[api]
    except:
      old = "MISSING"
    new = preferred[api]
    if old!= new:
      print api, old,'->',new

  oldbook=["Introduction", "Environment", "Primitives", "Graphics_State", "Variables", "Lists", "Strings", "Repetition", "Commands", "Libraries", "Classes", "Animation", "Interaction", "Paths", "Color", "Math", "Extending", "Scripting", "plotdevice"]
  newbook = sum(tut.values(), [])
  for i in xrange(len(newbook)):
    print '%2i'%(i+1), oldbook[i] if oldbook[i:] else '<>', newbook[i].encode('utf-8')
  print newbook

if __name__=='__main__':
  reorg()