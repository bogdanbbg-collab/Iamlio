<?php
// Contorul „citită de X ori” (de câte ori a fost deschisă o poveste).
// GET            → {"citiri": {"<id>": număr, ...}}
// POST ?id=<id>  → crește contorul poveștii și întoarce toate contoarele, plus "numarat": true/false.
//
// Protecție: aceeași adresă numără o poveste cel mult o dată la 30 de minute și cel mult MAX_PER_HOUR citiri
// pe oră în total. Pe o rețea comună (aceeași adresă pentru o familie sau o grădiniță), două citiri ale aceleiași
// povești în 30 de minute se numără o dată: numărul e orientativ, nu o statistică exactă.
// Confidențialitate: adresa IP nu se salvează; se păstrează cel mult o oră amprente HMAC (vezi comun.php).
// Siguranța datelor: scriere atomică și o copie zilnică în data/copii/ (ultimele 14 zile).
require __DIR__ . '/comun.php';

const WINDOW_SECONDS = 1800;
const HOUR = 3600;
const MAX_PER_HOUR = 120;
const MAX_RECENT = 20000;
const BACKUP_DAYS = 14;

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if ($method !== 'GET' && $method !== 'POST') {
    header('Allow: GET, POST');
    send_json(405, ['error' => 'metodă nepermisă']);
}

$lock = lock_resource('citiri');
$file = data_path('citiri.json');
$stored = read_json_file($file);
// Formatul vechi era doar {"<id>": număr}.
$counts = isset($stored['citiri']) && is_array($stored['citiri']) ? $stored['citiri'] : array_filter($stored, 'is_int');
$recent = isset($stored['recente']) && is_array($stored['recente']) ? $stored['recente'] : [];
$hourly = isset($stored['ore']) && is_array($stored['ore']) ? $stored['ore'] : [];

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
        send_json(404, ['error' => 'poveste necunoscută']);
    }
    $visitor = visitor_mark('poveste|' . $id);
    $client = visitor_mark('ora');
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
    $saved = write_json_atomic($file, ['citiri' => (object) $counts, 'recente' => (object) $recent, 'ore' => (object) $hourly]);
    if (!$saved) {
        send_json(500, ['error' => 'contorul nu a putut fi salvat']);
    }
    // copie zilnică (doar numerele, fără amprente), păstrată BACKUP_DAYS zile
    $backups = data_path('copii');
    if (!is_dir($backups)) {
        mkdir($backups, 0750, true);
    }
    $today = $backups . '/citiri-' . gmdate('Y-m-d') . '.json';
    if (!is_file($today)) {
        write_json_atomic($today, ['citiri' => (object) $counts]);
        foreach (glob($backups . '/citiri-*.json') ?: [] as $old) {
            if (filemtime($old) < $now - BACKUP_DAYS * 86400) {
                @unlink($old);
            }
        }
    }
}

$response = ['citiri' => (object) $counts];
if ($method === 'POST') {
    $response['numarat'] = $counted;
}
send_json(200, $response);
