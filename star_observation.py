#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
三山岛观星选址程序
帮助用户根据星星方向选择最佳观测点
"""

import csv
import math
import warnings
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from astropy.coordinates import EarthLocation, AltAz, SkyCoord, get_body
from astropy.time import Time
import astropy.units as u
from astropy.utils.exceptions import AstropyWarning
from astropy.utils import iers
import json

# 忽略astropy的IERS警告
warnings.filterwarnings('ignore', category=AstropyWarning)

# 设置astropy为离线模式，避免下载IERS数据卡住
iers.conf.auto_download = False
iers.conf.auto_max_age = None


# 常见亮星数据库（含中英文名称和坐标）
BRIGHT_STARS = {
    'Sirius': {'name_cn': '天狼星', 'ra': 101.287, 'dec': -16.716, 'mag': -1.46},
    'Canopus': {'name_cn': '老人星', 'ra': 95.988, 'dec': -52.696, 'mag': -0.72},
    'Arcturus': {'name_cn': '大角星', 'ra': 213.915, 'dec': 19.182, 'mag': -0.05},
    'Vega': {'name_cn': '织女星', 'ra': 279.234, 'dec': 38.783, 'mag': 0.03},
    'Capella': {'name_cn': '五车二', 'ra': 79.172, 'dec': 45.998, 'mag': 0.08},
    'Rigel': {'name_cn': '参宿七', 'ra': 78.634, 'dec': -8.202, 'mag': 0.12},
    'Procyon': {'name_cn': '南河三', 'ra': 114.826, 'dec': 5.225, 'mag': 0.38},
    'Betelgeuse': {'name_cn': '参宿四', 'ra': 88.793, 'dec': 7.407, 'mag': 0.50},
    'Altair': {'name_cn': '牛郎星', 'ra': 297.696, 'dec': 8.868, 'mag': 0.77},
    'Aldebaran': {'name_cn': '毕宿五', 'ra': 68.980, 'dec': 16.509, 'mag': 0.85},
    'Spica': {'name_cn': '角宿一', 'ra': 201.298, 'dec': -11.161, 'mag': 0.98},
    'Antares': {'name_cn': '心宿二', 'ra': 247.352, 'dec': -26.432, 'mag': 1.09},
    'Pollux': {'name_cn': '北河三', 'ra': 116.329, 'dec': 28.026, 'mag': 1.14},
    'Fomalhaut': {'name_cn': '北落师门', 'ra': 344.413, 'dec': -29.622, 'mag': 1.16},
    'Deneb': {'name_cn': '天津四', 'ra': 310.358, 'dec': 45.280, 'mag': 1.25},
    'Regulus': {'name_cn': '轩辕十四', 'ra': 152.093, 'dec': 11.967, 'mag': 1.35},
    'Castor': {'name_cn': '北河二', 'ra': 113.650, 'dec': 31.888, 'mag': 1.58},
    'Polaris': {'name_cn': '北极星', 'ra': 37.954, 'dec': 89.264, 'mag': 1.98},
    # 新增更多亮星
    'Achernar': {'name_cn': '水委一', 'ra': 24.429, 'dec': -57.237, 'mag': 0.46},
    'Bellatrix': {'name_cn': '参宿五', 'ra': 81.283, 'dec': 6.350, 'mag': 1.64},
    'Alnilam': {'name_cn': '参宿二', 'ra': 84.053, 'dec': -1.202, 'mag': 1.69},
    'Alnitak': {'name_cn': '参宿一', 'ra': 85.190, 'dec': -1.943, 'mag': 1.77},
    'Saiph': {'name_cn': '参宿六', 'ra': 86.939, 'dec': -9.669, 'mag': 2.06},
    'Mirfak': {'name_cn': '天船三', 'ra': 51.081, 'dec': 49.861, 'mag': 1.79},
    'Dubhe': {'name_cn': '天枢', 'ra': 165.932, 'dec': 61.751, 'mag': 1.79},
    'Alkaid': {'name_cn': '摇光', 'ra': 206.885, 'dec': 49.313, 'mag': 1.86},
    'Alioth': {'name_cn': '玉衡', 'ra': 193.507, 'dec': 55.960, 'mag': 1.77},
    'Mizar': {'name_cn': '开阳', 'ra': 200.981, 'dec': 54.925, 'mag': 2.27},
    'Merak': {'name_cn': '天璇', 'ra': 165.460, 'dec': 56.382, 'mag': 2.37},
    'Phecda': {'name_cn': '天玑', 'ra': 178.457, 'dec': 53.695, 'mag': 2.44},
    'Megrez': {'name_cn': '天权', 'ra': 183.856, 'dec': 57.032, 'mag': 3.31},
    'Shaula': {'name_cn': '尾宿八', 'ra': 263.402, 'dec': -37.104, 'mag': 1.63},
    'Sargas': {'name_cn': '尾宿五', 'ra': 264.330, 'dec': -42.998, 'mag': 1.87},
    'Kaus Australis': {'name_cn': '箕宿三', 'ra': 276.043, 'dec': -34.385, 'mag': 1.85},
    'Nunki': {'name_cn': '斗宿四', 'ra': 283.816, 'dec': -26.297, 'mag': 2.02},
    'Peacock': {'name_cn': '孔雀十一', 'ra': 306.412, 'dec': -56.735, 'mag': 1.94},
    'Alphard': {'name_cn': '星宿一', 'ra': 141.897, 'dec': -8.658, 'mag': 1.98},
    'Hamal': {'name_cn': '娄宿三', 'ra': 31.793, 'dec': 23.462, 'mag': 2.00},
    'Schedar': {'name_cn': '王良一', 'ra': 10.127, 'dec': 56.537, 'mag': 2.23},
    'Diphda': {'name_cn': '土司空', 'ra': 10.897, 'dec': -17.987, 'mag': 2.04},
    'Rasalhague': {'name_cn': '侯', 'ra': 263.733, 'dec': 12.560, 'mag': 2.08},
}

# 太阳系天体
SOLAR_SYSTEM_BODIES = {
    'sun': '太阳',
    'moon': '月亮',
    'mercury': '水星',
    'venus': '金星',
    'mars': '火星',
    'jupiter': '木星',
    'saturn': '土星',
    'uranus': '天王星',
    'neptune': '海王星'
}


class ObservationPoint:
    """观测点类"""
    
    def __init__(self, longitude: float, latitude: float, difficulty: str, 
                 view_start: float, view_end: float, name: str):
        self.longitude = longitude
        self.latitude = latitude
        self.difficulty = difficulty  # 难易到达程度（简单/中等/困难）
        self.view_start = view_start  # 视角起始（顺时针，北为0°）
        self.view_end = view_end      # 视角结束（顺时针，北为0°）
        self.name = name
    
    def can_observe_azimuth(self, azimuth: float) -> bool:
        """判断该观测点是否可以观测指定方位角的天体"""
        # 标准化方位角到0-360
        azimuth = azimuth % 360
        
        # 如果视角范围不跨越0度
        if self.view_start <= self.view_end:
            return self.view_start <= azimuth <= self.view_end
        else:
            # 如果视角范围跨越0度（例如：330° - 30°）
            return azimuth >= self.view_start or azimuth <= self.view_end
    
    def __repr__(self):
        return f"{self.name} ({self.longitude}, {self.latitude})"


class StarObservationSelector:
    """观星选址选择器"""
    
    # 三山岛的默认位置
    SANSHAN_ISLAND_LON = 120.45
    SANSHAN_ISLAND_LAT = 31.22
    
    def __init__(self, csv_file: str = 'data.csv'):
        """初始化，读取CSV数据"""
        self.observation_points = []
        self.load_data(csv_file)
        self.location = EarthLocation(
            lat=self.SANSHAN_ISLAND_LAT * u.deg,
            lon=self.SANSHAN_ISLAND_LON * u.deg
        )
    
    def load_data(self, csv_file: str):
        """从CSV文件加载观测点数据"""
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig自动移除BOM
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 使用空格分割
                    parts = line.split()
                    if len(parts) >= 6:
                        point = ObservationPoint(
                            longitude=float(parts[0]),
                            latitude=float(parts[1]),
                            difficulty=parts[2],
                            view_start=float(parts[3]),
                            view_end=float(parts[4]),
                            name=' '.join(parts[5:])  # 名称可能包含空格
                        )
                        self.observation_points.append(point)
            
            # 计算所有观测点的中心位置
            if self.observation_points:
                self.avg_lat = sum(p.latitude for p in self.observation_points) / len(self.observation_points)
                self.avg_lon = sum(p.longitude for p in self.observation_points) / len(self.observation_points)
            else:
                self.avg_lat = self.SANSHAN_ISLAND_LAT
                self.avg_lon = self.SANSHAN_ISLAND_LON
                
        except FileNotFoundError:
            raise
        except Exception as e:
            raise
    
    def get_visible_stars(self, obs_time: datetime = None, min_altitude: float = 0) -> List[Dict]:
        """
        获取当前可见的所有星星列表
        返回包含星星名称、方位角、高度角等信息的列表
        """
        visible_stars = []
        
        try:
            # 设置观测时间
            if obs_time is None:
                obs_time = datetime.now()
            
            time = Time(obs_time)
            altaz_frame = AltAz(obstime=time, location=self.location)
            
            # 检查亮星
            for star_name, star_data in BRIGHT_STARS.items():
                try:
                    star_coord = SkyCoord(
                        ra=star_data['ra'] * u.deg,
                        dec=star_data['dec'] * u.deg,
                        frame='icrs'
                    )
                    star_altaz = star_coord.transform_to(altaz_frame)
                    
                    altitude = float(star_altaz.alt.degree)
                    azimuth = float(star_altaz.az.degree)
                    
                    if altitude >= min_altitude:
                        visible_stars.append({
                            'name': str(star_name),
                            'name_cn': str(star_data['name_cn']),
                            'type': 'star',
                            'azimuth': round(azimuth, 2),
                            'altitude': round(altitude, 2),
                            'magnitude': float(star_data['mag']),
                            'ra': float(star_data['ra']),
                            'dec': float(star_data['dec'])
                        })
                except Exception as e:
                    continue
            
            # 检查太阳系天体
            for body_key, body_name_cn in SOLAR_SYSTEM_BODIES.items():
                try:
                    body_coord = get_body(body_key, time, self.location)
                    body_altaz = body_coord.transform_to(altaz_frame)
                    
                    altitude = float(body_altaz.alt.degree)
                    azimuth = float(body_altaz.az.degree)
                    
                    if altitude >= min_altitude:
                        visible_stars.append({
                            'name': str(body_key.capitalize()),
                            'name_cn': str(body_name_cn),
                            'type': 'planet',
                            'azimuth': round(azimuth, 2),
                            'altitude': round(altitude, 2),
                            'magnitude': 0.0,
                            'ra': float(body_coord.ra.degree),
                            'dec': float(body_coord.dec.degree)
                        })
                except Exception as e:
                    continue
            
            # 按高度角排序（从高到低）
            visible_stars.sort(key=lambda x: x['altitude'], reverse=True)
            
        except Exception as e:
            # 如果完全失败，返回空列表
            pass
        
        return visible_stars
    
    def _get_equipment_recommendation(self, name_cn: str, magnitude: Optional[float] = None) -> str:
        """根据天体类型和星等推荐观测器材"""
        # 太阳系天体
        if name_cn == '太阳':
            return "专业滤镜 (Solar Filter)"
        if name_cn == '月亮':
            return "肉眼 / 双筒 / 天文望远镜"
        
        bright_planets = ['水星', '金星', '火星', '木星', '土星']
        if name_cn in bright_planets:
            return "肉眼可见 / 双筒望远镜"
        
        dim_planets = ['天王星', '海王星']
        if name_cn in dim_planets:
            return "天文望远镜"
            
        # 恒星
        if magnitude is not None:
            if magnitude < 2.0:
                return "肉眼可见"
            elif magnitude < 5.0:
                return "双筒望远镜"
            else:
                return "天文望远镜"
        
        # 默认情况
        return "天文望远镜"

    def get_star_info(self, star_name: str, obs_time: datetime = None) -> Optional[Dict]:
        """获取星星的天文信息"""
        if obs_time is None:
            obs_time = datetime.now()
        
        try:
            name_cn = star_name  # 默认中文名就是输入名称
            magnitude = None
            
            # 检查是否在亮星数据库中
            if star_name in BRIGHT_STARS:
                star_data = BRIGHT_STARS[star_name]
                name_cn = star_data['name_cn']
                magnitude = star_data['mag']
                star_coord = SkyCoord(
                    ra=star_data['ra'] * u.deg,
                    dec=star_data['dec'] * u.deg,
                    frame='icrs'
                )
            # 检查是否是太阳系天体
            elif star_name.lower() in SOLAR_SYSTEM_BODIES or star_name in SOLAR_SYSTEM_BODIES.values():
                time = Time(obs_time)
                # 中文名转英文
                body_key = star_name.lower()
                for key, cn_name in SOLAR_SYSTEM_BODIES.items():
                    if star_name == cn_name:
                        body_key = key
                        name_cn = cn_name
                        break
                    elif star_name.lower() == key:
                        name_cn = cn_name
                        break
                star_coord = get_body(body_key, time, self.location)
                # 太阳系天体星等暂定为None，由名称判断器材
            else:
                # 尝试从Simbad查询
                try:
                    star_coord = SkyCoord.from_name(star_name)
                except:
                    return None
            
            # 计算地平坐标
            time = Time(obs_time)
            altaz_frame = AltAz(obstime=time, location=self.location)
            star_altaz = star_coord.transform_to(altaz_frame)
            
            azimuth = star_altaz.az.degree
            altitude = star_altaz.alt.degree
            
            # 获取器材推荐
            equipment = self._get_equipment_recommendation(name_cn, magnitude)
            
            result = {
                'name': star_name,
                'name_cn': name_cn,
                'azimuth': azimuth,
                'altitude': altitude,
                'ra': star_coord.ra.degree,
                'dec': star_coord.dec.degree,
                'observable': bool(altitude > 0),
                'magnitude': magnitude,
                'equipment': equipment
            }
            
            return result
            
        except Exception as e:
            return None
    
    def find_suitable_points(self, azimuth: float) -> List[ObservationPoint]:
        """查找可以观测指定方位角的观测点"""
        suitable_points = []
        
        for point in self.observation_points:
            if point.can_observe_azimuth(azimuth):
                suitable_points.append(point)
        
        return suitable_points
    
    def _calculate_bearing(self, lat1, lon1, lat2, lon2):
        """计算两点间的方位角"""
        y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
        x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
            math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(lon2 - lon1))
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360) % 360

    def calculate_score(self, point: ObservationPoint, azimuth: float, altitude: float) -> float:
        """
        计算观测点的综合评分
        评分规则：
        1. 观测点地理位置与星星方位的匹配度（权重40%）
           - 比如星星在东方，岛屿东侧的观测点得分更高
        2. 星星在观测点视角范围内的位置（权重40%）
           - 星星越接近视角中心，得分越高
        3. 难易程度（权重20%）
           - 越容易到达得分越高
        """
        # 1. 地理位置匹配度分数（0-40分）
        # 计算观测点相对于中心的方位
        point_azimuth = self._calculate_bearing(self.avg_lat, self.avg_lon, point.latitude, point.longitude)
        
        # 计算方位匹配度
        angle_diff = abs(azimuth - point_azimuth)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        
        # 差异越小分越高
        location_match_score = max(0, 40 * (1 - angle_diff / 180))
        
        # 2. 视角范围位置分数（0-40分）
        # 计算视角中心
        if point.view_start <= point.view_end:
            view_center = (point.view_start + point.view_end) / 2
            view_range = point.view_end - point.view_start
        else:
            view_center = ((point.view_start + point.view_end + 360) / 2) % 360
            view_range = (point.view_end + 360 - point.view_start)
        
        # 计算星星偏离视角中心的角度
        view_angle_diff = abs(azimuth - view_center)
        if view_angle_diff > 180:
            view_angle_diff = 360 - view_angle_diff
        
        # 星星在视角中心 → 高分
        if view_range > 0:
            max_offset = view_range / 2
            centrality = max(0, 1 - (view_angle_diff / max_offset))
        else:
            centrality = 1.0
        
        view_position_score = centrality * 40
        
        # 3. 难易程度分数（0-20分）
        # difficulty越小越容易。假设difficulty范围0-100
        # 将文字难度转换为数值进行计算
        difficulty_val = 50 # 默认中等
        if point.difficulty == '简单':
            difficulty_val = 20
        elif point.difficulty == '中等':
            difficulty_val = 50
        elif point.difficulty == '困难':
            difficulty_val = 80
            
        difficulty_score = (100 - difficulty_val) * 0.2
        
        # 总分 = 地理位置(40%) + 视角位置(40%) + 难易度(20%)
        total_score = location_match_score + view_position_score + difficulty_score
        
        return total_score
    
    def rank_points(self, points: List[ObservationPoint], 
                   azimuth: float, altitude: float) -> List[Tuple[ObservationPoint, float]]:
        """对观测点进行排名"""
        ranked = []
        for point in points:
            score = self.calculate_score(point, azimuth, altitude)
            ranked.append((point, score))
        
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
    
    def recommend_for_star(self, star_name: str, obs_time: datetime = None) -> Optional[Dict]:
        """为指定星星推荐最佳观测点"""
        print("\n" + "=" * 80)
        
        # 获取星星信息
        star_info = self.get_star_info(star_name, obs_time)
        
        if star_info is None:
            return None
        
        if not star_info['observable']:
            print(f"\n❌ '{star_name}' 当前在地平线以下（高度角: {star_info['altitude']:.1f}°）")
            print(f"   暂时无法观测，请选择其他时间或其他天体。")
            return None
        
        # 查找适合的观测点
        azimuth = star_info['azimuth']
        altitude = star_info['altitude']
        suitable_points = self.find_suitable_points(azimuth)
        
        if not suitable_points:
            print(f"\n❌ 抱歉，没有找到可以观测该方位角 ({azimuth:.1f}°) 的观测点。")
            return None
        
        # 排名并推荐
        ranked_points = self.rank_points(suitable_points, azimuth, altitude)
        
        print(f"\n🌟 观测 '{star_name}' 的推荐观测点（共{len(ranked_points)}个）：")
        print("=" * 80)
        print(f"\n天体信息:")
        print(f"  方位角: {azimuth:.1f}°")
        print(f"  高度角: {altitude:.1f}°")
        
        print(f"\n推荐观测点排名:")
        print("-" * 80)
        
        for idx, (point, score) in enumerate(ranked_points, 1):
            if idx == 1:
                print(f"\n🏆 最佳推荐 #{idx} - 综合评分: {score:.1f}")
            else:
                print(f"\n备选方案 #{idx} - 综合评分: {score:.1f}")
            
            print(f"  📍 名称: {point.name}")
            print(f"  📌 位置: 经度 {point.longitude}°, 纬度 {point.latitude}°")
            print(f"  🚶 难易程度: {point.difficulty}")
            print(f"  🧭 可观测范围: {point.view_start}° - {point.view_end}°")
            
            if idx == 1:
                if point.difficulty == '简单':
                    print(f"  💡 推荐理由: 交通便利，易于到达")
                else:
                    print(f"  💡 推荐理由: 最佳视角")
        
        print("\n" + "=" * 80)
        
        best_point, best_score = ranked_points[0]
        return {
            'star_info': star_info,
            'best_point': {
                'name': best_point.name,
                'longitude': best_point.longitude,
                'latitude': best_point.latitude,
                'difficulty': best_point.difficulty,
                'view_start': best_point.view_start,
                'view_end': best_point.view_end,
                'score': best_score
            },
            'all_points': [
                {
                    'name': p.name,
                    'longitude': p.longitude,
                    'latitude': p.latitude,
                    'difficulty': p.difficulty,
                    'view_start': p.view_start,
                    'view_end': p.view_end,
                    'score': s
                }
                for p, s in ranked_points
            ]
        }
    
    def get_all_points(self) -> List[Dict]:
        """获取所有观测点信息"""
        return [
            {
                'name': p.name,
                'longitude': p.longitude,
                'latitude': p.latitude,
                'difficulty': p.difficulty,
                'view_start': p.view_start,
                'view_end': p.view_end
            }
            for p in self.observation_points
        ]
    
    def get_point_by_name(self, name: str) -> Optional[ObservationPoint]:
        """根据名称获取观测点"""
        for point in self.observation_points:
            if point.name == name:
                return point
        return None

    def get_visible_stars_from_point(self, point_name: str, obs_time: datetime = None) -> Dict:
        """获取特定观测点可见的星星"""
        point = self.get_point_by_name(point_name)
        if not point:
            return None
            
        # 获取所有在地平线以上的星星
        all_visible = self.get_visible_stars(obs_time=obs_time, min_altitude=0)
        
        # 根据观测点的视角限制进行过滤
        point_visible_stars = []
        for star in all_visible:
            if point.can_observe_azimuth(star['azimuth']):
                point_visible_stars.append(star)
                
        return {
            'point': {
                'name': point.name,
                'longitude': point.longitude,
                'latitude': point.latitude,
                'difficulty': point.difficulty,
                'view_start': point.view_start,
                'view_end': point.view_end
            },
            'stars': point_visible_stars,
            'count': len(point_visible_stars)
        }


def main():
    """主程序"""
    print("=" * 80)
    print("🌠 三山岛观星选址系统 🌠")
    print("=" * 80)
    print("\n欢迎使用智能观星选址系统！")
    print("输入您想观测的星星名称，系统将自动为您推荐最佳观测点。")
    
    try:
        selector = StarObservationSelector('data.csv')
        
        while True:
            print("\n" + "=" * 80)
            print("请输入您想要观测的星星名称（或输入 'q' 退出）:")
            print("\n💫 常见星星推荐:")
            print("  明亮恒星: Sirius(天狼星), Vega(织女星), Altair(牛郎星)")
            print("            Polaris(北极星), Betelgeuse(参宿四), Rigel(参宿七)")
            print("  太阳系:   太阳, 月亮, 火星, 木星, 土星, 金星")
            print("=" * 80)
            
            star_name = input("\n🌟 星星名称: ").strip()
            
            if star_name.lower() in ['q', 'quit', '退出', 'exit']:
                print("\n✨ 感谢使用三山岛观星选址系统！")
                print("💫 祝您观星愉快，晴空万里！")
                break
            
            if not star_name:
                print("⚠️  请输入有效的星星名称！")
                continue
            
            result = selector.recommend_for_star(star_name)
            
            if result:
                print(f"\n✅ 系统推荐: 前往 '{result['best_point']['name']}' 观测 '{star_name}'")
    
    except FileNotFoundError:
        print("\n❌ 错误: 找不到 data.csv 文件，请确保文件在当前目录下。")
    except KeyboardInterrupt:
        print("\n\n✨ 程序已中断。再见小可爱！")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
