from flask import Flask, render_template, jsonify
import requests
from datetime import datetime, timezone
import dateutil.parser

# Removing youtube-search-python import since we will generate links directly
# from youtubesearchpython import VideosSearch 

app = Flask(__name__)

def get_nfl_scores(week=None):
    url = "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    params = {}
    if week:
        params['week'] = week

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"Error fetching scores: {e}")
        return None

def get_weeks_data(data):
    weeks = []
    current_season_label = ""
    current_season_type = 2 # Default to Reg Season
    current_week = 1
    
    if data and 'leagues' in data and data['leagues']:
        league = data['leagues'][0]
        if 'calendar' in league:
            for stage in league['calendar']:
                # Check for 'entries' (weeks)
                entries = stage.get('entries', [])
                if not entries and 'value' in stage: 
                     pass

                for entry in entries:
                     weeks.append({
                         'label': entry.get('label'),
                         'value': entry.get('value'),
                         'startDate': entry.get('startDate'),
                         'endDate': entry.get('endDate')
                     })

        # Try to determine current week/season from the response root
        if 'week' in data:
            current_week = data['week'].get('number', 1)

    return weeks, current_week

def get_highlight_video(query):
    # Fallback to a direct YouTube search URL for reliability
    # query is likely "NFL TeamA vs TeamB full highlights"
    base_url = "https://www.youtube.com/results?search_query="
    return base_url + query.replace(" ", "+")

@app.route('/')
def index():
    # Get week from request args
    from flask import request
    selected_week = request.args.get('week')
    
    data = get_nfl_scores(selected_week)
    games = []
    weeks = []
    
    if data:
        weeks, current_week_num = get_weeks_data(data)
        
        # If no week selected, default to what API says is current (or what was returned)
        if not selected_week and 'week' in data:
             selected_week = str(data['week']['number'])

        if 'events' in data:
            for event in data['events']:
                game = {
                    'id': event['id'],
                    'status': event['status']['type']['state'],
                    'shortDetail': event['status']['type']['shortDetail'],
                    'completed': event['status']['type']['completed'],
                    'competitors': []
                }

                # Get video link if game is done or live
                home_team = ""
                away_team = ""
                home_score = 0
                away_score = 0
                
                # Sort competitors to ensure consistent order (Away @ Home usually)
                competitions = event.get('competitions', [{}])[0]
                competitor_list = competitions.get('competitors', [])
                
                # Sometimes API order varies, let's just process them
                for competitor in competitor_list:
                    score_val = int(competitor.get('score', '0'))
                    team = {
                        'name': competitor['team']['displayName'],
                        'logo': competitor['team']['logo'],
                        'score': competitor.get('score', '0'),
                        'record': competitor.get('records', [{'summary': '0-0'}])[0]['summary'] if competitor.get('records') else '0-0',
                        'isWinner': competitor.get('winner', False),
                        'homeAway': competitor['homeAway']
                    }
                    game['competitors'].append(team)
                    
                    if team['homeAway'] == 'home':
                        home_team = team['name']
                        home_score = score_val
                    else:
                        away_team = team['name']
                        away_score = score_val

                # Calculate differential
                diff = abs(home_score - away_score)
                # FILTER: Only show if differential < 8
                # OR if the game hasn't started (score 0-0 logic might be tricky, but assuming they mean finished/live games?
                # The user said "results", implying finished games. 
                # But pre-game 0-0 diff is 0, which is < 8. 
                # Let's include everything < 8. 
                # Wait, if I include everything < 8, all 0-0 scheduled games will show up. That's probably fine?
                # The user asked for "results", maybe they only want finished games?
                # "i don't want all nfl scores, i want only the scores with the point differential under 8 points"
                # This explicitly talks about "scores". Scheduled games don't have scores.
                # If I hide scheduled games, I lose the utility of the app for future games.
                # But "scores with point differential" implies games where points exist.
                # However, 0-0 is a score?
                # Let's assume they want close games that are LIVE or FINAL. 
                # If a game is scheduled (status 'pre'), the score is 0-0. 
                # If I show 'pre' games, the diff is 0 < 8.
                # I'll include 'pre' games because otherwise "Week X" view would be empty for upcoming weeks.
                # But if the user strictly wants "Thrillers", maybe they only care about completed/live?
                # I'll assume: Show ALL games where diff < 8. This naturally includes 0-0 starts.
                # If the user strictly meant "Finished Close Games", I might be wrong.
                # But showing future games is usually desired.
                
                if diff < 8:
                    # Simple heuristic for highlights
                    if game['status'] in ['in', 'post']: # In progress or Final
                        query = f"NFL {away_team} vs {home_team} full highlights"
                        game['highlight_db_query'] = query

                    games.append(game)

    return render_template('index.html', games=games, weeks=weeks, selected_week=selected_week)

@app.route('/api/highlight/<query>')
def highlight(query):
    link = get_highlight_video(query)
    return jsonify({'link': link})

if __name__ == '__main__':
    app.run(debug=True)
