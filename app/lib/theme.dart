import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Bold Typography 디자인 토큰 — 다크 배경, 버밀리언 액센트, 모서리 반경 0.
class T {
  static const bg = Color(0xFF0A0A0A);
  static const surface = Color(0xFF141414);
  static const line = Color(0xFF2A2A2A);
  static const text = Color(0xFFF5F5F5);
  static const muted = Color(0xFF9A9A9A);
  static const accent = Color(0xFFFF3D00);

  // 신호등 — 고대비 유지
  static const low = Color(0xFF00E676);
  static const caution = Color(0xFFFFD600);
  static const high = Color(0xFFFF1744);

  static const gap = 16.0;
  static const pad = EdgeInsets.symmetric(horizontal: 24);

  static TextStyle display(double size, {Color color = text}) => GoogleFonts.interTight(
      fontSize: size, fontWeight: FontWeight.w900, height: 0.95, letterSpacing: -1.5, color: color);

  static TextStyle title(double size, {Color color = text}) =>
      GoogleFonts.interTight(fontSize: size, fontWeight: FontWeight.w800, height: 1.1, color: color);

  static TextStyle body({Color color = text, double size = 16}) =>
      GoogleFonts.interTight(fontSize: size, fontWeight: FontWeight.w500, height: 1.45, color: color);

  static TextStyle mono({Color color = muted, double size = 12, FontWeight weight = FontWeight.w500}) =>
      GoogleFonts.jetBrainsMono(fontSize: size, fontWeight: weight, letterSpacing: 0.5, color: color);

  static ThemeData theme() {
    const zero = RoundedRectangleBorder(borderRadius: BorderRadius.zero);
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: bg,
      colorScheme: const ColorScheme.dark(primary: accent, surface: surface, onSurface: text),
      textTheme: GoogleFonts.interTightTextTheme(ThemeData.dark().textTheme),
      appBarTheme: AppBarTheme(
          backgroundColor: bg, elevation: 0, scrolledUnderElevation: 0,
          titleTextStyle: mono(size: 13, color: text, weight: FontWeight.w700)),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface,
        hintStyle: body(color: muted),
        border: const OutlineInputBorder(borderRadius: BorderRadius.zero, borderSide: BorderSide(color: line)),
        enabledBorder:
            const OutlineInputBorder(borderRadius: BorderRadius.zero, borderSide: BorderSide(color: line)),
        focusedBorder: const OutlineInputBorder(
            borderRadius: BorderRadius.zero, borderSide: BorderSide(color: accent, width: 2)),
      ),
      filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
              backgroundColor: accent, foregroundColor: bg, shape: zero,
              minimumSize: const Size.fromHeight(56), textStyle: title(16))),
      outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
              foregroundColor: text, shape: zero, side: const BorderSide(color: text, width: 2),
              minimumSize: const Size.fromHeight(56), textStyle: title(16))),
      progressIndicatorTheme: const ProgressIndicatorThemeData(color: accent, linearTrackColor: line),
      snackBarTheme: SnackBarThemeData(
          backgroundColor: surface, contentTextStyle: body(), shape: zero, behavior: SnackBarBehavior.floating),
    );
  }
}
