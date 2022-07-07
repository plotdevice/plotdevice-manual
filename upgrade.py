import sys, os, re
from glob import glob
from pprint import pprint
from os.path import abspath, basename, dirname, exists
from collections import Counter, defaultdict as ddict, OrderedDict as odict
from subprocess import call, check_output, PIPE
_root = dirname(abspath(__file__))
_mkdir = lambda pth: exists(pth) or os.makedirs(pth)

import html

def run_2to3(m):
  fn = 'conv/src.py'
  src = html.unescape(m.group(1))

  responses = []
  def obfuscate(m):
    placeholder = '_p_l_a_c_e_h_o_l_d_e_r_%i_'%len(responses)
    responses.append(m.group(1))
    return placeholder
  def deobfuscate(m):
    return responses[int(m.group(1))]

  to_be_updated = re.sub(r'^(>>>.*)$', obfuscate, src, 0, re.M)
  with open(fn, 'w', encoding='utf8') as f:
    f.write(to_be_updated)

  try:
    check_output([sys.executable, '-m', 'lib2to3', '--write', fn], stderr=PIPE)
    print("👍")
  except Exception as e:
    print('=====================================================================')
    print("SKIP")
    print(to_be_updated)
    # print('---------------------------------------------------------------------')
    return '<pre>%s</pre>' % m.group(1)

  with open(fn, encoding='utf8') as f:
    updated = re.sub(r'_p_l_a_c_e_h_o_l_d_e_r_(\d+)_', deobfuscate, f.read())
    print("=" if updated==src else "👍")
    # return '<pre>%s</pre>' % html.escape(updated, quote=False)
    return '<pre>%s</pre>' % updated

def main():
  _mkdir('conv')
  for fn in glob('src/tut/*.html') + glob('src/ref/*/*/*.html'):
    print(fn)
    src = open(fn, encoding='utf-8').read()
    mod = re.sub(r'<pre>(.*?)</pre>', run_2to3, src, 0, re.S)
    with open(fn, 'w', encoding='utf-8') as f:
      f.write(mod)


if __name__ == '__main__':
  main()