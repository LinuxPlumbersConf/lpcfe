#!/usr/bin/env python3
#
# The quick-n-dirty LPC BBB frontend system
#   Copyright 2020 Jonathan Corbet <corbet@lwn.net>
#   Copyright 2020 Guy Lunardi <guy@linux.com>
#   Copyright 2023 Mike Rapoport <rppt@kernel.org>
# Redistributable under the terms of the GNU General Public License,
# version 2 or greater
#
#
# Interface to Indico (to get the schedule mainly)
#
import requests
import argparse
import config

def parse_timetable():
    url = '%s/export/timetable/%d.json?ak=%s&pretty=yes' % (config.INDICO_SERVER,
                                                            config.EVENT_ID,
                                                            config.INDICO_API_KEY)
    r = requests.get(url)
    if r.status_code != 200:
        print('Bad status %d getting timetable' % (r.status_code))
        return

    sessions = decrypt_indico_json(r.json())
    with open(options.sessions_file, "wt") as f:
        for s in sessions:
            f.write("%s\n" % s)

#
# Get slotId:title pairs for each session slot in Indico timetable
#
def decrypt_indico_json(j):
    days = j['results'][str(config.EVENT_ID)]
    sessions = []
    for day in days.values():
        for item in day.values():
            if item['entryType'] == 'Session':
                slotId = item['sessionSlotId']
                title = item['title']
                room = item['room']
                sessions.append("%s:%s:%s" % (slotId, title, room))
            elif item['entryType'] == 'Contribution':
                pass
            else:
                print('Unknown entry', item['id'], item['entryType'])
    return sessions


def load_configs():
    cdir = options.config
    config.load_config(cdir)


parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', dest = 'config', default = './conf')
parser.add_argument('-s', '--sessions', dest = 'sessions_file', default = 'sessions')
options = parser.parse_args()

load_configs()
parse_timetable()
