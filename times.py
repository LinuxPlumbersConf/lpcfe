#
# The quick-n-dirty LPC BBB frontend system
#   Copyright 2020 Jonathan Corbet <corbet@lwn.net>
#   Copyright 2020 Guy Lunardi <guy@linux.com>
# Redistributable under the terms of the GNU General Public License,
# version 2 or greater
#
#
# Simple time manipulation.
#
import datetime
from datetime import timezone

def current_time():
    return datetime.datetime.now(tz = timezone.utc)

def user_tz_offset(request):
    return -int(request.get_cookie('tzoffset', '0'))

#
# Shift a datetime from its current zone to our current offset.
#
def offset_time(request, dt):
    current = dt.tzinfo.utcoffset(dt)
    shift = current - datetime.timedelta(minutes = user_tz_offset(request))
    return dt - shift

def utc_time(dt):
    return dt.astimezone(timezone.utc)
