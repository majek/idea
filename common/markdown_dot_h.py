import markdown
from markdown.util import etree, AtomicString
import os.path
import os
import sys
import shutil
import re
import md5
import yaml

defaults = {'height': 200,
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

        cmd = '''dot -Gsize="10,%.3f" -Gbgcolor=transparent -Gtruecolor=true -Grankdir=LR -Tpng -o%s %s''' % (
            int(ctx['height'])/96.0, outfile, dotfile)
        print ' [.] %r ' % (cmd,)
        if os.system(cmd) != 0: sys.exit(1)

        el = etree.Element("img")
        el.set('src', ctx['file'])
        el.set('height', str(ctx['height']) + 'px')
        el.set('alt', str(ctx['descr']))
        return el


class DotExtension(markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        dp = DotPattern(md)
        dp.getConfig = self.getConfig
        md.inlinePatterns.insert(0, 'a', dp)

def makeExtension(configs=None):
    return DotExtension(configs=configs)
