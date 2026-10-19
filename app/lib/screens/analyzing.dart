import 'dart:async';

import 'package:flutter/material.dart';

import '../api/client.dart';
import '../api/models.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'result.dart';

/// 영상 분석 진행 화면 — 1초 간격 폴링.
class AnalyzingScreen extends StatefulWidget {
  const AnalyzingScreen({super.key, required this.jobId});
  final String jobId;
  @override
  State<AnalyzingScreen> createState() => _AnalyzingScreenState();
}

class _AnalyzingScreenState extends State<AnalyzingScreen> {
  Job? _job;
  String? _error;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _poll();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) => _poll());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _poll() async {
    try {
      final job = await api.job(widget.jobId);
      if (!mounted) return;
      setState(() => _job = job);
      if (job.state == JobState.done && job.result != null) {
        _timer?.cancel();
        Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => ResultScreen(result: job.result!)));
      } else if (job.state == JobState.failed) {
        _timer?.cancel();
        setState(() => _error = job.error ?? '분석에 실패했습니다');
      }
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final job = _job;
    return Scaffold(
      appBar: AppBar(title: const Text('ANALYZING')),
      body: Padding(
        padding: T.pad,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Spacer(),
          if (_error != null) ...[
            const Label('실패', color: T.high),
            const SizedBox(height: 12),
            Text(_error!, style: T.title(22)),
            const SizedBox(height: 32),
            OutlinedButton(onPressed: () => Navigator.of(context).pop(), child: const Text('돌아가기')),
          ] else ...[
            Semantics(
              liveRegion: true,
              child: Text(job?.stageLabel ?? '요청 접수', style: T.display(44)),
            ),
            const SizedBox(height: 24),
            LinearProgressIndicator(value: job?.progress, minHeight: 8),
            const SizedBox(height: 12),
            Text('${((job?.progress ?? 0) * 100).round()}%', style: T.mono(color: T.text, size: 14)),
            const SizedBox(height: 32),
            Text('전·중·후 구간을 샘플링해 신호·출처·의미 세 축을 병렬로 분석합니다.\n원본 영상은 분석 후 서버에서 삭제됩니다.',
                style: T.body(color: T.muted, size: 15)),
          ],
          const Spacer(flex: 2),
        ]),
      ),
    );
  }
}
