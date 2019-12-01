
#
# webscrape_nps.py
#
# Scrapes all of the national parks from the nps.gov website, and then geocodes them using Google API and saves list to a pipe-delimited file
#  Dan Stober
#  2019-11-30
#
#  Saved on github in my webscraping project
#
###############################################################################################################################

import re
import urllib.request
from bs4 import BeautifulSoup

import os

import requests
import json

#Google maps API key
KEY = "***************************************"

READ = "r"
WRITE = "w"
APPEND = "a"
READWRITE = "w+"
BINARY = "b"

v_FilePath = 'c:\\Users\\Dan\\Documents'
v_FileName = 'nps_units_geocodes.txt'
v_WriteFileName = os.path.join ( v_FilePath, v_FileName )

gps_lookup_errors_list = []

#This splits the component pieces of the NPS unit name into values to be passed into the URL
#First, split at comma (if any), then split any spaces
def split_park_name_for_url ( unit_name_in ):
    url_component = []
    comma_split = unit_name_in.split(',')
    if comma_split == None:
        comma_split = [unit_name_in]	
    for chunk in comma_split: 
        space_split = chunk.split ( ' ')
        if space_split == None:
            space_split = [chunk]		
        for component in space_split:
            url_component.append(component)		
    
    for i, c in enumerate ( url_component ):
        if i == 0:
            retval = 'address={}'.format(c)		
# Not passing city,state, so no comma needed in URL
#        elif i == len(url_component)-2:
#            retval = "{}+{},".format(retval,c)
        else:
            retval = "{}+{}".format(retval,c)

    return retval		
# The result should look like this...
# https://maps.googleapis.com/maps/api/geocode/json?address=Canyonlands+National+Park&key=*******************************************

def getLatLong ( unit_name ):

    url_string = 'https://maps.googleapis.com/maps/api/geocode/json?{}&key={}'.format( split_park_name_for_url ( unit_name ),KEY )
    resp = requests.get( url_string )

    if resp.status_code != 200:
        # This means something went wrong.
        raise ApiError('GET /tasks/ {}'.format(resp.status_code))

    try:
        return (  resp.json()['results'][0]['geometry']['location'] )
    except: 
        error_dict = {}
        error_dict['unit_name'] =  unit_name 
        error_dict['url_string'] =  url_string 
        error_dict['json_returned'] = resp.json() 
        print ( 'GPS Lookup error!\n{}\n ++++++++++++++++++++++++++++++++++'.format( error_dict ))
        gps_lookup_errors_list.append ( error_dict )
        return ( {'lat': None, 'lng': None} )


def getparks_bystate (  state ): 
 # The states are embedded into the url, so we are really just collecting all of the parks on a particular page
    url = 'https://www.nps.gov/state/{}/index.htm'.format ( state.lower() )

    html = urllib.request.urlopen( url )
    soup = BeautifulSoup(html, 'html.parser')

    #There is a series of h2 and h3 tags that contain the type (National Park, etc) in the h2 followed by the name in the h3 tag    
    #There are a couple extra h2 tags that are not park unit related, but those have a class attribute, so we can ignore them
    h2 = soup.find_all('h2', class_=None )
    h3 = soup.find_all('h3', class_=None )
	
#These are the ways you can find the tags with NO class
#attrs={'class': None}
#soup.find_all(class_=None)
#soup.find_all(class_=False)

    ret_list = []
    for ( park, type ) in zip ( h3, h2 ):
        ret_list.append ( ( park.get_text(), type.get_text(), state ) ) 	

    return ret_list

STATES = [ 'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA'
         , 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD'
         , 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ'
         , 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC'
         , 'SD', 'TX', 'UT', 'VT', 'TN', 'VA', 'WA', 'WV', 'WI', 'WY'
         , 'AS', 'DC', 'FM', 'GU', 'MH', 'MP', 'PW', 'PR', 'VI' ]

PLACES_WITHOUT_NPS_SITES = [ 'FM', 'MH', 'PW' ]

STATES = sorted ( list ( set ( STATES ) - set ( PLACES_WITHOUT_NPS_SITES ) ) )

# I decided to remove the missing values using set subtraction instead
##	#These three territories have no NPS sites
##  STATES.remove( 'FM' )
##  STATES.remove( 'MH' )
##  STATES.remove( 'PW' )

parks_list = []

for state in STATES:

    print ( 'Processing {}...'.format ( state ))
    parks_list += getparks_bystate ( state )
#This result is a list of Tuples in this format ( park, type, state)	

#### Remove duplicates section.
### There are duplicates because any park which is in more than one state appears in each state page (eg:Yellowstone)

_unit_types = []
_unit_names = []
_units      = []

unit_dict_states_list = {}
unit_dict_types = {}

for _entry in parks_list:
    unit = '{} {}'.format( _entry[0],_entry[1]) 
	
    if unit not in unit_dict_states_list.keys():
       unit_dict_states_list [ unit ] = [ ]
	
    unit_state = _entry[2]
    _unit_types.append ( _entry[1] )
    _unit_names.append ( _entry[0] )
    _units.append ( unit ) 

    unit_dict_states_list [ unit ].append (  unit_state )
    unit_dict_types [ unit ] = _entry[1]

 
# Performing a SET intersect on the same set to itself, will result in a set with only unique values
unique_unit_types = set ( _unit_types ) & set ( _unit_types ) 
unique_unit_names = set ( _unit_names ) & set ( _unit_names ) 
unique_units      = set ( _units ) & set ( _units ) 

final_list = []

for i, unit in enumerate(unique_units):

    if i%10==0:
        print ( 'Geocoding calls. {} of {}...'.format ( i, len( unique_units )))

    #This creates a list of Tuples. The tuples consist of four components ( park name, park type, [state(s)], {gps} )
	#   The state(s) component is a list -- even for parks which are only in one state
	#  The GPS component is a dictionary, with keys for lat and lng 
	
    final_list.append ( ( unit,  unit_dict_types [ unit ], unit_dict_states_list [unit] ,  getLatLong ( unit ) ) )

with open(v_WriteFileName, WRITE, encoding = "utf-16" ) as WriteFile:
	
    WriteFile.write( '{}|{}|"{}"|{}|{}\n'.format ( "Unit","Type","State(s)","Latitude","Longitude" ) )
    for x in final_list:

        try:
            WriteFile.write( '{}|{}|"{}"|{}|{}\n'.format ( x[0],x[1],x[2],x[3]['lat'],x[3]['lng'] ) )
        except:
            print ( 'Exception on {}'.format(x[0]))
            print ( '{}|{}|"{}"|{}|{}'.format ( x[0],x[1],x[2],x[3]['lat'],x[3]['lng'] ) )
            raise
		
    WriteFile.write( 'File created by python webscraping {}\n'.format ( 'C:\\dan\\learn\\python\\webscrape_projects\\webscrape_nps.py') ) 
  
print ( 'COMPLETE')
print ( 'NPS units written to file = {}'.format ( len ( final_list )))
print ( 'GPS lookup errors = {}'.format ( len(gps_lookup_errors_list)))
