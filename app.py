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
from light_pollution_service import LightPollutionService
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
# 初始化光污染服务
light_pollution_service = LightPollutionService()


def get_changelog():
    """读取更新日志"""
    logs = []
    try:
        import os
        # 使用绝对路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(base_dir, '日志')
        print(f"Attempting to read log from: {log_path}")
        
        if os.path.exists(log_path):
            content = ""
            # 尝试 UTF-8
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                print("UTF-8 decode failed, trying GBK")
                # 尝试 GBK
                with open(log_path, 'r', encoding='gbk') as f:
                    content = f.read()
            
            if content:
                for line in content.splitlines():
                    line = line.strip()
                    if line:
                        parts = line.split(' ', 1)
                        if len(parts) == 2:
                            logs.append({'date': parts[0], 'content': parts[1]})
                        else:
                            logs.append({'date': '', 'content': line})
                print(f"Successfully read {len(logs)} log entries")
            else:
                print("Log file is empty")
        else:
            print("Log file not found")
            
        # 倒序排列，最新的在最前
        return logs[::-1]
    except Exception as e:
        print(f"Error reading log file: {e}")
    return []


@app.route('/')
def index():
    """主页"""
    logs = get_changelog()
    return render_template('index.html', logs=logs)


@app.route('/star/<star_name>')
def star_detail(star_name):
    """星球详情页面"""
    return render_template('star_detail.html', star_name=star_name)


def calculate_ahp_weights(preferences):
    """
    根据AHP成对比较矩阵计算权重
    preferences: dict with keys 'loc_vs_view', 'loc_vs_diff', 'view_vs_diff'
    Values are from 1/9 to 9.
    """
    try:
        # Criteria: Location, View, Difficulty, Light Pollution
        # Matrix:
        #       Loc   View  Diff  LP
        # Loc   1     a     b     d
        # View  1/a   1     c     e
        # Diff  1/b   1/c   1     f
        # LP    1/d   1/e   1/f   1
        
        a = float(preferences.get('loc_vs_view', 1))
        b = float(preferences.get('loc_vs_diff', 1))
        c = float(preferences.get('view_vs_diff', 1))
        
        # 新增的光污染比较参数，默认为1
        d = float(preferences.get('loc_vs_lp', 1))
        e = float(preferences.get('view_vs_lp', 1))
        f = float(preferences.get('diff_vs_lp', 1))
        
        matrix = [
            [1,   a,   b,   d],
            [1/a, 1,   c,   e],
            [1/b, 1/c, 1,   f],
            [1/d, 1/e, 1/f, 1]
        ]
        
        # 列向量归一化法计算权重
        n = 4
        col_sums = [sum(row[i] for row in matrix) for i in range(n)]
        
        norm_matrix = [[matrix[i][j] / col_sums[j] for j in range(n)] for i in range(n)]
        
        weights_list = [sum(row) / n for row in norm_matrix]
        
        return {
            'location': weights_list[0],
            'view': weights_list[1],
            'difficulty': weights_list[2],
            'light_pollution': weights_list[3]
        }
    except Exception as e:
        print(f"AHP calculation error: {e}")
        return None


@app.route('/api/search', methods=['POST'])
def search_star():
    """搜索星星并推荐观测点"""
    try:
        data = request.get_json()
        star_name = data.get('star_name', '').strip()
        obs_time_str = data.get('obs_time', None)
        ahp_preferences = data.get('ahp_preferences', None)
        
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
        
        # 计算权重
        weights = None
        if ahp_preferences:
            weights = calculate_ahp_weights(ahp_preferences)
            
        # 获取推荐结果
        result = selector.recommend_for_star(star_name, obs_time, weights)
        
        if result is None:
            return jsonify({'error': '未找到该星星或当前无法观测'}), 404
            
        # 获取天气评分
        weather_score = 60 # 默认
        weather_info = {}
        try:
            weather_data = weather_service.get_current_weather()
            if weather_data:
                weather_info = weather_data
                if 'stargazing_score' in weather_data:
                    weather_score = weather_data['stargazing_score']
        except Exception as e:
            print(f"Error getting weather score: {e}")

        # 注入光污染数据和天气评分
        try:
            if 'all_points' in result:
                for point in result['all_points']:
                    lp_data = light_pollution_service.get_pollution_data(
                        point['name'], 
                        point['latitude'], 
                        point['longitude']
                    )
                    point.update(lp_data)
                    # 注入天气评分到 score_details
                    if 'score_details' in point:
                        point['score_details']['weather'] = weather_score
            
            if 'best_point' in result:
                lp_data = light_pollution_service.get_pollution_data(
                    result['best_point']['name'], 
                    result['best_point']['latitude'], 
                    result['best_point']['longitude']
                )
                result['best_point'].update(lp_data)
                # 注入天气评分到 score_details
                if 'score_details' in result['best_point']:
                    result['best_point']['score_details']['weather'] = weather_score
        except Exception as e:
            print(f"Error injecting LP/Weather data: {e}")
        
        # 添加天气信息到结果中
        result['weather_info'] = weather_info
        
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
        
        # 为每个点添加光污染数据
        for point in points:
            try:
                lp_data = light_pollution_service.get_pollution_data(
                    point['name'], 
                    point['latitude'], 
                    point['longitude']
                )
                point.update(lp_data)
            except Exception as e:
                print(f"Error calculating light pollution for {point.get('name')}: {e}")
                point.update({'bortle': 4, 'sqm': 20.45})
            
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
            
        # 添加光污染数据
        if 'point' in result:
            point = result['point']
            try:
                lp_data = light_pollution_service.get_pollution_data(
                    point['name'], 
                    point['latitude'], 
                    point['longitude']
                )
                point.update(lp_data)
            except Exception as e:
                print(f"Error calculating light pollution for {point.get('name')}: {e}")
                # Fallback defaults
                point.update({'bortle': 4, 'sqm': 20.45})
            
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


@app.route('/api/wild-spots')
def get_wild_spots():
    """获取野外推荐观测点"""
    try:
        azimuth = request.args.get('azimuth', type=float)
        altitude = request.args.get('altitude', type=float)
        
        spots = terrain_service.get_wild_spots(target_azimuth=azimuth, target_altitude=altitude)
        return jsonify(spots), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/weather')
def get_weather():
    """获取当前天气和观星条件"""
    try:
        weather = weather_service.get_current_weather()
        if weather:
            # 获取未来12小时预报
            forecast = weather_service.get_hourly_forecast()
            weather['forecast'] = forecast
            return jsonify(weather), 200
        else:
            return jsonify({'error': '无法获取天气数据'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
