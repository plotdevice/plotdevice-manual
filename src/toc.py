from collections import OrderedDict as odict

ref=odict()
ref['Canvas'] = {
    'commands': ['size()', 'speed()', 'background()', 'geometry()', 'export()', 'plot()', 'clear()', ],
    'types': ['Constants'],
    'compat': ['outputmode()', 'ximport()'] }
ref['Line+Color'] = {
    'commands': ['color()', 'stroke()', 'fill()', 'pen()', ],
    'types': ['Color', ], # 'Gradient',
    'compat': ['capstyle()', 'colormode()', 'joinstyle()', 'nofill()', 'nostroke()', 'strokewidth()'] }
ref['Primitives'] = {
    'commands': ['image()', 'rect()',  'oval()', 'poly()', 'arc()', 'line()',  ],
    'types': ['Image'],
    'compat': ['arrow()', 'star()'] }
ref['Drawing'] = {
    'commands': ['bezier()', 'moveto()', 'lineto()', 'arcto()', 'curveto()',  ],
    'types': ['Bezier', 'Curve'],
    'compat': ['autoclosepath()', 'beginpath()', 'drawpath()', 'endpath()', 'findpath()'] }
ref['Transform'] = {
    'commands': ['transform()', 'translate()', 'rotate()', 'scale()', 'skew()', 'reset()', ],
    'types': ['Transform'],
    'compat': ['pop()', 'push()'] }
ref['Compositing'] = {
    'commands': ['alpha()', 'blend()', 'shadow()', ('clip()', 'mask()'), ],
    'types': ['Shadow', ],
    'compat': ['noshadow()', 'beginclip()', 'endclip()', ] }
ref['Typography'] = {
    'commands': ['font()', 'text()', 'align()', 'stylesheet()'],
    'types': ['Family', 'Font', 'Stylesheet', 'Text'],
    'compat': ['fontsize()', 'lineheight()', 'textheight()', 'textmetrics()', 'textpath()', 'textwidth()'] }
# grouped into Misc.html
ref['Entropy'] = {
    'commands': ['random()', 'choice()', 'shuffled()', 'ordered()', 'grid()',  ],
    'types': [ 'dictionaries', ],
    'compat': ['autotext()', ] }
ref['Utility'] = {
    'commands': ['read()', 'measure()', 'files()', 'fonts()', 'var()',],
    'types': ['Point', 'Size', 'Region', ],
    'compat': ['imagesize()', 'open()', ] }


tut=odict()
tut['Basics']=["Introduction", "Environment", "Primitives", "Graphics_State",]
tut['Specifics']=["Animation", u"Bezier_Paths", "Color", "Math",]
tut['Data']=["Variables", "Lists", "Strings", "Serialization"]
tut['Structure']=["Repetition", "Commands", "Libraries", "Classes",]
tut['Advanced']=["Interaction", "Extending", "Scripting", "plotdevice",]

lib=odict()
lib['Design']=["Colors", "Grid", "Pixie", "Fatpath",]
lib['Pixels']=["Core Image", "iSight", "Quicktime",]
lib['Paths']=["Cornu", "SVG", "Supershape", "Bezier Editor",]
lib['I/O']=["Web", "Database", "WiiNode", "TUIO", ] # OSC
lib['Systems']=["Boids", "Ants", "L-system", "Noise",]
lib['Words']=["WordNet", "Keywords", "Graph", "Linguistics", "Perception",]
