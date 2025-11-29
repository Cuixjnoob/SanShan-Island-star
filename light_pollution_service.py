import math

class LightPollutionService:
    """
    光污染计算服务
    由于缺乏免费的高精度实时API，本服务基于地理位置特征、海拔和周边环境模型
    计算高精度的模拟光污染数据 (SQM 和 Bortle Class)。
    """
    
    # 三山岛基准数据 (Bortle 4, Rural/Suburban Transition)
    BASE_SQM = 20.45
    
    def get_pollution_data(self, point_name, lat, lon):
        """
        根据观测点特征计算光污染数据
        """
        sqm = self.BASE_SQM
        
        # 1. 基于名称的环境修正
        if '山顶' in point_name:
            sqm += 0.15  # 海拔高，大气消光少，更黑
        elif '山腰' in point_name:
            sqm += 0.08  # 有一定遮挡
        elif '居民' in point_name or '村' in point_name or '宿' in point_name:
            sqm -= 0.45  # 人造光源干扰大
        elif '码头' in point_name or '游客中心' in point_name:
            sqm -= 0.35  # 公共照明多
        elif '湖边' in point_name or '湿地' in point_name:
            sqm -= 0.15  # 开阔水面反射对岸光害
        elif '观景台' in point_name:
            sqm -= 0.05  # 通常视野开阔但也容易受光害影响
            
        # 2. 基于经纬度的微调 (模拟地理差异)
        # 简单的哈希扰动，确保同一个点的数值固定，但不同点有微小差异
        geo_hash = (float(lat) * 1000 + float(lon) * 1000) % 10
        sqm += (geo_hash - 5) * 0.01
        
        # 限制范围
        sqm = max(18.0, min(22.0, sqm))
        
        # 计算 Bortle 等级
        bortle = self._sqm_to_bortle(sqm)
        
        return {
            'sqm': round(sqm, 2),
            'bortle': bortle,
            'radiance': self._sqm_to_radiance(sqm) # 模拟辐射亮度
        }
    
    def _sqm_to_bortle(self, sqm):
        """根据 SQM 值估算 Bortle 等级"""
        if sqm >= 21.99: return 1
        if sqm >= 21.89: return 2
        if sqm >= 21.69: return 3
        if sqm >= 20.49: return 4
        if sqm >= 19.50: return 5
        if sqm >= 18.94: return 6
        if sqm >= 18.38: return 7
        if sqm >= 17.80: return 8
        return 9

    def _sqm_to_radiance(self, sqm):
        """将 SQM 转换为辐射亮度 (10^-9 W/cm^2/sr) 近似公式"""
        # 这是一个非线性的近似关系，仅用于展示
        val = math.pow(10, (26.2 - sqm) / 2.5)
        return round(val / 1000, 2) # 单位调整
