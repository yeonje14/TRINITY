import 'package:flutter/material.dart';

import '../api/models.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'channel.dart';
import 'explanation.dart';

/// 결과 요약 — 탭하면 결과 해설로.
class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.result});
  final AnalysisResult result;

  @override
  Widget build(BuildContext context) {
    final r = result;
    final color = riskColor(r.risk);
    void explain() =>
        Navigator.of(context).push(MaterialPageRoute(builder: (_) => ExplanationScreen(result: r)));

    return Scaffold(
      appBar: AppBar(title: const Text('RESULT')),
      body: ListView(padding: T.pad, children: [
        const SizedBox(height: 16),
        Semantics(
          button: true,
          label: '위험도 ${r.risk.label}, 점수 ${pct(r.score)}. 탭하면 결과 해설',
          excludeSemantics: true,
          child: InkWell(
            onTap: explain,
            child: Container(
              color: color,
              padding: const EdgeInsets.all(24),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Text('위험도 ${r.risk.label}', style: T.mono(color: T.bg, size: 14, weight: FontWeight.w800)),
                  const Spacer(),
                  const Icon(Icons.arrow_forward, color: T.bg),
                ]),
                const SizedBox(height: 24),
                Text(r.risk.headline, style: T.display(48, color: T.bg)),
                const SizedBox(height: 24),
                Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Text(pct(r.score), style: T.display(72, color: T.bg)),
                  const SizedBox(width: 8),
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Text('/ 100', style: T.mono(color: T.bg, size: 14, weight: FontWeight.w700)),
                  ),
                ]),
              ]),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Row(children: [
          TrafficLight(r.risk),
          const Spacer(),
          Text('신뢰도 ${pct(r.confidence)}', style: T.mono(color: T.text, size: 13)),
        ]),
        const SizedBox(height: 32),
        const Label('축별 근거'),
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: [for (final a in r.axes) AxisChip(a)]),
        const SizedBox(height: 32),
        const Label('대상'),
        const SizedBox(height: 8),
        Text(r.source.display, style: T.title(20)),
        if (r.source.channelId != null) ...[
          const SizedBox(height: 12),
          OutlinedButton(
            onPressed: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => ChannelScreen(channelId: r.source.channelId!))),
            child: Text('채널 이력 · ${r.source.channel ?? r.source.channelId}'),
          ),
        ],
        const SizedBox(height: 32),
        FilledButton(onPressed: explain, child: const Text('결과 해설 보기')),
        const SizedBox(height: 24),
        Text(r.disclaimer, style: T.body(color: T.muted, size: 13)),
        const SizedBox(height: 40),
      ]),
    );
  }
}
