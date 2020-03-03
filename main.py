#!/usr/bin/env python3

from requests import get
import json
import lxml.html
import lxml.etree

from re import search

import pdb

from RobotEvents import RobotEvents
from VexDb import VexDb


AWARDS_API_URL = "https://api.vexdb.io/v1/get_awards"

EVENTS_URL = "https://www.robotevents.com/robot-competitions/college-competition"
EVENT_DETAILS_URL = "https://www.robotevents.com/robot-competitions/college-competition/"


def main():
    get_skills_qualifications('Canada', 'VEX U', 'VEXU', 'College')



def get_skills_qualifications(country, program, vexdb_program, grade_level):
    re = RobotEvents()
    vexu = re.get_programs(name=program)[0]
    current_season = vexu.get_current_season()
    events = current_season.get_events(country=country, when='all', qual_wc=1, from_date='2019/05/01')

    skills = RobotEvents.get_skills_data(grade_level)

    qualified_teams = [  ]

    # Build list of teams that qualified
    for event in events:
        qualified_teams.extend(event.get_qualified_teams())

    # Remove duplicates
    unique_qualified_teams = set(qualified_teams)

    # Get full list of teams from VexDB
    teams = VexDb.get_teams(vexdb_program, country)
    # Get just the team numbers in uppercase
    team_numbers = set([ team['number'].upper() for team in teams ])

    # Get list of qualified teams by cross-referencing with teams from given country from VexDB
    qualified_teams = [ team for team in qualified_teams if team in team_numbers ]
    unique_qualified_teams = set(qualified_teams)

    skills_spots = len(qualified_teams) - len(unique_qualified_teams)

    # Build list of US teams that have not qualified
    skills_teams_quals = [ ]
    for entry in skills:
        entry_country = entry['team']['country']
        team_number = entry['team']['team'].upper()
        if (entry_country == country
            and team_number not in unique_qualified_teams
            and len(skills_teams_quals) != skills_spots):

            skills_teams_quals.append(team_number)


    print(f"The following {len(unique_qualified_teams)} teams have qualified through events: ")
    print(unique_qualified_teams)
    print(f"As a result, there are {skills_spots} qualification spots available for skills")
    print(f"As of right now, the following teams from {country} may qualify through skills")
    print(skills_teams_quals)




def dump(obj):
   for attr in dir(obj):
       if hasattr( obj, attr ):
           print( "obj.%s = %s" % (attr, getattr(obj, attr)))

def json_dump(j):
    print(json.dumps(j, indent=2))

if __name__ == "__main__":
    main()
