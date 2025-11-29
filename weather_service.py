import requests
import math
from datetime import datetime
from astropy.coordinates import get_body, EarthLocation, AltAz
from astropy.time import Time
import astropy.units as u

class WeatherService:
    # 三山岛坐标
    LAT = 31.03
    LON = 120.29
    
    def __init__(self):
        self._weather_cache = None
        self._weather_cache_time = None
        self._forecast_cache = None
        self._forecast_cache_time = None
        self._cache_duration = 1800  # 缓存30分钟

    def get_current_weather(self):
        """
        获取当前天气和观星条件
        优先使用 Open-Meteo API (更稳定)
        """
        # 检查缓存
        if self._weather_cache and self._weather_cache_time:
            if (datetime.now() - self._weather_cache_time).total_seconds() < self._cache_duration:
                return self._weather_cache

        try:
            # 1. 获取天气数据
            weather_info = self._fetch_open_meteo()
            
            if not weather_info:
                # 如果 Open-Meteo 失败，尝试国内 API
                weather_info = self._fetch_chinese_weather()
            
            if not weather_info:
                return None
            
            # 2. 计算天文数据 (月相、日出日落)
            astronomy = self._calculate_astronomy()
            weather_info.update(astronomy)
            
            # 3. 计算观星指数
            self._calculate_score(weather_info)
            
            # 更新缓存
            self._weather_cache = weather_info
            self._weather_cache_time = datetime.now()
            
            return weather_info
            
        except Exception as e:
            print(f"Error in weather service: {e}")
            return None

    def get_hourly_forecast(self):
        """
        获取未来12小时的天气预报 (使用 Open-Meteo)
        """
        # 检查缓存
        if self._forecast_cache and self._forecast_cache_time:
            if (datetime.now() - self._forecast_cache_time).total_seconds() < self._cache_duration:
                return self._forecast_cache

        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": self.LAT,
                "longitude": self.LON,
                "hourly": "temperature_2m,relativehumidity_2m,cloudcover",
                "timezone": "Asia/Shanghai",
                "forecast_days": 2
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                hourly = data.get('hourly', {})
                
                times = hourly.get('time', [])
                temps = hourly.get('temperature_2m', [])
                humidities = hourly.get('relativehumidity_2m', [])
                clouds = hourly.get('cloudcover', [])
                
                # 获取当前时间并找到最近的索引
                now = datetime.now()
                current_hour_str = now.strftime('%Y-%m-%dT%H:00')
                
                start_idx = 0
                for i, t in enumerate(times):
                    if t >= current_hour_str:
                        start_idx = i
                        break
                
                # 提取未来12小时的数据
                forecast = []
                for i in range(start_idx, min(start_idx + 12, len(times))):
                    # 格式化时间为 HH:00
                    dt = datetime.fromisoformat(times[i])
                    time_str = dt.strftime('%H:00')
                    
                    forecast.append({
                        'time': time_str,
                        'temperature': temps[i],
                        'humidity': humidities[i],
                        'cloud_cover': clouds[i]
                    })
                
                # 更新缓存
                self._forecast_cache = forecast
                self._forecast_cache_time = datetime.now()

                return forecast
            return []
        except Exception as e:
            print(f"Forecast API failed: {e}")
            # 返回模拟数据作为后备
            return self._generate_mock_forecast()

    def _generate_mock_forecast(self):
        """生成模拟预报数据 (当API失败时)"""
        forecast = []
        now = datetime.now()
        current_hour = now.hour
        
        for i in range(12):
            h = (current_hour + i) % 24
            # 简单的模拟逻辑
            temp = 15 - 3 * math.sin((h - 14) * math.pi / 12) # 模拟气温日变化
            cloud = 20 + 10 * math.sin(h) # 随机云量
            humidity = 60 + 20 * math.cos((h - 14) * math.pi / 12) # 相对湿度与气温反相关
            
            forecast.append({
                'time': f"{h:02d}:00",
                'temperature': round(temp, 1),
                'humidity': round(humidity, 0),
                'cloud_cover': round(abs(cloud) % 100, 0)
            })
        return forecast

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
        """从 Open-Meteo 获取天气数据"""
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": self.LAT,
                "longitude": self.LON,
                "current_weather": "true",
                "hourly": "temperature_2m,relativehumidity_2m,cloudcover,windspeed_10m",
                "timezone": "Asia/Shanghai"
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                current = data.get('current_weather', {})
                hourly = data.get('hourly', {})
                
                # 获取当前时间的小时索引
                now = datetime.now()
                current_hour_str = now.strftime('%Y-%m-%dT%H:00')
                
                idx = 0
                times = hourly.get('time', [])
                for i, t in enumerate(times):
                    if t >= current_hour_str:
                        idx = i
                        break
                
                # 从 hourly 数据中获取更详细的信息
                cloud_cover = hourly.get('cloudcover', [])[idx] if idx < len(hourly.get('cloudcover', [])) else 0
                humidity = hourly.get('relativehumidity_2m', [])[idx] if idx < len(hourly.get('relativehumidity_2m', [])) else 0
                
                return {
                    'temperature': current.get('temperature'),
                    'humidity': humidity,
                    'cloud_cover': cloud_cover,
                    'wind_speed': current.get('windspeed'),
                    'weather_code': current.get('weathercode'),
                    'source': 'Open-Meteo'
                }
            return None
        except Exception as e:
            print(f"Open-Meteo API failed: {e}")
            return None

    def _calculate_astronomy(self):
        """本地计算天文数据"""
        try:
            t = Time.now()
            location = EarthLocation(lat=self.LAT*u.deg, lon=self.LON*u.deg)
            
            sun = get_body('sun', t)
            moon = get_body('moon', t)
            
            # 计算月相 (被照亮比例 0.0-1.0)
            elongation = sun.separation(moon)
            illumination = (1 - math.cos(elongation.radian)) / 2
            
            # 计算月亮高度角
            altaz = AltAz(obstime=t, location=location)
            moon_altaz = moon.transform_to(altaz)
            moon_altitude = moon_altaz.alt.degree
            
            return {
                'moon_phase': illumination, # 0=New, 1=Full
                'moon_phase_text': self._get_moon_phase_text(illumination),
                'moon_altitude': moon_altitude
            }
        except Exception as e:
            print(f"Astronomy calc failed: {e}")
            return {'moon_phase': 0, 'moon_phase_text': '未知', 'moon_altitude': -90}

    def _calculate_score(self, weather_info):
        """计算观星指数"""
        cloud_cover = weather_info['cloud_cover']
        cloud_score = max(0, 100 - cloud_cover)
        
        # 使用月相干扰算法计算月亮影响
        moon_phase = weather_info['moon_phase']
        moon_alt = weather_info.get('moon_altitude', -90)
        
        moon_interference = self._calculate_moon_interference(moon_phase, moon_alt)
        moon_score = 100 - moon_interference
        
        # 综合评分: 云量占70%, 月亮影响占30%
        stargazing_score = (cloud_score * 0.7) + (moon_score * 0.3)
        
        weather_info['stargazing_score'] = round(stargazing_score)
        weather_info['condition_text'] = self._get_condition_text(stargazing_score)
        weather_info['moon_score'] = round(moon_score) # 记录月亮得分供参考
        weather_info['moon_interference'] = round(moon_interference, 1) # 记录干扰指数

    def _calculate_moon_interference(self, moon_phase, moon_altitude):
        """
        使用月相干扰算法量化计算月亮影响 (0-100)
        基于 Krisciunas & Schaefer (1991) 的月光亮度模型简化
        """
        # 1. 如果月亮在地平线以下一定角度 (天文曙暮光 -18度)，干扰为0
        if moon_altitude < -18:
            return 0
            
        # 2. 计算月亮视星等 (Visual Magnitude)
        # moon_phase 是照亮比例 0~1。相位角 alpha 0(满)~180(新)
        # alpha = arccos(2*phase - 1)
        try:
            # 限制在 -1 到 1 之间以防浮点误差
            val = max(-1.0, min(1.0, 2 * moon_phase - 1))
            alpha_rad = math.acos(val)
            alpha_deg = math.degrees(alpha_rad)
        except:
            alpha_deg = 0 if moon_phase > 0.5 else 180
            
        # 经验公式: V = -12.73 + 0.026*|alpha| + 4e-9*alpha^4
        # 满月 V = -12.73, 新月 V ~ -2
        v_moon = -12.73 + 0.026 * abs(alpha_deg) + 4e-9 * math.pow(alpha_deg, 4)
        
        # 3. 计算相对亮度因子 (相对于满月)
        # 亮度比 = 10^((V_ref - V_moon) / 2.5)
        # 这是一个 0~1 的值，表示当前月亮亮度相对于满月的比例
        brightness_factor = math.pow(10, (-12.73 - v_moon) / -2.5)
        
        # 4. 高度角修正 (大气消光和散射)
        # 月亮越高，直接光越强，散射光分布越广
        if moon_altitude >= 0:
            # 简化的大气质量模型: Airmass ~ 1/sin(h)
            # 但对于光污染干扰，我们更关心散射。
            # 经验上，月亮越高，对全天背景的增亮越显著
            # 使用 sin(alt) 作为因子，但在低空保留一定散射值
            alt_rad = math.radians(moon_altitude)
            altitude_factor = math.sin(alt_rad) * 0.8 + 0.2
        else:
            # 地平线以下 -18 ~ 0 度，线性衰减
            # 此时只有大气散射的余辉
            altitude_factor = (18 + moon_altitude) / 18 * 0.1
            
        # 5. 最终干扰指数 (0-100)
        interference = brightness_factor * altitude_factor * 100
        
        return min(100, max(0, interference))

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
