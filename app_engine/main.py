import os
import logging
from django.utils import simplejson

from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from twilio import TwilioRestException
from twilio.rest import TwilioRestClient
import configuration


# Data model to store callers
class User(db.Model):
  phone = db.StringProperty()
  date  = db.DateTimeProperty(auto_now_add=True)
##

class MainHandler(webapp.RequestHandler):
    def post(self):
    
      # who called?
      phone = self.request.get('From')
      msg = self.request.get('Body')
      logging.debug('received msg from %s : %s' % (phone,msg))
      
      # create a user instance if we need to
      create_user(phone)
      
      # take a look at the request and see if it is valid
      if msg.isdigit() is False:
        response = 'Snap! I can only accept stop ID numbers'
      else:
        # extract the first result for this stop request
        response = extract_bus_result(msg)

      # reply back to twilio with twiml        
      self.response.headers['Content-Type'] = "text/xml; charset=utf-8"
      self.response.out.write('<Response><Sms>%s</Sms></Response>' % response)

      return
      

## end MainHandler

class GoodbyeHandler(webapp.RequestHandler):
    def get(self):
      users = db.GqlQuery('select * from User').fetch(100)
      for u in users:
        sendSMS(u.phone,'Thanks for coming to Nonprofit Day! Now go build yourself a Twilio app :)')
      

def extract_bus_result(msg):
    url = 'http://www.smsmybus.com/api/v1/getarrivals?key=nomar&stopID=%s' % msg
    result = urlfetch.fetch(url)
        
    # pull out the first result
    json = simplejson.loads(result.content)
    first = json['stop']['route'][0]
    response = 'Route %s will arrive in %s minutes' % (first['routeID'],first['minutes'])
    return response

def create_user(phone):
    user = db.GqlQuery("select * from User where phone = :1", phone).get()
    if user is None:
        logging.debug('adding new user %s to the system' % phone)
        user = User()
        user.phone = phone
        user.put()


def sendSMS(phone,msg):
    """
    Convenience method to send an SMS
    """
    try:
        client = TwilioRestClient(configuration.TWILIO_ACCOUNT_SID,
                                  configuration.TWILIO_AUTH_TOKEN)
        logging.debug('sending message - %s - to %s' % (msg,phone))
        message = client.sms.messages.create(to=phone,
                                             from_=configuration.TWILIO_CALLER_ID,
                                             body=msg)
    except TwilioRestException,te:
        logging.error('Unable to send SMS message! %s'%te)
        
## end sendSMS()



def main():
    logging.getLogger().setLevel(logging.DEBUG)
    application = webapp.WSGIApplication([('/sms', MainHandler),
                                          ('/goodbye', GoodbyeHandler),
                                         ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
