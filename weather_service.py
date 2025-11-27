import requests
import math
from datetime import datetime
from astropy.coordinates import get_body
from astropy.time import Time

class WeatherService:
    # 三山岛坐标
    LAT = 31.03
    LON = 120.29
    
    def get_current_weather(self):
        """
        获取当前天气和观星条件
        优先使用国内API (中华万年历/Etouch)，结合本地天文计算
        """
        try:
            # 1. 获取天气数据 (使用中华万年历API，无需Key，国内速度快)
            # 苏州代码: 101190401
            weather_info = self._fetch_chinese_weather()
            
            if not weather_info:
                # 如果国内API失败，返回None
                return None
            
            # 2. 计算天文数据 (月相、日出日落)
            astronomy = self._calculate_astronomy()
            weather_info.update(astronomy)
            
            # 3. 计算观星指数
            self._calculate_score(weather_info)
            
            return weather_info
            
        except Exception as e:
            print(f"Error in weather service: {e}")
            return None

    def _fetch_chinese_weather(self):
        """从中华万年历API获取天气"""
        try:
            # 尝试使用 sojson API (基于中国气象局数据)
            url = "http://t.weather.sojson.com/api/weather/city/101190401"
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 200:
                    weather_data = data.get('data')
                    current_temp = float(weather_data.get('wendu'))
                    humidity_str = weather_data.get('shidu', '0').replace('%', '')
                    humidity = float(humidity_str)
                    
                    forecast_today = weather_data.get('forecast')[0]
                    weather_type = forecast_today.get('type')
                    
                    # 估算云量
                    cloud_cover = 50 # 默认
                    if '晴' in weather_type: cloud_cover = 0
                    elif '少云' in weather_type: cloud_cover = 25
                    elif '多云' in weather_type: cloud_cover = 60
                    elif '阴' in weather_type: cloud_cover = 90
                    elif '雨' in weather_type or '雪' in weather_type: cloud_cover = 100
                    
                    # 提取风力
                    wind_str = forecast_today.get('fl', '')
                    wind_speed = 0
                    if '3级' in wind_str: wind_speed = 10
                    elif '4级' in wind_str: wind_speed = 20
                    elif '5级' in wind_str: wind_speed = 30
                    
                    return {
                        'temperature': current_temp,
                        'humidity': humidity,
                        'cloud_cover': cloud_cover,
                        'wind_speed': wind_speed,
                        'weather_code': 0,
                        'source': 'CN (SoJson)'
                    }
            return None
        except Exception as e:
            print(f"Chinese API failed: {e}")
            return None

    def _fetch_open_meteo(self):
        """Open-Meteo备用方案 (已移除，仅使用国内源)"""
        return None

    def _calculate_astronomy(self):
        """本地计算天文数据"""
        try:
            t = Time.now()
            sun = get_body('sun', t)
            moon = get_body('moon', t)
            
            # 计算月相 (被照亮比例 0.0-1.0)
            elongation = sun.separation(moon)
            illumination = (1 - math.cos(elongation.radian)) / 2
            
            return {
                'moon_phase': illumination, # 0=New, 1=Full
                'moon_phase_text': self._get_moon_phase_text(illumination)
            }
        except Exception as e:
            print(f"Astronomy calc failed: {e}")
            return {'moon_phase': 0, 'moon_phase_text': '未知'}

    def _calculate_score(self, weather_info):
        """计算观星指数"""
        cloud_cover = weather_info['cloud_cover']
        cloud_score = max(0, 100 - cloud_cover)
        
        # 月相影响 (满月1.0时光害大，得分低)
        moon_phase = weather_info['moon_phase']
        moon_score = (1 - moon_phase) * 100
        
        # 综合评分: 云量占70%, 月相占30%
        stargazing_score = (cloud_score * 0.7) + (moon_score * 0.3)
        
        weather_info['stargazing_score'] = round(stargazing_score)
        weather_info['condition_text'] = self._get_condition_text(stargazing_score)

    def _get_condition_text(self, score):
        if score >= 80: return "极佳"
        if score >= 60: return "良好"
        if score >= 40: return "一般"
        if score >= 20: return "较差"
        return "不宜"

    def _get_moon_phase_text(self, illumination):
        # 简单根据照亮比例判断
        if illumination < 0.1: return "新月/残月"
        if illumination < 0.4: return "蛾眉月"
        if illumination < 0.6: return "弦月"
        if illumination < 0.9: return "凸月"
        return "满月"
