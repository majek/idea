import sys
import os
import yaml
import mako.template
import mako.lookup

import common.filters
import common.utils

with open('context.yml', 'r') as f:
    ctx = yaml.load(f.read())

dst_dir = os.path.join(sys.argv[1], common.utils.subdir_from_ctx(ctx))
print " [*] Dst dir: %r" % (dst_dir,)
if not os.path.isdir(dst_dir): os.makedirs(dst_dir)

ctx['filters'] = common.filters.MakoFilters({'dst_dir': [dst_dir], 'leading': [28]})

mylookup = mako.lookup.TemplateLookup(directories=['.', '../../templates'])
template = mako.template.Template(filename='main.md', lookup=mylookup,
                                  input_encoding="utf-8")

with open(os.path.join(dst_dir, 'index.html'), 'w') as f:
    f.write( template.render(**ctx).encode('utf-8') )
