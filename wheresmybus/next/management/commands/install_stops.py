# encoding: utf-8

import logging
import urllib2
import os
import re

from lxml import etree

from django.db import connections
from django.core.management.base import BaseCommand, CommandError
from wheresmybus.settings import MTA_FEED_URL, DDOT_BASE_URL
from wheresmybus.next.models import Point, Stop
from wheresmybus.next.urls import STOP_ID_REGEX

logger = logging.getLogger("wheresmybus")

def get_stop(stop_id, name, lat, lon):
    r = {}
    r["stop_id"] = stop_id
    r["name"] = name
    loc = {}
    loc["lat"] = lat
    loc["lon"] = lon
    r["loc"] = loc

    return Stop(**r)

class Command(BaseCommand):
    help = 'Purge the database and install all the stops.'
    
    def handle(self, *args, **options):
        """ Install the stops.
        """
        
        self.purge()
        self.install_stops()
        self.create_index()
        self.verify()
    
    def purge(self):
        """Removes all the stops.
        """
        
        # see http://django-mongodb.org/topics/lowerlevel.html
        dbwrapper = connections['default']
        stops = dbwrapper.get_collection('next_stop')
        stops.drop()
        
        nb = len(Stop.objects.all())

        if (nb == 0):
            print "Removed all existing data."
        else:
            logger.error("Even after having deleted everything, there are still %d items in db." % nb) 
            raise Exception("Illogical: there are still some elements in the database")

    def install_stops(self):
        stops = []

        # TODO: use django caching to speed up
        print "Downloading data from MTA"
	stops_url = DDOT_BASE_URL + "stop-ids-for-agency/DDOT.xml?key=BETA"
	print stops_url
        logger.info("Calling %s" % stops_url)
        f = urllib2.urlopen(stops_url)

       	feed = etree.parse(f).getroot() 
	print feed
	i = 0
	failedstops = []
	for s in feed.iter ("string"):
		stop_info_url = DDOT_BASE_URL + "stop/" + s.text + ".xml?key=BETA"
		print stop_info_url
		
		try:
			g = urllib2.urlopen(stop_info_url)
			stopdata = etree.parse(g).getroot()
			e = stopdata.find ("data/entry")
			stop_id = e.find("id").text
			lat = e.find("lat").text
			lon = e.find("lon").text
			name = e.find("name").text
      	  		if not Stop.objects.filter(stop_id=stop_id):
                		print "Saving stop #%s" % stop_id
                		stop = get_stop(stop_id, name, lat, lon)
                		stop.save()
                   		i += 1
		except: 
			print "could not load stop " + s.text 
			failedstops.append (s.text)

        print "Installed %d stops." % i
	print failedstops
        return i
    
    def create_index(self):
        """Creates the geospatial index.
        """
        
        os.system('mongo localhost/wheresmybus --quiet --eval \'db.next_stop.ensureIndex({ loc : "2d"})\'')
        print "Created the index."
    
    def verify(self):
        """Verifies the stops format.
        """
        #TODO: put this as a test
        
        stop_id_regex = re.compile(STOP_ID_REGEX)

        # Check if all ids validate against the regex
        invalid_ids = []
        for s in Stop.objects.all():
            if not stop_id_regex.match(str(s.stop_id)):
                invalid_ids.append(s.stop_id)
                logger.error("%d does not validate against the regex" % str(s.stop_id))
        
        if invalid_ids:
            raise Exception("%n stops do not respect the regex." % len(invalid_ids))
        else:
            print "Verified all stop_id."
