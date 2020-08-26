#
# The quick-n-dirty LPC BBB frontend system
#   Copyright 2020 Jonathan Corbet <corbet@lwn.net>
#   Copyright 2020 Guy Lunardi <guy@linux.com>
# Redistributable under the terms of the GNU General Public License,
# version 2 or greater
#
#
# Poor-hacker's configuration file
#

config_vars = { }

def load_config(cdir):
    with open(cdir + '/vars', 'r') as f:
        # Using globals() here dumps the variables directly into the
        # module namespace.
        exec(f.read(), globals())
