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
                
                # Check for Overtime
                # API usually has period > 4 for OT
                period = event.get('status', {}).get('period', 0)
                is_overtime = period > 4

                # FILTER LOGIC:
                # 1. Show all active/scheduled games (status != 'post')
                # 2. For completed games, show if:
                #    a. Point differential < 6
                #    b. OR Game went to Overtime
                
                status_state = game['status'] # 'pre', 'in', 'post'
                
                should_show = False
                if status_state != 'post':
                    should_show = True
                elif diff < 6 or is_overtime:
                    should_show = True

                if diff < 8:
                    # Simple heuristic for highlights
                    if game['status'] in ['in', 'post']: # In progress or Final
                        query = f"NFL {away_team} vs {home_team} full highlights"
                        # Link to our specific redirector
                        game['highlight_link'] = f"/watch_highlight?query={query}"

                    games.append(game)

    return render_template('index.html', games=games, weeks=weeks, selected_week=selected_week)

@app.route('/watch_highlight')
def watch_highlight():
    from flask import request, redirect
    from youtubesearchpython import VideosSearch
    
    query = request.args.get('query')
    if not query:
        return redirect("/") # Fallback to home if no query
        
    try:
        # Search for the video
        # We want "Official" highlights, typically from "NFL" channel or strictly matching the game
        search = VideosSearch(query, limit=5)
        results = search.result()
        
        best_link = None
        
        if results['result']:
        if results['result']:
            # 1. Look for video from "NFL" channel
            for video in results['result']:
                channel = video.get('channel', {}).get('name', '')
                if channel == 'NFL' or channel == 'NFL Highlights': 
                     best_link = video.get('link')
                     break
            
            # 2. If no strict Official NFL video found, take the VERY FIRST result (Best Match)
            # This ensures we go straight to a video player, as requested.
            if not best_link:
                best_link = results['result'][0].get('link')
                
        if best_link:
            return redirect(best_link)
            
    except Exception as e:
        print(f"Error finding specific video: {e}")
        
    # Fallback to search page
    base_url = "https://www.youtube.com/results?search_query="
    return redirect(base_url + query.replace(" ", "+"))

if __name__ == '__main__':
    app.run(debug=True)
