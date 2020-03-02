#!/usr/bin/env python3

from requests import get
import json
import lxml.html
import lxml.etree

from re import search

import pdb

AWARDS_API_URL = "https://api.vexdb.io/v1/get_awards"
TEAMS_API_URL = "https://api.vexdb.io/v1/get_teams"

SKILLS_API_URL = "https://www.robotevents.com/api/seasons/131/skills?post_season=1&grade_level=College"
EVENTS_URL = "https://www.robotevents.com/robot-competitions/college-competition"
EVENT_DETAILS_URL = "https://www.robotevents.com/robot-competitions/college-competition/"


def main():
    params = {
        "post_season": 1,
        "grade_level": "College"
    }
    resp = get(SKILLS_API_URL, params=params)
    skills = json.loads(resp.content)

    competition_awards = get_world_qualifier_awards()

    qualified_teams = [  ]

    # Build list of teams that qualified
    for competition in competition_awards:
        for award in competition['awards']:
            if award['team']:
                qualified_teams.append(award['team'])

    # Remove duplicates
    unique_qualified_teams = set(qualified_teams)

    # Get full list of teams from VexDB
    us_teams = get_us_teams()
    # Get just the team numbers in uppercase
    us_team_numbers = set([ team['number'].upper() for team in us_teams ])

    # Get list of qualified US teams by cross-referencing with US teams from VexDB
    qualified_us_teams = [ team for team in qualified_teams if team in us_team_numbers ]
    unique_qualified_us_teams = set(qualified_us_teams)

    skills_spots = len(qualified_us_teams) - len(unique_qualified_us_teams)

    print("The following teams have qualified through events: ")
    print(unique_qualified_us_teams)
    print(f"As a result, there are {skills_spots} qualification spots available for skills")

    # Build list of US teams that have not qualified
    skills_us_teams_quals = [ ]
    for entry in skills:
        country = entry['team']['country']
        team_number = entry['team']['team'].upper()
        if (country == 'United States'
            and team_number not in unique_qualified_us_teams
            and len(skills_us_teams_quals) != skills_spots):

            skills_us_teams_quals.append(team_number)

    print("As of right now, the following teams from the US may qualify through skills")
    print(skills_us_teams_quals)


#TODO: If team gets 2 qualification spots at same tournament, it goes to skills from that tournament


def get_us_teams():
    params = {
        'program': 'VEXU',
        'country': 'United States'
    }

    resp = get(TEAMS_API_URL, params=params)
    resp_json = json.loads(resp.content)
    teams = resp_json['result']

    return teams



def get_world_qualifier_awards():
    page = 1
    is_last_page = False
    links = []

    # Iterate through every page of events
    while not is_last_page:
        params = {
            "grade_level": 4,
            "from_date": "05/08/2019",
            "country_id": "*",
            "qual_wc": 1,
            "page": page
        }
        resp = get(EVENTS_URL, params=params)
        root = lxml.html.fromstring(resp.content)

        # Keep going until next page button is disabled (i.e. last page)
        links.extend(
            root.xpath("//div[contains(@class,'results')]/div/p/strong/a/@href"))
        next_btn = root.xpath("//ul[@class='pagination']/li[4]")[0]

        print(f"Currently on page {page}")
        is_last_page = 'disabled' in next_btn.attrib['class']

        page += 1


    all_awards = []

    for link in links:
        print(f"Getting awards from {link}")
        resp = get(link)
        event_sku = search("RE-VEXU-[0-9]{2}-[0-9]{4}", link)[0]
        root = lxml.html.fromstring(resp.content)

        table_divs = root.xpath("//div[@id='tab-awards']/div")
        event_name = root.xpath(".//title/text()")[0].strip()

        competition = {
            'sku': event_sku,
            'name': event_name,
            'awards': [ ]
        }

        qualifying_awards = []
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
                        qualifying_awards.append(award_name)

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

                    if award_name in qualifying_awards:
                        award_dict = {
                            'award_name': award_name,
                            'team': team
                        }
                        competition['awards'].append(award_dict)
        else:
            # If awards have not been published, no team has received any awards
            for qualifying_award in qualifying_awards:
                award_dict = {
                    'award_name': qualifying_award,
                    'team': ''
                }
                competition['awards'].append(award_dict)

        print(competition)
        all_awards.append(competition)


    return all_awards



def dump(obj):
   for attr in dir(obj):
       if hasattr( obj, attr ):
           print( "obj.%s = %s" % (attr, getattr(obj, attr)))

if __name__ == "__main__":
    main()
