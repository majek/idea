import re
import markdown
from markdown.extensions.codehilite import CodeHilite, CodeHiliteExtension


import gnuplot


FENCED_BLOCK_RE = re.compile(
    r'<gnuplot>(?P<code>.*?)(?<=\n)</gnuplot>[ ]*$',
    re.MULTILINE|re.DOTALL
    )


class FencedCodeExtension(markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)

        x = FencedBlockPreprocessor(md)
        x.getConfig = self.getConfig
        md.preprocessors.add('gnuplot_code_block', x, "_begin")


class FencedBlockPreprocessor(markdown.preprocessors.Preprocessor):
    def run(self, lines):
        text = "\n".join(lines)
        while 1:
            m = FENCED_BLOCK_RE.search(text)
            if m:
                code = m.group('code')

                el = gnuplot.generate(code, self.getConfig('dst_dir'),
                                      self.getConfig('leading'))

                placeholder = self.markdown.htmlStash.store(el, safe=True)
                text = '%s\n%s\n%s'% (text[:m.start()], placeholder, text[m.end():])
            else:
                break
        return text.split("\n")

def makeExtension(configs=None):
    return FencedCodeExtension(configs=configs)

