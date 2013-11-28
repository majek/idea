import md5
import os
import yaml
import sys
import png

defaults = {
    'size': '300x300',
    'data': '',
    'xsize': '',
    }

join_attr = lambda attr:' '.join( '%s="%s"' % (k,v) for k, v in attr)

# pyc -> py, pyo -> py
with open(sys.modules[__name__].__file__.rstrip('co'), 'r') as f:
    current_module_checksum = md5.new(f.read()).hexdigest()


def generate(content, dst_dir, leading):
    checksum = md5.new(current_module_checksum + content).hexdigest()

    t = content.split('--\n', 1)
    if len(t) == 1:
        yml_data, content = ['', content]
    else:
        yml_data, content = t

    ctx = dict(defaults)
    ctx['file'] = checksum
    ctx.update( yaml.load(yml_data) or {} )

    outfile = os.path.join(dst_dir, ctx['file'])

    required_ext = ['.gnu', '.png', '.dat']
    if sum(os.path.isfile(outfile + ext) for ext in required_ext) < 3:
        do_generate(ctx, outfile, content)
        if ctx['xsize']:
            ctx['size'] = ctx['xsize']
            do_generate(ctx, outfile + '-large', content)
    else:
        print ' [.] %r already present' % (outfile + '.gnu',)


    with open(outfile + '.png', 'r') as f:
        (width, height, _, _) = png.Reader(file=f).read()

    attr = [
        ('alt', ''),
        ('width', '%spx' % (width,)),
        ('height', '%spx' % (height, )),
        ('src', '%s.png' % ctx['file']),
        ('style', 'padding-bottom:%spx' % (leading - (height % leading),)),
        ]

    r = '''<div class="gnuimage"><img %s></div>''' % (
        join_attr(attr))
    if ctx['xsize']:
        r = '''<a href="%s-large.png">%s</a>'''% (ctx['file'], r)
    return r


def do_generate(ctx, outfile, content):
    with open(outfile + '.gnu', 'w') as f:
        f.write(content.replace('data.dat', outfile + '.dat'))

    with open(outfile + '.dat', 'w') as f:
        f.write(ctx['data'])

    width, height = map(int, ctx['size'].split('x', 1))
    lines = ["set terminal pngcairo transparent enhanced linewidth 2 font 'arial,10' size %s, %s" % (width, height),
             "set output %r" % (outfile + '.png',),
             "set samples 1001"]
    cmd = '''gnuplot -e "%s" %s''' % ( '; '.join(lines),
                                     outfile + '.gnu')
    print ' [.] %s' % (cmd,)
    if os.system(cmd) != 0: sys.exit(1)
