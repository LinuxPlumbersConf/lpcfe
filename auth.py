import hashlib
import ldap
import config
import threading
#
# Cheesy authentication stuff.
#

#
# Speaking of cheesy, here's the cookie scheme.  We start with a super
# duper secret:
#
secret = '1da177e4c3f41524e886b7f1b8a0c1fc7321cac2'
#
# Then, when we log somebody in, we append the secret to their email,
# take a hash of the whole thing, then make a cookie value with the
# email and the hash.  That lets us validate logins without having to
# maintain a session database.
#

class User:
    def __init__(self, id, email, name, roles):
        self.id = id
        self.email = email
        self.name = name
        self.roles = roles

    def is_moderator(self):
        return 'moderator' in self.roles

    def is_admin(self):
        return 'admin' in self.roles

#
# LDAP machinery.
#
ldap_search_base = 'dc=users,dc=2020,dc=linuxplumbersconf,dc=org'
ldap_search_filter = '(cn=%s)'
ldap_attrs = ['givenName', 'sn', 'labeledURI', 'businessCategory']
ldap_conn = None
ldap_lock = threading.Lock()

def ldap_connect():
    global ldap_conn
    ldap_conn = ldap.initialize(config.LDAP_SERVER)
    ldap_conn.simple_bind_s(config.LDAP_USER, config.LDAP_PW)

def ldap_lookup(email):
    with ldap_lock:
        return do_ldap_lookup(email)

def do_ldap_lookup(email):
    #
    # Query the LDAP server.
    #
    ss = ldap_search_filter % (email)
    results = ldap_conn.search_s(ldap_search_base, ldap.SCOPE_ONELEVEL, ss, ldap_attrs)
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

def setup():
    ldap_connect()

def check_password(email, password):
    u = ldap_lookup(email)
    if not u:
        return False
    if password == u.id:
        return u
    return False

#
# Session cookie management.
#
def make_hash(u):
    return hashlib.sha1((u.email + secret).encode('utf8')).hexdigest()

def validate_cookie(cookie):
    sc = cookie.split(':')
    if len(sc) != 2:
        return None
    #
    # This goes to the LDAP server for every hit.  Probably not a
    # terrible thing but we could consider some sort of caching.
    #
    u = ldap_lookup(sc[0])
    if not u:
        return None
    hash = make_hash(u)
    if hash != sc[1]:
        return None
    return u

def make_cookie(u):
    return u.email + ':' + make_hash(u)
