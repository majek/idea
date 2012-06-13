import sys
import os
import yaml
import mako.template
import mako.lookup

import common.filters

dst_dir = sys.argv[1]

print " [*] Dst dir: %r" % (dst_dir,)

with open('context.yml', 'r') as f:
    ctx = yaml.load(f.read())

ctx['filters'] = common.filters.MakoFilters({})


mylookup = mako.lookup.TemplateLookup(directories=['.', '../../templates'])
template = mako.template.Template(filename='main.md', lookup=mylookup)

with open(os.path.join(dst_dir, 'index.html'), 'w') as f:
    f.write( template.render(**ctx) )
