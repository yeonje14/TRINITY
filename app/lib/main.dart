import 'package:flutter/material.dart';

import 'screens/home.dart';
import 'theme.dart';

void main() => runApp(const TrinityApp());

class TrinityApp extends StatelessWidget {
  const TrinityApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'TRINITY',
        debugShowCheckedModeBanner: false,
        theme: T.theme(),
        home: const HomeScreen(),
      );
}
