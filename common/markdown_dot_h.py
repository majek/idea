import markdown
from markdown.util import etree, AtomicString
import os.path
import os
import sys
import shutil
import re
import md5
import yaml
import png

defaults = {'height': 28*7,
            'width': 625,
            'descr': 'Diagram'}


class DotPattern(markdown.inlinepatterns.Pattern):
    def __init__ (self, md):
        markdown.inlinepatterns.Pattern.__init__(self, r'<dot>(.*)</dot>')
        self.md = md

    def handleMatch(self, m):
        content = m.groups()[1]
        checksum = md5.new(content).hexdigest()
        t = content.split('--\n', 1)
        if len(t) == 1:
            yml_data, dot_data = ['', content]
        else:
            yml_data, dot_data = t
        ctx = dict(defaults)
        ctx['file'] = checksum + '.png'
        ctx.update( yaml.load(yml_data) or {} )

        dotfile = os.path.join(self.getConfig('dst_dir'), checksum + '.dot')
        outfile = os.path.join(self.getConfig('dst_dir'), ctx['file'])
        if not os.path.isfile(dotfile):
            with open(dotfile, 'w') as f:
                f.write(dot_data)

        cmd = '''dot -Gsize="%.3f,%.3f" -Gbgcolor=transparent -Gtruecolor=true -Grankdir=LR -Tpng -o%s %s''' % (
            int(ctx['width'])/96.0, int(ctx['height'])/96.0, outfile, dotfile)
        print ' [.] %r ' % (cmd,)
        if os.system(cmd) != 0: sys.exit(1)

        with open(outfile, 'r') as f:
            (width, height, _, _) = png.Reader(file=f).read()

        el = etree.Element("img")
        el.set('src', ctx['file'])
        el.set('height', str(height) + 'px')
        el.set('width', str(width) + 'px')
        el.set('alt', str(ctx['descr']))

        leading = self.getConfig('leading')
        remainder = height % leading
        if remainder:
            el.set('style', 'padding-bottom:%spx' % (leading - remainder,))
        return el


class DotExtension(markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        dp = DotPattern(md)
        dp.getConfig = self.getConfig
        md.inlinePatterns.insert(0, 'a', dp)

def makeExtension(configs=None):
    return DotExtension(configs=configs)
