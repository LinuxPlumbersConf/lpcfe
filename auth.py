#
# The quick-n-dirty LPC BBB frontend system
#   Copyright 2020 Jonathan Corbet <corbet@lwn.net>
#   Copyright 2020 Guy Lunardi <guy@linux.com>
# Redistributable under the terms of the GNU General Public License,
# version 2 or greater
#
import hashlib
import ldap
import config
import threading
import base64

import ldap.ldapobject, ldapurl

#
# Cheesy authentication stuff.
#

class User:
    def __init__(self, id, email, name, roles):
        self.id = id
        self.email = email
        self.name = name
        self.roles = roles

    def is_moderator(self):
        if self.is_admin():
            return 'moderator'
        return 'moderator' in self.roles

    def is_admin(self):
        return 'admin' in self.roles

class GuestUser(User):
    def __init__(self, name):
        User.__init__(self, 'guest', 'guest', name, [])
#
# flat-file auth stuff.  This works with three files located in the
# configuration directory:
#
#  admins	users with admin access (includes moderation)
#  moderators	users with mod access
#  users	plain boring users
#
# Each file is just a set of simple lines:
#
#  email password full-name
#
# If somebody puts a space into a password life will not be happy.
#
FF_users = { }

def ff_load_file(file, roles):
    ret = { }
    with open(file, 'r') as data:
        for line in data.readlines():
            line = line.strip()
            if (line == '') or (line[0] == '#'):
                continue
            sline = line.split()
            if len(sline) < 3:
                print('Funky line in %s: "%s"' % (file, line))
                continue
            u = User(sline[1], sline[0], ' '.join(sline[2:]), roles)
            FF_users[sline[0].lower()] = u

def ff_load():
    ff_load_file(config.CONFIG_DIR + '/admins', ['admin', 'moderator'])
    ff_load_file(config.CONFIG_DIR + '/moderators', ['moderator'])
    ff_load_file(config.CONFIG_DIR + '/users', [])

def ff_lookup(email):
    return FF_users.get(email.lower(), None)
#
# LDAP machinery.
#
ldap_search_base = 'dc=users,dc=lpc,dc=events'
ldap_search_filter = '(cn=%s)'
ldap_attrs = ['givenName', 'sn', 'labeledURI', 'businessCategory']
ldap_conn = None
ldap_lock = threading.Lock()

def ldap_initialize(server):
    ldap_url = ldapurl.LDAPUrl(server)

    return ldap.ldapobject.ReconnectLDAPObject(ldap_url.initializeUrl())

def ldap_connect():
    global ldap_conn
    ldap_conn = ldap_initialize(config.LDAP_SERVER)
    print(type(ldap_conn))
    ldap_conn.simple_bind_s(config.LDAP_USER, config.LDAP_PW)

def ldap_lookup(email):
    with ldap_lock:
        return do_ldap_lookup(email)

def do_ldap_lookup(email):
    #
    # Query the LDAP server.
    #
    ss = ldap_search_filter % (email)
    try:
        results = ldap_conn.search_s(ldap_search_base, ldap.SCOPE_ONELEVEL, ss, ldap_attrs)
    except ldap.NO_SUCH_OBJECT:
        return None
    if not results:
        return None
    #
    # Now dig into the response to eventually get the stuff we're after.
    #
    try:
        results = results[0][1] # it's down there somewhere!
        id = results['labeledURI'][0].decode('utf8') # it *must* be in there somewhere!
        name = '%s %s' % (results['givenName'][0].decode('utf8'),
                          results['sn'][0].decode('utf8'))
    except (KeyError, IndexError):
        print('Screwy LDAP response: %s' % (results))
        return None
    try:
        roles = [ res.decode('utf8') for res in results['businessCategory'] ]
    except (KeyError, IndexError):
        roles = [ ]
    return User(id, email, name, roles)

def lookup(email):
    if config.AUTH_MODE == 'flat':
        return ff_lookup(email)
    return ldap_lookup(email)

#
# Externally visible interface here.

Logfile = None

def setup():
    global Logfile
    
    if config.AUTH_MODE == 'flat':
        ff_load()
    else:
        ldap_connect()
    if config.LOGFILE:
        Logfile = open(config.LOGFILE, 'a')

def check_password(email, password):
    u = lookup(email)
    if not u:
        return False
    if password == u.id:
        return u
    return False

#
# Session cookie management.
#
# Speaking of cheesy, here's the cookie scheme.  We start with a super
# duper secret (config.AUTH_SECRET).
#
# Then, when we log somebody in, we append the secret to their email,
# take a hash of the whole thing, then make a cookie value with the
# email and the hash.  That lets us validate logins without having to
# maintain a session database.
#
#
def make_hash(u):
    return hashlib.sha1((u.email + config.AUTH_SECRET).encode('utf8')).hexdigest()

def validate_cookie(cookie):
    cookie = decode_cookie(cookie)
    sc = cookie.split(':')
    if len(sc) != 2:
        return None
    #
    # Is this a guest login?
    #
    if config.GUEST_ALLOWED and (sc[1] == '$$GUEST'):
        return GuestUser(sc[0])
    #
    # This goes to the LDAP server for every hit.  Probably not a
    # terrible thing but we could consider some sort of caching.
    #
    u = lookup(sc[0])
    if not u:
        return None
    hash = make_hash(u)
    if hash != sc[1]:
        return None
    if Logfile:
        Logfile.write('%s\n' % (u.name))
        Logfile.flush()
    return u

def make_cookie(u):
    return encode_cookie(u.email + ':' + make_hash(u))

def make_guest_cookie(name):
    return encode_cookie(name + ':' + '$$GUEST')

#
# This mess is required to get cookies back unmangled from Firefox.
#
def encode_cookie(cookie):
    return base64.b64encode(cookie.encode('utf8')).decode('ascii')

def decode_cookie(cookie):
    return base64.b64decode(cookie).decode('utf8')
