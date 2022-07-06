#!./env/bin/python
# encoding: utf-8
"""
spellunk.py

Created by Christian Swinehart on 2014/03/21.
Copyright (c) 2014 Samizdat Drafting Co. All rights reserved.
"""

from __future__ import with_statement, division
from os.path import basename, abspath, dirname, join, relpath, exists, getmtime, splitext, normpath
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
import json

sys.path.append('%s/src'%py_root) # so we can pick up toc.py
from toc import ref
from build import parse

input_files = [ # files used as args within example code, rewrite to tests/_in/*
  "header.jpg", "plaid.png", "logo-stencil.png", "~/Pictures/triforce.png",
  "superfolia.jpg", "kant.xml", "~/macpaint-dark.png", "~/macpaint-thatch.png",
]
collations = { # group different sections into different tests/*.py files
  "Geometry": ["Transform", "Utility"],
  "Drawing": ["Bezier_Paths", "Line+Color", "Color", "Canvas"],
  "Misc": ["Commands", "Variables", "Entropy"]
}
skipped_images = [ # don't overwrite the copy in tests/_ref, it intentionally differs from the manual
  'test_color_gradients1', 'test_color_gradients2', 'test_color_gradients3', 'test_pathmatics_contours',
  'test_paths_flat_difference', 'test_paths_flat_intersect', 'test_paths_flat_union',
  'test_paths_flat_xor', 'test_paths_transform_post', 'test_paths_transform_pre',
  'test_math_angle', 'test_math_coordinates',
]
skipped_tests = ['test_var', 'test_math_trig7', 'test_paths_ctrl1']
skipped_cats = ['Misc']
skipped_code = ['goldenratio']

def _flatten(seq):
    return sum( ([x] if not isinstance(x, (list,tuple)) else list(x) for x in seq), [] )

def indent(code, n=1, end='\n', tab='    '):
  pad = tab*n
  lines = code.split('\n')
  return pad + ('\n'+pad).join(lines).encode('utf-8') + end

def flatten_strings(code):
  def oneline(multiline):
    return '"%s"'%multiline.group(1).replace('\n', r'\n').replace('"', r'\"')
  return re.sub(r'"""(.*?)"""', oneline, code, flags=re.S)

def categorized(fn):
  if '/ref/' in fn:
    cmd = splitext(basename(fn))[0]
    for cat, subcats in ref.items():
      fields = subcats.values()
      while not all(isinstance(f, basestring) for f in fields):
        fields = _flatten(fields)
      if cmd in fields:
        break
    else:
      print "uncategorizable", fn
  else:
    cat = splitext(basename(fn))[0]
  for parent, kids in collations.items():
    if cat in kids:
      return parent
  return cat

def skip(fn, case):
  if 'code' in case:
    print fn
    if 'code' in case:
      print indent(case['code'])
    print '-'*40
  else:
    print 'skip', fn


from PIL import Image
def parse_example(fn, eg):
  case = {}
  if eg.find('pre'):
    code = eg.find('pre').text.rstrip()
    code = re.sub(r'print ([\'\"].*)\n *>>> +(\S.+)\n', r'self.assertEqual(" ".join(map(str, [\1])), "\2")', code)
    code = re.sub(r'print (.*)\n *>>> +(\S+)', r'self.assertAlmostEqual(\1, \2)', code)
    code = re.sub(r'^(\s*)\.\.\.(\s*)$', r'\1# ...\2', code, flags=re.M)
    for infile in input_files:
      code = code.replace(infile, 'tests/_in/%s'%basename(infile))
    case['code'] = flatten_strings(code)
    # case['code'] = eg.find('pre').text.rstrip().replace('>>>','# >>>')
  if eg.find('img'):
    pth = normpath(join('doc/_____', eg.find('img')['src']))
    case['origin'] = relpath(fn, 'src').replace('.html','')
    case['img'] = pth
    case['test'] = 'test_%s'%splitext(basename(pth))[0].replace('-','_')
    case['size'] = Image.open(pth).size
  return case

def collect_examples():
  categories = ddict(list)

  for fn in glob('src/tut/*.html') + glob('src/ref/*/*/*.html'):
    category = categorized(fn)
    soup = parse(fn)
    for eg in soup.find_all('div', class_='example'):
      case = parse_example(fn, eg)

      if any(c in case.get('code','') for c in skipped_code):
        skip(fn, case)
      elif case.get('test') in skipped_tests or category in skipped_cats:
        skip(fn, case)
      elif 'code' in case and 'img' in case:
        categories[category].append(case)
      else:
        skip(fn, case)

  for cat, cases in categories.items():
    print '%2i'%len(cases), cat
  return categories

test_header = """# encoding: utf-8
import unittest
from . import PlotDeviceTestCase, reference
from plotdevice import *
\n"""

test_class = "class %sTests(PlotDeviceTestCase):\n"

test_footer = """
def suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(%sTests))
  return suite
"""

def make_tests():
  test_path = '%s/../plotdevice/tests'%py_root

  categories = collect_examples()
  for cat, cases in categories.items():
    img_path = '%s/_ref/%s'%(test_path, cat.lower())
    if not exists(img_path):
      os.makedirs(img_path)
    for case in cases:
      if case['test'] not in skipped_images:
        os.system('ln -f %s %s'%(case['img'], join(img_path, basename(case['img']))))

    with open('%s/%s.py'%(test_path, cat.lower()), 'w') as f:
      f.write(test_header)
      f.write(test_class%cat)
      for i, case in enumerate(cases):
        origin = '# %s'%case['origin']
        if 'tut/' in origin:
          origin += ' (%i)'%(i+1)
        f.write("    @reference('%s/%s')\n"%(cat.lower(), basename(case['img'])))
        f.write("    def %s(self):\n"%case['test'])
        f.write(indent(origin, 2))
        if not re.search(r'(^| )size\(', case['code'], re.M):
          f.write(indent('size(%i, %i)'%case['size'],2))
        f.write(indent(case['code'], 2, end='\n\n'))
      f.write(test_footer%cat)



if __name__=='__main__':
  make_tests()
