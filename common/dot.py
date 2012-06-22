import md5
import os
import png
import yaml
import sys

svg_disabled = False

defaults = {'height': 'auto',
            'width': 625,
            'descr': 'Diagram'}


join_attr = lambda attr:' '.join( '%s="%s"' % (k,v) for k, v in attr.iteritems())

def generate(content, dst_dir, leading):
    checksum = md5.new(content).hexdigest()

    t = content.split('--\n', 1)
    if len(t) == 1:
        yml_data, dot_data = ['', content]
    else:
        yml_data, dot_data = t
    ctx = dict(defaults)
    ctx['file'] = checksum
    ctx.update( yaml.load(yml_data) or {} )
    
    outfile = os.path.join(dst_dir, ctx['file'])
    dotfile = outfile + '.dot'

    if not os.path.isfile(dotfile):
        with open(dotfile, 'w') as f:
            f.write(dot_data)

    opts = {
        'Gbgcolor':'transparent',
        'Gtruecolor':'true',
        'Grankdir':'LR',
        'Gfontname': '"Arial"',
        'Nfontname': '"Arial"',
        'Efontname': '"Arial"',
        }

    if ctx['height'] != 'auto':
        opts['Gsize'] = '"%.3f,%.3f"' % (int(ctx['width'])/96.0,
                                        int(ctx['height'])/96.0)
    else:
        opts['Gdpi'] = ctx.get('dpi', '72')

    for ext in ['png', 'svg']:
        cmd = '''dot %s -T%s -o%s %s''' % ( ' '.join('-%s=%s' % (k,v)
                                                     for k, v in opts.items()),
                                            ext, outfile + '.' + ext, dotfile)
        print ' [.] %r ' % (cmd,)
        if os.system(cmd) != 0: sys.exit(1)

    with open(outfile + '.png', 'r') as f:
        (width, height, _, _) = png.Reader(file=f).read()

    attr = {
        'height': str(height) + 'px',
        'width': str(width) + 'px',
        }

    png_attr = {
        'src': ctx['file'] + '.png',
        'alt': "",
        }
    svg_attr = {
        'data': ctx['file'] + '.svg',
        'type': "image/svg+xml" + ("" if not svg_disabled else "XXX"),
        }
    png_attr.update(attr)
    svg_attr.update(attr)

    remainder = height % leading
    if remainder:
        svg_attr['style'] = 'padding-bottom:%spx' % (leading - remainder,)



    return '''<object %s><img %s></object>''' % (
        join_attr(svg_attr), join_attr(png_attr))

