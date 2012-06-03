import glob
import os
import yaml
import mako.template
import sys
import mako.lookup
import collections


import common.filters

dst_dir = sys.argv[1]


sites = []

for dir_name in filter(os.path.isdir, glob.glob('*')):
    yml_file = os.path.join(dir_name, 'context.yml')
    if not os.path.isfile(yml_file): continue
    with open(yml_file, 'r') as f:
        yml = yaml.load(f.read())
        yml['dir_name'] = dir_name
        assert yml['date']
        sites.append(yml)


sites.sort(key = lambda yml:yml['date'])

sites_by_year = collections.defaultdict(lambda:list())
for site in sites:
    sites_by_year[site['date'].year].append( site )

mylookup = mako.lookup.TemplateLookup(directories=['.', '../templates'])
template = mako.template.Template(filename='main.html', lookup=mylookup)
ctx = {
    'sites': sites,
    'sites_by_year': sites_by_year,
    'filters': common.filters,
}

with open(os.path.join(dst_dir, 'index.html'), 'w') as f:
    f.write( template.render(**ctx) )

