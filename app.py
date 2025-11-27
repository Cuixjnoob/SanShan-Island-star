#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web服务器 - 提供观星选址服务的HTTP API
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from star_observation import StarObservationSelector
from terrain_service import TerrainService
from weather_service import WeatherService
from datetime import datetime
import warnings
from astropy.utils.exceptions import AstropyWarning

warnings.filterwarnings('ignore', category=AstropyWarning)

app = Flask(__name__)
CORS(app)

# 初始化观星选择器
selector = StarObservationSelector('data.csv')
# 初始化地形服务
terrain_service = TerrainService()
# 初始化天气服务
weather_service = WeatherService()


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/test')
def test():
    """测试页面"""
    return render_template('test.html')


@app.route('/star/<star_name>')
def star_detail(star_name):
    """星球详情页面"""
    return render_template('star_detail.html', star_name=star_name)


@app.route('/api/search', methods=['POST'])
def search_star():
    """搜索星星并推荐观测点"""
    try:
        data = request.get_json()
        star_name = data.get('star_name', '').strip()
        obs_time_str = data.get('obs_time', None)
        
        if not star_name:
            return jsonify({'error': '请输入星星名称'}), 400
        
        # 处理观测时间
        obs_time = None
        if obs_time_str:
            try:
                # 解析ISO格式时间字符串
                obs_time = datetime.fromisoformat(obs_time_str.replace('Z', '+00:00'))
            except:
                # 如果解析失败，使用当前时间
                obs_time = None
        
        # 获取推荐结果
        result = selector.recommend_for_star(star_name, obs_time)
        
        if result is None:
            return jsonify({'error': '未找到该星星或当前无法观测'}), 404
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


@app.route('/api/visible-stars', methods=['GET'])
def get_visible_stars():
    """获取当前可见的星星列表"""
    try:
        min_altitude = float(request.args.get('min_altitude', 0))
        obs_time_str = request.args.get('obs_time', None)
        
        # 处理观测时间
        obs_time = None
        if obs_time_str:
            try:
                # 解析ISO格式时间字符串
                obs_time = datetime.fromisoformat(obs_time_str.replace('Z', '+00:00'))
            except:
                # 如果解析失败，使用当前时间
                obs_time = None
        
        visible_stars = selector.get_visible_stars(min_altitude=min_altitude, obs_time=obs_time)
        
        # 确保返回的数据是可序列化的
        result = {
            'stars': visible_stars,
            'count': len(visible_stars),
            'status': 'success'
        }
        
        return jsonify(result), 200
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return jsonify({
            'error': str(e),
            'detail': error_detail,
            'stars': [],
            'count': 0,
            'status': 'error'
        }), 500


@app.route('/api/points', methods=['GET'])
def get_all_points():
    """获取所有观测点信息"""
    try:
        points = selector.get_all_points()
        return jsonify(points), 200
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


@app.route('/api/all-stars', methods=['GET'])
def get_all_stars():
    """获取所有星星和行星的列表（用于检索）"""
    try:
        from star_observation import BRIGHT_STARS, SOLAR_SYSTEM_BODIES
        
        all_celestial = []
        
        # 添加所有亮星
        for star_name, star_data in BRIGHT_STARS.items():
            all_celestial.append({
                'name': star_name,
                'name_cn': star_data['name_cn'],
                'type': 'star',
                'magnitude': star_data['mag']
            })
        
        # 添加太阳系天体
        for body_key, body_name_cn in SOLAR_SYSTEM_BODIES.items():
            all_celestial.append({
                'name': body_key.capitalize(),
                'name_cn': body_name_cn,
                'type': 'planet',
                'magnitude': None
            })
        
        # 按星等排序（亮的在前）
        all_celestial.sort(key=lambda x: x['magnitude'] if x['magnitude'] is not None else 999)
        
        return jsonify({
            'celestial_objects': all_celestial,
            'count': len(all_celestial)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/point/<point_name>')
def point_detail(point_name):
    """观测点详情页面"""
    return render_template('point_detail.html', point_name=point_name)


@app.route('/api/point/<point_name>')
def get_point_details(point_name):
    """获取观测点详情及可见星星"""
    try:
        obs_time_str = request.args.get('time', None)
        
        # 处理观测时间
        obs_time = None
        if obs_time_str:
            try:
                obs_time = datetime.fromisoformat(obs_time_str.replace('Z', '+00:00'))
            except:
                obs_time = None
        
        result = selector.get_visible_stars_from_point(point_name, obs_time)
        
        if result is None:
            return jsonify({'error': '未找到该观测点'}), 404
            
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


@app.route('/api/wild-spots')
def get_wild_spots():
    """获取野外推荐观测点"""
    try:
        spots = terrain_service.get_wild_spots()
        return jsonify(spots), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/weather')
def get_weather():
    """获取当前天气和观星条件"""
    try:
        weather = weather_service.get_current_weather()
        if weather:
            return jsonify(weather), 200
        else:
            return jsonify({'error': '无法获取天气数据'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
