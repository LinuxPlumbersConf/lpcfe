#
# The quick-n-dirty LPC BBB frontend system
#   Copyright 2020 Jonathan Corbet <corbet@lwn.net>
#   Copyright 2020 Guy Lunardi <guy@linux.com>
# Redistributable under the terms of the GNU General Public License,
# version 2 or greater
#
#
# Encapsulate our dealings with BBB
#
import hashlib, requests, datetime
from requests.exceptions import ConnectionError, ReadTimeout
from xml.etree import ElementTree
from urllib.parse import quote_plus
import config

#
# We may eventually want some more flexibility here.
#
Welcome = '''Welcome to the Linux Plumbers Conference 2021 %s!
<br><br>
Please remember that the <a
href="https://www.linuxplumbersconf.org/event/7/page/48-anti-harassment-policy"
target="_blank">LPC
anti-harassment policy</a> applies to interaction in this room, and that
this room is being recorded.
<br><br>
Please keep your microphone muted and your video off except when participating
in the discussion.
'''

#
# A simple class representing a room.
#
class Room:
    def __init__(self, name, server, type, matrix):
        self.name = name
        self.server = server
        self.type = type
        self.matrix = matrix

def add_room(name, server, type, matrix):
    rooms[name] = Room(name, server, type, matrix)

servers = { }  # Just maps name to secret
rooms = { }    # Rooms we know about.

MOD_PW = 'LPCmoderator'  # Oh the security
ATT_PW = 'LPCattendee'

def load_servers(cdir):
    try:
        with open(cdir + '/servers', 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if line == '' or line[0] == '#':
                    continue
                sline = line.split(':')
                if len(sline) != 2:
                    print('Bad server line: "%s"' % line)
                else:
                    servers[sline[0]] = sline[1]
    except FileNotFoundError:
        print('Unable to open servers file')

Room_types = [ 'session', 'hack', 'private' ]

def load_rooms(cdir):
    try:
        with open(cdir + '/rooms', 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if line == '' or line[0] == '#':
                    continue
                sline = line.split(':')
                matrix = 'default' # what should this really be?
                if len(sline) == 4:
                    matrix = sline[3]
                elif len(sline) != 3:
                    print('Bad rooms line: "%s"' % line)
                    continue
                server = sline[1]
                type = sline[2]
                if type not in Room_types:
                    print(f'Bad type ({type}) for room {sline[0]}')
                elif server not in servers:
                    print('Room %s on bad server %s' % (sline[0], server))
                else:
                    add_room(sline[0], server, type, matrix)
    except FileNotFoundError:
        print('Unable to open rooms file')

def load_config(cdir):
    load_servers(cdir)
    load_rooms(cdir)

def all_servers():
    return sorted(servers.keys())

#
# Ping a server to see what's going on; assuming it's up, return info
# about what's running there.
#
def status(server):
    response = run_request(server, 'getMeetings')
    if not response:
        return None
    meetings = [ ]
    for meeting in response.findall('meetings/meeting'):
        d = dict(room = meeting.findtext('meetingName'),
                 people = meeting.findtext('participantCount'))
        mods = [ ]
        for attendee in meeting.findall('attendees/attendee'):
            if attendee.findtext('role') == 'MODERATOR':
                mods.append(attendee.findtext('fullName'))
        d['moderators'] = ' '.join(mods)
        meetings.append(d)
    return meetings


#
# Check up on a specific room.
#
def room_status(room):
    ret = { 'running': False, 'server': '???' }
    try:
        ret['server'] = server = rooms[room].server
    except KeyError:
        return ret
    ret['type'] = rooms[room].type
    response = run_request(server, 'getMeetingInfo', meetingID = room)
    if not response:
        return ret
    status = response.findtext('running')
    if (not status) or (status != 'true'):
        return ret
    ret['running'] = True
    ret['people'] = response.findtext('participantCount')
    ret['listeners'] = response.findtext('listenerCount')
    ret['video'] = response.findtext('videoCount')
    mods = [ ]
    parts = [ ]
    for attendee in response.findall('attendees/attendee'):
        if attendee.findtext('role') == 'MODERATOR':
            mods.append(attendee.findtext('fullName'))
        parts.append(attendee.findtext('fullName'))
    ret['moderators'] = ', '.join(sorted(mods))
    ret['participants'] = ', '.join(sorted(parts))
    return ret

def valid_room(room):
    return room in rooms

def all_rooms(type = None):
    ret = sorted(rooms.keys(), key = lambda r: rooms[r].type + r )
    if type:
        ret = [ room for room in ret if rooms[room].type == type ]
    return ret

# 
def start_room(room):
    #
    # Policy: for most rooms, we turn on recording unconditionally and
    # don't let anybody turn it off.  "Private" rooms, though, don't
    # record by default and allow control.
    #
    if rooms[room].type != 'private':
        autostart = 'true'
        allowstop = 'false'
    else:
        autostart = 'false'
        allowstop = 'true'
    #
    # Fire it up.
    #
    server = rooms[room].server
    response = run_request(server, 'create', name = room,
                           meetingID = room,
                           attendeePW = ATT_PW,
                           moderatorPW = MOD_PW,
                           breakoutRoomsEnabled = "false",
                           logo = config.LOGO_URL,
                           logoutURL = config.SITE_URL,
                           matrixRoomId = rooms[room].matrix,
                           maxParticipants = '250',
                           muteOnStart = 'true',
                           record = 'true',
                           autoStartRecording = autostart,
                           allowStartStopRecording = allowstop,
                           welcome = Welcome % (room))
    # We should maybe return something rather than assuming it worked...

def join_room_url(name, room, as_moderator, as_admin = False):
    pw = ATT_PW
    if as_moderator:
        pw = MOD_PW
    if as_moderator and not as_admin:
        d = {'userdata-bbb_custom_style_url':
             'https://bbb0.2020.linuxplumbersconf.org/lpc-moderator.css' }
    else:
        d = {'userdata-bbb_custom_style_url':
             'https://bbb0.2020.linuxplumbersconf.org/lpc.css' }
    return make_request(rooms[room].server, 'join', dargs = d,
                        meetingID = room,
                        fullName = name,
                        password = pw)

#
# Recordings.
#
class bbb_recording:
    def __init__(self, id, meeting, start, len, url):
        self.id = id
        self.meeting = meeting
        self.start = start
        self.length = len
        self.url = url

def recordings(server):
    response = run_request(server, 'getRecordings')
    recs = [ ]
    for rec in response.findall('recordings/recording'):
        id = rec.findtext('recordID')
        meeting = rec.findtext('meetingID')
        start = int(rec.findtext('startTime')[:-3])
        end = int(rec.findtext('endTime')[:-3])
        dtstart = datetime.datetime.fromtimestamp(start)
        len = end - start
        url = None
        for pb in rec.findall('playback/format'):
            if pb.findtext('type') == 'presentation':
                url = pb.findtext('url')
        recs.append(bbb_recording(id, meeting, dtstart, len, url))
    return recs

#
# Low-level BBB request machinery.
#
def make_request(dest, command, dargs = None, **args):
    if dargs:
        args.update(dargs)
    secret = servers[dest]
    aargs = '&'.join([ '%s=%s' % (arg, quote_plus(args[arg])) for arg in args ])
    # aargs = quote_plus(aargs)
    hash = hashlib.sha1((command + aargs + secret).encode('utf8')).hexdigest()
    if len(args) > 0:
        return 'https://' + dest + '/bigbluebutton/api/' + command + '?' + \
               aargs + '&checksum=' + hash
    return 'https://' + dest + '/bigbluebutton/api/' + command + \
           '?checksum=' + hash

def run_request(server, command, **args):
    url = make_request(server, command, **args)
    # print('\n', url)
    try:
        r = requests.get(url, timeout = 5.0)
    except (ConnectionError, ReadTimeout):
        return None
    if r.status_code != 200:
        return None
    # print(r.text)
    return ElementTree.fromstring(r.text)
