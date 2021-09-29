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

#
# Default values for variables.
#
EVENT = 'Linux Plumbers Conference'
DEFAULT_CHATROOM = 'default' # Certainly not what you want.
LOGFILE = None
AUTH_SECRET = '1da177e4c3f41524e886b7f1b8a0c1fc7321cac2'

def load_config(cdir):
    global CONFIG_DIR
    CONFIG_DIR = cdir
    with open(cdir + '/vars', 'r') as f:
        # Using globals() here dumps the variables directly into the
        # module namespace.
        exec(f.read(), globals())
