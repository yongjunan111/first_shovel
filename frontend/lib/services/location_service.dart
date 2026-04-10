import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

/// Requests permission and streams the current GPS position.
/// Emits the latest [Position] and re-emits on each location update.
final locationProvider = StreamProvider<Position>((ref) async* {
  LocationPermission permission = await Geolocator.checkPermission();
  if (permission == LocationPermission.denied) {
    permission = await Geolocator.requestPermission();
  }
  if (permission == LocationPermission.deniedForever) {
    throw Exception('Location permission permanently denied');
  }

  const settings = LocationSettings(
    accuracy: LocationAccuracy.high,
    distanceFilter: 5, // emit every 5 m of movement
  );

  yield await Geolocator.getCurrentPosition(desiredAccuracy: LocationAccuracy.high);
  yield* Geolocator.getPositionStream(locationSettings: settings);
});
