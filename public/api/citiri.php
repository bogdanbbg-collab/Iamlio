<?php
// Contorul „citită de X ori” (de câte ori a fost deschisă o poveste).
// GET            → {"citiri": {"<id>": număr, ...}}
// POST ?id=<id>  → crește contorul poveștii (cel mult o dată la 30 de minute pentru același vizitator)
//                  și întoarce toate contoarele, plus "numarat": true/false
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

const WINDOW_SECONDS = 1800;   // același vizitator + aceeași poveste = o singură citire în 30 de minute
const MAX_RECENT = 20000;      // câte urme de vizitatori păstrăm (siguranță pentru fișier)

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if ($method !== 'GET' && $method !== 'POST') {
    http_response_code(405);
    header('Allow: GET, POST');
    echo '{"error":"metodă nepermisă"}';
    exit;
}

$dataDir = __DIR__ . '/data';
if (!is_dir($dataDir)) {
    mkdir($dataDir, 0755, true);
}

$handle = fopen($dataDir . '/citiri.json', 'c+');
if ($handle === false || !flock($handle, LOCK_EX)) {
    http_response_code(500);
    echo '{"error":"contorul nu este disponibil"}';
    exit;
}

function fail($handle, $code, $message)
{
    flock($handle, LOCK_UN);
    fclose($handle);
    http_response_code($code);
    echo json_encode(['error' => $message], JSON_UNESCAPED_UNICODE);
    exit;
}

$stored = json_decode(stream_get_contents($handle) ?: '{}', true);
if (!is_array($stored)) {
    $stored = [];
}
// Format: {"citiri": {...}, "recente": {"<amprentă>": timestamp}}. Formatul vechi era doar {"<id>": număr}.
$counts = isset($stored['citiri']) && is_array($stored['citiri']) ? $stored['citiri'] : array_filter($stored, 'is_int');
$recent = isset($stored['recente']) && is_array($stored['recente']) ? $stored['recente'] : [];
$counted = false;

if ($method === 'POST') {
    $id = isset($_GET['id']) ? (string) $_GET['id'] : '';
    $storyExists = preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/', $id)
        && is_file(__DIR__ . '/../stories/' . $id . '/story.json');
    if (!$storyExists) {
        fail($handle, 404, 'poveste necunoscută');
    }

    $now = time();
    $recent = array_filter($recent, function ($time) use ($now) {
        return $now - $time < WINDOW_SECONDS;
    });
    // Nu păstrăm adresa IP, doar o amprentă din care nu se poate reconstitui.
    $visitor = hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . '|' . ($_SERVER['HTTP_USER_AGENT'] ?? '') . '|' . $id);
    if (!isset($recent[$visitor])) {
        $counts[$id] = (isset($counts[$id]) ? (int) $counts[$id] : 0) + 1;
        $recent[$visitor] = $now;
        $counted = true;
    }
    if (count($recent) > MAX_RECENT) {
        asort($recent);
        $recent = array_slice($recent, -MAX_RECENT, null, true);
    }

    ftruncate($handle, 0);
    rewind($handle);
    fwrite($handle, json_encode(['citiri' => $counts, 'recente' => $recent], JSON_UNESCAPED_UNICODE));
    fflush($handle);
}

flock($handle, LOCK_UN);
fclose($handle);

$response = ['citiri' => (object) $counts];
if ($method === 'POST') {
    $response['numarat'] = $counted;
}
echo json_encode($response, JSON_UNESCAPED_UNICODE);
