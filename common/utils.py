import string
import urllib


special_chars = {
    ' ': '-',
    }

allowed = string.ascii_lowercase + string.digits + '-_'

def subdir_from_ctx(ctx, default='none'):
    sub_dir = ''
    if ctx.get('date', None):
        sub_dir += ctx['date'].strftime('%Y-%m-%d-')
    title = ''.join( (c in special_chars and special_chars[c] or c) for c in ctx['title'].lower() )
    title = ''.join( c for c in title if c in allowed )
    title = title.lstrip('-').rstrip('-')
    sub_dir += urllib.quote(title)
    return sub_dir or default
