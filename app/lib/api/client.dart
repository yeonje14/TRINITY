import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'models.dart';

/// 서버 주소: `flutter run --dart-define=TRINITY_API=http://192.168.0.10:8000`
/// (안드로이드 에뮬레이터에서 맥 로컬 서버는 http://10.0.2.2:8000)
const apiBase = String.fromEnvironment('TRINITY_API', defaultValue: 'http://localhost:8000');

class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  @override
  String toString() => message;
}

class TrinityApi {
  TrinityApi({String base = apiBase, http.Client? client})
      : _base = Uri.parse(base),
        _http = client ?? http.Client();

  final Uri _base;
  final http.Client _http;
  static const _timeout = Duration(seconds: 60);

  Uri _u(String path, [Map<String, String>? q]) => _base.replace(path: path, queryParameters: q);

  Future<dynamic> _send(Future<http.Response> req) async {
    final http.Response res;
    try {
      res = await req.timeout(_timeout);
    } catch (_) {
      throw ApiException('서버에 연결할 수 없습니다 ($apiBase)');
    }
    final body = res.bodyBytes.isEmpty ? null : jsonDecode(utf8.decode(res.bodyBytes));
    if (res.statusCode >= 400) throw ApiException(_detail(body) ?? '요청 실패 (${res.statusCode})');
    return body;
  }

  static String? _detail(dynamic body) {
    final d = body is Map ? body['detail'] : null;
    if (d is String) return d;
    if (d is List && d.isNotEmpty && d.first is Map) {
      return (d.first['msg'] as String?)?.replaceFirst('Value error, ', '');
    }
    return null;
  }

  Future<String> analyzeUrl(String url) async {
    final j = await _send(_http.post(_u('/analyze/url'),
        headers: {'content-type': 'application/json'}, body: jsonEncode({'url': url})));
    return j['job_id'];
  }

  Future<AnalysisResult> analyzeImage(Uint8List bytes, String filename) async {
    final req = http.MultipartRequest('POST', _u('/analyze/image'))
      ..files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
    return AnalysisResult.fromJson(await _send(_http.send(req).then(http.Response.fromStream)));
  }

  Future<Job> job(String id) async => Job.fromJson(await _send(_http.get(_u('/jobs/$id'))));

  Future<AnalysisResult> analysis(String id) async =>
      AnalysisResult.fromJson(await _send(_http.get(_u('/analyses/$id'))));

  Future<List<HistoryItem>> history({int limit = 30}) async {
    final list = await _send(_http.get(_u('/history', {'limit': '$limit'}))) as List;
    return [for (final h in list) HistoryItem.fromJson(h)];
  }

  Future<ChannelSummary> channel(String id) async =>
      ChannelSummary.fromJson(await _send(_http.get(_u('/channels/$id'))));
}

final api = TrinityApi();
