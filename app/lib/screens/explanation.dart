import 'package:flutter/material.dart';

import '../api/models.dart';
import '../theme.dart';
import '../widgets/common.dart';

/// 결과 해설 — 축별 상세 근거.
class ExplanationScreen extends StatelessWidget {
  const ExplanationScreen({super.key, required this.result});
  final AnalysisResult result;

  // 서버가 근거 문장을 따로 주지 않는 플래그만 여기서 풀어 쓴다
  static const _flagLabels = {
    'low_quality': '저화질 입력 — 신호 축 하향, 의미 축 상향',
    'provenance_cross_checked': '출처 신호를 타 축이 교차 확인함',
  };

  @override
  Widget build(BuildContext context) {
    final r = result;
    return Scaffold(
      appBar: AppBar(title: const Text('EXPLANATION')),
      body: ListView(padding: T.pad, children: [
        const SizedBox(height: 16),
        Row(children: [
          RiskBadge(r.risk),
          const SizedBox(width: 12),
          Text('점수 ${pct(r.score)} · 신뢰도 ${pct(r.confidence)}', style: T.mono(color: T.text, size: 13)),
        ]),
        const SizedBox(height: 16),
        Text('왜 이렇게\n판단했나', style: T.display(44)),
        if (r.evidence.isNotEmpty || r.flags.any(_flagLabels.containsKey)) ...[
          const SizedBox(height: 32),
          const Label('종합', color: T.accent),
          const SizedBox(height: 8),
          for (final e in r.evidence) EvidenceRow(e),
          for (final f in r.flags.where(_flagLabels.containsKey))
            EvidenceRow(Evidence.fromJson({'code': f, 'message': _flagLabels[f], 'supports_ai': null})),
        ],
        for (final a in r.axes) _AxisSection(a),
        const SizedBox(height: 32),
        const Rule(),
        const SizedBox(height: 16),
        Text('+ AI 생성 쪽 근거   − 실촬영 쪽 근거   · 중립·주의', style: T.mono()),
        const SizedBox(height: 12),
        Text(r.disclaimer, style: T.body(color: T.muted, size: 13)),
        const SizedBox(height: 40),
      ]),
    );
  }
}

class _AxisSection extends StatelessWidget {
  const _AxisSection(this.a);
  final AxisReport a;

  static const _desc = {
    'signal': '생성 모델의 업샘플링이 주파수 도메인에 남기는 주기적 격자 흔적',
    'provenance': 'C2PA 매니페스트와 워터마크의 교차 감사 — 음성은 진본 증명이 아님',
    'semantic': '특징 분포 편차와 시공간 일관성',
  };

  @override
  Widget build(BuildContext context) {
    final color = !a.usable ? T.muted : a.score! >= 0.7 ? T.high : a.score! >= 0.4 ? T.caution : T.low;
    return Padding(
      padding: const EdgeInsets.only(top: 40),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Rule(color: T.text, thickness: 2),
        const SizedBox(height: 12),
        Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text(axisLabel(a.axis), style: T.display(32)),
          const Spacer(),
          Text(a.usable ? pct(a.score) : axisStatusLabel(a.status),
              style: T.mono(color: color, size: 20, weight: FontWeight.w800)),
        ]),
        const SizedBox(height: 6),
        Text(_desc[a.axis] ?? '', style: T.body(color: T.muted, size: 14)),
        const SizedBox(height: 12),
        if (a.usable) ...[
          ScoreBar(a.score!, color: color),
          const SizedBox(height: 8),
          Text('가중 ${pct(a.weight)}% · 신뢰도 ${pct(a.confidence)}', style: T.mono()),
        ],
        if (a.gateReason != null) ...[
          const SizedBox(height: 8),
          Text('게이트 · ${a.gateReason}', style: T.mono(color: T.caution)),
        ],
        const SizedBox(height: 8),
        for (final e in a.evidence) EvidenceRow(e),
      ]),
    );
  }
}
