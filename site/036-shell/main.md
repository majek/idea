
<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">


Command line tools can suggest to rerun them with different
parameters. For example:

    $ ls --blah
    ls: unrecognized option '--blah'
    Try 'ls --help' for more information.

That got me thinking: what if a tool wants to suggest more
sophisticated parameters? For example, say a program wants to be
executed with this single parameter: `$'\`\n` (dollar sign, single
quote, a back quote and new line, in hex "XXXX"). Should it print:

    $ weirdparameters --blah
    weirdparameters: unrecognized option '--blah'
    Try 'weirdparameters " $'`
    "' for more information.

This is plainly wrong :)

Let me rephrase the question:

> How does bash decode command line parameters?

Let's dig into the details.

The Bash way
-----------

After you typed something into Bash, it deals with it using the
following steps:

 - Bash splits simple command line into words
 - Brace expansion
 - Tilde expansion
 - Parameter expansion
 - Variable expansion
 - Arithmetic expansion
 - Command substitution
 - Word splitting (using IFS)  of results of parameter expansion, command substitution or arithmetic expansion.
 - Pathname expansion
 - Quote removal

I'll briefly describe all of these steps but only briefly, for details
you should read the `bash(1)` manpage; start with `EXPANSION` section.

0) Bash splits simple commands line into words.

The manpage says:

> A simple command is a sequence of optional variable assignments
> followed by blank-separated words and redirections, and terminated
> by a control operator.

Where "blank" is a tab or space and "control operator" is one of "|| &
&& ; ;; ( ) | |& <newline>".

Executive summary of the ignorant: When command line is first parsed
bash splits the words with spaces and tabs and expects a newline (or
one of the control tokens) to mark the end.

1) Brace expansion


Forbidden
=========

Command line parameters are stored in a C zero-terminated string. That
means the zero byte (`0x00`) is not allowed anywhere in the argv.

Unescaped
===========

Stray quote, double quote and backtick.

Delimiters
-----------

Bash treats some unescaped whitespace as a parameters delimiter. Space
(`0x20`), tab (`0x09`) can delimit paramters. But surprisingly not
vspace (`0x0b`), carriage return (`0x0d`) or form feed (`0x0c`).

> Pro tip: try `man ascii`

path expansion
----------

Tilda (`~`), question mark (`?`) and wildcard (`*`) will be
path-expanded. Also square brackets.

Shell meainig
---------

New line and semicolon in shell are interperted as command delimiters,
so can't be passed to the parameters directly.

Hash, ampersant, vertical bar, exclamation mark also have special meaning.

\n\x0b\x0c\r "#&\'()*;<>\\`|~')




Say you're using bash and you've run a command `cmd.py` in your terminal
and gave it four arguments:

    $ cmd.py 1 2 3 4

The code
===========


For simplicty we could avoid quoting at all. But we only can do that
safely for strings not conaining any of the characters

> '\t\n\x0b\x0c\r "#&\'()*;<>\\`|~[]?'.

The list is pretty messy, so it's much safer to whitelist characters instead of blacklisting:


Avoid using backslash encoding.

The safe options is to pack every argument possilbe into single
quotes.

'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_+=:.,'

marek@ubuntu-saucy:~/sh$ ./cmd01.py 'a'\''d'
['./cmd01.py', "a'd"]


```.py
import string

SAFE=set(string.ascii_lowercase +
         string.ascii_uppercase +
         string.digits +
         '-_+=:.,')

def shell_escape(args):
    b = []
    for arg in args:
        if not set(arg) - SAFE:
            b.append(arg)
        else:
            if "'" not in arg:
                b.append("'" + arg + "'")
            else:
                for c in '\\"`$':
                    arg = arg.replace(c, '\\' + c)
                b.append('"' + arg + '"')
    return ' '.join(args)
```

</%block>


$'`\n



// blog post o defensive bash
// blog post on when to use [[ vs [ vs ((


http://redsymbol.net/articles/unofficial-bash-strict-mode/

https://developer.gnome.org/glib/2.37/glib-Shell-related-Utilities.html
g_shell_parse_argvn

http://blog.flowblok.id.au/2013-02/shell-startup-scripts.html

http://www.dwheeler.com/essays/filenames-in-shell.html
