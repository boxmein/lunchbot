import json
from html.parser import HTMLParser
import http.client
from urllib.parse import parse_qs
import ssl

DOMAIN = 'päevapakkumised.ee'
URL_BASE = '/'
DEFAULT_VENUES = ['rp9', 'göök']

cache = {}

def get_location_for_city(city):
    if city in ['tallinn', 'tartu']:
        return URL_BASE + city
    else:
        return None

class LunchHTMLParser(HTMLParser):
    venue_offers = {}
    current_venue = None
    state = 'idle'

    def _find_classname(self, attrs):
        if len(attrs) == 0:
            return None
        for (name, value) in attrs:
            if name == 'class':
                return value

    def _is_start_venue(self, tag, attrs):
        return tag == 'div' and self._find_classname(attrs) == 'dinerInfo'

    def _is_start_offer(self, tag, attrs):
        return tag == 'div' and self._find_classname(attrs) == 'offer'

    def _is_price_tag(self, tag, attrs):
        return tag == 'strong'

    def _set_state(self, state):
        if state in ['idle', 'parsing_venue_name', 'parsing_lunch_offer', 'parsing_price']:
            self.state = state
        else:
            print("Error: invalid state", state)

    def _set_current_venue(self, venue):
        self.current_venue = venue
        if venue not in self.venue_offers:
            self.venue_offers[venue] = {}

    def handle_starttag(self, tag, attrs):
        # print("Start tag: ", tag, attrs)

        if self._is_start_venue(tag, attrs):
            self._set_state('parsing_venue_name')

        if self._is_start_offer(tag, attrs):
            self._set_state('parsing_lunch_offer')

        if self.state == 'parsing_lunch_offer' and self._is_price_tag(tag, attrs):
            self._set_state('parsing_price')

    def handle_data(self, data):
        if self.state == 'parsing_venue_name' and data.strip() != '':
            # print("Found venue name: ", data.strip())
            self._set_state('idle')
            self.current_venue = data.strip()
            if self.current_venue not in self.venue_offers:
                self.venue_offers[self.current_venue] = []
        elif self.state == 'parsing_lunch_offer' and data.strip() != '':
            # print("Found lunch offer: ", data.strip())
            self.venue_offers[self.current_venue].append(data.strip())

    #def handle_endtag(self, tag):
        # print("End tag: ", tag)

def streaming_download_and_parse_offers(url):
    parser = LunchHTMLParser()
    conn = http.client.HTTPSConnection(DOMAIN, check_hostname=False, context=ssl._create_unverified_context())
    headers = { 'Connection': 'close' }
    conn.request('GET', url, None, headers)
    response = conn.getresponse()

    if response.status != 200:
        print("Received non-200 response!")
        return None

    while not response.closed:
        res_data = response.read(8192).decode('utf-8')
        if len(res_data) == 0:
            break
        parser.feed(res_data)

    return parser.venue_offers

# Downloads and parses the lunch offers for a given city.
def get_lunch_offers(city):
    if city not in cache:
        url = get_location_for_city(city)
        offers = streaming_download_and_parse_offers(url)
        cache[city] = offers
    return cache[city]



# Builds a string out of the lunch offers.
def format_lunch_offers(lunch_offers, venues_filter=None):
    if lunch_offers is None:
        return "No lunch offers available :("

    message = "Lunch offers for you today!\n"

    all_offers = lunch_offers.items()
    for (index, (venue, offers)) in enumerate(all_offers):
        if venues_filter is not None:
            print("Applying filter:", venues_filter, venue)
            venue_pat = venue.lower()
            keep_venue = False
            for filt in venues_filter:
                if filt in venue_pat:
                    keep_venue = True
            if not keep_venue:
                continue

        if index > 5:
            break
        message += "*{}*: {}\n".format(venue, offers[0])
    return message

# Slack Slash Command handler
def slack(event, context):
    query = None

    if 'body' in event:
        query = parse_qs(event['body'])

    venue_filter = []
    city = 'tartu'

    if 'queryStringParameters' in event:
        query = event['queryStringParameters']
        if 'venues' in query:
            venue_filter = query['venues'][0:512].split(',')
        if 'city' in query and query['city'] in ['tallinn', 'tartu']:
            city = query['city']

    offers = get_lunch_offers(city)
    message = format_lunch_offers(offers, venue_filter)

    response = {
        "statusCode": 200,
        "body": message
    }

    return response
