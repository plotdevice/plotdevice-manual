from collections import OrderedDict as odict

ref=odict()
ref['Canvas'] = {
    'commands': ['size()', 'speed()', 'background()', 'geometry()', 'export()', ('plot()', 'clear()'), ],
    'compat': ['outputmode()', 'ximport()', 'halt()'] }
ref['Line+Color'] = {
    'commands': ['color()', 'stroke()', 'fill()', 'pen()', ],
    'types': ['Color', 'Gradient', 'Shadow'],
    'compat': ['capstyle()', 'colormode()', 'joinstyle()', 'nofill()', 'nostroke()', 'strokewidth()'] }
ref['Primitives'] = {
    'commands': [('poly()', 'rect()'),  ('arc()', 'oval()'), 'line()', 'image()', 'text()', ],
    'compat': ['arrow()', 'star()'] }
ref['Drawing'] = {
    'commands': ['bezier()', 'moveto()', 'lineto()', 'arcto()', 'curveto()',  ],
    'types': ['Bezier', 'Curve', 'Image', 'Context'],
    'compat': ['autoclosepath()', 'beginpath()', 'drawpath()', 'endpath()', 'findpath()'] }
ref['Transform'] = {
    'commands': ['transform()', 'translate()', 'rotate()', 'scale()', 'skew()', 'reset()', ],
    'types': ['Point', 'Size', 'Region', 'Transform'],
    'compat': ['pop()', 'push()'] }
ref['Compositing'] = {
    'commands': ['alpha()', 'blend()', 'shadow()', ('clip()', 'mask()'), ],
    'compat': ['noshadow()', 'beginclip()', 'endclip()', ] }
ref['Typography'] = {
    'commands': [ 'font()', 'layout()', 'stylesheet()', 'paginate()', 'textpath()', ],
    'types': ['Text', 'TextBlock', 'TextFragment', ('Font', 'Family') ],
    'compat': ['align()', 'fontsize()', 'lineheight()', 'textheight()', 'textmetrics()', 'textwidth()'] }
# grouped into Misc.html
ref['Utility'] = {
    'commands': ['read()', 'measure()', 'files()', 'fonts()', 'var()',],
    'types': ['constants', 'dictionaries'],
    'compat': ['imagesize()', 'open()', ] }
ref['Entropy'] = {
    'commands': ['random()', 'choice()', 'shuffled()', 'ordered()', 'grid()',  ],
    'compat': ['autotext()', ] }


tut=odict()
tut['Basics']=["Getting_Started", "Environment", "Primitives", "Graphics_State",]
tut['Specifics']=["Color", "Geometry", u"Bezier_Paths", "Typography", ]
tut['Data']=["Variables", "Strings", "Collections", "Serialization"]
tut['Structure']=["Repetition", "Commands", "Classes", "Libraries", ]
tut['Advanced']=["Animation", "Interaction", "Console", "Cocoa",]

lib=odict()
lib['Design']=["Colors", "Grid", "Pixie", "Fatpath",]
lib['Pixels']=["Core Image", "iSight", "Quicktime",]
lib['Paths']=["Cornu", "SVG", "Supershape", "Bezier Editor",]
lib['I/O']=["Web", "Database", "WiiNode", "TUIO", ] # OSC
lib['Systems']=["Boids", "Ants", "L-system", "Noise",]
lib['Words']=["WordNet", "Keywords", "Graph", "Linguistics", "Perception",]
