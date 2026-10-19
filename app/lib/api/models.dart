/// 서버 `interfaces/api/schemas.py`와 1:1 대응하는 모델.
library;

enum RiskLevel { low, caution, high }

RiskLevel _risk(String s) => RiskLevel.values.byName(s);

extension RiskLevelLabel on RiskLevel {
  String get label => switch (this) { RiskLevel.low => '낮음', RiskLevel.caution => '주의', RiskLevel.high => '높음' };
  String get headline => switch (this) {
        RiskLevel.low => 'AI 생성 흔적이\n적습니다',
        RiskLevel.caution => '주의가\n필요합니다',
        RiskLevel.high => 'AI 생성\n의심',
      };
}

String axisLabel(String axis) =>
    const {'signal': '신호', 'provenance': '출처', 'semantic': '의미·물리'}[axis] ?? axis;

String axisStatusLabel(String status) => const {
      'ok': '분석됨',
      'no_evidence': '신호 없음',
      'not_applicable': '적용 불가',
      'unavailable': '미연결',
      'error': '오류',
    }[status] ??
    status;

DateTime _date(String s) => DateTime.parse(s).toLocal();
double? _num(dynamic v) => (v as num?)?.toDouble();

class Evidence {
  final String code, message;
  final bool? supportsAi;
  Evidence.fromJson(Map<String, dynamic> j)
      : code = j['code'],
        message = j['message'],
        supportsAi = j['supports_ai'];
}

class AxisReport {
  final String axis, status;
  final double? score;
  final double confidence, weight;
  final String? gateReason;
  final List<Evidence> evidence;
  AxisReport.fromJson(Map<String, dynamic> j)
      : axis = j['axis'],
        status = j['status'],
        score = _num(j['score']),
        confidence = _num(j['confidence']) ?? 0,
        weight = _num(j['weight']) ?? 0,
        gateReason = j['gate_reason'],
        evidence = [for (final e in j['evidence'] as List) Evidence.fromJson(e)];

  bool get usable => status == 'ok' && score != null;
}

class SourceInfo {
  final String? url, channelId, channel, title, filename;
  SourceInfo.fromJson(Map<String, dynamic> j)
      : url = j['url'],
        channelId = j['channel_id'],
        channel = j['channel'],
        title = j['title'],
        filename = j['filename'];

  String get display => title ?? filename ?? url ?? '업로드한 이미지';
}

class AnalysisResult {
  final String id, track, disclaimer;
  final RiskLevel risk;
  final double? score;
  final double confidence;
  final List<AxisReport> axes;
  final List<String> flags, gates;
  final List<Evidence> evidence;
  final SourceInfo source;
  final DateTime createdAt;

  AnalysisResult.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        track = j['track'],
        disclaimer = j['disclaimer'] ?? '',
        risk = _risk(j['risk_level']),
        score = _num(j['score']),
        confidence = _num(j['confidence']) ?? 0,
        axes = [for (final a in j['axes'] as List) AxisReport.fromJson(a)],
        flags = List<String>.from(j['flags'] ?? const []),
        gates = List<String>.from(j['gates'] ?? const []),
        evidence = [for (final e in (j['evidence'] ?? const []) as List) Evidence.fromJson(e)],
        source = SourceInfo.fromJson(j['source'] ?? const {}),
        createdAt = _date(j['created_at']);
}

enum JobState { queued, running, done, failed }

class Job {
  final String id;
  final JobState state;
  final double progress;
  final String? stage, error;
  final AnalysisResult? result;
  Job.fromJson(Map<String, dynamic> j)
      : id = j['job_id'],
        state = JobState.values.byName(j['state']),
        progress = _num(j['progress']) ?? 0,
        stage = j['stage'],
        error = j['error'],
        result = j['result'] == null ? null : AnalysisResult.fromJson(j['result']);

  String get stageLabel => const {
        'starting': '준비 중',
        'downloading': '영상 내려받는 중',
        'preprocessing': '프레임 샘플링 중',
        'analyzing': '3축 분석 중',
        'fusing': '근거 종합 중',
        'done': '완료',
        'failed': '실패',
      }[stage] ??
      '대기 중';
}

class HistoryItem {
  final String id, track;
  final RiskLevel risk;
  final double? score;
  final String? title, channelId;
  final DateTime createdAt;
  HistoryItem.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        track = j['track'],
        risk = _risk(j['risk_level']),
        score = _num(j['score']),
        title = j['title'],
        channelId = j['channel_id'],
        createdAt = _date(j['created_at']);
}

class ChannelSummary {
  final String channelId;
  final String? channel;
  final int analyzed, highRisk, caution;
  final List<HistoryItem> recent;
  ChannelSummary.fromJson(Map<String, dynamic> j)
      : channelId = j['channel_id'],
        channel = j['channel'],
        analyzed = j['analyzed'],
        highRisk = j['high_risk'],
        caution = j['caution'],
        recent = [for (final h in j['recent'] as List) HistoryItem.fromJson(h)];
}
