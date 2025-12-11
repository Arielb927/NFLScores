"""
Test script to verify ESPN API and YouTube search functionality
"""
import requests
from datetime import datetime

def test_espn_api():
    """Test ESPN NFL scoreboard API"""
    print("Testing ESPN API...")
    url = "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ ESPN API working!")
        print(f"  Found {len(data.get('events', []))} games")
        
        # Show sample game data
        if data.get('events'):
            game = data['events'][0]
            competitions = game.get('competitions', [{}])[0]
            competitors = competitions.get('competitors', [])
            
            if len(competitors) >= 2:
                home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
                away = competitors[1] if competitors[1].get('homeAway') == 'away' else competitors[0]
                
                print(f"\n  Sample game:")
                print(f"    {away['team']['displayName']} @ {home['team']['displayName']}")
                print(f"    Score: {away.get('score', 'N/A')} - {home.get('score', 'N/A')}")
                print(f"    Status: {game.get('status', {}).get('type', {}).get('description', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"✗ ESPN API failed: {e}")
        return False

def test_youtube_search():
    """Test YouTube search using youtubesearchpython"""
    print("\nTesting YouTube search...")
    
    try:
        from youtubesearchpython import VideosSearch
        
        # Search for a recent NFL highlight
        search = VideosSearch('NFL highlights week 14', limit=1)
        results = search.result()
        
        if results.get('result'):
            video = results['result'][0]
            print(f"✓ YouTube search working!")
            print(f"  Found: {video.get('title', 'N/A')}")
            print(f"  Video ID: {video.get('id', 'N/A')}")
            print(f"  Link: {video.get('link', 'N/A')}")
            return True
        else:
            print("✗ No results found")
            return False
            
    except ImportError:
        print("✗ youtubesearchpython not installed")
        print("  Run: pip install youtube-search-python")
        return False
    except Exception as e:
        print(f"✗ YouTube search failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("API Testing for NFL Scores App")
    print("=" * 50)
    
    espn_ok = test_espn_api()
    youtube_ok = test_youtube_search()
    
    print("\n" + "=" * 50)
    if espn_ok and youtube_ok:
        print("✓ All tests passed! Ready to build the app.")
    else:
        print("✗ Some tests failed. Check errors above.")
    print("=" * 50)
