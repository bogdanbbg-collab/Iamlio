<?php
// Contorul „citită de X ori” (de câte ori a fost deschisă o poveste).
// GET            → {"citiri": {"<id>": număr, ...}}
// POST ?id=<id>  → crește contorul poveștii și întoarce toate contoarele, plus "numarat": true/false.
//
// Protecție: aceeași adresă numără o poveste cel mult o dată la 30 de minute și cel mult MAX_PER_HOUR citiri
// pe oră în total. Numărul e orientativ, nu o statistică exactă.
// Confidențialitate: adresa IP nu se salvează. Se păstrează doar amprente HMAC cu o cheie secretă generată pe
// server și schimbată zilnic (nu pot fi legate de o adresă și nici între zile), șterse după cel mult o oră.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

const WINDOW_SECONDS = 1800;   // aceeași adresă + aceeași poveste = o singură citire în 30 de minute
const HOUR = 3600;
const MAX_PER_HOUR = 30;       // câte citiri (orice poveste) poate număra aceeași adresă într-o oră
const MAX_RECENT = 20000;      // câte amprente păstrăm cel mult (siguranță pentru mărimea fișierului)

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if ($method !== 'GET' && $method !== 'POST') {
    http_response_code(405);
    header('Allow: GET, POST');
    echo '{"error":"metodă nepermisă"}';
    exit;
}

$dataDir = __DIR__ . '/data';
if (!is_dir($dataDir)) {
    mkdir($dataDir, 0750, true);
}

$handle = fopen($dataDir . '/citiri.json', 'c+');
if ($handle === false || !flock($handle, LOCK_EX)) {
    http_response_code(500);
    echo '{"error":"contorul nu este disponibil"}';
    exit;
}

function finish($handle, $code, $body)
{
    flock($handle, LOCK_UN);
    fclose($handle);
    http_response_code($code);
    echo json_encode($body, JSON_UNESCAPED_UNICODE);
    exit;
}

// Cheia secretă stă doar pe server (api/data/ nu e accesibil din internet și nu e în repository).
function secret_key($dataDir)
{
    $file = $dataDir . '/cheie.txt';
    $key = is_file($file) ? trim((string) file_get_contents($file)) : '';
    if (strlen($key) < 64) {
        $key = bin2hex(random_bytes(32));
        file_put_contents($file, $key, LOCK_EX);
        @chmod($file, 0600);
    }
    return $key;
}

$stored = json_decode(stream_get_contents($handle) ?: '{}', true);
if (!is_array($stored)) {
    $stored = [];
}
// Format: {"citiri": {...}, "recente": {amprentă: timp}, "ore": {amprentă: [început, număr]}}.
// Formatul vechi era doar {"<id>": număr}.
$counts = isset($stored['citiri']) && is_array($stored['citiri']) ? $stored['citiri'] : array_filter($stored, 'is_int');
$recent = isset($stored['recente']) && is_array($stored['recente']) ? $stored['recente'] : [];
$hourly = isset($stored['ore']) && is_array($stored['ore']) ? $stored['ore'] : [];

// Ștergem la fiecare cerere ce a expirat, ca nicio amprentă să nu rămână mai mult decât e nevoie.
$now = time();
$before = count($recent) + count($hourly);
$recent = array_filter($recent, function ($time) use ($now) {
    return is_int($time) && $now - $time < WINDOW_SECONDS;
});
$hourly = array_filter($hourly, function ($entry) use ($now) {
    return is_array($entry) && isset($entry[0], $entry[1]) && $now - $entry[0] < HOUR;
});
$dirty = count($recent) + count($hourly) !== $before || !isset($stored['citiri']);
$counted = false;

if ($method === 'POST') {
    $id = isset($_GET['id']) ? (string) $_GET['id'] : '';
    $storyExists = preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/', $id)
        && is_file(__DIR__ . '/../stories/' . $id . '/story.json');
    if (!$storyExists) {
        finish($handle, 404, ['error' => 'poveste necunoscută']);
    }

    $dailyKey = secret_key($dataDir) . '|' . gmdate('Y-m-d');
    $address = $_SERVER['REMOTE_ADDR'] ?? '';
    $visitor = hash_hmac('sha256', 'poveste|' . $address . '|' . $id, $dailyKey);
    $client = hash_hmac('sha256', 'ora|' . $address, $dailyKey);
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
    $dirty = true;
}

if ($dirty) {
    ftruncate($handle, 0);
    rewind($handle);
    fwrite($handle, json_encode(['citiri' => (object) $counts, 'recente' => (object) $recent, 'ore' => (object) $hourly],
        JSON_UNESCAPED_UNICODE));
    fflush($handle);
}

$response = ['citiri' => (object) $counts];
if ($method === 'POST') {
    $response['numarat'] = $counted;
}
finish($handle, 200, $response);
