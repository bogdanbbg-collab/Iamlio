<?php
// Contorul „citită de X ori” (de câte ori a fost deschisă o poveste).
// GET            → {"citiri": {"<id>": număr, ...}}
// POST ?id=<id>  → crește contorul poveștii și întoarce toate contoarele, plus "numarat": true/false.
//                  Protecție: aceeași adresă numără o poveste cel mult o dată la 30 de minute și
//                  cel mult MAX_PER_HOUR citiri pe oră în total. Numărul e orientativ, nu o statistică exactă.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

const WINDOW_SECONDS = 1800;   // același vizitator + aceeași poveste = o singură citire în 30 de minute
const MAX_PER_HOUR = 30;       // câte citiri (orice poveste) poate număra aceeași adresă într-o oră
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
$hourly = isset($stored['ore']) && is_array($stored['ore']) ? $stored['ore'] : [];
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
        return is_int($time) && $now - $time < WINDOW_SECONDS;
    });
    $hourly = array_filter($hourly, function ($entry) use ($now) {
        return is_array($entry) && isset($entry[0], $entry[1]) && $now - $entry[0] < 3600;
    });
    // Nu păstrăm adresa IP, doar amprente din care nu se poate reconstitui.
    $address = $_SERVER['REMOTE_ADDR'] ?? '';
    $visitor = hash('sha256', 'poveste|' . $address . '|' . $id);
    $client = hash('sha256', 'ora|' . $address);
    $usedThisHour = isset($hourly[$client]) ? (int) $hourly[$client][1] : 0;
    if (!isset($recent[$visitor]) && $usedThisHour < MAX_PER_HOUR) {
        $counts[$id] = (isset($counts[$id]) ? (int) $counts[$id] : 0) + 1;
        $recent[$visitor] = $now;
        $hourly[$client] = [isset($hourly[$client]) ? $hourly[$client][0] : $now, $usedThisHour + 1];
        $counted = true;
    }
    if (count($recent) > MAX_RECENT) {
        asort($recent);
        $recent = array_slice($recent, -MAX_RECENT, null, true);
    }
    if (count($hourly) > MAX_RECENT) {
        $hourly = array_slice($hourly, -MAX_RECENT, null, true);
    }

    ftruncate($handle, 0);
    rewind($handle);
    fwrite($handle, json_encode(['citiri' => $counts, 'recente' => $recent, 'ore' => $hourly], JSON_UNESCAPED_UNICODE));
    fflush($handle);
}

flock($handle, LOCK_UN);
fclose($handle);

$response = ['citiri' => (object) $counts];
if ($method === 'POST') {
    $response['numarat'] = $counted;
}
echo json_encode($response, JSON_UNESCAPED_UNICODE);
