from flask import Flask, render_template, jsonify
import requests
from datetime import datetime, timezone
import dateutil.parser
from youtubesearchpython import VideosSearch

app = Flask(__name__)

def get_nfl_scores():
    url = "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"Error fetching scores: {e}")
        return None

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
    data = get_nfl_scores()
    games = []

    if data and 'events' in data:
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

            for competition in event['competitions']:
                for competitor in competition['competitors']:
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
                game['highlight_db_query'] = query # We can fetch this client side or async to speed up load
                # game['highlight_link'] = get_highlight_video(query) # Too slow to do for all games on load

            games.append(game)

    return render_template('index.html', games=games)

@app.route('/api/highlight/<query>')
def highlight(query):
    link = get_highlight_video(query)
    return jsonify({'link': link})

if __name__ == '__main__':
    app.run(debug=True)
