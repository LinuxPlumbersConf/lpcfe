import hashlib
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

Users = { }

class User:
    def __init__(self, id, email, name, mod):
        self.id = id
        self.email = email
        self.name = name
        self.moderator = mod

def load_lines(f, mod):
    for line in f.readlines():
        if len(line.strip()) == 0 or line[0] == '#':
            continue
        sline = line.strip().split(':')
        if len(sline) != 3:
            print("Bad user line: '%s'" % (line[:-1]))
            continue
        u = User(sline[2], sline[0], sline[1], mod)
        if u.email in Users:
            print('Duplicate user %s' % (u.email))
            continue
        Users[u.email] = u

def load_file(name, mod):
    try:
        with open(name, 'r') as f:
            load_lines(f, mod)
    except FileNotFoundError:
        print('Unable to open "%s"' % (name))

def load_users():
    load_file('users', False)
    load_file('moderators', True)

def check_password(email, password):
    try:
        u = Users[email]
    except KeyError:
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
    try:
        u = Users[sc[0]]
    except KeyError:
        return None
    hash = make_hash(u)
    if hash == sc[1]:
        return u
    return None

def make_cookie(u):
    return u.email + ':' + make_hash(u)
