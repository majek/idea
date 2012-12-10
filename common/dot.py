import md5
import os
import png
import yaml
import sys

svg_disabled = False

defaults = {
    'height': 'auto',
    'width': 625,
    'descr': 'Diagram',
    'dpi': 72,
    'rankdir':'LR',
    }


join_attr = lambda attr:' '.join( '%s="%s"' % (k,v) for k, v in attr.iteritems())
join_style = lambda style:'; '.join( '%s: %s' % (k,v) for k, v in style) + ';'

# pyc -> py, pyo -> py
with open(sys.modules[__name__].__file__.rstrip('co'), 'r') as f:
    current_module_checksum = md5.new(f.read()).hexdigest()


def generate(content, dst_dir, leading):

    checksum = md5.new(current_module_checksum + content).hexdigest()

    t = content.split('--\n', 1)
    if len(t) == 1:
        yml_data, dot_data = ['', content]
    else:
        yml_data, dot_data = t
    ctx = dict(defaults)
    ctx['file'] = checksum
    ctx.update( yaml.load(yml_data) or {} )
    
    outfile = os.path.join(dst_dir, ctx['file'])

    required_ext = ['.dot', '.svg', '.png']
    if sum(os.path.isfile(outfile + ext) for ext in required_ext) < 3:
        do_generate(ctx, outfile, dot_data)
    else:
        print ' [.] %r already present' % (outfile + '.dot',)


    with open(outfile + '.png', 'r') as f:
        (width, height, _, _) = png.Reader(file=f).read()

    style = [
        ('width', '%spx' % (width,)),
        ('height', '%spx' % (height, )),
        ('padding-bottom', '%spx' % (leading - (height % leading),)),
        ]

    return '''<div class="svgimage"><img style="%s" src="%s.svg"></div>''' % (
        join_style(style), ctx['file'])


def do_generate(ctx, outfile, dot_data):
    with open(outfile + '.dot', 'w') as f:
        f.write(dot_data)

    opts = {
        'Gbgcolor':'transparent',
        'Gtruecolor':'true',
        'Grankdir': ctx['rankdir'],
        'Gfontname': '"Arial"',
        'Nfontname': '"Arial"',
        'Efontname': '"Arial"',
        'Gcolor': 'transparent', # box of subgraph
        }

    if ctx['height'] != 'auto':
        opts['Gsize'] = '"%.3f,%.3f"' % (int(ctx['width'])/96.0,
                                         int(ctx['height'])/96.0)
    else:
        opts['Gdpi'] = '%s' % (ctx['dpi'],)

    for ext in ['png', 'svg']:
        cmd = '''dot %s -T%s -o%s %s''' % ( ' '.join('-%s=%s' % (k,v)
                                                     for k, v in opts.items()),
                                            ext, outfile + '.' + ext,
                                            outfile + '.dot')
        print ' [.] %r ' % (cmd,)
        if os.system(cmd) != 0: sys.exit(1)


    cmd=r'''sed -i 's#^\(<svg width=".*\)pt\(" height=".*\)pt#\1px\2px#g' %s''' % (outfile + '.svg',)
    print ' [.] %r ' % (cmd,)
    if os.system(cmd) != 0: sys.exit(1)
