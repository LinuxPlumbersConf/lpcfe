#
# The quick-n-dirty LPC BBB frontend system
#   Copyright 2020 Jonathan Corbet <corbet@lwn.net>
#   Copyright 2020 Guy Lunardi <guy@linux.com>
# Redistributable under the terms of the GNU General Public License,
# version 2 or greater
#
#
# Interface to Indico (to get the schedule mainly)
#
import requests, datetime, copy
import config

#
# Save the time of the final session
#
final_time = None

class Session:
    def __init__(self, slot_id, title, room, matrix, extra):
        self.slot_id = slot_id
        self.title = title
        self.room = room
        self.matrix = matrix
        self.extra = extra
        self.talks = []

Sessions = {}

def session_name(slot_id):
    try:
        return Sessions[slot_id].title
    except:
        print('No session ', s)
        return ''

def session_extra(slot_id):
    try:
        return Sessions[slot_id].extra
    except:
        print('No session ', s)

def session_room(slot_id):
    try:
        return Sessions[slot_id].room
    except:
        print('No session ', s)

def load_sessions(cdir):
    try:
        with open(cdir + '/sessions', 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if line == '' or line[0] == '#':
                    continue
                sline = line.split(':')
                if len(sline) not in [3, 4, 5]:
                    print('Bad tracks line: %s' % (line))
                    continue
                slotId = int(sline[0])
                title = sline[1]
                room = sline[2]
                matrix = ''
                extra = ''
                if len(sline) >= 4:
                    matrix = sline[3]
                if len(sline) == 5:
                    extra = sline[4]
                Sessions[slotId] = Session(slotId, title, room, matrix, extra)
    except FileNotFoundError:
        print('Unable to open tracks file')

def load_timetable():
    url = '%s/export/timetable/%d.json?ak=%s&pretty=yes' % (config.INDICO_SERVER,
                                                            config.EVENT_ID,
                                                            config.INDICO_API_KEY)
    r = requests.get(url)
    if r.status_code != 200:
        print('Bad status %d getting timetable' % (r.status_code))
        return
    decrypt_indico_json(r.json())

#
# Try to turn the massive blob of json we get back from Indico into some
# sort of rational data structure.
#

def decrypt_indico_json(j):
    days = j['results'][str(config.EVENT_ID)]
    for day in days.values():
        for item in day.values():
            if item['entryType'] == 'Session':
                decrypt_session(item)
            elif item['entryType'] == 'Contribution':
                # A talk outside of any session
                # FIXME: there shoud be Session object for these talks
                add_talk('none', item, 0)
            else:
                print('Unknown entry', item['id'], item['entryType'])

def add_talk(talks, session, talk, slot_id):
    global final_time

    item = sched_item(talk, session, slot_id)
    talks.append(item)
    if (final_time is None) or (item.end > final_time):
        final_time = item.end

def decrypt_session(session):
    global Sessions

    title = session['title']
    slot_id = session['sessionSlotId']

    if not Sessions.get(slot_id):
        print('New session ', title, ' appeared?')
        return

    #
    # The talks is loaded into an empty list, then assigned over at the end,
    # just in case some other thread is trying to access it.
    #
    talks = []
    for entry in session['entries'].values():
        if entry['entryType'] not in ['Break', 'Contribution']:
            print('Funky session entry', title, entry['title'], entry['entryType'])
        else:
            add_talk(talks, title, entry, slot_id)
    Sessions[slot_id].talks = talks

#
# Let's try to simplify the representation of a schedule item
#

def fixtime(indico_time):
    ts = indico_time['date'] + ' ' + indico_time['time'] + ' ' + config.INDICO_TZOFFSET
    return datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S %z')

class sched_item:
    def __init__(self, item, track, slot_id):
        self.is_break = item['entryType'] == 'Break'
        self.slot_id = slot_id
        self.title = item['title']
        self.begin = fixtime(item['startDate'])
        self.end = fixtime(item['endDate'])
        self.room = item['room']
        self.desc = item['description'].replace('\n', ' ')
        self.track = track
        self.bgcolor = item['color']
        self.color = item['textColor']
        try:
            self.url = config.INDICO_SERVER + item['url']
        except KeyError:
            self.url = None
        self.presenters = [ ]
        if 'presenters' in item:
            for pres in item['presenters']:
                self.presenters.append(pres['name'])

#
# Get a piece of the timetable.
#
def get_timetable(begin, minutes, in_progress = 10):
    end = begin + datetime.timedelta(minutes = minutes)
    ip_end = begin + datetime.timedelta(minutes = in_progress)
    ret = { }
    tracks = dict(sorted(Sessions.items(), key=lambda x:x[1].title))
    for track in tracks:
        items = [ ]
        title = Sessions[track].title
        for item in Sessions[track].talks:
            if (begin <= item.begin < end) or (ip_end < item.end < end) or\
               (item.begin < begin and item.end > end):
                items.append(copy.copy(item))
        if items:
            ret[track] = items
    return ret

#
# Find out when the next session begins after the present time.  This is
# inefficient, we could do this in the get_timetable() pass, but nobody
# will care...
#
def find_restart_time(begin):
    if begin > final_time:
        return None
    earliest = final_time
    for track in Sessions.keys():
        for talk in Sessions[track].talks:
            if (talk.begin > begin) and (talk.begin < earliest):
                earliest = talk.begin
    return earliest

#
# Which track is in the given room now (or soon)?
#
def track_in_room(room, time, lead = 60):
    end = time + datetime.timedelta(minutes = lead)
    for track in Sessions:
        for item in Sessions[track].talks:
            if (item.room == room) and\
               ((time <= item.begin < end) or (time < item.end < end) or\
               (item.begin < time and item.end > end)):
                return track
    return None

#
# Get matrix room ID for the session running in the @room
#
def matrix_room(room, time):
    track = track_in_room(room, time)
    if track:
        return Sessions[track].matrix
    return ''
