import 'package:flutter/material.dart';

import '../api/models.dart';
import '../theme.dart';

Color riskColor(RiskLevel r) => switch (r) { RiskLevel.low => T.low, RiskLevel.caution => T.caution, RiskLevel.high => T.high };

String pct(double? v) => v == null ? '—' : '${(v * 100).round()}';

/// 대문자 모노 라벨 — 섹션 구분용.
class Label extends StatelessWidget {
  const Label(this.text, {super.key, this.color = T.muted});
  final String text;
  final Color color;
  @override
  Widget build(BuildContext context) =>
      Text(text.toUpperCase(), style: T.mono(color: color, weight: FontWeight.w700));
}

class Rule extends StatelessWidget {
  const Rule({super.key, this.color = T.line, this.thickness = 1});
  final Color color;
  final double thickness;
  @override
  Widget build(BuildContext context) => Container(height: thickness, color: color);
}

/// 신호등 3칸 — 현재 위험도만 점등.
class TrafficLight extends StatelessWidget {
  const TrafficLight(this.risk, {super.key, this.size = 18});
  final RiskLevel risk;
  final double size;
  @override
  Widget build(BuildContext context) => Semantics(
        label: '위험도 ${risk.label}',
        excludeSemantics: true,
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          for (final r in RiskLevel.values)
            Container(
              width: size,
              height: size,
              margin: const EdgeInsets.only(right: 6),
              color: r == risk ? riskColor(r) : T.line,
            ),
        ]),
      );
}

class RiskBadge extends StatelessWidget {
  const RiskBadge(this.risk, {super.key});
  final RiskLevel risk;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        color: riskColor(risk),
        child: Text(risk.label, style: T.mono(color: T.bg, weight: FontWeight.w800)),
      );
}

/// 축별 근거 칩.
class AxisChip extends StatelessWidget {
  const AxisChip(this.axis, {super.key});
  final AxisReport axis;
  @override
  Widget build(BuildContext context) {
    final active = axis.usable;
    final score = axis.score ?? 0;
    final color = !active ? T.muted : score >= 0.7 ? T.high : score >= 0.4 ? T.caution : T.low;
    return Semantics(
      label: '${axisLabel(axis.axis)} 축, ${active ? '점수 ${pct(axis.score)}' : axisStatusLabel(axis.status)}',
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        decoration: BoxDecoration(border: Border.all(color: active ? color : T.line, width: 2)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(axisLabel(axis.axis), style: T.title(15)),
          const SizedBox(height: 4),
          Text(active ? pct(axis.score) : axisStatusLabel(axis.status),
              style: T.mono(color: color, size: 13, weight: FontWeight.w700)),
        ]),
      ),
    );
  }
}

class ScoreBar extends StatelessWidget {
  const ScoreBar(this.value, {super.key, this.color = T.accent});
  final double value;
  final Color color;
  @override
  Widget build(BuildContext context) => SizedBox(
        height: 6,
        child: Stack(children: [
          Container(color: T.line),
          FractionallySizedBox(widthFactor: value.clamp(0, 1), child: Container(color: color)),
        ]),
      );
}

class EvidenceRow extends StatelessWidget {
  const EvidenceRow(this.e, {super.key});
  final Evidence e;
  @override
  Widget build(BuildContext context) {
    final (mark, color) = switch (e.supportsAi) {
      true => ('+', T.accent),
      false => ('−', T.low),
      null => ('·', T.muted),
    };
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(width: 20, child: Text(mark, style: T.mono(color: color, size: 16, weight: FontWeight.w800))),
        Expanded(child: Text(e.message, style: T.body(size: 15))),
      ]),
    );
  }
}

class HistoryTile extends StatelessWidget {
  const HistoryTile(this.item, {super.key, required this.onTap});
  final HistoryItem item;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 14),
          child: Row(children: [
            RiskBadge(item.risk),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(item.title ?? (item.track == 'image' ? '이미지' : '영상'),
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: T.title(15)),
                const SizedBox(height: 2),
                Text('${item.track.toUpperCase()} · ${_ago(item.createdAt)}', style: T.mono()),
              ]),
            ),
            Text(pct(item.score), style: T.mono(color: T.text, size: 16, weight: FontWeight.w700)),
          ]),
        ),
      );
}

String _ago(DateTime t) {
  final d = DateTime.now().difference(t);
  if (d.inMinutes < 1) return '방금';
  if (d.inHours < 1) return '${d.inMinutes}분 전';
  if (d.inDays < 1) return '${d.inHours}시간 전';
  return '${d.inDays}일 전';
}

void showError(BuildContext context, Object e) =>
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
