import scss
import markdown as Markdown

import markdown_urlize
import markdown_wrap_h
import markdown_dot_h
import markdown_dot2_h


CSS_UNCOMPR = scss.Scss(scss_opts={
        'compress': False,
        'debug_info': False,
    }
)

CSS_COMPR = scss.Scss(scss_opts={
        'compress': True,
        'debug_info': False,
    }
)

class MakoFilters(object):
    def __init__(self, configs):
        urlize = markdown_urlize.UrlizeExtension(dict(configs))
        wrap = markdown_wrap_h.HeaderIdExtension(dict(configs))
        dot2 = markdown_dot2_h.makeExtension(dict(configs))
        self.markdown_extensions = ['extra', 'headerid',
                                    'toc(title=Contents)', urlize, wrap, dot2]

    def sass(self, text):
        return CSS_UNCOMPR.compile(text)

    def sass_compr(self, text):
        return CSS_COMPR.compile(text)

    def markdown(self, text):
        return Markdown.markdown(text, extensions=self.markdown_extensions[:],
                                 encoding="utf-8",
                                 output_format="html5")
