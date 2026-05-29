import 'package:latlong2/latlong.dart';

List<LatLng> coordinatesFromJson(Object? value) {
  final raw = value as List<dynamic>? ?? const [];
  return raw.map((point) {
    final pair = point as List<dynamic>;
    return LatLng((pair[0] as num).toDouble(), (pair[1] as num).toDouble());
  }).toList();
}

List<List<double>> coordinatesToJson(List<LatLng> points) {
  return points.map((point) => [point.latitude, point.longitude]).toList();
}

class BlueprintSummary {
  const BlueprintSummary({
    required this.id,
    required this.title,
    required this.coordinates,
  });

  final int id;
  final String title;
  final List<LatLng> coordinates;

  factory BlueprintSummary.fromJson(Map<String, dynamic> json) {
    return BlueprintSummary(
      id: json['id'] as int,
      title: json['title'] as String,
      coordinates: coordinatesFromJson(json['coordinates']),
    );
  }
}

class RideSession {
  const RideSession({
    required this.id,
    required this.blueprintId,
    required this.targetCoordinates,
    required this.startedAt,
  });

  final int id;
  final int blueprintId;
  final List<LatLng> targetCoordinates;
  final DateTime startedAt;

  factory RideSession.fromJson(Map<String, dynamic> json) {
    return RideSession(
      id: json['id'] as int,
      blueprintId: json['blueprint_id'] as int,
      targetCoordinates: coordinatesFromJson(json['target_coordinates']),
      startedAt: DateTime.parse(json['started_at'] as String),
    );
  }
}

class ScoreResult {
  const ScoreResult({
    required this.score,
    required this.avgDeviationM,
    required this.completionRate,
  });

  final double score;
  final double avgDeviationM;
  final double completionRate;

  factory ScoreResult.fromJson(Map<String, dynamic> json) {
    final details = json['details'] as Map<String, dynamic>;
    return ScoreResult(
      score: (json['score'] as num).toDouble(),
      avgDeviationM: (details['avg_deviation_m'] as num).toDouble(),
      completionRate: (details['completion_rate'] as num).toDouble(),
    );
  }
}
