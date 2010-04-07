#!/usr/local/bin/python

# pesterPM.py -- send bulk tweets to MPs using twitter oauth
# -nsh (06/04/10) 

import csv
import urllib
import twitter
import oauth
import logging
import time
import random

import cgi
import Cookie

from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.labs import taskqueue




from twitterkeys import *

request_token_URL = "http://twitter.com/oauth/request_token"
request_token_URL = "http://twitter.coTypeError: cannot concatenate 'str' and 'Morsel' objectsm/oauth/access_token"
authorize_URL = "http://twitter.com/oauth/authorize"

callback_url = "http://pesterMP.appspot.com/callback.py"

members_CSV = "http://mps.monstermischief.com/data/mps.csv"

members_file = open("members.csv")

tehshiz = csv.reader(members_file)

MPtwits = [row[4] for row in tehshiz if len(row) == 5][1:]
testtwits = ["unftest", "meh3232", "meh65232", "meh62352", "meh2632623", "meh2363533", "meh23523"] 

recept = MPtwits 

def start_tweets(username, client_token, client_secret, message):    
    for t in recept:
        taskqueue.add(url='/send.py', params={'username': username,
                                              'target': t, 
                                              'token': client_token, 
                                              'secret': client_secret, 
                                              'message': message})
        logging.debug("Queued tweet from user " + username + ": " + message)
    
def tweet(client, client_token, client_secret, message):
    additional_params = {
        "status": message,
    }
    
#    logging.debug("(Would have) sent tweet: " + message)

    result = client.make_request(
        "http://twitter.com/statuses/update.json",
        token=client_token,
        secret=client_secret,
        additional_params=additional_params,
        method=urlfetch.POST)
    
    logging.debug("Response: " + str(result.status_code) + str(result.content))
    
    if int(result.status_code) == 200:
        return True
    else:
        return False

class SentTo(db.Model):
    user = db.UserProperty()
    MPs = db.StringListProperty()

class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.out.write(open("pester01.html").read())

class Login(webapp.RequestHandler):
    def get(self):
        client = oauth.TwitterClient(consumer_key, consumer_secret, callback_url)
        self.redirect(client.get_authorization_url())

class CallbackHandler(webapp.RequestHandler):
  def get(self):
    client = oauth.TwitterClient(consumer_key, consumer_secret, callback_url)
    auth_token = self.request.get("oauth_token")
    auth_verifier = self.request.get("oauth_verifier")
    user_info = client.get_user_info(auth_token, auth_verifier=auth_verifier)
    username = user_info['username']
    token = user_info['token']
    secret = user_info['secret']
    html = open("pester02.html").read()
    html = html.replace('%UNAME%','<a href="http://twitter.com/' + username + '">@' + username + '</a>')
    html = html.replace('%AUTH%','<input type="hidden" name="username", value='+username+'><input type="hidden" name="token", value='+token+'><input type="hidden" name="secret", value='+secret+'>')
    self.response.out.write(html)

class PostHandler(webapp.RequestHandler):
    def post(self):
           
        client_token = self.request.get('token')
        client_secret = self.request.get('secret')
        username =  self.request.get('username')
        message = self.request.get('text')
        
        prevsent = SentTo.get_or_insert(username)
        SentTo.delete(prevsent)
 
        cookie = Cookie.SimpleCookie()
        cookie['username'] = username
        
        self.response.headers.add_header('Set-Cookie:', cookie.output(header=''))
        self.redirect("progress.py")
        
        start_tweets(username, client_token, client_secret, message)

class ProgressHandler(webapp.RequestHandler):
    def get(self):
        
        cookie = Cookie.SmartCookie()
        cookie.load(self.request.headers.get('Cookie'))
        
        if cookie.has_key('username'):
            username = cookie['username'].value

        sent = SentTo.get_or_insert(username).MPs
        sentstr = "Sent for %s -- " % ('<a href="http://twitter.com/'+username+'">@'+username+'</a>') + ", ".join(map(lambda x: '<a href="http://twitter.com/'+x+'">@'+x+'</a>',sent)) + " -- %d / %d = %.2f%%" % (len(sent), len(recept), (100.0 * len(sent) / len(recept)))
        html = open("pester03.html").read()
        html = html.replace("%SENT%",sentstr)
        self.response.out.write(html)


class TweetSender(webapp.RequestHandler):
    def post(self):
            
        t = self.request.get('target')
        client_token = self.request.get('token')
        client_secret = self.request.get('secret')
        username = self.request.get('username')
        message = self.request.get('message')        
        
        client = oauth.TwitterClient(consumer_key, consumer_secret, callback_url)
        twit = "@"+t+" "+message
        
        def txn(key, t):
            sent = db.get(key)
            sent.MPs.append(t)
            db.put(sent)
            logging.debug("Current sent-to list:" + ",".join(sent.MPs))

        if tweet(client, client_token, client_secret, twit[:139]):
            logging.debug("Sent tweet from user " + username + ": " + twit)        
            sent = SentTo.get_or_insert(username)            
            db.run_in_transaction(txn,sent.key(),t)
        else:
            delay = random.randint(2 * 60,10 * 60)
            logging.debug("Failed to send tweet for user " + username + ". Requeuing to execute at " + time.asctime(time.localtime(time.time() + delay)))
            taskqueue.add(url='/send.py', countdown=delay, params={'username': username,
                                                                   'target': t, 
                                                                   'token': client_token, 
                                                                   'secret': client_secret, 
                                                                   'message': message})
           

application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/login.py', Login),
                                      ('/callback.py', CallbackHandler),
                                      ('/progress.py', ProgressHandler),
                                      ('/send.py', TweetSender),
                                      ('/post.py', PostHandler)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

# self.redirect(client.get_authorization_url())

