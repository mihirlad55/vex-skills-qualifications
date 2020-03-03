#!/usr/bin/env python3

from requests import get
from requests import post
import json

from enum import Enum
import lxml.html
import lxml.etree

from re import search

import urllib.parse

ROBOTEVENTS_EVENTS_API = "https://www.robotevents.com/api/events"
ROBOTEVENTS_PROGRAMS_API = "https://www.robotevents.com/api/programs"
ROBOTEVENTS_EVENTS_SEARCH_URL = "https://www.robotevents.com/robot-competitions/all"
ROBOTEVENTS_EVENTS_PAGE_PREFIX_URL = "https://www.robotevents.com/robot-competitions"
ROBOTEVENTS_SKILLS_API_URL = "https://www.robotevents.com/api/seasons/131/skills?post_season=1&grade_level=College"

ROBOTEVENTS_PROGRAM_MAP = {
    "VIQC": "vex-iq-challenge",
    "VRC": "vex-robotics-competition",
    "VEXU": "college-competition",
    "TIQC": "tsaviqc",
    "TVRC": "tsavrc",
    "CREATE": "create-foundation",
    "WORKSHOP": "workshops",
    "RAD": "rad",
    "DIS": "drones-in-school",
    "NRL": "national-robotics-league"
}

class RobotEvents:
    class Program:
        def __init__(self, dictionary):
            # Only set the following keys as class attributes
            allowed_keys = ['id', 'name', 'abbr']
            for k in dictionary.keys():
                if k in allowed_keys:
                    setattr(self, k, dictionary[k])

            # Add seasons as objects
            self.seasons = []
            for season in dictionary['seasons']:
                self.seasons.append(self.Season(season, self))


        def get_current_season(self):
            sorted_seasons = sorted(self.seasons, reverse=True, key = lambda i: i.id)
            return sorted_seasons[0]

        class Season:
            def __init__(self, dictionary, program):
                # Only set the following keys as class attributes
                allowed_keys = ['id', 'name', 'start_year', 'end_year']
                for k in dictionary.keys():
                    if k in allowed_keys:
                        setattr(self, k, dictionary[k])

                self.program = program


            def get_events(self, **kwargs):
                events = RobotEvents.get_events(programs=[self.program.id],
                                                season=self, **kwargs)
                return events


            def __repr__(self):
                return json.dumps({
                    'id': self.id,
                    'name': self.name,
                    'start_year': self.start_year,
                    'end_year': self.end_year
                }, indent=2)

            def __str__(self):
                return self.name



    class Event:
        def __init__(self, dictionary, season):
            # Only set the following keys as class attributes
            allowed_keys = ['id', 'lat', 'lng', 'date', 'sku', 'address',
                            'name', 'phone', 'email', 'program_slug',
                            'webcast_link', 'event_entity_id']
            for k in dictionary.keys():
                if k in allowed_keys:
                    setattr(self, k, dictionary[k])

            self.event_url = (ROBOTEVENTS_EVENTS_PAGE_PREFIX_URL + "/" +
                    ROBOTEVENTS_PROGRAM_MAP[season.program.abbr] + "/" +
                              self.sku + ".html")
            self.season = season


        def get_awards(self):
            if hasattr(self, 'awards'):
                return self.awards

            all_awards = []

            print(f"Getting awards from {self.event_url}")
            resp = get(self.event_url)
            root = lxml.html.fromstring(resp.content)

            table_divs = root.xpath("//div[@id='tab-awards']/div")

            self.awards = [  ]

            for div in table_divs:
                # Table with list of awards is called 'Awards'
                table_name = div.xpath("./div[@class='panel-heading']/b/text()")[0]

                if table_name == "Awards":
                    award_rows = div.xpath("./div/table//tr")
                    # Get list of awards that qualify for Worlds
                    for award_row in award_rows[1:]:
                        award_columns = list(award_row)
                        award_name = award_columns[0].text
                        award_qualifies_for = award_columns[1].text.strip()
                        if 'World Championship' in award_qualifies_for:
                            award = self.Award(name=award_name, qual_wc=True)
                        else:
                            award = self.Award(name=award_name, qual_wc=False)
                        self.awards.append(award)

            qualifying_award_names = [ award.name for award in self.awards if award.qual_wc ]

            # If 'Awards' is first table, it is assumed that the results have not
            # been published
            first_table_name = table_divs[0].xpath("./div[@class='panel-heading']/b/text()")[0]
            if first_table_name != 'Awards':
                # Get team numbers for qualifying awards from other tables
                for awarded_table in table_divs[:-1]:
                    award_rows = awarded_table.xpath("./div/table//tr")
                    for award_row in award_rows[1:]:
                        award_columns = list(award_row)
                        award_name = award_columns[0].text
                        team = award_columns[1].text.upper()

                        for award in self.awards:
                            if award_name == award.name:
                                award.team = team

            return self.awards


        def get_world_qualifying_awards(self):
            if not hasattr(self, 'awards'):
                self.get_awards()

            qualifying_awards = [ award for award in self.awards if award.qual_wc ]

            return qualifying_awards


        def get_skills_scores(self):
            resp = get(self.event_url)
            root = lxml.html.fromstring(resp.content)

            combined_scores = [  ]

            el = root.xpath("//div[@id='skills']/div/div/skills/@data")
            if el:
                scores = json.loads(el[0])

                teams = { score['team'] for score in scores }

                for team in teams:
                    total_score = 0
                    for score in scores:
                        if score['team'] == team:
                            total_score += score['highscore']
                            entry = {
                                'team': team,
                                'total_score': total_score
                            }
                            combined_scores.append(entry)

                combined_scores = sorted(combined_scores, reverse=True, key = lambda i: i['total_score'] )

            return combined_scores



        def get_qualified_teams(self):
            #TODO: If team gets 2 qualification spots at same tournament, it goes to skills from that tournament
            qualifying_awards = self.get_world_qualifying_awards()
            num_of_skills_spots = 0

            teams = [ ]
            for award in qualifying_awards:
                if award.team:
                    if award.team in teams:
                        num_of_skills_spots += 1
                    else:
                        teams.append(award.team)

            scores = self.get_skills_scores()

            if scores:
                while num_of_skills_spots > 0:
                    for entry in scores:
                        entry_team = entry['team']

                        if entry_team not in teams:
                            teams.append(entry_team)
                            num_of_skills_spots -= 1
                            break

            print(teams)
            return teams


        class Award:
            def __init__(self, name, qual_wc=False, team=''):
                self.name = name
                self.qual_wc = qual_wc
                self.team = team

            def __repr__(self):
                return json.dumps({
                    "name": self.name,
                    "qual_wc": self.qual_wc,
                    "team": self.team
                }, indent=2)

            def __str__(self):
                return self.name



        def __repr__(self):
            return json.dumps({
                'id': self.id,
                'lat': self.lat,
                'lng': self.lng,
                'date': self.date,
                'sku': self.sku,
                'address': self.address,
                'name': self.name,
                'phone': self.phone,
                'email': self.email,
                'program_slug': self.program_slug,
                'webcast_link': self.webcast_link,
                'event_entity_id': self.event_entity_id
            }, indent=2)


        def __str__():
            return f"{self.name} ({self.sku})"


    @classmethod
    def get_programs(self, **kwargs):
        resp = get(ROBOTEVENTS_PROGRAMS_API)
        json_resp = json.loads(resp.content)
        programs = json_resp['data']

        if 'name' in kwargs:
            for program in programs:
                if program['name'] == kwargs['name']:
                    return [self.Program(program)]
        else:
            program_objs = [  ]
            for program in programs:
                program_objs.append(self.Program(program))
            return programs_objs


    class GradeLevel(Enum):
        ELEMENTARY = 1
        MIDDLE_SCHOOL = 2
        HIGH_SCHOOL = 3
        COLLEGE = 4


    @classmethod
    def sku_from_url(self, url):
        event_sku = search("RE-[A-Za-z]*-[0-9]{2}-[0-9]{4}", url)[0]
        return event_sku


    @classmethod
    def scrape_event_skus(self, **kwargs):
        grade_level = kwargs.get('grade_level', '')
        from_date = kwargs.get('from_date', '')
        to_date = kwargs.get('to_date', '')
        qual_wc = kwargs.get('qual_wc', '')
        season_id = kwargs.get('season_id', '')

        page = 1
        is_last_page = False

        event_skus = [  ]
        # Iterate through every page of events
        while not is_last_page:
            params = {
                "grade_level": grade_level,
                "from_date": from_date,
                'to_date': to_date,
                "country_id": "*",
                "qual_wc": qual_wc,
                "seasonId": season_id,
                "page": page
            }

            resp = get(ROBOTEVENTS_EVENTS_SEARCH_URL, params=params)
            root = lxml.html.fromstring(resp.content)

            # Keep going until next page button is disabled (i.e. last page)
            links = root.xpath("//div[contains(@class,'results')]/div/p/strong/a/@href")
            event_skus.extend([ RobotEvents.sku_from_url(link) for link in links ])
            next_btn = root.xpath("//ul[@class='pagination']/li[last()]")[0]

            print(f"Currently on page {page}")
            is_last_page = 'disabled' in next_btn.attrib['class']

            page += 1

        return event_skus


    @classmethod
    def get_events(self, **kwargs):
        what = 'events'

        # Get values, otherwise use these defaults
        programs = kwargs.get('programs', 0)
        season = kwargs.get('season')
        season_id = kwargs.get('season_id', season.id if season else 0)
        when = kwargs.get('when', 'future')
        city = kwargs.get('city', '')
        lat = kwargs.get('lat', '')
        lng = kwargs.get('lng', '')
        country = kwargs.get('country', 'All')
        region = kwargs.get('region', 'N/A')
        grade_level = kwargs.get('grade_level', '')
        level_class_id = kwargs.get('level_class_id', '')
        from_date = kwargs.get('from_date', '')
        to_date = kwargs.get('to_date', '')
        qual_wc = kwargs.get('qual_wc', '')


        event_skus_filter = []
        kwargs_that_require_scrape = ['grade_level', 'level_class_id',
                                        'from_date', 'to_date', 'qual_wc']
        for k in kwargs_that_require_scrape:
            if k in kwargs:
                event_skus_filter = RobotEvents.scrape_event_skus(
                    grade_level=grade_level, level_class_id=level_class_id,
                    from_date=from_date, to_date=to_date, season_id=season_id,
                    qual_wc=qual_wc)
                break

        data = {
            'programs': programs,
            'when': when,
            'what': what,
            'season_id': season_id,
            'city': city,
            'lat': lat,
            'lng': lng,
            'country': country,
            'region': region
        }

        # Non-API feature to grab past and future events
        if when == 'all':
            data['when'] = 'past'
            resp_past = post(ROBOTEVENTS_EVENTS_API, data)
            json_resp = json.loads(resp_past.content)
            events = json_resp['data']

            data['when'] = 'future'
            resp_future = post(ROBOTEVENTS_EVENTS_API, data)
            json_resp = json.loads(resp_future.content)
            events.extend(json_resp['data'])
        else:
            resp = post(ROBOTEVENTS_EVENTS_API, data)
            json_resp = json.loads(resp.content)
            events = json_resp['data']

        if event_skus_filter:
            events = [ event for event in events if event['sku'] in
                        event_skus_filter ]

        event_objs = [  ]
        for event in events:
            event_obj = self.Event(event, season)
            event_objs.append(event_obj)

        return event_objs


    @classmethod
    def get_skills_data(self, grade_level, post_season=1):
        params = {
            "post_season": post_season,
            "grade_level": grade_level
        }
        resp = get(ROBOTEVENTS_SKILLS_API_URL, params=params)
        skills = json.loads(resp.content)

        return skills


def keep_attributes(attributes, obj):
    if type(obj) is dict:
        arr = [obj]
    elif type(obj) is list:
        arr = obj

    allowed = set(attributes)
    has = set(arr[0].keys())
    to_remove = has - allowed

    for i in arr:
        for a in to_remove:
            if a in i.keys():
                del i[a]
