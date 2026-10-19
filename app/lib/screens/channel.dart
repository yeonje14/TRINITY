import 'package:flutter/material.dart';

import '../api/client.dart';
import '../api/models.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'result.dart';

/// 채널 상세 — 채널 ID 단위 누적 이력.
class ChannelScreen extends StatefulWidget {
  const ChannelScreen({super.key, required this.channelId});
  final String channelId;
  @override
  State<ChannelScreen> createState() => _ChannelScreenState();
}

class _ChannelScreenState extends State<ChannelScreen> {
  late final Future<ChannelSummary> _summary = api.channel(widget.channelId);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('CHANNEL')),
      body: FutureBuilder<ChannelSummary>(
        future: _summary,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Padding(padding: T.pad, child: Text('${snap.error}', style: T.body(color: T.muted)));
          }
          final s = snap.data!;
          final ratio = s.analyzed == 0 ? 0.0 : s.highRisk / s.analyzed;
          return ListView(padding: T.pad, children: [
            const SizedBox(height: 16),
            const Label('채널'),
            const SizedBox(height: 8),
            Text(s.channel ?? s.channelId, style: T.display(40)),
            const SizedBox(height: 32),
            Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Text('${s.highRisk}', style: T.display(80, color: s.highRisk > 0 ? T.high : T.text)),
              Padding(
                padding: const EdgeInsets.only(bottom: 12, left: 8),
                child: Text('/ ${s.analyzed}', style: T.title(28, color: T.muted)),
              ),
            ]),
            Text('분석된 ${s.analyzed}개 영상 중 ${s.highRisk}개가 AI 생성 의심', style: T.title(18)),
            const SizedBox(height: 12),
            ScoreBar(ratio, color: T.high),
            const SizedBox(height: 8),
            Text('주의 ${s.caution}개 포함', style: T.mono()),
            const SizedBox(height: 40),
            const Label('최근 분석'),
            const SizedBox(height: 8),
            const Rule(color: T.text, thickness: 2),
            for (final h in s.recent) ...[
              HistoryTile(h, onTap: () async {
                try {
                  final r = await api.analysis(h.id);
                  if (context.mounted) {
                    Navigator.of(context).push(MaterialPageRoute(builder: (_) => ResultScreen(result: r)));
                  }
                } catch (e) {
                  if (context.mounted) showError(context, e);
                }
              }),
              const Rule(),
            ],
            const SizedBox(height: 40),
          ]);
        },
      ),
    );
  }
}
