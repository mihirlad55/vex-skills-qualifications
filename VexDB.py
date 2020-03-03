#!/usr/bin/env python3

from requests import get
import json


TEAMS_API_URL = "https://api.vexdb.io/v1/get_teams"

class VexDB:
    @classmethod
    def get_teams(self, program, country):
        params = {
            'program': program,
            'country': country
        }

        resp = get(TEAMS_API_URL, params=params)
        resp_json = json.loads(resp.content)
        teams = resp_json['result']

        return teams
