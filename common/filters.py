import scss
import markdown as Markdown

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


def sass(text):
    return CSS_UNCOMPR.compile(text)

def sass_compr(text):
    return CSS_COMPR.compile(text)


import markdown_urlize
urlize = markdown_urlize.UrlizeExtension({})

import markdown_wrap_h
wrap = markdown_wrap_h.HeaderIdExtension({})

def markdown(text):
    return Markdown.markdown(text, extensions=['extra', 'headerid', 'toc(title=Contents)', urlize, wrap],
                             encoding="utf-8",
                             output_format="html5")
