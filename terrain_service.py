import requests
import json
import os
import math
from typing import List, Dict

class TerrainService:
    # 三山岛大致范围
    LAT_MIN = 31.015
    LAT_MAX = 31.045
    LON_MIN = 120.275
    LON_MAX = 120.315
    
    # 太湖水位大致在3-4米，我们过滤掉低海拔区域
    MIN_ELEVATION = 5.0
    
    CACHE_FILE = 'terrain_cache.json'

    def __init__(self):
        self.grid_points = []

    def get_wild_spots(self, grid_size=15, target_azimuth: float = None, target_altitude: float = None) -> List[Dict]:
        """
        获取野外推荐点
        grid_size: 网格密度，15x15大约225个点
        target_azimuth: 目标天体方位角 (可选)
        target_altitude: 目标天体高度角 (可选)
        """
        # 1. 尝试从缓存读取
        if os.path.exists(self.CACHE_FILE):
            with open(self.CACHE_FILE, 'r') as f:
                cached_data = json.load(f)
                if cached_data:
                    return self._analyze_spots(cached_data, target_azimuth, target_altitude)

        # 2. 生成网格坐标
        locations = []
        lat_step = (self.LAT_MAX - self.LAT_MIN) / grid_size
        lon_step = (self.LON_MAX - self.LON_MIN) / grid_size

        for i in range(grid_size):
            for j in range(grid_size):
                lat = self.LAT_MIN + i * lat_step
                lon = self.LON_MIN + j * lon_step
                locations.append({"latitude": round(lat, 4), "longitude": round(lon, 4)})

        # 3. 调用API获取海拔
        try:
            # 优先读取缓存
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r') as f:
                    all_results = json.load(f)
                    return self._analyze_spots(all_results, target_azimuth, target_altitude)

            # 如果没有缓存，由于无法访问国外API，生成模拟数据或返回空
            # 实际部署建议预先生成 terrain_cache.json
            print("Warning: No terrain cache found and external API disabled.")
            return []

        except Exception as e:
            print(f"Error fetching elevation: {e}")
            # 如果API失败，返回空列表或模拟数据
            return []

    def _calculate_bearing(self, lat1, lon1, lat2, lon2):
        """计算两点间的方位角"""
        y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
        x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
            math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(lon2 - lon1))
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360) % 360

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """计算两点间距离（米）"""
        R = 6371000 # 地球半径
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def _check_occlusion(self, point, all_points, target_azimuth, target_altitude):
        """检查是否被遮挡"""
        if target_altitude is None or target_altitude > 60:
            return False # 高空天体一般不被遮挡
            
        for other in all_points:
            if other == point:
                continue
                
            # 如果其他点比当前点低，不可能遮挡
            if other['elevation'] <= point['elevation']:
                continue
                
            # 计算方位角
            bearing = self._calculate_bearing(point['latitude'], point['longitude'], 
                                           other['latitude'], other['longitude'])
            
            # 检查是否在视线方向上 (比如 +/- 5度)
            angle_diff = abs(bearing - target_azimuth)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
                
            if angle_diff < 10: # 在视线方向10度范围内
                dist = self._calculate_distance(point['latitude'], point['longitude'],
                                             other['latitude'], other['longitude'])
                if dist < 10: continue # 太近忽略
                
                # 计算仰角
                ele_diff = other['elevation'] - point['elevation']
                angle_ele = math.degrees(math.atan2(ele_diff, dist))
                
                if angle_ele > target_altitude:
                    return True # 被遮挡
        return False

    def _analyze_spots(self, points: List[Dict], target_azimuth=None, target_altitude=None) -> List[Dict]:
        """
        分析并评分
        评分标准：
        1. 海拔越高越好 (权重 0.4)
        2. 距离岛中心越远光污染越小 (权重 0.2)
        3. (新) 地理位置与观测方向匹配度 (权重 0.4)
        4. (新) 遮挡检测 (直接剔除)
        """
        valid_spots = [p for p in points if p['elevation'] > self.MIN_ELEVATION]
        
        if not valid_spots:
            return []

        # 找到最大海拔用于归一化
        max_ele = max(p['elevation'] for p in valid_spots)
        center_lat = (self.LAT_MIN + self.LAT_MAX) / 2
        center_lon = (self.LON_MIN + self.LON_MAX) / 2

        scored_spots = []
        for p in valid_spots:
            # 0. 遮挡检测
            if target_azimuth is not None and target_altitude is not None:
                if self._check_occlusion(p, valid_spots, target_azimuth, target_altitude):
                    continue # 被遮挡，跳过

            # 1. 海拔得分 (0-100)
            ele_score = (p['elevation'] / max_ele) * 100 if max_ele > 0 else 0
            
            # 2. 距离得分
            dist = math.sqrt((p['latitude'] - center_lat)**2 + (p['longitude'] - center_lon)**2)
            dist_score = min(dist * 1000, 100)

            # 3. 方向匹配得分
            dir_score = 0
            if target_azimuth is not None:
                # 计算点相对于岛中心的方位
                point_bearing = self._calculate_bearing(center_lat, center_lon, p['latitude'], p['longitude'])
                
                # 计算与目标方位的差异
                angle_diff = abs(point_bearing - target_azimuth)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                
                # 差异越小分越高 (0度差->100分, 180度差->0分)
                dir_score = max(0, 100 * (1 - angle_diff / 180))
            else:
                dir_score = 50 # 默认中等分数

            # 综合评分
            # 如果有目标方位，增加方向权重的比重
            if target_azimuth is not None:
                total_score = 0.3 * ele_score + 0.1 * dist_score + 0.6 * dir_score
            else:
                total_score = 0.7 * ele_score + 0.3 * dist_score
            
            scored_spots.append({
                'latitude': p['latitude'],
                'longitude': p['longitude'],
                'elevation': p['elevation'],
                'score': round(total_score, 1),
                'type': 'wild'
            })

        # 按分数排序，取前10个
        scored_spots.sort(key=lambda x: x['score'], reverse=True)
        return scored_spots[:10]
