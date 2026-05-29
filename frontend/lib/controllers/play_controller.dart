import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../models/play_models.dart';
import '../services/api_service.dart';

const seoulCenter = LatLng(37.5665, 126.9780);
const _unset = Object();

final apiServiceProvider = Provider<ApiService>((ref) => ApiService());

final playControllerProvider =
    StateNotifierProvider<PlayController, PlayState>((ref) {
  return PlayController(ref.watch(apiServiceProvider));
});

class PlayState {
  const PlayState({
    this.isLoading = false,
    this.error,
    this.blueprints = const [],
    this.selectedBlueprint,
    this.targetPath = const [],
    this.actualPath = const [],
    this.activeRide,
    this.score,
  });

  final bool isLoading;
  final String? error;
  final List<BlueprintSummary> blueprints;
  final BlueprintSummary? selectedBlueprint;
  final List<LatLng> targetPath;
  final List<LatLng> actualPath;
  final RideSession? activeRide;
  final ScoreResult? score;

  bool get isRiding => activeRide != null;

  PlayState copyWith({
    bool? isLoading,
    String? error,
    bool clearError = false,
    List<BlueprintSummary>? blueprints,
    Object? selectedBlueprint = _unset,
    List<LatLng>? targetPath,
    List<LatLng>? actualPath,
    Object? activeRide = _unset,
    Object? score = _unset,
  }) {
    return PlayState(
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : error ?? this.error,
      blueprints: blueprints ?? this.blueprints,
      selectedBlueprint: selectedBlueprint == _unset
          ? this.selectedBlueprint
          : selectedBlueprint as BlueprintSummary?,
      targetPath: targetPath ?? this.targetPath,
      actualPath: actualPath ?? this.actualPath,
      activeRide:
          activeRide == _unset ? this.activeRide : activeRide as RideSession?,
      score: score == _unset ? this.score : score as ScoreResult?,
    );
  }
}

class PlayController extends StateNotifier<PlayState> {
  PlayController(this._api) : super(const PlayState());

  final ApiService _api;

  Future<void> bootstrap({LatLng target = seoulCenter}) async {
    await _run(() async {
      var blueprints = await _api.fetchBlueprints();
      if (blueprints.isEmpty) {
        final demo = await _api.createDemoBlueprint();
        blueprints = [demo];
      }
      final selected = blueprints.first;
      final preview = await _api.preview(
        blueprintId: selected.id,
        target: target,
      );
      state = state.copyWith(
        blueprints: blueprints,
        selectedBlueprint: selected,
        targetPath: preview,
        actualPath: const [],
        activeRide: null,
        score: null,
      );
    });
  }

  Future<void> refreshPreview({LatLng target = seoulCenter}) async {
    final selected = state.selectedBlueprint;
    if (selected == null) {
      return;
    }
    await _run(() async {
      final preview = await _api.preview(
        blueprintId: selected.id,
        target: target,
      );
      state = state.copyWith(targetPath: preview, score: null);
    });
  }

  Future<void> start({LatLng target = seoulCenter}) async {
    final selected = state.selectedBlueprint;
    if (selected == null) {
      return;
    }
    await _run(() async {
      final ride = await _api.startRide(
        blueprintId: selected.id,
        target: target,
      );
      state = state.copyWith(
        activeRide: ride,
        targetPath: ride.targetCoordinates,
        actualPath: const [],
        score: null,
      );
    });
  }

  void addActualPoint(LatLng point) {
    if (!state.isRiding) {
      return;
    }
    final path = state.actualPath;
    if (path.isNotEmpty) {
      final last = path.last;
      final distance = const Distance().as(LengthUnit.Meter, last, point);
      if (distance < 3) {
        return;
      }
    }
    state = state.copyWith(actualPath: [...path, point]);
  }

  Future<void> finishAndScore() async {
    final ride = state.activeRide;
    if (ride == null) {
      return;
    }
    await _run(() async {
      final actualPath = state.actualPath.length >= 2
          ? state.actualPath
          : ride.targetCoordinates;
      await _api.finishRide(ride: ride, actualPath: actualPath);
      final score = await _api.createScore(ride.id);
      state = state.copyWith(
        actualPath: actualPath,
        activeRide: null,
        score: score,
      );
    });
  }

  Future<void> _run(Future<void> Function() action) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await action();
      state = state.copyWith(isLoading: false);
    } catch (error) {
      state = state.copyWith(isLoading: false, error: _friendlyError(error));
    }
  }

  String _friendlyError(Object error) {
    final message = error.toString();
    if (message.contains('/api/auth/dev-login')) {
      return 'Dev login is disabled. Set ALLOW_DEV_LOGIN=true for local demos.';
    }
    return message;
  }
}
