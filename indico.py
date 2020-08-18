#
# Interface to Indico (to get the schedule mainly)
#
import requests, datetime, copy
import config

#
# Save the time of the final session
#
final_time = None

Tracks = { }
NewTracks = { }

def load_timetable():
    global Tracks, NewTracks

    url = '%s/export/timetable/%d.json?ak=%s&pretty=yes' % (config.INDICO_SERVER,
                                                            config.EVENT_ID,
                                                            config.INDICO_API_KEY)
    r = requests.get(url)
    if r.status_code != 200:
        print('Bad status %d getting timetable' % (r.status_code))
        return
    #
    # The timetable is loaded into NewTracks, then assigned over at the end,
    # just in case some other thread is trying to access it.
    #
    NewTracks = { }
    decrypt_indico_json(r.json())
    Tracks = NewTracks

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
                add_talk('none', item)
            else:
                print('Unknown entry', item['id'], item['entryType'])

def add_talk(session, talk):
    global final_time

    item = sched_item(talk, session)
    try:
        NewTracks[session].append(item)
    except KeyError:
        NewTracks[session] = [item]
    if (final_time is None) or (item.end > final_time):
        final_time = item.end

def decrypt_session(session):
    title = session['title']
    for entry in session['entries'].values():
        if entry['entryType'] not in ['Break', 'Contribution']:
            print('Funky session entry', title, entry['title'], entry['entryType'])
        else:
            add_talk(title, entry)

#
# Let's try to simplify the representation of a schedule item
#

def fixtime(indico_time):
    ts = indico_time['date'] + ' ' + indico_time['time'] + ' ' + config.INDICO_TZOFFSET
    return datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S %z')

class sched_item:
    def __init__(self, item, track):
        self.is_break = item['entryType'] == 'Break'
        self.title = item['title']
        self.begin = fixtime(item['startDate'])
        self.end = fixtime(item['endDate'])
        self.room = item['room']
        self.desc = item['description'].replace('\n', ' ')
        self.track = track
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
    for track in Tracks.keys():
        items = [ ]
        for item in Tracks[track]:
            if (begin <= item.begin < end) or (ip_end < item.end < end) or \
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
    for track in Tracks.keys():
        for talk in Tracks[track]:
            if (talk.begin > begin) and (talk.begin < earliest):
                earliest = talk.begin
    return earliest
