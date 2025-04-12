import pytz
import os
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
ICON_DIR = os.path.expanduser("~/icons/")  # Contains 64x64 and 32x32 folders
FONT_DIR = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
UPDATE_INTERVAL = 900  # 15 minutes in seconds

"""https://api.weather.com/v2/pws/observations/current?stationId={WU_STATION_ID}&format=json&units=e&apiKey={WU_API_KEY}"""

"""https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&daily=weathercode,temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit&timezone=auto"""

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

# Initialize URL Builder
url_builder = WeatherURLBuilder()

# Initialize display
epd = epd7in5b_V2.EPD()

def fetch_current_weather():
    """Fetch current conditions from Weather Underground"""
    try:
        url = url_builder.build_wu_url(WU_STATION_ID, WU_API_KEY)
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'},timeout=10)
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
        response = requests.get(url, timeout=10)
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
    """Fetch ONLY the Open-Meteo weather code for icon mapping"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current=weather_code"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()['current']['weather_code']  # Return raw code (e.g., 3)
    except Exception as e:
        print(f"Open-Meteo Error: {e}")
    return 0  # Default: clear sky (code 0)

def map_om_condition(code):
    """Map Open-Meteo WMO codes to icon names"""
    if code == 0: return 'day-sunny'
    elif 1 <= code <= 3: return 'cloudy'
    elif 51 <= code <= 55: return 'rain'
    elif 61 <= code <= 65: return 'rain'
    elif 71 <= code <= 75: return 'snow'
    elif 95 <= code <= 99: return 'thunderstorm'
    else: return 'na'

def draw_wind_arrow(draw, x, y, degrees):
    """Draw compass with wind direction arrow"""
    radius = 30
    draw.ellipse([(x-radius, y-radius), (x+radius, y+radius)], outline=0)
    radians = math.radians(degrees)
    end_x = x + radius * 0.7 * math.sin(radians)
    end_y = y - radius * 0.7 * math.cos(radians)
    draw.line([(x, y), (end_x, end_y)], fill=0, width=3)
    
def feels_like(weather_data: dict) -> float:
    try:
        temp = weather_data['temp']
        if temp == 'N/A':  # Handle string fallback
            return 'N/A'
        return weather_data['heatindex'] if temp >= 50 else weather_data['windchill']
    except (KeyError, TypeError) as e:
        print(f"feels_like error: {e}")
        return 'N/A'

def render_display(current, forecast, condition):
    # Create two separate images - one for black, one for red
    image_black = Image.new('1', (epd.width, epd.height), 255)  # White background
    image_red = Image.new('1', (epd.width, epd.height), 255)    # White background
    draw_black = ImageDraw.Draw(image_black)
    draw_red = ImageDraw.Draw(image_red)

    # === Upper Half: Current Conditions ===
    # Header (black)
    draw_black.text((epd.width//2, 10), LOCATION, font=font_medium, anchor='mt', fill=0)
    draw_black.text((epd.width-10, 10), time.strftime("%b %d %I:%M %p"), font=font_small, anchor='rt', fill=0)

    # Current Conditions (Left)
    try:
        icon_name = map_om_condition(condition)  # Convert code to icon name
        icon_path = f"{ICON_DIR}64x64/wi-{icon_name}.png"
        icon = Image.open(icon_path).convert('1')
        target_size = epd.width // 6  
        icon = icon.resize((target_size, target_size))
        image_black.paste(icon, (30, 50))
        print(f"Using icon: {icon_name} (OM Code: {condition})")  # Debug log
    except Exception as e:
        print(f"Icon error: {e}")


    # Temperature (red)
    draw_red.text((120, 60), f"{current['temp']}°F", font=font_large, fill=0)
    current['feels_like'] = feels_like(current)
    draw_black.text((120, 120), f"Feels {current['feels_like']}°F", font=font_small, fill=0)

    # Wind (black)
    draw_wind_arrow(draw_black, epd.width-70, 90, current['wind_dir'])
    draw_black.text((epd.width-70, 140), f"{current['wind_speed']} mph", font=font_small, anchor='mt', fill=0)
    draw_black.text((epd.width-70, 160), f"Gust: {current['wind_gust']} mph", font=font_small, anchor='mt', fill=0)

    # Metrics (black)
    metrics = [
        (f"Humidity: {current['humidity']}%", 30, 180),
        (f"Pressure: {current['pressure']} hPa", 150, 180),
        (f"Rain Rate:️ {current['rain_rate']}\"/hr", 270, 180),
        (f"Rain Total: {current['rain_total']}\"", 390, 180)
    ]
    for text, x, y in metrics:
        draw_black.text((x, y), text, font=font_small, fill=0)

    # === Lower Half: 7-Day Forecast ===
    # Graph parameters
    graph_top = 220
    graph_height = 150
    day_width = epd.width / 7

    # Calculate Y-axis range
    min_temp = min(forecast['lows']) - 10
    max_temp = max(forecast['highs']) + 10
    temp_range = max_temp - min_temp

    # Draw grid lines (black)
    for temp in range(int(min_temp), int(max_temp)+1, 10):
        y = graph_top + graph_height - ((temp-min_temp)/temp_range)*graph_height
        draw_black.line([(0, y), (epd.width, y)], fill=0, width=1)

    # Plot temperatures
    prev_high = prev_low = None
    for i in range(7):
        x = i * day_width + day_width/2

        # High temp (red)
        high_y = graph_top + graph_height - ((forecast['highs'][i]-min_temp)/temp_range)*graph_height
        if prev_high:
            draw_red.line([prev_high, (x, high_y)], fill=0, width=2)
        prev_high = (x, high_y)

        # Low temp (black)
        low_y = graph_top + graph_height - ((forecast['lows'][i]-min_temp)/temp_range)*graph_height
        if prev_low:
            draw_black.line([prev_low, (x, low_y)], fill=0, width=2)
        prev_low = (x, low_y)

    # Footer with forecast (black)
    for i in range(7):
        x = i * day_width + day_width/2
        try:
            icon = Image.open(f"{ICON_DIR}/32x32/wi-{forecast['conditions'][i]}.png")
            icon_path = f"{ICON_DIR}32x32/wi-{forecast['conditions'][i]}.png"
            icon = Image.open(icon_path).convert('1')
            target_size = epd.width // 10
            icon = icon.resize((target_size, target_size))
            image_black.paste(icon, (int(x-16), epd.height-70))
        except:
            pass
        draw_black.text((x, epd.height-40), forecast['days'][i], font=font_small, anchor='mt', fill=0)
        draw_black.text((x, epd.height-20), forecast['dates'][i], font=font_small, anchor='mt', fill=0)

    # Display both layers
    epd.display(epd.getbuffer(image_black), epd.getbuffer(image_red))
    epd.sleep()    

def main():
    epd.init()
    # Initialize fonts here (same as before)
    global font_large, font_medium, font_small
    font_large = ImageFont.truetype(FONT_DIR, 48)
    font_medium = ImageFont.truetype(FONT_DIR, 24)
    font_small = ImageFont.truetype(FONT_DIR, 18)

    epd.Clear()  # Full clear on startup

    while True:
        current = fetch_current_weather()
        om_code = fetch_current_conditions()
        forecast = fetch_7day_forecast()

        if current and forecast and om_code:
        render_display(
            current, 
            forecast, 
            om_code  # Pass weather code
        )

        time.sleep(UPDATE_INTERVAL)  

if __name__ == "__main__":
    main()