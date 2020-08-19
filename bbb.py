#
# Encapsulate our dealings with BBB
#
import hashlib, requests
from requests.exceptions import ConnectionError, ReadTimeout
from xml.etree import ElementTree
from urllib.parse import quote_plus
import config

#
# We may eventually want some more flexibility here.
#
Welcome = '''Welcome to the Linux Plumbers Conference 2020 %s!
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
    def __init__(self, name, server, type):
        self.name = name
        self.server = server
        self.type = type

def add_room(name, server, type):
    rooms[name] = Room(name, server, type)

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


def load_rooms(cdir):
    try:
        with open(cdir + '/rooms', 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if line == '' or line[0] == '#':
                    continue
                sline = line.split(':')
                if len(sline) == 2: # backward compatibility already!
                    type = 'session'
                elif len(sline) == 3:
                    type = sline[2]
                else:
                    print('Bad rooms line: "%s"' % line)
                    continue
                if sline[1] not in servers:
                    print('Room %s on bad server %s' % (sline[0], sline[1]))
                else:
                    add_room(sline[0], sline[1], type)
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

def all_rooms(type = None):
    ret = sorted(rooms.keys(), key = lambda r: rooms[r].type + r )
    if type:
        ret = [ room for room in ret if rooms[room].type == type ]
    return ret

# 
def start_room(room):
    server = rooms[room].server
    response = run_request(server, 'create', name = room,
                           meetingID = room,
                           attendeePW = ATT_PW,
                           moderatorPW = MOD_PW,
                           breakoutRoomsEnabled = "false",
                           logo = config.LOGO_URL,
                           logoutURL = config.SITE_URL,
                           maxParticipants = '250',
                           muteOnStart = 'true',
                           record = 'true',
                           welcome = Welcome % (room))
    # We should maybe return something rather than assuming it worked...

def join_room_url(name, room, as_moderator):
    pw = ATT_PW
    if as_moderator:
        pw = MOD_PW
    return make_request(rooms[room].server, 'join', meetingID = room,
                        fullName = name,
                        password = pw)

#
# Low-level BBB request machinery.
#
def make_request(dest, command, **args):
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
        r = requests.get(url, timeout = 10.0)
    except (ConnectionError, ReadTimeout):
        return None
    if r.status_code != 200:
        return None
    # print(r.text)
    return ElementTree.fromstring(r.text)
