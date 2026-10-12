// Regenerates the typed OpenAPI client from the canonical schema snapshot
// (MT-5.5-03, NFR-11 / ADR-005: schemas/openapi.yaml is the single source).
//
// Usage (from mobile/):
//   dart run tool/openapi_client.dart regen   # regenerate the committed client
//   dart run tool/openapi_client.dart check   # regenerate and fail on drift
//
// Determinism: the OpenAPI Generator version is pinned (below) and its jar is
// checksum-verified on download; the schema is read offline from the
// committed snapshot; generated Dart is formatted and the built_value part
// files are produced with the build_runner/built_value_generator versions
// locked in pubspec.lock. `check` snapshots the committed client, regenerates
// in place and exits non-zero on any byte difference (Section 18 contract
// row: drift fails the pipeline).
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';

/// Pinned OpenAPI Generator release (Maven coordinate openapi-generator-cli).
const String generatorVersion = '7.26.0';

const String generatorUrl =
    'https://repo1.maven.org/maven2/org/openapitools/openapi-generator-cli/'
    '$generatorVersion/openapi-generator-cli-$generatorVersion.jar';

const String generatorSha256 =
    '1760050094997b9cc790cc1350be095f15da8c08a996b184d3eadc4ccda5e35e'; // pragma: allowlist secret

/// Generator name (dio-based Dart client: typed models + interceptor seam
/// for the Section 9.2 error mapping).
const String generator = 'dart-dio';

/// Package name baked into generated imports (`package:<pubName>/...`), so
/// the output must live at the conventional `lib/src/` of this package.
const String pubName = 'orchestrator_mobile';

/// Directory that regen/check own inside `lib/` (everything under it is
/// generated; hand-written code never lives here).
const String generatedDir = 'lib/src';

/// The generated barrel file at `lib/` root (name follows [pubName]).
const String generatedBarrel = 'lib/$pubName.dart';

/// [packageRoot] is computed from this script's location (`mobile/tool/`).
final Directory packageRoot = () {
  final String scriptPath = Platform.script.toFilePath();
  return Directory(scriptPath).parent.parent;
}();

final Directory cacheDir =
    Directory('${packageRoot.path}${Platform.pathSeparator}.dart_tool'
        '${Platform.pathSeparator}openapi-generator');

final File schemaFile = File('${packageRoot.parent.path}'
    '${Platform.pathSeparator}schemas${Platform.pathSeparator}openapi.yaml');

final File jarFile = File('${cacheDir.path}${Platform.pathSeparator}'
    'openapi-generator-cli-$generatorVersion.jar');

Future<void> main(List<String> args) async {
  final String mode = args.isNotEmpty ? args.first : 'regen';
  if (mode != 'regen' && mode != 'check') {
    stderr.writeln('usage: dart run tool/openapi_client.dart [regen|check]');
    exitCode = 2;
    return;
  }

  if (!schemaFile.existsSync()) {
    stderr.writeln('schema not found: ${schemaFile.path}');
    exitCode = 2;
    return;
  }

  final Map<String, String> baseline = mode == 'check' ? snapshotClient() : {};

  try {
    await ensureGeneratorJar();
    generate();
    runBuildRunner();
    stampGeneratedHeaders();
    formatGenerated();
  } on ToolFailure catch (e) {
    stderr.writeln(e.message);
    exitCode = 2;
    return;
  }

  if (mode == 'regen') {
    stdout.writeln('regenerated $generatedBarrel + $generatedDir '
        'from ${schemaFile.path}');
    return;
  }

  // check: compare the regenerated client against the snapshot.
  final Map<String, String> current = snapshotClient();
  final List<String> drift = <String>{
    ...baseline.keys,
    ...current.keys,
  }.where((String p) => baseline[p] != current[p]).toList()
    ..sort();

  if (drift.isEmpty) {
    stdout.writeln('client in sync with ${schemaFile.path} '
        '(generator $generatorVersion)');
    return;
  }
  stderr.writeln('DRIFT between the committed client and '
      '${schemaFile.path}:');
  for (final String path in drift) {
    final String state = !baseline.containsKey(path)
        ? 'missing in committed client'
        : !current.containsKey(path)
            ? 'stale (no longer generated)'
            : 'content differs';
    stderr.writeln('  $path: $state');
  }
  stderr.writeln('Run `dart run tool/openapi_client.dart regen` and commit '
      'the result.');
  exitCode = 1;
}

class ToolFailure implements Exception {
  ToolFailure(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Bytes of every generated file currently in the package (barrel, `lib/src`
/// tree including built_value part files).
Map<String, String> snapshotClient() {
  final Map<String, String> files = <String, String>{};
  final File barrel = File('${packageRoot.path}${Platform.pathSeparator}'
      '${generatedBarrel.replaceAll('/', Platform.pathSeparator)}');
  if (barrel.existsSync()) {
    files[generatedBarrel] = _sha256Of(barrel);
  }
  final Directory gen = Directory('${packageRoot.path}'
      '${Platform.pathSeparator}${generatedDir.replaceAll('/', Platform.pathSeparator)}');
  if (gen.existsSync()) {
    for (final FileSystemEntity e
        in gen.listSync(recursive: true, followLinks: false)) {
      if (e is File) {
        final String rel = 'lib/src/'
            '${e.path.substring(gen.path.length + 1).replaceAll(Platform.pathSeparator, '/')}';
        files[rel] = _sha256Of(e);
      }
    }
  }
  return files;
}

String _sha256Of(File f) => sha256.convert(f.readAsBytesSync()).toString();

Future<void> ensureGeneratorJar() async {
  if (jarFile.existsSync()) {
    final String digest = _sha256Of(jarFile);
    if (digest != generatorSha256) {
      stderr.writeln('cached jar checksum mismatch ($digest) — removing');
      jarFile.deleteSync();
    }
  }
  if (jarFile.existsSync()) {
    return;
  }
  cacheDir.createSync(recursive: true);
  stdout.writeln('downloading openapi-generator-cli $generatorVersion ...');
  final HttpClient client = HttpClient();
  try {
    final HttpClientRequest request =
        await client.getUrl(Uri.parse(generatorUrl));
    final HttpClientResponse response = await request.close();
    if (response.statusCode != HttpStatus.ok) {
      throw ToolFailure('download failed: HTTP ${response.statusCode} '
          'for $generatorUrl');
    }
    final List<int> bytes = await response.fold<List<int>>(
      <int>[],
      (List<int> acc, List<int> chunk) => acc..addAll(chunk),
    );
    jarFile.writeAsBytesSync(bytes);
  } finally {
    client.close(force: true);
  }
  final String digest = _sha256Of(jarFile);
  if (digest != generatorSha256) {
    jarFile.deleteSync();
    throw ToolFailure('jar checksum mismatch: expected $generatorSha256 '
        'got $digest');
  }
}

void generate() {
  final Directory out = Directory('${cacheDir.path}${Platform.pathSeparator}'
      'out');
  if (out.existsSync()) {
    out.deleteSync(recursive: true);
  }
  final ProcessResult result = Process.runSync(
    'java',
    <String>[
      '-jar',
      jarFile.path,
      'generate',
      '-i',
      schemaFile.path,
      '-g',
      generator,
      '-o',
      out.path,
      '--additional-properties=pubName=$pubName,hideGenerationTimestamp=true',
    ],
    stdoutEncoding: utf8,
    stderrEncoding: utf8,
  );
  if (result.exitCode != 0) {
    throw ToolFailure('openapi-generator failed '
        '(exit ${result.exitCode}):\n${result.stdout}\n${result.stderr}');
  }

  // Sync ONLY the lib/ outputs: the generated package's own pubspec, README,
  // doc/ and test/ folders are not part of this package.
  final File filesManifest =
      File('${out.path}${Platform.pathSeparator}.openapi-generator'
          '${Platform.pathSeparator}FILES');
  if (!filesManifest.existsSync()) {
    throw ToolFailure('generator did not write .openapi-generator/FILES');
  }
  final List<String> libEntries = filesManifest
      .readAsLinesSync()
      .map((String l) => l.trim().replaceAll('\\', '/'))
      .where((String l) => l.isNotEmpty && l.startsWith('lib/'))
      .toList();
  if (!libEntries.contains(generatedBarrel)) {
    throw ToolFailure('expected $generatedBarrel in generator output, got: '
        '${libEntries.take(5).join(', ')}');
  }
  final bool outside = libEntries.any(
    (String l) => l != generatedBarrel && !l.startsWith('$generatedDir/'),
  );
  if (outside) {
    throw ToolFailure('generator output outside $generatedDir: $libEntries');
  }

  // Replace the owned paths wholesale so stale files are pruned too.
  final Directory gen = Directory('${packageRoot.path}'
      '${Platform.pathSeparator}${generatedDir.replaceAll('/', Platform.pathSeparator)}');
  if (gen.existsSync()) {
    gen.deleteSync(recursive: true);
  }
  gen.createSync(recursive: true);
  for (final String entry in libEntries) {
    final File src = File(
        '${out.path}${Platform.pathSeparator}${entry.replaceAll('/', Platform.pathSeparator)}');
    if (!src.existsSync()) {
      throw ToolFailure('generator manifest lists missing file: $entry');
    }
    final File dst = File('${packageRoot.path}${Platform.pathSeparator}'
        '${entry.replaceAll('/', Platform.pathSeparator)}');
    dst.parent.createSync(recursive: true);
    src.copySync(dst.path);
  }
}

void runBuildRunner() {
  // built_value part files (*.g.dart) for the generated @BuiltValue models.
  final ProcessResult result = Process.runSync(
    'dart',
    <String>['run', 'build_runner', 'build', '--delete-conflicting-outputs'],
    workingDirectory: packageRoot.path,
    stdoutEncoding: utf8,
    stderrEncoding: utf8,
  );
  if (result.exitCode != 0) {
    throw ToolFailure('build_runner failed (exit ${result.exitCode}):\n'
        '${result.stdout}\n${result.stderr}');
  }
}

/// Style lints the generator's output cannot satisfy under flutter_lints.
/// They are silenced per generated FILE (never package-wide), so the type
/// checker still covers every generated line (Section 18 contract row: the
/// generated clients compile). Applied identically on every regen, so `check`
/// stays byte-deterministic.
const List<String> generatedLintExemptions = <String>[
  'constant_identifier_names',
  'no_leading_underscores_for_local_identifiers',
  'unnecessary_brace_in_string_interps',
  'unnecessary_this',
  'unused_import',
  'use_function_type_syntax_for_parameters',
  'use_super_parameters',
];

void stampGeneratedHeaders() {
  final List<File> files = <File>[
    File('${packageRoot.path}${Platform.pathSeparator}'
        '${generatedBarrel.replaceAll('/', Platform.pathSeparator)}'),
    ...Directory('${packageRoot.path}${Platform.pathSeparator}'
            '${generatedDir.replaceAll('/', Platform.pathSeparator)}')
        .listSync(recursive: true)
        .whereType<File>()
        .where((File f) => f.path.endsWith('.dart')),
  ];
  for (final File file in files) {
    final List<String> lines = file.readAsLinesSync();
    final int existing = lines.indexWhere(
      (String l) => l.startsWith('// ignore_for_file:'),
    );
    final Set<String> tokens = <String>{...generatedLintExemptions};
    if (existing >= 0) {
      tokens.addAll(
        lines[existing]
            .substring('// ignore_for_file:'.length)
            .split(',')
            .map((String t) => t.trim())
            .where((String t) => t.isNotEmpty),
      );
      lines[existing] =
          '// ignore_for_file: ${(tokens.toList()..sort()).join(', ')}';
    } else {
      lines.insert(
        0,
        '// ignore_for_file: ${(tokens.toList()..sort()).join(', ')}',
      );
    }
    file.writeAsStringSync('${lines.join('\n')}\n');
  }
}

void formatGenerated() {
  // Keeps the committed output clean under the repo-wide
  // `dart format --set-exit-if-changed` gate.
  final ProcessResult result = Process.runSync(
    'dart',
    <String>['format', generatedBarrel, generatedDir],
    workingDirectory: packageRoot.path,
    stdoutEncoding: utf8,
    stderrEncoding: utf8,
  );
  if (result.exitCode != 0) {
    throw ToolFailure('dart format failed (exit ${result.exitCode}):\n'
        '${result.stdout}\n${result.stderr}');
  }
}
