<?php
// Contorul „citită de X ori”.
// GET            → {"citiri": {"<id>": număr, ...}}
// POST ?id=<id>  → crește contorul poveștii și întoarce toate contoarele
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

$dataFile = __DIR__ . '/data/citiri.json';
if (!is_dir(dirname($dataFile))) {
    mkdir(dirname($dataFile), 0755, true);
}

$handle = fopen($dataFile, 'c+');
if ($handle === false || !flock($handle, LOCK_EX)) {
    http_response_code(500);
    echo '{"error":"contorul nu este disponibil"}';
    exit;
}

$counts = json_decode(stream_get_contents($handle) ?: '{}', true);
if (!is_array($counts)) {
    $counts = [];
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $id = isset($_GET['id']) ? (string) $_GET['id'] : '';
    $storyExists = preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/', $id)
        && is_file(__DIR__ . '/../stories/' . $id . '/story.json');
    if (!$storyExists) {
        flock($handle, LOCK_UN);
        fclose($handle);
        http_response_code(404);
        echo '{"error":"poveste necunoscută"}';
        exit;
    }
    $counts[$id] = (isset($counts[$id]) ? (int) $counts[$id] : 0) + 1;
    ftruncate($handle, 0);
    rewind($handle);
    fwrite($handle, json_encode($counts, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    fflush($handle);
}

flock($handle, LOCK_UN);
fclose($handle);

echo json_encode(['citiri' => (object) $counts], JSON_UNESCAPED_UNICODE);
