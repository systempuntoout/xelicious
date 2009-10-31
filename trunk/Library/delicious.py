'''
 A library to access the del.ici.us api via python
 
 see http://del.icio.us/doc/api for more informations about the api

 add(user, passwd, url, description, tags=, extended=, dt=None) => bool
 get(user, passwd, dt=, tag=, count=0) => Post Obj
 get_all(user, passwd) => Post Obj
 delete(user, passwd, url) => bool

 rename_tag(user, passwd, oldtag, newtag) => bool
 get_tags(user, passwd) => xlist Obj

 get_userposts(user) => Post obj
 get_tagposts(tag)  => Post obj
 get_urlposts(url)  => Post obj

 DeliciousAPI -- class to access all functions of del.icio.us
 Post -- uses this to represent data coming from del.icio.us
 Posts -- container obj for Post objects

 - throws a HTTPError with code 503 if encountering a 503 Error.
   503 indicates that the service is currently not available, due to
   technical problems or throtteling.
 - supports limiting of accesses to del.icio.us via limittime variable,
   limittime = dict(calls = 3, time = 4) means, you are allowed to do 3 calls
   in 4 seconds. You can change this to your needs. BUT KEEP IN MIND, that throttling
   by del.icio.us is done on base of the user_agent id, that means not only you
   will be blocked, also all other users with this user_agent id.
 - currently this limiting is done by calling time.sleep(1) until the limiting is
   over. however this may change and result in calling an exception, or in
   allowing the user to choose between this two alternatives.
 - critic and ideas are necessary to improve all this, see
   http://delicious-py.berlios.de/ for more contact and comment infos.

## [0.2.4] bug fix release, fixed an error in the add function. thanks to Greg Wilson to report this bug.
## [0.2.5] there has been a change in the api of del.icio.us // this release corrects the calls to del.icio.us
'''



import re
import xml.parsers.expat
import md5
import httplib
import urllib, urllib2
import time
import datetime

# <TakenFromFeedParser.py>
# timeoutsocket allows feedparser to time out rather than hang forever on ultra-slow servers.
# Python 2.3 now has this functionality available in the standard socket library, so under
# 2.3 you don't need to install anything.  But you probably should anyway, because the socket
# module is buggy and timeoutsocket is better.
try:
    import timeoutsocket # http://www.timo-tasi.org/python/timeoutsocket.py
    timeoutsocket.setDefaultSocketTimeout(20)
except ImportError:
    import socket
    if hasattr(socket, 'setdefaulttimeout'): socket.setdefaulttimeout(20)
# </<TakenFromFeedParser.py>> 




##
# Variablen
version      = '0.2.5'
author       = 'Frank Timmermann'
contact      = 'http://delicios-py.berlios.de/'
debug        = 0
thelicense   = """PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2"""
mail         = "http://www.opensource.org/licenses/PythonSoftFoundation.php or regenkind at users.berlios.de"
throttled_message = 'You encountered a 503 Error Message from the web server.\
The service is temporary not available \
This may indicate that you have been throttled. \
This happens if you access del.icio.us to frequently. Try again later. \
This can also mean, that this service is currently not available. \
If you encounter this while accessing a rss file, this may indicates, that the\
server is under heavy load. Try again later.'

dws_hostname = 'http://del.icio.us/'
dws_realm    = 'del.icio.us API'
dws_api      = 'http://del.icio.us/api/'
user_agent   = 'delicious.py/%(version)s %(contact)s' % {'version':version, 'contact':contact}

limittime = dict(calls = 1, time = 1)

delicious_date_pattern  = re.compile("[1,2][0-9]{3}-[0-2][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]Z")
## delicious_date_strf     = "%Y-%m-%dT%H:%M:%SZ"
## short_date_pattern      = re.compile("[1,2][0-9]{3}-[0-2][0-9]-[0-3][0-9]")
## short_date_strf         = "%Y-%m-%d"

class xlist(list):  pass 
class xbool(object):
    def __init__(self, x):  self.x = x
    def __repr__(self): return str(bool(self.x))

class DeliciousException(Exception):
    '''Std. Error Function'''
    pass

class DefaultErrorHandler(urllib2.HTTPDefaultErrorHandler):
    '''Handles HTTP Error, currently only 503
    Behandelt die HTTP Fehler, behandelt nur 503 Fehler'''
    def http_error_503(self, req, fp, code, msg, headers):
        raise urllib2.HTTPError(req, code, throttled_message, headers, fp)

class Post(dict):
    '''A post dictionary, usefull in this lib.
    Ein post dictionary zugeschnitten auf die Beduerfnisse dieser Bibliothek'''
    args = ["url", "description", "tags", "extended", "dt", "user"]
    def __init__(self, url = "", description = "", tags = "", extended = "", dt = "", user = ""):
        for i in self.args: self[i] = eval(i)

    def __getattr__(self, name):
        try: return self[name]
        except: object.__getattribute__(self, name)
        
    def validate(self):
        return not(self["url"] == "" or self["description"] == "" or not delicious_date_pattern.match(self["dt"]))

class Posts(list):
    '''A list for all the Post objects.
    Eine Liste die einzelne Post Obj enthaelt.'''
    def __getattr__(self, attr):
        try: return [p[attr] for p in self]
        except: object.__getattribute__(self, attr)
    def validate(self):
        return (bool([i for i in self if isinstance(i,(Post,dict))]) and \
                bool([0 for p in self if hasattr(p, "validate") and p.validate()==0]))

class Requester:
    '''class to handle requests to del.icio.us
    >>> Requester(user, passwd).handle_request(post_all, parameter) '''
    def __init__(self, user = "", passwd = ""):
        self.user, self.passwd = user, passwd
        self.timel = [time.time()-3600 for i in range(limittime["calls"]+1)]

    def set_user(self, user, passwd):         
        self.user, self.passwd = user, passwd

    def handle_request(self, request_url, params="", use_request_url_as_is = 0):
        ## keeps time between requests
        self.timel.append(time.time())
        while time.time()-self.timel[0] < limittime["time"]:
            time.sleep(1)
            if 1: print "TIMELIMIT BLOCKED"
        self.timel.pop(0)
        if debug: httplib.HTTPConnection.debuglevel = 1
        authinfo = urllib2.HTTPBasicAuthHandler()
        authinfo.add_password(dws_realm, dws_hostname, self.user, self.passwd)
        opener = urllib2.build_opener(authinfo, DefaultErrorHandler())
        request = urllib2.Request(dws_api + request_url + params)
        if use_request_url_as_is: request = urllib2.Request(request_url)
        request.add_header('User-Agent', user_agent)
        if debug: print "request_url:", request_url
        o = opener.open(request)
        return o.read()
##
# need this, creates a Requester object
req = Requester()

class DeliciousAPI:
    '''class to access delicios, implements the API calls'''
    def __init__(self, user='', passwd=''):
        self.__user, self.__passwd = user, passwd
        req.set_user(user, passwd)
        self.handle_request = req.handle_request
        
    def set_user(self, user, passwd):
        self.__user, self.__passwd = user, passwd
        req.set_user(user, passwd)
        self.handle_request = req.handle_request
        
    def posts_dates(self, tag = ''):
        if tag != "": params = urllib.urlencode({"tag" : tag})
        else: params = ""
        x = self.handle_request("posts/dates?", params)
        p = dXML.posts_dates(x)
        p.xml = x
        return(p)

    def tags_get(self):
        x = self.handle_request("tags/get?")
        p = dXML.tags_get(x)
        p.xml = x
        return(p)
    
    def posts_get(self, tag = '', dt = ''):
        if tag != "" and dt != "":  params = urllib.urlencode({"tag" : tag, "dt" : dt})
        elif tag == "" and dt != "": params = urllib.urlencode({"dt" : dt})
        elif tag != "" and dt == "": params = urllib.urlencode({"tag" : tag})
        elif tag == "" and dt == "": params = ""
        x = self.handle_request("posts/get?", params)
        p = dXML.post(x, self.__user)
        p.xml = x
        return(p)

    def posts_recent(self, tag = "", count = 15):
        if tag == "": params = urllib.urlencode({"count" : count})
        else: params = urllib.urlencode({"tag" : tag, "count" : count})
        x = self.handle_request("posts/recent?", params)
        p = dXML.post(x, self.__user)
        p.xml = x
        return(p)

    def posts_all(self, tag = ""):
        if tag != "":
            params = urllib.urlencode({"tag":tag})
            x = self.handle_request("posts/all?",params)
        else:
            x = self.handle_request("posts/all")
        p = dXML.post(x, self.__user)
        p.xml = x
        return(p)

    def posts_add(self, url, description, extended = '', tags = '', dt =''):
        params = urllib.urlencode({"url" : url, "description" : description,
                                   "extended" : extended, "tags" : tags, "dt" : dt})
        x = self.handle_request("posts/add?", params)
        p = dXML.okay(x)
        p.xml = x
        return(p)

    def posts_delete(self, url):
        x = self.handle_request("posts/delete?", urllib.urlencode({"url" : url}))
        p = dXML.okay(x)
        p.xml = x
        return(p)

    def tags_rename(self, old, new):
        x = self.handle_request("tags/rename?", urllib.urlencode({"old" : old, "new": new}))
        p = dXML.okay(x)
        p.xml = x
        return(p)

    ##def inbox_get(self, dt = ''):
    ##    return self.handle_request(inbox_get, urllib.urlencode({'dt':dt}))

    ##def inbox_dates(self):
    ##    return self.handle_request(inbox_dates)

    ##def inbox_subs(self):
    ##    return self.handle_request(inbox_subs)

    ##def inbox_sub(self, user, tag = ''):
    ##    return self.handle_request(inbox_sub, urllib.urlencode({'user': user, 'tag': tag}))

    ##def inbox_unsub(self, user, tag = ''):
    ##    return self.handle_request(inbox_unsub, urllib.urlencode({'user': user, 'tag': tag}))

class DeliciousNOTAPI:
    '''class to access other services of delicios'''
    handle_request = req.handle_request

    def get_posts_by_user(self, user, tag = ''):
        request_url = '''http://del.icio.us/rss/%s'''%user
        if tag != '': request_url += '''/%s'''%tag
        return dXML.rss(self.handle_request(request_url,"", 1))

    def get_posts_by_tag(self, tag):
        request_url = '''http://del.icio.us/rss/tag/%s'''%tag
        return dXML.rss(req.handle_request(request_url,"", 1))

    def get_popular(self, tag=""):
        request_url = '''http://del.icio.us/rss/popular/%s'''%tag
        return dXML.rss(req.handle_request(request_url,"", 1))

    def get_posts_by_url(self, url):
        ### uses the html to parse ###
        request_url = '''http://del.icio.us/url/%s'''%(md5.md5(url).hexdigest())
        htmlcode = urllib.urlopen(request_url).read()
        return HTPfeed(htmlcode)
        
class DeliciousXML:
    '''Handle XML Stuff'''
    def okay(self, s):
        self.OKAY = None
        def start_element(name, attrs):
            if name == "result" and attrs.has_key("code") and attrs["code"] == "something went wrong": self.OKAY = False
            if name == "result" and attrs.has_key("code") and attrs["code"] == "done": self.OKAY = True
        def char_data(data):
            if data == "something went wrong": self.OKAY = False
            if data == "done": self.OKAY = True
        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = start_element
        p.CharacterDataHandler = char_data
        p.Parse(s)
        if self.OKAY == None: raise DeliciousException, "xml_okay was called with with wrong input: %s"%s
        p = xbool(self.OKAY)
        p.xml = s
        return p

    def post(self, s, user):
        def start_element(name, attrs):
            if name == "post":
                d = Post(url = attrs["href"],
                         description = attrs["description"],
                         tags = attrs["tag"],
                         dt = attrs["time"],
                         user = user,
                         extended = (attrs.has_key("extended") and attrs["extended"]) or "")
                posts.append(d)
        posts = Posts()
        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = start_element
        p.Parse(s)
        posts.xml = s
        return posts

    def tags_get(self, s):
        def start_element(name, attrs):
            if name == "tag": posts.append(dict(count = attrs["count"], tag = attrs["tag"]))
        posts = xlist()
        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = start_element
        p.Parse(s)
        posts.xml = s
        return posts

    def posts_dates(self, s):
        def start_element(name, attrs):
            if name == "date": posts.append(dict(count = attrs["count"], date = attrs["date"]))
        posts = xlist()
        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = start_element
        p.Parse(s)
        posts.xml = s
        return posts

    def rss(self, s):
        def start_element(name, attrs):
            if name == "item":
                self.in_item = 1
                self.post = dict(url = "", description = "", tags = "", dt = "", extended = "", user="")
            self.start_element = name
        def char_data(data):
            if self.in_item == 0: self.start_element = ""
            if self.start_element == "link":        self.post["url"] += data.strip()
            if self.start_element == "title":       self.post["description"] += data.strip()
            if self.start_element == "description": self.post["extended"] += data.strip()
            if self.start_element == "dc:date":     self.post["dt"] += data.strip()
            if self.start_element == "dc:subject":  self.post["tags"] += data.strip()
            if self.start_element == "dc:creator":  self.post["user"] += data.strip()
        def end_element(name):
            self.start_element = ""
            if name == "item":
                self.in_item = 0
                self.posts.append(self.post)
        try:
            self.in_item = 0
            self.posts = Posts()
            self.post = dict(href = "", description = "", tag = "", time = "", extended = "", user = "")
            p = xml.parsers.expat.ParserCreate()
            p.StartElementHandler = start_element
            p.CharacterDataHandler = char_data
            p.EndElementHandler = end_element
            p.Parse(s)
            self.posts.xml = s
        except xml.parsers.expat.ExpatError, e:
            print s, e; raise Exception
        return self.posts

##
# need this, create a XML parser object
dXML = DeliciousXML()

##
## some functions, that may help

def add(user, passwd, url, description, tags = "", extended = "", dt = None):
    if dt == None: dt = datetime.datetime.now()
    return DeliciousAPI(user, passwd).posts_add(url, description, extended, tags, dt)

def get(user, passwd, tag="", dt="",  count = 0):
    posts = DeliciousAPI(user, passwd).posts_get(tag,dt)
    if count != 0: posts = posts[0:count]
    return posts

def get_all(user, passwd, tag = ""):
    return DeliciousAPI(user, passwd).posts_all(tag)

def delete(user, passwd, url):
    return DeliciousAPI(user,passwd).posts_delete(url)

def rename_tag(user, passwd, oldtag, newtag):
    return DeliciousAPI(user,passwd).tags_rename(oldtag, newtag)

def get_tags(user, passwd):
    return DeliciousAPI(user,passwd).tags_get()

##
## not API conform functions for delicious
## !!! only the last 25????
def get_userposts(user):
    return DeliciousNOTAPI().get_posts_by_user(user)

def get_tagposts(tag): 
    return DeliciousNOTAPI().get_posts_by_tag(tag)

def get_urlposts(url): 
    return DeliciousNOTAPI().get_posts_by_url(url)

def get_popular(tag = ""):
    return DeliciousNOTAPI().get_popular(tag)
###############################################################################################
## this was  covered in htmltoposts
'''part of the delicious.py lib - see more informations in that file

it is a helper to handle the html files that are generated by the del.icio.us/url/thing.
as long as there is no rss feed for this, I must use this. Perhaps it will become part of
the rest api?'''

import sgmllib

class HtmlToPosts(sgmllib.SGMLParser):
    def __init__(self):
        sgmllib.SGMLParser.__init__(self)
        self.in_delNav = 0
        self.list_delNav = []
        self.in_extended = 0 
        self.in_delLink = 0
        self.Posts = Posts()
        self.Post = Post
        self.url = ""
        self.extended = ""
        self.delLink = ""
        
    def start_a(self, attrib):
        if ("class", "delNav") in attrib: self.in_delNav = 1
        if ("class", "delLink") in attrib:
            self.in_delLink = 1
            for i in attrib:
                if i[0] == "href": self.url = i[1]
            
    def start_div(self, attrib):
        if ('style', 'font-size: 90%; margin-left: 1em;') in attrib: self.in_extended = 1
        if ("class", "delPost") in attrib:
            if self.url =="" : pass
            else:
                url = self.url
                des = self.delLink
                ext = self.extended
                dt  = self.list_delNav.pop()
                usr = self.list_delNav.pop()
                tgs = " ".join(self.list_delNav)
                self.Posts.append(self.Post(url, des, tgs, ext, dt, usr))
                self.url, self.delLink, self.extended, self.list_delNav = "","","",[]
        
    def end_a(self):
        if self.in_delNav == 1: self.in_delNav = 0
        elif self.in_delLink == 1: self.in_delLink = 0

    def end_div(self):
        if self.in_extended == 1: self.in_extended = 0

    def handle_data(self, data):
        if self.in_delNav == 1: self.list_delNav.append(data)
        if self.in_extended == 1: self.extended = data
        if self.in_delLink == 1: self.delLink = data

def HTPfeed(s):
    p = HtmlToPosts()
    p.feed(s)
    return p.Posts


##
## main
if __name__ == "__main__":
    import pydoc
    import delicious
    print "Read delicious.html for more informations about this script"
    pydoc.writedoc("delicious",1)
