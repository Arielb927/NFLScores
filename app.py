from flask import Flask, render_template, jsonify
import requests
from datetime import datetime, timezone
import dateutil.parser
from youtubesearchpython import VideosSearch

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
                stage_label = stage.get('label', '')
                # API structure: events directly in stage (some stages), or in 'entries'
                # For regular season, it usually has 'entries' which are weeks
                # For postseason, it might be different. 
                # Let's handle the common 'entries' (weeks) structure.
                
                # Check for 'entries' (weeks)
                entries = stage.get('entries', [])
                if not entries and 'value' in stage: 
                     # Sometimes a stage itself is a clickable item if it has no sub-entries? 
                     # But mostly we want weeks.
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
        if 'season' in data:
            current_season_type = data['season'].get('type', 2)

    return weeks, current_week

def get_highlight_video(query):
    try:
        search = VideosSearch(query, limit=1)
        results = search.result()
        if results['result']:
            return results['result'][0]['link']
    except Exception as e:
        print(f"Error fetching highlight: {e}")
    return None

@app.route('/')
def index():
    # Get week from request args
    from flask import request
    selected_week = request.args.get('week')
    
    data = get_nfl_scores(selected_week)
    games = []
    weeks = []
    current_week_num = 1
    
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
                
                # Sort competitors to ensure consistent order (Away @ Home usually)
                competitions = event.get('competitions', [{}])[0]
                competitor_list = competitions.get('competitors', [])
                
                # Sometimes API order varies, let's just process them
                for competitor in competitor_list:
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
                    else:
                        away_team = team['name']

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
