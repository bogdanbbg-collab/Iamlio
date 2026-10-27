<?php
// Panoul de administrare (admin.html). Toate datele cer autentificare (vezi comun.php).
//
// POST actiune=intrare, parola=…  → autentificare (sesiune de 12 ore)
// POST actiune=iesire             → deconectare
// POST actiune=sterge-erori       → golește lista de erori (după ce au fost rezolvate)
// GET                             → toate datele panoului: poveștile, citirile, părerile, vizitele, erorile, starea serverului
require __DIR__ . '/comun.php';

header('X-Robots-Tag: noindex, nofollow');

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$action = isset($_POST['actiune']) ? (string) $_POST['actiune'] : '';

if ($method === 'POST' && $action === 'intrare') {
    admin_login();
}
if ($method === 'POST' && $action === 'iesire') {
    admin_logout();
}
if (!admin_session_valid()) {
    send_json(401, ['error' => 'autentificare necesară']);
}
if ($method === 'POST' && $action === 'sterge-erori') {
    $lock = lock_resource('erori');
    write_json_atomic(data_path('erori.json'), ['grupuri' => (object) [], 'zi' => date('Y-m-d'), 'azi' => 0]);
    send_json(200, ['sters' => true]);
}
if ($method !== 'GET') {
    header('Allow: GET, POST');
    send_json(405, ['error' => 'metodă nepermisă']);
}

$reads = read_json_file(data_path('citiri.json'));
$visits = read_json_file(data_path('vizite.json'));
$errors = read_json_file(data_path('erori.json'));
$likes = read_json_file(data_path('pareri.json'));
$backups = glob(data_path('copii') . '/citiri-*.json') ?: [];
$lastBackup = $backups ? max(array_map('filemtime', $backups)) : 0;

send_json(200, [
    'acum' => date('c'),
    'azi' => date('Y-m-d'),
    // scris la publicare de scripts/stories.py stage: poveștile, versiunea publicată, bugetul imaginilor
    'site' => (object) read_json_file(data_path('admin-info.json')),
    'citiri' => [
        'totaluri' => (object) (isset($reads['citiri']) && is_array($reads['citiri']) ? $reads['citiri'] : []),
        'zile' => (object) (isset($reads['zile']) && is_array($reads['zile']) ? $reads['zile'] : []),
    ],
    'vizite' => (object) (isset($visits['zile']) && is_array($visits['zile']) ? $visits['zile'] : []),
    // „Ți-a plăcut povestea?”: pe poveste, câte voturi 1 (😐), 2 (🙂), 3 (😍)
    'pareri' => (object) (isset($likes['totaluri']) && is_array($likes['totaluri']) ? $likes['totaluri'] : []),
    'erori' => array_values(isset($errors['grupuri']) && is_array($errors['grupuri']) ? $errors['grupuri'] : []),
    'server' => [
        'php' => PHP_VERSION,
        'ultima_copie' => $lastBackup ? date('c', $lastBackup) : null,
        'copii' => count($backups),
    ],
]);
