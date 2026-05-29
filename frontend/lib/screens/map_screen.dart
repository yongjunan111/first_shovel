import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_cancellable_tile_provider/flutter_map_cancellable_tile_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';
import '../controllers/play_controller.dart';
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
  void initState() {
    super.initState();
    Future.microtask(() {
      ref.read(playControllerProvider.notifier).bootstrap();
    });
  }

  @override
  Widget build(BuildContext context) {
    final locationAsync = ref.watch(locationProvider);
    final playState = ref.watch(playControllerProvider);
    final currentPosition = locationAsync.valueOrNull;
    final currentPoint = currentPosition == null
        ? null
        : LatLng(currentPosition.latitude, currentPosition.longitude);

    ref.listen(locationProvider, (_, next) {
      final position = next.valueOrNull;
      if (position == null) {
        return;
      }
      ref
          .read(playControllerProvider.notifier)
          .addActualPoint(LatLng(position.latitude, position.longitude));
    });

    return Scaffold(
      appBar: AppBar(
        title: const Text('Earth Canvas'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: _seoulCenter,
              initialZoom: _initialZoom,
              minZoom: _minZoom,
              maxZoom: _maxZoom,
              cameraConstraint: CameraConstraint.containCenter(
                bounds: LatLngBounds(_seoulSW, _seoulNE),
              ),
            ),
            children: [
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
              if (playState.targetPath.isNotEmpty)
                PolylineLayer(
                  polylines: [
                    Polyline(
                      points: playState.targetPath,
                      strokeWidth: 5,
                      color: const Color(0xFF2E7D32),
                    ),
                  ],
                ),
              if (playState.actualPath.isNotEmpty)
                PolylineLayer(
                  polylines: [
                    Polyline(
                      points: playState.actualPath,
                      strokeWidth: 4,
                      color: const Color(0xFF1565C0),
                    ),
                  ],
                ),
              if (currentPoint != null)
                MarkerLayer(
                  markers: [
                    Marker(
                      point: currentPoint,
                      width: 22,
                      height: 22,
                      child: Container(
                        decoration: BoxDecoration(
                          color: const Color(0xFF1565C0),
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 3),
                          boxShadow: const [
                            BoxShadow(blurRadius: 4, color: Colors.black26),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              PolygonLayer(
                polygons: [
                  Polygon(
                    points: [
                      _seoulSW,
                      LatLng(_seoulSW.latitude, _seoulNE.longitude),
                      _seoulNE,
                      LatLng(_seoulNE.latitude, _seoulSW.longitude),
                    ],
                    borderColor: Colors.green.withValues(alpha: 0.25),
                    borderStrokeWidth: 1.5,
                    color: Colors.transparent,
                  ),
                ],
              ),
            ],
          ),
          _PlayPanel(
            state: playState,
            onPrepare: () => ref
                .read(playControllerProvider.notifier)
                .bootstrap(target: currentPoint ?? seoulCenter),
            onRefresh: () => ref
                .read(playControllerProvider.notifier)
                .refreshPreview(target: currentPoint ?? seoulCenter),
            onStart: () => ref
                .read(playControllerProvider.notifier)
                .start(target: currentPoint ?? seoulCenter),
            onFinish: () =>
                ref.read(playControllerProvider.notifier).finishAndScore(),
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

class _PlayPanel extends StatelessWidget {
  const _PlayPanel({
    required this.state,
    required this.onPrepare,
    required this.onRefresh,
    required this.onStart,
    required this.onFinish,
  });

  final PlayState state;
  final VoidCallback onPrepare;
  final VoidCallback onRefresh;
  final VoidCallback onStart;
  final VoidCallback onFinish;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final title = state.selectedBlueprint?.title ?? 'No route';
    final status = state.isRiding
        ? 'Riding'
        : state.score == null
            ? 'Ready'
            : 'Score ${state.score!.score.toStringAsFixed(1)}';

    return Align(
      alignment: Alignment.bottomCenter,
      child: SafeArea(
        minimum: const EdgeInsets.fromLTRB(12, 0, 12, 12),
        child: Material(
          color: theme.colorScheme.surface,
          elevation: 8,
          borderRadius: BorderRadius.circular(8),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (state.isLoading) const LinearProgressIndicator(),
                  if (state.isLoading) const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              title,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: theme.textTheme.titleMedium,
                            ),
                            const SizedBox(height: 2),
                            Text(
                              '$status · target ${state.targetPath.length} · actual ${state.actualPath.length}',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: theme.textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        tooltip: 'Refresh',
                        onPressed: state.isLoading ? null : onRefresh,
                        icon: const Icon(Icons.refresh),
                      ),
                    ],
                  ),
                  if (state.score != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      'Avg ${state.score!.avgDeviationM.toStringAsFixed(1)} m · completion ${(state.score!.completionRate * 100).toStringAsFixed(0)}%',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodyMedium,
                    ),
                  ],
                  if (state.error != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      state.error!,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.error,
                      ),
                    ),
                  ],
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: state.isLoading ? null : onPrepare,
                          icon: const Icon(Icons.route),
                          label: const Text('Prepare'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: state.isLoading
                              ? null
                              : state.isRiding
                                  ? onFinish
                                  : onStart,
                          icon: Icon(
                            state.isRiding ? Icons.flag : Icons.play_arrow,
                          ),
                          label: Text(state.isRiding ? 'Finish' : 'Start'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
