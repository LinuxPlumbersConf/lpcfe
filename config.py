#
# Poor-hacker's configuration file
#

config_vars = { }

def load_config(cdir):
    with open(cdir + '/vars', 'r') as f:
        # Using globals() here dumps the variables directly into the
        # module namespace.
        exec(f.read(), globals())
