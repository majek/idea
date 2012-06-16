import glob
import os
import yaml
import mako.template
import sys
import mako.lookup
import collections
import shutil

import common.filters
import common.utils

dst_dir = sys.argv[1]
print " [*] Dst dir: %r" % (dst_dir,)


sites = []

for dir_name in filter(os.path.isdir, glob.glob('*')):
    yml_file = os.path.join(dir_name, 'context.yml')
    if not os.path.isfile(yml_file): continue
    with open(yml_file, 'r') as f:
        yml = yaml.load(f.read())
        if yml.get('disabled') is True:
            continue
        yml['dir_name'] = common.utils.subdir_from_ctx(yml)
        assert yml['date']
        sites.append(yml)


sites.sort(key = lambda yml:yml['date'])

sites_by_year = collections.defaultdict(lambda:list())
for site in sites:
    sites_by_year[site['date'].year].append( site )

mylookup = mako.lookup.TemplateLookup(directories=['.', '../templates'])
ctx = {
    'sites': sites,
    'sites_by_year': sites_by_year,
    'filters': common.filters.MakoFilters({}),
}

with open(os.path.join(dst_dir, 'index.html'), 'w') as f:
    template = mako.template.Template(filename='main.html', lookup=mylookup,
                                      input_encoding="utf-8")
    f.write( template.render(**ctx) )

with open(os.path.join(dst_dir, '404.html'), 'w') as f:
    template = mako.template.Template(filename='404.html', lookup=mylookup,
                                      input_encoding="utf-8")

    f.write( template.render(**ctx) )

for fname in ['zarowka.png', 'favicon.ico', '28px_grid_bg.gif']:
    print ' [.] copying %r' % (fname,)
    shutil.copy2(fname, dst_dir)
