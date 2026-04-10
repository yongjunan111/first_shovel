import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_cancellable_tile_provider/flutter_map_cancellable_tile_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';
import '../services/location_service.dart';

/// Seoul bounding box
const _seoulSW = LatLng(37.413, 126.734);
const _seoulNE = LatLng(37.701, 127.269);
const _seoulCenter = LatLng(37.5665, 126.9780);
const _minZoom = 10.0;
const _maxZoom = 18.0;
const _initialZoom = 13.0;

class MapScreen extends ConsumerStatefulWidget {
  const MapScreen({super.key});

  @override
  ConsumerState<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends ConsumerState<MapScreen> {
  final MapController _mapController = MapController();

  @override
  Widget build(BuildContext context) {
    final locationAsync = ref.watch(locationProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Earth Canvas'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      body: FlutterMap(
        mapController: _mapController,
        options: MapOptions(
          initialCenter: _seoulCenter,
          initialZoom: _initialZoom,
          minZoom: _minZoom,
          maxZoom: _maxZoom,
          // Lock camera to Seoul bounds
          cameraConstraint: CameraConstraint.containCenter(
            bounds: LatLngBounds(_seoulSW, _seoulNE),
          ),
        ),
        children: [
          // CyclOSM tile layer — cyclist-optimised OSM tiles
          TileLayer(
            urlTemplate:
                'https://tile.waymarkedtrails.org/cycling/{z}/{x}/{y}.png',
            fallbackUrl:
                'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            subdomains: const ['a', 'b', 'c'],
            userAgentPackageName: 'com.earthcanvas.app',
            tileProvider: CancellableNetworkTileProvider(),
            maxZoom: _maxZoom,
          ),
          // Current location marker
          locationAsync.when(
            data: (pos) => MarkerLayer(
              markers: [
                Marker(
                  point: LatLng(pos.latitude, pos.longitude),
                  width: 20,
                  height: 20,
                  child: Container(
                    decoration: BoxDecoration(
                      color: const Color(0xFF1565C0),
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 2),
                      boxShadow: const [
                        BoxShadow(blurRadius: 4, color: Colors.black26),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            loading: () => const MarkerLayer(markers: []),
            error: (_, __) => const MarkerLayer(markers: []),
          ),
          // Seoul bounds visualiser (debug — remove in prod)
          PolygonLayer(
            polygons: [
              Polygon(
                points: [
                  _seoulSW,
                  LatLng(_seoulSW.latitude, _seoulNE.longitude),
                  _seoulNE,
                  LatLng(_seoulNE.latitude, _seoulSW.longitude),
                ],
                borderColor: Colors.green.withValues(alpha: 0.4),
                borderStrokeWidth: 1.5,
                color: Colors.transparent,
              ),
            ],
          ),
        ],
      ),
      floatingActionButton: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          FloatingActionButton.small(
            heroTag: 'locate',
            onPressed: _moveToCurrentLocation,
            child: const Icon(Icons.my_location),
          ),
        ],
      ),
    );
  }

  void _moveToCurrentLocation() {
    final pos = ref.read(locationProvider).valueOrNull;
    if (pos != null) {
      _mapController.move(LatLng(pos.latitude, pos.longitude), 15.0);
    }
  }
}
