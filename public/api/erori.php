<?php
// Erorile din browserele vizitatorilor (JavaScript, imagini sau fișiere audio care nu se încarcă), pentru panoul
// de administrare. POST cu JSON {tip, mesaj, sursa, linie, pagina}. Nu conține date personale: doar mesajul
// erorii, fișierul, pagina și familia browserului (ex. „Safari · telefon”). Se păstrează 14 zile.
require __DIR__ . '/comun.php';

const TYPES = ['js', 'promisiune', 'imagine', 'audio', 'alta'];
const MAX_PER_VISITOR_DAY = 30;

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
    header('Allow: POST');
    send_json(405, ['error' => 'metodă nepermisă']);
}
$raw = (string) file_get_contents('php://input', false, null, 0, 4096);
$report = json_decode($raw, true);
if (!is_array($report) || empty($report['mesaj'])) {
    send_json(400, ['error' => 'raport invalid']);
}

// cel mult MAX_PER_VISITOR_DAY rapoarte pe zi de la același vizitator (amprente HMAC, păstrate o zi)
$lock = lock_resource('erori-vizitatori');
$file = data_path('erori-vizitatori.json');
$stored = read_json_file($file);
$today = date('Y-m-d');
$marks = isset($stored['azi'], $stored['amprente']) && $stored['azi'] === $today && is_array($stored['amprente'])
    ? $stored['amprente'] : [];
$who = visitor_mark('erori');
$sent = isset($marks[$who]) ? (int) $marks[$who] : 0;
if ($sent >= MAX_PER_VISITOR_DAY) {
    send_json(429, ['error' => 'prea multe rapoarte']);
}
$marks[$who] = $sent + 1;
write_json_atomic($file, ['azi' => $today, 'amprente' => (object) $marks]);
flock($lock, LOCK_UN);

$type = isset($report['tip']) && in_array($report['tip'], TYPES, true) ? $report['tip'] : 'alta';
record_error($type, $report['mesaj'], $report['sursa'] ?? '', (int) ($report['linie'] ?? 0), $report['pagina'] ?? '');
send_json(200, ['primit' => true]);
