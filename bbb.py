#
# Encapsulate our dealings with BBB
#
import hashlib, requests
from requests.exceptions import ConnectionError
from xml.etree import ElementTree
from urllib.parse import quote_plus
import config

servers = { }  # Just maps name to secret
rooms = { }    # maps name to server

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
                if len(sline) != 2:
                    print('Bad rooms line: "%s"' % line)
                else:
                    if sline[1] not in servers:
                        print('Room %s on bad server %s' % (sline[0], sline[1]))
                    else:
                        rooms[sline[0]] = sline[1]
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
        ret['server'] = server = rooms[room]
    except KeyError:
        return ret
    response = run_request(server, 'getMeetingInfo', meetingID = room)
    status = response.findtext('running')
    if (not status) or (status != 'true'):
        return ret
    ret['running'] = True
    ret['people'] = response.findtext('participantCount')
    ret['listeners'] = response.findtext('listenerCount')
    ret['video'] = response.findtext('videoCount')
    mods = [ ]
    for attendee in response.findall('attendees/attendee'):
        if attendee.findtext('role') == 'MODERATOR':
            mods.append(attendee.findtext('fullName'))
    ret['moderators'] = ', '.join(mods)
    return ret

def all_rooms():
    return sorted(rooms.keys())

# 
def start_room(room):
    server = rooms[room]
    response = run_request(server, 'create', name = room,
                           meetingID = room,
                           attendeePW = ATT_PW,
                           moderatorPW = MOD_PW,
                           logo = config.LOGO_URL,
                           logoutURL = config.SITE_URL,
                           maxParticipants = '250',
                           muteOnStart = 'true')
    # We should maybe return something rather than assuming it worked...

def join_room_url(name, room, as_moderator):
    pw = ATT_PW
    if as_moderator:
        pw = MOD_PW
    return make_request(rooms[room], 'join', meetingID = room,
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
        r = requests.get(url, timeout = 5.0)
    except ConnectionError:
        return None
    # print(r.text)
    return ElementTree.fromstring(r.text)
