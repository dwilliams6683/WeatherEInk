import math
import requests
from PIL import Image, ImageDraw, ImageFont
import time
from datetime import datetime
from waveshare_epd import epd7in5b_V2

# ===== CONFIG =====
WU_API_KEY = "a6125c54c8274250925c54c827a250de"
WU_STATION_ID = "KVANORFO488"
LOCATION = "Norfolk, VA"
LATITUDE = 36.8507  # Replace with your coordinates
LONGITUDE = -76.2858
OM_OPTIONS_FORECAST = "weather_code,temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit&timezone=auto"
ICON_DIR = "/icons/"  # Contains 64x64 and 32x32 folders
FONT_DIR = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"

"""https://api.weather.com/v2/pws/observations/current?stationId={WU_STATION_ID}&format=json&units=e&apiKey={WU_API_KEY}"""

"""https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&daily=weathercode,temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit&timezone=auto"""

# Initialize URL Builder
url_builder = WeatherURLBuilder()

class WeatherURLBuilder:
    def __init__(self):
        self.wu_base = "https://api.weather.com/v2/pws/observations/current"
        self.om_base = "https://api.open-meteo.com/v1/forecast"
    
    def build_wu_url(self, station_id, api_key):
        return (
            f"{self.wu_base}?"
            f"stationId={station_id}&"
            f"format=json&"
            f"units=e&"
            f"apiKey={api_key}"
        )
    
    def build_om_url(self, lat, lon, options):
        return (
            f"{self.om_base}?"
            f"latitude={lat}&"
            f"longitude={lon}&"
            f"daily={options}"
        )

# Initialize display
epd = epd7in5_V2.EPD()
epd.init()

def fetch_current_weather():
    """Fetch current conditions from Weather Underground"""
    try:
        url = url_builder.build_wu_url(WU_STATION_ID, WU_API_KEY)
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            obs = response.json()['observations'][0]
            imperial = obs['imperial']
            return {
                'temp': imperial.get('temp', 'N/A'),
                'heatindex': imperial.get('heatIndex', 'N/A'),
                'windchill': imperial.get('windChill', 'N/A'),
                'humidity': obs.get('humidity', 'N/A'),
                'pressure': imperial.get('pressure', 'N/A'),
                'wind_speed': imperial.get('windSpeed', 'N/A'),
                'wind_gust': imperial.get('windGust', 'N/A'),
                'wind_dir': obs.get('winddir', 0),
                'rain_rate': imperial.get('precipRate', 'N/A'),
                'rain_total': imperial.get('precipTotal', 'N/A')
            }
            
    except Exception as e:
        print(f"WU Current Error: {e}")
    return None
	
def fetch_7day_forecast():
    """Fetch 7-day forecast from Open-Meteo"""
    try:
        url = url_builder.build_om_url(LATITUDE, LONGITUDE, OM_OPTIONS_FORECAST)
        response = requests.get(url)
        if response.status_code == 200:
            daily = response.json()['daily']
            return {
                'days': [datetime.strptime(str(d), "%Y-%m-%d").strftime("%a") for d in daily['time']],
                'dates': [d[5:10] for d in daily['time']],
                'highs': daily['temperature_2m_max'],
                'lows': daily['temperature_2m_min'],
                'conditions': [map_om_condition(c) for c in daily['weather_code']]
            }
    except Exception as e:
        print(f"Open-Meteo Error: {e}")
    return None

def fetch_current_conditions():
    try:
        url = https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current=weather_code
        response = requests.get(url)
        if response.status_code == 200:
            current = response.json()['current']
            return {
                'conditions': current.get('weather_code', 'N/A')
            }
    except Exception as e:
        print(f"Open-Meteo Error: {e}")
    return None

def map_om_condition(code):
    """Map Open-Meteo WMO codes to icon names"""
    if code == 0: return 'day-sunny'
    elif 1 <= code <= 3: return 'cloudy'
    elif 51 <= code <= 55: return 'rain'
    elif 61 <= code <= 65: return 'rain'
    elif 71 <= code <= 75: return 'snow'
    elif 95 <= code <= 99: return 'thunderstorm'
    else: return 'na'

