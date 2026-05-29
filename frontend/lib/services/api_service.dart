import 'package:dio/dio.dart';
import 'package:latlong2/latlong.dart';

import '../models/play_models.dart';

const _defaultBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000',
);

class ApiService {
  ApiService()
      : _dio = Dio(BaseOptions(
          baseUrl: _defaultBaseUrl,
          connectTimeout: const Duration(seconds: 5),
          receiveTimeout: const Duration(seconds: 10),
          headers: {'Content-Type': 'application/json'},
        ));

  final Dio _dio;
  String? _token;

  Future<void> devLogin() async {
    if (_token != null) {
      return;
    }
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/auth/dev-login',
      data: {
        'email': 'demo@earthcanvas.local',
        'nickname': 'Demo Rider',
      },
    );
    _token = response.data?['access_token'] as String?;
    _dio.options.headers['Authorization'] = 'Bearer $_token';
  }

  Future<List<BlueprintSummary>> fetchBlueprints() async {
    final response = await _dio.get<Map<String, dynamic>>('/api/blueprints');
    final items = response.data?['items'] as List<dynamic>? ?? const [];
    return items
        .map((item) => BlueprintSummary.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<BlueprintSummary> createDemoBlueprint() async {
    await devLogin();
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/blueprints',
      data: {
        'title': 'Seoul demo loop',
        'description': 'Demo route for the Play flow',
        'tags': ['demo', 'seoul'],
        'difficulty': 1,
        'estimated_time': 15,
        'distance': 1.2,
        'coordinates': const [
          [37.5665, 126.9780],
          [37.5680, 126.9810],
          [37.5700, 126.9800],
          [37.5690, 126.9760],
          [37.5665, 126.9780],
        ],
      },
    );
    return BlueprintSummary.fromJson(response.data!);
  }

  Future<List<LatLng>> preview({
    required int blueprintId,
    required LatLng target,
    double rotationAngle = 0,
    double scale = 1,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/stencil/transform',
      data: {
        'blueprint_id': blueprintId,
        'target_lat': target.latitude,
        'target_lng': target.longitude,
        'rotation_angle': rotationAngle,
        'scale': scale,
      },
    );
    return coordinatesFromJson(response.data?['transformed_coordinates']);
  }

  Future<RideSession> startRide({
    required int blueprintId,
    required LatLng target,
    double rotationAngle = 0,
    double scale = 1,
  }) async {
    await devLogin();
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/rides',
      data: {
        'blueprint_id': blueprintId,
        'started_at': DateTime.now().toUtc().toIso8601String(),
        'target_lat': target.latitude,
        'target_lng': target.longitude,
        'rotation_angle': rotationAngle,
        'scale': scale,
      },
    );
    return RideSession.fromJson(response.data!);
  }

  Future<void> finishRide({
    required RideSession ride,
    required List<LatLng> actualPath,
  }) async {
    final distanceM = _pathDistanceM(actualPath);
    final duration = DateTime.now().difference(ride.startedAt).inSeconds;
    await _dio.put<Map<String, dynamic>>(
      '/api/rides/${ride.id}/finish',
      data: {
        'actual_coordinates': coordinatesToJson(actualPath),
        'finished_at': DateTime.now().toUtc().toIso8601String(),
        'distance': distanceM / 1000,
        'duration': duration < 1 ? 1 : duration,
      },
    );
  }

  Future<ScoreResult> createScore(int rideId) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/scores',
      data: {'ride_id': rideId},
    );
    return ScoreResult.fromJson(response.data!);
  }

  double _pathDistanceM(List<LatLng> points) {
    if (points.length < 2) {
      return 0;
    }
    const distance = Distance();
    var total = 0.0;
    for (var i = 1; i < points.length; i++) {
      total += distance.as(LengthUnit.Meter, points[i - 1], points[i]);
    }
    return total;
  }
}
