import json
from html.parser import HTMLParser
import http.client

DOMAIN = 'xn--pevapakkumised-5hb.ee'
URL_BASE = '/'

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
            print("Found venue name: ", data.strip())
            self._set_state('idle')
            self.current_venue = data.strip()
            if self.current_venue not in self.venue_offers:
                self.venue_offers[self.current_venue] = []
        elif self.state == 'parsing_lunch_offer' and data.strip() != '':
            print("Found lunch offer: ", data.strip())
            self.venue_offers[self.current_venue].append(data.strip())

    #def handle_endtag(self, tag):
        # print("End tag: ", tag)

def streaming_download_and_parse_offers(url):
    parser = LunchHTMLParser()
    conn = http.client.HTTPSConnection(DOMAIN)
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

    print(parser.venue_offers)

    return {}

def get_lunch_offers(city):
    url = get_location_for_city(city)
    return streaming_download_and_parse_offers(url)

def hello(event, context):
    body = {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "input": event
    }

    get_lunch_offers('tartu')

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response

    # Use this code if you don't use the http event with the LAMBDA-PROXY
    # integration
    """
    return {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "event": event
    }
    """
