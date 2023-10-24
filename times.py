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
import pytz
import config

fake_time = datetime.datetime(2023, 11, 13, 14, 30, 0, tzinfo = timezone.utc)

def fake_time_set(time):
    global current_time, fake_time

    fake_time = time
    current_time = fake_current_time

def fake_time_reset():
    global current_time

    current_time = real_current_time

def real_current_time():
    return datetime.datetime.now(tz = timezone.utc)

def fake_current_time():
    return fake_time

current_time = real_current_time

def user_tz_offset(request):
    return -int(request.get_cookie('tzoffset', '0'))

def user_tz(request):
    return (request.get_cookie('tz', '0'))

#
# Shift a datetime from its current zone to our current offset.
#
def offset_time(request, dt):
    current = dt.tzinfo.utcoffset(dt)
    shift = current - datetime.timedelta(minutes = user_tz_offset(request))
    return dt - shift

def utc_time(dt):
    return dt.astimezone(timezone.utc)

def venue_time(dt):
    return dt.astimezone(pytz.timezone(config.VENUE_TZ))
