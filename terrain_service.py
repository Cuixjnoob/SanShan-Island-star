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

    def get_wild_spots(self, grid_size=15) -> List[Dict]:
        """
        获取野外推荐点
        grid_size: 网格密度，15x15大约225个点
        """
        # 1. 尝试从缓存读取
        if os.path.exists(self.CACHE_FILE):
            with open(self.CACHE_FILE, 'r') as f:
                cached_data = json.load(f)
                if cached_data:
                    return self._analyze_spots(cached_data)

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
            # Open-Elevation API 格式
            # POST https://api.open-elevation.com/api/v1/lookup
            # body: { "locations": [...] }
            
            # 分批请求，避免超时
            batch_size = 50
            all_results = []
            
            for i in range(0, len(locations), batch_size):
                batch = locations[i:i+batch_size]
                response = requests.post(
                    'https://api.open-elevation.com/api/v1/lookup',
                    json={"locations": batch},
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    all_results.extend(data['results'])
            
            # 写入缓存
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(all_results, f)
                
            return self._analyze_spots(all_results)

        except Exception as e:
            print(f"Error fetching elevation: {e}")
            # 如果API失败，返回空列表或模拟数据
            return []

    def _analyze_spots(self, points: List[Dict]) -> List[Dict]:
        """
        分析并评分
        评分标准：
        1. 海拔越高越好 (权重 0.7)
        2. (模拟) 距离岛中心越远光污染越小 (权重 0.3)
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
            # 海拔得分 (0-100)
            ele_score = (p['elevation'] / max_ele) * 100 if max_ele > 0 else 0
            
            # 距离得分 (离中心越远越好，模拟边缘光污染少) - 这是一个简单的启发式
            dist = math.sqrt((p['latitude'] - center_lat)**2 + (p['longitude'] - center_lon)**2)
            dist_score = min(dist * 1000, 100) # 简单缩放

            # 综合评分
            total_score = 0.8 * ele_score + 0.2 * dist_score
            
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
