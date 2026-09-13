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
EVENT_NAME = 'Linux Plumbers Conference'
EVENT_START = '2026-10-05'
EVENT_END = '2026-10-07'
DEFAULT_CHATROOM = 'default' # Certainly not what you want.
LOGFILE = None
AUTH_SECRET = '1da177e4c3f41524e886b7f1b8a0c1fc7321cac2'

import datetime


def _format_event_dates(start, end):
    separator = '\N{EN DASH}'
    if (start.year, start.month) == (end.year, end.month):
        return f'{start.day}{separator}{end.day} {end:%b %Y}'
    if start.year == end.year:
        return f'{start.day} {start:%b}{separator}{end.day} {end:%b %Y}'
    return f'{start.day} {start:%b %Y}{separator}{end.day} {end:%b %Y}'


def load_config(cdir):
    global CONFIG_DIR, EVENT, EVENT_START, EVENT_END, EVENT_YEAR, EVENT_DATES
    CONFIG_DIR = cdir
    with open(cdir + '/vars', 'r') as f:
        # Using globals() here dumps the variables directly into the
        # module namespace.
        exec(f.read(), globals())
    try:
        EVENT_START = datetime.date.fromisoformat(EVENT_START)
        EVENT_END = datetime.date.fromisoformat(EVENT_END)
    except (TypeError, ValueError) as exc:
        raise ValueError('EVENT_START and EVENT_END must use YYYY-MM-DD format') from exc
    if EVENT_END < EVENT_START:
        raise ValueError('EVENT_END must not precede EVENT_START')
    EVENT_YEAR = EVENT_START.year
    EVENT = f'{EVENT_NAME} {EVENT_YEAR}'
    EVENT_DATES = _format_event_dates(EVENT_START, EVENT_END)
