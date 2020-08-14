#
# Simple time manipulation.
#
import datetime

def user_tz_offset(request):
    return -int(request.get_cookie('tzoffset', '0'))

#
# Shift a datetime from its current zone to our current offset.
#
def offset_time(request, dt):
    current = dt.tzinfo.utcoffset(dt)
    shift = current - datetime.timedelta(minutes = user_tz_offset(request))
    return dt - shift
