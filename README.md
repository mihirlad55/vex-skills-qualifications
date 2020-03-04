# vex-skills-qualifications
Scrapes RobotEvents and VEXDB to find list of teams that will qualify through skills

Note that this has only been tested for VEX U.

# Instructions to Run
1. Clone the repository
2. Install Python3 and pip3 if not already installed.
3. Run `pip3 install -r requirements.txt` from the same directory as the script
4. Run the script with `python3 main.py` from the same directory of the script

# To Try a Different Country
The script currently only displays qualifications for US teams. For other countries, modify the line:
`get_skills_qualifications('United States', 'VEX U', 'VEXU', 'College')` and change United States to your country.
