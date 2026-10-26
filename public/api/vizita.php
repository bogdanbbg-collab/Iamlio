<?php
// Vizitele site-ului, pentru panoul de administrare: doar totaluri pe zi.
// POST ?pagina=acasa|poveste|altele → numără o afișare; un vizitator e numărat o singură dată pe zi.
//
// Confidențialitate: fără cookie-uri pentru vizitatori și fără adrese IP salvate. Ca un vizitator să fie numărat
// o dată pe zi, se păstrează până la sfârșitul zilei doar amprente HMAC (vezi comun.php), apoi se șterg.
// Vizitele administratorului (autentificat) nu se numără.
require __DIR__ . '/comun.php';

const PAGES = ['acasa', 'poveste', 'altele'];
const MAX_PER_VISITOR_DAY = 300;
const KEEP_DAYS = 400;

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
    header('Allow: POST');
    send_json(405, ['error' => 'metodă nepermisă']);
}
if (admin_session_valid()) {
    send_json(200, ['numarat' => false]);
}

$page = isset($_GET['pagina']) && in_array($_GET['pagina'], PAGES, true) ? $_GET['pagina'] : 'altele';
$lock = lock_resource('vizite');
$file = data_path('vizite.json');
$stored = read_json_file($file);
$today = date('Y-m-d');
$days = isset($stored['zile']) && is_array($stored['zile']) ? $stored['zile'] : [];
$marks = isset($stored['azi'], $stored['amprente']) && $stored['azi'] === $today && is_array($stored['amprente'])
    ? $stored['amprente'] : [];

$who = visitor_mark('vizita');
$seen = isset($marks[$who]) ? (int) $marks[$who] : 0;
if ($seen >= MAX_PER_VISITOR_DAY) {
    send_json(200, ['numarat' => false]);
}
$day = isset($days[$today]) && is_array($days[$today]) ? $days[$today] : ['vizitatori' => 0, 'afisari' => []];
if (!$seen) {
    $day['vizitatori'] = (int) $day['vizitatori'] + 1;
}
$day['afisari'][$page] = (isset($day['afisari'][$page]) ? (int) $day['afisari'][$page] : 0) + 1;
$days[$today] = $day;
$marks[$who] = $seen + 1;
ksort($days);
$days = array_slice($days, -KEEP_DAYS, null, true);

if (!write_json_atomic($file, ['zile' => (object) $days, 'azi' => $today, 'amprente' => (object) $marks])) {
    send_json(500, ['error' => 'vizita nu a putut fi salvată']);
}
send_json(200, ['numarat' => true]);
