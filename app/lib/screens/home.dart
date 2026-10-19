import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../api/client.dart';
import '../api/models.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'analyzing.dart';
import 'result.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _url = TextEditingController();
  bool _busy = false;
  late Future<List<HistoryItem>> _history = api.history();

  void _refresh() => setState(() => _history = api.history());

  Future<void> _open(Widget screen) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
    if (mounted) _refresh();
  }

  Future<void> _analyzeUrl() async {
    final url = _url.text.trim();
    if (url.isEmpty) return;
    setState(() => _busy = true);
    try {
      final jobId = await api.analyzeUrl(url);
      _url.clear();
      await _open(AnalyzingScreen(jobId: jobId));
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _analyzeImage() async {
    final file = await FilePicker.pickFile(type: FileType.image);
    if (file == null) return;
    setState(() => _busy = true);
    try {
      final result = await api.analyzeImage(await file.readAsBytes(), file.name);
      await _open(ResultScreen(result: result));
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openHistory(HistoryItem item) async {
    try {
      await _open(ResultScreen(result: await api.analysis(item.id)));
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async => _refresh(),
          child: ListView(padding: T.pad, children: [
            const SizedBox(height: 40),
            const Label('3-Axis AI Media Detector', color: T.accent),
            const SizedBox(height: 12),
            Text('TRINITY', style: T.display(64)),
            const SizedBox(height: 12),
            Text('신호가 말하고, 출처가 증언하며,\n의미가 검증한다.', style: T.body(color: T.muted, size: 17)),
            const SizedBox(height: 40),
            const Label('유튜브 링크'),
            const SizedBox(height: 8),
            TextField(
              controller: _url,
              enabled: !_busy,
              style: T.body(),
              keyboardType: TextInputType.url,
              decoration: const InputDecoration(hintText: 'https://youtube.com/watch?v=...'),
              onSubmitted: (_) => _analyzeUrl(),
            ),
            const SizedBox(height: 12),
            FilledButton(onPressed: _busy ? null : _analyzeUrl, child: const Text('영상 분석')),
            const SizedBox(height: 12),
            OutlinedButton(onPressed: _busy ? null : _analyzeImage, child: const Text('이미지 업로드')),
            if (_busy) ...[const SizedBox(height: 16), const LinearProgressIndicator()],
            const SizedBox(height: 48),
            const Label('최근 분석'),
            const SizedBox(height: 8),
            const Rule(color: T.text, thickness: 2),
            FutureBuilder<List<HistoryItem>>(
              future: _history,
              builder: (context, snap) {
                if (snap.connectionState != ConnectionState.done) {
                  return const Padding(padding: EdgeInsets.all(24), child: LinearProgressIndicator());
                }
                if (snap.hasError) {
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 20),
                    child: Text('${snap.error}', style: T.body(color: T.muted)),
                  );
                }
                final items = snap.data!;
                if (items.isEmpty) {
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 20),
                    child: Text('아직 분석 이력이 없습니다.', style: T.body(color: T.muted)),
                  );
                }
                return Column(children: [
                  for (final h in items) ...[HistoryTile(h, onTap: () => _openHistory(h)), const Rule()],
                ]);
              },
            ),
            const SizedBox(height: 40),
          ]),
        ),
      ),
    );
  }
}
