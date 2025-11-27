import requests
from datetime import datetime

class WeatherService:
    # 三山岛坐标
    LAT = 31.03
    LON = 120.29
    
    def get_current_weather(self):
        """
        获取当前天气和观星条件
        使用 Open-Meteo API (无需API Key)
        """
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": self.LAT,
                "longitude": self.LON,
                "current": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m,weather_code",
                "daily": "sunrise,sunset,moon_phase",
                "timezone": "Asia/Shanghai"
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code != 200:
                return None
                
            data = response.json()
            current = data.get('current', {})
            daily = data.get('daily', {})
            
            # 解析数据
            weather_info = {
                'temperature': current.get('temperature_2m'),
                'humidity': current.get('relative_humidity_2m'),
                'cloud_cover': current.get('cloud_cover'), # 云量 0-100
                'wind_speed': current.get('wind_speed_10m'),
                'weather_code': current.get('weather_code'),
                'sunrise': daily.get('sunrise', [])[0] if daily.get('sunrise') else None,
                'sunset': daily.get('sunset', [])[0] if daily.get('sunset') else None,
                'moon_phase': daily.get('moon_phase', [])[0] if daily.get('moon_phase') else 0, # 0.00 New Moon, 0.50 Full Moon
            }
            
            # 计算观星指数 (0-100)
            # 云量是主要因素，月相是次要因素
            cloud_score = max(0, 100 - weather_info['cloud_cover'])
            
            # 月相影响 (满月时光害大，得分低)
            # moon_phase: 0=新月(好), 0.5=满月(差), 1=新月(好)
            moon_phase = weather_info['moon_phase']
            moon_factor = abs(moon_phase - 0.5) * 2 # 0(满月) -> 1(新月)
            moon_score = moon_factor * 100
            
            # 综合评分: 云量占70%, 月相占30%
            stargazing_score = (cloud_score * 0.7) + (moon_score * 0.3)
            
            weather_info['stargazing_score'] = round(stargazing_score)
            weather_info['condition_text'] = self._get_condition_text(stargazing_score)
            weather_info['moon_phase_text'] = self._get_moon_phase_text(moon_phase)
            
            return weather_info
            
        except Exception as e:
            print(f"Error fetching weather: {e}")
            return None

    def _get_condition_text(self, score):
        if score >= 80: return "极佳"
        if score >= 60: return "良好"
        if score >= 40: return "一般"
        if score >= 20: return "较差"
        return "不宜"

    def _get_moon_phase_text(self, phase):
        if phase < 0.03 or phase > 0.97: return "新月"
        if phase < 0.25: return "蛾眉月"
        if phase < 0.27: return "上弦月"
        if phase < 0.48: return "盈凸月"
        if phase < 0.52: return "满月"
        if phase < 0.73: return "亏凸月"
        if phase < 0.77: return "下弦月"
        return "残月"
