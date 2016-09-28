import glob
import mako.lookup
import mako.template
import os
import shutil
import sys
import yaml

import common.filters
import common.utils

with open('context.yml', 'r') as f:
    ctx = yaml.load(f.read())

dst_dir = os.path.join(sys.argv[1], common.utils.subdir_from_ctx(ctx))
print " [*] Dst dir: %r" % (dst_dir,)
if not os.path.isdir(dst_dir): os.makedirs(dst_dir)

ctx['filters'] = common.filters.MakoFilters({'dst_dir': [dst_dir], 'leading': [28]})

mylookup = mako.lookup.TemplateLookup(directories=['.', '../../templates'])

with open(os.path.join(dst_dir, 'index.html'), 'w') as f:
    template = mako.template.Template(filename='main.md', lookup=mylookup,
                                      input_encoding="utf-8")
    f.write( template.render(**ctx).encode('utf-8') )

for fname in ctx.get('copied_files', []):
    for fname in glob.glob(fname):
        pass
        #print ' [.] copying %r' % (fname,)
        # shutil.copy2(fname, dst_dir)
