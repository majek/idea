import markdown
from markdown.util import etree
import re
from string import ascii_lowercase, digits, punctuation
import logging
import unicodedata


class HeaderIdExtension (markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)
        self.processor = HeaderIdTreeprocessor()
        self.processor.md = md
        self.processor.config = self.getConfigs()
        # Replace existing hasheader in place.
        md.treeprocessors.add('headerid', self.processor, '>inline')

    def reset(self):
        self.processor.IDs = []


class HeaderIdTreeprocessor(markdown.treeprocessors.Treeprocessor):
    """ Assign IDs to headers. """

    IDs = set()

    def run(self, doc):
        for elem in doc.getiterator():
            if elem.tag in ['h1', 'blockquote', 'table']:
                tag = elem.tag 
                if elem.get('ok'): continue
                ne = etree.SubElement(elem, tag)
                elem.tag = 'div'
                ne.text = elem.text
                elem.text = ''
                elem.set('class', tag + 'wrapper')
                ne.set('ok', 'ok')
                for child in elem.getchildren():
                    if child is ne: continue
                    elem.remove(child)
                    ne.append(child)


def makeExtension(configs=None):
    return HeaderIdExtension(configs=configs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
